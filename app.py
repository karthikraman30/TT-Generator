"""
Timetable Generator — Web Interface with Firebase Authentication
================================================================
A Flask web application with role-based access control:
  - ADMIN: Full dashboard, all data, faculty PDF downloads
  - FACULTY: Personal timetable only + PDF download

Uses Firebase Authentication for login and session management.

Usage:
    python app.py
    # Then open http://localhost:5001 in your browser
"""

import os
import io
import sys
import zipfile
from datetime import time as dt_time
from functools import wraps

from flask import (Flask, render_template_string, request, jsonify,
                   redirect, url_for, session, make_response, send_file)

# Import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_manager import DBManager
from faculty_pdf import generate_faculty_pdf

# Firebase Admin SDK (server-side token verification)
try:
    import firebase_admin
    from firebase_admin import credentials, auth as firebase_auth
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("WARNING: firebase-admin not installed. Auth will be disabled.")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-me')

# ---------------------------------------------------------------------------
# Firebase Initialization
# ---------------------------------------------------------------------------
def init_firebase():
    """Initialize Firebase Admin SDK if not already initialized."""
    if not FIREBASE_AVAILABLE:
        return False
    if firebase_admin._apps:
        return True  # Already initialized

    sa_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH',
                        './firebase-service-account.json')
    if not os.path.exists(sa_path):
        print(f"  WARNING: Firebase service account not found at {sa_path}")
        print("  Auth features will be disabled. Set up Firebase to enable.")
        return False

    try:
        cred = credentials.Certificate(sa_path)
        firebase_admin.initialize_app(cred)
        print("  ✓ Firebase Admin SDK initialized")
        return True
    except Exception as e:
        print(f"  WARNING: Firebase init failed: {e}")
        return False


FIREBASE_INITIALIZED = init_firebase()

# Firebase Web SDK config (for client-side login page)
FIREBASE_WEB_CONFIG = {
    'apiKey': os.getenv('FIREBASE_API_KEY', ''),
    'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN', ''),
    'projectId': os.getenv('FIREBASE_PROJECT_ID', ''),
}


# ---------------------------------------------------------------------------
# Auth Helpers
# ---------------------------------------------------------------------------
# Password policy constants
PASSWORD_RULES = {
    'min_length': 8,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_digit': True,
    'require_special': True,
}


