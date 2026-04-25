"""
Scheduler Service — Slot-Based Timetable Generation.

Ported from the 'sai' version's Slot-Bucket Paradigm (Phase 3):
  - Courses come pre-assigned to slots from the Excel import.
  - The algorithm validates, detects conflicts, trims by L-value, and assigns rooms.

Three-pass approach:
  Pass 1: Assign each Slot to 3 (day, period) time blocks (auto or manual).
  Pass 2: Validate slot buckets (faculty conflicts, combined classes, VF exemption).
  Pass 3: Apply L-value trimming + Assign rooms (capacity-aware).

Hard Constraints:
  - Wednesday Period 1 (08:00) is always free.
  - Each slot appears on 3 DIFFERENT days (max 1 lecture/day/course).
  - No two slots share the same time block.
  - No faculty double-booking (same prof in different rooms at same time).
  - VF (Visiting Faculty) is exempt from faculty conflict checks.

Composability: Each function is independent and testable.
"""

from collections import defaultdict
from itertools import combinations

from models import db, Slot, SlotCourse, Course, TimeSlot, TimetableEntry, \
    SchedulingViolation, CourseFaculty, CourseBatch, Faculty, Room, \
    LTrimmingOverride, BatchOverlapRule


# ─── SLOT-TIME MAPPING TABLE ────────────────────────────────
# We store the mapping in a lightweight table: which slot occupies which time block.

class SlotTimeMapping(db.Model):
    """Maps a slot to one of its assigned time blocks."""
    __tablename__ = 'slot_time_mappings'
    __table_args__ = (
        db.UniqueConstraint('slot_id', 'time_slot_id'),
        db.UniqueConstraint('time_slot_id', 'semester_id'),  # no two slots in same time block
    )

    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('slots.id', ondelete='CASCADE'), nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slots.id', ondelete='CASCADE'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='CASCADE'), nullable=False)

    slot = db.relationship('Slot', backref='time_mappings')
    time_slot = db.relationship('TimeSlot', backref='slot_mappings')

    def to_dict(self):
        return {
            'id': self.id,
            'slot': self.slot.slot_label if self.slot else None,
            'day': self.time_slot.day if self.time_slot else None,
            'period': self.time_slot.period if self.time_slot else None,
            'start_time': self.time_slot.start_time.strftime('%H:%M') if self.time_slot else None,
        }


# ─── CONSTANTS ──────────────────────────────────────────────
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
DAY_ORDER = {d: i for i, d in enumerate(DAYS)}

# VF codes are exempt from faculty conflict checks
# (multiple visiting professors share the code but are different people)
VF_CODES = {'vf', '(vf)', 'vf1', 'vf2'}

# Blocked time blocks: Wed 8AM is always free
BLOCKED = [
    ('Wednesday', 1),
]


# ─── HELPERS ────────────────────────────────────────────────

def _get_available_time_slots():
    """Get all usable time blocks (excluding blocked ones)."""
    all_ts = TimeSlot.query.order_by(TimeSlot.day, TimeSlot.period).all()
    available = []
    for ts in all_ts:
        is_blocked = any(ts.day == day and ts.period == period for day, period in BLOCKED)
        if not is_blocked:
            available.append(ts)
    return available


def _get_day_index(day_name):
    """Convert day name to index for sorting."""
    return DAY_ORDER.get(day_name, 99)


def _is_vf(abbreviation):
    """Check if a faculty abbreviation is a Visiting Faculty code."""
    return abbreviation and abbreviation.strip().lower() in VF_CODES


def is_overlap(batch_name_1, section_1, batch_name_2, section_2, overlap_rules=None):
    """Check if two (batch_name, section) pairs share students.

    Uses DB-driven overlap rules if provided, with hardcoded CS-Only fallback.
    Ported from sai/generate_timetable.py.
    """
    # Same batch & same/overlapping section
    if batch_name_1 == batch_name_2 and (section_1 == section_2 or section_1 == 'All' or section_2 == 'All'):
        return True

    # DB-driven overlap rules
    if overlap_rules:
        for rule in overlap_rules:
            ba, sa = rule.batch_a, rule.section_a
            bb, sb = rule.batch_b, rule.section_b
            # Check both directions
            if (ba in batch_name_1 and (sa == 'All' or sa == section_1) and
                    bb in batch_name_2 and (sb == 'All' or sb == section_2)):
                return True
            if (ba in batch_name_2 and (sa == 'All' or sa == section_2) and
                    bb in batch_name_1 and (sb == 'All' or sb == section_1)):
                return True
    else:
        # Hardcoded fallback: CS-Only is a subset of ICT+CS Sec B
        if 'CS-Only' in batch_name_1 and 'ICT + CS' in batch_name_2 and section_2 in ('Sec B', 'All'):
            return True
        if 'CS-Only' in batch_name_2 and 'ICT + CS' in batch_name_1 and section_1 in ('Sec B', 'All'):
            return True
    return False


