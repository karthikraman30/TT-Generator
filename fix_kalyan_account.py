#!/usr/bin/env python3
"""
Fix KALYAN SASIDAR's account to require password reset
"""

from app import create_app
from models import db, Faculty
from routes.admin import _generate_temp_password, _ensure_firebase_admin
from firebase_admin import auth as firebase_auth

def fix_kalyan_account():
    """Fix KALYAN SASIDAR's account."""
    app = create_app()
    
    with app.app_context():
        # Find KALYAN SASIDAR
        faculty = Faculty.query.filter_by(abbreviation='PKS').first()
        
        if not faculty:
            print("❌ Faculty with abbreviation 'PKS' not found")
            print("   Searching by name...")
            faculty = Faculty.query.filter(Faculty.full_name.like('%KALYAN%')).first()
        
        if not faculty:
            print("❌ KALYAN SASIDAR not found in database")
            return
        
        print(f"✅ Found: {faculty.full_name}")
        print(f"   Email: {faculty.email}")
        print(f"   Firebase UID: {faculty.firebase_uid}")
        print(f"   Current must_reset_password: {faculty.must_reset_password}")
        
        if not faculty.email:
            print("❌ No email address. Cannot create Firebase account.")
            return
        
        if not faculty.firebase_uid:
            print("⚠️  No Firebase UID. Creating Firebase account...")
        
        # Generate new temporary password
        temp_password = _generate_temp_password()
        print(f"\n🔐 Generated temporary password: {temp_password}")
        
        try:
            _ensure_firebase_admin()
            
            if faculty.firebase_uid:
                # Update existing Firebase user
                print("   Updating existing Firebase user...")
                firebase_auth.update_user(faculty.firebase_uid, password=temp_password)
            else:
                # Create new Firebase user
                print("   Creating new Firebase user...")
                try:
                    user = firebase_auth.get_user_by_email(faculty.email)
                    print(f"   User already exists in Firebase with UID: {user.uid}")
                    firebase_auth.update_user(user.uid, password=temp_password)
                    faculty.firebase_uid = user.uid
                except firebase_auth.UserNotFoundError:
                    user = firebase_auth.create_user(email=faculty.email, password=temp_password)
                    faculty.firebase_uid = user.uid
                    print(f"   Created Firebase user with UID: {user.uid}")
            
            # Update database
            faculty.must_reset_password = True
            db.session.commit()
            
            print("\n✅ SUCCESS!")
            print(f"   Updated must_reset_password to: {faculty.must_reset_password}")
            print(f"\n📋 IMPORTANT: Share this temporary password with KALYAN SASIDAR:")
            print(f"   Email: {faculty.email}")
            print(f"   Temporary Password: {temp_password}")
            print(f"\n   They will be forced to change it on first login.")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            db.session.rollback()

if __name__ == '__main__':
    fix_kalyan_account()
