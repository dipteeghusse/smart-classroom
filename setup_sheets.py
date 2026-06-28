"""
setup_sheets.py — Create all 10 required tabs in your Google Sheet.

Run once before uploading any data:
    python setup_sheets.py

It will:
  • Create any missing tabs with the exact names expected by the app
  • Add header rows to each tab
  • Skip tabs that already exist
"""
import sys
import os

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend.services.sheets import SheetsService

TABS = {
    "Student Master": [
        "PRN/Roll Number", "Student Name", "Department", "Program",
        "Semester", "Class", "Division", "Batch",
        "Mobile Number", "Parent Mobile", "Parent Email", "WhatsApp Number",
    ],
    "Faculty Master": [
        "Faculty ID", "Faculty Name", "Department", "Subject",
        "Course", "Semester", "Mobile Number", "Email",
    ],
    "Subject Master": [
        "Subject Code", "Subject Name", "Department", "Course",
        "Semester", "Credits", "Faculty Assigned",
    ],
    "Teaching Plan": [
        "Subject Code", "Unit Number", "Topic Number", "Topic Name",
        "Planned Date", "Planned Hours", "Course Outcome",
        "Blooms Level", "Status", "Actual Date", "Completed Hours",
    ],
    "Lecture Schedule": [
        "Lecture ID", "Subject Code", "Faculty ID", "Date",
        "Start Time", "End Time", "Classroom", "Topic Number", "QR Token",
    ],
    "Attendance Sheet": [
        "Date", "Lecture Number", "Subject", "Student PRN", "Student Name",
        "Attendance", "Scan Time", "GPS", "QR Valid",
    ],
    "Student Quiz Sheet": [
        "Date", "Lecture Number", "Subject Code", "Topic Number",
        "Student PRN", "Student Name", "Attempt", "Score", "Total",
        "Percentage", "Time Taken (s)", "Questions Count",
    ],
    "Question Bank Repository": [
        "Question ID", "Subject", "Unit", "Topic", "Difficulty",
        "Blooms Level", "Course Outcome", "Type", "Question",
        "Option A", "Option B", "Option C", "Option D",
        "Answer", "Explanation", "Source",
    ],
    "Users": [
        "ID", "Name", "Role", "Department", "Class", "Division",
        "Email", "Password_Hash", "Must_Reset",
    ],
    "Departments": [
        "Department Code", "Department Name", "HoD ID", "Faculty Count",
    ],
}


def main():
    print("Connecting to Google Sheets …")
    try:
        svc = SheetsService()
        wb  = svc._wb
    except Exception as e:
        print(f"ERROR: Could not connect — {e}")
        print("\nMake sure:")
        print("  1. GOOGLE_SHEET_ID is set in your .env")
        print("  2. You ran: gcloud auth application-default login --scopes=...")
        print("     or placed credentials.json in the project root")
        sys.exit(1)

    existing = {ws.title for ws in wb.worksheets()}
    print(f"Existing tabs: {sorted(existing)}\n")

    for tab_name, headers in TABS.items():
        if tab_name in existing:
            print(f"  ✓  {tab_name!r} — already exists, skipping")
        else:
            ws = wb.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
            ws.append_row(headers, value_input_option="USER_ENTERED")
            print(f"  +  {tab_name!r} — created with {len(headers)} columns")

    print("\nDone! All required tabs are ready.")
    print("You can now upload sample data from the Admin dashboard.")


if __name__ == "__main__":
    main()
