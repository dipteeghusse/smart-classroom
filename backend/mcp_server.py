"""
mcp_server.py — Model Context Protocol server.

Exposes classroom tools so any MCP-compatible LLM client
(Claude Desktop, Cursor, etc.) can call them directly.

Run standalone:
  python -m backend.mcp_server

Tools exposed:
  1. read_sheet         — read any of the 8 Google Sheet modules
  2. mark_attendance    — mark one student's attendance
  3. generate_qr        — create a rotating QR code for a lecture
  4. generate_questions — produce GATE-level questions for a topic
  5. evaluate_quiz      — score a student quiz submission
  6. student_analytics  — get attendance + quiz analytics for a student
  7. hod_dashboard      — department-level KPIs for the HoD
  8. notify_parents     — send WhatsApp + email alerts to parents
  9. generate_report    — export a report to PDF/XLSX/DOCX on Drive
"""
import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from backend.services.sheets import SheetsService
from backend.services.qr_service import generate_qr
from backend.agents import (
    attendance_agent,
    question_agent,
    quiz_agent,
    analytics_agent,
    notification_agent,
    report_agent,
)

app = Server("smart-classroom")

# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
    Tool(
        name="read_sheet",
        description="Read all records from one of the 8 Google Sheet modules",
        inputSchema={
            "type": "object",
            "required": ["tab"],
            "properties": {
                "tab": {
                    "type": "string",
                    "enum": ["students","faculty","subjects","teaching_plan",
                             "lectures","attendance","quiz","question_bank"],
                    "description": "Which sheet tab to read",
                }
            },
        },
    ),
    Tool(
        name="mark_attendance",
        description="Verify QR + GPS and mark a student's attendance in Google Sheets",
        inputSchema={
            "type": "object",
            "required": ["lecture_id","lecture_number","subject_code","date",
                         "student_prn","student_name","qr_token",
                         "student_lat","student_lon","classroom_lat","classroom_lon"],
            "properties": {
                "lecture_id":     {"type": "string"},
                "lecture_number": {"type": "integer"},
                "subject_code":   {"type": "string"},
                "date":           {"type": "string"},
                "student_prn":    {"type": "string"},
                "student_name":   {"type": "string"},
                "qr_token":       {"type": "string"},
                "student_lat":    {"type": "number"},
                "student_lon":    {"type": "number"},
                "classroom_lat":  {"type": "number"},
                "classroom_lon":  {"type": "number"},
            },
        },
    ),
    Tool(
        name="generate_qr",
        description="Generate a rotating QR code (valid 60 s) for a lecture",
        inputSchema={
            "type": "object",
            "required": ["lecture_id"],
            "properties": {"lecture_id": {"type": "string"}},
        },
    ),
    Tool(
        name="generate_questions",
        description="Generate GATE-level MCQs for a completed topic using RAG + Groq",
        inputSchema={
            "type": "object",
            "required": ["subject_code","unit","topic","topic_number"],
            "properties": {
                "subject_code":  {"type": "string"},
                "unit":          {"type": "integer"},
                "topic":         {"type": "string"},
                "topic_number":  {"type": "string"},
                "co_mapping":    {"type": "string", "default": "CO1"},
                "blooms_level":  {"type": "string", "default": "Apply"},
            },
        },
    ),
    Tool(
        name="evaluate_quiz",
        description="Score a student's quiz and save the result to Sheets",
        inputSchema={
            "type": "object",
            "required": ["student_prn","student_name","subject_code",
                         "topic_number","lecture_number","answers","answer_key"],
            "properties": {
                "student_prn":    {"type": "string"},
                "student_name":   {"type": "string"},
                "subject_code":   {"type": "string"},
                "topic_number":   {"type": "string"},
                "lecture_number": {"type": "integer"},
                "answers":        {"type": "array",  "description": "[{question_id, selected}]"},
                "answer_key":     {"type": "object", "description": "{question_id: correct_option}"},
            },
        },
    ),
    Tool(
        name="student_analytics",
        description="Get attendance %, quiz scores, weak topics and GATE readiness for a student",
        inputSchema={
            "type": "object",
            "required": ["student_prn"],
            "properties": {"student_prn": {"type": "string"}},
        },
    ),
    Tool(
        name="hod_dashboard",
        description="Get department-level KPIs: attendance, syllabus coverage, GATE index",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="notify_parents",
        description="Send WhatsApp + email alerts to parents of at-risk students",
        inputSchema={
            "type": "object",
            "properties": {
                "subject_code":  {"type": "string"},
                "faculty_email": {"type": "string"},
            },
        },
    ),
    Tool(
        name="generate_report",
        description="Export a Google Sheet as PDF/XLSX/DOCX to Google Shared Drive",
        inputSchema={
            "type": "object",
            "required": ["report_type"],
            "properties": {
                "report_type": {
                    "type": "string",
                    "enum": ["attendance","quiz","teaching_plan","question_bank"],
                },
                "formats": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["pdf","xlsx","docx"]},
                    "default": ["pdf","xlsx"],
                },
            },
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


# ── Tool execution ────────────────────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, args: dict) -> list[TextContent]:
    def respond(data) -> list[TextContent]:
        return [TextContent(type="text", text=json.dumps(data, indent=2))]

    if name == "read_sheet":
        sheets  = SheetsService()
        records = sheets.read_all(args["tab"])
        return respond(records[:50])             # cap to 50 rows for context size

    if name == "mark_attendance":
        result = attendance_agent.run(args)
        return respond(result)

    if name == "generate_qr":
        result = generate_qr(args["lecture_id"])
        # Don't return the raw base64 image bytes — just metadata
        return respond({k: v for k, v in result.items() if k != "image_b64"})

    if name == "generate_questions":
        result = question_agent.run(args)
        # Omit full question list from context (it's in Sheets)
        return respond({k: v for k, v in result.items() if k != "questions"})

    if name == "evaluate_quiz":
        result = quiz_agent.run(args)
        return respond(result)

    if name == "student_analytics":
        result = analytics_agent.student_report(args["student_prn"])
        return respond(result)

    if name == "hod_dashboard":
        result = analytics_agent.hod_dashboard()
        return respond(result)

    if name == "notify_parents":
        result = notification_agent.run(args)
        return respond(result)

    if name == "generate_report":
        result = report_agent.run(args)
        return respond(result)

    return respond({"error": f"Unknown tool: {name}"})


# ── Entry point ───────────────────────────────────────────────────────────────

async def _run():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_run())
