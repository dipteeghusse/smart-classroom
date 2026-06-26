"""
main.py — FastAPI backend entry point.

All endpoints delegate to orchestrator.invoke() which routes through
the LangGraph supervisor to the correct agent.

Run locally:
  uvicorn backend.main:app --reload --port 8080

Endpoints:
  POST /api/attend           — mark attendance (QR + GPS)
  GET  /api/qr/{lecture_id}  — get rotating QR code
  POST /api/questions        — generate GATE questions for a topic
  POST /api/quiz/evaluate    — score a quiz submission
  GET  /api/analytics/student/{prn}  — student report
  GET  /api/analytics/faculty/{id}   — faculty report
  GET  /api/analytics/hod            — HoD dashboard
  POST /api/notify           — send parent alerts
  POST /api/reports          — export report to Drive
  GET  /health               — health check
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

from backend import orchestrator
from backend.services.qr_service import generate_qr

app = FastAPI(
    title="Smart Classroom AI",
    description="AI-Powered Smart Classroom — MITAOE CSE (AI & ML)",
    version="1.0.0",
)

# Allow the frontend (any origin in dev, lock down in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ────────────────────────────────────────────────────────────

class AttendanceRequest(BaseModel):
    lecture_id:     str
    lecture_number: int
    subject_code:   str
    date:           str
    student_prn:    str
    student_name:   str
    qr_token:       str
    student_lat:    float
    student_lon:    float
    classroom_lat:  float
    classroom_lon:  float

class QuestionRequest(BaseModel):
    subject_code:  str
    unit:          int
    topic:         str
    topic_number:  str
    co_mapping:    str = "CO1"
    blooms_level:  str = "Apply"

class QuizEvalRequest(BaseModel):
    student_prn:    str
    student_name:   str
    subject_code:   str
    topic_number:   str
    lecture_number: int
    answers:        list[dict]   # [{ question_id, selected }]
    answer_key:     dict         # { question_id: "A"|"B"|"C"|"D" }
    date:           Optional[str] = None
    time_taken_seconds: int = 0

class NotifyRequest(BaseModel):
    subject_code:  str = ""
    faculty_email: str = "faculty@mitaoe.ac.in"
    students:      Optional[list[dict]] = None  # auto-detect if None

class ReportRequest(BaseModel):
    report_type: str              # attendance | quiz | teaching_plan | question_bank
    formats:     list[str] = ["pdf", "xlsx"]
    title:       Optional[str] = None


# ── Attendance ─────────────────────────────────────────────────────────────────

@app.post("/api/attend")
def mark_attendance(req: AttendanceRequest):
    try:
        return orchestrator.invoke("attendance", req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/qr/{lecture_id}")
def get_qr(lecture_id: str):
    """Returns QR token metadata + base64 PNG image."""
    return generate_qr(lecture_id)


# ── Questions & Quiz ──────────────────────────────────────────────────────────

@app.post("/api/questions")
def generate_questions(req: QuestionRequest):
    try:
        return orchestrator.invoke("question_gen", req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quiz/evaluate")
def evaluate_quiz(req: QuizEvalRequest):
    try:
        return orchestrator.invoke("quiz_eval", req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.get("/api/analytics/student/{prn}")
def student_analytics(prn: str):
    try:
        return orchestrator.invoke("student_analytics", {"student_prn": prn})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/faculty/{faculty_id}")
def faculty_analytics(faculty_id: str):
    try:
        return orchestrator.invoke("faculty_analytics", {"faculty_id": faculty_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/hod")
def hod_dashboard():
    try:
        return orchestrator.invoke("hod_dashboard", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Notifications ─────────────────────────────────────────────────────────────

@app.post("/api/notify")
def notify_parents(req: NotifyRequest):
    try:
        return orchestrator.invoke("notify_parents", req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Reports ───────────────────────────────────────────────────────────────────

@app.post("/api/reports")
def generate_report(req: ReportRequest):
    try:
        return orchestrator.invoke("generate_report", req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "smart-classroom-ai"}


# ── Serve frontend from /frontend ─────────────────────────────────────────────

_FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_FRONTEND):
    app.mount("/static", StaticFiles(directory=_FRONTEND), name="static")

    @app.get("/")
    def root():
        return FileResponse(os.path.join(_FRONTEND, "index.html"))
