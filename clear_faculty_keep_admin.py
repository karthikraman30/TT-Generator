#!/usr/bin/env python3
"""
Clear all faculty records EXCEPT admin accounts.
This preserves your ability to login after clearing.
"""

from app import create_app
from models import db, Faculty, CourseFaculty

def clear_faculty_keep_admin():
    """Delete all faculty records except admins."""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("🔧 CLEAR FACULTY (KEEP ADMINS)")
        print("="*60)
        
        # Count faculty by role
        total_faculty = Faculty.query.count()
        admin_count = Faculty.query.filter_by(role='admin').count()
        faculty_count = Faculty.query.filter_by(role='faculty').count()
        
        print(f"\nCurrent state:")
        print(f"  Total records: {total_faculty}")
        print(f"  Admin accounts: {admin_count}")
        print(f"  Faculty accounts: {faculty_count}")
        
        if faculty_count == 0:
            print("\n✅ No faculty to delete (only admins remain)!")
            return
        
        # Show which admins will be kept
        admins = Faculty.query.filter_by(role='admin').all()
        print(f"\n✅ These admin accounts will be KEPT:")
        for admin in admins:
            print(f"   • {admin.full_name} ({admin.abbreviation}) - {admin.email}")
        
        # Show what will be deleted
        print(f"\n❌ This will DELETE:")
        print(f"   • {faculty_count} faculty records (role='faculty')")
        print(f"   • Their course assignments")
        print(f"   • Their Firebase account links")
        
        print(f"\n✅ This will KEEP:")
        print(f"   • {admin_count} admin accounts")
        print(f"   • You can still login after this!")
        
        response = input("\nType 'DELETE FACULTY ONLY' to confirm: ").strip()
        
        if response != 'DELETE FACULTY ONLY':
            print("\n✅ Aborted. No changes made.")
            return
        
        print("\n🗑️  Deleting faculty records (keeping admins)...")
        
        try:
            # Get all faculty IDs (not admins)
            faculty_to_delete = Faculty.query.filter_by(role='faculty').all()
            faculty_ids = [f.id for f in faculty_to_delete]
            
            # Delete course-faculty links for these faculty
            deleted_links = 0
            for fac_id in faculty_ids:
                links = CourseFaculty.query.filter_by(faculty_id=fac_id).delete()
                deleted_links += links
            
            print(f"   Deleted {deleted_links} course-faculty links")
            
            # Delete faculty records (not admins)
            deleted_faculty = Faculty.query.filter_by(role='faculty').delete()
            print(f"   Deleted {deleted_faculty} faculty records")
            
            db.session.commit()
            
            # Show final state
            remaining = Faculty.query.count()
            print(f"\n✅ SUCCESS!")
            print(f"   Remaining accounts: {remaining} (all admins)")
            
            print("\n📋 Next steps:")
            print("   1. Upload Faculty_Names_With_Emails.xlsx")
            print("   2. Go to Admin → Upload → Faculty Mapping")
            print("   3. All faculty will be imported fresh")
            print("   4. Admin accounts remain intact")
            print("   5. You can still login!")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            db.session.rollback()
            print("   Database rolled back. No changes made.")

if __name__ == '__main__':
    clear_faculty_keep_admin()
