#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy/gcp/deploy.sh  — Build images, push to Artifact Registry, deploy
# Usage:
#   PROJECT_ID=my-project REGION=asia-south1 bash deploy/gcp/deploy.sh
# Optional:
#   TAG=v1.2.3  (default: git short SHA)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-asia-south1}"
AR_REPO="smart-classroom"
TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo latest)}"
SA_EMAIL="${SA_EMAIL:-smart-classroom-sa@${PROJECT_ID}.iam.gserviceaccount.com}"

AR_HOST="${REGION}-docker.pkg.dev"
BACKEND_IMAGE="${AR_HOST}/${PROJECT_ID}/${AR_REPO}/backend:${TAG}"
FRONTEND_IMAGE="${AR_HOST}/${PROJECT_ID}/${AR_REPO}/frontend:${TAG}"

echo "=== Smart Classroom Deploy  tag=$TAG ==="

# ── Auth Docker to Artifact Registry ─────────────────────────────────────────
gcloud auth configure-docker "${AR_HOST}" --quiet

# ── Build & push backend ──────────────────────────────────────────────────────
echo "Building backend image…"
docker build -t "$BACKEND_IMAGE" -f Dockerfile .
docker push "$BACKEND_IMAGE"

# ── Build & push frontend ─────────────────────────────────────────────────────
echo "Building frontend image…"
docker build -t "$FRONTEND_IMAGE" -f frontend/Dockerfile frontend/
docker push "$FRONTEND_IMAGE"

# ── Helper: secret env-var flags for Cloud Run ───────────────────────────────
# All secrets follow the naming convention SC_<KEY> in Secret Manager.
secret_flag() {
  # $1 = env var name in container, $2 = Secret Manager secret name
  echo "--set-secrets=${1}=${2}:latest"
}

BACKEND_SECRETS=$(cat <<EOF
$(secret_flag GROQ_API_KEY       SC_GROQ_API_KEY)
$(secret_flag GOOGLE_SHEET_ID    SC_GOOGLE_SHEET_ID)
$(secret_flag GOOGLE_DRIVE_FOLDER_ID SC_GOOGLE_DRIVE_FOLDER_ID)
$(secret_flag SECRET_KEY         SC_SECRET_KEY)
$(secret_flag TWILIO_SID         SC_TWILIO_SID)
$(secret_flag TWILIO_TOKEN       SC_TWILIO_TOKEN)
$(secret_flag TWILIO_WHATSAPP    SC_TWILIO_WHATSAPP)
$(secret_flag SENDGRID_API_KEY   SC_SENDGRID_API_KEY)
$(secret_flag SENDGRID_FROM      SC_SENDGRID_FROM)
$(secret_flag GOOGLE_CREDS_JSON  SC_GOOGLE_CREDS_JSON)
EOF
)

# ── Deploy backend to Cloud Run ───────────────────────────────────────────────
echo "Deploying backend Cloud Run service…"
# shellcheck disable=SC2086
gcloud run deploy smart-classroom-backend \
  --image="$BACKEND_IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --service-account="$SA_EMAIL" \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=0 \
  --max-instances=5 \
  --concurrency=80 \
  --timeout=300 \
  --set-env-vars="CHROMA_PERSIST_DIR=/tmp/chromadb,PYTHONUNBUFFERED=1" \
  $BACKEND_SECRETS \
  --quiet

BACKEND_URL=$(gcloud run services describe smart-classroom-backend \
  --region="$REGION" --format='value(status.url)')
echo "  Backend URL: $BACKEND_URL"

# ── Deploy frontend to Cloud Run ──────────────────────────────────────────────
echo "Deploying frontend Cloud Run service…"
gcloud run deploy smart-classroom-frontend \
  --image="$FRONTEND_IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=256Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --set-env-vars="BACKEND_URL=${BACKEND_URL}" \
  --quiet

FRONTEND_URL=$(gcloud run services describe smart-classroom-frontend \
  --region="$REGION" --format='value(status.url)')

echo ""
echo "=== Deployment complete ==="
echo "  Frontend : $FRONTEND_URL"
echo "  Backend  : $BACKEND_URL"
echo ""
echo "Open the app: $FRONTEND_URL/login.html"
