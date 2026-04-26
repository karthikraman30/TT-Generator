#!/usr/bin/env python3
"""
Check if system is ready for demo.
Verifies all requirements and provides status report.
"""

import os
import sys
from pathlib import Path

def check_demo_readiness():
    """Check if system is ready for demo."""
    print("\n" + "="*60)
    print("🔍 DEMO READINESS CHECK")
    print("="*60 + "\n")
    
    issues = []
    warnings = []
    
    # Check 1: Required files exist
    print("📁 Checking required files...")
    required_files = {
        'app.py': 'Main application file',
        'config.py': 'Configuration file',
        'models.py': 'Database models',
        '.env': 'Environment variables',
        'requirements.txt': 'Python dependencies',
    }
    
    for file, description in required_files.items():
        if os.path.exists(file):
            print(f"   ✅ {file} - {description}")
        else:
            print(f"   ❌ {file} - {description} (MISSING)")
            issues.append(f"Missing {file}")
    
    # Check 2: Demo data files
    print("\n📊 Checking demo data files...")
    demo_files = {
        'Slots_Win_2025-26_15Dec2025.xlsx': 'Slots data',
        'Faculty names.xlsx': 'Faculty mapping',
        'rooms_reference.xlsx': 'Rooms data',
        'section_strengths.xlsx': 'Section strengths',
        'course_strengths.csv': 'Course strengths',
    }
    
    for file, description in demo_files.items():
        if os.path.exists(file):
            size = os.path.getsize(file) / 1024  # KB
            print(f"   ✅ {file} - {description} ({size:.1f} KB)")
        else:
            print(f"   ⚠️  {file} - {description} (NOT FOUND)")
            warnings.append(f"Demo file {file} not found")
    
    # Check 3: Python dependencies
    print("\n📦 Checking Python dependencies...")
    try:
        import flask
        print(f"   ✅ Flask {flask.__version__}")
    except ImportError:
        print("   ❌ Flask (NOT INSTALLED)")
        issues.append("Flask not installed")
    
    try:
        import flask_sqlalchemy
        print(f"   ✅ Flask-SQLAlchemy")
    except ImportError:
        print("   ❌ Flask-SQLAlchemy (NOT INSTALLED)")
        issues.append("Flask-SQLAlchemy not installed")
    
    try:
        import firebase_admin
        print(f"   ✅ Firebase Admin SDK")
    except ImportError:
        print("   ⚠️  Firebase Admin SDK (NOT INSTALLED)")
        warnings.append("Firebase not installed - use dev login")
    
    try:
        import pandas
        print(f"   ✅ Pandas {pandas.__version__}")
    except ImportError:
        print("   ❌ Pandas (NOT INSTALLED)")
        issues.append("Pandas not installed")
    
    try:
        import openpyxl
        print(f"   ✅ OpenPyXL")
    except ImportError:
        print("   ❌ OpenPyXL (NOT INSTALLED)")
        issues.append("OpenPyXL not installed")
    
    try:
        import reportlab
        print(f"   ✅ ReportLab")
    except ImportError:
        print("   ⚠️  ReportLab (NOT INSTALLED)")
        warnings.append("ReportLab not installed - PDF export won't work")
    
    # Check 4: Database
    print("\n🗄️  Checking database...")
    if os.path.exists('timetable.db'):
        size = os.path.getsize('timetable.db') / 1024  # KB
        print(f"   ✅ SQLite database exists ({size:.1f} KB)")
        
        # Try to connect
        try:
            from app import create_app
            from models import db, Faculty, Semester
            
            app = create_app()
            with app.app_context():
                faculty_count = Faculty.query.count()
                semester_count = Semester.query.count()
                print(f"   ✅ Database accessible")
                print(f"      - Faculty: {faculty_count}")
                print(f"      - Semesters: {semester_count}")
                
                if faculty_count == 0:
                    warnings.append("No faculty in database - will need to upload")
                if semester_count == 0:
                    warnings.append("No semesters - will need to create one")
        except Exception as e:
            print(f"   ⚠️  Database connection issue: {e}")
            warnings.append("Database connection issue")
    else:
        print("   ⚠️  SQLite database not found (will be created on first run)")
        warnings.append("Database will be created on first run")
    
    # Check 5: Firebase configuration
    print("\n🔥 Checking Firebase configuration...")
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_content = f.read()
            if 'FIREBASE_API_KEY' in env_content:
                print("   ✅ Firebase API key configured")
            else:
                print("   ⚠️  Firebase API key not configured")
                warnings.append("Firebase not configured - use dev login")
    
    if os.path.exists('firebase-credentials.json'):
        print("   ✅ Firebase credentials file exists")
    else:
        print("   ⚠️  Firebase credentials file not found")
        warnings.append("Firebase credentials missing - use dev login")
    
    # Check 6: Upload folder
    print("\n📂 Checking upload folder...")
    if os.path.exists('uploads'):
        print("   ✅ Upload folder exists")
    else:
        print("   ⚠️  Upload folder not found (will be created)")
        warnings.append("Upload folder will be created")
    
    # Check 7: Demo scripts
    print("\n📝 Checking demo scripts...")
    demo_scripts = {
        'clear_database.py': 'Clear database for fresh demo',
        'DEMO_PLAN.md': 'Complete demo plan',
        'DEMO_CHECKLIST.md': 'Quick demo checklist',
    }
    
    for file, description in demo_scripts.items():
        if os.path.exists(file):
            print(f"   ✅ {file} - {description}")
        else:
            print(f"   ⚠️  {file} - {description} (NOT FOUND)")
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    if not issues and not warnings:
        print("\n✅ SYSTEM READY FOR DEMO!")
        print("\n🚀 Next steps:")
        print("   1. Start Flask app: python app.py")
        print("   2. Open browser: http://localhost:5000")
        print("   3. Login as admin (dev login)")
        print("   4. Follow DEMO_CHECKLIST.md")
        return True
    
    if issues:
        print(f"\n❌ CRITICAL ISSUES ({len(issues)}):")
        for issue in issues:
            print(f"   • {issue}")
        print("\n🔧 Fix these issues before demo:")
        print("   pip install -r requirements.txt")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"   • {warning}")
        print("\n💡 These won't prevent demo but may limit features")
    
    if not issues:
        print("\n✅ No critical issues - you can proceed with demo")
        print("   (Warnings are optional features)")
        return True
    
    return False

if __name__ == '__main__':
    try:
        ready = check_demo_readiness()
        print("\n" + "="*60 + "\n")
        sys.exit(0 if ready else 1)
    except Exception as e:
        print(f"\n❌ Error during check: {e}")
        print("\n" + "="*60 + "\n")
        sys.exit(1)
