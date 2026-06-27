"""
services/upload_service.py — Parse uploaded CSV/Excel files and push to Google Sheets.

Supported upload types:
  students       → Student Master sheet
  faculty        → Faculty Master sheet
  subjects       → Subject Master sheet
  lesson_plan    → Teaching Plan sheet
  users          → Users sheet (for login accounts)

File formats accepted: .csv  .xlsx  .xls
"""
import io
import csv
import openpyxl
from backend.services.sheets import SheetsService
from backend.services.auth import hash_password

# ── Expected column headers per upload type ───────────────────────────────────

HEADERS = {
    "students": [
        "PRN/Roll Number", "Student Name", "Department", "Program",
        "Semester", "Class", "Division", "Batch",
        "Mobile Number", "Parent Mobile", "Parent Email", "WhatsApp Number",
    ],
    "faculty": [
        "Faculty ID", "Faculty Name", "Department", "Subject",
        "Course", "Semester", "Mobile Number", "Email",
    ],
    "subjects": [
        "Subject Code", "Subject Name", "Department", "Course",
        "Semester", "Credits", "Faculty Assigned",
    ],
    "lesson_plan": [
        "Subject Code", "Unit Number", "Topic Number", "Topic Name",
        "Planned Date", "Planned Hours", "Course Outcome",
        "Blooms Level", "Status",
    ],
    "users": [
        "ID", "Name", "Role", "Department", "Class", "Division", "Password_Hash",
    ],
}

# Map upload type → sheet tab key
SHEET_MAP = {
    "students":    "students",
    "faculty":     "faculty",
    "subjects":    "subjects",
    "lesson_plan": "teaching_plan",
    "users":       "users",
}


def _read_file(filename: str, content: bytes) -> list[list[str]]:
    """Parse CSV or Excel bytes into a list of rows (each row = list of strings)."""
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "csv":
        text = content.decode("utf-8-sig")           # handle BOM
        reader = csv.reader(io.StringIO(text))
        return [row for row in reader if any(cell.strip() for cell in row)]

    elif ext in ("xlsx", "xls"):
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            if any(c.strip() for c in cells):
                rows.append(cells)
        return rows

    else:
        raise ValueError(f"Unsupported file type: .{ext}  (use .csv or .xlsx)")


def _validate_headers(file_rows: list[list], upload_type: str) -> list[list]:
    """
    Check that the first row matches expected headers (case-insensitive).
    Returns data rows (skipping the header row).
    Raises ValueError with a clear message if headers are wrong.
    """
    if not file_rows:
        raise ValueError("File is empty")

    expected = [h.lower() for h in HEADERS[upload_type]]
    actual   = [h.strip().lower() for h in file_rows[0]]

    missing = [h for h in expected if h not in actual]
    if missing:
        raise ValueError(
            f"Missing columns: {missing}\n"
            f"Expected: {HEADERS[upload_type]}\n"
            f"Got:      {file_rows[0]}"
        )

    return file_rows[1:]   # skip header row


def process_upload(filename: str, content: bytes, upload_type: str) -> dict:
    """
    Main entry point called by the API endpoint.

    upload_type: students | faculty | subjects | lesson_plan | users
    Returns: { inserted, skipped, errors }
    """
    if upload_type not in HEADERS:
        raise ValueError(f"Unknown upload type: {upload_type}")

    rows      = _read_file(filename, content)
    data_rows = _validate_headers(rows, upload_type)

    sheets   = SheetsService()
    tab      = SHEET_MAP[upload_type]
    inserted = 0
    skipped  = 0
    errors   = []

    for i, row in enumerate(data_rows, start=2):   # row 2 is first data row
        try:
            # For users upload: hash the plain-text password in the last column
            if upload_type == "users" and len(row) >= 7:
                plain_pw = row[6].strip()
                if plain_pw and not len(plain_pw) == 64:   # not already hashed
                    row = list(row)
                    row[6] = hash_password(plain_pw)

            # Skip completely empty rows
            if not any(str(c).strip() for c in row):
                skipped += 1
                continue

            sheets.append(tab, row)
            inserted += 1

        except Exception as e:
            msg = str(e)
            # WorksheetNotFound stringifies to just the tab name — make it clear
            if msg in ("Users", "Student Master", "Faculty Master",
                       "Subject Master", "Teaching Plan", "Lecture Schedule",
                       "Attendance Sheet", "Student Quiz Sheet",
                       "Question Bank Repository", "Departments"):
                msg = (f"Sheet tab '{msg}' not found. Open your Google Sheet "
                       f"and create a tab with that exact name, then retry. "
                       f"Or run: python setup_sheets.py")
            errors.append({"row": i, "error": msg})

    return {
        "upload_type": upload_type,
        "filename":    filename,
        "inserted":    inserted,
        "skipped":     skipped,
        "errors":      errors,
    }
