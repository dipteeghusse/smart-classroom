"""
services/auth.py — JWT authentication for all four roles.

Roles: student | faculty | hod | admin
Users are stored in the 'Users' Google Sheet tab.

Sheet columns:
  ID | Name | Role | Department | Class | Division | Email | Password_Hash | Must_Reset

Must_Reset: set to "true" for new accounts so users change their password on first login.
Login accepts either ID or Email.
"""
import hashlib
import hmac
import time
import json
import base64
from backend.config import SECRET_KEY
from backend.services.sheets import SheetsService

# ── Password helpers ──────────────────────────────────────────────────────────

def _hash_password(plain: str) -> str:
    return hashlib.sha256((plain + SECRET_KEY).encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(_hash_password(plain), hashed)

def hash_password(plain: str) -> str:
    return _hash_password(plain)

# ── Minimal JWT (no extra library needed) ────────────────────────────────────

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * pad)

def _make_token(payload: dict, expires_in: int = 86400) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload["exp"] = int(time.time()) + expires_in
    enc_payload = _b64url(json.dumps(payload).encode())
    sig_input = f"{header}.{enc_payload}".encode()
    sig = hmac.new(SECRET_KEY.encode(), sig_input, hashlib.sha256).digest()
    return f"{header}.{enc_payload}.{_b64url(sig)}"

def create_token(user_id: str, name: str, role: str,
                 department: str, cls: str, division: str,
                 email: str = "", expires_in: int = 86400) -> str:
    return _make_token({
        "sub": user_id, "name": name, "role": role,
        "department": department, "class": cls, "division": division,
        "email": email,
    }, expires_in)

def _create_reset_token(user_id: str) -> str:
    """Short-lived (15 min) token used only to authorise the change-password call."""
    return _make_token({"sub": user_id, "role": "reset"}, expires_in=900)

def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT token.
    Raises ValueError if signature is invalid or token is expired.
    """
    try:
        header, payload, sig = token.split(".")
    except ValueError:
        raise ValueError("Malformed token")

    sig_input = f"{header}.{payload}".encode()
    expected  = hmac.new(SECRET_KEY.encode(), sig_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url(expected), sig):
        raise ValueError("Invalid signature")

    claims = json.loads(_b64url_decode(payload))
    if claims.get("exp", 0) < int(time.time()):
        raise ValueError("Token expired")

    return claims

# ── Local fallback users (used when Google Sheets is unavailable) ─────────────

_LOCAL_USERS = [
    {"ID": "MIT2024001", "Name": "Demo Student",  "Role": "student", "Department": "CSE AI&ML", "Class": "SE",  "Division": "A", "Email": "student@mitaoe.ac.in",  "Password_Hash": hash_password("student123"),  "Must_Reset": "false"},
    {"ID": "FAC001",     "Name": "Demo Faculty",  "Role": "faculty", "Department": "CSE AI&ML", "Class": "",    "Division": "",  "Email": "faculty@mitaoe.ac.in",  "Password_Hash": hash_password("faculty123"),  "Must_Reset": "false"},
    {"ID": "HOD001",     "Name": "Demo HoD",      "Role": "hod",     "Department": "CSE AI&ML", "Class": "",    "Division": "",  "Email": "hod@mitaoe.ac.in",      "Password_Hash": hash_password("hod123"),      "Must_Reset": "false"},
    {"ID": "ADMIN001",   "Name": "Admin",         "Role": "admin",   "Department": "MITAOE",    "Class": "",    "Division": "",  "Email": "admin@mitaoe.ac.in",    "Password_Hash": hash_password("admin123"),    "Must_Reset": "false"},
]

# ── Shared user loader ────────────────────────────────────────────────────────

def _load_users() -> list[dict]:
    try:
        sheets = SheetsService()
        sheet_users = sheets.read_all("users")
        if sheet_users:
            return sheet_users
    except Exception:
        pass
    return _LOCAL_USERS

# ── Login logic ───────────────────────────────────────────────────────────────

def login(user_id_or_email: str, password: str) -> dict:
    """
    Look up the user by ID or Email, verify password.
    If Must_Reset is true, returns {must_reset: true, temp_token} instead of a full token.
    Falls back to _LOCAL_USERS if Google Sheets is unavailable.
    """
    credential = user_id_or_email.strip()
    users = _load_users()

    user = next(
        (u for u in users
         if str(u.get("ID", "")).strip() == credential
         or str(u.get("Email", "")).strip().lower() == credential.lower()),
        None,
    )
    if not user:
        raise ValueError("User not found")

    stored_hash = str(user.get("Password_Hash", ""))
    if not verify_password(password, stored_hash):
        raise ValueError("Incorrect password")

    # First-login password reset gate
    must_reset = str(user.get("Must_Reset", "false")).strip().lower() in ("true", "1", "yes")
    if must_reset:
        return {
            "must_reset": True,
            "user_id":    str(user["ID"]),
            "temp_token": _create_reset_token(str(user["ID"])),
        }

    return _build_response(user)


def _build_response(user: dict) -> dict:
    token = create_token(
        user_id    = str(user["ID"]),
        name       = str(user.get("Name", "")),
        role       = str(user.get("Role", "student")).lower(),
        department = str(user.get("Department", "")),
        cls        = str(user.get("Class", "")),
        division   = str(user.get("Division", "")),
        email      = str(user.get("Email", "")),
    )
    return {
        "token":      token,
        "id":         str(user["ID"]),
        "name":       str(user.get("Name", "")),
        "role":       str(user.get("Role", "student")).lower(),
        "department": str(user.get("Department", "")),
        "class":      str(user.get("Class", "")),
        "division":   str(user.get("Division", "")),
        "email":      str(user.get("Email", "")),
    }


# ── Change password ───────────────────────────────────────────────────────────

def change_password(user_id: str, temp_token: str, new_password: str) -> dict:
    """
    Verify the reset token, update the password in Google Sheets, return a full token.
    Raises ValueError on bad token or if user not found.
    """
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters")

    claims = decode_token(temp_token)
    if claims.get("role") != "reset" or claims.get("sub") != user_id:
        raise ValueError("Invalid or expired reset token")

    new_hash = hash_password(new_password)

    # Update in Google Sheets
    try:
        sheets = SheetsService()
        sheets.update_row("users", "ID", user_id,
                          {"Password_Hash": new_hash, "Must_Reset": "false"})
    except Exception:
        pass  # Sheets unavailable; local-only session continues

    # Reload user and return full session token
    users = _load_users()
    user = next((u for u in users if str(u.get("ID", "")).strip() == user_id), None)
    if not user:
        raise ValueError("User not found after password change")

    # Use the freshly hashed password (sheet may not have updated yet in same request)
    user = dict(user)
    user["Password_Hash"] = new_hash
    user["Must_Reset"]    = "false"
    return _build_response(user)


def get_current_user(authorization: str) -> dict:
    """Extract user claims from 'Bearer <token>' header."""
    if not authorization.startswith("Bearer "):
        raise ValueError("Missing Bearer token")
    claims = decode_token(authorization[7:])
    if claims.get("role") == "reset":
        raise ValueError("Reset token cannot be used for API access")
    return claims
