#!/usr/bin/env python3
"""
Generate Firebase accounts and temporary passwords for faculty who have emails but no Firebase UID.
"""

from app import create_app
from models import db, Faculty
from routes.admin import _generate_temp_password, _ensure_firebase_admin
from firebase_admin import auth as firebase_auth

def generate_passwords():
    """Generate passwords for faculty with emails but no Firebase accounts."""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("🔐 GENERATING FIREBASE ACCOUNTS & PASSWORDS")
        print("="*60 + "\n")
        
        # Find faculty with email but no firebase_uid
        faculty_without_firebase = Faculty.query.filter(
            Faculty.email.isnot(None),
            Faculty.email != '',
            Faculty.firebase_uid.is_(None)
        ).all()
        
        if not faculty_without_firebase:
            print("✅ All faculty with emails already have Firebase accounts!")
            return
        
        print(f"Found {len(faculty_without_firebase)} faculty without Firebase accounts:\n")
        
        for fac in faculty_without_firebase:
            print(f"  • {fac.full_name} ({fac.abbreviation}) - {fac.email}")
        
        print("\n" + "="*60)
        response = input("\nGenerate Firebase accounts for these faculty? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("\n❌ Aborted. No changes made.")
            return
        
        print("\n🔄 Generating accounts...\n")
        
        _ensure_firebase_admin()
        
        passwords = []
        errors = []
        
        for fac in faculty_without_firebase:
            try:
                # Generate password
                temp_password = _generate_temp_password()
                
                # Create or update Firebase user
                try:
                    user = firebase_auth.get_user_by_email(fac.email)
                    # User exists, update password
                    firebase_auth.update_user(user.uid, password=temp_password)
                    print(f"✅ Updated existing Firebase user: {fac.full_name}")
                except firebase_auth.UserNotFoundError:
                    # Create new user
                    user = firebase_auth.create_user(
                        email=fac.email,
                        password=temp_password
                    )
                    print(f"✅ Created new Firebase user: {fac.full_name}")
                
                # Update database
                fac.firebase_uid = user.uid
                fac.must_reset_password = True
                
                passwords.append({
                    'name': fac.full_name,
                    'abbr': fac.abbreviation,
                    'email': fac.email,
                    'password': temp_password
                })
                
            except Exception as e:
                print(f"❌ Error for {fac.full_name}: {e}")
                errors.append({'name': fac.full_name, 'error': str(e)})
        
        db.session.commit()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 SUMMARY")
        print("="*60)
        print(f"✅ Success: {len(passwords)}")
        print(f"❌ Errors: {len(errors)}")
        
        if passwords:
            print("\n" + "="*60)
            print("🔑 TEMPORARY PASSWORDS")
            print("="*60)
            print("\n⚠️  IMPORTANT: Save these passwords! They won't be shown again.\n")
            
            for p in passwords:
                print(f"Name: {p['name']}")
                print(f"Abbreviation: {p['abbr']}")
                print(f"Email: {p['email']}")
                print(f"Password: {p['password']}")
                print("-" * 60)
            
            # Save to file
            with open('faculty_passwords.txt', 'w') as f:
                f.write("TEMPORARY PASSWORDS\n")
                f.write("="*60 + "\n\n")
                for p in passwords:
                    f.write(f"Name: {p['name']}\n")
                    f.write(f"Abbreviation: {p['abbr']}\n")
                    f.write(f"Email: {p['email']}\n")
                    f.write(f"Password: {p['password']}\n")
                    f.write("-" * 60 + "\n")
            
            print(f"\n💾 Passwords also saved to: faculty_passwords.txt")
        
        if errors:
            print("\n" + "="*60)
            print("❌ ERRORS")
            print("="*60 + "\n")
            for e in errors:
                print(f"• {e['name']}: {e['error']}")

if __name__ == '__main__':
    generate_passwords()
