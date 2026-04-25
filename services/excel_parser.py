"""
Excel Parser Service.
Handles ingestion of the university's Slots Excel file and other data files.
"""

import re
import pandas as pd
from models import db, Semester, Program, Batch, Faculty, Room, Course, Slot, SlotCourse, CourseBatch, CourseFaculty


def parse_slots_file(filepath):
    """
    Parse the university Slots Excel file.
    Structure: Row 0 = headers (Batch, Slot-1, Slot-2, ..., Slot-Free)
    Each slot group spans 6 columns: [code, name, L-T-P-C, type, faculty_abbr, empty]
    Col 0 = batch group, Col 1 = sub-batch name.
    """
    df = pd.read_excel(filepath, sheet_name='Slots', header=None)

    # Get or create active semester
    active_sem = Semester.query.filter_by(is_active=True).first()
    if not active_sem:
        raise ValueError("No active semester. Please create and activate a semester first.")

    # ─── 1. Identify slot column positions ───────────────────
    slot_columns = {}  # slot_label -> start_col_index
    for col_idx, val in enumerate(df.iloc[0]):
        if pd.notna(val) and isinstance(val, str) and ('Slot' in val or val == 'Batch'):
            if val != 'Batch':
                slot_columns[val] = col_idx

    stats = {'courses': 0, 'batches': 0, 'faculty': 0, 'slots': 0, 'mappings': 0}

    # ─── 2. Create Slot records ──────────────────────────────
    for label in slot_columns:
        num = None
        match = re.search(r'(\d+)', label)
        if match:
            num = int(match.group(1))

        existing = Slot.query.filter_by(slot_label=label, semester_id=active_sem.id).first()
        if not existing:
            slot = Slot(slot_label=label, slot_number=num, semester_id=active_sem.id)
            db.session.add(slot)
            stats['slots'] += 1

    db.session.flush()

    # ─── 3. Parse row by row ────────────────────────────────
    current_batch_group = None
    current_sub_batch = None

    for row_idx in range(1, len(df)):
        row = df.iloc[row_idx]

        # Check for batch group (col 0)
        if pd.notna(row.iloc[0]):
            current_batch_group = str(row.iloc[0]).strip()

        # Check for sub-batch (col 1)
        if pd.notna(row.iloc[1]):
            current_sub_batch = str(row.iloc[1]).strip()
        elif pd.notna(row.iloc[0]):
            # If col 0 has value but col 1 doesn't, sub-batch is the group itself
            current_sub_batch = current_batch_group

        if not current_sub_batch:
            continue

        # Get or create batch
        batch = _get_or_create_batch(current_sub_batch, current_batch_group, active_sem.id)
        if batch:
            stats['batches'] += 1  # counts attempts, not unique

        # ─── 4. Parse each slot's columns for this row ───────
        for slot_label, start_col in slot_columns.items():
            course_data = _extract_course_from_row(row, start_col)
            if not course_data:
                continue

            # Get or create course
            course = _get_or_create_course(course_data, active_sem.id)
            if course:
                stats['courses'] += 1

                # Get or create faculty
                if course_data.get('faculty_abbr'):
                    fac = _get_or_create_faculty(course_data['faculty_abbr'])
                    if fac:
                        stats['faculty'] += 1
                        _link_course_faculty(course.id, fac.id)

                # Link course to batch
                if batch:
                    _link_course_batch(course.id, batch.id)

                # Link course to slot
                slot = Slot.query.filter_by(slot_label=slot_label, semester_id=active_sem.id).first()
                if slot and batch:
                    _link_slot_course(slot.id, course.id, batch.id)
                    stats['mappings'] += 1

    db.session.commit()
    return f"Imported: {stats['slots']} slots, {stats['courses']} course entries, {stats['faculty']} faculty refs, {stats['mappings']} slot-course mappings"


def _extract_course_from_row(row, start_col):
    """Extract course data from a slot's column group starting at start_col."""
    try:
        code = row.iloc[start_col] if start_col < len(row) else None
        if pd.isna(code) or not str(code).strip():
            return None

        code = str(code).strip()
        name = str(row.iloc[start_col + 1]).strip() if start_col + 1 < len(row) and pd.notna(row.iloc[start_col + 1]) else code
        ltpc_str = str(row.iloc[start_col + 2]).strip() if start_col + 2 < len(row) and pd.notna(row.iloc[start_col + 2]) else '0-0-0-0'
        course_type = str(row.iloc[start_col + 3]).strip() if start_col + 3 < len(row) and pd.notna(row.iloc[start_col + 3]) else 'Core'
        faculty_abbr = str(row.iloc[start_col + 4]).strip() if start_col + 4 < len(row) and pd.notna(row.iloc[start_col + 4]) else None

        # Parse L-T-P-C
        l, t, p, c = _parse_ltpc(ltpc_str)

        return {
            'code': code, 'name': name,
            'L': l, 'T': t, 'P': p, 'C': c,
            'course_type': course_type,
            'faculty_abbr': faculty_abbr
        }
    except (IndexError, ValueError):
        return None


