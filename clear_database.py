#!/usr/bin/env python3
"""
Clear database for fresh demo while keeping structure intact.
This script deletes all data but preserves tables and schema.
"""

from app import create_app
from models import db, Program, Semester, Batch, Faculty, Room, Course, Slot, \
    SlotCourse, CourseBatch, CourseFaculty, TimetableEntry, SchedulingViolation, \
    TimeSlot
from services.scheduler import SlotTimeMapping

def clear_database():
    """Clear all data from database while keeping structure."""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("🗑️  DATABASE CLEARING SCRIPT")
        print("="*60)
        print("\n⚠️  WARNING: This will delete ALL data from the database!")
        print("   (Tables and structure will be preserved)")
        
        response = input("\nAre you sure you want to continue? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("\n❌ Aborted. No changes made.")
            return
        
        print("\n🔄 Clearing database...")
        
        try:
            # Delete in reverse order of dependencies
            print("   Deleting scheduling violations...")
            SchedulingViolation.query.delete()
            
            print("   Deleting timetable entries...")
            TimetableEntry.query.delete()
            
            print("   Deleting slot time mappings...")
            SlotTimeMapping.query.delete()
            
            print("   Deleting course-faculty links...")
            CourseFaculty.query.delete()
            
            print("   Deleting course-batch links...")
            CourseBatch.query.delete()
            
            print("   Deleting slot-course links...")
            SlotCourse.query.delete()
            
            print("   Deleting courses...")
            Course.query.delete()
            
            print("   Deleting slots...")
            Slot.query.delete()
            
            print("   Deleting rooms...")
            Room.query.delete()
            
            print("   Deleting faculty...")
            Faculty.query.delete()
            
            print("   Deleting batches...")
            Batch.query.delete()
            
            print("   Deleting semesters...")
            Semester.query.delete()
            
            print("   Deleting programs...")
            Program.query.delete()
            
            # Note: TimeSlot is kept as it's seeded on app startup
            print("   Keeping time slots (will be re-seeded on app start)...")
            
            db.session.commit()
            
            print("\n✅ SUCCESS! Database cleared.")
            print("\n📊 Current state:")
            print(f"   Programs: {Program.query.count()}")
            print(f"   Semesters: {Semester.query.count()}")
            print(f"   Batches: {Batch.query.count()}")
            print(f"   Faculty: {Faculty.query.count()}")
            print(f"   Rooms: {Room.query.count()}")
            print(f"   Courses: {Course.query.count()}")
            print(f"   Slots: {Slot.query.count()}")
            print(f"   Timetable Entries: {TimetableEntry.query.count()}")
            print(f"   Time Slots: {TimeSlot.query.count()} (preserved)")
            
            print("\n💡 Next steps:")
            print("   1. Start Flask app: python app.py")
            print("   2. Login as admin")
            print("   3. Create and activate a semester")
            print("   4. Upload data files")
            print("   5. Generate timetable")
            
            print("\n" + "="*60)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            db.session.rollback()
            print("   Database rolled back. No changes made.")

if __name__ == '__main__':
    clear_database()
