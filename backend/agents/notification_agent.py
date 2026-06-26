"""
agents/notification_agent.py — Parent notification via WhatsApp and Email.

Automatically identifies at-risk students (attendance < 75%) and
sends alerts to their parents through WhatsApp (Twilio) and Email (SendGrid).
"""
import httpx
from twilio.rest import Client as Twilio
from backend.services.sheets import SheetsService
from backend.config import (
    TWILIO_SID, TWILIO_TOKEN, TWILIO_WA_FROM,
    SENDGRID_KEY, EMAIL_FROM,
)

ATTENDANCE_THRESHOLD = 75.0   # alert if attendance drops below this

WA_MESSAGE = """📚 *MITAOE Academic Alert*

Student: *{name}* (PRN: {prn})
Subject: *{subject}*
Attendance: *{att_pct}%* ⚠️

{message}

Please contact: {faculty_email}
— AI Smart Classroom, MITAOE"""


def _send_whatsapp(to: str, text: str) -> bool:
    """Send WhatsApp message via Twilio. Returns True on success."""
    if not TWILIO_SID:
        return False
    try:
        client = Twilio(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(
            from_=f"whatsapp:{TWILIO_WA_FROM}",
            to=f"whatsapp:{to}",
            body=text,
        )
        return True
    except Exception as e:
        print(f"[WhatsApp] Failed for {to}: {e}")
        return False


def _send_email(to: str, subject: str, body_html: str) -> bool:
    """Send email via SendGrid HTTP API. Returns True on success."""
    if not SENDGRID_KEY:
        return False
    try:
        resp = httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {SENDGRID_KEY}"},
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": EMAIL_FROM},
                "subject": subject,
                "content": [{"type": "text/html", "value": body_html}],
            },
            timeout=10,
        )
        return resp.status_code in (200, 202)
    except Exception as e:
        print(f"[Email] Failed for {to}: {e}")
        return False


def run(payload: dict) -> dict:
    """
    payload keys:
      subject_code, faculty_email
      students (optional): list of { prn, name, parent_whatsapp, parent_email }
                           — if omitted, auto-detect at-risk students from Sheets
    Returns:
      { notified: int, results: [...] }
    """
    sheets   = SheetsService()
    subject  = payload.get("subject_code", "All Subjects")
    f_email  = payload.get("faculty_email", "faculty@mitaoe.ac.in")

    students = payload.get("students")

    # Auto-detect at-risk students if none provided
    if not students:
        students = []
        for s in sheets.read_all("students"):
            prn = str(s.get("PRN/Roll Number", ""))
            records = sheets.get_student_attendance(prn)
            if not records:
                continue
            present = sum(1 for r in records if r.get("Attendance") == "Present")
            att_pct = round((present / len(records)) * 100, 2)
            if att_pct < ATTENDANCE_THRESHOLD:
                students.append({
                    "prn":             prn,
                    "name":            s.get("Student Name", ""),
                    "parent_whatsapp": s.get("WhatsApp Number", ""),
                    "parent_email":    s.get("Parent Email", ""),
                    "att_pct":         att_pct,
                })

    results = []
    for s in students:
        msg = WA_MESSAGE.format(
            name=s["name"], prn=s["prn"], subject=subject,
            att_pct=s.get("att_pct", 0),
            message="Attendance is below 75%. Immediate improvement required.",
            faculty_email=f_email,
        )
        wa_ok    = _send_whatsapp(s["parent_whatsapp"], msg)
        email_ok = _send_email(
            to=s["parent_email"],
            subject=f"MITAOE Alert: {s['name']} Attendance Warning",
            body_html=f"<pre>{msg}</pre>",
        )
        results.append({"prn": s["prn"], "whatsapp": wa_ok, "email": email_ok})

    return {"notified": len(results), "results": results}
