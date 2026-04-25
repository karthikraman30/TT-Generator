"""
Scheduler Service — Slot-Based Timetable Generation.

Two-pass approach:
  Pass 1: Assign each Slot to 3 (day, period) time blocks (auto or manual).
  Pass 2: Assign rooms to entries (future phase).

Hard Constraints:
  - Wednesday Period 1 (08:00) is always free.
  - Each slot appears on 3 DIFFERENT days (max 1 lecture/day/course).
  - No two slots share the same time block.
"""

from models import db, Slot, SlotCourse, Course, TimeSlot, TimetableEntry, \
    SchedulingViolation, CourseFaculty, Faculty


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


# ─── BLOCKED TIME BLOCKS ────────────────────────────────────
BLOCKED = [
    ('Wednesday', 1),  # Wed 8AM is always free
]


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
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    return days.index(day_name) if day_name in days else 99


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
    day_load = {d: 0 for d in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']}

    assignments = []  # list of (slot, [time_slots])

    for slot in slots:
        # Find 3 time blocks on 3 different days
        chosen = []
        used_days = set()

        # Sort available blocks: prefer days with lower load, then spread across periods
        candidates = [
            ts for ts in available
            if ts.id not in used_ts_ids
        ]
        # Sort: least-loaded day first, then by period for even spread
        candidates.sort(key=lambda ts: (day_load.get(ts.day, 0), ts.period, _get_day_index(ts.day)))

        for ts in candidates:
            if ts.day in used_days:
                continue
            chosen.append(ts)
            used_days.add(ts.day)
            if len(chosen) == blocks_per_slot:
                break

        if len(chosen) < blocks_per_slot:
            # Log a violation — couldn't find enough blocks
            violation = SchedulingViolation(
                semester_id=semester_id,
                violation_type='SLOT_ASSIGNMENT_FAILED',
                severity='error',
                description=f'Could not assign {blocks_per_slot} time blocks to {slot.slot_label}. '
                            f'Only found {len(chosen)} available blocks on different days.'
            )
            db.session.add(violation)

        # Record assignments
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


# ─── PASS 1b: GENERATE TIMETABLE ENTRIES FROM MAPPINGS ──────

def generate_entries_from_mappings(semester_id):
    """
    After slots are mapped to time blocks, create timetable_entries
    for each course based on its L value.

    - L=3: course gets all 3 time blocks of its slot
    - L=2: course gets first 2 time blocks
    - L=1: course gets first 1 time block
    """
    # Clear existing entries
    TimetableEntry.query.filter_by(semester_id=semester_id).delete()
    db.session.flush()

    # Get all slot-course links for this semester
    slot_courses = db.session.query(SlotCourse).join(Slot).filter(
        Slot.semester_id == semester_id
    ).all()

    entries_created = 0
    seen_course_slots = set()  # avoid duplicates (same course in same slot via different batches)

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
            continue  # skip courses with no lectures (e.g., lab-only)

        # Take the first `lectures_needed` time blocks from this slot's assignments
        blocks_to_use = mappings[:lectures_needed]

        # Find faculty for this course
        cf = CourseFaculty.query.filter_by(course_id=course.id).first()
        faculty_id = cf.faculty_id if cf else None

        for mapping in blocks_to_use:
            entry = TimetableEntry(
                slot_id=slot.id,
                course_id=course.id,
                faculty_id=faculty_id,
                room_id=None,  # Pass 2: room assignment comes later
                time_slot_id=mapping.time_slot_id,
                semester_id=semester_id,
                is_combined=False,
                combined_strength=0
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

    # Swap the slot_ids instead of time_slot_ids to avoid 
    # violating the UNIQUE constraint on (time_slot_id, semester_id)
    # during the sequential UPDATE statements inside the commit.
    m1.slot_id, m2.slot_id = m2.slot_id, m1.slot_id
    db.session.commit()

    return f"Swapped slots successfully."


# ─── PASS 2: ROOM ASSIGNMENT ────────────────────────────────

def assign_rooms(semester_id):
    """
    Assign rooms to timetable entries.
    For each time slot, gather all entries and assign the smallest
    available room that fits the course's total student enrollment.

    Room optimization: smallest room that still fits.
    """
    from models import Room, CourseBatch, Batch

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
        used_room_ids = set()  # rooms already used in this time slot

        for entry in ts_entries:
            # Calculate total students for this course
            if entry.course and entry.course.capacity_override:
                total_students = entry.course.capacity_override
            else:
                total_students = _get_course_student_count(entry.course_id)

            # Find smallest available room that fits
            assigned = False
            for room in rooms:
                if room.id in used_room_ids:
                    continue
                if room.capacity >= total_students:
                    entry.room_id = room.id
                    if total_students > 0:
                        entry.combined_strength = total_students
                    used_room_ids.add(room.id)
                    rooms_assigned += 1
                    assigned = True
                    break

            if not assigned:
                # Log violation
                course_code = entry.course.code if entry.course else 'Unknown'
                violation = SchedulingViolation(
                    semester_id=semester_id,
                    violation_type='NO_ROOM_AVAILABLE',
                    severity='warning',
                    description=f'No available room for {course_code} '
                                f'(needs {total_students} seats) at this time slot. '
                                f'All fitting rooms are occupied.',
                    course_id=entry.course_id,
                    time_slot_id=ts_id
                )
                db.session.add(violation)

    db.session.commit()
    return rooms_assigned


def _get_course_student_count(course_id):
    """
    Get total student count for a course by summing up
    all batches enrolled in it.
    """
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
    2. Generate timetable entries from those mappings
    3. Assign rooms to entries
    """
    # Clear old violations
    SchedulingViolation.query.filter_by(semester_id=semester_id).delete()
    db.session.flush()

    # Pass 1: Assign slots to grid
    assign_result = auto_assign_slots(semester_id)

    # Pass 1b: Generate entries
    entry_count = generate_entries_from_mappings(semester_id)

    # Pass 2: Assign rooms
    rooms_assigned = assign_rooms(semester_id)

    return f"{assign_result} Created {entry_count} timetable entries. Assigned {rooms_assigned} rooms."

