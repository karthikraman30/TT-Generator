"""
Faculty Name Updater
=====================
Reads the Winter2026_Electives.xlsx file (FacNames sheet) and syncs
full faculty names into the PostgreSQL database.

The FacNames sheet format:
  Column 0: "Full Name (ShortCode)"  e.g., "Pokhar M Jat (PMJ)"
  Column 1: "ShortCode"              e.g., "PMJ"

This script:
  1. Parses the Excel to extract (short_name → full_name) mappings
  2. Ensures each short_name exists in the faculty table
  3. Updates faculty.name with the full name
  4. Upserts into faculty_name_map for persistent mapping

Usage:
    python update_faculty_names.py                     # Apply updates
    python update_faculty_names.py --dry-run            # Preview only
    python update_faculty_names.py --file other.xlsx    # Custom file
"""

import os
import re
import sys
import argparse

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas is not installed. Run: pip install pandas openpyxl")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 is not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_db_connection():
    """Connect to PostgreSQL using .env configuration."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        dbname=os.getenv('DB_NAME', 'timetable_generator_db'),
        user=os.getenv('DB_USER', os.getenv('USER', 'postgres')),
        password=os.getenv('DB_PASSWORD', ''),
    )


def parse_faculty_names(excel_path, sheet_name='FacNames'):
    """Parse the FacNames sheet and return a dict of short_name → full_name.

    Handles the format: "Full Name (ShortCode)" in column 0,
    and "ShortCode" in column 1.
    """
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
    except FileNotFoundError:
        print(f"  ✗ File not found: {excel_path}")
        sys.exit(1)
    except ValueError as e:
        print(f"  ✗ Sheet '{sheet_name}' not found in {excel_path}: {e}")
        sys.exit(1)

    mappings = {}
    skipped = 0

    for idx, row in df.iterrows():
        full_col = str(row.iloc[0]).strip()
        short_col = str(row.iloc[1]).strip() if len(row) > 1 else ''

        if not full_col or full_col == 'nan' or not short_col or short_col == 'nan':
            skipped += 1
            continue

        # Extract the full name by removing the "(ShortCode)" suffix
        # e.g., "Pokhar M Jat (PMJ)" → "Pokhar M Jat"
        match = re.match(r'^(.+?)\s*\(\s*\w+\s*\)\s*$', full_col)
        if match:
            full_name = match.group(1).strip()
        else:
            # No parenthesized code — use the whole string as the name
            full_name = full_col.strip()

        short_name = short_col.strip()

        if short_name and full_name:
            mappings[short_name] = full_name

    print(f"  ✓ Parsed {len(mappings)} faculty name mappings from '{excel_path}'")
    if skipped:
        print(f"  ⚠ Skipped {skipped} empty/invalid rows")

    return mappings


def sync_to_database(mappings, dry_run=False):
    """Update the faculty table and faculty_name_map with full names.

    Args:
        mappings: Dict of short_name → full_name
        dry_run: If True, only preview changes without writing to DB
    """
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cur = conn.cursor()
        print(f"  ✓ Connected to database")
    except Exception as e:
        print(f"  ✗ Database connection failed: {e}")
        sys.exit(1)

    updated = 0
    inserted = 0
    skipped = 0
    not_in_db = []

    for short_name, full_name in sorted(mappings.items()):
        # Check if this faculty exists in the faculty table
        cur.execute("SELECT faculty_id, name FROM faculty WHERE short_name = %s",
                    (short_name,))
        row = cur.fetchone()

        if not row:
            not_in_db.append(short_name)
            skipped += 1
            continue

        faculty_id, current_name = row

        if current_name == full_name:
            skipped += 1
            continue

        if dry_run:
            old = repr(current_name)
            print(f"  [DRY RUN] {short_name:6s}: {old:<30s} → {full_name!r}")
        else:
            # Update faculty.name
            cur.execute(
                "UPDATE faculty SET name = %s WHERE faculty_id = %s",
                (full_name, faculty_id)
            )

            # Upsert into faculty_name_map
            cur.execute("""
                INSERT INTO faculty_name_map (short_name, full_name, source)
                VALUES (%s, %s, 'Excel')
                ON CONFLICT (short_name) DO UPDATE
                SET full_name = EXCLUDED.full_name,
                    source = 'Excel',
                    updated_at = CURRENT_TIMESTAMP
            """, (short_name, full_name))

        updated += 1

    if not dry_run:
        conn.commit()

    cur.close()
    conn.close()

    print(f"\n  Summary:")
    print(f"    Updated:  {updated}")
    print(f"    Skipped:  {skipped} (already correct or not in faculty table)")
    if not_in_db:
        print(f"    Not in DB: {len(not_in_db)} short names not found in faculty table:")
        for s in not_in_db:
            print(f"      - {s} ({mappings[s]})")
        print(f"    → Run the timetable generator with --use-db first to populate the faculty table.")

    if dry_run:
        print(f"\n  [DRY RUN] No changes written. Remove --dry-run to apply.")


def main():
    parser = argparse.ArgumentParser(
        description='Sync faculty full names from Excel into PostgreSQL.')
    parser.add_argument(
        '--file', '-f',
        default='Winter2026_Electives.xlsx',
        help='Excel file with FacNames sheet (default: Winter2026_Electives.xlsx)')
    parser.add_argument(
        '--sheet', '-s',
        default='FacNames',
        help='Sheet name containing faculty names (default: FacNames)')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview changes without writing to database')
    args = parser.parse_args()

    print("=" * 60)
    print("  Faculty Name Updater")
    print("=" * 60)

    print(f"\n  Reading: {args.file} → {args.sheet}")
    mappings = parse_faculty_names(args.file, args.sheet)

    if not mappings:
        print("  ✗ No mappings found. Check the Excel file format.")
        sys.exit(1)

    print(f"\n  Syncing to database {'(DRY RUN)' if args.dry_run else ''}...")
    sync_to_database(mappings, dry_run=args.dry_run)

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
