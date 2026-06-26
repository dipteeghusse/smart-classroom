"""
config.py — All environment variables in one place.
Copy .env.example to .env and fill in your values.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Groq LLM ──────────────────────────────────────────────────────────────────
GROQ_API_KEY       = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL         = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Google Sheets ─────────────────────────────────────────────────────────────
SPREADSHEET_ID     = os.getenv("GOOGLE_SPREADSHEET_ID", "")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")

# ── ChromaDB (RAG) ────────────────────────────────────────────────────────────
CHROMA_PATH        = os.getenv("CHROMA_PATH", "./data/chromadb")

# ── Notifications ─────────────────────────────────────────────────────────────
TWILIO_SID         = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN       = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WA_FROM     = os.getenv("TWILIO_WHATSAPP_FROM", "")
SENDGRID_KEY       = os.getenv("SENDGRID_API_KEY", "")
EMAIL_FROM         = os.getenv("EMAIL_FROM", "noreply@mitaoe.ac.in")

# ── App ───────────────────────────────────────────────────────────────────────
APP_HOST           = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT           = int(os.getenv("APP_PORT", "8080"))
SECRET_KEY         = os.getenv("SECRET_KEY", "change-me")
MCP_PORT           = int(os.getenv("MCP_PORT", "9000"))

# ── Google Shared Drive ───────────────────────────────────────────────────────
SHARED_DRIVE_ID    = os.getenv("GOOGLE_SHARED_DRIVE_ID", "")

# Sheet tab names — must match your spreadsheet exactly
SHEET_TABS = {
    "students":        "Student Master",
    "faculty":         "Faculty Master",
    "subjects":        "Subject Master",
    "teaching_plan":   "Teaching Plan",
    "lectures":        "Lecture Schedule",
    "attendance":      "Attendance Sheet",
    "quiz":            "Student Quiz Sheet",
    "question_bank":   "Question Bank Repository",
}
