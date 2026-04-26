#!/usr/bin/env python3
"""
Quick login script to bypass Firebase authentication issues.
Creates an admin session cookie that you can use in your browser.
"""

import sys
from app import app
from models import Faculty

def create_admin_session():
    """Create a session for admin user."""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            # Find an admin user
            admin = Faculty.query.filter_by(role='admin').first()
            
            if not admin:
                print("❌ No admin user found in database!")
                print("   Create an admin user first.")
                return False
            
            # Set session
            sess['user'] = {
                'id': admin.id,
                'name': admin.full_name,
                'abbreviation': admin.abbreviation,
                'email': admin.email,
                'role': admin.role,
            }
            
            print(f"✅ Session created for: {admin.full_name} ({admin.abbreviation})")
            print(f"   Role: {admin.role}")
            print(f"   Email: {admin.email}")
            print("\n📋 To use this session:")
            print("   1. Open your browser")
            print("   2. Go to: http://127.0.0.1:5000/auth/dev-login")
            print("   3. Enter abbreviation: " + admin.abbreviation)
            print("   4. Click 'Dev Login'")
            return True

if __name__ == '__main__':
    with app.app_context():
        if not create_admin_session():
            sys.exit(1)