# ─── L-VALUE TRIMMING (from sai) ────────────────────────────

def pick_max_spacing(available_days, keep_count):
    """Pick keep_count days from available_days with maximum spacing.

    Ported from sai/generate_timetable.py — the max-spacing heuristic.
    """
    if keep_count >= len(available_days):
        return set(available_days)
    if keep_count <= 0:
        return set()

    # Sort by weekday index
    sorted_days = sorted(available_days, key=lambda d: DAY_ORDER.get(d, 0))

    if keep_count == 1:
        mid = len(sorted_days) // 2
        return {sorted_days[mid]}

    if keep_count == 2 and len(sorted_days) == 3:
        return {sorted_days[0], sorted_days[2]}

    # General case: try all combinations and pick the one with max min-gap
    best = None
    best_score = -1
    for combo in combinations(range(len(sorted_days)), keep_count):
        indices = sorted(combo)
        min_gap = min(indices[i + 1] - indices[i] for i in range(len(indices) - 1))
        if min_gap > best_score:
            best_score = min_gap
            best = {sorted_days[i] for i in indices}
    return best or set(sorted_days[:keep_count])


# ─── PASS 1: AUTO-ASSIGN SLOTS TO TIME BLOCKS ───────────────

def auto_assign_slots(semester_id):
    """
    Automatically assign each numbered slot (Slot-1 to Slot-8) to 3 time blocks.
    Uses a greedy balanced distribution across the grid.

    Returns summary string.
    """
    # Clear existing mappings for this semester
    SlotTimeMapping.query.filter_by(semester_id=semester_id).delete()
    db.session.flush()

    # Get numbered slots (Slot-1 through Slot-8, ignore Slot-Free)
    slots = Slot.query.filter(
        Slot.semester_id == semester_id,
        Slot.slot_number.isnot(None)
    ).order_by(Slot.slot_number).all()

    if not slots:
        raise ValueError("No numbered slots found. Upload a Slots file first.")

    available = _get_available_time_slots()
    blocks_per_slot = 3  # max L is 3

    # Track which time blocks are used and how many slots each day has
    used_ts_ids = set()
    day_load = {d: 0 for d in DAYS}

    assignments = []

    for slot in slots:
        chosen = []
        used_days = set()

        # Sort available blocks: prefer days with lower load, then spread across periods
        candidates = [
            ts for ts in available
            if ts.id not in used_ts_ids
        ]
        candidates.sort(key=lambda ts: (day_load.get(ts.day, 0), ts.period, _get_day_index(ts.day)))

        for ts in candidates:
            if ts.day in used_days:
                continue
            chosen.append(ts)
            used_days.add(ts.day)
            if len(chosen) == blocks_per_slot:
                break

        if len(chosen) < blocks_per_slot:
            violation = SchedulingViolation(
                semester_id=semester_id,
                violation_type='SLOT_ASSIGNMENT_FAILED',
                severity='error',
                description=f'Could not assign {blocks_per_slot} time blocks to {slot.slot_label}. '
                            f'Only found {len(chosen)} available blocks on different days.'
            )
            db.session.add(violation)

        for ts in chosen:
            used_ts_ids.add(ts.id)
            day_load[ts.day] = day_load.get(ts.day, 0) + 1

            mapping = SlotTimeMapping(
                slot_id=slot.id,
                time_slot_id=ts.id,
                semester_id=semester_id
            )
            db.session.add(mapping)

        assignments.append((slot, chosen))

    db.session.commit()
    return f"Assigned {len(slots)} slots to {sum(len(c) for _, c in assignments)} time blocks."


# ─── PASS 1b: VALIDATE SLOT BUCKETS (from sai) ─────────────

