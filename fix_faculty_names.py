#!/usr/bin/env python3
"""
Fix swapped faculty names (where full name and abbreviation are reversed).
"""

from app import create_app
from models import db, Faculty

def fix_faculty_names():
    """Fix faculty records where names appear to be swapped."""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("🔧 FIXING FACULTY NAMES")
        print("="*60 + "\n")
        
        fixed = []
        
        for fac in Faculty.query.all():
            # Heuristic: If abbreviation is longer than 10 chars or contains spaces,
            # it's probably the full name
            abbr_looks_like_name = (
                len(fac.abbreviation) > 10 or
                ' ' in fac.abbreviation or
                '(' in fac.abbreviation
            )
            
            # If full_name is very short (< 5 chars) and no spaces, probably abbreviation
            name_looks_like_abbr = (
                len(fac.full_name) < 5 and
                ' ' not in fac.full_name
            )
            
            if abbr_looks_like_name or name_looks_like_abbr:
                # Swap them
                old_name = fac.full_name
                old_abbr = fac.abbreviation
                
                fac.full_name = old_abbr
                fac.abbreviation = old_name
                
                fixed.append({
                    'old_name': old_name,
                    'old_abbr': old_abbr,
                    'new_name': fac.full_name,
                    'new_abbr': fac.abbreviation
                })
                
                print(f"Fixed: {fac.full_name} ({fac.abbreviation})")
                print(f"  Was: {old_name} ({old_abbr})")
                print()
        
        if fixed:
            response = input(f"\nFound {len(fixed)} faculty to fix. Apply changes? (yes/no): ").strip().lower()
            
            if response in ['yes', 'y']:
                db.session.commit()
                print(f"\n✅ Fixed {len(fixed)} faculty records!")
            else:
                db.session.rollback()
                print("\n❌ Aborted. No changes made.")
        else:
            print("✅ No issues found. All faculty names look correct!")

if __name__ == '__main__':
    fix_faculty_names()
