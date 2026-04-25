"""
SQLAlchemy ORM models for the Timetable Generator.
Maps directly to the PostgreSQL schema defined in sql/schema.sql.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ─── PROGRAMS ────────────────────────────────────────────────
class Program(db.Model):
    __tablename__ = 'programs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(30), nullable=False, unique=True)
    degree_type = db.Column(db.String(20), nullable=False)  # BTech, MTech, MSc
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    batches = db.relationship('Batch', backref='program', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name,
            'code': self.code, 'degree_type': self.degree_type
        }


# ─── SEMESTERS ───────────────────────────────────────────────
class Semester(db.Model):
    __tablename__ = 'semesters'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    batches = db.relationship('Batch', backref='semester', lazy='dynamic')
    courses = db.relationship('Course', backref='semester', lazy='dynamic')
    slots = db.relationship('Slot', backref='semester', lazy='dynamic')

    @property
    def semester_weeks(self):
        """Calculate weeks between start and end dates."""
        if self.start_date and self.end_date:
            delta = (self.end_date - self.start_date).days
            return max(1, delta // 7)
        return 16  # default

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': self.is_active
        }


# ─── BATCHES ─────────────────────────────────────────────────
class Batch(db.Model):
    __tablename__ = 'batches'

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id', ondelete='SET NULL'))
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='CASCADE'))
    name = db.Column(db.String(150), nullable=False)
    sem_number = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(10))
    student_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name,
            'sem_number': self.sem_number, 'section': self.section,
            'student_count': self.student_count,
            'program': self.program.name if self.program else None
        }


# ─── FACULTY ─────────────────────────────────────────────────
class Faculty(db.Model):
    __tablename__ = 'faculty'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    abbreviation = db.Column(db.String(10), nullable=False, unique=True)
    email = db.Column(db.String(200), unique=True)
    firebase_uid = db.Column(db.String(200), unique=True)
    role = db.Column(db.String(20), nullable=False, default='faculty')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'full_name': self.full_name,
            'abbreviation': self.abbreviation, 'email': self.email,
            'role': self.role
        }


# ─── ROOMS ───────────────────────────────────────────────────
class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    capacity = db.Column(db.Integer, nullable=False)
    building = db.Column(db.String(100))
    floor = db.Column(db.Integer)
    room_type = db.Column(db.String(20), default='lecture')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name,
            'capacity': self.capacity, 'building': self.building,
            'room_type': self.room_type
        }


# ─── COURSES ─────────────────────────────────────────────────
class Course(db.Model):
    __tablename__ = 'courses'
    __table_args__ = (db.UniqueConstraint('code', 'name', 'semester_id'),)

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    lectures_per_week = db.Column(db.Integer, nullable=False, default=0)
    tutorials_per_week = db.Column(db.Integer, nullable=False, default=0)
    practicals_per_week = db.Column(db.Integer, nullable=False, default=0)
    credits = db.Column(db.Numeric(3, 1), nullable=False, default=0)
    course_type = db.Column(db.String(40), nullable=False, default='Core')
    capacity_override = db.Column(db.Integer, nullable=True)  # Admin overrides for specific sections
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='CASCADE'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    batches = db.relationship('Batch', secondary='course_batches', backref='courses', lazy='dynamic')
    faculty_members = db.relationship('Faculty', secondary='course_faculty', backref='courses', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'L': self.lectures_per_week, 'T': self.tutorials_per_week,
            'P': self.practicals_per_week, 'C': float(self.credits),
            'course_type': self.course_type
        }


# ─── COURSE ↔ BATCH ─────────────────────────────────────────
class CourseBatch(db.Model):
    __tablename__ = 'course_batches'
    __table_args__ = (db.UniqueConstraint('course_id', 'batch_id'),)

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'))
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id', ondelete='CASCADE'))


# ─── COURSE ↔ FACULTY ───────────────────────────────────────
class CourseFaculty(db.Model):
    __tablename__ = 'course_faculty'
    __table_args__ = (db.UniqueConstraint('course_id', 'faculty_id'),)

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='CASCADE'))


# ─── SLOTS ───────────────────────────────────────────────────
class Slot(db.Model):
    __tablename__ = 'slots'
    __table_args__ = (db.UniqueConstraint('slot_label', 'semester_id'),)

    id = db.Column(db.Integer, primary_key=True)
    slot_label = db.Column(db.String(20), nullable=False)
    slot_number = db.Column(db.Integer)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='CASCADE'))

    def to_dict(self):
        return {
            'id': self.id, 'slot_label': self.slot_label,
            'slot_number': self.slot_number
        }


# ─── SLOT ↔ COURSE ──────────────────────────────────────────
class SlotCourse(db.Model):
    __tablename__ = 'slot_courses'
    __table_args__ = (db.UniqueConstraint('slot_id', 'course_id', 'batch_id'),)

    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('slots.id', ondelete='CASCADE'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'))
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id', ondelete='CASCADE'))

    slot = db.relationship('Slot', backref='slot_courses')
    course = db.relationship('Course', backref='slot_courses')
    batch = db.relationship('Batch', backref='slot_courses')


# ─── TIME SLOTS (GRID) ──────────────────────────────────────
class TimeSlot(db.Model):
    __tablename__ = 'time_slots'
    __table_args__ = (db.UniqueConstraint('day', 'period'),)

    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10), nullable=False)
    period = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id, 'day': self.day, 'period': self.period,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M')
        }


# ─── TIMETABLE ENTRIES ──────────────────────────────────────
class TimetableEntry(db.Model):
    __tablename__ = 'timetable_entries'

    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('slots.id', ondelete='CASCADE'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='SET NULL'))
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='SET NULL'))
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slots.id', ondelete='CASCADE'))
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='CASCADE'))
    is_combined = db.Column(db.Boolean, default=False)
    combined_strength = db.Column(db.Integer, default=0)
    is_moved = db.Column(db.Boolean, default=False)
    original_slot_group = db.Column(db.String(20))  # Original slot from Excel before admin override
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    slot = db.relationship('Slot', backref='timetable_entries')
    course = db.relationship('Course', backref='timetable_entries')
    faculty = db.relationship('Faculty', backref='timetable_entries')
    room = db.relationship('Room', backref='timetable_entries')
    time_slot = db.relationship('TimeSlot', backref='timetable_entries')
    semester = db.relationship('Semester', backref='timetable_entries')

    def to_dict(self):
        return {
            'id': self.id,
            'slot': self.slot.slot_label if self.slot else None,
            'course': self.course.to_dict() if self.course else None,
            'faculty': self.faculty.to_dict() if self.faculty else None,
            'room': self.room.to_dict() if self.room else None,
            'time_slot': self.time_slot.to_dict() if self.time_slot else None,
            'is_combined': self.is_combined,
            'combined_strength': self.combined_strength
        }


# ─── SCHEDULING VIOLATIONS ──────────────────────────────────
class SchedulingViolation(db.Model):
    __tablename__ = 'scheduling_violations'

    id = db.Column(db.Integer, primary_key=True)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='CASCADE'))
    violation_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default='error')
    description = db.Column(db.Text, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='SET NULL'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='SET NULL'))
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='SET NULL'))
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slots.id', ondelete='SET NULL'))
    resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    semester = db.relationship('Semester', backref='violations')
    course = db.relationship('Course', backref='violations')
    faculty = db.relationship('Faculty', backref='violations')
    room = db.relationship('Room', backref='violations')
    time_slot = db.relationship('TimeSlot', backref='violations')

    def to_dict(self):
        return {
            'id': self.id,
            'violation_type': self.violation_type,
            'severity': self.severity,
            'description': self.description,
            'course': self.course.code if self.course else None,
            'faculty': self.faculty.abbreviation if self.faculty else None,
            'room': self.room.name if self.room else None,
            'resolved': self.resolved,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ─── FACULTY NAME MAP ───────────────────────────────────────
class FacultyNameMap(db.Model):
    """Maps faculty abbreviations to full academic names (for PDFs/ICS exports)."""
    __tablename__ = 'faculty_name_maps'

    id = db.Column(db.Integer, primary_key=True)
    abbreviation = db.Column(db.String(10), db.ForeignKey('faculty.abbreviation', ondelete='CASCADE'),
                             nullable=False, unique=True)
    full_name = db.Column(db.String(200), nullable=False)
    source = db.Column(db.String(50), default='Manual')  # 'Excel', 'Admin UI', 'Manual'
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    faculty = db.relationship('Faculty', backref=db.backref('name_map', uselist=False))

    def to_dict(self):
        return {
            'id': self.id, 'abbreviation': self.abbreviation,
            'full_name': self.full_name, 'source': self.source
        }


# ─── BATCH OVERLAP RULES ────────────────────────────────────
class BatchOverlapRule(db.Model):
    """Defines which student batches share students (e.g., CS-Only ⊆ ICT Sec B).
    Used by the scheduler for conflict validation instead of hardcoded checks."""
    __tablename__ = 'batch_overlap_rules'

    id = db.Column(db.Integer, primary_key=True)
    batch_a = db.Column(db.String(150), nullable=False)
    section_a = db.Column(db.String(20), nullable=False, default='All')
    batch_b = db.Column(db.String(150), nullable=False)
    section_b = db.Column(db.String(20), nullable=False, default='All')
    description = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'batch_a': self.batch_a, 'section_a': self.section_a,
            'batch_b': self.batch_b, 'section_b': self.section_b,
            'description': self.description
        }


# ─── L-TRIMMING OVERRIDES ───────────────────────────────────
class LTrimmingOverride(db.Model):
    """Admin override for L-value trimming.
    When a course has fewer lecture hours (L) than its slot provides,
    the algorithm picks the most spaced-out days by default.
    This table allows admins to manually choose which days to keep."""
    __tablename__ = 'l_trimming_overrides'
    __table_args__ = (db.UniqueConstraint('course_code', 'semester_id'),)

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='CASCADE'))
    keep_days = db.Column(db.Text, nullable=False)  # Comma-separated: "Monday,Friday"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    semester = db.relationship('Semester', backref='l_trimming_overrides')

    @property
    def keep_days_list(self):
        """Parse the comma-separated days string into a list."""
        return [d.strip() for d in self.keep_days.split(',') if d.strip()]

    def to_dict(self):
        return {
            'id': self.id, 'course_code': self.course_code,
            'keep_days': self.keep_days_list,
            'semester': self.semester.name if self.semester else None
        }


# ─── TIMETABLE SNAPSHOTS ────────────────────────────────────
class TimetableSnapshot(db.Model):
    """Stores complete timetable snapshots for versioning and history."""
    __tablename__ = 'timetable_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='CASCADE'))
    notes = db.Column(db.Text)
    entry_count = db.Column(db.Integer, default=0)
    violation_count = db.Column(db.Integer, default=0)
    snapshot_data = db.Column(db.Text, nullable=False)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    semester = db.relationship('Semester', backref='snapshots')

    def to_dict(self):
        return {
            'id': self.id, 'label': self.label,
            'entry_count': self.entry_count,
            'violation_count': self.violation_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