def _parse_ltpc(ltpc_str):
    """Parse L-T-P-C string like '3-0-2-4' or '3-0-3-4.5'."""
    parts = str(ltpc_str).split('-')
    if len(parts) == 4:
        try:
            return int(parts[0]), int(parts[1]), int(parts[2]), float(parts[3])
        except ValueError:
            pass
    return 0, 0, 0, 0


def _get_or_create_batch(sub_batch_name, batch_group, semester_id):
    """Get or create a Batch record. Also auto-creates the Program."""
    existing = Batch.query.filter_by(name=sub_batch_name, semester_id=semester_id).first()
    if existing:
        return existing

    # Extract sem number from name like "BTech Sem-II (ICT + CS)"
    sem_num = 0
    sem_match = re.search(r'Sem-(\w+)', sub_batch_name)
    if sem_match:
        roman = sem_match.group(1)
        roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8}
        sem_num = roman_map.get(roman, 0)

    # Auto-create program from batch name
    program = _get_or_create_program(sub_batch_name)

    batch = Batch(
        name=sub_batch_name,
        sem_number=sem_num,
        semester_id=semester_id,
        student_count=0,
        program_id=program.id if program else None
    )
    db.session.add(batch)
    db.session.flush()
    return batch


def _get_or_create_program(batch_name):
    """
    Extract and create a Program from a batch name.
    E.g. 'BTech Sem-II (ICT + CS)' → Program(name='BTech ICT+CS', code='BTECH_ICT_CS', degree_type='BTech')
         'MTech Sem-II (ICT-ML)' → Program(name='MTech ICT-ML', code='MTECH_ICT_ML', degree_type='MTech')
         'MSc Sem-II (IT)' → Program(name='MSc IT', code='MSC_IT', degree_type='MSc')
    """
    # Determine degree type
    degree_type = 'BTech'
    if 'MTech' in batch_name or 'M Tech' in batch_name:
        degree_type = 'MTech'
    elif 'MSc' in batch_name or 'M.Sc' in batch_name:
        degree_type = 'MSc'
    elif 'BTech' in batch_name or 'B Tech' in batch_name or 'B-Tech' in batch_name:
        degree_type = 'BTech'

    # Extract specialization from parentheses
    spec = ''
    spec_match = re.search(r'\((.+?)\)', batch_name)
    if spec_match:
        spec = spec_match.group(1).strip()

    if spec:
        prog_name = f"{degree_type} {spec}"
    else:
        prog_name = degree_type

    # Create a clean code
    code = prog_name.upper().replace(' ', '_').replace('+', '_').replace('-', '_').replace('&', '_')
    # Remove duplicate underscores
    code = re.sub(r'_+', '_', code).strip('_')

    existing = Program.query.filter_by(code=code).first()
    if existing:
        return existing

    program = Program(name=prog_name, code=code, degree_type=degree_type)
    db.session.add(program)
    db.session.flush()
    return program


def _get_or_create_course(data, semester_id):
    """Get or create a Course record."""
    existing = Course.query.filter_by(code=data['code'], name=data['name'], semester_id=semester_id).first()
    if existing:
        return existing

    course = Course(
        code=data['code'], name=data['name'],
        lectures_per_week=data['L'], tutorials_per_week=data['T'],
        practicals_per_week=data['P'], credits=data['C'],
        course_type=data['course_type'], semester_id=semester_id
    )
    db.session.add(course)
    db.session.flush()
    return course


def _get_or_create_faculty(abbreviation):
    """Get or create a Faculty record (with abbreviation as placeholder name)."""
    if not abbreviation or abbreviation == 'nan':
        return None
    abbreviation = abbreviation.strip().upper()
    existing = Faculty.query.filter_by(abbreviation=abbreviation).first()
    if existing:
        return existing

    fac = Faculty(full_name=abbreviation, abbreviation=abbreviation)
    db.session.add(fac)
    db.session.flush()
    return fac


def _link_course_faculty(course_id, faculty_id):
    """Link a course to a faculty member."""
    existing = CourseFaculty.query.filter_by(course_id=course_id, faculty_id=faculty_id).first()
    if not existing:
        db.session.add(CourseFaculty(course_id=course_id, faculty_id=faculty_id))
        db.session.flush()


