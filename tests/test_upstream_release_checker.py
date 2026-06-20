from __future__ import annotations

from pathlib import Path
import re
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

    def test_workflow_dispatches_existing_build_workflow_on_test_label_by_default(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "check-upstream-releases.yml").read_text(encoding="utf-8")
        match = re.search(r"(?ms)^      publish_target:\n(?P<body>(?:        .*\n)+)", workflow)
        self.assertIsNotNone(match)
        assert match is not None
        publish_target_input = match.group("body")

        self.assertIn("gh workflow run build-packages.yml", workflow)
        self.assertIn('--ref "$AUTOMATION_BRANCH"', workflow)
        self.assertIn('publish_target="${PUBLISH_TARGET:-test-label}"', workflow)
        self.assertIn("- artifact-only", publish_target_input)
        self.assertIn("- test-label", publish_target_input)
        self.assertIn("default: test-label", publish_target_input)
        self.assertNotIn("- default-label", publish_target_input)
        self.assertIn('if [[ "$publish_target" == "default-label" ]]; then', workflow)
        self.assertIn("Nightly upstream release checks may not dispatch default-label publishes.", workflow)


if __name__ == "__main__":
    unittest.main()
