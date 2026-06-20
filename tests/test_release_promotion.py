from __future__ import annotations

from pathlib import Path
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
        self.assertIn("github.event.pull_request.head.ref == 'automation/upstream-releases'", workflow)
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


if __name__ == "__main__":
    unittest.main()
