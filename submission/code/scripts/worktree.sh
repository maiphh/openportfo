#!/usr/bin/env bash
# Create git worktree + branch for an unrelated feature (unix counterpart to worktree.ps1)
# Usage: ./scripts/worktree.sh BL-027 portfolio-csv [main] [../]
set -euo pipefail

ID="${1:-}"; SLUG="${2:-}"; BASE="${3:-main}"; ROOT="${4:-..}"
if [[ -z "$ID" || -z "$SLUG" ]]; then
  echo "Usage: $0 <BL-XXX|XXX> <kebab-slug> [base=main] [worktree-root=..]" >&2
  exit 1
fi

# Normalize ID
if [[ "$ID" =~ ^[0-9]+$ ]]; then
  ID=$(printf "BL-%03d" "$ID")
elif [[ "$ID" =~ ^BL-?([0-9]+)$ ]]; then
  ID=$(printf "BL-%03d" "${BASH_REMATCH[1]}")
elif [[ ! "$ID" =~ ^BL-[0-9]{3}$ ]]; then
  echo "Id must be BL-XXX or XXX, got: $ID" >&2; exit 1
fi

SLUG=$(echo "$SLUG" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-//; s/-$//')
BRANCH="feat/$ID-$SLUG"
NUM=${ID#BL-}
WT="$ROOT/a3-wt-bl$NUM"

echo "Base: $BASE  Branch: $BRANCH  Worktree: $WT"
git worktree list

if [[ -e "$WT" ]]; then echo "Worktree path exists: $WT" >&2; exit 1; fi
if git branch --list "$BRANCH" | grep -q "$BRANCH"; then echo "Branch exists: $BRANCH" >&2; exit 1; fi

git branch "$BRANCH" "$BASE"
git worktree add "$WT" "$BRANCH"
echo "Done. cd \"$WT\""
git worktree list
