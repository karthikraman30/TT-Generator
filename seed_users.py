"""
Firebase Account Seeder
========================
Creates Firebase Auth accounts for all faculty and one admin.
Inserts corresponding user_role rows into PostgreSQL.

Prerequisites:
    1. Firebase project with Email/Password auth enabled
    2. Service account JSON file at the path specified in .env
    3. Database schema already initialized (init_schema.sql)
    4. Faculty table populated (run generate_timetable.py --use-db first)

Usage:
    python seed_users.py
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
import psycopg2

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Intentionally weak — forces mandatory password change on first login.
# Firebase accepts it; the app's own policy blocks re-use of weak passwords.
DEFAULT_PASSWORD = 'daiict2026'
ADMIN_EMAIL = 'admin@daiict.ac.in'
FACULTY_EMAIL_DOMAIN = 'daiict.ac.in'

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------
def get_db_connection():
    """Connect to PostgreSQL using .env configuration."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        dbname=os.getenv('DB_NAME', 'timetable_generator_db'),
        user=os.getenv('DB_USER', os.getenv('USER', 'postgres')),
        password=os.getenv('DB_PASSWORD', ''),
    )


def init_firebase():
    """Initialize Firebase Admin SDK."""
    sa_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH',
                        './firebase-service-account.json')
    if not os.path.exists(sa_path):
        print(f"  [x] Service account file not found: {sa_path}")
        print("  Download it from Firebase Console -> Project Settings -> Service Accounts")
        sys.exit(1)

    cred = credentials.Certificate(sa_path)
    firebase_admin.initialize_app(cred)
    print("  [OK] Firebase Admin SDK initialized")


def create_firebase_user(email, password=DEFAULT_PASSWORD):
    """Create a Firebase Auth user. Returns UID or None if already exists."""
    try:
        user = firebase_auth.create_user(
            email=email,
            password=password,
            email_verified=True,
        )
        return user.uid
    except firebase_admin.exceptions.AlreadyExistsError:
        # User already exists — fetch their UID
        user = firebase_auth.get_user_by_email(email)
        return user.uid
    except Exception as e:
        print(f"  [x] Failed to create {email}: {e}")
        return None


def seed_users():
    """Main seeding logic."""
    print("=" * 60)
    print("  Firebase Account Seeder")
    print("=" * 60)

    # 1. Initialize Firebase
    print("\n[1/4] Initializing Firebase...")
    init_firebase()

    # 2. Connect to database
    print("\n[2/4] Connecting to PostgreSQL...")
    conn = get_db_connection()
    cur = conn.cursor()
    print(f"  [OK] Connected to {os.getenv('DB_NAME', 'timetable_generator_db')}")

    # 3. Create admin account
    print("\n[3/4] Creating admin account...")
    admin_uid = create_firebase_user(ADMIN_EMAIL)
    if admin_uid:
        cur.execute(
            """INSERT INTO user_role (uid, email, role, faculty_id)
               VALUES (%s, %s, 'ADMIN', NULL)
               ON CONFLICT (uid) DO UPDATE SET role = 'ADMIN'""",
            (admin_uid, ADMIN_EMAIL)
        )
        print(f"  [OK] Admin: {ADMIN_EMAIL} (UID: {admin_uid[:12]}...)")

    # 4. Create faculty accounts
    print("\n[4/4] Creating faculty accounts...")
    cur.execute("SELECT faculty_id, short_name FROM faculty ORDER BY short_name")
    faculties = cur.fetchall()

    created = 0
    skipped = 0
    for faculty_id, short_name in faculties:
        email = f"{short_name.lower()}@{FACULTY_EMAIL_DOMAIN}"
        uid = create_firebase_user(email)

        if uid:
            cur.execute(
                """INSERT INTO user_role (uid, email, role, faculty_id)
                   VALUES (%s, %s, 'FACULTY', %s)
                   ON CONFLICT (uid) DO UPDATE
                   SET faculty_id = EXCLUDED.faculty_id,
                       role = 'FACULTY'""",
                (uid, email, faculty_id)
            )
            created += 1
        else:
            skipped += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n  [OK] {created} faculty accounts created/updated")
    if skipped:
        print(f"  [!] {skipped} accounts skipped (errors)")
    print(f"  [OK] 1 admin account created ({ADMIN_EMAIL})")
    print(f"\n  Default password for all accounts: {DEFAULT_PASSWORD}")
    print("  Faculty should change their password on first login.\n")
    print("=" * 60)


if __name__ == '__main__':
    seed_users()
