"""
services/auth.py — JWT authentication for all four roles.

Roles: student | faculty | hod | admin
Users are stored in the 'Users' Google Sheet tab.

Sheet columns:
  ID | Name | Role | Department | Class | Division | Password_Hash
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

def create_token(user_id: str, name: str, role: str,
                 department: str, cls: str, division: str,
                 expires_in: int = 86400) -> str:
    """Create a signed JWT token. Expires in 24 hours by default."""
    header  = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({
        "sub":        user_id,
        "name":       name,
        "role":       role,
        "department": department,
        "class":      cls,
        "division":   division,
        "exp":        int(time.time()) + expires_in,
    }).encode())
    sig_input = f"{header}.{payload}".encode()
    sig = hmac.new(SECRET_KEY.encode(), sig_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"

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
    {"ID": "MIT2024001", "Name": "Demo Student",  "Role": "student", "Department": "CSE AI&ML", "Class": "SE",  "Division": "A", "Password_Hash": hash_password("student123")},
    {"ID": "FAC001",     "Name": "Demo Faculty",  "Role": "faculty", "Department": "CSE AI&ML", "Class": "",    "Division": "",  "Password_Hash": hash_password("faculty123")},
    {"ID": "HOD001",     "Name": "Demo HoD",      "Role": "hod",     "Department": "CSE AI&ML", "Class": "",    "Division": "",  "Password_Hash": hash_password("hod123")},
    {"ID": "ADMIN001",   "Name": "Admin",         "Role": "admin",   "Department": "MITAOE",    "Class": "",    "Division": "",  "Password_Hash": hash_password("admin123")},
]

# ── Login logic ───────────────────────────────────────────────────────────────

def login(user_id: str, password: str) -> dict:
    """
    Look up the user in the 'users' sheet and verify password.
    Falls back to _LOCAL_USERS if Google Sheets is unavailable.
    Returns token + user info on success, raises ValueError on failure.
    """
    users = _LOCAL_USERS   # default fallback
    try:
        sheets = SheetsService()
        sheet_users = sheets.read_all("users")
        if sheet_users:           # only use sheet if it has data
            users = sheet_users
    except Exception:
        pass                      # Sheets unavailable — continue with local users

    user = next(
        (u for u in users if str(u.get("ID", "")).strip() == user_id.strip()),
        None
    )
    if not user:
        raise ValueError("User not found")

    stored_hash = str(user.get("Password_Hash", ""))
    if not verify_password(password, stored_hash):
        raise ValueError("Incorrect password")

    token = create_token(
        user_id    = str(user["ID"]),
        name       = str(user.get("Name", "")),
        role       = str(user.get("Role", "student")).lower(),
        department = str(user.get("Department", "")),
        cls        = str(user.get("Class", "")),
        division   = str(user.get("Division", "")),
    )

    return {
        "token":      token,
        "id":         str(user["ID"]),
        "name":       str(user.get("Name", "")),
        "role":       str(user.get("Role", "student")).lower(),
        "department": str(user.get("Department", "")),
        "class":      str(user.get("Class", "")),
        "division":   str(user.get("Division", "")),
    }

def get_current_user(authorization: str) -> dict:
    """Extract user claims from 'Bearer <token>' header."""
    if not authorization.startswith("Bearer "):
        raise ValueError("Missing Bearer token")
    return decode_token(authorization[7:])
