from __future__ import annotations

import json
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


class CiMatrixTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
