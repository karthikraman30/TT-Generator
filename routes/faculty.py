"""
Faculty routes.
Read-only views: personal timetable, master timetable, and ICS download.
"""

from flask import Blueprint, render_template, session, make_response, flash, redirect, url_for
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


@faculty_bp.route('/download-ics')
@login_required
def download_ics():
    """Faculty downloads their own timetable as an ICS calendar file."""
    from services.ics_generator import generate_faculty_ics

    user = session.get('user', {})
    faculty_id = user.get('id')

    if not faculty_id:
        flash('No faculty profile linked.', 'error')
        return redirect(url_for('faculty.dashboard'))

    faculty = Faculty.query.get(faculty_id)
    if not faculty:
        flash('Faculty not found.', 'error')
        return redirect(url_for('faculty.dashboard'))

    try:
        ics_bytes = generate_faculty_ics(faculty_id)
    except Exception as e:
        flash(f'ICS generation failed: {str(e)}', 'error')
        return redirect(url_for('faculty.dashboard'))

    response = make_response(ics_bytes)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = \
        f'attachment; filename=Timetable_{faculty.abbreviation}.ics'
    return response


@faculty_bp.route('/download/pdf')
@login_required
def download_pdf():
    """Download the specific faculty's timetable as a PDF."""
    active = Semester.query.filter_by(is_active=True).first()
    if not active:
        flash('No active semester.', 'error')
        return redirect(url_for('faculty.dashboard'))

    faculty_id = session.get('user', {}).get('id')
    faculty = Faculty.query.get(faculty_id) if faculty_id else None
    if not faculty:
        flash('Faculty profile not found.', 'error')
        return redirect(url_for('faculty.dashboard'))

    from services.pdf_generator import generate_faculty_pdf
    pdf_buffer = generate_faculty_pdf(active.id, faculty.id)
    
    if not pdf_buffer:
        flash('Failed to generate PDF.', 'error')
        return redirect(url_for('faculty.dashboard'))
        
    from flask import send_file
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"My_Timetable_{faculty.abbreviation}_{active.name.replace(' ', '_')}.pdf",
        mimetype='application/pdf'
    )