def validate_buckets(semester_id):
    """Validate slot assignments for conflicts (ported from sai).

    For each slot bucket, check:
    - Faculty double-booking (same prof, different courses) → CRITICAL
    - Faculty combined class (same prof, same code, diff sections) → Info/auto-merge
    - VF exemption → Skip VF from faculty conflict checks

    Returns:
        tuple: (errors, warnings, merges) — lists of strings/dicts
    """
    errors = []
    warnings = []
    merges = []

    slots = Slot.query.filter_by(semester_id=semester_id).all()

    for slot in slots:
        # Get all slot_courses for this slot
        slot_courses_entries = SlotCourse.query.filter_by(slot_id=slot.id).all()
        if not slot_courses_entries:
            continue

        # Group by faculty
        fac_courses = defaultdict(list)
        for sc in slot_courses_entries:
            course = sc.course
            if not course:
                continue
            # Get faculty for this course
            cf = CourseFaculty.query.filter_by(course_id=course.id).first()
            if cf and cf.faculty_id:
                fac = Faculty.query.get(cf.faculty_id)
                if fac and not _is_vf(fac.abbreviation):
                    fac_courses[fac.abbreviation].append({
                        'course': course,
                        'batch': sc.batch,
                        'slot_course': sc,
                    })

        for fac_abbr, clist in fac_courses.items():
            # Group by course code
            by_code = defaultdict(list)
            for entry in clist:
                by_code[entry['course'].code].append(entry)

            if len(by_code) > 1:
                codes = ', '.join(sorted(by_code.keys()))
                errors.append(
                    f"CRITICAL: Faculty '{fac_abbr}' is assigned to DIFFERENT courses "
                    f"({codes}) in {slot.slot_label}. This is a data error — "
                    f"a professor cannot be in two rooms simultaneously."
                )

            for code, same_code_entries in by_code.items():
                if len(same_code_entries) > 1:
                    batch_names = sorted(set(
                        e['batch'].name if e['batch'] else 'Unknown'
                        for e in same_code_entries
                    ))
                    if len(batch_names) > 1:
                        merges.append({
                            'course_code': code,
                            'faculty': fac_abbr,
                            'slot': slot.slot_label,
                            'batches': batch_names,
                        })
                        warnings.append(
                            f"Auto-merge: {fac_abbr} teaches {code} to multiple batches "
                            f"({', '.join(batch_names)}) in {slot.slot_label}. "
                            f"Combined room capacity will be used."
                        )

    # Log critical errors as violations
    for err in errors:
        violation = SchedulingViolation(
            semester_id=semester_id,
            violation_type='FACULTY_DOUBLE_BOOKING',
            severity='error',
            description=err
        )
        db.session.add(violation)

    # Log merges as info violations
    for warn in warnings:
        violation = SchedulingViolation(
            semester_id=semester_id,
            violation_type='COMBINED_CLASS_DETECTED',
            severity='warning',
            description=warn
        )
        db.session.add(violation)

    db.session.flush()
    return errors, warnings, merges


# ─── PASS 1c: GENERATE TIMETABLE ENTRIES FROM MAPPINGS ──────

