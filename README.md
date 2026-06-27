# 🎓 Smart Classroom Management System
### MITAOE · CSE (AI & ML) Department

AI-powered classroom management with 15 AI agents, Google Sheets as database, LangGraph orchestration, Groq LLM, ChromaDB RAG, and MCP Server.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.11 |
| AI Agents | LangGraph + Groq (LLaMA 3.3 70B) |
| Database | Google Sheets (10 tabs) |
| Vector Store | ChromaDB + sentence-transformers |
| MCP Server | `mcp` library (stdio transport) |
| Frontend | Pure HTML / CSS / JS |
| Deployment | GCP Cloud Run |

---

## Project Structure

```
smart-classroom/
├── backend/
│   ├── main.py              # FastAPI app — all REST endpoints
│   ├── orchestrator.py      # LangGraph state machine — routes to 15 agents
│   ├── mcp_server.py        # MCP server — 9 tools over stdio
│   ├── config.py            # All environment variables
│   ├── agents/
│   │   ├── attendance_agent.py   # QR + GPS attendance
│   │   ├── question_agent.py     # GATE question generation (RAG)
│   │   ├── quiz_agent.py         # Quiz evaluation
│   │   ├── analytics_agent.py    # Student / faculty / HoD reports
│   │   ├── notification_agent.py # WhatsApp + email alerts
│   │   └── report_agent.py       # PDF / XLSX / DOCX → Google Drive
│   └── services/
│       ├── sheets.py        # Google Sheets read/write
│       ├── auth.py          # JWT login (all 4 roles)
│       ├── llm.py           # Groq SDK wrapper
│       ├── rag.py           # ChromaDB vector store
│       ├── qr_service.py    # Rotating QR code generation
│       └── upload_service.py # CSV / Excel file uploads
├── frontend/
│   ├── login.html           # Role-based login page
│   ├── index.html           # Main dashboard
│   ├── app.js               # Dashboard logic
│   └── style.css            # Styles
├── sample_data/
│   ├── students.csv
│   ├── faculty.csv
│   ├── subjects.csv
│   ├── lesson_plan.csv
│   └── users.csv
├── deploy/gcp/
│   ├── setup.sh             # One-time GCP bootstrap
│   ├── secrets.sh           # Upload .env → Secret Manager
│   ├── deploy.sh            # Build + deploy to Cloud Run
│   └── cloudbuild.yaml      # CI/CD pipeline
├── Dockerfile               # Backend container
├── frontend/Dockerfile      # Frontend nginx container
└── pyproject.toml           # Python dependencies
```

---

## Local Setup & Run

### Prerequisites

- Python 3.11+
- Git
- A Google account with a Google Sheet
- Groq API key (free at console.groq.com)

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/dipteeghusse/smart-classroom.git
cd smart-classroom
```

---

### Step 2 — Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Mac / Linux
# .venv\Scripts\activate         # Windows
```

---

### Step 3 — Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install fastapi "uvicorn[standard]" python-multipart groq langgraph \
    chromadb sentence-transformers gspread google-auth \
    google-api-python-client mcp "qrcode[pil]" Pillow \
    reportlab openpyxl python-docx httpx python-dotenv \
    "gspread[auth]"
```

---

### Step 4 — Create .env File

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
GROQ_API_KEY=gsk_xxxx                     # console.groq.com → API Keys
GOOGLE_SHEET_ID=1BxiMVs0XRA5nFMd...       # from Sheet URL between /d/ and /edit
GOOGLE_DRIVE_FOLDER_ID=1a2B3c4D5e...      # from Drive folder URL after /folders/
SECRET_KEY=any-random-32-char-string      # run: openssl rand -hex 32
```

> **Note:** Leave `TWILIO_*` and `SENDGRID_*` blank if you don't need notifications.

---

### Step 5 — Set Up Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) → create a new sheet named **Smart Classroom DB**
2. Create these **10 tabs** (exact names required):

| Tab Name |
|----------|
| `Student Master` |
| `Faculty Master` |
| `Subject Master` |
| `Teaching Plan` |
| `Lecture Schedule` |
| `Attendance Sheet` |
| `Student Quiz Sheet` |
| `Question Bank Repository` |
| `Users` |
| `Departments` |

---

### Step 6 — Google Authentication

**Option A — OAuth2 (Recommended for local dev)**

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. APIs & Services → Credentials → **+ Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Desktop app** → Download JSON
4. Save as **`credentials.json`** in the project root folder
5. First login will open browser → sign in with the Google account that owns the Sheet → click Allow

**Option B — gcloud CLI**

```bash
gcloud auth application-default login \
  --scopes="https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/cloud-platform"
```

