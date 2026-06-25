from __future__ import annotations

import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ci_matrix
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
        self.assertIn("name: Evaluate smoke for ${{ matrix.recipe }} (${{ matrix.platform }}, ${{ inputs.publish_target }}, smoke=${{ inputs.run_smoke_tests }})", workflow)
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


class SmokeConsumersTests(unittest.TestCase):
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
