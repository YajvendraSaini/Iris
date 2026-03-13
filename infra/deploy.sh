#!/bin/bash
# ── Iris — One-command Cloud Run Deploy ─────────────────────────────────────
#
# USAGE:
#   1. Fill in the CONFIG section below (PROJECT_ID etc.)
#   2. Make sure you have:
#        - gcloud CLI installed & authenticated  (gcloud auth login)
#        - Docker installed & running
#        - Required APIs enabled (see enable-apis step below)
#   3. Run from the REPO ROOT:
#        chmod +x infra/deploy.sh && ./infra/deploy.sh
#
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── CONFIG — fill these in ────────────────────────────────────────────────────
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-gcp-project-id}"   # e.g. my-iris-project
REGION="us-central1"
SERVICE_NAME="iris-backend"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Secret names in Google Secret Manager (created in step below)
SECRET_GEMINI="GEMINI_API_KEY"
SECRET_MAPS="GOOGLE_MAPS_API_KEY"
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "🌍 Deploying Iris to Google Cloud Run"
echo "   Project : ${PROJECT_ID}"
echo "   Region  : ${REGION}"
echo "   Image   : ${IMAGE}"
echo ""

# Guard: make sure PROJECT_ID was set
if [[ "${PROJECT_ID}" == "your-gcp-project-id" ]]; then
  echo "❌  ERROR: Set PROJECT_ID in infra/deploy.sh (or export GOOGLE_CLOUD_PROJECT=...) before running."
  exit 1
fi

# ── Step 1: Enable required GCP APIs ─────────────────────────────────────────
echo "⚙️  Enabling GCP APIs (safe to re-run)..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  maps-backend.googleapis.com \
  --project="${PROJECT_ID}" \
  --quiet

# ── Step 2: Store secrets in Secret Manager (idempotent) ─────────────────────
echo ""
echo "🔐  Setting up Secret Manager secrets..."

_upsert_secret() {
  local name=$1
  local value=$2
  if gcloud secrets describe "${name}" --project="${PROJECT_ID}" &>/dev/null; then
    echo "   ↻  Secret '${name}' already exists — adding new version"
    echo -n "${value}" | gcloud secrets versions add "${name}" \
      --data-file=- --project="${PROJECT_ID}"
  else
    echo "   +  Creating secret '${name}'"
    echo -n "${value}" | gcloud secrets create "${name}" \
      --data-file=- --replication-policy=automatic --project="${PROJECT_ID}"
  fi
}

# Load keys from local .env (never baked into the image)
if [[ -f "backend/.env" ]]; then
  GEMINI_VAL=$(grep -E '^GEMINI_API_KEY=' backend/.env | cut -d'=' -f2-)
  MAPS_VAL=$(grep -E '^GOOGLE_MAPS_API_KEY=' backend/.env | cut -d'=' -f2-)

  [[ -n "${GEMINI_VAL}" ]] && _upsert_secret "${SECRET_GEMINI}" "${GEMINI_VAL}"
  [[ -n "${MAPS_VAL}"   ]] && _upsert_secret "${SECRET_MAPS}"   "${MAPS_VAL}"
else
  echo "   ⚠️  backend/.env not found — secrets must already exist in Secret Manager"
fi

# ── Step 3: Build Docker image from REPO ROOT ─────────────────────────────────
echo ""
echo "📦  Building Docker image (build context = repo root)..."
gcloud auth configure-docker --quiet

# Build context is repo root so frontend/ is accessible inside the Dockerfile
docker build \
  -f backend/Dockerfile \
  -t "${IMAGE}" \
  .

echo "📤  Pushing image to Container Registry..."
docker push "${IMAGE}"

# ── Step 4: Deploy to Cloud Run ───────────────────────────────────────────────
echo ""
echo "🚀  Deploying to Cloud Run..."

# Grant Cloud Run SA access to the secrets
CR_SA="${PROJECT_ID}@appspot.gserviceaccount.com"
for secret in "${SECRET_GEMINI}" "${SECRET_MAPS}"; do
  gcloud secrets add-iam-policy-binding "${secret}" \
    --member="serviceAccount:${CR_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="${PROJECT_ID}" \
    --quiet 2>/dev/null || true
done

gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},FIRESTORE_DATABASE=(default)" \
  --set-secrets "GEMINI_API_KEY=${SECRET_GEMINI}:latest,GOOGLE_MAPS_API_KEY=${SECRET_MAPS}:latest" \
  --quiet

# ── Step 5: Print deployed URL ────────────────────────────────────────────────
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format "value(status.url)")

echo ""
echo "✅  Iris is live!"
echo "   🔗  URL    : ${SERVICE_URL}"
echo "   🏥  Health : ${SERVICE_URL}/health"
echo "   🔌  WS     : wss://$(echo "${SERVICE_URL}" | sed 's|https://||')/ws"
echo ""
echo "📋  Next steps:"
echo "   1. Open ${SERVICE_URL} in your phone browser"
echo "   2. Allow camera + mic permissions"
echo "   3. Make sure Firestore is created in project ${PROJECT_ID}"
echo "      → https://console.cloud.google.com/firestore"
echo ""
