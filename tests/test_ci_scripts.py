from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ci_matrix
import publish_packages
import resolve_build_numbers
import smoke_consumers


class CiMatrixTests(unittest.TestCase):
    def test_parse_recipes_expands_package_wildcard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            for version in ["1.0.0", "1.1.0"]:
                recipe = tmp / "foo" / version
                recipe.mkdir(parents=True)
                (recipe / "recipe.yaml").write_text(f"recipe:\n  name: foo\n  version: {version}\n", encoding="utf-8")
            (tmp / "foo" / "notes").mkdir()

            cwd = Path.cwd()
            try:
                os.chdir(tmp)
                self.assertEqual(
                    ci_matrix.parse_recipes("foo/*"),
                    [Path("foo/1.0.0"), Path("foo/1.1.0")],
                )
            finally:
                os.chdir(cwd)

    def test_parse_recipes_expands_bare_package_selector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            for version in ["1.0.0", "1.1.0"]:
                recipe = tmp / "foo" / version
                recipe.mkdir(parents=True)
                (recipe / "recipe.yaml").write_text(f"recipe:\n  name: foo\n  version: {version}\n", encoding="utf-8")
            (tmp / "foo" / "notes").mkdir()

            cwd = Path.cwd()
            try:
                os.chdir(tmp)
                self.assertEqual(
                    ci_matrix.parse_recipes("foo"),
                    [Path("foo/1.0.0"), Path("foo/1.1.0")],
                )
            finally:
                os.chdir(cwd)

    def test_parse_recipes_rejects_unsupported_wildcard_shape(self) -> None:
        with self.assertRaisesRegex(SystemExit, r"must look like package/\*"):
            ci_matrix.parse_recipes("foo/1.*")

    def test_parse_recipes_rejects_bare_package_without_version_recipes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            (tmp / "foo" / "notes").mkdir(parents=True)

            cwd = Path.cwd()
            try:
                os.chdir(tmp)
                with self.assertRaisesRegex(SystemExit, r"should look like package/version"):
                    ci_matrix.parse_recipes("foo")
            finally:
                os.chdir(cwd)

    def test_parse_recipes_rejects_deeper_explicit_recipe_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            recipe = tmp / "foo" / "1.0.0" / "extra"
            recipe.mkdir(parents=True)
            (recipe / "recipe.yaml").write_text("recipe:\n  name: foo\n  version: 1.0.0\n", encoding="utf-8")

            cwd = Path.cwd()
            try:
                os.chdir(tmp)
                with self.assertRaisesRegex(SystemExit, r"should look like package/version"):
                    ci_matrix.parse_recipes("foo/1.0.0/extra")
            finally:
                os.chdir(cwd)

    def test_ci_matrix_cli_expands_wildcard_recipe_selector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            for version in ["1.0.0", "1.1.0"]:
                recipe = tmp / "foo" / version
                recipe.mkdir(parents=True)
                (recipe / "recipe.yaml").write_text(f"recipe:\n  name: foo\n  version: {version}\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "ci_matrix.py"),
                    "--recipes",
                    "foo/*",
                    "--platforms",
                    "linux-64",
                    "--build-number",
                    "4",
                    "--publish-target",
                    "default-label",
                ],
                cwd=tmp,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            matrix = json.loads(completed.stdout)
            self.assertEqual(
                [item["recipe"] for item in matrix["include"]],
                ["foo/1.0.0", "foo/1.1.0"],
            )
            self.assertEqual([item["build_number"] for item in matrix["include"]], ["4", "4"])

    def test_ci_matrix_cli_expands_bare_package_recipe_selector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            for version in ["1.0.0", "1.1.0"]:
                recipe = tmp / "foo" / version
                recipe.mkdir(parents=True)
                (recipe / "recipe.yaml").write_text(f"recipe:\n  name: foo\n  version: {version}\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "ci_matrix.py"),
                    "--recipes",
                    "foo",
                    "--platforms",
                    "linux-64",
                    "--build-number",
                    "4",
                    "--publish-target",
                    "default-label",
                ],
                cwd=tmp,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            matrix = json.loads(completed.stdout)
            self.assertEqual(
                [item["recipe"] for item in matrix["include"]],
                ["foo/1.0.0", "foo/1.1.0"],
            )
            self.assertEqual([item["build_number"] for item in matrix["include"]], ["4", "4"])

    def test_ci_matrix_cli_expands_bare_package_with_resolved_build_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            for version in ["1.0.0", "1.1.0"]:
                recipe = tmp / "foo" / version
                recipe.mkdir(parents=True)
                (recipe / "recipe.yaml").write_text(f"recipe:\n  name: foo\n  version: {version}\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "ci_matrix.py"),
                    "--recipes",
                    "foo",
                    "--platforms",
                    "linux-64",
                    "--build-number",
                    "",
                    "--publish-target",
                    "default-label",
                    "--resolved-build-numbers",
                    '{"foo/1.0.0": "5", "foo/1.1.0": "6"}',
                ],
                cwd=tmp,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            matrix = json.loads(completed.stdout)
            self.assertEqual(
                [(item["recipe"], item["build_number"]) for item in matrix["include"]],
                [("foo/1.0.0", "5"), ("foo/1.1.0", "6")],
            )

    def test_build_packages_workflow_defaults_to_default_label(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "build-packages.yml").read_text(encoding="utf-8")
        self.assertIn("run-name: Build ${{ inputs.recipes }} (${{ inputs.platforms }}, ${{ inputs.publish_target }}, smoke=${{ inputs.run_smoke_tests }})", workflow)
        self.assertIn("name: Prepare ${{ inputs.recipes }} matrix", workflow)
        self.assertIn("name: ${{ inputs.publish_target == 'artifact-only' && format('Skip publish for {0} (artifact-only)', inputs.recipes) || format('Publish {0} to Anaconda ({1})', inputs.recipes, inputs.publish_target) }}", workflow)
        self.assertIn("name: Build ${{ matrix.recipe }} (${{ matrix.platform }}, ${{ matrix.partition }})", workflow)
        self.assertIn("name: Evaluate smoke for ${{ matrix.recipe }} (${{ matrix.platform }}, ${{ matrix.partition }}, ${{ inputs.publish_target }}, smoke=${{ inputs.run_smoke_tests }})", workflow)
        self.assertIn("VARIANT_ARGS: ${{ matrix.variant_args }}", workflow)
        build_step_match = re.search(r"(?ms)^      - name: Build package\n(?P<body>.*?)(?=^      - name: )", workflow)
        self.assertIsNotNone(build_step_match)
        assert build_step_match is not None
        build_step = build_step_match.group("body")
        pre_typhoon, typhoon_and_rest = build_step.split('if [[ "$RECIPE" == openusd-typhoon/* ]]; then', 1)
        typhoon_block, post_typhoon = typhoon_and_rest.split("\n          fi", 1)
        self.assertIn("https://conda.anaconda.org/anderslanglands", pre_typhoon)
        self.assertIn("conda-forge", pre_typhoon)
        self.assertIn("channel_priority=strict", pre_typhoon)
        self.assertNotIn("https://conda.anaconda.org/anderslanglands/label/test", pre_typhoon)
        self.assertNotIn("channel_priority=disabled", pre_typhoon)
        self.assertRegex(
            typhoon_block,
            r"(?s)https://conda\.anaconda\.org/anderslanglands/label/test.*"
            r"https://conda\.anaconda\.org/anderslanglands.*conda-forge",
        )
        self.assertIn("channel_priority=disabled", typhoon_block)
        self.assertIn('args+=(--channel "$channel")', post_typhoon)
        self.assertIn("args+=(--variant \"$variant_pair\")", workflow)
        match = re.search(r"(?ms)^      publish_target:\n(?P<body>(?:        .*\n)+)", workflow)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertIn("default: default-label", match.group("body"))
        self.assertNotIn("default: artifact-only", match.group("body"))

    def test_build_packages_workflow_concurrency_scopes_by_recipe(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "build-packages.yml").read_text(encoding="utf-8")
        match = re.search(r"(?m)^concurrency:\n(?P<body>(?:^  .*\n)+)", workflow)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(
            match.group("body"),
            "  group: package-build-publish-${{ inputs.recipes }}\n"
            "  cancel-in-progress: false\n"
            "  queue: max\n",
        )

    def test_matrix_carries_resolved_build_number(self) -> None:
        recipe = Path("foo/1.0.0")
        result = ci_matrix.matrix(
            [recipe],
            ["linux-64", "win-64"],
            {recipe.as_posix(): "3"},
        )

        self.assertEqual(
            [item["build_number"] for item in result["include"]],
            ["3", "3"],
        )

    def test_read_simple_variant_values_reads_quoted_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = Path(tmp_raw) / "openusd" / "26.05"
            recipe.mkdir(parents=True)
            (recipe / "variants.yaml").write_text(
                "python:\n  - \"3.10\"\n  - \"3.11\"\nopenusd_build_set:\n  - full\n",
                encoding="utf-8",
            )

            self.assertEqual(
                ci_matrix.read_simple_variant_values(recipe, "python"),
                ["3.10", "3.11"],
            )

    def test_openusd_matrix_splits_long_build_partitions(self) -> None:
        recipe = Path("openusd/26.05")
        result = ci_matrix.matrix(
            [recipe],
            ["linux-64"],
            {recipe.as_posix(): "4"},
        )

        self.assertEqual(len(result["include"]), 11)
        self.assertEqual(
            [item["partition"] for item in result["include"]],
            [
                "minimal-cpp",
                "minimal-python-py310",
                "minimal-python-py311",
                "minimal-python-py312",
                "minimal-python-py313",
                "minimal-python-py314",
                "full-py310",
                "full-py311",
                "full-py312",
                "full-py313",
                "full-py314",
            ],
        )
        self.assertEqual(result["include"][0]["variant_args"], "openusd_build_set=minimal-cpp")
        self.assertEqual(
            result["include"][3]["variant_args"],
            "openusd_build_set=minimal-python python=3.12",
        )
        self.assertEqual(
            result["include"][-1]["variant_args"],
            "openusd_build_set=full python=3.14",
        )
        self.assertEqual(
            result["include"][-1]["artifact"],
            "openusd-26.05-linux-64-full-py314",
        )

    def test_openusd_typhoon_matrix_splits_python_variants(self) -> None:
        recipe = Path("openusd-typhoon/26.05.8.4bdd4b656")
        result = ci_matrix.matrix(
            [recipe],
            ["linux-64"],
            {recipe.as_posix(): "2"},
        )

        self.assertEqual(
            [
                (item["partition"], item["variant_args"], item["artifact"])
                for item in result["include"]
            ],
            [
                (
                    "py310",
                    "python=3.10",
                    "openusd-typhoon-26.05.8.4bdd4b656-linux-64-py310",
                ),
                (
                    "py311",
                    "python=3.11",
                    "openusd-typhoon-26.05.8.4bdd4b656-linux-64-py311",
                ),
                (
                    "py312",
                    "python=3.12",
                    "openusd-typhoon-26.05.8.4bdd4b656-linux-64-py312",
                ),
                (
                    "py313",
                    "python=3.13",
                    "openusd-typhoon-26.05.8.4bdd4b656-linux-64-py313",
                ),
                (
                    "py314",
                    "python=3.14",
                    "openusd-typhoon-26.05.8.4bdd4b656-linux-64-py314",
                ),
            ],
        )

    def test_openusd_typhoon_root_build_task_uses_relaxed_test_label_channels(self) -> None:
        manifest = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
        tasks = manifest["tasks"]

        self.assertNotIn("build-openusd-typhoon-26-05-900b8ec", tasks)
        self.assertNotIn("build-openusd-typhoon-26-05-3be04db", tasks)
        self.assertNotIn("build-openusd-typhoon-26-05-0beaac8", tasks)
        self.assertNotIn("build-openusd-typhoon-26-05-a99d9b6", tasks)
        self.assertNotIn("build-openusd-typhoon-26-05-1-a99d9b6", tasks)
        self.assertNotIn("build-openusd-typhoon-26-05-2-05126acbb", tasks)
        self.assertNotIn("build-openusd-typhoon-26-05-3-48b9fba91", tasks)
        self.assertNotIn("build-openusd-typhoon-26-05-3-2aa94b0ab", tasks)
        self.assertNotIn("build-openusd-typhoon-26-05-4-6d9726091", tasks)
        self.assertNotIn("build-openusd-typhoon-26-05-5-6be07687d", tasks)
        self.assertNotIn("build-openusd-typhoon-26-05-6-72fa115c7", tasks)
        self.assertNotIn("build-openusd-typhoon-26-05-7-ebc59aadd", tasks)
        self.assertEqual(
            tasks["build-openusd-typhoon"],
            {"depends-on": ["build-openusd-typhoon-26-05-8-4bdd4b656"]},
        )
        build_task = tasks["build-openusd-typhoon-26-05-8-4bdd4b656"]
        self.assertIn("--recipe openusd-typhoon/26.05.8.4bdd4b656/recipe.yaml", build_task)
        self.assertIn("--channel https://conda.anaconda.org/anderslanglands/label/test", build_task)
        self.assertIn("--channel-priority disabled", build_task)

    def test_openusd_typhoon_consumer_manifest_uses_relaxed_test_label_channels(self) -> None:
        recipe_version = "26.05.8.4bdd4b656"
        manifest = tomllib.loads(
            (ROOT / "openusd-typhoon" / recipe_version / "pixi.toml").read_text(encoding="utf-8")
        )

        self.assertEqual(
            manifest["workspace"]["channels"],
            [
                "https://conda.anaconda.org/anderslanglands/label/test",
                "https://conda.anaconda.org/anderslanglands",
                "conda-forge",
            ],
        )
        self.assertEqual(manifest["workspace"]["channel-priority"], "disabled")
        self.assertEqual(manifest["dependencies"]["openusd-typhoon"], f"=={recipe_version}")

    def test_openusd_typhoon_recipe_is_test_label_only(self) -> None:
        recipe = ROOT / "openusd-typhoon" / "26.05.8.4bdd4b656"
        recipe_text = (recipe / "recipe.yaml").read_text(encoding="utf-8")

        version_match = re.search(r'(?m)^  version: "(?P<version>[^"]+)"$', recipe_text)
        upstream_rev_match = re.search(r"(?m)^  upstream_rev: (?P<rev>[0-9a-f]{40})$", recipe_text)
        self.assertIsNotNone(version_match)
        self.assertIsNotNone(upstream_rev_match)
        assert version_match is not None
        assert upstream_rev_match is not None
        self.assertEqual(version_match.group("version"), recipe.name)
        self.assertEqual(upstream_rev_match.group("rev"), "4bdd4b6561529720164f7d2f1e865382a797a38b")
        self.assertTrue(upstream_rev_match.group("rev").startswith(recipe.name.rsplit(".", 1)[-1]))

        self.assertEqual(ci_matrix.recipe_allowed_publish_targets(recipe), {"test-label"})
        self.assertEqual(resolve_build_numbers.recipe_package_names(recipe), ["openusd-typhoon"])
        self.assertIn("upstream_branch: typhoon-anders", recipe_text)
        self.assertIn("git: https://github.com/NVIDIA-Omniverse/OpenUSD.git", recipe_text)
        self.assertIn("recipe:\n  name: openusd-typhoon\n  version: ${{ version }}", recipe_text)
        self.assertIn("rev: ${{ upstream_rev }}", recipe_text)
        host_match = re.search(
            r"(?ms)requirements:\n      build:.*?      host:\n(?P<body>.*?)(?=\n\n  - package:\n      name: openusd-typhoon)",
            recipe_text,
        )
        run_match = re.search(
            r"(?ms)- package:\n      name: openusd-typhoon.*?requirements:\n      run:\n(?P<body>.*?)(?=\n      run_constraints:)",
            recipe_text,
        )
        self.assertIsNotNone(host_match)
        self.assertIsNotNone(run_match)
        assert host_match is not None
        assert run_match is not None
        for requirements in [host_match.group("body"), run_match.group("body")]:
            self.assertIn("        - embree 4.4.*", requirements)
            self.assertIn("        - openqmc-dev ==0.7.1", requirements)
            openimageio_requirements = [
                line.strip()
                for line in requirements.splitlines()
                if line.strip().startswith("- openimageio")
            ]
            self.assertEqual(openimageio_requirements, ["- openimageio-dev 2.5.*"])
            self.assertIn("        - pyopengl ==3.1.10", requirements)
            self.assertNotIn("numpy", requirements)
        self.assertIn("-DOpenQMC_ROOT=$PREFIX", recipe_text)
        self.assertIn("-DOpenQMC_ROOT=%LIBRARY_PREFIX_FWD%", recipe_text)
        self.assertNotIn("openusd_build_set", recipe_text)
        self.assertNotRegex(recipe_text, r"(?m)^      name: openusd$")
        self.assertNotRegex(recipe_text, r"name: openusd-minimal")

    def test_openusd_recipes_cap_high_parallelism_instead_of_failing(self) -> None:
        cases = [
            (ROOT / "openusd" / "26.05" / "recipe.yaml", 3),
            (ROOT / "openusd-typhoon" / "26.05.8.4bdd4b656" / "recipe.yaml", 1),
        ]

        for recipe, staging_builds in cases:
            recipe_text = recipe.read_text(encoding="utf-8")
            unix_snippets = re.findall(
                r'(?ms)^            detected_jobs=.*?^            echo "OpenUSD build parallelism: \$build_jobs"$',
                recipe_text,
            )
            self.assertEqual(len(unix_snippets), staging_builds)
            self.assertEqual(recipe_text.count('--parallel "$build_jobs"'), staging_builds)

            for index, raw_snippet in enumerate(unix_snippets):
                snippet = "\n".join(
                    line[12:] if line.startswith(" " * 12) else line
                    for line in raw_snippet.splitlines()
                )
                script = snippet + '\nprintf "RESULT=%s\\n" "$CMAKE_BUILD_PARALLEL_LEVEL"\n'
                for env_name in ["OPENUSD_BUILD_PARALLEL_LEVEL", "CMAKE_BUILD_PARALLEL_LEVEL"]:
                    with self.subTest(recipe=recipe.relative_to(ROOT).as_posix(), snippet=index, env=env_name):
                        env = dict(os.environ)
                        env.pop("OPENUSD_BUILD_PARALLEL_LEVEL", None)
                        env.pop("CMAKE_BUILD_PARALLEL_LEVEL", None)
                        env[env_name] = "64"
                        completed = subprocess.run(
                            ["bash", "-e", "-c", script],
                            env=env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                        )

                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        self.assertIn("OpenUSD build parallelism capped at 24 from '64'", completed.stdout)
                        self.assertIn("OpenUSD build parallelism: 24", completed.stdout)
                        self.assertIn("RESULT=24", completed.stdout)

            with self.subTest(recipe=recipe.relative_to(ROOT).as_posix(), platform="win"):
                self.assertNotIn("OpenUSD build parallelism must be between 1 and 24", recipe_text)
                self.assertEqual(recipe_text.count("setlocal EnableDelayedExpansion"), staging_builds)
                self.assertEqual(recipe_text.count("if !BUILD_JOBS! GTR 24 ("), staging_builds)
                self.assertEqual(recipe_text.count('set "BUILD_JOBS=24"'), staging_builds)
                self.assertEqual(recipe_text.count('set "CMAKE_BUILD_PARALLEL_LEVEL=!BUILD_JOBS!"'), staging_builds)
                self.assertEqual(recipe_text.count("--parallel !BUILD_JOBS!"), staging_builds)

    def test_recipe_publish_policy_allows_test_label_and_artifact_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = Path(tmp_raw) / "preview" / "1.0.0"
            recipe.mkdir(parents=True)
            (recipe / "recipe.yaml").write_text(
                """recipe:
  name: preview
  version: 1.0.0

extra:
  allowed_publish_targets: ["test-label"] # preview-only package
""",
                encoding="utf-8",
            )

            self.assertEqual(ci_matrix.recipe_allowed_publish_targets(recipe), {"test-label"})
            ci_matrix.validate_recipe_publish_target(recipe, "test-label")
            ci_matrix.validate_recipe_publish_target(recipe, "artifact-only")
            with self.assertRaisesRegex(SystemExit, "may only be published to test-label"):
                ci_matrix.validate_recipe_publish_target(recipe, "default-label")

    def test_recipe_publish_policy_rejects_unknown_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = Path(tmp_raw) / "preview" / "1.0.0"
            recipe.mkdir(parents=True)
            (recipe / "recipe.yaml").write_text(
                """recipe:
  name: preview
  version: 1.0.0

extra:
  allowed_publish_targets:
    - test-label
    - "staging-label" # unsupported target
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SystemExit, "unsupported allowed_publish_targets: staging-label"):
                ci_matrix.validate_recipe_publish_target(recipe, "test-label")

    def test_ci_matrix_cli_rejects_default_label_disallowed_by_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            recipe = tmp / "preview" / "1.0.0"
            recipe.mkdir(parents=True)
            (recipe / "recipe.yaml").write_text(
                """recipe:
  name: preview
  version: 1.0.0

extra:
  allowed_publish_targets:
    - test-label
""",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "ci_matrix.py"),
                    "--recipes",
                    "preview/1.0.0",
                    "--platforms",
                    "linux-64",
                    "--build-number",
                    "4",
                    "--publish-target",
                    "default-label",
                ],
                cwd=tmp,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "Recipe preview/1.0.0 may only be published to test-label; requested default-label.",
                completed.stderr,
            )

    def test_openusd_partition_variants_render_expected_outputs(self) -> None:
        rattler_build = shutil.which("rattler-build")
        if rattler_build is None:
            self.skipTest("rattler-build is not available on PATH")

        cases = [
            (["openusd_build_set=minimal-cpp"], ["openusd-minimal-lib", "openusd-minimal-dev", "openusd-minimal-tools"]),
            (["openusd_build_set=minimal-python", "python=3.12"], ["openusd-minimal-python"]),
            (["openusd_build_set=full", "python=3.12"], ["openusd"]),
        ]
        for variants, expected_names in cases:
            with self.subTest(variants=variants), tempfile.TemporaryDirectory() as tmp_raw:
                cmd = [
                    rattler_build,
                    "build",
                    "--recipe",
                    "openusd/26.05/recipe.yaml",
                    "--target-platform",
                    "linux-64",
                    "--channel",
                    "https://conda.anaconda.org/anderslanglands",
                    "--channel",
                    "conda-forge",
                    "--channel-priority",
                    "strict",
                    "--output-dir",
                    tmp_raw,
                    "--package-format",
                    "conda",
                    "--test",
                    "skip",
                    "--render-only",
                ]
                for variant in variants:
                    cmd.extend(["--variant", variant])

                completed = subprocess.run(
                    cmd,
                    cwd=ROOT,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                rendered_names = re.findall(r"Build variant: (.+?)-26\.05-", completed.stdout)

                self.assertEqual(rendered_names, expected_names)

    def test_resolved_build_numbers_must_cover_requested_recipes(self) -> None:
        with self.assertRaisesRegex(SystemExit, "Missing resolved build number"):
            ci_matrix.parse_resolved_build_numbers(
                '{"foo/1.0.0": "1"}',
                [Path("foo/1.0.0"), Path("bar/2.0.0")],
                "",
            )

    def test_ci_matrix_cli_accepts_empty_build_number_with_resolved_json(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/ci_matrix.py",
                "--recipes",
                "imath/3.2.2",
                "--platforms",
                "win-64",
                "--build-number",
                "",
                "--publish-target",
                "default-label",
                "--resolved-build-numbers",
                '{"imath/3.2.2": "4"}',
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )

        matrix = json.loads(completed.stdout)
        self.assertEqual(matrix["include"][0]["build_number"], "4")
        self.assertEqual(matrix["include"][0]["runner"], "windows-latest")


class ResolveBuildNumbersTests(unittest.TestCase):
    def make_recipe(self, root: Path) -> Path:
        recipe = root / "foo" / "1.0.0"
        recipe.mkdir(parents=True)
        (recipe / "recipe.yaml").write_text(
            """recipe:
  name: foo
  version: 1.0.0

outputs:
  - staging:
      name: foo-build
  - package:
      name: foo-lib
  - package:
      name: foo
""",
            encoding="utf-8",
        )
        return recipe

    def test_recipe_package_names_ignore_staging_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = self.make_recipe(Path(tmp_raw))
            self.assertEqual(
                resolve_build_numbers.recipe_package_names(recipe),
                ["foo-lib", "foo"],
            )

    def test_recipe_package_names_match_real_imath_recipe(self) -> None:
        self.assertEqual(
            resolve_build_numbers.recipe_package_names(ROOT / "imath" / "3.2.2"),
            ["imath-lib", "imath-dev", "imath"],
        )

    def test_recipe_package_names_read_top_level_package_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = Path(tmp_raw) / "app" / "1.0.0"
            recipe.mkdir(parents=True)
            (recipe / "recipe.yaml").write_text(
                """context:
  version: 1.0.0

package:
  name: app
  version: ${{ version }}
""",
                encoding="utf-8",
            )

            self.assertEqual(resolve_build_numbers.recipe_package_names(recipe), ["app"])

    def test_recipe_package_names_prefer_outputs_over_top_level_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = Path(tmp_raw) / "split-app" / "1.0.0"
            recipe.mkdir(parents=True)
            (recipe / "recipe.yaml").write_text(
                """context:
  version: 1.0.0

package:
  name: split-app
  version: ${{ version }}

outputs:
  - package:
      name: split-app-lib
  - package:
      name: split-app
""",
                encoding="utf-8",
            )

            self.assertEqual(
                resolve_build_numbers.recipe_package_names(recipe),
                ["split-app-lib", "split-app"],
            )

    def test_empty_publish_build_number_resolves_real_imath_recipe(self) -> None:
        fetched_urls: list[str] = []

        def fake_fetch(url: str) -> list[dict[str, object]]:
            fetched_urls.append(url)
            return []

        recipe = ROOT / "imath" / "3.2.2"
        self.assertEqual(
            resolve_build_numbers.resolve_build_numbers(
                [recipe],
                ["linux-64"],
                "default-label",
                "",
                fake_fetch,
            ),
            {recipe.as_posix(): "0"},
        )
        self.assertCountEqual(
            fetched_urls,
            [
                "https://api.anaconda.org/package/anderslanglands/imath/files",
                "https://api.anaconda.org/package/anderslanglands/imath-dev/files",
                "https://api.anaconda.org/package/anderslanglands/imath-lib/files",
            ],
        )
        self.assertEqual(len(fetched_urls), 3)

    def test_fetch_package_files_accepts_list_and_dict_payloads(self) -> None:
        class FakeResponse:
            def __init__(self, payload: object) -> None:
                self.payload = payload

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> str:
                return json.dumps(self.payload)

        payloads: list[object] = [
            [{"version": "1.0.0"}],
            {"files": [{"version": "2.0.0"}]},
        ]
        original_urlopen = resolve_build_numbers.urlopen

        def fake_urlopen(url: str, timeout: int) -> FakeResponse:
            self.assertEqual(timeout, 30)
            return FakeResponse(payloads.pop(0))

        try:
            resolve_build_numbers.urlopen = fake_urlopen
            self.assertEqual(
                resolve_build_numbers.fetch_package_files("https://example.test/list"),
                [{"version": "1.0.0"}],
            )
            self.assertEqual(
                resolve_build_numbers.fetch_package_files("https://example.test/dict"),
                [{"version": "2.0.0"}],
            )
        finally:
            resolve_build_numbers.urlopen = original_urlopen

    def test_fetch_package_files_treats_404_as_empty_package(self) -> None:
        original_urlopen = resolve_build_numbers.urlopen

        def fake_urlopen(url: str, timeout: int) -> object:
            raise HTTPError(url, 404, "missing", hdrs=None, fp=None)

        try:
            resolve_build_numbers.urlopen = fake_urlopen
            self.assertEqual(resolve_build_numbers.fetch_package_files("https://example.test/missing"), [])
        finally:
            resolve_build_numbers.urlopen = original_urlopen

    def test_fetch_package_files_rejects_unexpected_payload_shape(self) -> None:
        class FakeResponse:
            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> str:
                return json.dumps({"unexpected": []})

        original_urlopen = resolve_build_numbers.urlopen

        try:
            resolve_build_numbers.urlopen = lambda url, timeout: FakeResponse()
            with self.assertRaisesRegex(SystemExit, "Unexpected Anaconda package file listing shape"):
                resolve_build_numbers.fetch_package_files("https://example.test/bad")
        finally:
            resolve_build_numbers.urlopen = original_urlopen

    def test_artifact_only_empty_build_number_preserves_recipe_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = self.make_recipe(Path(tmp_raw))

            def fail_fetch(_: str) -> list[dict[str, object]]:
                raise AssertionError("artifact-only should not fetch package files")

            self.assertEqual(
                resolve_build_numbers.resolve_build_numbers(
                    [recipe],
                    ["linux-64"],
                    "artifact-only",
                    "",
                    fail_fetch,
                ),
                {recipe.as_posix(): ""},
            )

    def test_artifact_only_rejects_explicit_auto_build_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = self.make_recipe(Path(tmp_raw))
            with self.assertRaisesRegex(SystemExit, "requires test-label or default-label"):
                resolve_build_numbers.resolve_build_numbers(
                    [recipe],
                    ["linux-64"],
                    "artifact-only",
                    "auto",
                    lambda _: [],
                )

    def test_explicit_build_number_skips_package_file_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = self.make_recipe(Path(tmp_raw))

            def fail_fetch(_: str) -> list[dict[str, object]]:
                raise AssertionError("explicit build number should not fetch package files")

            self.assertEqual(
                resolve_build_numbers.resolve_build_numbers(
                    [recipe],
                    ["linux-64"],
                    "default-label",
                    "7",
                    fail_fetch,
                ),
                {recipe.as_posix(): "7"},
            )

    def test_resolve_build_numbers_cli_expands_wildcard_recipe_selector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            for version in ["1.0.0", "1.1.0"]:
                recipe = tmp / "foo" / version
                recipe.mkdir(parents=True)
                (recipe / "recipe.yaml").write_text(f"recipe:\n  name: foo\n  version: {version}\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "resolve_build_numbers.py"),
                    "--recipes",
                    "foo/*",
                    "--platforms",
                    "linux-64",
                    "--target",
                    "default-label",
                    "--build-number",
                    "7",
                ],
                cwd=tmp,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(json.loads(completed.stdout), {"foo/1.0.0": "7", "foo/1.1.0": "7"})

    def test_resolve_build_numbers_cli_expands_bare_package_recipe_selector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            for version in ["1.0.0", "1.1.0"]:
                recipe = tmp / "foo" / version
                recipe.mkdir(parents=True)
                (recipe / "recipe.yaml").write_text(f"recipe:\n  name: foo\n  version: {version}\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "resolve_build_numbers.py"),
                    "--recipes",
                    "foo",
                    "--platforms",
                    "linux-64",
                    "--target",
                    "default-label",
                    "--build-number",
                    "7",
                ],
                cwd=tmp,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(json.loads(completed.stdout), {"foo/1.0.0": "7", "foo/1.1.0": "7"})


    def test_resolve_build_numbers_rejects_default_label_disallowed_by_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = self.make_recipe(Path(tmp_raw))
            with (recipe / "recipe.yaml").open("a", encoding="utf-8") as handle:
                handle.write("""
extra:
  allowed_publish_targets:
    - test-label
""")

            def fail_fetch(_: str) -> list[dict[str, object]]:
                raise AssertionError("publish policy should reject before network lookup")

            with self.assertRaisesRegex(SystemExit, "may only be published to test-label"):
                resolve_build_numbers.resolve_build_numbers(
                    [recipe],
                    ["linux-64"],
                    "default-label",
                    "",
                    fail_fetch,
                )


    def test_explicit_build_number_resolver_cli_does_not_need_network(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/resolve_build_numbers.py",
                "--recipes",
                "imath/3.2.2",
                "--platforms",
                "win-64",
                "--target",
                "default-label",
                "--build-number",
                "7",
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )

        self.assertEqual(json.loads(completed.stdout), {"imath/3.2.2": "7"})


    def test_empty_publish_build_number_resolves_and_flows_into_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = self.make_recipe(Path(tmp_raw))

            def fake_fetch(url: str) -> list[dict[str, object]]:
                if url.endswith("/foo/files"):
                    return [
                        {
                            "version": "1.0.0",
                            "basename": "linux-64/foo-1.0.0-h456_2.conda",
                            "attrs": {"subdir": "linux-64", "build_number": 2},
                        }
                    ]
                return []

            resolved = resolve_build_numbers.resolve_build_numbers(
                [recipe],
                ["linux-64"],
                "default-label",
                "",
                fake_fetch,
            )
            matrix_build_numbers = ci_matrix.parse_resolved_build_numbers(
                json.dumps(resolved),
                [recipe],
                "",
            )
            matrix = ci_matrix.matrix([recipe], ["linux-64"], matrix_build_numbers)

            self.assertEqual(resolved, {recipe.as_posix(): "3"})
            self.assertEqual(matrix["include"][0]["build_number"], "3")

    def test_auto_build_number_uses_max_existing_matching_file_across_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = self.make_recipe(Path(tmp_raw))
            fetched_urls: list[str] = []

            def fake_fetch(url: str) -> list[dict[str, object]]:
                fetched_urls.append(url)
                if url.endswith("/foo-lib/files"):
                    return [
                        {
                            "basename": "linux-64/foo-lib-1.0.0-h999_5.conda",
                            "attrs": {"version": "1.0.0", "subdir": "linux-64", "build_number": 5},
                        },
                        {
                            "version": "2.0.0",
                            "basename": "linux-64/foo-lib-2.0.0-h123_99.conda",
                            "attrs": {"subdir": "linux-64", "build_number": 99},
                        },
                    ]
                if url.endswith("/foo/files"):
                    return [
                        {
                            "version": "1.0.0",
                            "basename": "win-64/foo-1.0.0-h456_2.conda",
                            "attrs": {"subdir": "win-64", "build": "h456_2"},
                        },
                        {
                            "version": "1.0.0",
                            "basename": "osx-64/foo-1.0.0-h789_8.conda",
                            "attrs": {"subdir": "osx-64", "build_number": 8},
                        },
                    ]
                return []

            self.assertEqual(
                resolve_build_numbers.resolve_build_numbers(
                    [recipe],
                    ["linux-64", "win-64"],
                    "test-label",
                    "auto",
                    fake_fetch,
                ),
                {recipe.as_posix(): "6"},
            )
            self.assertIn(
                "https://api.anaconda.org/package/anderslanglands/foo-lib/files",
                fetched_urls,
            )
            self.assertIn(
                "https://api.anaconda.org/package/anderslanglands/foo/files",
                fetched_urls,
            )


class PublishPackagesTests(unittest.TestCase):
    @staticmethod
    def make_typhoon_artifacts(tmp: Path) -> Path:
        artifact_dir = tmp / "artifacts" / "job" / "linux-64"
        artifact_dir.mkdir(parents=True)
        package = artifact_dir / "openusd-typhoon-26.05.8.4bdd4b656-py312h123_0.conda"
        package.write_bytes(b"placeholder")
        manifest = tmp / "artifacts" / "job" / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "recipe": "openusd-typhoon/26.05.8.4bdd4b656",
                    "platform": "linux-64",
                    "packages": [
                        {
                            "path": "linux-64/openusd-typhoon-26.05.8.4bdd4b656-py312h123_0.conda",
                            "file_name": "openusd-typhoon-26.05.8.4bdd4b656-py312h123_0.conda",
                            "subdir": "linux-64",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return package

    def test_package_paths_rejects_default_label_disallowed_by_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            recipe = tmp / "preview" / "1.0.0"
            recipe.mkdir(parents=True)
            (recipe / "recipe.yaml").write_text(
                """recipe:
  name: preview
  version: 1.0.0

extra:
  allowed_publish_targets:
    - test-label
""",
                encoding="utf-8",
            )
            artifact_dir = tmp / "artifacts" / "job" / "linux-64"
            artifact_dir.mkdir(parents=True)
            package = artifact_dir / "preview-1.0.0-h123_0.conda"
            package.write_bytes(b"placeholder")
            manifest = tmp / "artifacts" / "job" / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "recipe": "preview/1.0.0",
                        "platform": "linux-64",
                        "packages": [
                            {
                                "path": "linux-64/preview-1.0.0-h123_0.conda",
                                "file_name": "preview-1.0.0-h123_0.conda",
                                "subdir": "linux-64",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            cwd = Path.cwd()
            try:
                os.chdir(tmp)
                self.assertEqual(publish_packages.package_paths(tmp / "artifacts", "test-label"), [package])
                with self.assertRaisesRegex(SystemExit, "may only be published to test-label"):
                    publish_packages.package_paths(tmp / "artifacts", "default-label")
            finally:
                os.chdir(cwd)

    def test_publish_packages_cli_allows_real_typhoon_recipe_to_test_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            package = self.make_typhoon_artifacts(tmp)

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/publish_packages.py",
                    "--target",
                    "test-label",
                    "--root",
                    str(tmp / "artifacts"),
                    "--dry-run",
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("--channel test", completed.stdout)
            self.assertNotIn("--channel main", completed.stdout)
            self.assertIn(str(package), completed.stdout)

    def test_publish_packages_cli_rejects_default_label_for_real_typhoon_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            self.make_typhoon_artifacts(tmp)

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/publish_packages.py",
                    "--target",
                    "default-label",
                    "--root",
                    str(tmp / "artifacts"),
                    "--dry-run",
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "Recipe openusd-typhoon/26.05.8.4bdd4b656 may only be published to test-label; requested default-label.",
                completed.stderr,
            )


class SmokeConsumersTests(unittest.TestCase):
    def test_channel_priority_for_recipe_relaxes_openusd_typhoon_only(self) -> None:
        self.assertEqual(
            smoke_consumers.channel_priority_for_recipe(Path("openusd-typhoon/26.05.8.4bdd4b656")),
            "disabled",
        )
        self.assertEqual(smoke_consumers.channel_priority_for_recipe(Path("openusd/26.05")), "strict")
        self.assertEqual(smoke_consumers.channel_priority_for_recipe(Path("openusd-typhoon")), "strict")

    def test_write_manifest_uses_requested_channel_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            manifest = Path(tmp_raw) / "pixi.toml"

            smoke_consumers.write_manifest(
                manifest,
                {"name": "openusd-typhoon", "version": "26.05.8.4bdd4b656", "build": "py312h123_0"},
                "linux-64",
                [
                    "https://conda.anaconda.org/anderslanglands/label/test",
                    "https://conda.anaconda.org/anderslanglands",
                    "conda-forge",
                ],
                "disabled",
                False,
            )

            rendered = manifest.read_text(encoding="utf-8")
            self.assertIn(
                """channels = [
  "https://conda.anaconda.org/anderslanglands/label/test",
  "https://conda.anaconda.org/anderslanglands",
  "conda-forge",
]""",
                rendered,
            )
            self.assertIn('channel-priority = "disabled"', rendered)

    def test_run_cmake_consumer_runs_ctest_after_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            recipe = tmp / "openqmc" / "0.7.1"
            tests = recipe / "tests"
            tests.mkdir(parents=True)
            (tests / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.15)\n",
                encoding="utf-8",
            )
            manifest = tmp / "pixi.toml"
            manifest.write_text("", encoding="utf-8")

            calls: list[tuple[str, ...]] = []
            original_pixi = smoke_consumers.pixi

            def fake_pixi(*args: str) -> None:
                calls.append(args)

            try:
                smoke_consumers.pixi = fake_pixi
                smoke_consumers.run_cmake_consumer(
                    manifest,
                    recipe,
                    "openqmc",
                    {"name": "openqmc-header-only"},
                    tmp,
                )
            finally:
                smoke_consumers.pixi = original_pixi

            build = tmp / "build-openqmc-header-only"
            self.assertEqual(calls[-1], (
                "run",
                "--manifest-path",
                str(manifest),
                "ctest",
                "--test-dir",
                str(build),
                "--output-on-failure",
            ))

    def test_run_cmake_consumer_passes_opensubdiv_platform_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            recipe = tmp / "opensubdiv" / "3.7.0"
            tests = recipe / "tests"
            tests.mkdir(parents=True)
            (tests / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.20)\n",
                encoding="utf-8",
            )
            manifest = tmp / "pixi.toml"
            manifest.write_text("", encoding="utf-8")

            calls: list[tuple[str, ...]] = []
            original_pixi = smoke_consumers.pixi

            def fake_pixi(*args: str) -> None:
                calls.append(args)

            try:
                smoke_consumers.pixi = fake_pixi
                smoke_consumers.run_cmake_consumer(
                    manifest,
                    recipe,
                    "opensubdiv",
                    {"name": "opensubdiv-gpu-dev", "subdir": "osx-arm64"},
                    tmp,
                )
            finally:
                smoke_consumers.pixi = original_pixi

            cmake_configure = calls[0]
            self.assertIn("-DOPENSUBDIV_CONSUMER_REQUIRE_GPU=ON", cmake_configure)
            self.assertIn("-DOPENSUBDIV_CONSUMER_REQUIRE_METAL=ON", cmake_configure)
            self.assertIn("-DOPENSUBDIV_CONSUMER_FORBID_CUDA=ON", cmake_configure)
            self.assertNotIn("-DOPENSUBDIV_CONSUMER_FORBID_METAL=ON", cmake_configure)

    def test_openqmc_header_only_runs_cmake_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = Path(tmp_raw) / "openqmc" / "0.7.1"
            tests = recipe / "tests"
            tests.mkdir(parents=True)
            (tests / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.15)\n",
                encoding="utf-8",
            )

            self.assertTrue(
                smoke_consumers.package_needs_consumer_test(
                    "openqmc",
                    {"name": "openqmc-header-only"},
                    recipe,
                )
            )

    def test_openqmc_header_only_passes_expected_cmake_flag(self) -> None:
        self.assertEqual(
            smoke_consumers.cmake_consumer_args("openqmc", {"name": "openqmc-header-only"}, "linux-64"),
            ["-DOPENQMC_CONSUMER_EXPECT_HEADER_ONLY=ON"],
        )

    def test_opensubdiv_public_flavor_metapackages_run_cmake_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            recipe = Path(tmp_raw) / "opensubdiv" / "3.7.0"
            tests = recipe / "tests"
            tests.mkdir(parents=True)
            (tests / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.20)\n",
                encoding="utf-8",
            )

            for package_name in ["opensubdiv", "opensubdiv-dev", "opensubdiv-gpu", "opensubdiv-cuda"]:
                with self.subTest(package_name=package_name):
                    self.assertTrue(
                        smoke_consumers.package_needs_consumer_test(
                            "opensubdiv",
                            {"name": package_name},
                            recipe,
                        )
                    )

    def test_opensubdiv_flavor_packages_pass_expected_cmake_flags(self) -> None:
        self.assertEqual(
            smoke_consumers.cmake_consumer_args("opensubdiv", {"name": "opensubdiv-dev"}, "linux-64"),
            ["-DOPENSUBDIV_CONSUMER_EXPECT_CPU_ONLY=ON"],
        )
        graphics_api_args = [
            "-DOPENSUBDIV_CONSUMER_REQUIRE_GPU=ON",
            "-DOPENSUBDIV_CONSUMER_REQUIRE_OPENGL=ON",
            "-DOPENSUBDIV_CONSUMER_REQUIRE_TBB=ON",
            "-DOPENSUBDIV_CONSUMER_FORBID_CUDA=ON",
            "-DOPENSUBDIV_CONSUMER_FORBID_METAL=ON",
        ]
        for package_name in ["opensubdiv-gpu", "opensubdiv-gpu-dev"]:
            with self.subTest(package_name=package_name, platform="linux-64"):
                self.assertEqual(
                    smoke_consumers.cmake_consumer_args("opensubdiv", {"name": package_name}, "linux-64"),
                    graphics_api_args,
                )
            with self.subTest(package_name=package_name, platform="win-64"):
                self.assertEqual(
                    smoke_consumers.cmake_consumer_args("opensubdiv", {"name": package_name}, "win-64"),
                    graphics_api_args,
                )
        self.assertEqual(
            smoke_consumers.cmake_consumer_args("opensubdiv", {"name": "opensubdiv-gpu-dev"}, "osx-arm64"),
            [
                "-DOPENSUBDIV_CONSUMER_REQUIRE_GPU=ON",
                "-DOPENSUBDIV_CONSUMER_REQUIRE_METAL=ON",
                "-DOPENSUBDIV_CONSUMER_FORBID_CUDA=ON",
            ],
        )
        cuda_args = [
            "-DOPENSUBDIV_CONSUMER_REQUIRE_GPU=ON",
            "-DOPENSUBDIV_CONSUMER_REQUIRE_CUDA=ON",
            "-DOPENSUBDIV_CONSUMER_REQUIRE_OPENGL=ON",
            "-DOPENSUBDIV_CONSUMER_REQUIRE_TBB=ON",
            "-DOPENSUBDIV_CONSUMER_FORBID_METAL=ON",
        ]
        for package_name in ["opensubdiv-cuda", "opensubdiv-cuda-dev"]:
            with self.subTest(package_name=package_name, platform="linux-64"):
                self.assertEqual(
                    smoke_consumers.cmake_consumer_args("opensubdiv", {"name": package_name}, "linux-64"),
                    cuda_args,
                )
            with self.subTest(package_name=package_name, platform="win-64"):
                self.assertEqual(
                    smoke_consumers.cmake_consumer_args("opensubdiv", {"name": package_name}, "win-64"),
                    cuda_args,
                )

    def test_openqmc_flavor_packages_are_mutually_exclusive(self) -> None:
        recipe = (ROOT / "openqmc" / "0.7.1" / "recipe.yaml").read_text(encoding="utf-8")
        self.assertRegex(
            recipe,
            r"(?ms)name: openqmc-dev.*run_constraints:\n\s+- openqmc-header-only <0a0",
        )
        self.assertRegex(
            recipe,
            r"(?ms)name: openqmc-header-only.*run_constraints:\n\s+- openqmc-dev <0a0",
        )

    def test_opensubdiv_flavor_packages_are_mutually_exclusive(self) -> None:
        recipe = (ROOT / "opensubdiv" / "3.7.0" / "recipe.yaml").read_text(encoding="utf-8")

        def output_block(package_name: str) -> str:
            match = re.search(
                rf"(?ms)^  - package:\n      name: {re.escape(package_name)}\n(?P<block>.*?)(?=^  - (?:package|staging):|\Z)",
                recipe,
            )
            self.assertIsNotNone(match, f"missing output block for {package_name}")
            return match.group("block") if match else ""

        def run_constraints(package_name: str) -> set[str]:
            match = re.search(
                r"(?ms)^      run_constraints:\n(?P<body>(?:        - .+\n)+)",
                output_block(package_name),
            )
            self.assertIsNotNone(match, f"missing run_constraints for {package_name}")
            return set(re.findall(r"^        - (.+)$", match.group("body"), flags=re.MULTILINE)) if match else set()

        expected_constraints = {
            "opensubdiv-lib": {"opensubdiv-gpu-lib <0a0", "opensubdiv-cuda-lib <0a0"},
            "opensubdiv-gpu-lib": {"opensubdiv-lib <0a0", "opensubdiv-cuda-lib <0a0"},
            "opensubdiv-cuda-lib": {"opensubdiv-lib <0a0", "opensubdiv-gpu-lib <0a0"},
            "opensubdiv-dev": {"opensubdiv-gpu-dev <0a0", "opensubdiv-cuda-dev <0a0"},
            "opensubdiv-gpu-dev": {"opensubdiv-dev <0a0", "opensubdiv-cuda-dev <0a0"},
            "opensubdiv-cuda-dev": {"opensubdiv-dev <0a0", "opensubdiv-gpu-dev <0a0"},
            "opensubdiv": {"opensubdiv-gpu <0a0", "opensubdiv-cuda <0a0"},
            "opensubdiv-gpu": {"opensubdiv <0a0", "opensubdiv-cuda <0a0"},
            "opensubdiv-cuda": {"opensubdiv <0a0", "opensubdiv-gpu <0a0"},
        }
        for package_name, expected in expected_constraints.items():
            with self.subTest(package_name=package_name):
                self.assertEqual(run_constraints(package_name), expected)


if __name__ == "__main__":
    unittest.main()