def generate_entries_from_mappings(semester_id):
    """
    After slots are mapped to time blocks, create timetable_entries
    for each course based on its L value, with L-trimming support.

    - L=3: course gets all 3 time blocks of its slot
    - L=2: course gets 2 time blocks (max-spacing or admin override)
    - L=1: course gets 1 time block
    """
    # Clear existing entries
    TimetableEntry.query.filter_by(semester_id=semester_id).delete()
    db.session.flush()

    # Load L-trimming overrides
    overrides = {}
    for ov in LTrimmingOverride.query.filter_by(semester_id=semester_id).all():
        overrides[ov.course_code] = set(ov.keep_days_list)

    # Get all slot-course links for this semester
    slot_courses = db.session.query(SlotCourse).join(Slot).filter(
        Slot.semester_id == semester_id
    ).all()

    entries_created = 0
    seen_course_slots = set()

    for sc in slot_courses:
        course = sc.course
        slot = sc.slot
        if not course or not slot:
            continue

        key = (course.id, slot.id)
        if key in seen_course_slots:
            continue
        seen_course_slots.add(key)

        # Get time blocks for this slot
        mappings = SlotTimeMapping.query.filter_by(
            slot_id=slot.id,
            semester_id=semester_id
        ).all()

        if not mappings:
            continue

        # Sort by day then period for consistent ordering
        mappings.sort(key=lambda m: (_get_day_index(m.time_slot.day), m.time_slot.period))

        # How many blocks does this course need?
        lectures_needed = course.lectures_per_week
        if lectures_needed <= 0:
            continue

        # Apply L-trimming: determine which time blocks to use
        if course.code in overrides:
            # Admin override: use specific days
            keep_days = overrides[course.code]
            blocks_to_use = [m for m in mappings if m.time_slot.day in keep_days]
            # If override doesn't match available mappings, fall back to first N
            if not blocks_to_use:
                blocks_to_use = mappings[:lectures_needed]
        elif lectures_needed < len(mappings):
            # Auto L-trimming with max-spacing heuristic
            available_days = [m.time_slot.day for m in mappings]
            keep_days = pick_max_spacing(available_days, lectures_needed)
            blocks_to_use = [m for m in mappings if m.time_slot.day in keep_days]
        else:
            blocks_to_use = mappings[:lectures_needed]

        # Find faculty for this course
        cf = CourseFaculty.query.filter_by(course_id=course.id).first()
        faculty_id = cf.faculty_id if cf else None

        for mapping in blocks_to_use:
            entry = TimetableEntry(
                slot_id=slot.id,
                course_id=course.id,
                faculty_id=faculty_id,
                room_id=None,  # Pass 3: room assignment comes later
                time_slot_id=mapping.time_slot_id,
                semester_id=semester_id,
                is_combined=False,
                combined_strength=0,
                is_moved=False,
                original_slot_group=slot.slot_label,
            )
            db.session.add(entry)
            entries_created += 1

    db.session.commit()
    return entries_created


# ─── SWAP SLOTS ─────────────────────────────────────────────

def swap_slot_time_blocks(mapping_id_1, mapping_id_2):
    """
    Swap two slot-time mappings. This allows the admin to manually
    rearrange slot positions in the timetable grid.
    """
    m1 = SlotTimeMapping.query.get(mapping_id_1)
    m2 = SlotTimeMapping.query.get(mapping_id_2)

    if not m1 or not m2:
        raise ValueError("One or both mappings not found.")

    # Swap the slot_ids to avoid UNIQUE constraint violations
    m1.slot_id, m2.slot_id = m2.slot_id, m1.slot_id
    db.session.commit()

    return "Swapped slots successfully."


# ─── CHANGE COURSE SLOT (Admin Override) ────────────────────

