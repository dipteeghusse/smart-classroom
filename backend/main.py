"""
main.py — FastAPI backend.

Endpoints:
  AUTH
    POST /api/auth/login               — login (all roles)
    GET  /api/auth/me                  — get current user from token

  UPLOADS  (admin / faculty only)
    POST /api/upload/students          — upload student list CSV/Excel
    POST /api/upload/faculty           — upload faculty list
    POST /api/upload/subjects          — upload subject/course list
    POST /api/upload/lesson_plan       — upload teaching/lesson plan
    POST /api/upload/users             — upload user accounts (admin only)

  DATA (read — filtered by role in responses)
    GET  /api/students                 — list students (admin/hod/faculty)
    GET  /api/students/{prn}           — one student (student sees only own)
    GET  /api/faculty                  — list faculty
    GET  /api/subjects                 — subject/course list
    GET  /api/lesson_plan              — teaching plan
    GET  /api/lesson_plan/{subject}    — lesson plan for one subject

  ATTENDANCE
    POST /api/attend                   — mark attendance
    GET  /api/qr/{lecture_id}          — get rotating QR

  QUESTIONS & QUIZ
    POST /api/questions                — generate GATE questions
    POST /api/quiz/evaluate            — score a quiz

  ANALYTICS
    GET  /api/analytics/student/{prn}  — student report
    GET  /api/analytics/faculty/{id}   — faculty report
    GET  /api/analytics/hod            — HoD dashboard

  NOTIFICATIONS & REPORTS
    POST /api/notify                   — parent alerts
    POST /api/reports                  — export to Drive

  HEALTH
    GET  /health
"""
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

from backend import orchestrator
from backend.services.qr_service  import generate_qr
from backend.services.auth        import login, get_current_user
from backend.services.upload_service import process_upload
from backend.services.sheets      import SheetsService

app = FastAPI(title="Smart Classroom AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth helpers ──────────────────────────────────────────────────────────────

def require_auth(authorization: str = Header(...)) -> dict:
    try:
        return get_current_user(authorization)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

def require_role(user: dict, *roles: str):
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail=f"Requires role: {list(roles)}")

# ── Request models ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    user_id:  str
    password: str

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
    answers:        list[dict]
    answer_key:     dict
    date:           Optional[str] = None
    time_taken_seconds: int = 0

class NotifyRequest(BaseModel):
    subject_code:  str = ""
    faculty_email: str = "faculty@mitaoe.ac.in"
    students:      Optional[list[dict]] = None

class ReportRequest(BaseModel):
    report_type: str
    formats:     list[str] = ["pdf", "xlsx"]
    title:       Optional[str] = None

# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.post("/api/auth/login")
def auth_login(req: LoginRequest):
    try:
        return login(req.user_id, req.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/api/auth/me")
def auth_me(authorization: str = Header(...)):
    return require_auth(authorization)

# ── UPLOADS ───────────────────────────────────────────────────────────────────

async def _handle_upload(file: UploadFile, upload_type: str,
                         authorization: str, allowed_roles: tuple):
    user = require_auth(authorization)
    require_role(user, *allowed_roles)
    content = await file.read()
    try:
        return process_upload(file.filename, content, upload_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.post("/api/upload/students")
async def upload_students(
    file: UploadFile = File(...),
    authorization: str = Header(...),
):
    return await _handle_upload(file, "students", authorization, ("admin", "hod"))

@app.post("/api/upload/faculty")
async def upload_faculty(
    file: UploadFile = File(...),
    authorization: str = Header(...),
):
    return await _handle_upload(file, "faculty", authorization, ("admin", "hod"))

@app.post("/api/upload/subjects")
async def upload_subjects(
    file: UploadFile = File(...),
    authorization: str = Header(...),
):
    return await _handle_upload(file, "subjects", authorization, ("admin", "hod"))

@app.post("/api/upload/lesson_plan")
async def upload_lesson_plan(
    file: UploadFile = File(...),
    authorization: str = Header(...),
):
    return await _handle_upload(file, "lesson_plan", authorization, ("admin", "faculty", "hod"))

@app.post("/api/upload/users")
async def upload_users(
    file: UploadFile = File(...),
    authorization: str = Header(...),
):
    return await _handle_upload(file, "users", authorization, ("admin",))

# ── DATA READS ────────────────────────────────────────────────────────────────

@app.get("/api/students")
def get_students(authorization: str = Header(...)):
    user = require_auth(authorization)
    require_role(user, "admin", "hod", "faculty")
    sheets = SheetsService()
    return sheets.read_all("students")

@app.get("/api/students/{prn}")
def get_student(prn: str, authorization: str = Header(...)):
    user = require_auth(authorization)
    # Students can only see their own record
    if user["role"] == "student" and user["id"] != prn:
        raise HTTPException(status_code=403, detail="Access denied")
    sheets = SheetsService()
    all_students = sheets.read_all("students")
    record = next((s for s in all_students
                   if str(s.get("PRN/Roll Number", "")) == prn), None)
    if not record:
        raise HTTPException(status_code=404, detail="Student not found")
    return record

@app.get("/api/faculty")
def get_faculty(authorization: str = Header(...)):
    user = require_auth(authorization)
    require_role(user, "admin", "hod", "faculty")
    sheets = SheetsService()
    return sheets.read_all("faculty")

@app.get("/api/subjects")
def get_subjects(authorization: str = Header(...)):
    require_auth(authorization)   # all roles can view subjects
    sheets = SheetsService()
    records = sheets.read_all("subjects")
    user = get_current_user(authorization[7:]) if authorization.startswith("Bearer ") else {}
    # Faculty see only their own subjects
    if user.get("role") == "faculty":
        fid = user.get("id", "")
        records = [r for r in records
                   if str(r.get("Faculty Assigned", "")).strip() == fid]
    return records

@app.get("/api/lesson_plan")
def get_lesson_plan(authorization: str = Header(...)):
    require_auth(authorization)
    sheets = SheetsService()
    return sheets.read_all("teaching_plan")

@app.get("/api/lesson_plan/{subject_code}")
def get_lesson_plan_by_subject(subject_code: str, authorization: str = Header(...)):
    require_auth(authorization)
    sheets = SheetsService()
    return [r for r in sheets.read_all("teaching_plan")
            if str(r.get("Subject Code", "")).upper() == subject_code.upper()]

# ── ATTENDANCE ────────────────────────────────────────────────────────────────

@app.post("/api/attend")
def mark_attendance(req: AttendanceRequest, authorization: str = Header(...)):
    user = require_auth(authorization)
    require_role(user, "student", "faculty", "admin")
    try:
        return orchestrator.invoke("attendance", req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/qr/{lecture_id}")
def get_qr(lecture_id: str, authorization: str = Header(...)):
    user = require_auth(authorization)
    require_role(user, "faculty", "admin")
    return generate_qr(lecture_id)

# ── QUESTIONS & QUIZ ──────────────────────────────────────────────────────────

@app.post("/api/questions")
def generate_questions(req: QuestionRequest, authorization: str = Header(...)):
    user = require_auth(authorization)
    require_role(user, "faculty", "admin", "hod")
    try:
        return orchestrator.invoke("question_gen", req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/quiz/evaluate")
def evaluate_quiz(req: QuizEvalRequest, authorization: str = Header(...)):
    require_auth(authorization)
    try:
        return orchestrator.invoke("quiz_eval", req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── ANALYTICS ─────────────────────────────────────────────────────────────────

@app.get("/api/analytics/student/{prn}")
def student_analytics(prn: str, authorization: str = Header(...)):
    user = require_auth(authorization)
    if user["role"] == "student" and user["id"] != prn:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return orchestrator.invoke("student_analytics", {"student_prn": prn})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/faculty/{faculty_id}")
def faculty_analytics(faculty_id: str, authorization: str = Header(...)):
    user = require_auth(authorization)
    require_role(user, "faculty", "hod", "admin")
    try:
        return orchestrator.invoke("faculty_analytics", {"faculty_id": faculty_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/hod")
def hod_dashboard(authorization: str = Header(...)):
    user = require_auth(authorization)
    require_role(user, "hod", "admin")
    try:
        return orchestrator.invoke("hod_dashboard", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── NOTIFICATIONS & REPORTS ───────────────────────────────────────────────────

@app.post("/api/notify")
def notify_parents(req: NotifyRequest, authorization: str = Header(...)):
    user = require_auth(authorization)
    require_role(user, "faculty", "hod", "admin")
    try:
        return orchestrator.invoke("notify_parents", req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reports")
def generate_report(req: ReportRequest, authorization: str = Header(...)):
    user = require_auth(authorization)
    require_role(user, "faculty", "hod", "admin")
    try:
        return orchestrator.invoke("generate_report", req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── HEALTH ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "smart-classroom-ai"}

# ── Serve frontend ────────────────────────────────────────────────────────────

_FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_FRONTEND):
    app.mount("/static", StaticFiles(directory=_FRONTEND), name="static")

    @app.get("/")
    def root():
        return FileResponse(os.path.join(_FRONTEND, "login.html"))

    @app.get("/dashboard")
    def dashboard():
        return FileResponse(os.path.join(_FRONTEND, "index.html"))
