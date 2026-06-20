#!/usr/bin/env bash
set -euo pipefail

: "${AUTOMATION_BRANCH:?AUTOMATION_BRANCH is required}"
: "${REPORT:?REPORT is required}"

base_branch="${BASE_BRANCH:-${GITHUB_REF_NAME:-main}}"
recipe="${RECIPE:-}"
if [[ -n "$recipe" ]]; then
  title="Add $recipe upstream release recipe"
else
  title="Add upstream release recipe updates"
fi

body_file="$RUNNER_TEMP/upstream-release-pr-body.md"
{
  if [[ -n "$recipe" ]]; then
    echo "Automated upstream release check created a new recipe copy for \`$recipe\`."
  else
    echo "Automated upstream release check created new recipe copies."
  fi
  echo
  cat "$REPORT"
  echo
  echo "The build workflow is dispatched separately on this branch when enabled."
} > "$body_file"

pr_number=""
existing="$(gh pr list --head "$AUTOMATION_BRANCH" --base "$base_branch" --state open --json number --jq '.[0].number // empty' 2>/dev/null || true)"
if [[ -n "$existing" ]]; then
  if gh pr edit "$existing" --title "$title" --body-file "$body_file"; then
    pr_number="$existing"
  else
    echo "::warning::Could not update upstream release PR #$existing."
  fi
else
  if gh pr create \
    --head "$AUTOMATION_BRANCH" \
    --base "$base_branch" \
    --title "$title" \
    --body-file "$body_file"; then
    pr_number="$(gh pr list --head "$AUTOMATION_BRANCH" --base "$base_branch" --state open --json number --jq '.[0].number // empty')"
  else
    compare_url="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/compare/$base_branch...$AUTOMATION_BRANCH?expand=1"
    echo "::warning::Could not create upstream release PR. Enable 'Allow GitHub Actions to create and approve pull requests' or configure an UPSTREAM_RELEASE_PR_TOKEN secret. Manual PR URL: $compare_url"
    {
      echo "Could not create the upstream release PR automatically."
      echo
      echo "Enable repository Actions setting 'Allow GitHub Actions to create and approve pull requests' or configure an \`UPSTREAM_RELEASE_PR_TOKEN\` secret with pull request write access."
      echo
      echo "Manual PR URL: $compare_url"
    } >> "$GITHUB_STEP_SUMMARY"
  fi
fi

echo "number=$pr_number" >> "$GITHUB_OUTPUT"
