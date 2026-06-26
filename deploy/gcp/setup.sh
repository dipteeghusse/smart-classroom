#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy/gcp/setup.sh  — One-time GCP project bootstrap
# Run ONCE per project. Safe to re-run (most commands are idempotent).
# Prerequisites: gcloud CLI authenticated, billing enabled on PROJECT_ID
# Usage: PROJECT_ID=my-project REGION=asia-south1 bash deploy/gcp/setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID env var}"
REGION="${REGION:-asia-south1}"
AR_REPO="smart-classroom"

echo "=== GCP Bootstrap  project=$PROJECT_ID  region=$REGION ==="

# ── 1. Set active project ─────────────────────────────────────────────────────
gcloud config set project "$PROJECT_ID"

# ── 2. Enable required APIs ───────────────────────────────────────────────────
echo "Enabling APIs…"
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  drive.googleapis.com \
  sheets.googleapis.com \
  --quiet

# ── 3. Artifact Registry repository ──────────────────────────────────────────
echo "Creating Artifact Registry repo…"
gcloud artifacts repositories create "$AR_REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="Smart Classroom Docker images" \
  --quiet 2>/dev/null || echo "  Repo already exists — skipping."

# ── 4. Cloud Storage bucket for ChromaDB persistence ─────────────────────────
CHROMA_BUCKET="gs://${PROJECT_ID}-chromadb"
echo "Creating ChromaDB storage bucket: $CHROMA_BUCKET"
gcloud storage buckets create "$CHROMA_BUCKET" \
  --location="$REGION" \
  --uniform-bucket-level-access \
  --quiet 2>/dev/null || echo "  Bucket already exists — skipping."

# ── 5. Pub/Sub topics ─────────────────────────────────────────────────────────
echo "Creating Pub/Sub topics…"
for TOPIC in attendance-events quiz-events notification-events; do
  gcloud pubsub topics create "$TOPIC" --quiet 2>/dev/null || echo "  Topic $TOPIC already exists."
done

# ── 6. Service Account for Cloud Run ─────────────────────────────────────────
SA_NAME="smart-classroom-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
echo "Creating service account: $SA_EMAIL"
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="Smart Classroom Runtime SA" \
  --quiet 2>/dev/null || echo "  SA already exists — skipping."

# Grant required roles
for ROLE in \
  roles/secretmanager.secretAccessor \
  roles/storage.objectAdmin \
  roles/pubsub.publisher \
  roles/sheets.editor \
  roles/drive.file; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$ROLE" --quiet
done

# Grant Cloud Build SA permission to deploy to Cloud Run
CB_SA="$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')@cloudbuild.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CB_SA" \
  --role=roles/run.admin --quiet
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --member="serviceAccount:$CB_SA" \
  --role=roles/iam.serviceAccountUser --quiet

echo ""
echo "=== Bootstrap complete ==="
echo "Next step: fill in your .env then run:  bash deploy/gcp/secrets.sh"
echo "           SERVICE_ACCOUNT=$SA_EMAIL"
