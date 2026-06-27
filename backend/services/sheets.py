"""
services/sheets.py — Google Sheets service.

Single responsibility: read from and write to the 8 Google Sheet modules.
All agents call this service; no agent talks to Sheets directly.
"""
import json
import gspread
import google.auth
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from backend.config import GOOGLE_CREDS_JSON, SPREADSHEET_ID, SHEET_TABS

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_credentials():
    """
    Credential resolution order:
    1. GOOGLE_CREDS_JSON env var  — inline SA JSON (CI / Cloud Run)
    2. credentials.json file      — OAuth2 Desktop app (local dev, no gcloud needed)
    3. ADC                        — gcloud auth application-default login (with --scopes)
    """
    if GOOGLE_CREDS_JSON:
        info = json.loads(GOOGLE_CREDS_JSON)
        return Credentials.from_service_account_info(info, scopes=_SCOPES)

    # OAuth2 file — download from GCP Console → APIs & Services → Credentials
    import os
    oauth_file = os.path.join(os.path.dirname(__file__), "..", "..", "credentials.json")
    if os.path.exists(oauth_file):
        return gspread.oauth(credentials_filename=oauth_file, scopes=_SCOPES)

    # ADC fallback — requires: gcloud auth application-default login --scopes=...
    creds, _ = google.auth.default(scopes=_SCOPES)
    if hasattr(creds, "refresh"):
        creds.refresh(Request())
    return creds


class SheetsService:
    """Thin wrapper around gspread for the classroom spreadsheet."""

    def __init__(self):
        creds = _get_credentials()
        # gspread.oauth() returns a gspread.Client directly; others return Credentials
        if isinstance(creds, gspread.Client):
            client = creds
        else:
            client = gspread.authorize(creds)
        self._wb = client.open_by_key(SPREADSHEET_ID)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _tab(self, key: str) -> gspread.Worksheet:
        return self._wb.worksheet(SHEET_TABS[key])

    # ── Generic read / write ──────────────────────────────────────────────────

    def read_all(self, tab: str) -> list[dict]:
        """Return all rows of a sheet as a list of dicts."""
        return self._tab(tab).get_all_records()

    def append(self, tab: str, row: list) -> None:
        """Append one row to a sheet."""
        self._tab(tab).append_row(row, value_input_option="USER_ENTERED")

    def update_row(self, tab: str, match_col: str, match_val: str, changes: dict) -> bool:
        """Find the first row where match_col == match_val and apply changes dict."""
        ws = self._tab(tab)
        headers = ws.row_values(1)
        records = ws.get_all_records()

        for idx, rec in enumerate(records, start=2):   # row 1 is header
            if str(rec.get(match_col, "")) == str(match_val):
                for col_name, new_val in changes.items():
                    col_idx = headers.index(col_name) + 1
                    ws.update_cell(idx, col_idx, new_val)
                return True
        return False

    # ── Domain-specific writes ────────────────────────────────────────────────

    def mark_attendance(self, date, lecture_no, subject, prn, name,
                        status, scan_time, gps, qr_ok):
        self.append("attendance", [
            date, lecture_no, subject, prn, name,
            status, scan_time, gps, qr_ok,
        ])

    def save_quiz_result(self, date, lecture_no, subject, topic_no,
                         prn, name, attempt, score, total, pct, time_s, count):
        self.append("quiz", [
            date, lecture_no, subject, topic_no,
            prn, name, attempt, score, total, pct, time_s, count,
        ])

    def save_question(self, q: dict) -> None:
        self.append("question_bank", [
            q["id"], q["subject"], q["unit"], q["topic"],
            q["difficulty"], q["blooms"], q["co"],
            q["type"], q["question"],
            q["a"], q["b"], q["c"], q["d"],
            q["answer"], q["explanation"], q["source"],
        ])

    def get_student_attendance(self, prn: str) -> list[dict]:
        return [r for r in self.read_all("attendance")
                if str(r.get("Student PRN")) == str(prn)]

    def get_student_quiz_scores(self, prn: str) -> list[dict]:
        return [r for r in self.read_all("quiz")
                if str(r.get("Student PRN")) == str(prn)]

    def get_completed_topics(self) -> list[dict]:
        return [r for r in self.read_all("teaching_plan")
                if r.get("Status") == "Completed"]

    def complete_topic(self, topic_no: str, actual_date: str, done_hrs: float) -> bool:
        return self.update_row(
            "teaching_plan", "Topic Number", topic_no,
            {"Status": "Completed", "Actual Date": actual_date,
             "Completed Hours": done_hrs},
        )
