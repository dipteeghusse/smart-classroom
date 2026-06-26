#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy/gcp/secrets.sh  — Upload all env vars to Secret Manager
# Usage: PROJECT_ID=my-project bash deploy/gcp/secrets.sh
# Reads values from .env in the project root (never committed to git).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID env var}"
ENV_FILE="${ENV_FILE:-.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Copy .env.example and fill in values."
  exit 1
fi

echo "=== Uploading secrets to Secret Manager (project=$PROJECT_ID) ==="

upsert_secret() {
  local name="$1"
  local value="$2"
  if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
    echo "  Updating $name"
    printf '%s' "$value" | gcloud secrets versions add "$name" \
      --data-file=- --project="$PROJECT_ID" --quiet
  else
    echo "  Creating $name"
    printf '%s' "$value" | gcloud secrets create "$name" \
      --data-file=- --replication-policy=automatic \
      --project="$PROJECT_ID" --quiet
  fi
}

# Parse .env — skip blank lines and comments
while IFS='=' read -r key val; do
  [[ -z "$key" || "$key" =~ ^# ]] && continue
  # Strip surrounding quotes from value
  val="${val%\"}" ; val="${val#\"}"
  val="${val%\'}" ; val="${val#\'}"
  upsert_secret "SC_${key}" "$val"
done < <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')

echo ""
echo "=== All secrets uploaded ==="
echo "Now run:  bash deploy/gcp/deploy.sh"