def validate_password(password):
    """Check password against policy rules. Returns (ok, error_message)."""
    if len(password) < PASSWORD_RULES['min_length']:
        return False, f'Password must be at least {PASSWORD_RULES["min_length"]} characters'
    if PASSWORD_RULES['require_uppercase'] and not any(c.isupper() for c in password):
        return False, 'Password must contain at least one uppercase letter'
    if PASSWORD_RULES['require_lowercase'] and not any(c.islower() for c in password):
        return False, 'Password must contain at least one lowercase letter'
    if PASSWORD_RULES['require_digit'] and not any(c.isdigit() for c in password):
        return False, 'Password must contain at least one digit'
    if PASSWORD_RULES['require_special'] and not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/~`' for c in password):
        return False, 'Password must contain at least one special character (!@#$%^&*...)'
    return True, ''


def get_current_user():
    """
    Get the currently logged-in user from session.
    Returns dict with uid, email, role, faculty_short_name, password_changed or None.
    """
    if 'user_uid' not in session:
        return None
    return {
        'uid': session.get('user_uid'),
        'email': session.get('user_email'),
        'role': session.get('user_role'),
        'faculty_short_name': session.get('faculty_short_name'),
        'password_changed': session.get('password_changed', False),
    }


def login_required(f):
    """Decorator: requires authenticated user who has changed their password."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for('login'))
        # Force password change for first-time faculty logins
        if not user.get('password_changed', False) and user['role'] != 'ADMIN':
            return redirect(url_for('change_password'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator: requires ADMIN role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for('login'))
        if user['role'] != 'ADMIN':
            return redirect(url_for('faculty_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# CSS Styles (shared across all pages)
# ---------------------------------------------------------------------------
SHARED_STYLES = """
:root {
    --bg-primary: #0f0f1a;
    --bg-secondary: #1a1a2e;
    --bg-card: #16213e;
    --bg-card-hover: #1a2745;
    --text-primary: #e8e8f0;
    --text-secondary: #8888a8;
    --text-muted: #5a5a7a;
    --accent-blue: #4f8fff;
    --accent-purple: #8b5cf6;
    --accent-green: #10b981;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
    --accent-cyan: #06b6d4;
    --border-color: #2a2a4a;
    --gradient-1: linear-gradient(135deg, #4f8fff, #8b5cf6);
    --gradient-2: linear-gradient(135deg, #10b981, #06b6d4);
    --shadow-glow: 0 0 30px rgba(79, 143, 255, 0.15);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    line-height: 1.6;
}

nav {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    padding: 0 2rem;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(12px);
}

.nav-inner {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    gap: 2rem;
    height: 64px;
}

.nav-brand {
    font-weight: 700;
    font-size: 1.1rem;
    background: var(--gradient-1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    white-space: nowrap;
}

.nav-links {
    display: flex;
    gap: 0.15rem;
    list-style: none;
    overflow-x: auto;
    flex: 1;
    scrollbar-width: none;  /* Firefox */
    -ms-overflow-style: none;  /* IE/Edge */
}
.nav-links::-webkit-scrollbar {
    display: none;  /* Chrome/Safari */
}

.nav-links a {
    text-decoration: none;
    color: var(--text-secondary);
    padding: 0.4rem 0.7rem;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 500;
    transition: all 0.2s;
    white-space: nowrap;
}

.nav-links a:hover, .nav-links a.active {
    color: var(--text-primary);
    background: rgba(79, 143, 255, 0.1);
}

.nav-links a.active {
    background: rgba(79, 143, 255, 0.2);
    color: var(--accent-blue);
}

.nav-user {
    display: flex;
    align-items: center;
    gap: 1rem;
    white-space: nowrap;
}

.nav-user .user-email {
    font-size: 0.8rem;
    color: var(--text-secondary);
}

.nav-user .user-role {
    font-size: 0.7rem;
    padding: 0.15rem 0.6rem;
    border-radius: 20px;
    font-weight: 600;
}

.role-admin {
    background: rgba(139, 92, 246, 0.2);
    color: var(--accent-purple);
    border: 1px solid rgba(139, 92, 246, 0.3);
}

.role-faculty {
    background: rgba(16, 185, 129, 0.2);
    color: var(--accent-green);
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.btn-logout {
    background: rgba(239, 68, 68, 0.1);
    color: var(--accent-red);
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 0.4rem 1rem;
    border-radius: 8px;
    font-size: 0.8rem;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.2s;
}

.btn-logout:hover {
    background: rgba(239, 68, 68, 0.2);
}

main {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
}

h1 {
    font-size: 1.8rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}

h1 .icon { margin-right: 0.5rem; }

.subtitle {
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin-bottom: 2rem;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}

.stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.25rem;
    transition: all 0.3s;
}

.stat-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-glow);
    border-color: var(--accent-blue);
}

.stat-value {
    font-size: 2rem;
    font-weight: 700;
    background: var(--gradient-1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.stat-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.25rem;
}

.filters {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}

.filter-group {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.filter-group label {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

select, input[type="text"] {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-size: 0.85rem;
    font-family: 'Inter', sans-serif;
    min-width: 160px;
    transition: border-color 0.2s;
}

select:focus, input[type="text"]:focus {
    outline: none;
    border-color: var(--accent-blue);
}

.btn {
    background: var(--gradient-1);
    color: white;
    border: none;
    padding: 0.5rem 1.5rem;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    align-self: flex-end;
    text-decoration: none;
    display: inline-block;
}

.btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(79, 143, 255, 0.3);
}

.btn-sm {
    padding: 0.35rem 0.9rem;
    font-size: 0.75rem;
}

.btn-green {
    background: var(--gradient-2);
}

.table-container {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 2rem;
}

.table-header {
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.table-header h2 {
    font-size: 1rem;
    font-weight: 600;
}

.table-count {
    font-size: 0.8rem;
    color: var(--text-muted);
    background: var(--bg-secondary);
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
}

.table-scroll { overflow-x: auto; }

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
}

th {
    background: var(--bg-secondary);
    color: var(--text-secondary);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
    padding: 0.75rem 1rem;
    text-align: left;
    white-space: nowrap;
    position: sticky;
    top: 0;
}

td {
    padding: 0.65rem 1rem;
    border-top: 1px solid rgba(42, 42, 74, 0.5);
    vertical-align: top;
}

tr:hover td { background: var(--bg-card-hover); }

.badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}

.badge-hard {
    background: rgba(239, 68, 68, 0.15);
    color: var(--accent-red);
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.badge-soft {
    background: rgba(245, 158, 11, 0.15);
    color: var(--accent-amber);
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.badge-db {
    background: rgba(79, 143, 255, 0.15);
    color: var(--accent-blue);
    border: 1px solid rgba(79, 143, 255, 0.3);
}

.badge-app {
    background: rgba(139, 92, 246, 0.15);
    color: var(--accent-purple);
    border: 1px solid rgba(139, 92, 246, 0.3);
}

.badge-both {
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent-green);
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.badge-active {
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent-green);
}

.badge-inactive {
    background: rgba(239, 68, 68, 0.15);
    color: var(--accent-red);
}

.btn-delete {
    background: rgba(239, 68, 68, 0.1);
    color: var(--accent-red);
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.2s;
    font-family: 'Inter', sans-serif;
}
.btn-delete:hover {
    background: rgba(239, 68, 68, 0.3);
    border-color: var(--accent-red);
}

.tab-btn {
    background: var(--bg-secondary);
    color: var(--text-secondary);
    border: 1px solid var(--border);
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    font-family: 'Inter', sans-serif;
}
.tab-btn:hover {
    color: var(--text-primary);
    border-color: var(--accent-blue);
}
.tab-btn.active {
    background: rgba(79, 143, 255, 0.15);
    color: var(--accent-blue);
    border-color: var(--accent-blue);
}

.badge-core {
    background: rgba(6, 182, 212, 0.15);
    color: var(--accent-cyan);
    border: 1px solid rgba(6, 182, 212, 0.3);
}

.badge-elective {
    background: rgba(245, 158, 11, 0.15);
    color: var(--accent-amber);
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.badge-moved {
    background: rgba(245, 158, 11, 0.15);
    color: var(--accent-amber);
}

.util-bar-bg {
    background: var(--bg-secondary);
    border-radius: 6px;
    height: 8px;
    width: 100px;
    overflow: hidden;
}

.util-bar {
    height: 100%;
    border-radius: 6px;
    transition: width 0.5s ease;
}

.util-low { background: var(--accent-green); }
.util-med { background: var(--accent-amber); }
.util-high { background: var(--accent-red); }

.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--text-muted);
}

.empty-state .icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

/* Faculty PDF list */
.faculty-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1rem;
    margin-top: 1rem;
}

.faculty-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: all 0.2s;
}

.faculty-card:hover {
    border-color: var(--accent-blue);
    transform: translateY(-1px);
}

.faculty-card .name {
    font-weight: 600;
    font-size: 0.9rem;
}

.faculty-card .classes {
    font-size: 0.75rem;
    color: var(--text-muted);
}

/* Schedule grid for faculty */
.schedule-grid {
    display: grid;
    grid-template-columns: 100px repeat(5, 1fr);
    gap: 2px;
    margin-bottom: 2rem;
}

.schedule-cell {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    padding: 0.75rem;
    min-height: 80px;
    font-size: 0.78rem;
}

.schedule-cell.header {
    background: var(--bg-secondary);
    font-weight: 600;
    text-align: center;
    min-height: auto;
    padding: 0.5rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
    text-transform: uppercase;
}

.schedule-cell.time-label {
    background: var(--bg-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    color: var(--text-secondary);
    min-height: auto;
}

.schedule-cell .course-code {
    font-weight: 700;
    color: var(--accent-blue);
    font-size: 0.85rem;
}

.schedule-cell .room {
    color: var(--accent-green);
    font-size: 0.72rem;
}

.schedule-cell .batch {
    color: var(--text-muted);
    font-size: 0.7rem;
}

.schedule-cell.empty {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 1.2rem;
}

/* ===== Master Timetable Grid ===== */
.master-grid {
    display: grid;
    grid-template-columns: 110px repeat(5, 1fr);
    gap: 2px;
    margin-bottom: 2rem;
    background: var(--border-color);
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--border-color);
}
.master-grid .mg-header {
    background: var(--bg-secondary);
    font-weight: 600;
    text-align: center;
    padding: 0.6rem 0.4rem;
    font-size: 0.78rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.master-grid .mg-time {
    background: var(--bg-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    color: var(--text-secondary);
    padding: 0.4rem;
    font-weight: 600;
}
.master-grid .mg-cell {
    background: var(--bg-card);
    padding: 0.4rem;
    min-height: 70px;
    vertical-align: top;
    transition: background 0.15s;
}
.master-grid .mg-cell:hover {
    background: var(--bg-card-hover);
}
.mg-cell .cell-entry {
    background: rgba(79, 143, 255, 0.06);
    border: 1px solid rgba(79, 143, 255, 0.15);
    border-radius: 6px;
    padding: 0.35rem 0.45rem;
    margin-bottom: 3px;
    font-size: 0.72rem;
    line-height: 1.35;
    transition: all 0.15s;
}
.mg-cell .cell-entry:last-child { margin-bottom: 0; }
.mg-cell .cell-entry:hover {
    border-color: var(--accent-blue);
    background: rgba(79, 143, 255, 0.12);
}
.cell-entry .ce-code {
    font-weight: 700;
    color: var(--accent-blue);
    font-size: 0.78rem;
}
.cell-entry .ce-name {
    color: var(--text-secondary);
    font-size: 0.66rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 140px;
}
.cell-entry .ce-faculty { color: var(--accent-purple); font-size: 0.68rem; }
.cell-entry .ce-room { color: var(--accent-green); font-size: 0.68rem; }
.cell-entry .ce-batch { color: var(--text-muted); font-size: 0.64rem; }
.cell-entry .ce-type {
    display: inline-block;
    padding: 0.05rem 0.35rem;
    border-radius: 8px;
    font-size: 0.58rem;
    font-weight: 600;
    margin-left: 0.3rem;
}
.ce-type-core { background: rgba(6,182,212,0.15); color: var(--accent-cyan); }
.ce-type-elective { background: rgba(245,158,11,0.15); color: var(--accent-amber); }
.mg-cell-empty {
    background: var(--bg-card);
    min-height: 70px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 0.8rem;
    opacity: 0.4;
}

/* ===== Multi-Select Dropdown ===== */
.multi-select {
    position: relative;
    min-width: 180px;
}
.ms-trigger {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    padding: 0.45rem 0.75rem;
    border-radius: 8px;
    font-size: 0.82rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-height: 38px;
    flex-wrap: wrap;
    transition: border-color 0.2s;
    font-family: 'Inter', sans-serif;
}
.ms-trigger:hover, .ms-trigger.active { border-color: var(--accent-blue); }
.ms-trigger .ms-placeholder { color: var(--text-muted); }
.ms-pill {
    background: rgba(79, 143, 255, 0.15);
    color: var(--accent-blue);
    padding: 0.1rem 0.5rem;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
}
.ms-pill .ms-remove { cursor: pointer; font-size: 0.8rem; opacity: 0.7; }
.ms-pill .ms-remove:hover { opacity: 1; }
.ms-dropdown {
    display: none;
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    z-index: 200;
    max-height: 240px;
    overflow-y: auto;
    padding: 0.3rem 0;
}
.ms-dropdown.open { display: block; }
.ms-option {
    padding: 0.4rem 0.75rem;
    font-size: 0.8rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: background 0.1s;
}
.ms-option:hover { background: rgba(79, 143, 255, 0.1); }
.ms-option input[type="checkbox"] { accent-color: var(--accent-blue); }

/* ===== Drag-and-Drop Editor ===== */
.dnd-grid {
    display: grid;
    grid-template-columns: 110px repeat(5, 1fr);
    gap: 2px;
    margin-bottom: 1rem;
    background: var(--border-color);
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--border-color);
}
.dnd-cell {
    background: var(--bg-card);
    padding: 0.4rem;
    min-height: 80px;
    transition: all 0.2s;
}
.dnd-cell.drag-over {
    background: rgba(79, 143, 255, 0.15) !important;
    border: 2px dashed var(--accent-blue);
}
.dnd-card {
    background: rgba(79, 143, 255, 0.08);
    border: 1px solid rgba(79, 143, 255, 0.2);
    border-radius: 6px;
    padding: 0.35rem 0.45rem;
    margin-bottom: 3px;
    font-size: 0.72rem;
    cursor: grab;
    transition: all 0.15s;
    user-select: none;
}
.dnd-card:active { cursor: grabbing; }
.dnd-card.dragging { opacity: 0.4; transform: scale(0.95); }
.dnd-card .dnd-code { font-weight: 700; color: var(--accent-blue); }

/* ===== Pending Changes ===== */
.pending-changes {
    background: rgba(245,158,11,0.08);
    border: 1px solid rgba(245,158,11,0.3);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
}
.pending-item {
    font-size: 0.82rem;
    padding: 0.25rem 0;
    color: var(--text-secondary);
}
.pending-item .arrow { color: var(--accent-amber); margin: 0 0.4rem; }

/* ===== Confirmation Modal ===== */
.modal-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6);
    z-index: 1000;
    align-items: center;
    justify-content: center;
}
.modal-overlay.show { display: flex; }
.modal-box {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 2rem;
    max-width: 480px;
    width: 90%;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}
.modal-box h3 { margin-bottom: 0.75rem; font-size: 1.1rem; }
.modal-box p { color: var(--text-secondary); font-size: 0.88rem; margin-bottom: 1.5rem; line-height: 1.6; }
.modal-actions { display: flex; gap: 0.75rem; justify-content: flex-end; }
.btn-danger {
    background: rgba(239, 68, 68, 0.15);
    color: var(--accent-red);
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 0.5rem 1.2rem;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    font-family: 'Inter', sans-serif;
}
.btn-danger:hover { background: rgba(239, 68, 68, 0.3); }
.btn-confirm {
    background: var(--gradient-2);
    color: white;
    border: none;
    padding: 0.5rem 1.2rem;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    font-family: 'Inter', sans-serif;
}
.btn-confirm:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(16,185,129,0.3); }

/* ===== View Toggle ===== */
.view-toggle {
    display: flex;
    gap: 0.4rem;
    margin-bottom: 1rem;
}
.view-toggle button {
    background: var(--bg-secondary);
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
    padding: 0.4rem 0.9rem;
    border-radius: 8px;
    font-size: 0.78rem;
    cursor: pointer;
    transition: all 0.2s;
    font-family: 'Inter', sans-serif;
}
.view-toggle button.active {
    background: rgba(79, 143, 255, 0.15);
    color: var(--accent-blue);
    border-color: var(--accent-blue);
}

@media (max-width: 768px) {
    nav { padding: 0 1rem; }
    main { padding: 1rem; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    .filters { flex-direction: column; }
    .filter-group { width: 100%; }
    select, input[type="text"] { width: 100%; }
    .schedule-grid { grid-template-columns: 80px repeat(5, 1fr); }
    .master-grid { grid-template-columns: 80px repeat(5, 1fr); }
    .dnd-grid { grid-template-columns: 80px repeat(5, 1fr); }
}
"""


# ---------------------------------------------------------------------------
# Navigation builder
# ---------------------------------------------------------------------------
def build_nav(user, active_page=''):
    """Build the navigation bar HTML based on user role."""
    if not user:
        return ''

    links = ''
    if user['role'] == 'ADMIN':
        pages = [
            ('admin_dashboard', 'dashboard', 'Dashboard'),
            ('admin_generate', 'generate', 'Generate'),
            ('admin_timetable', 'timetable', 'Timetable'),
            ('admin_history', 'history', 'History'),
            ('admin_faculty', 'faculty', 'Faculty'),
            ('admin_rooms', 'rooms', 'Rooms'),
            ('admin_constraints', 'constraints', 'Constraints'),
            ('admin_violations', 'violations', 'Violations'),
            ('admin_faculty_pdfs', 'pdfs', 'PDFs'),
            ('admin_data_manager', 'data', 'Data Manager'),
            ('admin_manage_users', 'users', 'Users'),
            ('admin_configuration', 'config', 'Config'),
        ]
    else:
        pages = [
            ('faculty_dashboard', 'dashboard', 'My Schedule'),
        ]

    for endpoint, page_id, label in pages:
        active = 'active' if page_id == active_page else ''
        links += f'<li><a href="{url_for(endpoint)}" class="{active}">{label}</a></li>'

    role_class = 'role-admin' if user['role'] == 'ADMIN' else 'role-faculty'
    role_label = user['role']

    return f'''
    <nav>
        <div class="nav-inner">
            <div class="nav-brand">📅 Timetable Generator</div>
            <ul class="nav-links">{links}</ul>
            <div class="nav-user">
                <span class="user-email">{user["email"]}</span>
                <span class="user-role {role_class}">{role_label}</span>
                <a href="{url_for("logout")}" class="btn-logout">Logout</a>
            </div>
        </div>
    </nav>
    '''


def page_shell(title, user, active_page, content):
    """Wrap content in the full page HTML shell."""
    nav_html = build_nav(user, active_page)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Timetable Generator</title>
    <meta name="description" content="University Timetable Generator - View schedules, room utilization, and constraint enforcement">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>{SHARED_STYLES}</style>
</head>
<body>
    {nav_html}
    <main>{content}</main>
</body>
</html>'''


# ---------------------------------------------------------------------------
# Helper: format time objects for display
# ---------------------------------------------------------------------------
def format_entries(entries):
    """Convert time objects to strings for Jinja rendering."""
    for entry in entries:
        for key, val in entry.items():
            if isinstance(val, dt_time):
                entry[key] = val.strftime('%H:%M')
            elif hasattr(val, 'strftime'):
                entry[key] = val.strftime('%Y-%m-%d %H:%M')
    return entries


# ---------------------------------------------------------------------------
# LOGIN / LOGOUT ROUTES
# ---------------------------------------------------------------------------

LOGIN_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login — Timetable Generator</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        ''' + SHARED_STYLES + '''
        .login-container {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 2rem;
        }
        .login-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 3rem;
            width: 100%;
            max-width: 420px;
            box-shadow: var(--shadow-glow);
        }
        .login-card h1 {
            text-align: center;
            margin-bottom: 0.5rem;
            font-size: 1.5rem;
        }
        .login-card .subtitle {
            text-align: center;
            margin-bottom: 2rem;
        }
        .form-group {
            margin-bottom: 1.25rem;
        }
        .form-group label {
            display: block;
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 0.4rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .form-group input {
            width: 100%;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-family: 'Inter', sans-serif;
            transition: border-color 0.2s;
        }
        .form-group input:focus {
            outline: none;
            border-color: var(--accent-blue);
        }
        .login-btn {
            width: 100%;
            background: var(--gradient-1);
            color: white;
            border: none;
            padding: 0.85rem;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            margin-top: 0.5rem;
        }
        .login-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 20px rgba(79, 143, 255, 0.4);
        }
        .login-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .error-msg {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: var(--accent-red);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            margin-bottom: 1rem;
            display: none;
        }
        .brand-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .brand-header .logo {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-card">
            <div class="brand-header">
                <div class="logo">📅</div>
                <h1>Timetable Generator</h1>
                <p class="subtitle">Sign in to access your schedule</p>
            </div>

            <div id="error-msg" class="error-msg"></div>

            <form id="login-form" onsubmit="handleLogin(event)">
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" id="email" placeholder="yourname@daiict.ac.in" required autocomplete="email">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="password" placeholder="Enter your password" required autocomplete="current-password">
                </div>
                <button type="submit" class="login-btn" id="login-btn">Sign In</button>
            </form>
            <div id="reset-msg" style="display:none;padding:0.75rem 1rem;border-radius:8px;font-size:0.85rem;margin-top:1rem;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);color:#10b981;"></div>
            <div style="text-align:center;margin-top:1rem;">
                <a href="#" onclick="handleForgotPassword(event)" style="color:#8888a8;font-size:0.85rem;text-decoration:none;" onmouseover="this.style.color='#4f8fff'" onmouseout="this.style.color='#8888a8'">Forgot Password?</a>
            </div>
        </div>
    </div>

    <!-- Firebase JS SDK -->
    <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js"></script>
    <script>
        // Initialize Firebase
        const firebaseConfig = {{ firebase_config | tojson }};
        firebase.initializeApp(firebaseConfig);

        async function handleLogin(e) {
            e.preventDefault();
            const btn = document.getElementById('login-btn');
            const errorDiv = document.getElementById('error-msg');
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            btn.disabled = true;
            btn.textContent = 'Signing in...';
            errorDiv.style.display = 'none';

            try {
                // Authenticate with Firebase client SDK
                const userCredential = await firebase.auth()
                    .signInWithEmailAndPassword(email, password);

                // Get the ID token
                const idToken = await userCredential.user.getIdToken();

                // Send to our Flask backend to create session
                const response = await fetch('/api/session-login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id_token: idToken })
                });

                const data = await response.json();

                if (data.success) {
                    window.location.href = data.redirect;
                } else {
                    errorDiv.textContent = data.error || 'Login failed';
                    errorDiv.style.display = 'block';
                }
            } catch (err) {
                let msg = 'Authentication failed';
                if (err.code === 'auth/wrong-password' || err.code === 'auth/invalid-credential') {
                    msg = 'Invalid email or password';
                } else if (err.code === 'auth/user-not-found') {
                    msg = 'No account found with this email';
                } else if (err.code === 'auth/too-many-requests') {
                    msg = 'Too many attempts. Please try again later.';
                }
                errorDiv.textContent = msg;
                errorDiv.style.display = 'block';
            } finally {
                btn.disabled = false;
                btn.textContent = 'Sign In';
            }
        }

        async function handleForgotPassword(e) {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const errorDiv = document.getElementById('error-msg');
            const resetMsg = document.getElementById('reset-msg');
            errorDiv.style.display = 'none';
            resetMsg.style.display = 'none';

            if (!email) {
                errorDiv.textContent = 'Please enter your email address first';
                errorDiv.style.display = 'block';
                return;
            }

            try {
                await firebase.auth().sendPasswordResetEmail(email);
                resetMsg.textContent = '✓ Password reset email sent! Check your inbox.';
                resetMsg.style.display = 'block';
            } catch (err) {
                let msg = 'Failed to send reset email';
                if (err.code === 'auth/user-not-found') {
                    msg = 'No account found with this email';
                } else if (err.code === 'auth/too-many-requests') {
                    msg = 'Too many requests. Please try again later.';
                }
                errorDiv.textContent = msg;
                errorDiv.style.display = 'block';
            }
        }
    </script>
</body>
</html>'''


@app.route('/login')
def login():
    user = get_current_user()
    if user:
        if user['role'] == 'ADMIN':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('faculty_dashboard'))

    return render_template_string(
        LOGIN_TEMPLATE,
        firebase_config=FIREBASE_WEB_CONFIG,
    )


@app.route('/api/session-login', methods=['POST'])
def session_login():
    """Verify Firebase ID token and create a Flask session."""
    data = request.get_json()
    id_token = data.get('id_token', '')

    if not id_token:
        return jsonify({'success': False, 'error': 'No token provided'}), 400

    if not FIREBASE_INITIALIZED:
        return jsonify({'success': False,
                        'error': 'Firebase not configured on server'}), 500

    try:
        # Verify the ID token with Firebase Admin SDK (allow 60s clock skew)
        decoded_token = firebase_auth.verify_id_token(id_token, clock_skew_seconds=60)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')

        # Look up user role in our database
        db = DBManager(quiet=True)
        try:
            db.cur.execute(
                """SELECT ur.role, f.short_name, ur.password_changed
                   FROM user_role ur
                   LEFT JOIN faculty f ON ur.faculty_id = f.faculty_id
                   WHERE ur.uid = %s""",
                (uid,)
            )
            row = db.cur.fetchone()
        finally:
            db.close()

        if not row:
            return jsonify({
                'success': False,
                'error': 'Account not authorized. Contact admin.'
            }), 403

        role, faculty_short_name, password_changed = row

        # Store in Flask session
        session['user_uid'] = uid
        session['user_email'] = email
        session['user_role'] = role
        session['faculty_short_name'] = faculty_short_name or ''
        session['password_changed'] = password_changed

        # Determine redirect
        if role == 'ADMIN':
            redirect_url = url_for('admin_dashboard')
        elif not password_changed:
            # Force password change on first login
            redirect_url = url_for('change_password')
        else:
            redirect_url = url_for('faculty_dashboard')

        return jsonify({'success': True, 'redirect': redirect_url})

    except firebase_admin.exceptions.InvalidArgumentError as e:
        print(f"Token error: {e}", flush=True)
        return jsonify({'success': False, 'error': f'Invalid token: {e}'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def index():
    user = get_current_user()
    if user:
        if user['role'] == 'ADMIN':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('faculty_dashboard'))
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# FACULTY ROUTES
# ---------------------------------------------------------------------------

@app.route('/faculty/dashboard')
@login_required
def faculty_dashboard():
    user = get_current_user()
    faculty_name = user.get('faculty_short_name', '')

    db = DBManager(quiet=True)
    try:
        entries = db.get_faculty_schedule(faculty_name) if faculty_name else []
        entries = format_entries(entries)
    finally:
        db.close()

    # Build schedule grid data
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = ['08:00', '09:00', '10:00', '11:00', '12:00']
    period_labels = ['8:00 – 8:50', '9:00 – 9:50', '10:00 – 10:50',
                     '11:00 – 11:50', '12:00 – 12:50']

    schedule = {}
    for e in entries:
        day = e.get('day_of_week', '')
        start = str(e.get('start_time', ''))[:5]
        key = (day, start)
        if key not in schedule:
            schedule[key] = []
        schedule[key].append(e)

    # Build grid HTML
    grid_html = '<div class="schedule-grid">'
    # Header row
    grid_html += '<div class="schedule-cell header"></div>'
    for day in days:
        grid_html += f'<div class="schedule-cell header">{day}</div>'

    # Data rows
    for p_idx, period in enumerate(periods):
        grid_html += f'<div class="schedule-cell time-label">{period_labels[p_idx]}</div>'
        for day in days:
            cell_entries = schedule.get((day, period), [])
            if cell_entries:
                cell_html = ''
                for e in cell_entries:
                    code = e.get('course_code', '?')
                    room = e.get('room_number', '-') or '-'
                    batch = e.get('sub_batch', '')
                    sec = e.get('section', '')
                    cell_html += f'''
                        <div class="course-code">{code}</div>
                        <div class="room">📍 {room}</div>
                        <div class="batch">{batch} {sec}</div>
                    '''
                grid_html += f'<div class="schedule-cell">{cell_html}</div>'
            else:
                grid_html += '<div class="schedule-cell empty">—</div>'

    grid_html += '</div>'

    content = f'''
    <h1><span class="icon">👨‍🏫</span>Welcome, Prof. {faculty_name}</h1>
    <p class="subtitle">Your personal teaching schedule for this semester</p>

    <div style="margin-bottom: 1.5rem;">
        <a href="{url_for('faculty_download_pdf')}" class="btn btn-green">
            📄 Download My Timetable (PDF)
        </a>
    </div>

    {grid_html}

    <div class="table-container">
        <div class="table-header">
            <h2>Detailed Schedule</h2>
            <span class="table-count">{len(entries)} sessions</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>Day</th>
                        <th>Time</th>
                        <th>Course Code</th>
                        <th>Course Name</th>
                        <th>Batch</th>
                        <th>Section</th>
                        <th>Room</th>
                    </tr>
                </thead>
                <tbody>
    '''

    for e in entries:
        content += f'''
            <tr>
                <td>{e.get("day_of_week", "")}</td>
                <td>{e.get("start_time", "")}</td>
                <td><strong>{e.get("course_code", "")}</strong></td>
                <td>{e.get("course_name", "")}</td>
                <td>{e.get("sub_batch", "")}</td>
                <td>{e.get("section", "")}</td>
                <td>{e.get("room_number", "-") or "-"}</td>
            </tr>
        '''

    content += '''
                </tbody>
            </table>
        </div>
    </div>
    '''

    return page_shell(f'Schedule — {faculty_name}', user, 'dashboard', content)


@app.route('/faculty/download-pdf')
@login_required
def faculty_download_pdf():
    """Faculty downloads their own timetable as PDF."""
    user = get_current_user()
    faculty_name = user.get('faculty_short_name', '')
    if not faculty_name:
        return "No faculty profile linked", 400

    db = DBManager(quiet=True)
    try:
        pdf_bytes = generate_faculty_pdf(db, faculty_name)
    finally:
        db.close()

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = \
        f'attachment; filename=Timetable_{faculty_name}.pdf'
    return response


# ---------------------------------------------------------------------------
# ADMIN ROUTES
# ---------------------------------------------------------------------------

@app.route('/admin/')
@admin_required
def admin_dashboard():
    db = DBManager(quiet=True)
    try:
        stats = db.get_stats()
        constraints = db.get_constraints()
        constraints = format_entries(constraints)

        # Check for unscheduled (Slot-Free) courses
        db.cur.execute("""
            SELECT DISTINCT c.course_code, c.course_name, f.short_name AS faculty,
                   sb.sub_batch, sb.section
            FROM master_timetable mt
            JOIN faculty_course_map fcm ON mt.assignment_id = fcm.assignment_id
            JOIN course c ON fcm.course_id = c.course_id
            JOIN faculty f ON fcm.faculty_id = f.faculty_id
            JOIN student_batch sb ON mt.batch_id = sb.batch_id
            JOIN time_slot ts ON mt.slot_id = ts.slot_id
            WHERE ts.slot_group = 'Slot-Free'
            ORDER BY c.course_code
        """)
        unscheduled = db.cur.fetchall()
    finally:
        db.close()

    # Stats grid
    stats_html = '<div class="stats-grid">'
    for key, val in stats.items():
        label = key.replace('_', ' ')
        stats_html += f'''
        <div class="stat-card">
            <div class="stat-value">{val}</div>
            <div class="stat-label">{label}</div>
        </div>'''
    stats_html += '</div>'

    # Unscheduled courses alert
    unsched_html = ''
    if unscheduled:
        unsched_rows = ''
        for code, name, faculty, batch, section in unscheduled:
            unsched_rows += f'''
                <tr>
                    <td style="color:#f59e0b;font-weight:600;">{code}</td>
                    <td>{name}</td>
                    <td>{faculty}</td>
                    <td>{batch} {section}</td>
                </tr>'''
        unsched_html = f'''
        <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.3);border-radius:12px;padding:1.25rem;margin-bottom:1.5rem;">
            <h3 style="color:#f59e0b;margin:0 0 0.75rem 0;font-size:1rem;">
                ⚠️ {len(unscheduled)} Unscheduled Course(s) — Slot-Free (no time/room assigned)
            </h3>
            <div class="table-scroll">
                <table style="margin:0;">
                    <thead><tr><th>Code</th><th>Course</th><th>Faculty</th><th>Batch</th></tr></thead>
                    <tbody>{unsched_rows}</tbody>
                </table>
            </div>
            <p style="margin:0.75rem 0 0;font-size:0.78rem;color:var(--text-muted);">
                These courses were marked as "Slot-Free" in the input Excel. They need manual scheduling.
            </p>
        </div>'''

    # Constraints table
    constraints_html = '''
    <div class="table-container">
        <div class="table-header">
            <h2>🔒 Active Scheduling Constraints</h2>
            <span class="table-count">''' + str(len(constraints)) + ''' rules</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>ID</th><th>Name</th><th>Type</th>
                        <th>Scope</th><th>Enforced By</th><th>Status</th>
                    </tr>
                </thead>
                <tbody>'''

    for c in constraints:
        ctype = c.get('constraint_type', '').lower()
        enforcement = c.get('enforcement_level', '').lower()
        is_active = c.get('is_active', False)
        active_class = 'active' if is_active else 'inactive'
        active_label = 'ACTIVE' if is_active else 'OFF'
        constraints_html += f'''
            <tr>
                <td>{c.get("constraint_id", "")}</td>
                <td>{c.get("constraint_name", "")}</td>
                <td><span class="badge badge-{ctype}">{c.get("constraint_type", "")}</span></td>
                <td>{c.get("scope", "")}</td>
                <td><span class="badge badge-{enforcement}">{c.get("enforcement_level", "")}</span></td>
                <td><span class="badge badge-{active_class}">{active_label}</span></td>
            </tr>'''

    constraints_html += '</tbody></table></div></div>'

    content = f'''
    <h1><span class="icon">📊</span>Dashboard</h1>
    <p class="subtitle">University Timetable Generator — Database Overview</p>
    {unsched_html}
    {stats_html}
    {constraints_html}
    '''

    return page_shell('Dashboard', get_current_user(), 'dashboard', content)


@app.route('/admin/timetable')
@admin_required
def admin_timetable():
    selected_days = request.args.getlist('day')
    selected_batches = request.args.getlist('batch')
    selected_faculties = request.args.getlist('faculty')

    filters = {}
    if selected_days:
        filters['day_of_week'] = selected_days
    if selected_batches:
        filters['sub_batch'] = selected_batches
    if selected_faculties:
        filters['faculty'] = selected_faculties

    db = DBManager(quiet=True)
    try:
        entries = db.get_master_timetable(filters if filters else None)
        entries = format_entries(entries)
        all_entries = db.get_master_timetable()
        all_entries = format_entries(all_entries)
        batches = sorted(set(e['sub_batch'] for e in all_entries if e.get('sub_batch')))
        faculties = sorted(set(e['faculty_short_name'] for e in all_entries if e.get('faculty_short_name')))
    finally:
        db.close()

    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = ['08:00', '09:00', '10:00', '11:00', '12:00']
    period_labels = ['8:00 – 8:50', '9:00 – 9:50', '10:00 – 10:50',
                     '11:00 – 11:50', '12:00 – 12:50']

    # Build schedule dict keyed by (day, time_prefix)
    schedule = {}
    for e in entries:
        day = e.get('day_of_week', '')
        start = str(e.get('start_time', ''))[:5]
        key = (day, start)
        if key not in schedule:
            schedule[key] = []
        schedule[key].append(e)

    # Build multi-select filter options
    def ms_options(name, items, selected):
        opts = ''
        for item in items:
            chk = 'checked' if item in selected else ''
            opts += f'<div class="ms-option"><input type="checkbox" name="{name}" value="{item}" {chk} onchange="submitFilters()"><span>{item}</span></div>'
        return opts

    day_opts = ms_options('day', days_list, selected_days)
    batch_opts = ms_options('batch', batches, selected_batches)
    fac_opts = ms_options('faculty', faculties, selected_faculties)

    def ms_pills(selected):
        if not selected:
            return '<span class="ms-placeholder">All</span>'
        return ''.join(f'<span class="ms-pill">{s}<span class="ms-remove" onclick="removePill(this, \'{s}\')">×</span></span>' for s in selected)

    day_pills = ms_pills(selected_days)
    batch_pills = ms_pills(selected_batches)
    fac_pills = ms_pills(selected_faculties)

    # Build grid HTML
    grid_html = '<div class="master-grid">'
    # Header row
    grid_html += '<div class="mg-header"></div>'
    for day in days_list:
        grid_html += f'<div class="mg-header">{day}</div>'

    # Data rows
    for p_idx, period in enumerate(periods):
        grid_html += f'<div class="mg-time">{period_labels[p_idx]}</div>'
        for day in days_list:
            cell_entries = schedule.get((day, period), [])
            if cell_entries:
                cell_html = ''
                # Deduplicate by course_code + section to avoid showing same entry multiple times
                seen = set()
                for e in cell_entries:
                    dedup_key = (e.get('course_code',''), e.get('sub_batch',''), e.get('section',''))
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)
                    code = e.get('course_code', '?')
                    ctype = e.get('course_type', '') or ''
                    type_cls = 'ce-type-core' if 'core' in ctype.lower() else 'ce-type-elective'
                    type_short = 'Core' if 'core' in ctype.lower() else 'Elec'
                    faculty = e.get('faculty_short_name', '') or ''
                    room = e.get('room_number', '') or '-'
                    batch = e.get('sub_batch', '')
                    sec = e.get('section', '')
                    moved = ' 🔀' if e.get('is_moved') else ''
                    cell_html += f'''<div class="cell-entry">
                        <div><span class="ce-code">{code}</span><span class="ce-type {type_cls}">{type_short}</span>{moved}</div>
                        <div class="ce-faculty">👤 {faculty}</div>
                        <div class="ce-room">📍 {room}</div>
                        <div class="ce-batch">{batch} {sec}</div>
                    </div>'''
                grid_html += f'<div class="mg-cell">{cell_html}</div>'
            else:
                grid_html += '<div class="mg-cell mg-cell-empty">—</div>'
    grid_html += '</div>'

    # Build detail table rows
    rows_html = ''
    for e in entries:
        course_type = e.get('course_type', '') or ''
        type_class = 'core' if 'core' in course_type.lower() else 'elective'
        moved_badge = '<span class="badge badge-moved">MOVED</span>' if e.get('is_moved') else '-'
        rows_html += f'''
            <tr>
                <td>{e.get("day_of_week", "")}</td>
                <td>{e.get("start_time", "")}</td>
                <td>{e.get("slot_group", "")}</td>
                <td><strong>{e.get("course_code", "")}</strong></td>
                <td>{e.get("course_name", "")}</td>
                <td><span class="badge badge-{type_class}">{course_type}</span></td>
                <td>{e.get("faculty_short_name", "")}</td>
                <td>{e.get("sub_batch", "")}</td>
                <td>{e.get("section", "")}</td>
                <td>{e.get("room_number", "") or "-"}</td>
                <td>{moved_badge}</td>
            </tr>'''

    if not entries:
        rows_html = '''<tr><td colspan="11" class="empty-state">
            <div class="icon">📭</div>
            <p>No timetable entries found. Run the generator first.</p>
        </td></tr>'''

    content = f'''
    <h1><span class="icon">📅</span>Master Timetable</h1>
    <p class="subtitle">Complete schedule with batch, faculty, and room details</p>

    <form id="filter-form" class="filters" method="GET" action="{url_for("admin_timetable")}">
        <div class="filter-group">
            <label>Day</label>
            <div class="multi-select" id="ms-day">
                <div class="ms-trigger" onclick="toggleMs('ms-day')">{day_pills}</div>
                <div class="ms-dropdown" id="ms-day-dd">{day_opts}</div>
            </div>
        </div>
        <div class="filter-group">
            <label>Batch</label>
            <div class="multi-select" id="ms-batch">
                <div class="ms-trigger" onclick="toggleMs('ms-batch')">{batch_pills}</div>
                <div class="ms-dropdown" id="ms-batch-dd">{batch_opts}</div>
            </div>
        </div>
        <div class="filter-group">
            <label>Faculty</label>
            <div class="multi-select" id="ms-faculty">
                <div class="ms-trigger" onclick="toggleMs('ms-faculty')">{fac_pills}</div>
                <div class="ms-dropdown" id="ms-faculty-dd">{fac_opts}</div>
            </div>
        </div>
        <button type="submit" class="btn">Filter</button>
        <a href="{url_for("admin_timetable")}" class="btn" style="background:rgba(239,68,68,0.1);color:var(--accent-red);border:1px solid rgba(239,68,68,0.3);">Clear</a>
    </form>

    <div class="view-toggle">
        <button class="active" onclick="showView('grid', this)">📊 Grid View</button>
        <button onclick="showView('table', this)">📋 List View</button>
    </div>

    <div id="view-grid">
        {grid_html}
    </div>

    <div id="view-table" style="display:none;">
        <div class="table-container">
            <div class="table-header">
                <h2>Schedule</h2>
                <span class="table-count">{len(entries)} entries</span>
            </div>
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Day</th><th>Time</th><th>Slot</th>
                            <th>Course Code</th><th>Course Name</th><th>Type</th>
                            <th>Faculty</th><th>Batch</th><th>Section</th>
                            <th>Room</th><th>Moved?</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
    function toggleMs(id) {{
        var dd = document.getElementById(id + '-dd');
        var wasOpen = dd.classList.contains('open');
        document.querySelectorAll('.ms-dropdown').forEach(function(el) {{ el.classList.remove('open'); }});
        if (!wasOpen) dd.classList.add('open');
    }}
    document.addEventListener('click', function(e) {{
        if (!e.target.closest('.multi-select')) {{
            document.querySelectorAll('.ms-dropdown').forEach(function(el) {{ el.classList.remove('open'); }});
        }}
    }});
    function submitFilters() {{
        document.getElementById('filter-form').submit();
    }}
    function removePill(el, val) {{
        var ms = el.closest('.multi-select');
        var cb = ms.querySelector('input[value="' + val + '"]');
        if (cb) cb.checked = false;
        submitFilters();
    }}
    function showView(view, btn) {{
        document.getElementById('view-grid').style.display = view === 'grid' ? 'block' : 'none';
        document.getElementById('view-table').style.display = view === 'table' ? 'block' : 'none';
        document.querySelectorAll('.view-toggle button').forEach(function(b) {{ b.classList.remove('active'); }});
        btn.classList.add('active');
    }}
    </script>
    '''

    return page_shell('Master Timetable', get_current_user(), 'timetable', content)


@app.route('/admin/faculty')
@admin_required
def admin_faculty():
    selected_faculty = request.args.get('faculty', '')

    db = DBManager(quiet=True)
    try:
        if selected_faculty:
            entries = db.get_faculty_schedule(selected_faculty)
        else:
            entries = db.get_faculty_schedule()
        entries = format_entries(entries)
        all_entries = db.get_faculty_schedule()
        faculties = sorted(set(e['faculty'] for e in all_entries if e.get('faculty')))
    finally:
        db.close()

    fac_options = '<option value="">All Faculty</option>'
    for f in faculties:
        sel = 'selected' if f == selected_faculty else ''
        fac_options += f'<option value="{f}" {sel}>{f}</option>'

    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = ['08:00', '09:00', '10:00', '11:00', '12:00']
    period_labels = ['8:00 – 8:50', '9:00 – 9:50', '10:00 – 10:50',
                     '11:00 – 11:50', '12:00 – 12:50']

    # Build schedule dict keyed by (day, time_prefix)
    schedule = {}
    for e in entries:
        day = e.get('day_of_week', '')
        start = str(e.get('start_time', ''))[:5]
        key = (day, start)
        if key not in schedule:
            schedule[key] = []
        schedule[key].append(e)

    # Build grid HTML
    grid_html = '<div class="master-grid">'
    # Header row
    grid_html += '<div class="mg-header"></div>'
    for day in days_list:
        grid_html += f'<div class="mg-header">{day}</div>'

    # Data rows
    for p_idx, period in enumerate(periods):
        grid_html += f'<div class="mg-time">{period_labels[p_idx]}</div>'
        for day in days_list:
            cell_entries = schedule.get((day, period), [])
            if cell_entries:
                cell_html = ''
                # Group by (course_code, faculty) to combine batches
                grouped = {}
                for e in cell_entries:
                    code = e.get('course_code', '?')
                    fac = e.get('faculty', '')
                    room = e.get('room_number', '') or '-'
                    g_key = (code, fac, room)
                    if g_key not in grouped:
                        grouped[g_key] = []
                    
                    batch_str = f"{e.get('sub_batch', '')}"
                    if e.get('section', '') and e.get('section', '') != 'All':
                        batch_str += f" (Sec {e.get('section', '')})"
                    grouped[g_key].append(batch_str)
                
                for (code, fac, room), batches in grouped.items():
                    # Check if it's a core or elective
                    # (Faculty view might not have course_type, we can just style it generically or check if any original entry has it)
                    # For simplicity, just use the core style or generic style.
                    # We'll use a generic faculty class
                    batches_joined = ', '.join(batches)
                    fac_display = f"👤 {fac}" if not selected_faculty else "" # Hide faculty name if already filtered for them, or show if ALL
                    
                    cell_html += f'''<div class="cell-entry">
                        <div><span class="ce-code">{code}</span></div>
                        {f'<div class="ce-faculty">{fac_display}</div>' if fac_display else ''}
                        <div class="ce-room">📍 {room}</div>
                        <div class="ce-batch" style="white-space: normal;">{batches_joined}</div>
                    </div>'''
                grid_html += f'<div class="mg-cell">{cell_html}</div>'
            else:
                grid_html += '<div class="mg-cell mg-cell-empty">—</div>'
    grid_html += '</div>'


    rows_html = ''
    for e in entries:
        rows_html += f'''
            <tr>
                <td><strong>{e.get("faculty", "")}</strong></td>
                <td>{e.get("day_of_week", "")}</td>
                <td>{e.get("start_time", "")}</td>
                <td>{e.get("course_code", "")}</td>
                <td>{e.get("course_name", "")}</td>
                <td>{e.get("sub_batch", "")}</td>
                <td>{e.get("section", "")}</td>
                <td>{e.get("room_number", "") or "-"}</td>
            </tr>'''

    if not entries:
        rows_html = '''<tr><td colspan="8" class="empty-state">
            <div class="icon">📭</div><p>No schedule data.</p>
        </td></tr>'''

    content = f'''
    <h1><span class="icon">👨‍🏫</span>Faculty Schedule</h1>
    <p class="subtitle">Individual teaching schedules for all faculty members</p>

    <form class="filters" method="GET" action="{url_for("admin_faculty")}">
        <div class="filter-group"><label>Faculty</label>
        <select name="faculty" onchange="this.form.submit()" style="background:var(--bg-secondary);border:1px solid var(--border-color);color:var(--text-primary);padding:0.5rem;border-radius:6px;min-width:200px;">
        {fac_options}
        </select>
        </div>
        <noscript><button type="submit" class="btn">Filter</button></noscript>
    </form>

    <div class="view-toggle">
        <button class="active" onclick="showView('grid', this)">📊 Grid View</button>
        <button onclick="showView('table', this)">📋 List View</button>
    </div>

    <div id="view-grid">
        {grid_html}
    </div>

    <div id="view-table" style="display:none;">
        <div class="table-container">
            <div class="table-header">
                <h2>Teaching Schedule</h2>
                <span class="table-count">{len(entries)} sessions</span>
            </div>
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Faculty</th><th>Day</th><th>Time</th>
                            <th>Course Code</th><th>Course Name</th>
                            <th>Batch</th><th>Section</th><th>Room</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
    function showView(view, btn) {{
        document.getElementById('view-grid').style.display = view === 'grid' ? 'block' : 'none';
        document.getElementById('view-table').style.display = view === 'table' ? 'block' : 'none';
        document.querySelectorAll('.view-toggle button').forEach(function(b) {{ b.classList.remove('active'); }});
        btn.classList.add('active');
    }}
    </script>
    '''

    return page_shell('Faculty Schedule', get_current_user(), 'faculty', content)


@app.route('/admin/rooms')
@admin_required
def admin_rooms():
    db = DBManager(quiet=True)
    try:
        entries = db.get_room_utilization()
        entries = format_entries(entries)
    finally:
        db.close()

    rows_html = ''
    for e in entries:
        pct = float(e.get('utilization_pct', 0))
        bar_class = 'util-low' if pct < 40 else ('util-med' if pct < 75 else 'util-high')
        rows_html += f'''
            <tr>
                <td><strong>{e.get("room_number", "")}</strong></td>
                <td>{e.get("room_type", "")}</td>
                <td>{e.get("capacity", "")}</td>
                <td>{e.get("total_classes", "")} / 25</td>
                <td>{pct}%</td>
                <td>
                    <div class="util-bar-bg">
                        <div class="util-bar {bar_class}" style="width: {pct}%"></div>
                    </div>
                </td>
            </tr>'''

    if not entries:
        rows_html = '''<tr><td colspan="6" class="empty-state">
            <div class="icon">📭</div><p>No room data available.</p>
        </td></tr>'''

    content = f'''
    <h1><span class="icon">🏫</span>Room Utilization</h1>
    <p class="subtitle">Classroom occupancy and utilization rates (out of 25 possible slots/week)</p>

    <div class="table-container">
        <div class="table-header">
            <h2>Utilization Report</h2>
            <span class="table-count">{len(entries)} rooms</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>Room</th><th>Type</th><th>Capacity</th>
                        <th>Classes/Week</th><th>Utilization</th><th></th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </div>
    '''

    return page_shell('Room Utilization', get_current_user(), 'rooms', content)


@app.route('/admin/constraints')
@admin_required
def admin_constraints():
    db = DBManager(quiet=True)
    try:
        entries = db.get_constraints()
        entries = format_entries(entries)
    finally:
        db.close()

    rows_html = ''
    for e in entries:
        ctype = e.get('constraint_type', '').lower()
        enforcement = e.get('enforcement_level', '').lower()
        is_active = e.get('is_active', False)
        active_class = 'active' if is_active else 'inactive'
        active_label = 'ACTIVE' if is_active else 'OFF'
        rows_html += f'''
            <tr>
                <td>{e.get("constraint_id", "")}</td>
                <td><strong>{e.get("constraint_name", "")}</strong></td>
                <td><span class="badge badge-{ctype}">{e.get("constraint_type", "")}</span></td>
                <td>{e.get("scope", "")}</td>
                <td style="max-width:400px;font-size:0.78rem;color:var(--text-secondary);">{e.get("rule_description", "")}</td>
                <td><span class="badge badge-{enforcement}">{e.get("enforcement_level", "")}</span></td>
                <td><span class="badge badge-{active_class}">{active_label}</span></td>
            </tr>'''

    content = f'''
    <h1><span class="icon">🔒</span>Scheduling Constraints</h1>
    <p class="subtitle">All scheduling rules — stored as queryable, toggleable database rows</p>

    <div class="table-container">
        <div class="table-header">
            <h2>Constraint Rules</h2>
            <span class="table-count">{len(entries)} rules</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>ID</th><th>Name</th><th>Type</th><th>Scope</th>
                        <th>Description</th><th>Enforced By</th><th>Status</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </div>
    '''

    return page_shell('Constraints', get_current_user(), 'constraints', content)


@app.route('/admin/violations')
@admin_required
def admin_violations():
    db = DBManager(quiet=True)
    try:
        entries = db.get_violations()
        entries = format_entries(entries)
    finally:
        db.close()

    rows_html = ''
    if entries:
        for e in entries:
            severity = e.get('severity', '')
            sev_class = 'hard' if severity in ('ERROR', 'CRITICAL') else 'soft'
            rows_html += f'''
                <tr>
                    <td>{e.get("violation_id", "")}</td>
                    <td>{e.get("constraint_name", "N/A")}</td>
                    <td>{e.get("constraint_type", "-")}</td>
                    <td><span class="badge badge-{sev_class}">{severity}</span></td>
                    <td style="max-width:500px;font-size:0.78rem;color:var(--text-secondary);">{e.get("violation_detail", "")}</td>
                    <td>{e.get("detected_at", "")}</td>
                </tr>'''
    else:
        rows_html = '''<tr><td colspan="6" class="empty-state">
            <div class="icon">✅</div>
            <p>No violations detected — all constraints satisfied!</p>
        </td></tr>'''

    content = f'''
    <h1><span class="icon">⚠️</span>Constraint Violation Log</h1>
    <p class="subtitle">Audit trail of all violations detected during timetable generation</p>

    <div class="table-container">
        <div class="table-header">
            <h2>Violations</h2>
            <span class="table-count">{len(entries)} entries</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>ID</th><th>Constraint</th><th>Type</th>
                        <th>Severity</th><th>Detail</th><th>Detected At</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </div>
    '''

    return page_shell('Violation Log', get_current_user(), 'violations', content)


@app.route('/admin/faculty-pdfs')
@admin_required
def admin_faculty_pdfs():
    db = DBManager(quiet=True)
    try:
        all_entries = db.get_faculty_schedule()
        all_entries = format_entries(all_entries)
    finally:
        db.close()

    # Count classes per faculty
    faculty_classes = {}
    for e in all_entries:
        f = e.get('faculty', '')
        if f:
            faculty_classes[f] = faculty_classes.get(f, 0) + 1

    sorted_faculty = sorted(faculty_classes.keys())

    cards_html = ''
    for f in sorted_faculty:
        count = faculty_classes[f]
        cards_html += f'''
        <div class="faculty-card">
            <div>
                <div class="name">👨‍🏫 {f}</div>
                <div class="classes">{count} sessions/week</div>
            </div>
            <a href="{url_for("admin_download_faculty_pdf", short_name=f)}"
               class="btn btn-sm btn-green">📄 PDF</a>
        </div>'''

    content = f'''
    <h1><span class="icon">📄</span>Faculty PDFs</h1>
    <p class="subtitle">Download individual timetable PDFs for each faculty member</p>

    <div style="margin-bottom: 1.5rem;">
        <a href="{url_for("admin_download_all_pdfs")}" class="btn">
            📦 Download All Faculty PDFs (ZIP)
        </a>
    </div>

    <div class="faculty-grid">
        {cards_html}
    </div>
    '''

    return page_shell('Faculty PDFs', get_current_user(), 'pdfs', content)


@app.route('/admin/download-faculty-pdf/<short_name>')
@admin_required
def admin_download_faculty_pdf(short_name):
    """Admin downloads a specific faculty member's PDF."""
    db = DBManager(quiet=True)
    try:
        pdf_bytes = generate_faculty_pdf(db, short_name)
    finally:
        db.close()

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = \
        f'attachment; filename=Timetable_{short_name}.pdf'
    return response


@app.route('/admin/download-all-pdfs')
@admin_required
def admin_download_all_pdfs():
    """Admin downloads a ZIP file containing all faculty PDFs."""
    db = DBManager(quiet=True)
    try:
        all_entries = db.get_faculty_schedule()
        faculties = sorted(set(e['faculty'] for e in all_entries if e.get('faculty')))

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in faculties:
                pdf_bytes = generate_faculty_pdf(db, f)
                zf.writestr(f'Timetable_{f}.pdf', pdf_bytes)
    finally:
        db.close()

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='All_Faculty_Timetables.zip'
    )


# ---------------------------------------------------------------------------
# CHANGE PASSWORD (Forced on first login for faculty)
# ---------------------------------------------------------------------------

CHANGE_PASSWORD_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Change Password — Timetable Generator</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        ''' + SHARED_STYLES + '''
        .change-pw-container {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 2rem;
        }
        .change-pw-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 3rem;
            width: 100%;
            max-width: 480px;
            box-shadow: var(--shadow-glow);
        }
        .change-pw-card h1 {
            text-align: center;
            margin-bottom: 0.5rem;
            font-size: 1.4rem;
        }
        .change-pw-card .subtitle {
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .form-group {
            margin-bottom: 1.25rem;
        }
        .form-group label {
            display: block;
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 0.4rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .form-group input {
            width: 100%;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-family: 'Inter', sans-serif;
            transition: border-color 0.2s;
        }
        .form-group input:focus {
            outline: none;
            border-color: var(--accent-blue);
        }
        .submit-btn {
            width: 100%;
            background: var(--gradient-2);
            color: white;
            border: none;
            padding: 0.85rem;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            margin-top: 0.5rem;
        }
        .submit-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4);
        }
        .submit-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .error-msg, .success-msg {
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            margin-bottom: 1rem;
            display: none;
        }
        .error-msg {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: var(--accent-red);
        }
        .success-msg {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--accent-green);
        }
        .policy-box {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
        }
        .policy-box h3 {
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }
        .policy-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.82rem;
            color: var(--text-muted);
            padding: 0.15rem 0;
        }
        .policy-item.pass { color: var(--accent-green); }
        .policy-item.fail { color: var(--accent-red); }
        .policy-icon { font-size: 0.9rem; }
        .warning-banner {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: var(--accent-amber);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            margin-bottom: 1.5rem;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="change-pw-container">
        <div class="change-pw-card">
            <h1>🔐 Change Your Password</h1>
            <p class="subtitle">{{ subtitle }}</p>

            {% if is_forced %}
            <div class="warning-banner">
                ⚠️ You must change your temporary password before accessing the system.
            </div>
            {% endif %}

            <div id="error-msg" class="error-msg"></div>
            <div id="success-msg" class="success-msg"></div>

            <div class="policy-box">
                <h3>Password Requirements</h3>
                <div class="policy-item" id="pol-length">
                    <span class="policy-icon">○</span> At least 8 characters
                </div>
                <div class="policy-item" id="pol-upper">
                    <span class="policy-icon">○</span> One uppercase letter (A-Z)
                </div>
                <div class="policy-item" id="pol-lower">
                    <span class="policy-icon">○</span> One lowercase letter (a-z)
                </div>
                <div class="policy-item" id="pol-digit">
                    <span class="policy-icon">○</span> One digit (0-9)
                </div>
                <div class="policy-item" id="pol-special">
                    <span class="policy-icon">○</span> One special character (!@#$%^&*...)
                </div>
            </div>

            <form id="change-pw-form" onsubmit="handleChangePassword(event)">
                <div class="form-group">
                    <label>New Password</label>
                    <input type="password" id="new-password" placeholder="Enter new password"
                           required oninput="checkPolicy()" autocomplete="new-password">
                </div>
                <div class="form-group">
                    <label>Confirm Password</label>
                    <input type="password" id="confirm-password" placeholder="Confirm new password"
                           required autocomplete="new-password">
                </div>
                <button type="submit" class="submit-btn" id="submit-btn">Change Password</button>
            </form>

            {% if not is_forced %}
            <div style="text-align: center; margin-top: 1rem;">
                <a href="{{ back_url }}" style="color: var(--text-muted); font-size: 0.85rem;">← Back to Dashboard</a>
            </div>
            {% endif %}
        </div>
    </div>

    <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js"></script>
    <script>
        const firebaseConfig = {{ firebase_config | tojson }};
        firebase.initializeApp(firebaseConfig);

        function checkPolicy() {
            const pw = document.getElementById('new-password').value;
            const checks = [
                { id: 'pol-length',  pass: pw.length >= 8 },
                { id: 'pol-upper',   pass: /[A-Z]/.test(pw) },
                { id: 'pol-lower',   pass: /[a-z]/.test(pw) },
                { id: 'pol-digit',   pass: /[0-9]/.test(pw) },
                { id: 'pol-special', pass: /[!@#$%^&*()_+\\-=\\[\\]{}|;:,.<>?/~`]/.test(pw) },
            ];
            checks.forEach(c => {
                const el = document.getElementById(c.id);
                el.className = 'policy-item ' + (c.pass ? 'pass' : 'fail');
                el.querySelector('.policy-icon').textContent = c.pass ? '✓' : '✗';
            });
        }

        async function handleChangePassword(e) {
            e.preventDefault();
            const btn = document.getElementById('submit-btn');
            const errorDiv = document.getElementById('error-msg');
            const successDiv = document.getElementById('success-msg');
            const newPw = document.getElementById('new-password').value;
            const confirmPw = document.getElementById('confirm-password').value;

            errorDiv.style.display = 'none';
            successDiv.style.display = 'none';

            if (newPw !== confirmPw) {
                errorDiv.textContent = 'Passwords do not match';
                errorDiv.style.display = 'block';
                return;
            }

            // Client-side policy check
            const checks = [
                newPw.length >= 8,
                /[A-Z]/.test(newPw),
                /[a-z]/.test(newPw),
                /[0-9]/.test(newPw),
                /[!@#$%^&*()_+\\-=\\[\\]{}|;:,.<>?/~`]/.test(newPw),
            ];
            if (!checks.every(Boolean)) {
                errorDiv.textContent = 'Password does not meet all requirements';
                errorDiv.style.display = 'block';
                return;
            }

            btn.disabled = true;
            btn.textContent = 'Updating...';

            try {
                // Update password in Firebase client SDK
                const user = firebase.auth().currentUser;
                if (!user) {
                    // Re-auth needed — use the session email
                    errorDiv.textContent = 'Session expired. Please log in again.';
                    errorDiv.style.display = 'block';
                    btn.disabled = false;
                    btn.textContent = 'Change Password';
                    return;
                }
                await user.updatePassword(newPw);

                // Notify our backend to update the flag
                const response = await fetch('/api/password-changed', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ success: true })
                });
                const data = await response.json();

                if (data.success) {
                    successDiv.textContent = 'Password changed successfully! Redirecting...';
                    successDiv.style.display = 'block';
                    setTimeout(() => { window.location.href = data.redirect; }, 1500);
                } else {
                    errorDiv.textContent = data.error || 'Failed to update';
                    errorDiv.style.display = 'block';
                }
            } catch (err) {
                let msg = 'Failed to change password';
                if (err.code === 'auth/requires-recent-login') {
                    msg = 'Session expired. Please log out and log in again, then change your password.';
                } else if (err.code === 'auth/weak-password') {
                    msg = 'Firebase rejected: password too weak';
                }
                errorDiv.textContent = msg;
                errorDiv.style.display = 'block';
            } finally {
                btn.disabled = false;
                btn.textContent = 'Change Password';
            }
        }
    </script>