def change_course_slot(slot_course_id, new_slot_id, semester_id):
    """Move a course from its current slot to a different slot.

    This is the admin slot override feature:
    - Updates the SlotCourse record to point to the new slot.
    - Marks related TimetableEntry rows as is_moved=True.
    - Preserves original_slot_group for audit trail.
    - Re-validates to detect any new conflicts.

    Args:
        slot_course_id: ID of the SlotCourse record to move.
        new_slot_id: ID of the target Slot to move the course to.
        semester_id: Current semester ID.

    Returns:
        dict with 'success', 'message', and optionally 'warnings'.
    """
    sc = SlotCourse.query.get(slot_course_id)
    if not sc:
        return {'success': False, 'message': 'Slot-course mapping not found.'}

    old_slot = Slot.query.get(sc.slot_id)
    new_slot = Slot.query.get(new_slot_id)
    if not new_slot:
        return {'success': False, 'message': 'Target slot not found.'}

    old_label = old_slot.slot_label if old_slot else 'Unknown'

    # Check for duplicate: is this course already in the target slot for this batch?
    existing = SlotCourse.query.filter_by(
        slot_id=new_slot_id,
        course_id=sc.course_id,
        batch_id=sc.batch_id
    ).first()
    if existing:
        return {'success': False, 'message': f'This course is already in {new_slot.slot_label}.'}

    # Perform the move
    sc.slot_id = new_slot_id
    db.session.flush()

    # Update timetable entries: mark as moved
    entries = TimetableEntry.query.filter_by(
        course_id=sc.course_id,
        semester_id=semester_id,
        slot_id=old_slot.id if old_slot else None,
    ).all()
    for entry in entries:
        if not entry.original_slot_group:
            entry.original_slot_group = old_label
        entry.is_moved = True
        entry.slot_id = new_slot_id

        # Update time_slot_id to match new slot's time blocks
        new_mappings = SlotTimeMapping.query.filter_by(
            slot_id=new_slot_id,
            semester_id=semester_id
        ).all()
        if new_mappings:
            # Keep same relative position (period index) if possible
            new_mappings.sort(key=lambda m: (_get_day_index(m.time_slot.day), m.time_slot.period))

    db.session.commit()

    # Re-run validation for the new slot
    warnings_list = []
    # Quick check: is the faculty double-booked in the new slot?
    cf = CourseFaculty.query.filter_by(course_id=sc.course_id).first()
    if cf:
        fac = Faculty.query.get(cf.faculty_id)
        if fac and not _is_vf(fac.abbreviation):
            other_scs = SlotCourse.query.filter(
                SlotCourse.slot_id == new_slot_id,
                SlotCourse.id != sc.id
            ).all()
            for other_sc in other_scs:
                other_cf = CourseFaculty.query.filter_by(course_id=other_sc.course_id).first()
                if other_cf and other_cf.faculty_id == cf.faculty_id:
                    other_course = Course.query.get(other_sc.course_id)
                    if other_course and other_course.code != sc.course.code:
                        warnings_list.append(
                            f"⚠️ Faculty '{fac.abbreviation}' now teaches both "
                            f"'{sc.course.code}' and '{other_course.code}' in {new_slot.slot_label}."
                        )

    return {
        'success': True,
        'message': f'Moved course from {old_label} to {new_slot.slot_label}.',
        'warnings': warnings_list
    }


# ─── PASS 3: ROOM ASSIGNMENT ────────────────────────────────