> **Important:** Your Google Sheet account and GCP account can be **different**.
> With Option A, sign in with whichever account owns the Sheet.

---

### Step 7 — Run the FastAPI Server

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8080
INFO:     Application startup complete.
```

Open browser → **http://localhost:8080**

---

### Step 8 — Run the MCP Server (separate terminal)

```bash
source .venv/bin/activate
python -m backend.mcp_server
```

---

### Step 9 — Login & Load Sample Data

**Demo credentials** (work even without Google Sheets):

| Role | ID | Password |
|------|----|----------|
| Student | `MIT2024001` | `student123` |
| Faculty | `FAC001` | `faculty123` |
| HoD | `HOD001` | `hod123` |
| Admin | `ADMIN001` | `admin123` |

**Upload sample data** (as Admin):
1. Login as `ADMIN001` / `admin123`
2. Go to **Upload** tab
3. Upload in this order:
   - `sample_data/users.csv`
   - `sample_data/students.csv`
   - `sample_data/faculty.csv`
   - `sample_data/subjects.csv`
   - `sample_data/lesson_plan.csv`

---

## API Endpoints

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/login` | All | Login |
| GET | `/api/auth/me` | All | Current user |
| POST | `/api/upload/students` | Admin/HoD | Upload student list |
| POST | `/api/upload/faculty` | Admin/HoD | Upload faculty list |
| POST | `/api/upload/subjects` | Admin/HoD | Upload subjects |
| POST | `/api/upload/lesson_plan` | Admin/Faculty | Upload lesson plan |
| POST | `/api/upload/users` | Admin | Upload user accounts |
| GET | `/api/students` | Admin/HoD/Faculty | List students |
| GET | `/api/faculty` | Admin/HoD | List faculty |
| GET | `/api/subjects` | All | List subjects |
| GET | `/api/lesson_plan` | All | Teaching plan |
| POST | `/api/attend` | Student | Mark attendance |
| GET | `/api/qr/{lecture_id}` | Faculty | Get QR code |
| POST | `/api/questions` | Faculty | Generate GATE questions |
| POST | `/api/quiz/evaluate` | All | Evaluate quiz |
| GET | `/api/analytics/student/{prn}` | Student/Faculty | Student report |
| GET | `/api/analytics/hod` | HoD | Department dashboard |
| POST | `/api/notify` | Faculty/HoD | Send parent alerts |
| POST | `/api/reports` | Faculty/HoD | Export reports |
| GET | `/health` | — | Health check |

---

## GCP Cloud Deployment

### Prerequisites
- gcloud CLI installed and authenticated
- Docker Desktop running
- GCP project with billing enabled

### Deploy in 4 commands

```bash
# 1. Set variables
export PROJECT_ID=your-gcp-project-id
export REGION=asia-south1
export SA_EMAIL=smart-classroom-sa@your-gcp-project-id.iam.gserviceaccount.com

# 2. Bootstrap GCP (one-time only)
bash deploy/gcp/setup.sh

# 3. Upload secrets
bash deploy/gcp/secrets.sh

# 4. Build and deploy
bash deploy/gcp/deploy.sh
```

After deploy you get two live URLs:
```
Frontend : https://smart-classroom-frontend-xxxx-el.a.run.app
Backend  : https://smart-classroom-backend-xxxx-el.a.run.app
```

### Share Sheet with Service Account

After deployment, share your Google Sheet with the service account as **Editor**:
```
smart-classroom-sa@your-gcp-project-id.iam.gserviceaccount.com
```

### Update after code changes

```bash
git add -A
git commit -m "describe your change"
git pull origin main --rebase
git push origin main
bash deploy/gcp/deploy.sh
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError` | `pip install -e .` or reinstall dependencies |
| `APIError 403: insufficient scopes` | Re-run `gcloud auth application-default login --scopes=...` |
| `PermissionError` on Sheets | Share the Sheet with your service account or personal account |
| `GOOGLE_SHEET_ID not set` | Check `.env` has correct Sheet ID |
| `Port 8080 in use` | Use `--port 8000` instead |
| `zsh: no matches found: qrcode[pil]` | Use quotes: `pip install "qrcode[pil]"` |
| `Failed to fetch` | Check server is running; open http://localhost:8080/health |
| Google account mismatch | Use `credentials.json` and sign in with the account that owns the Sheet |

---

## Cost (GCP — approximate)

| Service | $/month |
|---------|---------|
| Cloud Run (backend) | ~$5 |
| Cloud Run (frontend) | ~$1 |
| Secret Manager | ~$0.1 |
| Cloud Storage | ~$0.02 |
| **Total** | **~$7/month** |

Scales to zero when not in use.

---

## Repository

**GitHub:** https://github.com/dipteeghusse/smart-classroom
