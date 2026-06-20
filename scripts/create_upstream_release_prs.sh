#!/usr/bin/env bash
set -euo pipefail

: "${RESULT_JSON:?RESULT_JSON is required}"
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"

base_branch="${BASE_BRANCH:-${GITHUB_REF_NAME:-main}}"
branch_prefix="${AUTOMATION_BRANCH_PREFIX:-automation/upstream-release-prs}"
platforms="${PLATFORMS:-default}"
publish_target="${PUBLISH_TARGET:-test-label}"
run_smoke_tests="${RUN_SMOKE_TESTS:-true}"
dispatch_build="${DISPATCH_BUILD:-true}"
pr_token="${PR_GH_TOKEN:-${GH_TOKEN:-}}"
actions_token="${ACTIONS_GH_TOKEN:-${GH_TOKEN:-}}"

if [[ "$publish_target" == "default-label" ]]; then
  echo "Nightly upstream release checks may not dispatch default-label publishes." >&2
  exit 1
fi

if [[ "$dispatch_build" == "true" && "${GITHUB_ACTIONS:-}" == "true" && -z "${ACTIONS_GH_TOKEN:-}" ]]; then
  message="UPSTREAM_RELEASE_PR_TOKEN is required to dispatch build workflows from GitHub Actions so downstream auto-merge can run."
  echo "$message" >&2
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    echo "$message" >> "$GITHUB_STEP_SUMMARY"
  fi
  exit 1
fi

staging="$RUNNER_TEMP/upstream-release-recipes"
created_tsv="$RUNNER_TEMP/upstream-release-created.tsv"
rm -rf "$staging"
mkdir -p "$staging"

python3 - "$RESULT_JSON" "$staging" > "$created_tsv" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

result_json = Path(sys.argv[1])
staging = Path(sys.argv[2])
root = Path.cwd()
payload = json.loads(result_json.read_text(encoding="utf-8"))

for item in payload.get("created", []):
    recipe = item["recipe"]
    source = root / recipe
    destination = staging / recipe
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    print(
        "\t".join(
            [
                item["package"],
                item["version"],
                recipe,
                item["copied_from"],
                item["upstream_tag"],
                item.get("source_sha256", ""),
            ]
        )
    )
PY

if [[ ! -s "$created_tsv" ]]; then
  echo "No upstream release PRs to create." >> "$GITHUB_STEP_SUMMARY"
  exit 0
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git fetch origin "$base_branch"
base_ref="origin/$base_branch"

git reset --hard
git clean -fd

while IFS=$'\t' read -r package version recipe copied_from upstream_tag source_sha256; do
  branch="$branch_prefix/$recipe"
  recipe_report="$RUNNER_TEMP/upstream-release-${package}-${version}.md"
  existing_pr="$(GH_TOKEN="$pr_token" gh pr list --head "$branch" --base "$base_branch" --state open --json number --jq '.[0].number // empty' 2>/dev/null || true)"
  branch_exists=false
  if git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
    branch_exists=true
  fi

  if [[ -n "$existing_pr" ]]; then
    echo "Keeping existing upstream release PR #$existing_pr on $branch; not overwriting branch contents." >> "$GITHUB_STEP_SUMMARY"
  elif [[ "$branch_exists" == "true" ]]; then
    echo "Keeping existing upstream release branch $branch without an open PR; not overwriting branch contents." >> "$GITHUB_STEP_SUMMARY"
  else
    git checkout -B "$branch" "$base_ref"
    git reset --hard
    git clean -fd

    mkdir -p "$(dirname "$recipe")"
    cp -a "$staging/$recipe" "$recipe"

    python3 - "$package" <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, "scripts")
import check_upstream_releases as upstream

upstream.update_readme_versions(Path.cwd(), sys.argv[1], set())
PY

    git add "$recipe"
    if [[ -f README.md ]]; then
      git add README.md
    fi
    if git diff --cached --quiet; then
      echo "No changes were staged for $recipe." >&2
      exit 1
    fi

    git commit -m "Add $recipe upstream release recipe"
    git fetch origin "$branch" || true
    git push --force-with-lease origin "$branch"
  fi

  {
    echo "Automated upstream release check created a new recipe copy."
    echo
    echo "- \`$recipe\` from \`$copied_from\` for upstream tag \`$upstream_tag\`, sha256 \`$source_sha256\`"
  } > "$recipe_report"

  AUTOMATION_BRANCH="$branch" \
    BASE_BRANCH="$base_branch" \
    RECIPE="$recipe" \
    PACKAGE="$package" \
    VERSION="$version" \
    REPORT="$recipe_report" \
    GH_TOKEN="$pr_token" \
    scripts/open_upstream_release_pr.sh

  if [[ "$dispatch_build" == "true" ]]; then
    GH_TOKEN="$actions_token" gh workflow run build-packages.yml \
      --ref "$branch" \
      -f recipes="$recipe" \
      -f platforms="$platforms" \
      -f publish_target="$publish_target" \
      -f build_number="" \
      -f run_smoke_tests="$run_smoke_tests"
  else
    echo "Build dispatch disabled for $recipe." >> "$GITHUB_STEP_SUMMARY"
  fi

  echo "Created or refreshed upstream release PR branch \`$branch\` for \`$recipe\`." >> "$GITHUB_STEP_SUMMARY"
done < "$created_tsv"
