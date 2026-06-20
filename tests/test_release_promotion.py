from __future__ import annotations

from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import changed_recipes


class ChangedRecipeTests(unittest.TestCase):
    def make_recipe(self, root: Path, selector: str) -> None:
        recipe = root / selector
        recipe.mkdir(parents=True)
        (recipe / "recipe.yaml").write_text("recipe:\n  name: test\n", encoding="utf-8")

    def test_changed_recipe_selectors_filters_and_deduplicates_recipe_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            root = Path(tmp_raw)
            self.make_recipe(root, "foo/1.2.3")
            self.make_recipe(root, "bar/2.0.0")

            self.assertEqual(
                changed_recipes.changed_recipe_selectors(
                    [
                        "README.md",
                        "foo/1.2.3/recipe.yaml",
                        "foo/1.2.3/tests/consumer.cpp",
                        "bar/2.0.0/pixi.toml",
                        "baz/9.9.9/recipe.yaml",
                        "../outside/1.0.0/recipe.yaml",
                    ],
                    root,
                ),
                ["foo/1.2.3", "bar/2.0.0"],
            )

    def test_changed_recipes_cli_reads_stdin_and_prints_comma_separated_selectors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            root = Path(tmp_raw)
            self.make_recipe(root, "foo/1.2.3")
            self.make_recipe(root, "bar/2.0.0")

            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "changed_recipes.py"), "--root", str(root)],
                input="foo/1.2.3/recipe.yaml\nbar/2.0.0/pixi.toml\nREADME.md\n",
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(completed.stdout, "foo/1.2.3,bar/2.0.0\n")

    def test_promote_workflow_dispatches_default_label_for_merged_automation_prs(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "promote-upstream-releases.yml").read_text(encoding="utf-8")

        self.assertIn("pull_request:", workflow)
        self.assertIn("closed", workflow)
        self.assertIn("github.event.pull_request.merged == true", workflow)
        self.assertIn("github.event.pull_request.base.ref == 'main'", workflow)
        self.assertIn("startsWith(github.event.pull_request.head.ref, 'automation/upstream-release-prs/')", workflow)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", workflow)
        self.assertIn("ref: ${{ github.event.pull_request.merge_commit_sha }}", workflow)
        self.assertIn("PROMOTION_REF: automation/promote-upstream-releases/pr-${{ github.event.pull_request.number }}", workflow)
        self.assertIn('git push --force-with-lease origin "HEAD:refs/heads/$PROMOTION_REF"', workflow)
        self.assertIn("RECIPES: ${{ steps.recipes.outputs.recipes }}", workflow)
        self.assertIn("PROMOTION_REF: ${{ steps.promotion-ref.outputs.ref }}", workflow)
        self.assertIn("scripts/changed_recipes.py --root .", workflow)
        self.assertIn("gh workflow run build-packages.yml", workflow)
        self.assertIn('--ref "$PROMOTION_REF"', workflow)
        self.assertIn('-f recipes="$RECIPES"', workflow)
        self.assertIn('-f publish_target="default-label"', workflow)
        self.assertIn('-f run_smoke_tests="true"', workflow)

    def test_default_label_builds_still_use_production_environment_gate(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "build-packages.yml").read_text(encoding="utf-8")
        match = re.search(r"(?ms)^  publish:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\Z)", workflow)
        self.assertIsNotNone(match)
        assert match is not None

        self.assertIn(
            "environment: ${{ inputs.publish_target == 'default-label' && 'anaconda-production' || 'anaconda-test' }}",
            match.group("body"),
        )

    def test_merge_workflow_merges_successful_test_label_automation_builds(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "merge-upstream-release-pr.yml").read_text(encoding="utf-8")
        build_workflow = (ROOT / ".github" / "workflows" / "build-packages.yml").read_text(encoding="utf-8")

        self.assertIn("workflow_run:", workflow)
        self.assertIn("- Build packages", workflow)
        self.assertIn("- completed", workflow)
        self.assertIn("actions: read", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("pull-requests: write", workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("github.event.workflow_run.event == 'workflow_dispatch'", workflow)
        self.assertIn("startsWith(github.event.workflow_run.head_branch, 'automation/upstream-release-prs/')", workflow)
        self.assertIn("AUTOMATION_BRANCH: ${{ github.event.workflow_run.head_branch }}", workflow)
        self.assertIn("AUTOMATION_BRANCH_PREFIX: automation/upstream-release-prs", workflow)
        self.assertIn("RUN_DISPLAY_TITLE: ${{ github.event.workflow_run.display_title }}", workflow)
        self.assertIn("RUN_HEAD_SHA: ${{ github.event.workflow_run.head_sha }}", workflow)
        self.assertIn("uses: actions/checkout@v6", workflow)
        self.assertIn("run: bash scripts/merge_upstream_release_pr.sh", workflow)
        merge_script = (ROOT / "scripts" / "merge_upstream_release_pr.sh").read_text(encoding="utf-8")
        self.assertIn("gh api --paginate", merge_script)
        self.assertIn("pulls/$pr_number/files", merge_script)
        self.assertIn("README.md", merge_script)
        self.assertIn("smoke=${{ inputs.run_smoke_tests }}", build_workflow)

    def test_merge_upstream_release_pr_script_merges_matching_tested_pr_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            calls = tmp / "gh-calls.txt"
            fake_gh = bin_dir / "gh"
            fake_gh.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'printf "%s\\n" "$*" >> "$GH_CALLS"\n'
                'if [[ "$1 $2" == "pr list" && "$*" == *"--head automation/upstream-release-prs/foo/1.2.4"* && "$*" == *"--base main"* && "$*" == *"--state open"* && "$*" == *"--json number,headRefOid"* && "$*" == *".[0].number"* ]]; then echo 42; exit 0; fi\n'
                'if [[ "$1 $2" == "pr list" && "$*" == *"--head automation/upstream-release-prs/foo/1.2.4"* && "$*" == *"--base main"* && "$*" == *"--state open"* && "$*" == *"--json number,headRefOid"* && "$*" == *".[0].headRefOid"* ]]; then echo abc123; exit 0; fi\n'
                'if [[ "$1 $2" == "api --paginate" && "$*" == *"repos/anders/aswf-pixi/pulls/42/files"* && "$*" == *".[].filename"* ]]; then printf "%s\\n" foo/1.2.4/recipe.yaml README.md; exit 0; fi\n'
                'if [[ "$1 $2" == "pr merge" ]]; then exit 0; fi\n'
                'echo unexpected gh command: $* >&2\n'
                'exit 2\n',
                encoding="utf-8",
            )
            fake_gh.chmod(0o755)
            summary = tmp / "summary.md"
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "GH_CALLS": str(calls),
                "AUTOMATION_BRANCH": "automation/upstream-release-prs/foo/1.2.4",
                "AUTOMATION_BRANCH_PREFIX": "automation/upstream-release-prs",
                "BASE_BRANCH": "main",
                "RUN_DISPLAY_TITLE": "Build foo/1.2.4 (default, test-label, smoke=true)",
                "RUN_HEAD_SHA": "abc123",
                "RUN_HTML_URL": "https://github.com/anders/aswf-pixi/actions/runs/123",
                "GITHUB_REPOSITORY": "anders/aswf-pixi",
                "GITHUB_STEP_SUMMARY": str(summary),
            }

            subprocess.run(
                ["bash", str(ROOT / "scripts" / "merge_upstream_release_pr.sh")],
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            calls_text = calls.read_text(encoding="utf-8")
            self.assertIn(
                "pr merge 42 --squash --delete-branch --subject Add foo/1.2.4 upstream release recipe --body Automerged after the test-label build, publish, and smoke workflow succeeded: https://github.com/anders/aswf-pixi/actions/runs/123 --match-head-commit abc123\n",
                calls_text,
            )
            self.assertIn("Merged upstream release PR #42 for foo/1.2.4", summary.read_text(encoding="utf-8"))

    def test_merge_upstream_release_pr_script_skips_wrong_recipe_or_without_smoke(self) -> None:
        cases = [
            "Build bar/1.2.4 (default, test-label, smoke=true)",
            "Build foo/1.2.4 (default, test-label, smoke=false)",
            "Build foo/1.2.4 (default, artifact-only, smoke=true)",
        ]
        for title in cases:
            with self.subTest(title=title):
                with tempfile.TemporaryDirectory() as tmp_raw:
                    tmp = Path(tmp_raw)
                    bin_dir = tmp / "bin"
                    bin_dir.mkdir()
                    fake_gh = bin_dir / "gh"
                    fake_gh.write_text(
                        '#!/usr/bin/env bash\n'
                        'echo gh should not be called >&2\n'
                        'exit 2\n',
                        encoding="utf-8",
                    )
                    fake_gh.chmod(0o755)
                    summary = tmp / "summary.md"
                    env = {
                        **os.environ,
                        "PATH": f"{bin_dir}:{os.environ['PATH']}",
                        "AUTOMATION_BRANCH": "automation/upstream-release-prs/foo/1.2.4",
                        "RUN_DISPLAY_TITLE": title,
                        "GITHUB_STEP_SUMMARY": str(summary),
                    }

                    subprocess.run(
                        ["bash", str(ROOT / "scripts" / "merge_upstream_release_pr.sh")],
                        env=env,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )

                    self.assertIn("not a smoke-tested test-label build", summary.read_text(encoding="utf-8"))


    def test_merge_upstream_release_pr_script_rejects_extra_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            calls = tmp / "gh-calls.txt"
            fake_gh = bin_dir / "gh"
            fake_gh.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'printf "%s\\n" "$*" >> "$GH_CALLS"\n'
                'if [[ "$1 $2" == "pr list" && "$*" == *".[0].number"* ]]; then echo 42; exit 0; fi\n'
                'if [[ "$1 $2" == "pr list" && "$*" == *".[0].headRefOid"* ]]; then echo abc123; exit 0; fi\n'
                'if [[ "$1 $2" == "api --paginate" ]]; then printf "%s\\n" foo/1.2.4/recipe.yaml README.md .github/workflows/build-packages.yml bar/9.9.9/recipe.yaml; exit 0; fi\n'
                'if [[ "$1 $2" == "pr merge" ]]; then echo invalid files were merged >&2; exit 2; fi\n'
                'echo unexpected gh command: $* >&2\n'
                'exit 2\n',
                encoding="utf-8",
            )
            fake_gh.chmod(0o755)
            summary = tmp / "summary.md"
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "GH_CALLS": str(calls),
                "AUTOMATION_BRANCH": "automation/upstream-release-prs/foo/1.2.4",
                "BASE_BRANCH": "main",
                "RUN_DISPLAY_TITLE": "Build foo/1.2.4 (default, test-label, smoke=true)",
                "RUN_HEAD_SHA": "abc123",
                "GITHUB_REPOSITORY": "anders/aswf-pixi",
                "GITHUB_STEP_SUMMARY": str(summary),
            }

            subprocess.run(
                ["bash", str(ROOT / "scripts" / "merge_upstream_release_pr.sh")],
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotIn("pr merge", calls.read_text(encoding="utf-8"))
            summary_text = summary.read_text(encoding="utf-8")
            self.assertIn("includes files outside foo/1.2.4 and README.md", summary_text)
            self.assertIn(".github/workflows/build-packages.yml", summary_text)
            self.assertIn("bar/9.9.9/recipe.yaml", summary_text)

    def test_merge_upstream_release_pr_script_skips_stale_pr_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            calls = tmp / "gh-calls.txt"
            fake_gh = bin_dir / "gh"
            fake_gh.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'printf "%s\\n" "$*" >> "$GH_CALLS"\n'
                'if [[ "$1 $2" == "pr list" && "$*" == *".[0].number"* ]]; then echo 42; exit 0; fi\n'
                'if [[ "$1 $2" == "pr list" && "$*" == *".[0].headRefOid"* ]]; then echo newer456; exit 0; fi\n'
                'if [[ "$1 $2" == "pr merge" ]]; then echo stale head was merged >&2; exit 2; fi\n'
                'echo unexpected gh command: $* >&2\n'
                'exit 2\n',
                encoding="utf-8",
            )
            fake_gh.chmod(0o755)
            summary = tmp / "summary.md"
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "GH_CALLS": str(calls),
                "AUTOMATION_BRANCH": "automation/upstream-release-prs/foo/1.2.4",
                "BASE_BRANCH": "main",
                "RUN_DISPLAY_TITLE": "Build foo/1.2.4 (default, test-label, smoke=true)",
                "RUN_HEAD_SHA": "abc123",
                "GITHUB_STEP_SUMMARY": str(summary),
            }

            subprocess.run(
                ["bash", str(ROOT / "scripts" / "merge_upstream_release_pr.sh")],
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotIn("pr merge", calls.read_text(encoding="utf-8"))
            self.assertIn("successful build tested abc123", summary.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
