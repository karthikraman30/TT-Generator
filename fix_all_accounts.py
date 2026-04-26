#!/usr/bin/env python3
"""
Check and fix all faculty accounts that have Firebase UIDs but must_reset_password is False
"""

from app import create_app
from models import db, Faculty
from routes.admin import _generate_temp_password, _ensure_firebase_admin
from firebase_admin import auth as firebase_auth

def check_and_fix_accounts():
    """Check all faculty accounts and fix those with issues."""
    app = create_app()
    
    with app.app_context():
        # Find all faculty with Firebase UID but must_reset_password = False
        problematic = Faculty.query.filter(
            Faculty.firebase_uid.isnot(None),
            Faculty.must_reset_password == False
        ).all()
        
        if not problematic:
            print("✅ No problematic accounts found. All accounts are properly configured.")
            return
        
        print(f"⚠️  Found {len(problematic)} account(s) with firebase_uid but must_reset_password=False:\n")
        
        for i, faculty in enumerate(problematic, 1):
            print(f"{i}. {faculty.full_name} ({faculty.abbreviation})")
            print(f"   Email: {faculty.email}")
            print(f"   Firebase UID: {faculty.firebase_uid}")
            print(f"   must_reset_password: {faculty.must_reset_password}")
        
        print("\n" + "="*60)
        response = input("\nDo you want to fix these accounts? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("❌ Aborted. No changes made.")
            return
        
        print("\n" + "="*60)
        print("🔧 Fixing accounts...\n")
        
        _ensure_firebase_admin()
        fixed_accounts = []
        
        for faculty in problematic:
            try:
                # Generate new temporary password
                temp_password = _generate_temp_password()
                
                # Update Firebase password
                firebase_auth.update_user(faculty.firebase_uid, password=temp_password)
                
                # Update database
                faculty.must_reset_password = True
                db.session.commit()
                
                fixed_accounts.append({
                    'name': faculty.full_name,
                    'email': faculty.email,
                    'password': temp_password
                })
                
                print(f"✅ Fixed: {faculty.full_name}")
                
            except Exception as e:
                print(f"❌ Error fixing {faculty.full_name}: {e}")
                db.session.rollback()
        
        if fixed_accounts:
            print("\n" + "="*60)
            print("✅ SUCCESSFULLY FIXED ACCOUNTS")
            print("="*60)
            print("\n📋 IMPORTANT: Share these temporary passwords:\n")
            
            for account in fixed_accounts:
                print(f"Name: {account['name']}")
                print(f"Email: {account['email']}")
                print(f"Temporary Password: {account['password']}")
                print("-" * 60)
            
            print("\n⚠️  Users will be forced to change their passwords on first login.")
        else:
            print("\n⚠️  No accounts were fixed.")

if __name__ == '__main__':
    check_and_fix_accounts()
