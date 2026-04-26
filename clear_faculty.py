#!/usr/bin/env python3
"""
Clear all faculty records from the database.
WARNING: This will delete all faculty and their course assignments!
"""

from app import create_app
from models import db, Faculty, CourseFaculty

def clear_faculty():
    """Delete all faculty records."""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("⚠️  WARNING: CLEAR FACULTY RECORDS")
        print("="*60)
        
        faculty_count = Faculty.query.count()
        course_faculty_count = CourseFaculty.query.count()
        
        print(f"\nCurrent state:")
        print(f"  Faculty records: {faculty_count}")
        print(f"  Course-Faculty links: {course_faculty_count}")
        
        if faculty_count == 0:
            print("\n✅ Faculty table is already empty!")
            return
        
        print("\n⚠️  This will DELETE:")
        print(f"  • All {faculty_count} faculty records")
        print(f"  • All {course_faculty_count} course-faculty assignments")
        print(f"  • All Firebase account links")
        
        print("\n❌ This CANNOT be undone!")
        print("   (Unless you have a database backup)")
        
        response = input("\nType 'DELETE ALL FACULTY' to confirm: ").strip()
        
        if response != 'DELETE ALL FACULTY':
            print("\n✅ Aborted. No changes made.")
            return
        
        print("\n🗑️  Deleting faculty records...")
        
        try:
            # Delete course-faculty links first
            deleted_links = CourseFaculty.query.delete()
            print(f"   Deleted {deleted_links} course-faculty links")
            
            # Delete faculty records
            deleted_faculty = Faculty.query.delete()
            print(f"   Deleted {deleted_faculty} faculty records")
            
            db.session.commit()
            
            print("\n✅ SUCCESS! Faculty table cleared.")
            print("\n📋 Next steps:")
            print("   1. Upload Faculty_Names_With_Emails.xlsx")
            print("   2. Go to Admin → Upload → Faculty Mapping")
            print("   3. All faculty will be imported fresh")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            db.session.rollback()
            print("   Database rolled back. No changes made.")

if __name__ == '__main__':
    clear_faculty()