def assign_rooms(semester_id):
    """
    Assign rooms to timetable entries (capacity-aware, combined-class support).

    For each time slot, gather all entries and assign the smallest
    available room that fits the course's total student enrollment.
    Detects combined classes and sums their capacity.
    """
    entries = TimetableEntry.query.filter_by(semester_id=semester_id).all()
    rooms = Room.query.order_by(Room.capacity.asc()).all()  # smallest first

    if not rooms:
        violation = SchedulingViolation(
            semester_id=semester_id,
            violation_type='NO_ROOMS',
            severity='error',
            description='No rooms available in the system. Please add rooms before generating the timetable.'
        )
        db.session.add(violation)
        db.session.commit()
        return 0

    # Group entries by time_slot_id
    entries_by_ts = {}
    for entry in entries:
        entries_by_ts.setdefault(entry.time_slot_id, []).append(entry)

    rooms_assigned = 0

    for ts_id, ts_entries in entries_by_ts.items():
        used_room_ids = set()

        # Detect combined classes: same faculty, same course, same timeslot
        # Group by (faculty_id, course_id) to detect and combine
        combined_groups = defaultdict(list)
        standalone = []
        for entry in ts_entries:
            if entry.faculty_id and entry.course_id:
                combined_groups[(entry.faculty_id, entry.course_id)].append(entry)
            else:
                standalone.append(entry)

        # Process combined groups
        for (fac_id, course_id), group in combined_groups.items():
            if len(group) > 1:
                # Mark as combined
                for entry in group:
                    entry.is_combined = True

            # Calculate total students for this course
            course = Course.query.get(course_id)
            if course and course.capacity_override:
                total_students = course.capacity_override
            else:
                total_students = _get_course_student_count(course_id)

            if len(group) > 1:
                for entry in group:
                    entry.combined_strength = total_students

            # Assign one room for the whole group
            assigned = False
            for room in rooms:
                if room.id in used_room_ids:
                    continue
                if room.capacity >= total_students:
                    for entry in group:
                        entry.room_id = room.id
                    used_room_ids.add(room.id)
                    rooms_assigned += 1
                    assigned = True
                    break

            if not assigned:
                # Fallback: assign the largest available room even if too small
                for room in reversed(rooms):
                    if room.id not in used_room_ids:
                        for entry in group:
                            entry.room_id = room.id
                        used_room_ids.add(room.id)
                        rooms_assigned += 1
                        assigned = True
                        course_code = course.code if course else 'Unknown'
                        violation = SchedulingViolation(
                            semester_id=semester_id,
                            violation_type='ROOM_CAPACITY_OVERFLOW',
                            severity='warning',
                            description=f'{course_code} needs {total_students} seats '
                                        f'but assigned to {room.name} ({room.capacity} seats).',
                            course_id=course_id,
                            time_slot_id=ts_id
                        )
                        db.session.add(violation)
                        break
                if not assigned:
                    course_code = course.code if course else 'Unknown'
                    violation = SchedulingViolation(
                        semester_id=semester_id,
                        violation_type='NO_ROOM_AVAILABLE',
                        severity='error',
                        description=f'No rooms available at all for {course_code} '
                                    f'(needs {total_students} seats). All rooms occupied.',
                        course_id=course_id,
                        time_slot_id=ts_id
                    )
                    db.session.add(violation)

        # Process standalone entries
        for entry in standalone:
            total_students = 0
            if entry.course:
                if entry.course.capacity_override:
                    total_students = entry.course.capacity_override
                else:
                    total_students = _get_course_student_count(entry.course_id)

            assigned = False
            for room in rooms:
                if room.id in used_room_ids:
                    continue
                if room.capacity >= total_students:
                    entry.room_id = room.id
                    used_room_ids.add(room.id)
                    rooms_assigned += 1
                    assigned = True
                    break

            if not assigned:
                # Fallback: assign the largest available room even if too small
                for room in reversed(rooms):
                    if room.id not in used_room_ids:
                        entry.room_id = room.id
                        used_room_ids.add(room.id)
                        rooms_assigned += 1
                        assigned = True
                        course_code = entry.course.code if entry.course else 'Unknown'
                        violation = SchedulingViolation(
                            semester_id=semester_id,
                            violation_type='ROOM_CAPACITY_OVERFLOW',
                            severity='warning',
                            description=f'{course_code} needs {total_students} seats '
                                        f'but assigned to {room.name} ({room.capacity} seats).',
                            course_id=entry.course_id,
                            time_slot_id=ts_id
                        )
                        db.session.add(violation)
                        break
                if not assigned:
                    course_code = entry.course.code if entry.course else 'Unknown'
                    violation = SchedulingViolation(
                        semester_id=semester_id,
                        violation_type='NO_ROOM_AVAILABLE',
                        severity='error',
                        description=f'No rooms at all for {course_code} '
                                    f'(needs {total_students} seats). All rooms occupied.',
                        course_id=entry.course_id,
                        time_slot_id=ts_id
                    )
                    db.session.add(violation)

    db.session.commit()
    return rooms_assigned


def _get_course_student_count(course_id):
    """Get total student count for a course by summing up all batches enrolled."""
    from models import CourseBatch, Batch

    batch_links = CourseBatch.query.filter_by(course_id=course_id).all()
    total = 0
    for link in batch_links:
        batch = Batch.query.get(link.batch_id)
        if batch:
            total += batch.student_count
    return total


# ─── MAIN ENTRY POINT ───────────────────────────────────────

def generate_schedule(semester_id):
    """
    Full schedule generation:
    1. Auto-assign slots to time blocks
    2. Validate slot buckets (faculty conflicts, combined classes)
    3. Generate timetable entries from mappings (with L-trimming)
    4. Assign rooms to entries (capacity-aware, combined-class support)
    """
    # Clear old violations
    SchedulingViolation.query.filter_by(semester_id=semester_id).delete()
    db.session.flush()

    # Pass 1: Assign slots to grid
    assign_result = auto_assign_slots(semester_id)

    # Pass 2: Validate slot buckets
    errors, warnings, merges = validate_buckets(semester_id)
    validation_summary = f"{len(errors)} errors, {len(warnings)} warnings, {len(merges)} merges"

    # Pass 2b: Generate entries (with L-trimming)
    entry_count = generate_entries_from_mappings(semester_id)

    # Pass 3: Assign rooms
    rooms_assigned = assign_rooms(semester_id)

    parts = [assign_result]
    parts.append(f"Validation: {validation_summary}.")
    parts.append(f"Created {entry_count} timetable entries.")
    parts.append(f"Assigned {rooms_assigned} rooms.")

    if errors:
        parts.append(f"⚠️ {len(errors)} critical error(s) detected — check Violations Log.")

    return " ".join(parts)
