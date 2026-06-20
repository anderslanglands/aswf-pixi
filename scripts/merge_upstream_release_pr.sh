#!/usr/bin/env bash
set -euo pipefail

: "${AUTOMATION_BRANCH:?AUTOMATION_BRANCH is required}"
: "${GITHUB_STEP_SUMMARY:?GITHUB_STEP_SUMMARY is required}"

branch_prefix="${AUTOMATION_BRANCH_PREFIX:-automation/upstream-release-prs/}"
if [[ "$branch_prefix" != */ ]]; then
  branch_prefix="$branch_prefix/"
fi

if [[ "$AUTOMATION_BRANCH" != "$branch_prefix"* ]]; then
  {
    echo "Skipping upstream release PR auto-merge."
    echo
    echo "The completed build branch $AUTOMATION_BRANCH does not use the upstream release branch prefix $branch_prefix."
  } >> "$GITHUB_STEP_SUMMARY"
  exit 0
fi

recipe="${AUTOMATION_BRANCH#"$branch_prefix"}"
display_title="${RUN_DISPLAY_TITLE:-}"
if [[ -z "$display_title" && -n "${RUN_ID:-}" && -n "${GITHUB_REPOSITORY:-}" ]]; then
  display_title="$(gh api "repos/$GITHUB_REPOSITORY/actions/runs/$RUN_ID" --jq '.display_title // ""' 2>/dev/null || true)"
fi

expected_prefix="Build $recipe ("
if [[ "$display_title" != "$expected_prefix"* || "$display_title" != *", test-label, smoke=true)" ]]; then
  {
    echo "Skipping upstream release PR auto-merge."
    echo
    echo "The completed build was not a smoke-tested test-label build for $recipe: ${display_title:-unknown run title}"
  } >> "$GITHUB_STEP_SUMMARY"
  exit 0
fi

base_branch="${BASE_BRANCH:-main}"
pr_number="$(
  gh pr list \
    --head "$AUTOMATION_BRANCH" \
    --base "$base_branch" \
    --state open \
    --json number,headRefOid \
    --jq '.[0].number // empty'
)"
pr_head_sha="$(
  gh pr list \
    --head "$AUTOMATION_BRANCH" \
    --base "$base_branch" \
    --state open \
    --json number,headRefOid \
    --jq '.[0].headRefOid // empty'
)"

if [[ -z "$pr_number" ]]; then
  {
    echo "Skipping upstream release PR auto-merge."
    echo
    echo "No open PR was found from $AUTOMATION_BRANCH to $base_branch."
  } >> "$GITHUB_STEP_SUMMARY"
  exit 0
fi

if [[ -n "${RUN_HEAD_SHA:-}" && "$pr_head_sha" != "$RUN_HEAD_SHA" ]]; then
  {
    echo "Skipping upstream release PR auto-merge."
    echo
    echo "The successful build tested ${RUN_HEAD_SHA:-unknown}, but PR #$pr_number currently points at ${pr_head_sha:-unknown}."
  } >> "$GITHUB_STEP_SUMMARY"
  exit 0
fi

changed_files="$(gh api --paginate "repos/$GITHUB_REPOSITORY/pulls/$pr_number/files" --jq '.[].filename')"
recipe_file_seen=false
invalid_files=()
while IFS= read -r changed_file; do
  if [[ -z "$changed_file" ]]; then
    continue
  fi
  if [[ "$changed_file" == "$recipe"/* ]]; then
    recipe_file_seen=true
    continue
  fi
  if [[ "$changed_file" == "README.md" ]]; then
    continue
  fi
  invalid_files+=("$changed_file")
done <<< "$changed_files"

if [[ "$recipe_file_seen" != "true" || "${#invalid_files[@]}" -gt 0 ]]; then
  {
    echo "Skipping upstream release PR auto-merge."
    echo
    if [[ "$recipe_file_seen" != "true" ]]; then
      echo "PR #$pr_number does not change files under $recipe."
    fi
    if [[ "${#invalid_files[@]}" -gt 0 ]]; then
      echo "PR #$pr_number includes files outside $recipe and README.md:"
      printf -- '- %s\n' "${invalid_files[@]}"
    fi
  } >> "$GITHUB_STEP_SUMMARY"
  exit 0
fi

merge_args=(
  "$pr_number"
  --squash
  --delete-branch
  --subject "Add $recipe upstream release recipe"
  --body "Automerged after the test-label build, publish, and smoke workflow succeeded: ${RUN_HTML_URL:-unknown workflow run}"
)
if [[ -n "${RUN_HEAD_SHA:-}" ]]; then
  merge_args+=(--match-head-commit "$RUN_HEAD_SHA")
fi

gh pr merge "${merge_args[@]}"

{
  echo "Merged upstream release PR #$pr_number for $recipe after successful test-label build, publish, and smoke tests."
  if [[ -n "${RUN_HTML_URL:-}" ]]; then
    echo
    echo "Build run: $RUN_HTML_URL"
  fi
} >> "$GITHUB_STEP_SUMMARY"
