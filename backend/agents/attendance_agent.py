"""
agents/attendance_agent.py — Handles the full attendance workflow.

Steps:
  1. Verify QR token (time-based HMAC)
  2. Verify GPS geofence (student within 100 m of classroom)
  3. Mark attendance in Google Sheets
  4. Return result to caller
"""
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from backend.services.sheets import SheetsService
from backend.services.qr_service import verify_qr

GEOFENCE_RADIUS_M = 100    # students must be within 100 metres


def _distance_metres(lat1, lon1, lat2, lon2) -> float:
    """Haversine formula — returns distance in metres between two GPS points."""
    R = 6_371_000
    φ1, φ2 = radians(lat1), radians(lat2)
    dφ = radians(lat2 - lat1)
    dλ = radians(lon2 - lon1)
    a = sin(dφ/2)**2 + cos(φ1)*cos(φ2)*sin(dλ/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def run(payload: dict) -> dict:
    """
    payload keys:
      lecture_id, lecture_number, subject_code, date,
      student_prn, student_name,
      qr_token,
      student_lat, student_lon,
      classroom_lat, classroom_lon
    """
    sheets = SheetsService()

    # Step 1 — QR verification
    qr_ok = verify_qr(payload["lecture_id"], payload["qr_token"])

    # Step 2 — GPS geofence check
    dist = _distance_metres(
        payload["classroom_lat"], payload["classroom_lon"],
        payload["student_lat"],   payload["student_lon"],
    )
    gps_ok = dist <= GEOFENCE_RADIUS_M

    # Step 3 — Decide attendance status
    if qr_ok and gps_ok:
        status     = "Present"
        qr_result  = "Verified"
    elif qr_ok and not gps_ok:
        status     = "Absent"        # QR correct but outside classroom
        qr_result  = "GPS-Failed"
    else:
        status     = "Absent"
        qr_result  = "QR-Failed"

    # Step 4 — Write to Google Sheets
    sheets.mark_attendance(
        date       = payload["date"],
        lecture_no = payload["lecture_number"],
        subject    = payload["subject_code"],
        prn        = payload["student_prn"],
        name       = payload["student_name"],
        status     = status,
        scan_time  = datetime.now().strftime("%H:%M:%S"),
        gps        = f"{payload['student_lat']},{payload['student_lon']}",
        qr_ok      = qr_result,
    )

    return {
        "student_prn": payload["student_prn"],
        "status":      status,
        "qr_ok":       qr_ok,
        "gps_ok":      gps_ok,
        "distance_m":  round(dist, 1),
    }
