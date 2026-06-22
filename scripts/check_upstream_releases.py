#!/usr/bin/env python3
"""Check upstream GitHub releases and stage new package recipe copies."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


GITHUB_API_ROOT = "https://api.github.com"
NUMBERED_TAG_RE = re.compile(r"^v?(?P<number>[0-9]+(?:[._][0-9]+)+)$", re.IGNORECASE)
GITHUB_REPO_RE = re.compile(r"github\.com[/:](?P<owner>[^/\s]+)/(?P<repo>[^/\s?#]+)")
CONTEXT_VALUE_RE = re.compile(r"^  (?P<key>[A-Za-z_][A-Za-z0-9_]*):\s*(?P<value>.*?)\s*(?:#.*)?$")
SOURCE_URL_RE = re.compile(r"(?m)^(\s*url:\s*)(?P<value>.+?)\s*$")
SOURCE_REPOSITORY_RE = re.compile(r"(?m)^\s*(?:-\s*)?(?:url|git):\s*(?P<value>.+?)\s*$")
SHA256_RE = re.compile(r"(?m)^(\s*sha256:\s*)([0-9a-fA-F]+)(\s*(?:#.*)?)$")
BUILD_NUMBER_RE = re.compile(r"(?m)^(\s*build_number:\s*)[0-9]+(\s*(?:#.*)?)$")
RECIPE_VERSIONS_RE = re.compile(r"(?m)^Recipe versions:(?P<inline>.*)$")
RECIPE_VERSION_ITEM_RE = re.compile(r"^- `(?P<version>[0-9]+(?:[._][0-9]+)+)`\s*$")
TEMPLATE_EXPR_RE = re.compile(r"\$\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
README_HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")


@dataclass(frozen=True)
class Version:
    parts: tuple[int, ...]

    @classmethod
    def parse(cls, value: str) -> Version | None:
        normalized = value.strip().replace("_", ".")
        if not normalized:
            return None
        pieces = normalized.split(".")
        if len(pieces) < 2 or not all(piece.isdigit() for piece in pieces):
            return None
        return cls(tuple(int(piece) for piece in pieces))

    @property
    def text(self) -> str:
        return ".".join(str(part) for part in self.parts)

    @property
    def line(self) -> tuple[int, ...]:
        return self.parts[:2] if len(self.parts) >= 2 else self.parts

    def _padded(self, width: int) -> tuple[int, ...]:
        return self.parts + (0,) * (width - len(self.parts))

    def __lt__(self, other: Version) -> bool:
        width = max(len(self.parts), len(other.parts))
        return self._padded(width) < other._padded(width)

    def __le__(self, other: Version) -> bool:
        return self == other or self < other


@dataclass(frozen=True)
class ReleaseCandidate:
    version: Version
    tag: str
    source: str
    url: str = ""


@dataclass(frozen=True)
class LocalRecipe:
    package: str
    path: Path
    version: Version
    repository: str
    context: dict[str, str]


@dataclass(frozen=True)
class CreatedRecipe:
    package: str
    version: str
    recipe: str
    copied_from: str
    upstream_tag: str
    source_sha256: str


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_numbered_tag(value: str) -> Version | None:
    match = NUMBERED_TAG_RE.match(value.strip())
    if not match:
        return None
    return Version.parse(match.group("number"))


def parse_context(recipe_text: str) -> dict[str, str]:
    context: dict[str, str] = {}
    in_context = False
    for line in recipe_text.splitlines():
        if line == "context:":
            in_context = True
            continue
        if in_context and line and not line.startswith(" "):
            break
        if not in_context:
            continue
        match = CONTEXT_VALUE_RE.match(line)
        if match:
            context[match.group("key")] = strip_quotes(match.group("value"))
    return context


def github_repo_slug(url: str) -> str | None:
    match = GITHUB_REPO_RE.search(url)
    if not match:
        return None
    repo = match.group("repo")
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"{match.group('owner')}/{repo}"


def recipe_metadata_repository(recipe_text: str) -> str | None:
    repository_match = re.search(r"(?m)^\s*repository:\s*(?P<url>\S+)\s*$", recipe_text)
    if repository_match:
        slug = github_repo_slug(strip_quotes(repository_match.group("url")))
        if slug:
            return slug
    return None


def recipe_source_repository(recipe_text: str) -> str | None:
    for source_match in SOURCE_REPOSITORY_RE.finditer(recipe_text):
        slug = github_repo_slug(strip_quotes(source_match.group("value")))
        if slug:
            return slug
    return None


def recipe_repository(recipe_text: str) -> str | None:
    return recipe_metadata_repository(recipe_text) or recipe_source_repository(recipe_text)


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def read_local_recipe(path: Path) -> LocalRecipe | None:
    version = Version.parse(path.name)
    if version is None:
        return None

    recipe_file = path / "recipe.yaml"
    if not recipe_file.is_file():
        return None

    recipe_text = recipe_file.read_text(encoding="utf-8")
    context = parse_context(recipe_text)
    context_version = Version.parse(context.get("version", ""))
    if context_version is None:
        raise SystemExit(f"{recipe_file} does not define a numeric context.version.")
    if context_version != version:
        raise SystemExit(
            f"{recipe_file} context.version {context_version.text} does not match directory {version.text}."
        )

    repository = recipe_metadata_repository(recipe_text)
    if repository is None:
        source_repository = recipe_source_repository(recipe_text)
        if source_repository is None:
            warn(f"{recipe_file} does not point at a GitHub repository; skipping upstream release checks.")
            return None
        warn(
            f"{recipe_file} does not define an about.repository GitHub URL; "
            f"using source repository {source_repository}."
        )
        repository = source_repository

    return LocalRecipe(
        package=path.parent.name,
        path=path,
        version=version,
        repository=repository,
        context=context,
    )


def discover_recipes(root: Path, packages: set[str] | None = None) -> dict[str, list[LocalRecipe]]:
    recipes: dict[str, list[LocalRecipe]] = {}
    for package_dir in sorted(root.iterdir()):
        if not package_dir.is_dir() or package_dir.name.startswith("."):
            continue
        if packages is not None and package_dir.name not in packages:
            continue
        package_recipes = [
            recipe
            for version_dir in sorted(package_dir.iterdir())
            if (recipe := read_local_recipe(version_dir)) is not None
        ]
        if package_recipes:
            recipes[package_dir.name] = sorted(package_recipes, key=lambda recipe: recipe.version)
    return recipes


def github_request_json(url: str, token: str | None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "aswf-pixi-upstream-release-checker",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        raise SystemExit(f"Failed to fetch {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise SystemExit(f"Failed to fetch {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse JSON from {url}: {exc}") from exc


def github_api_pages(repo: str, endpoint: str, token: str | None) -> Iterable[list[dict[str, Any]]]:
    page = 1
    while True:
        payload = github_request_json(
            f"{GITHUB_API_ROOT}/repos/{repo}/{endpoint}?per_page=100&page={page}",
            token,
        )
        if not isinstance(payload, list):
            raise SystemExit(f"Unexpected GitHub API response shape for {repo}/{endpoint}.")
        records = [record for record in payload if isinstance(record, dict)]
        if not records:
            break
        yield records
        if len(records) < 100:
            break
        page += 1


def release_candidate_from_tag(tag: str, source: str, url: str = "") -> ReleaseCandidate | None:
    version = parse_numbered_tag(tag)
    if version is None:
        return None
    return ReleaseCandidate(version=version, tag=tag, source=source, url=url)


def dedupe_release_candidates(candidates: Iterable[ReleaseCandidate]) -> list[ReleaseCandidate]:
    by_version: dict[Version, ReleaseCandidate] = {}
    for candidate in candidates:
        by_version.setdefault(candidate.version, candidate)
    return sorted(by_version.values(), key=lambda candidate: candidate.version)


def fetch_upstream_releases(repo: str, token: str | None) -> list[ReleaseCandidate]:
    release_candidates: list[ReleaseCandidate] = []
    for page in github_api_pages(repo, "releases", token):
        for record in page:
            if record.get("draft") or record.get("prerelease"):
                continue
            tag_name = str(record.get("tag_name", ""))
            candidate = release_candidate_from_tag(
                tag_name,
                source="release",
                url=str(record.get("html_url", "")),
            )
            if candidate:
                release_candidates.append(candidate)

    if release_candidates:
        return dedupe_release_candidates(release_candidates)

    tag_candidates: list[ReleaseCandidate] = []
    for page in github_api_pages(repo, "tags", token):
        for record in page:
            candidate = release_candidate_from_tag(str(record.get("name", "")), source="tag")
            if candidate:
                tag_candidates.append(candidate)
    return dedupe_release_candidates(tag_candidates)


def releases_to_package(
    local_recipes: list[LocalRecipe],
    upstream_releases: list[ReleaseCandidate],
) -> list[ReleaseCandidate]:
    known_versions = {recipe.version for recipe in local_recipes}
    if not known_versions:
        return []

    latest_known = max(known_versions)
    latest_known_by_line: dict[tuple[int, ...], Version] = {}
    for version in known_versions:
        latest_known_by_line[version.line] = max(version, latest_known_by_line.get(version.line, version))

    selected_by_line: dict[tuple[int, ...], ReleaseCandidate] = {}
    for release in upstream_releases:
        if release.version in known_versions:
            continue

        known_line_version = latest_known_by_line.get(release.version.line)
        tracks_existing_line = known_line_version is not None and release.version > known_line_version
        starts_newer_line = known_line_version is None and release.version > latest_known
        if not tracks_existing_line and not starts_newer_line:
            continue

        current = selected_by_line.get(release.version.line)
        if current is None or current.version < release.version:
            selected_by_line[release.version.line] = release

    return sorted(selected_by_line.values(), key=lambda release: release.version)


def common_prefix_length(left: Version, right: Version) -> int:
    count = 0
    for left_part, right_part in zip(left.parts, right.parts):
        if left_part != right_part:
            break
        count += 1
    return count


def weighted_version_distance(left: Version, right: Version) -> int:
    width = max(len(left.parts), len(right.parts))
    distance = 0
    for left_part, right_part in zip(left._padded(width), right._padded(width)):
        distance = distance * 1000 + abs(left_part - right_part)
    return distance


def closest_recipe(local_recipes: list[LocalRecipe], target: Version) -> LocalRecipe:
    return min(
        local_recipes,
        key=lambda recipe: (
            -common_prefix_length(recipe.version, target),
            weighted_version_distance(recipe.version, target),
            recipe.version > target,
            recipe.path.as_posix(),
        ),
    )


def replace_text_in_tree(root: Path, old_version: str, new_version: str, old_tag: str | None, new_tag: str) -> None:
    old_task_version = old_version.replace(".", "-")
    new_task_version = new_version.replace(".", "-")
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        updated = text.replace(old_version, new_version)
        updated = updated.replace(old_task_version, new_task_version)
        if old_tag:
            updated = updated.replace(old_tag, new_tag)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def render_source_url(recipe_file: Path) -> str:
    recipe_text = recipe_file.read_text(encoding="utf-8")
    context = parse_context(recipe_text)
    match = SOURCE_URL_RE.search(recipe_text)
    if not match:
        raise SystemExit(f"{recipe_file} does not define source.url.")
    template = strip_quotes(match.group("value"))

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            raise SystemExit(f"{recipe_file} source.url references unknown context key {key!r}.")
        return context[key]

    return TEMPLATE_EXPR_RE.sub(replace, template)


def source_sha256(url: str, token: str | None) -> str:
    headers = {"User-Agent": "aswf-pixi-upstream-release-checker"}
    if token and "github.com/" in url:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    digest = hashlib.sha256()
    try:
        with urlopen(request, timeout=120) as response:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
    except HTTPError as exc:
        raise SystemExit(f"Failed to download source archive {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise SystemExit(f"Failed to download source archive {url}: {exc.reason}") from exc
    return digest.hexdigest()


def update_recipe_sha256(recipe_file: Path, sha256: str) -> None:
    text = recipe_file.read_text(encoding="utf-8")
    text = BUILD_NUMBER_RE.sub(lambda match: f"{match.group(1)}0{match.group(2)}", text, count=1)
    text, count = SHA256_RE.subn(
        lambda match: f"{match.group(1)}{sha256}{match.group(3)}",
        text,
        count=1,
    )
    if count != 1:
        raise SystemExit(f"{recipe_file} does not contain exactly one sha256 field to update.")
    recipe_file.write_text(text, encoding="utf-8")


def section_ranges(readme_text: str) -> list[tuple[int, int]]:
    headings = [match.start() for match in re.finditer(r"(?m)^## ", readme_text)]
    return [
        (start, headings[index + 1] if index + 1 < len(headings) else len(readme_text))
        for index, start in enumerate(headings)
    ]


def normalized_heading_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def readme_section_heading(section: str) -> str:
    lines = section.splitlines()
    first_line = lines[0] if lines else ""
    match = README_HEADING_RE.match(first_line)
    return match.group("title") if match else ""


def format_readme_recipe_versions(versions: list[str]) -> str:
    lines = ["Recipe versions:"]
    lines.extend(f"- `{version}`" for version in versions)
    return "\n".join(lines)


def replace_readme_recipe_versions(readme_text: str, start: int, end: int, versions: list[str]) -> str | None:
    section = readme_text[start:end]
    match = RECIPE_VERSIONS_RE.search(section)
    if match is None:
        return None

    remove_end = match.end()
    if section[remove_end : remove_end + 1] == "\n":
        remove_end += 1
    for item_match in re.finditer(r"(?m)^.*(?:\n|\Z)", section[remove_end:]):
        line = item_match.group(0)
        if not line.strip() or not RECIPE_VERSION_ITEM_RE.match(line.strip()):
            break
        remove_end += len(line)

    tail = section[remove_end:].lstrip("\n")
    separator = "\n\n" if tail else "\n"
    updated_section = section[: match.start()] + format_readme_recipe_versions(versions) + separator + tail
    return readme_text[:start] + updated_section + readme_text[end:]


def update_readme_versions(root: Path, package: str, anchor_versions: set[str]) -> None:
    readme = root / "README.md"
    if not readme.is_file():
        return

    current_versions = sorted(
        (
            version_dir.name
            for version_dir in (root / package).iterdir()
            if version_dir.is_dir() and (version_dir / "recipe.yaml").is_file() and Version.parse(version_dir.name)
        ),
        key=lambda value: Version.parse(value) or Version((0,)),
    )
    text = readme.read_text(encoding="utf-8")
    ranges = section_ranges(text)
    package_key = normalized_heading_key(package)
    for start, end in ranges:
        section = text[start:end]
        heading_key = normalized_heading_key(readme_section_heading(section))
        if package_key and package_key in heading_key:
            updated = replace_readme_recipe_versions(text, start, end, current_versions)
            if updated is not None:
                readme.write_text(updated, encoding="utf-8")
                return

    for start, end in ranges:
        section = text[start:end]
        if not any(f"`{version}`" in section for version in anchor_versions):
            continue
        updated = replace_readme_recipe_versions(text, start, end, current_versions)
        if updated is not None:
            readme.write_text(updated, encoding="utf-8")
            return


def create_recipe_copy(
    root: Path,
    local_recipes: list[LocalRecipe],
    release: ReleaseCandidate,
    token: str | None,
    apply: bool,
    sha256_fetcher: Callable[[str, str | None], str] = source_sha256,
) -> CreatedRecipe:
    source = closest_recipe(local_recipes, release.version)
    destination = root / source.package / release.version.text
    if destination.exists():
        raise SystemExit(f"{destination} already exists.")

    source_sha = ""
    if apply:
        shutil.copytree(source.path, destination)
        replace_text_in_tree(
            destination,
            old_version=source.version.text,
            new_version=release.version.text,
            old_tag=source.context.get("tag"),
            new_tag=release.tag,
        )
        recipe_file = destination / "recipe.yaml"
        source_url = render_source_url(recipe_file)
        source_sha = sha256_fetcher(source_url, token)
        update_recipe_sha256(recipe_file, source_sha)

    return CreatedRecipe(
        package=source.package,
        version=release.version.text,
        recipe=(Path(source.package) / release.version.text).as_posix(),
        copied_from=source.path.relative_to(root).as_posix(),
        upstream_tag=release.tag,
        source_sha256=source_sha,
    )


def build_report(created: list[CreatedRecipe], dry_run: bool) -> str:
    if not created:
        return "No new numbered upstream releases were detected.\n"

    mode = "Would create" if dry_run else "Created"
    lines = [f"{mode} {len(created)} new package recipe(s):", ""]
    for recipe in created:
        sha_text = f", sha256 `{recipe.source_sha256}`" if recipe.source_sha256 else ""
        lines.append(
            f"- `{recipe.recipe}` from `{recipe.copied_from}` "
            f"for upstream tag `{recipe.upstream_tag}`{sha_text}"
        )
    lines.append("")
    return "\n".join(lines)


def append_github_output(path: Path, created: list[CreatedRecipe], report: str) -> None:
    recipes = ",".join(recipe.recipe for recipe in created)
    with path.open("a", encoding="utf-8") as output:
        output.write(f"created={'true' if created else 'false'}\n")
        output.write(f"recipes={recipes}\n")
        output.write("report<<UPSTREAM_RELEASE_REPORT\n")
        output.write(report)
        if not report.endswith("\n"):
            output.write("\n")
        output.write("UPSTREAM_RELEASE_REPORT\n")


def check_upstream_releases(
    root: Path,
    packages: set[str] | None,
    token: str | None,
    apply: bool,
    release_fetcher: Callable[[str, str | None], list[ReleaseCandidate]] = fetch_upstream_releases,
    sha256_fetcher: Callable[[str, str | None], str] = source_sha256,
) -> list[CreatedRecipe]:
    recipes_by_package = discover_recipes(root, packages)
    if packages:
        existing_package_dirs = {path.name for path in root.iterdir() if path.is_dir()}
        missing = sorted(packages - existing_package_dirs)
        if missing:
            raise SystemExit(f"No recipe package directories found for: {', '.join(missing)}")

    created: list[CreatedRecipe] = []
    for package, local_recipes in recipes_by_package.items():
        if not local_recipes:
            continue
        repository = local_recipes[-1].repository
        upstream_releases = release_fetcher(repository, token)
        releases = releases_to_package(local_recipes, upstream_releases)
        if not releases:
            continue

        anchor_versions = {recipe.version.text for recipe in local_recipes}
        for release in releases:
            destination = root / package / release.version.text
            if destination.exists():
                warn(
                    f"{destination} already exists but was not usable for upstream release checks; "
                    "skipping this release candidate."
                )
                continue
            created.append(
                create_recipe_copy(
                    root,
                    local_recipes,
                    release,
                    token,
                    apply=apply,
                    sha256_fetcher=sha256_fetcher,
                )
            )
            if apply:
                new_recipe = read_local_recipe(root / package / release.version.text)
                if new_recipe:
                    local_recipes.append(new_recipe)

        if apply:
            update_readme_versions(root, package, anchor_versions)

    return created


def parse_package_filters(values: list[str]) -> set[str] | None:
    if not values:
        return None
    packages: set[str] = set()
    for value in values:
        packages.update(item.strip() for item in value.split(",") if item.strip())
    return packages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--package", action="append", default=[], help="Package directory to check. Can be repeated or comma-separated.")
    parser.add_argument("--apply", action="store_true", help="Create recipe copies instead of reporting only.")
    parser.add_argument("--output-json", type=Path, help="Write machine-readable results to this path.")
    parser.add_argument("--report", type=Path, help="Write a markdown report to this path.")
    parser.add_argument("--github-output", type=Path, help="Append GitHub Actions outputs to this path.")
    parser.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN"))
    args = parser.parse_args()

    root = args.root.resolve()
    created = check_upstream_releases(
        root=root,
        packages=parse_package_filters(args.package),
        token=args.github_token,
        apply=args.apply,
    )
    report = build_report(created, dry_run=not args.apply)
    payload = {"created": [recipe.__dict__ for recipe in created]}

    if args.output_json:
        args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.report:
        args.report.write_text(report, encoding="utf-8")
    if args.github_output:
        append_github_output(args.github_output, created, report)

    sys.stdout.write(report)


if __name__ == "__main__":
    main()
