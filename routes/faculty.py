"""
Faculty routes.
Read-only views: personal timetable and master timetable.
"""

from flask import Blueprint, render_template, session
from models import Semester, TimetableEntry, TimeSlot, Batch, Faculty
from routes.auth import login_required

faculty_bp = Blueprint('faculty', __name__)


@faculty_bp.route('/')
@login_required
def dashboard():
    """Faculty dashboard – personal schedule overview."""
    user = session.get('user', {})
    active = Semester.query.filter_by(is_active=True).first()
    personal_entries = []
    time_slots = TimeSlot.query.order_by(TimeSlot.day, TimeSlot.period).all()

    if active and user.get('id'):
        personal_entries = TimetableEntry.query.filter_by(
            semester_id=active.id,
            faculty_id=user['id']
        ).all()

    return render_template('faculty/dashboard.html',
                           entries=personal_entries,
                           time_slots=time_slots,
                           active_semester=active)


@faculty_bp.route('/timetable')
@login_required
def my_timetable():
    """Faculty's personal timetable grid."""
    user = session.get('user', {})
    active = Semester.query.filter_by(is_active=True).first()
    entries = []
    time_slots = TimeSlot.query.order_by(TimeSlot.day, TimeSlot.period).all()

    if active and user.get('id'):
        entries = TimetableEntry.query.filter_by(
            semester_id=active.id,
            faculty_id=user['id']
        ).all()

    return render_template('faculty/timetable.html',
                           entries=entries,
                           time_slots=time_slots,
                           active_semester=active,
                           view_type='personal')


@faculty_bp.route('/master')
@login_required
def master_timetable():
    """Master timetable view (read-only for faculty)."""
    active = Semester.query.filter_by(is_active=True).first()
    entries = []
    time_slots = TimeSlot.query.order_by(TimeSlot.day, TimeSlot.period).all()
    batches = []

    if active:
        entries = TimetableEntry.query.filter_by(semester_id=active.id).all()
        batches = Batch.query.filter_by(semester_id=active.id).order_by(Batch.name).all()

    return render_template('faculty/timetable.html',
                           entries=entries,
                           time_slots=time_slots,
                           batches=batches,
                           active_semester=active,
                           view_type='master')