</body>
</html>'''


@app.route('/change-password')
def change_password():
    """Password change page — forced for first-time faculty, optional otherwise."""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    is_forced = not user.get('password_changed', False) and user['role'] != 'ADMIN'

    if user['role'] == 'ADMIN':
        back_url = url_for('admin_dashboard')
    else:
        back_url = url_for('faculty_dashboard')

    subtitle = 'Set a secure password to continue' if is_forced else 'Update your password'

    return render_template_string(
        CHANGE_PASSWORD_TEMPLATE,
        firebase_config=FIREBASE_WEB_CONFIG,
        is_forced=is_forced,
        subtitle=subtitle,
        back_url=back_url,
    )


@app.route('/api/password-changed', methods=['POST'])
def api_password_changed():
    """Mark the current user's password as changed in the database."""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    db = DBManager(quiet=True)
    try:
        db.cur.execute(
            "UPDATE user_role SET password_changed = TRUE WHERE uid = %s",
            (user['uid'],)
        )
        db.conn.commit()
    finally:
        db.close()

    # Update session
    session['password_changed'] = True

    if user['role'] == 'ADMIN':
        redirect_url = url_for('admin_dashboard')
    else:
        redirect_url = url_for('faculty_dashboard')

    return jsonify({'success': True, 'redirect': redirect_url})


# ---------------------------------------------------------------------------
# ADMIN: MANAGE USERS (Create faculty accounts)
# ---------------------------------------------------------------------------

@app.route('/admin/manage-users')
@admin_required
def admin_manage_users():
    """Admin page to view existing users and create new faculty accounts."""
    db = DBManager(quiet=True)
    try:
        db.cur.execute(
            """SELECT ur.uid, ur.email, ur.role, ur.password_changed, ur.created_at,
                      f.short_name
               FROM user_role ur
               LEFT JOIN faculty f ON ur.faculty_id = f.faculty_id
               ORDER BY ur.role, ur.email"""
        )
        columns = [desc[0] for desc in db.cur.description]
        users = [dict(zip(columns, row)) for row in db.cur.fetchall()]

        # Get faculty members not yet linked to accounts
        db.cur.execute(
            """SELECT f.faculty_id, f.short_name
               FROM faculty f
               WHERE f.faculty_id NOT IN (
                   SELECT faculty_id FROM user_role WHERE faculty_id IS NOT NULL
               )
               ORDER BY f.short_name"""
        )
        unlinked_faculty = db.cur.fetchall()
    finally:
        db.close()

    users = format_entries(users)

    # Users table
    users_rows = ''
    for u in users:
        role_class = 'role-admin' if u['role'] == 'ADMIN' else 'role-faculty'
        pw_badge = ('<span class="badge badge-active">Changed</span>'
                    if u['password_changed']
                    else '<span class="badge badge-inactive">Pending</span>')
        delete_btn = ''
        if u['role'] != 'ADMIN':
            uid_safe = u['uid']
            email_safe = u['email']
            delete_btn = f'<button class="btn-delete" data-uid="{uid_safe}" data-email="{email_safe}" onclick="deleteUser(this)">🗑️ Delete</button>'
        users_rows += f'''
            <tr id="row-{u['uid']}">
                <td><strong>{u.get("short_name", "—")}</strong></td>
                <td>{u["email"]}</td>
                <td><span class="user-role {role_class}" style="padding:0.15rem 0.6rem;border-radius:20px;font-size:0.7rem;">{u["role"]}</span></td>
                <td>{pw_badge}</td>
                <td>{u.get("created_at", "")}</td>
                <td>{delete_btn}</td>
            </tr>'''

    # Unlinked faculty options
    faculty_options = ''
    for fid, sname in unlinked_faculty:
        faculty_options += f'<option value="{fid}" data-short="{sname}">{sname}</option>'

    content = f'''
    <h1><span class="icon">👥</span>Manage Users</h1>
    <p class="subtitle">Create and manage faculty accounts — only admin can create accounts</p>

    <div class="table-container" style="margin-bottom: 2rem;">
        <div class="table-header">
            <h2>➕ Create Faculty Account</h2>
        </div>
        <div style="padding: 1.5rem;">
            <div id="create-error" class="error-msg" style="display:none;margin-bottom:1rem;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);color:var(--accent-red);padding:0.75rem 1rem;border-radius:8px;font-size:0.85rem;"></div>
            <div id="create-success" class="success-msg" style="display:none;margin-bottom:1rem;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);color:var(--accent-green);padding:0.75rem 1rem;border-radius:8px;font-size:0.85rem;"></div>

            <form id="create-user-form" onsubmit="createUser(event)" style="display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end;">
                <div class="filter-group">
                    <label>Link to Faculty (optional)</label>
                    <select id="faculty-select" onchange="updateEmail()">
                        <option value="">— No link / Custom —</option>
                        {faculty_options}
                    </select>
                </div>
                <div class="filter-group">
                    <label>Email</label>
                    <input type="email" id="user-email" placeholder="faculty@daiict.ac.in" required style="min-width:220px;">
                </div>
                <div class="filter-group">
                    <label>Temp Password <span onclick="document.getElementById('temp-password').value=generatePassword()" style="cursor:pointer;color:var(--accent-blue);font-size:0.7rem;margin-left:0.3rem;">🔄 Regenerate</span></label>
                    <input type="text" id="temp-password" required style="min-width:200px;font-family:monospace;">
                </div>
                <button type="submit" class="btn btn-green" id="create-btn">Create Account</button>
            </form>
        </div>
    </div>

    <div class="table-container">
        <div class="table-header">
            <h2>📋 All User Accounts</h2>
            <span class="table-count">{len(users)} users</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>Faculty</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Password Status</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>{users_rows}</tbody>
            </table>
        </div>
    </div>

    <script>
    function generatePassword() {{
        const upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
        const lower = 'abcdefghjkmnpqrstuvwxyz';
        const digits = '23456789';
        const special = '!@#$%&*';
        let pw = '';
        pw += upper[Math.floor(Math.random() * upper.length)];
        pw += lower[Math.floor(Math.random() * lower.length)];
        pw += digits[Math.floor(Math.random() * digits.length)];
        pw += special[Math.floor(Math.random() * special.length)];
        const all = upper + lower + digits + special;
        for (let i = 0; i < 8; i++) {{
            pw += all[Math.floor(Math.random() * all.length)];
        }}
        // Shuffle
        pw = pw.split('').sort(() => Math.random() - 0.5).join('');
        return pw;
    }}

    function updateEmail() {{
        const sel = document.getElementById('faculty-select');
        const opt = sel.options[sel.selectedIndex];
        const short = opt.getAttribute('data-short') || '';
        if (short) {{
            document.getElementById('user-email').value = short.toLowerCase() + '@daiict.ac.in';
        }}
        document.getElementById('temp-password').value = generatePassword();
    }}

    async function createUser(e) {{
        e.preventDefault();
        const btn = document.getElementById('create-btn');
        const errorDiv = document.getElementById('create-error');
        const successDiv = document.getElementById('create-success');
        const facultyId = document.getElementById('faculty-select').value;
        const email = document.getElementById('user-email').value;
        const password = document.getElementById('temp-password').value;

        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';

        if (!email || !password) {{
            errorDiv.textContent = 'Please enter email and password';
            errorDiv.style.display = 'block';
            return;
        }}

        btn.disabled = true;
        btn.textContent = 'Creating...';

        try {{
            const resp = await fetch('/api/admin/create-user', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ faculty_id: facultyId, email: email, password: password }})
            }});
            const data = await resp.json();

            if (data.success) {{
                successDiv.innerHTML = 'Account created!<br><strong>Email:</strong> ' + email +
                    '<br><strong>Temporary Password:</strong> <code style="background:var(--bg-secondary);padding:0.2rem 0.5rem;border-radius:4px;">' +
                    password + '</code><br><em>Share this with the faculty member. They must change it on first login.</em>';
                successDiv.style.display = 'block';
                // Remove the option from dropdown
                const sel = document.getElementById('faculty-select');
                sel.remove(sel.selectedIndex);
                document.getElementById('user-email').value = '';
                document.getElementById('temp-password').value = '';
                // Reload after a moment to update the table
                setTimeout(() => location.reload(), 3000);
            }} else {{
                errorDiv.textContent = data.error || 'Failed to create account';
                errorDiv.style.display = 'block';
            }}
        }} catch (err) {{
            errorDiv.textContent = 'Network error: ' + err.message;
            errorDiv.style.display = 'block';
        }} finally {{
            btn.disabled = false;
            btn.textContent = 'Create Account';
        }}
    }}

    async function deleteUser(btn) {{
        const uid = btn.getAttribute('data-uid');
        const email = btn.getAttribute('data-email');
        if (!confirm('Delete account for ' + email + '?\\n\\nThis will remove their Firebase account and they will need to be re-created.')) return;

        btn.disabled = true;
        btn.textContent = 'Deleting...';

        try {{
            const resp = await fetch('/api/admin/delete-user', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ uid: uid }})
            }});
            const data = await resp.json();

            if (data.success) {{
                const row = document.getElementById('row-' + uid);
                if (row) {{
                    row.style.transition = 'opacity 0.4s';
                    row.style.opacity = '0';
                    window.setTimeout(function() {{
                        row.remove();
                        window.setTimeout(function() {{ location.reload(); }}, 400);
                    }}, 400);
                }} else {{
                    location.reload();
                }}
            }} else {{
                alert('Delete failed: ' + (data.error || 'Unknown error'));
                btn.disabled = false;
                btn.textContent = '🗑️ Delete';
            }}
        }} catch (err) {{
            alert('Network error: ' + err.message);
            btn.disabled = false;
            btn.textContent = '🗑️ Delete';
        }}
    }}
    </script>
    '''

    return page_shell('Manage Users', get_current_user(), 'users', content)


# ---------------------------------------------------------------------------
# Admin Generate Timetable Page — Upload Excel & Run Pipeline
# ---------------------------------------------------------------------------

@app.route('/admin/generate')
@admin_required
def admin_generate():
    """Admin page to upload slot Excel and generate timetable."""
    # Fetch past snapshots for seed-from-previous dropdown
    seed_options = ''
    try:
        db = DBManager(quiet=True)
        snapshots = db.list_snapshots()
        db.close()
        for s in snapshots:
            snap_id = s[0]
            label = s[1] or f'Snapshot #{snap_id}'
            semester = s[2] or ''
            snap_date = str(s[3])[:10] if s[3] else ''
            seed_options += f'<option value="{snap_id}">{label} — {semester} ({snap_date})</option>'
    except Exception:
        seed_options = ''

    content = f'''
    <h1><span class="icon">🚀</span>Generate Timetable</h1>
    <p class="subtitle">Upload the slot assignment Excel file to generate a new timetable</p>

    <div class="table-container" style="margin-bottom: 2rem;">
        <div class="table-header">
            <h2>📤 Upload & Generate</h2>
        </div>
        <div style="padding: 1.5rem;">
            <div id="gen-error" style="display:none;margin-bottom:1rem;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);color:var(--accent-red);padding:0.75rem 1rem;border-radius:8px;font-size:0.85rem;"></div>
            <div id="gen-success" style="display:none;margin-bottom:1rem;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);color:var(--accent-green);padding:0.75rem 1rem;border-radius:8px;font-size:0.85rem;"></div>

            <form id="generate-form" onsubmit="generateTimetable(event)" enctype="multipart/form-data">
                <div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end;margin-bottom:1.5rem;">
                    <div class="filter-group">
                        <label>Slot Assignment Excel *</label>
                        <input type="file" id="slot-file" accept=".xlsx,.xls" required
                               style="background:var(--bg-secondary);border:1px solid var(--border);color:var(--text-primary);padding:0.5rem;border-radius:6px;">
                    </div>
                    <div class="filter-group">
                        <label>Reference Timetable (optional)</label>
                        <input type="file" id="ref-file" accept=".xlsx,.xls"
                               style="background:var(--bg-secondary);border:1px solid var(--border);color:var(--text-primary);padding:0.5rem;border-radius:6px;">
                    </div>
                </div>
                <div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end;margin-bottom:1.5rem;">
                    <div class="filter-group">
                        <label>Version Label *</label>
                        <input type="text" id="gen-label" placeholder="e.g. Winter 2025-26 v1" required style="min-width:220px;">
                    </div>
                    <div class="filter-group">
                        <label>Year *</label>
                        <select id="gen-year" style="min-width:110px;">
                            <option value="2024">2024</option>
                            <option value="2025">2025</option>
                            <option value="2026" selected>2026</option>
                            <option value="2027">2027</option>
                            <option value="2028">2028</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>Term *</label>
                        <select id="gen-term" style="min-width:140px;">
                            <option value="Winter-Autumn">Winter-Autumn</option>
                            <option value="Summer">Summer</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>Notes (optional)</label>
                        <input type="text" id="gen-notes" placeholder="Any notes..." style="min-width:200px;">
                    </div>
                </div>
                <div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end;margin-bottom:1.5rem;">
                    <div class="filter-group">
                        <label>📊 Seed from Previous Semester (optional)</label>
                        <select id="gen-seed" style="min-width:260px;">
                            <option value="">— No seeding (fresh generation) —</option>
                            {seed_options}
                        </select>
                        <div style="font-size:0.72rem;color:var(--text-muted);margin-top:0.3rem;">Uses historical slot assignments to warm-start the solver, reusing past scheduling decisions where possible.</div>
                    </div>
                </div>
                <button type="submit" id="gen-btn" class="btn btn-green" style="font-size:1rem;padding:0.6rem 2rem;">
                    🚀 Generate Timetable
                </button>
            </form>
        </div>
    </div>

    <!-- Progress Log -->
    <div id="log-container" class="table-container" style="display:none;">
        <div class="table-header">
            <h2>📋 Generation Log</h2>
            <span id="gen-status" class="table-count">Running...</span>
        </div>
        <div style="padding:1rem;">
            <pre id="gen-log" style="background:var(--bg-primary);color:var(--accent-green);font-family:monospace;font-size:0.78rem;padding:1rem;border-radius:8px;border:1px solid var(--border);max-height:400px;overflow-y:auto;white-space:pre-wrap;line-height:1.6;"></pre>
        </div>
    </div>

    <!-- Results -->
    <div id="result-container" class="table-container" style="display:none;margin-top:1rem;">
        <div class="table-header">
            <h2>✅ Results</h2>
        </div>
        <div style="padding:1.5rem;" id="result-content"></div>
    </div>

    <script>
    async function generateTimetable(e) {{
        e.preventDefault();
        var btn = document.getElementById('gen-btn');
        var logContainer = document.getElementById('log-container');
        var logPre = document.getElementById('gen-log');
        var resultContainer = document.getElementById('result-container');
        var errorDiv = document.getElementById('gen-error');
        var successDiv = document.getElementById('gen-success');

        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';
        resultContainer.style.display = 'none';

        var slotFile = document.getElementById('slot-file').files[0];
        if (!slotFile) {{
            errorDiv.textContent = 'Please select a slot Excel file';
            errorDiv.style.display = 'block';
            return;
        }}

        btn.disabled = true;
        btn.textContent = 'Generating...';
        logContainer.style.display = 'block';
        logPre.textContent = 'Starting generation...\\n';
        document.getElementById('gen-status').textContent = 'Running...';

        var formData = new FormData();
        formData.append('slot_file', slotFile);
        var refFile = document.getElementById('ref-file').files[0];
        if (refFile) formData.append('ref_file', refFile);
        formData.append('label', document.getElementById('gen-label').value);
        var year = document.getElementById('gen-year').value;
        var term = document.getElementById('gen-term').value;
        formData.append('semester', year + ' ' + term);
        formData.append('notes', document.getElementById('gen-notes').value);
        var seedId = document.getElementById('gen-seed').value;
        if (seedId) formData.append('seed_snapshot_id', seedId);

        try {{
            var resp = await fetch('/api/admin/generate', {{
                method: 'POST',
                body: formData
            }});
            var data = await resp.json();

            // Show logs
            logPre.textContent = data.logs.join('\\n');
            logPre.scrollTop = logPre.scrollHeight;

            if (data.success) {{
                document.getElementById('gen-status').textContent = '✅ Complete';
                successDiv.textContent = 'Timetable generated and saved as version: ' + document.getElementById('gen-label').value;
                successDiv.style.display = 'block';

                // Show results
                resultContainer.style.display = 'block';
                var html = '<div style="display:flex;gap:2rem;flex-wrap:wrap;">';
                html += '<div><strong>Entries:</strong> ' + data.entry_count + '</div>';
                html += '<div><strong>Violations:</strong> ' + data.violation_count + '</div>';
                html += '<div><strong>Unresolved:</strong> ' + data.unresolved_count + '</div>';
                html += '<div><strong>Snapshot ID:</strong> #' + data.snapshot_id + '</div>';
                html += '</div>';
                html += '<div style="margin-top:1rem;display:flex;gap:1rem;">';
                if (data.output_pdf) {{
                    html += '<a href="/admin/download/' + encodeURIComponent(data.output_pdf) + '" class="btn btn-green">📄 Download PDF</a>';
                }}
                if (data.output_xlsx) {{
                    html += '<a href="/admin/download/' + encodeURIComponent(data.output_xlsx) + '" class="btn" style="background:rgba(79,143,255,0.15);color:var(--accent-blue);border:1px solid var(--accent-blue);">📊 Download Excel</a>';
                }}
                html += '<a href="/admin/timetable" class="btn" style="background:rgba(168,85,247,0.15);color:var(--accent-purple);border:1px solid var(--accent-purple);">📅 View Timetable</a>';
                html += '</div>';

                // Show unscheduled courses warning
                if (data.unscheduled && data.unscheduled.length > 0) {{
                    html += '<div style="margin-top:1.5rem;background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:8px;padding:1rem;">';
                    html += '<h3 style="color:#f59e0b;margin:0 0 0.75rem 0;font-size:0.95rem;">⚠️ ' + data.unscheduled.length + ' Unscheduled Course(s) — No time/room assigned</h3>';
                    html += '<table style="width:100%;font-size:0.8rem;"><thead><tr><th style="text-align:left;padding:0.3rem;">Code</th><th style="text-align:left;padding:0.3rem;">Course</th><th style="text-align:left;padding:0.3rem;">Faculty</th><th style="text-align:left;padding:0.3rem;">Batch</th></tr></thead><tbody>';
                    data.unscheduled.forEach(function(u) {{
                        html += '<tr><td style="padding:0.3rem;color:var(--accent-yellow);font-weight:600;">' + u.course_code + '</td>';
                        html += '<td style="padding:0.3rem;">' + u.course_name + '</td>';
                        html += '<td style="padding:0.3rem;">' + u.faculty + '</td>';
                        html += '<td style="padding:0.3rem;">' + u.sub_batch + ' ' + u.section + '</td></tr>';
                    }});
                    html += '</tbody></table>';
                    html += '<p style="margin:0.75rem 0 0;font-size:0.78rem;color:var(--text-muted);">These courses are in "Slot-Free" in the input Excel and need manual scheduling.</p>';
                    html += '</div>';
                }}

                document.getElementById('result-content').innerHTML = html;
            }} else {{
                document.getElementById('gen-status').textContent = '❌ Failed';
                errorDiv.textContent = data.error || 'Generation failed';
                errorDiv.style.display = 'block';
            }}
        }} catch (err) {{
            errorDiv.textContent = 'Network error: ' + err.message;
            errorDiv.style.display = 'block';
            document.getElementById('gen-status').textContent = '❌ Error';
        }}

        btn.disabled = false;
        btn.textContent = '🚀 Generate Timetable';
    }}
    </script>
    '''
    return page_shell('Generate Timetable', get_current_user(), 'generate', content)


@app.route('/api/admin/generate', methods=['POST'])
@admin_required
def api_admin_generate():
    """Handle Excel upload and run the timetable generation pipeline."""
    import os
    from werkzeug.utils import secure_filename

    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    # Save uploaded files
    slot_file = request.files.get('slot_file')
    if not slot_file:
        return jsonify({'success': False, 'error': 'No slot file uploaded', 'logs': []}), 400

    slot_filename = secure_filename(slot_file.filename)
    slot_path = os.path.join(upload_dir, slot_filename)
    slot_file.save(slot_path)

    ref_path = None
    ref_file = request.files.get('ref_file')
    if ref_file and ref_file.filename:
        ref_filename = secure_filename(ref_file.filename)
        ref_path = os.path.join(upload_dir, ref_filename)
        ref_file.save(ref_path)

    label = request.form.get('label', 'Generated Timetable')
    semester = request.form.get('semester', '')
    notes = request.form.get('notes', '')
    seed_snapshot_id = request.form.get('seed_snapshot_id', '')
    seed_snapshot_id = int(seed_snapshot_id) if seed_snapshot_id else None

    # Output files in uploads dir
    out_base = os.path.splitext(slot_filename)[0]
    output_xlsx = os.path.join(upload_dir, f'Generated_{out_base}.xlsx')
    output_pdf = os.path.join(upload_dir, f'Generated_{out_base}.pdf')

    try:
        from generate_timetable import run_pipeline
        result = run_pipeline(
            input_file=slot_path,
            reference_file=ref_path,
            output_xlsx=output_xlsx,
            output_pdf=output_pdf,
            use_db=True,
            seed_snapshot_id=seed_snapshot_id,
        )

        # Auto-save snapshot
        snapshot_id = None
        if result['success']:
            try:
                db = DBManager(quiet=True)
                snapshot_id = db.save_snapshot(
                    label=label,
                    semester=semester,
                    source_file=slot_filename,
                    notes=notes,
                )
                db.close()
            except Exception as snap_err:
                result['logs'].append(f"⚠ Snapshot save failed: {snap_err}")

        return jsonify({
            'success': result['success'],
            'logs': result['logs'],
            'entry_count': result['entry_count'],
            'violation_count': len(result['violations']),
            'unresolved_count': result['unresolved_count'],
            'unscheduled': result.get('unscheduled', []),
            'output_xlsx': os.path.basename(output_xlsx) if result['success'] else None,
            'output_pdf': os.path.basename(output_pdf) if result['success'] else None,
            'snapshot_id': snapshot_id,
            'error': result.get('error', ''),
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'logs': [traceback.format_exc()],
        }), 500


@app.route('/admin/download/<path:filename>')
@admin_required
def admin_download(filename):
    """Serve generated files for download."""
    import os
    from flask import send_from_directory
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    return send_from_directory(upload_dir, filename, as_attachment=True)


# ---------------------------------------------------------------------------
# Admin History Page — Timetable Versioning
# ---------------------------------------------------------------------------

@app.route('/admin/history')
@admin_required
def admin_history():
    """Admin page to view and manage timetable snapshots."""
    db = DBManager(quiet=True)
    try:
        snapshots = db.list_snapshots()
    finally:
        db.close()

    rows = ''
    for sid, label, semester, source, notes, entries, violations, created in snapshots:
        created_str = created.strftime('%Y-%m-%d %H:%M') if created else '—'
        notes_short = (notes[:60] + '...') if notes and len(notes) > 60 else (notes or '—')
        viol_badge = f'<span class="badge badge-inactive">{violations}</span>' if violations > 0 else '<span class="badge badge-active">0</span>'
        rows += f'''
            <tr>
                <td>#{sid}</td>
                <td><strong>{label}</strong></td>
                <td>{semester or "—"}</td>
                <td>{source or "—"}</td>
                <td>{entries}</td>
                <td>{viol_badge}</td>
                <td>{created_str}</td>
                <td style="white-space:nowrap;">
                    <button class="btn" style="font-size:0.7rem;padding:0.25rem 0.6rem;background:rgba(16,185,129,0.15);color:var(--accent-green);border:1px solid var(--accent-green);border-radius:6px;cursor:pointer;" onclick="restoreSnapshot({sid}, '{label.replace(chr(39), '')}')">♻️ Restore</button>
                    <button class="btn-delete" style="font-size:0.7rem;padding:0.25rem 0.6rem;" onclick="deleteSnapshot({sid})">Delete</button>
                </td>
            </tr>'''

    content = f'''
    <h1><span class="icon">📜</span>Timetable History</h1>
    <p class="subtitle">Browse, restore, or delete previous timetable versions</p>

    <div id="hist-msg" style="display:none;padding:0.75rem 1rem;border-radius:8px;font-size:0.85rem;margin-bottom:1rem;"></div>

    <div class="table-container">
        <div class="table-header">
            <h2>📋 Saved Versions</h2>
            <span class="table-count">{len(snapshots)} snapshots</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Label</th>
                        <th>Semester</th>
                        <th>Source File</th>
                        <th>Entries</th>
                        <th>Violations</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:2rem;">No snapshots yet. Generate a timetable to create the first version.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <script>
    function restoreSnapshot(sid, label) {{
        if (!confirm('Restore "' + label + '" as the active timetable?\\n\\nThis will replace the current timetable.')) return;
        fetch('/api/admin/history/restore', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ snapshot_id: sid }})
        }}).then(function(r) {{ return r.json(); }}).then(function(d) {{
            var el = document.getElementById('hist-msg');
            if (d.success) {{
                el.textContent = 'Restored! ' + d.restored + ' entries loaded, ' + d.skipped + ' skipped.';
                el.style.background = 'rgba(16,185,129,0.1)';
                el.style.border = '1px solid rgba(16,185,129,0.3)';
                el.style.color = 'var(--accent-green)';
            }} else {{
                el.textContent = 'Restore failed: ' + d.error;
                el.style.background = 'rgba(239,68,68,0.1)';
                el.style.border = '1px solid rgba(239,68,68,0.3)';
                el.style.color = 'var(--accent-red)';
            }}
            el.style.display = 'block';
        }});
    }}

    function deleteSnapshot(sid) {{
        if (!confirm('Delete this snapshot permanently?')) return;
        fetch('/api/admin/history/delete', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ snapshot_id: sid }})
        }}).then(function(r) {{ return r.json(); }}).then(function(d) {{
            if (d.success) location.reload();
            else alert('Delete failed: ' + d.error);
        }});
    }}
    </script>
    '''
    return page_shell('Timetable History', get_current_user(), 'history', content)


@app.route('/api/admin/history/restore', methods=['POST'])
@admin_required
def api_history_restore():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        restored, skipped = db.restore_snapshot(data['snapshot_id'])
        return jsonify({'success': True, 'restored': restored, 'skipped': skipped})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/history/delete', methods=['POST'])
@admin_required
def api_history_delete():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.delete_snapshot(data['snapshot_id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Admin Data Manager — CRUD for Faculty, Courses, Batches + Drag-and-Drop Editor
# ---------------------------------------------------------------------------

@app.route('/admin/data-manager')
@admin_required
def admin_data_manager():
    """Admin page for individual CRUD on Faculty, Courses, Batches, and Schedule Editor."""
    tab = request.args.get('tab', 'faculty')
    db = DBManager(quiet=True)
    try:
        faculty_list = db.get_all_faculty()
        course_list = db.get_all_courses()
        batch_list = db.get_all_batches()
        all_entries = db.get_master_timetable()
        all_entries = format_entries(all_entries)
    finally:
        db.close()

    # --- Faculty tab ---
    fac_rows = ''
    for f in faculty_list:
        fac_rows += f'''<tr id="fac-{f['faculty_id']}">
            <td>{f['short_name']}</td>
            <td><input type="text" value="{f.get('name','') or ''}" class="inline-edit" data-id="{f['faculty_id']}" data-field="name" data-entity="faculty"></td>
            <td><input type="text" value="{f.get('department','') or ''}" class="inline-edit" data-id="{f['faculty_id']}" data-field="department" data-entity="faculty"></td>
            <td><input type="text" value="{f.get('email','') or ''}" class="inline-edit" data-id="{f['faculty_id']}" data-field="email" data-entity="faculty"></td>
            <td><button class="btn-delete" onclick="deleteEntity('faculty',{f['faculty_id']},this)">🗑️</button></td>
        </tr>'''

    # --- Course tab ---
    crs_rows = ''
    for c in course_list:
        crs_rows += f'''<tr id="crs-{c['course_id']}">
            <td>{c['course_code']}</td>
            <td><input type="text" value="{c.get('course_name','') or ''}" class="inline-edit" data-id="{c['course_id']}" data-field="course_name" data-entity="course"></td>
            <td><input type="text" value="{c.get('ltpc','') or ''}" class="inline-edit" data-id="{c['course_id']}" data-field="ltpc" data-entity="course" style="width:70px;"></td>
            <td><select class="inline-edit" data-id="{c['course_id']}" data-field="course_type" data-entity="course" style="background:var(--bg-secondary);border:1px solid var(--border-color);color:var(--text-primary);padding:0.2rem;border-radius:4px;">
                <option value="Core" {'selected' if (c.get('course_type','') or '').lower()=='core' else ''}>Core</option>
                <option value="Elective" {'selected' if 'elec' in (c.get('course_type','') or '').lower() else ''}>Elective</option>
            </select></td>
            <td><button class="btn-delete" onclick="deleteEntity('course',{c['course_id']},this)">🗑️</button></td>
        </tr>'''

    # --- Batch tab ---
    bat_rows = ''
    for b in batch_list:
        bat_rows += f'''<tr id="bat-{b['batch_id']}">
            <td>{b['sub_batch']}</td>
            <td>{b['section']}</td>
            <td><input type="text" value="{b.get('program_name','') or ''}" class="inline-edit" data-id="{b['batch_id']}" data-field="program_name" data-entity="batch"></td>
            <td><input type="number" value="{b.get('headcount',0)}" class="inline-edit" data-id="{b['batch_id']}" data-field="headcount" data-entity="batch" style="width:70px;"></td>
            <td><button class="btn-delete" onclick="deleteEntity('batch',{b['batch_id']},this)">🗑️</button></td>
        </tr>'''

    # --- Schedule Editor grid ---
    days_list = ['Monday','Tuesday','Wednesday','Thursday','Friday']
    periods = ['08:00','09:00','10:00','11:00','12:00']
    period_labels = ['8:00–8:50','9:00–9:50','10:00–10:50','11:00–11:50','12:00–12:50']
    sched = {}
    for e in all_entries:
        day = e.get('day_of_week','')
        start = str(e.get('start_time',''))[:5]
        sched.setdefault((day, start), []).append(e)

    dnd_html = '<div class="dnd-grid"><div class="mg-header"></div>'
    for day in days_list:
        dnd_html += f'<div class="mg-header">{day}</div>'
    for pi, period in enumerate(periods):
        dnd_html += f'<div class="mg-time">{period_labels[pi]}</div>'
        for day in days_list:
            cell_id = f"cell-{day}-{period.replace(':','-')}"
            entries_in_cell = sched.get((day, period), [])
            cards = ''
            seen = set()
            for e in entries_in_cell:
                dk = (e.get('course_code',''), e.get('sub_batch',''), e.get('section',''))
                if dk in seen: continue
                seen.add(dk)
                tid = e.get('timetable_id', 0)
                code = e.get('course_code','?')
                fac = e.get('faculty_short_name','') or ''
                room = e.get('room_number','') or '-'
                batch = e.get('sub_batch','')
                cards += f'<div class="dnd-card" draggable="true" data-tid="{tid}" data-code="{code}" data-day="{day}" data-time="{period}" ondragstart="onDragStart(event)" ondragend="onDragEnd(event)"><span class="dnd-code">{code}</span> · {fac}<br><small>{batch} · {room}</small></div>'
            dnd_html += f'<div class="dnd-cell" id="{cell_id}" data-day="{day}" data-time="{period}" ondragover="onDragOver(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event)">{cards}</div>'
    dnd_html += '</div>'

    tab_active = lambda t: 'active' if tab == t else ''

    content = f'''
    <h1><span class="icon">🗄️</span>Data Manager</h1>
    <p class="subtitle">Add, edit, or delete individual records — no Excel upload needed</p>

    <div class="view-toggle" style="margin-bottom:1.5rem;">
        <button class="{tab_active('faculty')}" onclick="location.href='?tab=faculty'">👤 Faculty</button>
        <button class="{tab_active('courses')}" onclick="location.href='?tab=courses'">📚 Courses</button>
        <button class="{tab_active('batches')}" onclick="location.href='?tab=batches'">🎓 Batches</button>
        <button class="{tab_active('editor')}" onclick="location.href='?tab=editor'">✏️ Schedule Editor</button>
    </div>

    <div id="tab-faculty" style="display:{'block' if tab=='faculty' else 'none'};">
        <div class="table-container">
            <div class="table-header"><h2>Faculty</h2><span class="table-count">{len(faculty_list)} records</span></div>
            <div style="padding:1rem;">
                <form onsubmit="addEntity(event,'faculty')" style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem;">
                    <input type="text" id="add-fac-short" placeholder="Short Name *" required style="width:100px;">
                    <input type="text" id="add-fac-name" placeholder="Full Name" style="width:150px;">
                    <input type="text" id="add-fac-dept" placeholder="Department" style="width:120px;">
                    <input type="text" id="add-fac-email" placeholder="Email" style="width:180px;">
                    <button type="submit" class="btn">+ Add</button>
                </form>
            </div>
            <div class="table-scroll"><table><thead><tr><th>Short Name</th><th>Full Name</th><th>Department</th><th>Email</th><th></th></tr></thead><tbody>{fac_rows}</tbody></table></div>
        </div>
    </div>

    <div id="tab-courses" style="display:{'block' if tab=='courses' else 'none'};">
        <div class="table-container">
            <div class="table-header"><h2>Courses</h2><span class="table-count">{len(course_list)} records</span></div>
            <div style="padding:1rem;">
                <form onsubmit="addEntity(event,'course')" style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem;">
                    <input type="text" id="add-crs-code" placeholder="Course Code *" required style="width:100px;">
                    <input type="text" id="add-crs-name" placeholder="Course Name *" required style="width:180px;">
                    <input type="text" id="add-crs-ltpc" placeholder="L-T-P-C" style="width:80px;">
                    <select id="add-crs-type" style="background:var(--bg-secondary);border:1px solid var(--border-color);color:var(--text-primary);padding:0.4rem;border-radius:6px;">
                        <option value="Core">Core</option><option value="Elective">Elective</option>
                    </select>
                    <button type="submit" class="btn">+ Add</button>
                </form>
            </div>
            <div class="table-scroll"><table><thead><tr><th>Code</th><th>Name</th><th>L-T-P-C</th><th>Type</th><th></th></tr></thead><tbody>{crs_rows}</tbody></table></div>
        </div>
    </div>

    <div id="tab-batches" style="display:{'block' if tab=='batches' else 'none'};">
        <div class="table-container">
            <div class="table-header"><h2>Student Batches</h2><span class="table-count">{len(batch_list)} records</span></div>
            <div style="padding:1rem;">
                <form onsubmit="addEntity(event,'batch')" style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem;">
                    <input type="text" id="add-bat-sub" placeholder="Sub Batch *" required style="width:100px;">
                    <input type="text" id="add-bat-sec" placeholder="Section" value="All" style="width:80px;">
                    <input type="text" id="add-bat-prog" placeholder="Program" style="width:120px;">
                    <input type="number" id="add-bat-hc" placeholder="Headcount" value="0" style="width:90px;">
                    <button type="submit" class="btn">+ Add</button>
                </form>
            </div>
            <div class="table-scroll"><table><thead><tr><th>Sub Batch</th><th>Section</th><th>Program</th><th>Headcount</th><th></th></tr></thead><tbody>{bat_rows}</tbody></table></div>
        </div>
    </div>

    <div id="tab-editor" style="display:{'block' if tab=='editor' else 'none'};">
        <div class="table-container">
            <div class="table-header"><h2>✏️ Schedule Editor</h2><span class="table-count">Drag courses to rearrange</span></div>
            <div style="padding:1rem;">
                <div id="pending-box" class="pending-changes" style="display:none;">
                    <strong style="color:var(--accent-amber);">⏳ Pending Changes:</strong>
                    <div id="pending-list"></div>
                    <div style="margin-top:0.75rem;display:flex;gap:0.5rem;">
                        <button class="btn-confirm" onclick="showSaveModal()">💾 Save Changes</button>
                        <button class="btn-danger" onclick="discardChanges()">✖ Discard</button>
                    </div>
                </div>
                {dnd_html}
            </div>
        </div>
    </div>

    <!-- Save Confirmation Modal -->
    <div class="modal-overlay" id="save-modal">
        <div class="modal-box">
            <h3>⚠️ Confirm Schedule Changes</h3>
            <p>Moving courses may cause scheduling conflicts such as room double-booking or faculty clashes. The system will not automatically validate these changes.<br><br>Are you sure you want to save?</p>
            <div class="modal-actions">
                <button class="btn-danger" onclick="closeSaveModal()">Cancel</button>
                <button class="btn-confirm" onclick="saveChanges()">Yes, Save Changes</button>
            </div>
        </div>
    </div>

    <script>
    // --- Inline Edit ---
    document.querySelectorAll('.inline-edit').forEach(function(el) {{
        el.addEventListener('change', function() {{
            var entity = this.dataset.entity;
            var id = this.dataset.id;
            var field = this.dataset.field;
            var value = this.value;
            fetch('/api/admin/data/' + entity + '/update', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{id: parseInt(id), field: field, value: value}})
            }}).then(r => r.json()).then(d => {{
                if (!d.success) alert('Update failed: ' + d.error);
            }});
        }});
    }});

    // --- Add Entity ---
    function addEntity(e, type) {{
        e.preventDefault();
        var body = {{}};
        if (type === 'faculty') {{
            body = {{short_name: document.getElementById('add-fac-short').value, name: document.getElementById('add-fac-name').value, department: document.getElementById('add-fac-dept').value, email: document.getElementById('add-fac-email').value}};
        }} else if (type === 'course') {{
            body = {{course_code: document.getElementById('add-crs-code').value, course_name: document.getElementById('add-crs-name').value, ltpc: document.getElementById('add-crs-ltpc').value, course_type: document.getElementById('add-crs-type').value}};
        }} else if (type === 'batch') {{
            body = {{sub_batch: document.getElementById('add-bat-sub').value, section: document.getElementById('add-bat-sec').value, program_name: document.getElementById('add-bat-prog').value, headcount: parseInt(document.getElementById('add-bat-hc').value) || 0}};
        }}
        fetch('/api/admin/data/' + type + '/add', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(body)
        }}).then(r => r.json()).then(d => {{
            if (d.success) location.reload();
            else alert('Add failed: ' + d.error);
        }});
    }}

    // --- Delete Entity ---
    function deleteEntity(type, id, btn) {{
        if (!confirm('Delete this record? Related timetable entries may also be removed.')) return;
        btn.disabled = true;
        fetch('/api/admin/data/' + type + '/delete', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{id: id}})
        }}).then(r => r.json()).then(d => {{
            if (d.success) location.reload();
            else {{ alert('Delete failed: ' + d.error); btn.disabled = false; }}
        }});
    }}

    // --- Drag and Drop ---
    var pendingMoves = [];
    function onDragStart(e) {{
        e.dataTransfer.setData('text/plain', JSON.stringify({{tid: e.target.dataset.tid, code: e.target.dataset.code, day: e.target.dataset.day, time: e.target.dataset.time}}));
        e.target.classList.add('dragging');
    }}
    function onDragEnd(e) {{ e.target.classList.remove('dragging'); }}
    function onDragOver(e) {{ e.preventDefault(); e.currentTarget.classList.add('drag-over'); }}
    function onDragLeave(e) {{ e.currentTarget.classList.remove('drag-over'); }}
    function onDrop(e) {{
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        var src = JSON.parse(e.dataTransfer.getData('text/plain'));
        var destDay = e.currentTarget.dataset.day;
        var destTime = e.currentTarget.dataset.time;
        if (src.day === destDay && src.time === destTime) return;
        // Move card visually
        var card = document.querySelector('[data-tid="' + src.tid + '"]');
        if (card) {{
            card.dataset.day = destDay;
            card.dataset.time = destTime;
            e.currentTarget.appendChild(card);
        }}
        pendingMoves.push({{timetable_id: parseInt(src.tid), code: src.code, from_day: src.day, from_time: src.time, to_day: destDay, to_time: destTime}});
        renderPending();
    }}
    function renderPending() {{
        var box = document.getElementById('pending-box');
        var list = document.getElementById('pending-list');
        if (pendingMoves.length === 0) {{ box.style.display = 'none'; return; }}
        box.style.display = 'block';
        list.innerHTML = pendingMoves.map(function(m) {{
            return '<div class="pending-item"><strong>' + m.code + '</strong>: ' + m.from_day + ' ' + m.from_time + ' <span class="arrow">→</span> ' + m.to_day + ' ' + m.to_time + '</div>';
        }}).join('');
    }}
    function discardChanges() {{ pendingMoves = []; renderPending(); location.reload(); }}
    function showSaveModal() {{ document.getElementById('save-modal').classList.add('show'); }}
    function closeSaveModal() {{ document.getElementById('save-modal').classList.remove('show'); }}
    function saveChanges() {{
        closeSaveModal();
        fetch('/api/admin/move-entries', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{moves: pendingMoves}})
        }}).then(r => r.json()).then(d => {{
            if (d.success) {{ alert('Saved ' + d.moved + ' change(s).'); location.reload(); }}
            else alert('Save failed: ' + (d.error || d.errors.join(', ')));
        }});
    }}
    </script>
    '''
    return page_shell('Data Manager', get_current_user(), 'data', content)


# --- Data Manager API Endpoints ---

@app.route('/api/admin/data/faculty/add', methods=['POST'])
@admin_required
def api_data_faculty_add():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        fid = db.add_faculty(data['short_name'], data.get('name'), data.get('department'), data.get('email'))
        return jsonify({'success': True, 'id': fid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/admin/data/faculty/update', methods=['POST'])
@admin_required
def api_data_faculty_update():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.update_faculty(data['id'], **{data['field']: data['value']})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/admin/data/faculty/delete', methods=['POST'])
@admin_required
def api_data_faculty_delete():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.delete_faculty(data['id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/admin/data/course/add', methods=['POST'])
@admin_required
def api_data_course_add():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        cid = db.add_course(data['course_code'], data['course_name'], data.get('ltpc',''), data.get('course_type','Core'))
        return jsonify({'success': True, 'id': cid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/admin/data/course/update', methods=['POST'])
@admin_required
def api_data_course_update():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.update_course(data['id'], **{data['field']: data['value']})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/admin/data/course/delete', methods=['POST'])
@admin_required
def api_data_course_delete():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.delete_course(data['id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/admin/data/batch/add', methods=['POST'])
@admin_required
def api_data_batch_add():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        bid = db.add_batch(data['sub_batch'], data.get('section','All'), data.get('program_name',''), data.get('headcount',0))
        return jsonify({'success': True, 'id': bid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/admin/data/batch/update', methods=['POST'])
@admin_required
def api_data_batch_update():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.update_batch_fields(data['id'], **{data['field']: data['value']})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/admin/data/batch/delete', methods=['POST'])
@admin_required
def api_data_batch_delete():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.delete_batch(data['id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/admin/move-entries', methods=['POST'])
@admin_required
def api_move_entries():
    """Batch move timetable entries to new slots (drag-and-drop save)."""
    data = request.get_json()
    moves_raw = data.get('moves', [])
    db = DBManager(quiet=True)
    try:
        moves = []
        for m in moves_raw:
            slot_id = db.get_slot_id(m['to_day'], m['to_time'])
            if not slot_id:
                return jsonify({'success': False, 'error': f"No slot found for {m['to_day']} {m['to_time']}"}), 400
            moves.append({'timetable_id': m['timetable_id'], 'new_slot_id': slot_id})
        moved, errors = db.move_timetable_entries(moves)
        if errors:
            return jsonify({'success': False, 'errors': errors})
        return jsonify({'success': True, 'moved': moved})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Admin Configuration Page — Rooms, Batches, Electives, Slots, Overlaps
# ---------------------------------------------------------------------------

@app.route('/admin/configuration')
@admin_required
def admin_configuration():
    """Admin page to configure rooms, batches, electives, slots, and overlap rules."""
    db = DBManager(quiet=True)
    try:
        # Rooms
        db.cur.execute("SELECT room_id, room_number, room_type, capacity FROM room ORDER BY room_number")
        rooms = db.cur.fetchall()

        # Batches with headcounts
        db.cur.execute("SELECT batch_id, sub_batch, section, headcount FROM student_batch ORDER BY sub_batch, section")
        batches = db.cur.fetchall()

        # Elective enrollments
        db.cur.execute("""
            SELECT ee.enrollment_id, ee.course_code, COALESCE(c.course_name, '—'), ee.enrollment
            FROM elective_enrollment ee
            LEFT JOIN course c ON ee.course_code = c.course_code
            WHERE ee.semester = 'current'
            ORDER BY ee.course_code
        """)
        electives = db.cur.fetchall()

        # Slot matrix
        db.cur.execute("SELECT slot_id, day_of_week, start_time, end_time, slot_group FROM time_slot ORDER BY day_of_week, start_time")
        slots = db.cur.fetchall()

        # Overlap rules
        db.cur.execute("SELECT rule_id, batch_a, section_a, batch_b, section_b, description FROM batch_overlap_rule ORDER BY rule_id")
        overlaps = db.cur.fetchall()
    finally:
        db.close()

    # Build Rooms table
    rooms_rows = ''
    for rid, rnum, rtype, cap in rooms:
        rooms_rows += f'''
            <tr>
                <td><strong>{rnum}</strong></td>
                <td>{rtype or "Lecture Hall"}</td>
                <td><input type="number" value="{cap}" min="0" style="width:80px;background:var(--bg-secondary);border:1px solid var(--border);color:var(--text-primary);padding:0.3rem;border-radius:4px;text-align:center;" onchange="updateRoom('{rnum}', this.value)"></td>
                <td><button class="btn-delete" onclick="deleteRoom('{rnum}')">Delete</button></td>
            </tr>'''

    # Build Batches table
    batches_rows = ''
    for bid, sb, sec, hc in batches:
        batches_rows += f'''
            <tr>
                <td>{sb}</td>
                <td>{sec}</td>
                <td><input type="number" value="{hc}" min="0" style="width:80px;background:var(--bg-secondary);border:1px solid var(--border);color:var(--text-primary);padding:0.3rem;border-radius:4px;text-align:center;" onchange="updateBatch({bid}, this.value)"></td>
            </tr>'''

    # Build Electives table
    electives_rows = ''
    for eid, code, name, enr in electives:
        electives_rows += f'''
            <tr>
                <td><strong>{code}</strong></td>
                <td>{name}</td>
                <td><input type="number" value="{enr}" min="0" style="width:80px;background:var(--bg-secondary);border:1px solid var(--border);color:var(--text-primary);padding:0.3rem;border-radius:4px;text-align:center;" onchange="updateElective('{code}', this.value)"></td>
                <td><button class="btn-delete" onclick="deleteElective('{code}')">Delete</button></td>
            </tr>'''

    # Build Slot Matrix grid
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    slot_grid = {}
    for sid, day, st, et, sg in slots:
        start_str = st.strftime('%H:%M') if hasattr(st, 'strftime') else str(st)[:5]
        end_str = et.strftime('%H:%M') if hasattr(et, 'strftime') else str(et)[:5]
        period = f"{start_str}-{end_str}"
        if period not in slot_grid:
            slot_grid[period] = {}
        slot_grid[period][day] = (sid, sg)

    slot_headers = ''.join(f'<th>{d}</th>' for d in days_order)
    slot_rows = ''
    for period in sorted(slot_grid.keys()):
        cells = f'<td><strong>{period}</strong></td>'
        for day in days_order:
            if day in slot_grid[period]:
                sid, sg = slot_grid[period][day]
                cells += f'<td><input type="text" value="{sg}" style="width:90px;background:var(--bg-secondary);border:1px solid var(--border);color:var(--text-primary);padding:0.3rem;border-radius:4px;text-align:center;font-size:0.8rem;" onchange="updateSlot({sid}, this.value)"></td>'
            else:
                cells += '<td>—</td>'
        slot_rows += f'<tr>{cells}</tr>'

    # Build Overlaps table
    overlaps_rows = ''
    for oid, ba, sa, bb, sb, desc in overlaps:
        overlaps_rows += f'''
            <tr>
                <td>{ba} ({sa})</td>
                <td>→</td>
                <td>{bb} ({sb})</td>
                <td>{desc or ""}</td>
                <td><button class="btn-delete" onclick="deleteOverlap({oid})">Delete</button></td>
            </tr>'''

    content = f'''
    <h1><span class="icon">⚙️</span>Configuration</h1>
    <p class="subtitle">Manage rooms, batch sizes, elective enrollments, slot matrix, and batch overlaps</p>

    <div id="cfg-msg" style="display:none;padding:0.75rem 1rem;border-radius:8px;font-size:0.85rem;margin-bottom:1rem;"></div>

    <!-- Tab Navigation -->
    <div style="display:flex;gap:0.5rem;margin-bottom:1.5rem;flex-wrap:wrap;">
        <button class="tab-btn active" onclick="switchTab('rooms', this)">🏫 Rooms ({len(rooms)})</button>
        <button class="tab-btn" onclick="switchTab('batches', this)">👥 Batches ({len(batches)})</button>
        <button class="tab-btn" onclick="switchTab('electives', this)">📚 Elective Enrollment ({len(electives)})</button>
        <button class="tab-btn" onclick="switchTab('slots', this)">🕐 Slot Matrix</button>
        <button class="tab-btn" onclick="switchTab('overlaps', this)">🔗 Batch Overlaps ({len(overlaps)})</button>
    </div>

    <!-- ROOMS TAB -->
    <div id="tab-rooms" class="tab-content">
        <div class="table-container">
            <div class="table-header">
                <h2>🏫 Room Capacities</h2>
            </div>
            <div style="padding:1rem;">
                <form onsubmit="addRoom(event)" style="display:flex;gap:0.75rem;align-items:flex-end;margin-bottom:1rem;">
                    <div class="filter-group">
                        <label>Room Number</label>
                        <input type="text" id="new-room" placeholder="e.g. CEP301" required style="width:120px;">
                    </div>
                    <div class="filter-group">
                        <label>Capacity</label>
                        <input type="number" id="new-room-cap" placeholder="120" min="1" required style="width:80px;">
                    </div>
                    <button type="submit" class="btn btn-green">+ Add Room</button>
                </form>
            </div>
            <div class="table-scroll">
                <table>
                    <thead><tr><th>Room</th><th>Type</th><th>Capacity</th><th>Actions</th></tr></thead>
                    <tbody>{rooms_rows}</tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- BATCHES TAB -->
    <div id="tab-batches" class="tab-content" style="display:none;">
        <div class="table-container">
            <div class="table-header">
                <h2>👥 Batch Headcounts</h2>
                <span class="table-count">Edit headcounts inline</span>
            </div>
            <div class="table-scroll">
                <table>
                    <thead><tr><th>Sub-Batch</th><th>Section</th><th>Headcount</th></tr></thead>
                    <tbody>{batches_rows}</tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- ELECTIVES TAB -->
    <div id="tab-electives" class="tab-content" style="display:none;">
        <div class="table-container">
            <div class="table-header">
                <h2>📚 Elective Enrollments</h2>
            </div>
            <div style="padding:1rem;">
                <form onsubmit="addElective(event)" style="display:flex;gap:0.75rem;align-items:flex-end;margin-bottom:1rem;">
                    <div class="filter-group">
                        <label>Course Code</label>
                        <input type="text" id="new-elective-code" placeholder="e.g. IT505" required style="width:120px;">
                    </div>
                    <div class="filter-group">
                        <label>Enrollment</label>
                        <input type="number" id="new-elective-enr" placeholder="50" min="0" required style="width:80px;">
                    </div>
                    <button type="submit" class="btn btn-green">+ Add Elective</button>
                </form>
            </div>
            <div class="table-scroll">
                <table>
                    <thead><tr><th>Code</th><th>Course Name</th><th>Enrollment</th><th>Actions</th></tr></thead>
                    <tbody>{electives_rows}</tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- SLOT MATRIX TAB -->
    <div id="tab-slots" class="tab-content" style="display:none;">
        <div class="table-container">
            <div class="table-header">
                <h2>🕐 Slot Matrix</h2>
                <span class="table-count">Edit slot assignments inline</span>
            </div>
            <div style="padding:1rem;">
                <form onsubmit="addSlot(event)" style="display:flex;gap:0.75rem;align-items:flex-end;margin-bottom:1rem;">
                    <div class="filter-group">
                        <label>Day</label>
                        <select id="new-slot-day" required>
                            <option value="Monday">Monday</option>
                            <option value="Tuesday">Tuesday</option>
                            <option value="Wednesday">Wednesday</option>
                            <option value="Thursday">Thursday</option>
                            <option value="Friday">Friday</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>Start Time</label>
                        <input type="time" id="new-slot-start" required style="width:120px;">
                    </div>
                    <div class="filter-group">
                        <label>End Time</label>
                        <input type="time" id="new-slot-end" required style="width:120px;">
                    </div>
                    <div class="filter-group">
                        <label>Slot Group</label>
                        <input type="text" id="new-slot-group" placeholder="Slot-9" required style="width:100px;">
                    </div>
                    <button type="submit" class="btn btn-green">+ Add Slot</button>
                </form>
            </div>
            <div class="table-scroll">
                <table>
                    <thead><tr><th>Period</th>{slot_headers}</tr></thead>
                    <tbody>{slot_rows}</tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- OVERLAPS TAB -->
    <div id="tab-overlaps" class="tab-content" style="display:none;">
        <div class="table-container">
            <div class="table-header">
                <h2>🔗 Batch Overlap Rules</h2>
                <span class="table-count">Defines which batches share students</span>
            </div>
            <div style="padding:1rem;">
                <form onsubmit="addOverlap(event)" style="display:flex;gap:0.75rem;align-items:flex-end;flex-wrap:wrap;margin-bottom:1rem;">
                    <div class="filter-group">
                        <label>Batch A</label>
                        <input type="text" id="ov-ba" placeholder="CS-Only" required style="width:120px;">
                    </div>
                    <div class="filter-group">
                        <label>Section A</label>
                        <input type="text" id="ov-sa" value="All" style="width:80px;">
                    </div>
                    <div class="filter-group">
                        <label>Overlaps with Batch B</label>
                        <input type="text" id="ov-bb" placeholder="ICT + CS" required style="width:120px;">
                    </div>
                    <div class="filter-group">
                        <label>Section B</label>
                        <input type="text" id="ov-sb" value="Sec B" style="width:80px;">
                    </div>
                    <div class="filter-group">
                        <label>Description</label>
                        <input type="text" id="ov-desc" placeholder="Optional" style="width:180px;">
                    </div>
                    <button type="submit" class="btn btn-green">+ Add Rule</button>
                </form>
            </div>
            <div class="table-scroll">
                <table>
                    <thead><tr><th>Batch A</th><th></th><th>Batch B</th><th>Description</th><th>Actions</th></tr></thead>
                    <tbody>{overlaps_rows}</tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
    function switchTab(name, btn) {{
        document.querySelectorAll('.tab-content').forEach(function(el) {{ el.style.display = 'none'; }});
        document.querySelectorAll('.tab-btn').forEach(function(el) {{ el.classList.remove('active'); }});
        document.getElementById('tab-' + name).style.display = 'block';
        btn.classList.add('active');
    }}

    function showMsg(text, isError) {{
        var el = document.getElementById('cfg-msg');
        el.textContent = text;
        el.style.display = 'block';
        el.style.background = isError ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)';
        el.style.border = isError ? '1px solid rgba(239,68,68,0.3)' : '1px solid rgba(16,185,129,0.3)';
        el.style.color = isError ? 'var(--accent-red)' : 'var(--accent-green)';
        window.setTimeout(function() {{ el.style.display = 'none'; }}, 3000);
    }}

    function cfgPost(url, body) {{
        return fetch(url, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(body)
        }}).then(function(r) {{ return r.json(); }});
    }}

    // Rooms
    function updateRoom(room, cap) {{
        cfgPost('/api/admin/config/room', {{ room_number: room, capacity: parseInt(cap) }})
            .then(function(d) {{ showMsg(d.success ? 'Room updated' : d.error, !d.success); }});
    }}
    function deleteRoom(room) {{
        if (!confirm('Delete room ' + room + '?')) return;
        cfgPost('/api/admin/config/room/delete', {{ room_number: room }})
            .then(function(d) {{ if (d.success) location.reload(); else showMsg(d.error, true); }});
    }}
    function addRoom(e) {{
        e.preventDefault();
        var room = document.getElementById('new-room').value;
        var cap = parseInt(document.getElementById('new-room-cap').value);
        cfgPost('/api/admin/config/room', {{ room_number: room, capacity: cap }})
            .then(function(d) {{ if (d.success) location.reload(); else showMsg(d.error, true); }});
    }}

    // Batches
    function updateBatch(bid, hc) {{
        cfgPost('/api/admin/config/batch', {{ batch_id: bid, headcount: parseInt(hc) }})
            .then(function(d) {{ showMsg(d.success ? 'Headcount updated' : d.error, !d.success); }});
    }}

    // Electives
    function updateElective(code, enr) {{
        cfgPost('/api/admin/config/elective', {{ course_code: code, enrollment: parseInt(enr) }})
            .then(function(d) {{ showMsg(d.success ? 'Enrollment updated' : d.error, !d.success); }});
    }}
    function deleteElective(code) {{
        if (!confirm('Delete enrollment for ' + code + '?')) return;
        cfgPost('/api/admin/config/elective/delete', {{ course_code: code }})
            .then(function(d) {{ if (d.success) location.reload(); else showMsg(d.error, true); }});
    }}
    function addElective(e) {{
        e.preventDefault();
        var code = document.getElementById('new-elective-code').value;
        var enr = parseInt(document.getElementById('new-elective-enr').value);
        cfgPost('/api/admin/config/elective', {{ course_code: code, enrollment: enr }})
            .then(function(d) {{ if (d.success) location.reload(); else showMsg(d.error, true); }});
    }}

    // Slots
    function updateSlot(sid, sg) {{
        cfgPost('/api/admin/config/slot', {{ slot_id: sid, slot_group: sg }})
            .then(function(d) {{ showMsg(d.success ? 'Slot updated' : d.error, !d.success); }});
    }}
    function addSlot(e) {{
        e.preventDefault();
        cfgPost('/api/admin/config/slot/add', {{
            day: document.getElementById('new-slot-day').value,
            start: document.getElementById('new-slot-start').value,
            end: document.getElementById('new-slot-end').value,
            slot_group: document.getElementById('new-slot-group').value
        }}).then(function(d) {{ if (d.success) location.reload(); else showMsg(d.error, true); }});
    }}

    // Overlaps
    function deleteOverlap(rid) {{
        if (!confirm('Delete this overlap rule?')) return;
        cfgPost('/api/admin/config/overlap/delete', {{ rule_id: rid }})
            .then(function(d) {{ if (d.success) location.reload(); else showMsg(d.error, true); }});
    }}
    function addOverlap(e) {{
        e.preventDefault();
        cfgPost('/api/admin/config/overlap', {{
            batch_a: document.getElementById('ov-ba').value,
            section_a: document.getElementById('ov-sa').value,
            batch_b: document.getElementById('ov-bb').value,
            section_b: document.getElementById('ov-sb').value,
            description: document.getElementById('ov-desc').value
        }}).then(function(d) {{ if (d.success) location.reload(); else showMsg(d.error, true); }});
    }}
    </script>
    '''

    return page_shell('Configuration', get_current_user(), 'config', content)


# ---------------------------------------------------------------------------
# Configuration API Endpoints (admin only)
# ---------------------------------------------------------------------------

@app.route('/api/admin/config/room', methods=['POST'])
@admin_required
def api_config_room():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.update_room_capacity(data['room_number'], data['capacity'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/config/room/delete', methods=['POST'])
@admin_required
def api_config_room_delete():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.delete_room(data['room_number'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/config/batch', methods=['POST'])
@admin_required
def api_config_batch():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.update_batch_headcount(data['batch_id'], data['headcount'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/config/elective', methods=['POST'])
@admin_required
def api_config_elective():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.upsert_elective_enrollment(data['course_code'], data['enrollment'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/config/elective/delete', methods=['POST'])
@admin_required
def api_config_elective_delete():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.delete_elective_enrollment(data['course_code'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/config/slot', methods=['POST'])
@admin_required
def api_config_slot():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.update_slot_group(data['slot_id'], data['slot_group'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/config/slot/add', methods=['POST'])
@admin_required
def api_config_slot_add():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.add_time_slot(data['day'], data['start'], data['end'], data['slot_group'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/config/overlap', methods=['POST'])
@admin_required
def api_config_overlap():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.upsert_overlap_rule(data['batch_a'], data['section_a'], data['batch_b'], data['section_b'], data.get('description', ''))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/config/overlap/delete', methods=['POST'])
@admin_required
def api_config_overlap_delete():
    data = request.get_json()
    db = DBManager(quiet=True)
    try:
        db.delete_overlap_rule(data['rule_id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/create-user', methods=['POST'])
@admin_required
def api_admin_create_user():
    """Admin API endpoint to create a new faculty Firebase account."""
    data = request.get_json()
    faculty_id = data.get('faculty_id') or None  # Optional
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({'success': False, 'error': 'Email and password are required'}), 400

    # Validate password against policy
    ok, err_msg = validate_password(password)
    if not ok:
        return jsonify({'success': False, 'error': err_msg}), 400

    if not FIREBASE_INITIALIZED:
        return jsonify({'success': False, 'error': 'Firebase not configured'}), 500

    try:
        # Create Firebase Auth user
        user_record = firebase_auth.create_user(
            email=email,
            password=password,
            email_verified=True,
        )
        uid = user_record.uid

        # Insert into our database
        fid = int(faculty_id) if faculty_id else None
        db = DBManager(quiet=True)
        try:
            db.cur.execute(
                """INSERT INTO user_role (uid, email, role, faculty_id, password_changed)
                   VALUES (%s, %s, 'FACULTY', %s, FALSE)
                   ON CONFLICT (uid) DO UPDATE
                   SET faculty_id = EXCLUDED.faculty_id, role = 'FACULTY'""",
                (uid, email, fid)
            )
            db.conn.commit()
        finally:
            db.close()

        return jsonify({'success': True, 'uid': uid})

    except firebase_admin.exceptions.AlreadyExistsError:
        return jsonify({'success': False,
                        'error': f'Account {email} already exists in Firebase'}), 409
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/delete-user', methods=['POST'])
@admin_required
def api_admin_delete_user():
    """Admin API endpoint to delete a faculty Firebase account."""
    data = request.get_json()
    uid = data.get('uid', '').strip()

    if not uid:
        return jsonify({'success': False, 'error': 'Missing UID'}), 400

    # Prevent deleting admin accounts via API
    db = DBManager(quiet=True)
    try:
        db.cur.execute("SELECT role FROM user_role WHERE uid = %s", (uid,))
        row = db.cur.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        if row[0] == 'ADMIN':
            return jsonify({'success': False, 'error': 'Cannot delete admin accounts'}), 403

        # Delete from database first
        db.cur.execute("DELETE FROM user_role WHERE uid = %s", (uid,))
        db.conn.commit()
    finally:
        db.close()

    # Delete from Firebase
    if FIREBASE_INITIALIZED:
        try:
            firebase_auth.delete_user(uid)
        except Exception:
            pass  # If Firebase fails, DB record is already gone — user can be re-created

    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# API Endpoints (for programmatic access — admin only)
# ---------------------------------------------------------------------------

@app.route('/api/stats')
@admin_required
def api_stats():
    db = DBManager(quiet=True)
    try:
        return jsonify(db.get_stats())
    finally:
        db.close()


@app.route('/api/timetable')
@admin_required
def api_timetable():
    filters = {}
    for key in ['day_of_week', 'sub_batch', 'faculty', 'room']:
        val = request.args.get(key)
        if val:
            filters[key] = val

    db = DBManager(quiet=True)
    try:
        entries = db.get_master_timetable(filters if filters else None)
        entries = format_entries(entries)
        return jsonify(entries)
    finally:
        db.close()


@app.route('/api/constraints')
@admin_required
def api_constraints():
    db = DBManager(quiet=True)
    try:
        entries = db.get_constraints()
        entries = format_entries(entries)
        return jsonify(entries)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("  Timetable Generator — Web Interface")
    print("  Open http://localhost:5001 in your browser")
    if FIREBASE_INITIALIZED:
        print("  ✓ Firebase Auth: ENABLED")
    else:
        print("  ⚠ Firebase Auth: DISABLED (service account missing)")
    print("=" * 60)
    app.run(debug=True, port=5001)
