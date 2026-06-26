# GCP Deployment Guide — Smart Classroom

## Architecture

```
Browser → Cloud Run (frontend/nginx) → Cloud Run (FastAPI backend)
                                            │
                  ┌─────────────────────────┼──────────────────────┐
                  ▼                         ▼                      ▼
           Google Sheets            Secret Manager          Cloud Storage
           (all data)               (all secrets)           (ChromaDB GCS)
                  │                         │                      │
                  ▼                         ▼                      │
           Google Drive             Pub/Sub topics                 │
           (report files)           (events)                       │
                  │                                                │
                  ▼                                                ▼
           Groq API                                         ChromaDB
           (LLM calls)                                   (vector store)
```

## Prerequisites

| Tool | Min version | Install |
|------|-------------|---------|
| gcloud CLI | 450+ | https://cloud.google.com/sdk/install |
| Docker | 24+ | https://docs.docker.com/get-docker/ |
| gh (GitHub CLI) | 2+ | `brew install gh` |

```bash
gcloud auth login
gcloud auth application-default login
```

---

## Step 1 — Create & configure .env

```bash
cp .env.example .env
# Edit .env and fill in all values
```

**Required values:**
- `GROQ_API_KEY` — from https://console.groq.com
- `GOOGLE_SHEET_ID` — your Google Sheet ID
- `GOOGLE_DRIVE_FOLDER_ID` — Shared Drive folder ID for reports
- `GOOGLE_CREDS_JSON` — service account JSON (inline, one line):
  ```bash
  cat path/to/service-account.json | jq -c . > /tmp/creds_inline.txt
  # paste content as GOOGLE_CREDS_JSON value in .env
  ```
- `SECRET_KEY` — any 32+ char random string:
  ```bash
  openssl rand -hex 32
  ```

---

## Step 2 — Bootstrap GCP project (one-time)

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=asia-south1          # or us-central1, etc.

bash deploy/gcp/setup.sh
```

This creates:
- Artifact Registry repo `smart-classroom`
- Cloud Storage bucket `${PROJECT_ID}-chromadb`
- Pub/Sub topics: `attendance-events`, `quiz-events`, `notification-events`
- Service account `smart-classroom-sa` with required IAM roles

---

## Step 3 — Upload secrets

```bash
export PROJECT_ID=your-gcp-project-id

bash deploy/gcp/secrets.sh
```

Reads every key from `.env` and creates/updates `SC_<KEY>` secrets in Secret Manager.

---

## Step 4 — Deploy

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=asia-south1
export SA_EMAIL=smart-classroom-sa@${PROJECT_ID}.iam.gserviceaccount.com

bash deploy/gcp/deploy.sh
```

Outputs the live URLs at the end:
```
=== Deployment complete ===
  Frontend : https://smart-classroom-frontend-xxxx-as.a.run.app
  Backend  : https://smart-classroom-backend-xxxx-as.a.run.app
```

---

## Step 5 — Connect frontend to backend (important)

After deploy, update `frontend/login.html` and `frontend/app.js` to point to the **backend Cloud Run URL** instead of `localhost:8080`:

In `login.html`:
```js
const API = "https://smart-classroom-backend-xxxx-as.a.run.app";
```

In `app.js`:
```js
const API = "https://smart-classroom-backend-xxxx-as.a.run.app";
```

Then redeploy:
```bash
bash deploy/gcp/deploy.sh
```

---

## Step 6 — Set up CI/CD (optional)

1. In GCP Console → Cloud Build → Triggers → Create Trigger
2. Connect your GitHub repo `dipteeghusse/smart-classroom`
3. Branch: `^main$`
4. Config file: `deploy/gcp/cloudbuild.yaml`
5. Substitution variables:
   - `_REGION` = `asia-south1`
   - `_SA_EMAIL` = `smart-classroom-sa@<PROJECT_ID>.iam.gserviceaccount.com`

Every push to `main` will auto-build and deploy both services.

---

## Step 7 — Load initial data

After deployment, upload sample data via the Admin dashboard:

1. Login as `ADMIN001 / admin123`
2. Go to **Upload** tab
3. Upload in order:
   - `sample_data/users.csv` (creates all login accounts)
   - `sample_data/students.csv`
   - `sample_data/faculty.csv`
   - `sample_data/subjects.csv`
   - `sample_data/lesson_plan.csv`

---

## Costs (approximate, Mumbai region)

| Service | Usage | $/month |
|---------|-------|---------|
| Cloud Run (backend) | 2 vCPU × 2 GB, ~100 req/day | ~$5 |
| Cloud Run (frontend) | 1 vCPU × 256 MB | ~$1 |
| Artifact Registry | 2 images × 500 MB | ~$0.5 |
| Secret Manager | 10 secrets, 1k accesses/day | ~$0.1 |
| Cloud Storage | 1 GB ChromaDB | ~$0.02 |
| **Total** | | **~$7/month** |

Cloud Run min-instances=0 means it scales to zero when not in use — ideal for college environments.

---

## Troubleshooting

**Backend 500 error on first request:**
- Check logs: `gcloud run logs tail smart-classroom-backend --region=asia-south1`
- Usually a missing secret or wrong `GOOGLE_SHEET_ID`

**Login "invalid token":**
- Verify `SECRET_KEY` secret is set correctly in Secret Manager
- Check `SC_SECRET_KEY` has the same value as what was in `.env`

**ChromaDB empty (questions not generating):**
- ChromaDB is re-initialised on each container cold-start (Cloud Run /tmp is ephemeral)
- Use the RAG seed endpoint or mount a persistent GCS-backed volume for production

**Google Sheets permission denied:**
- Share the Google Sheet with the service account email: `smart-classroom-sa@<PROJECT_ID>.iam.gserviceaccount.com`
- Give it **Editor** access
