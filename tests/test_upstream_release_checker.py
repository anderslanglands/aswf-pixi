from __future__ import annotations

from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_upstream_releases as upstream


def version(value: str) -> upstream.Version:
    parsed = upstream.Version.parse(value)
    assert parsed is not None
    return parsed


def release(value: str, tag: str | None = None) -> upstream.ReleaseCandidate:
    return upstream.ReleaseCandidate(version(value), tag or f"v{value}", "release")


class UpstreamReleaseCheckerTests(unittest.TestCase):
    def local_recipe(self, package: str, value: str) -> upstream.LocalRecipe:
        return upstream.LocalRecipe(
            package=package,
            path=Path(package) / value,
            version=version(value),
            repository="example/project",
            context={"version": value},
        )

    def test_numbered_tags_normalize_v_prefix_and_underscores(self) -> None:
        parsed = upstream.parse_numbered_tag("v3_7_0")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.text, "3.7.0")
        self.assertIsNone(upstream.parse_numbered_tag("v3.7.0-rc1"))
        self.assertIsNone(upstream.parse_numbered_tag("release-3.7.0"))

    def test_fetch_upstream_releases_ignores_drafts_and_prereleases(self) -> None:
        original_pages = upstream.github_api_pages

        def fake_pages(repo: str, endpoint: str, token: str | None):
            self.assertEqual(repo, "example/foo")
            self.assertEqual(endpoint, "releases")
            self.assertEqual(token, "token")
            yield [
                {"tag_name": "v1.2.4", "draft": True},
                {"tag_name": "v1.2.5", "prerelease": True},
                {"tag_name": "v1.2.6", "html_url": "https://example.test/release"},
            ]

        try:
            upstream.github_api_pages = fake_pages
            releases = upstream.fetch_upstream_releases("example/foo", "token")
        finally:
            upstream.github_api_pages = original_pages

        self.assertEqual([candidate.version.text for candidate in releases], ["1.2.6"])

    def test_release_selection_tracks_existing_lines_and_newer_lines_only(self) -> None:
        local_recipes = [
            self.local_recipe("openimageio", "2.5.19.1"),
            self.local_recipe("openimageio", "3.0.19.1"),
            self.local_recipe("openimageio", "3.1.14.0"),
        ]
        candidates = [
            release("2.4.99.0"),
            release("2.5.20.0"),
            release("3.0.20.0"),
            release("3.1.15.0"),
            release("3.2.0.0"),
            release("3.2.1.0"),
        ]

        selected = upstream.releases_to_package(local_recipes, candidates)

        self.assertEqual(
            [candidate.version.text for candidate in selected],
            ["2.5.20.0", "3.0.20.0", "3.1.15.0", "3.2.1.0"],
        )

    def test_closest_recipe_prefers_matching_semantic_line(self) -> None:
        local_recipes = [
            self.local_recipe("openimageio", "2.5.19.1"),
            self.local_recipe("openimageio", "3.0.19.1"),
            self.local_recipe("openimageio", "3.1.14.0"),
        ]

        self.assertEqual(
            upstream.closest_recipe(local_recipes, version("3.0.20.0")).path,
            Path("openimageio") / "3.0.19.1",
        )
        self.assertEqual(
            upstream.closest_recipe(local_recipes, version("3.2.0.0")).path,
            Path("openimageio") / "3.1.14.0",
        )

    def test_apply_copies_recipe_updates_tag_sha_build_number_and_readme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            root = Path(tmp_raw)
            recipe_dir = root / "foo" / "1.2.3"
            recipe_dir.mkdir(parents=True)
            (recipe_dir / "recipe.yaml").write_text(
                f"""context:
  version: "1.2.3"
  tag: v1_2_3
  build_number: 9

recipe:
  name: foo
  version: ${{{{ version }}}}

source:
  url: https://github.com/example/foo/archive/refs/tags/${{{{ tag }}}}.tar.gz
  sha256: {"0" * 64}

about:
  repository: https://github.com/example/foo
""",
                encoding="utf-8",
            )
            (recipe_dir / "pixi.toml").write_text(
                "[tasks]\nbuild-foo-1-2-3 = \"echo 1.2.3\"\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text(
                "# Packages\n\n## Foo\n\nRecipe versions: `1.2.3`\n",
                encoding="utf-8",
            )

            def fake_releases(repo: str, token: str | None) -> list[upstream.ReleaseCandidate]:
                self.assertEqual(repo, "example/foo")
                self.assertIsNone(token)
                return [release("1.2.4", "v1_2_4")]

            def fake_sha256(url: str, token: str | None) -> str:
                self.assertEqual(url, "https://github.com/example/foo/archive/refs/tags/v1_2_4.tar.gz")
                self.assertIsNone(token)
                return "a" * 64

            created = upstream.check_upstream_releases(
                root,
                packages=None,
                token=None,
                apply=True,
                release_fetcher=fake_releases,
                sha256_fetcher=fake_sha256,
            )

            self.assertEqual([recipe.recipe for recipe in created], ["foo/1.2.4"])
            new_recipe = (root / "foo" / "1.2.4" / "recipe.yaml").read_text(encoding="utf-8")
            self.assertIn('version: "1.2.4"', new_recipe)
            self.assertIn("tag: v1_2_4", new_recipe)
            self.assertIn("build_number: 0", new_recipe)
            self.assertIn(f"sha256: {'a' * 64}", new_recipe)
            self.assertIn("v1_2_4.tar.gz", upstream.render_source_url(root / "foo" / "1.2.4" / "recipe.yaml"))
            self.assertNotIn('version: "1.2.3"', new_recipe)
            self.assertNotIn("tag: v1_2_3", new_recipe)
            self.assertNotIn("build_number: 9", new_recipe)
            self.assertNotIn("sha256: " + "0" * 64, new_recipe)

            pixi = (root / "foo" / "1.2.4" / "pixi.toml").read_text(encoding="utf-8")
            self.assertIn("build-foo-1-2-4", pixi)
            self.assertIn("1.2.4", pixi)
            self.assertNotIn("build-foo-1-2-3", pixi)
            self.assertNotIn("1.2.3", pixi)

            readme = (root / "README.md").read_text(encoding="utf-8")
            self.assertIn("Recipe versions: `1.2.3`, `1.2.4`", readme)

    def test_readme_update_targets_package_heading_when_versions_are_not_unique(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            root = Path(tmp_raw)
            for package in ["bar", "foo"]:
                recipe_dir = root / package / "1.2.3"
                recipe_dir.mkdir(parents=True)
                (recipe_dir / "recipe.yaml").write_text(
                    f"""context:
  version: "1.2.3"

recipe:
  name: {package}
  version: ${{{{ version }}}}

source:
  url: https://github.com/example/{package}/archive/refs/tags/v${{{{ version }}}}.tar.gz
  sha256: {"0" * 64}

about:
  repository: https://github.com/example/{package}
""",
                    encoding="utf-8",
                )
            (root / "foo" / "1.2.4").mkdir()
            (root / "foo" / "1.2.4" / "recipe.yaml").write_text(
                (root / "foo" / "1.2.3" / "recipe.yaml").read_text(encoding="utf-8").replace("1.2.3", "1.2.4"),
                encoding="utf-8",
            )
            (root / "README.md").write_text(
                "# Packages\n\n## Bar\n\nRecipe versions: `1.2.3`\n\n## Foo\n\nRecipe versions: `1.2.3`\n",
                encoding="utf-8",
            )

            upstream.update_readme_versions(root, "foo", {"1.2.3"})

            self.assertEqual(
                (root / "README.md").read_text(encoding="utf-8"),
                "# Packages\n\n## Bar\n\nRecipe versions: `1.2.3`\n\n## Foo\n\nRecipe versions: `1.2.3`, `1.2.4`\n",
            )

    def test_workflow_creates_per_recipe_prs_and_dispatches_test_label_builds_by_default(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "check-upstream-releases.yml").read_text(encoding="utf-8")
        fanout_step = re.search(
            r"(?ms)^      - name: Create per-recipe pull requests and dispatch builds\n(?P<body>.*?)(?=^      - name: |\Z)",
            workflow,
        )
        self.assertIsNotNone(fanout_step)
        assert fanout_step is not None
        match = re.search(r"(?ms)^      publish_target:\n(?P<body>(?:        .*\n)+)", workflow)
        self.assertIsNotNone(match)
        assert match is not None
        publish_target_input = match.group("body")
        fanout = fanout_step.group("body")
        script = (ROOT / "scripts" / "create_upstream_release_prs.sh").read_text(encoding="utf-8")

        self.assertIn("AUTOMATION_BRANCH_PREFIX: automation/upstream-release-prs", workflow)
        self.assertIn("BASE_BRANCH: ${{ github.event.repository.default_branch }}", workflow)
        self.assertIn("RESULT_JSON: ${{ runner.temp }}/upstream-releases.json", fanout)
        self.assertIn("PR_GH_TOKEN: ${{ secrets.UPSTREAM_RELEASE_PR_TOKEN || github.token }}", fanout)
        self.assertIn("ACTIONS_GH_TOKEN: ${{ github.token }}", fanout)
        self.assertIn("DISPATCH_BUILD: ${{ github.event_name == 'schedule' || inputs.dispatch_build }}", fanout)
        self.assertIn("run: scripts/create_upstream_release_prs.sh", fanout)
        self.assertNotIn("steps.pr.outputs.number", workflow)
        self.assertNotIn("RECIPES: ${{ steps.detect.outputs.recipes }}", workflow)

        self.assertIn('branch="$branch_prefix/$recipe"', script)
        self.assertIn('git commit -m "Add $recipe upstream release recipe"', script)
        self.assertIn('AUTOMATION_BRANCH="$branch"', script)
        self.assertIn('RECIPE="$recipe"', script)
        self.assertIn('gh workflow run build-packages.yml', script)
        self.assertIn('--ref "$branch"', script)
        self.assertIn('-f recipes="$recipe"', script)
        self.assertIn('if [[ "$publish_target" == "default-label" ]]; then', script)
        self.assertIn("Nightly upstream release checks may not dispatch default-label publishes.", script)

        self.assertIn("- artifact-only", publish_target_input)
        self.assertIn("- test-label", publish_target_input)
        self.assertIn("default: test-label", publish_target_input)
        self.assertNotIn("- default-label", publish_target_input)

    def test_create_upstream_release_prs_script_fans_out_one_branch_pr_and_build_per_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            work = tmp / "work"
            work.mkdir()
            scripts = work / "scripts"
            scripts.mkdir()
            for name in ["check_upstream_releases.py", "open_upstream_release_pr.sh", "create_upstream_release_prs.sh"]:
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
                (scripts / name).chmod(0o755)

            (work / "foo" / "1.2.3").mkdir(parents=True)
            (work / "foo" / "1.2.3" / "recipe.yaml").write_text(
                "context:\n  version: \"1.2.3\"\n\nrecipe:\n  name: foo\n  version: ${{ version }}\n\nabout:\n  repository: https://github.com/example/foo\n",
                encoding="utf-8",
            )
            (work / "foo" / "1.2.4").mkdir(parents=True)
            (work / "foo" / "1.2.4" / "recipe.yaml").write_text(
                "context:\n  version: \"1.2.4\"\n\nrecipe:\n  name: foo\n  version: ${{ version }}\n\nabout:\n  repository: https://github.com/example/foo\n",
                encoding="utf-8",
            )
            (work / "README.md").write_text("# Packages\n\n## Foo\n\nRecipe versions: `1.2.3`\n", encoding="utf-8")
            result_json = tmp / "upstream-releases.json"
            result_json.write_text(
                '{"created":[{"package":"foo","version":"1.2.4","recipe":"foo/1.2.4","copied_from":"foo/1.2.3","upstream_tag":"v1.2.4","source_sha256":"abc"}]}\n',
                encoding="utf-8",
            )

            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            git_log = tmp / "git.log"
            gh_log = tmp / "gh.log"
            gh_state = tmp / "gh-created"
            fake_git = bin_dir / "git"
            fake_git.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'printf "%s\\n" "$*" >> "$GIT_LOG"\n'
                'if [[ "$1" == "ls-remote" ]]; then exit 2; fi\n'
                'if [[ "$1" == "clean" ]]; then rm -rf foo/1.2.4; exit 0; fi\n'
                'if [[ "$1 $2" == "diff --cached" ]]; then exit 1; fi\n'
                'exit 0\n',
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            fake_gh = bin_dir / "gh"
            fake_gh.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'printf "%s\\n" "$*" >> "$GH_LOG"\n'
                'if [[ "$1 $2" == "pr list" ]]; then [[ -f "$GH_STATE" ]] && echo 7; exit 0; fi\n'
                'if [[ "$1 $2" == "pr create" ]]; then touch "$GH_STATE"; exit 0; fi\n'
                'if [[ "$1 $2" == "workflow run" ]]; then exit 0; fi\n'
                'echo unexpected gh command: $* >&2\n'
                'exit 2\n',
                encoding="utf-8",
            )
            fake_gh.chmod(0o755)
            summary = tmp / "summary.md"
            output = tmp / "output.txt"
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "RESULT_JSON": str(result_json),
                "RUNNER_TEMP": str(tmp),
                "GITHUB_STEP_SUMMARY": str(summary),
                "GITHUB_OUTPUT": str(output),
                "GITHUB_SERVER_URL": "https://github.com",
                "GITHUB_REPOSITORY": "anders/aswf-pixi",
                "GIT_LOG": str(git_log),
                "GH_LOG": str(gh_log),
                "GH_STATE": str(gh_state),
                "PR_GH_TOKEN": "pr-token",
                "ACTIONS_GH_TOKEN": "actions-token",
                "BASE_BRANCH": "main",
                "AUTOMATION_BRANCH_PREFIX": "automation/upstream-release-prs",
                "PLATFORMS": "default",
                "PUBLISH_TARGET": "test-label",
                "RUN_SMOKE_TESTS": "true",
                "DISPATCH_BUILD": "true",
            }

            subprocess.run(
                [str(scripts / "create_upstream_release_prs.sh")],
                cwd=work,
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertIn("Recipe versions: `1.2.3`, `1.2.4`", (work / "README.md").read_text(encoding="utf-8"))
            git_text = git_log.read_text(encoding="utf-8")
            self.assertIn("checkout -B automation/upstream-release-prs/foo/1.2.4 origin/main", git_text)
            self.assertIn("commit -m Add foo/1.2.4 upstream release recipe", git_text)
            self.assertIn("push --force-with-lease origin automation/upstream-release-prs/foo/1.2.4", git_text)
            gh_text = gh_log.read_text(encoding="utf-8")
            self.assertIn("pr create --head automation/upstream-release-prs/foo/1.2.4 --base main --title Add foo/1.2.4 upstream release recipe", gh_text)
            self.assertIn("workflow run build-packages.yml --ref automation/upstream-release-prs/foo/1.2.4 -f recipes=foo/1.2.4", gh_text)
            self.assertIn("-f publish_target=test-label", gh_text)
            self.assertIn("-f run_smoke_tests=true", gh_text)

    def test_create_upstream_release_prs_script_preserves_existing_pr_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            work = tmp / "work"
            work.mkdir()
            scripts = work / "scripts"
            scripts.mkdir()
            for name in ["check_upstream_releases.py", "open_upstream_release_pr.sh", "create_upstream_release_prs.sh"]:
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
                (scripts / name).chmod(0o755)

            (work / "foo" / "1.2.4").mkdir(parents=True)
            (work / "foo" / "1.2.4" / "recipe.yaml").write_text("recipe:\n  name: foo\n", encoding="utf-8")
            (work / "README.md").write_text("# Packages\n", encoding="utf-8")
            result_json = tmp / "upstream-releases.json"
            result_json.write_text(
                '{"created":[{"package":"foo","version":"1.2.4","recipe":"foo/1.2.4","copied_from":"foo/1.2.3","upstream_tag":"v1.2.4","source_sha256":"abc"}]}\n',
                encoding="utf-8",
            )

            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            git_log = tmp / "git.log"
            gh_log = tmp / "gh.log"
            fake_git = bin_dir / "git"
            fake_git.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'printf "%s\\n" "$*" >> "$GIT_LOG"\n'
                'if [[ "$1" == "checkout" || "$1" == "commit" || "$1" == "push" ]]; then echo branch should not be overwritten >&2; exit 2; fi\n'
                'exit 0\n',
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            fake_gh = bin_dir / "gh"
            fake_gh.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'printf "%s\\n" "$*" >> "$GH_LOG"\n'
                'if [[ "$1 $2" == "pr list" ]]; then echo 7; exit 0; fi\n'
                'if [[ "$1 $2" == "pr edit" ]]; then exit 0; fi\n'
                'if [[ "$1 $2" == "workflow run" ]]; then exit 0; fi\n'
                'echo unexpected gh command: $* >&2\n'
                'exit 2\n',
                encoding="utf-8",
            )
            fake_gh.chmod(0o755)
            summary = tmp / "summary.md"
            output = tmp / "output.txt"
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "RESULT_JSON": str(result_json),
                "RUNNER_TEMP": str(tmp),
                "GITHUB_STEP_SUMMARY": str(summary),
                "GITHUB_OUTPUT": str(output),
                "GITHUB_SERVER_URL": "https://github.com",
                "GITHUB_REPOSITORY": "anders/aswf-pixi",
                "GIT_LOG": str(git_log),
                "GH_LOG": str(gh_log),
                "BASE_BRANCH": "main",
                "AUTOMATION_BRANCH_PREFIX": "automation/upstream-release-prs",
                "PLATFORMS": "default",
                "PUBLISH_TARGET": "test-label",
                "RUN_SMOKE_TESTS": "true",
                "DISPATCH_BUILD": "true",
            }

            subprocess.run(
                [str(scripts / "create_upstream_release_prs.sh")],
                cwd=work,
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotIn("checkout -B automation/upstream-release-prs/foo/1.2.4", git_log.read_text(encoding="utf-8"))
            gh_text = gh_log.read_text(encoding="utf-8")
            self.assertIn("pr edit 7 --title Add foo/1.2.4 upstream release recipe", gh_text)
            self.assertIn("workflow run build-packages.yml --ref automation/upstream-release-prs/foo/1.2.4 -f recipes=foo/1.2.4", gh_text)
            self.assertIn("not overwriting branch contents", summary.read_text(encoding="utf-8"))

    def test_create_upstream_release_prs_script_preserves_existing_remote_branch_without_pr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            work = tmp / "work"
            work.mkdir()
            scripts = work / "scripts"
            scripts.mkdir()
            for name in ["check_upstream_releases.py", "open_upstream_release_pr.sh", "create_upstream_release_prs.sh"]:
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
                (scripts / name).chmod(0o755)

            (work / "foo" / "1.2.4").mkdir(parents=True)
            (work / "foo" / "1.2.4" / "recipe.yaml").write_text("recipe:\n  name: foo\n", encoding="utf-8")
            (work / "README.md").write_text("# Packages\n", encoding="utf-8")
            result_json = tmp / "upstream-releases.json"
            result_json.write_text(
                '{"created":[{"package":"foo","version":"1.2.4","recipe":"foo/1.2.4","copied_from":"foo/1.2.3","upstream_tag":"v1.2.4","source_sha256":"abc"}]}\n',
                encoding="utf-8",
            )

            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            git_log = tmp / "git.log"
            gh_log = tmp / "gh.log"
            gh_created = tmp / "gh-created"
            fake_git = bin_dir / "git"
            fake_git.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'printf "%s\\n" "$*" >> "$GIT_LOG"\n'
                'if [[ "$1" == "checkout" || "$1" == "commit" || "$1" == "push" ]]; then echo branch should not be overwritten >&2; exit 2; fi\n'
                'exit 0\n',
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            fake_gh = bin_dir / "gh"
            fake_gh.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'printf "%s\\n" "$*" >> "$GH_LOG"\n'
                'if [[ "$1 $2" == "pr list" ]]; then [[ -f "$GH_CREATED" ]] && echo 9; exit 0; fi\n'
                'if [[ "$1 $2" == "pr create" ]]; then touch "$GH_CREATED"; exit 0; fi\n'
                'if [[ "$1 $2" == "workflow run" ]]; then exit 0; fi\n'
                'echo unexpected gh command: $* >&2\n'
                'exit 2\n',
                encoding="utf-8",
            )
            fake_gh.chmod(0o755)
            summary = tmp / "summary.md"
            output = tmp / "output.txt"
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "RESULT_JSON": str(result_json),
                "RUNNER_TEMP": str(tmp),
                "GITHUB_STEP_SUMMARY": str(summary),
                "GITHUB_OUTPUT": str(output),
                "GITHUB_SERVER_URL": "https://github.com",
                "GITHUB_REPOSITORY": "anders/aswf-pixi",
                "GIT_LOG": str(git_log),
                "GH_LOG": str(gh_log),
                "GH_CREATED": str(gh_created),
                "BASE_BRANCH": "main",
                "AUTOMATION_BRANCH_PREFIX": "automation/upstream-release-prs",
                "PLATFORMS": "default",
                "PUBLISH_TARGET": "test-label",
                "RUN_SMOKE_TESTS": "true",
                "DISPATCH_BUILD": "true",
            }

            subprocess.run(
                [str(scripts / "create_upstream_release_prs.sh")],
                cwd=work,
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            git_text = git_log.read_text(encoding="utf-8")
            self.assertIn("ls-remote --exit-code --heads origin automation/upstream-release-prs/foo/1.2.4", git_text)
            self.assertNotIn("checkout -B automation/upstream-release-prs/foo/1.2.4", git_text)
            gh_text = gh_log.read_text(encoding="utf-8")
            self.assertIn("pr create --head automation/upstream-release-prs/foo/1.2.4 --base main --title Add foo/1.2.4 upstream release recipe", gh_text)
            self.assertIn("workflow run build-packages.yml --ref automation/upstream-release-prs/foo/1.2.4 -f recipes=foo/1.2.4", gh_text)
            self.assertIn("without an open PR; not overwriting branch contents", summary.read_text(encoding="utf-8"))

    def test_open_upstream_release_pr_script_tolerates_pr_creation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            fake_gh = bin_dir / "gh"
            fake_gh.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [[ \"$1 $2\" == \"pr list\" ]]; then exit 0; fi\n"
                "if [[ \"$1 $2\" == \"pr create\" ]]; then echo 'blocked' >&2; exit 1; fi\n"
                "echo unexpected gh command: $* >&2\n"
                "exit 2\n",
                encoding="utf-8",
            )
            fake_gh.chmod(0o755)
            report = tmp / "report.md"
            report.write_text("- `foo/1.2.4`\n", encoding="utf-8")
            output = tmp / "output.txt"
            summary = tmp / "summary.md"

            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "RUNNER_TEMP": str(tmp),
                "REPORT": str(report),
                "AUTOMATION_BRANCH": "automation/upstream-release-prs/foo/1.2.4",
                "BASE_BRANCH": "main",
                "RECIPE": "foo/1.2.4",
                "GITHUB_REF_NAME": "main",
                "GITHUB_SERVER_URL": "https://github.com",
                "GITHUB_REPOSITORY": "anders/aswf-pixi",
                "GITHUB_OUTPUT": str(output),
                "GITHUB_STEP_SUMMARY": str(summary),
            }

            completed = subprocess.run(
                [str(ROOT / "scripts" / "open_upstream_release_pr.sh")],
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertIn("Could not create upstream release PR", completed.stdout)
            self.assertEqual(output.read_text(encoding="utf-8"), "number=\n")
            self.assertIn(
                "Manual PR URL: https://github.com/anders/aswf-pixi/compare/main...automation/upstream-release-prs/foo/1.2.4?expand=1",
                summary.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