def _link_course_batch(course_id, batch_id):
    """Link a course to a batch."""
    existing = CourseBatch.query.filter_by(course_id=course_id, batch_id=batch_id).first()
    if not existing:
        db.session.add(CourseBatch(course_id=course_id, batch_id=batch_id))
        db.session.flush()


def _link_slot_course(slot_id, course_id, batch_id):
    """Link a course to a slot for a specific batch."""
    existing = SlotCourse.query.filter_by(slot_id=slot_id, course_id=course_id, batch_id=batch_id).first()
    if not existing:
        db.session.add(SlotCourse(slot_id=slot_id, course_id=course_id, batch_id=batch_id))
        db.session.flush()


def parse_rooms_file(filepath):
    """Parse a rooms CSV/Excel file with columns: Room Name, Capacity, Building, Type."""
    df = pd.read_excel(filepath) if filepath.endswith(('.xlsx', '.xls')) else pd.read_csv(filepath)
    count = 0
    for _, row in df.iterrows():
        name = str(row.iloc[0]).strip()
        capacity = int(row.iloc[1]) if pd.notna(row.iloc[1]) else 0
        building = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else None
        room_type = str(row.iloc[3]).strip() if len(row) > 3 and pd.notna(row.iloc[3]) else 'lecture'

        if not Room.query.filter_by(name=name).first():
            db.session.add(Room(name=name, capacity=capacity, building=building, room_type=room_type))
            count += 1

    db.session.commit()
    return f"{count} rooms added"


def parse_faculty_mapping(filepath):
    """Parse a faculty mapping CSV with columns: Abbreviation, Full Name, Email."""
    df = pd.read_csv(filepath) if filepath.endswith('.csv') else pd.read_excel(filepath)
    count = 0
    for _, row in df.iterrows():
        abbr = str(row.iloc[0]).strip().upper()
        full_name = str(row.iloc[1]).strip()
        email = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else None

        fac = Faculty.query.filter_by(abbreviation=abbr).first()
        if fac:
            fac.full_name = full_name
            if email:
                fac.email = email
            count += 1
        else:
            db.session.add(Faculty(full_name=full_name, abbreviation=abbr, email=email))
            count += 1

    db.session.commit()
    return f"{count} faculty records updated/created"


def parse_section_strengths(filepath):
    """
    Parse a section strengths Excel/CSV file.
    Columns: Label (e.g. 'Sec A', 'CS-Only', 'EVD'), Student Count.
    
    Matching rules (applied in order):
      1. 'Sec A' / 'Sec B' → matches courses with '(Sec A)' or '(Sec B)' in name
      2. 'CS-Only' → matches courses belonging to any 'CS-Only' batch
      3. Any other label → matches courses whose ONLY batches contain that label
         e.g. 'EVD' matches courses only in EVD batches
         e.g. 'MTech ICT-ML' matches courses only in MTech ICT-ML batches
    """
    df = pd.read_excel(filepath) if filepath.endswith(('.xlsx', '.xls')) else pd.read_csv(filepath)
    
    active_sem = Semester.query.filter_by(is_active=True).first()
    if not active_sem:
        raise ValueError("No active semester.")

    # Build lookup: label → count
    rules = []
    for _, row in df.iterrows():
        label = str(row.iloc[0]).strip()
        count = int(row.iloc[1]) if pd.notna(row.iloc[1]) else 0
        if label and count > 0:
            rules.append((label, count))

    courses = Course.query.filter_by(semester_id=active_sem.id).all()
    updated = 0

    for course in courses:
        batch_names = [cb.name for cb in course.batches.all()]
        matched = False

        for label, count in rules:
            # Rule 1: Section in course name
            if label.startswith('Sec') and f'({label})' in course.name:
                course.capacity_override = count
                matched = True
                break

            # Rule 2: CS-Only batch match
            if label == 'CS-Only':
                if any('CS-Only' in bn for bn in batch_names):
                    course.capacity_override = count
                    matched = True
                    break

            # Rule 3: Batch label match (for non-section labels)
            if not label.startswith('Sec') and label != 'CS-Only':
                # Check if ALL batches for this course contain this label
                # OR if the course is exclusively in batches matching this label
                if batch_names and any(label in bn for bn in batch_names):
                    # Only apply if this is the most specific match
                    # (course has no section in name and isn't CS-Only)
                    if '(Sec' not in course.name and not any('CS-Only' in bn for bn in batch_names):
                        course.capacity_override = count
                        matched = True
                        break

        if matched:
            updated += 1

    db.session.commit()
    return f"Applied section strengths to {updated} out of {len(courses)} courses"
