"""
Admin routes.
Full CRUD for all entities, file uploads, schedule generation, and violation logs.
"""

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, make_response
from models import db, Program, Semester, Batch, Faculty, Room, Course, Slot, SlotCourse, \
    CourseBatch, CourseFaculty, TimetableEntry, SchedulingViolation, TimeSlot
from routes.auth import admin_required

admin_bp = Blueprint('admin', __name__)


# ─── DASHBOARD ───────────────────────────────────────────────
@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard with overview stats filtered by active semester."""
    active_semester = Semester.query.filter_by(is_active=True).first()
    sid = active_semester.id if active_semester else None

    stats = {
        'semesters': Semester.query.count(),
        'programs': Program.query.count(),
        'batches': Batch.query.filter_by(semester_id=sid).count() if sid else 0,
        'faculty': Faculty.query.count(),
        'rooms': Room.query.count(),
        'courses': Course.query.filter_by(semester_id=sid).count() if sid else 0,
        'entries': TimetableEntry.query.filter_by(semester_id=sid).count() if sid else 0,
        'violations': SchedulingViolation.query.filter_by(semester_id=sid, resolved=False).count() if sid else 0,
    }
    return render_template('admin/dashboard.html', stats=stats, active_semester=active_semester)


# ─── SEMESTERS ───────────────────────────────────────────────
@admin_bp.route('/semesters')
@admin_required
def semesters():
    """List all semesters."""
    all_semesters = Semester.query.order_by(Semester.start_date.desc()).all()
    return render_template('admin/semesters.html', semesters=all_semesters)


@admin_bp.route('/semesters/add', methods=['POST'])
@admin_required
def add_semester():
    """Create a new semester."""
    from datetime import date as dt_date

    name = request.form.get('name', '').strip()
    start_date_str = request.form.get('start_date', '').strip()
    end_date_str = request.form.get('end_date', '').strip()

    if not all([name, start_date_str, end_date_str]):
        flash('All fields are required.', 'error')
        return redirect(url_for('admin.semesters'))

    try:
        start_date = dt_date.fromisoformat(start_date_str)
        end_date = dt_date.fromisoformat(end_date_str)
    except ValueError:
        flash('Invalid date format. Use YYYY-MM-DD.', 'error')
        return redirect(url_for('admin.semesters'))

    if end_date <= start_date:
        flash('End date must be after start date.', 'error')
        return redirect(url_for('admin.semesters'))

    existing = Semester.query.filter_by(name=name).first()
    if existing:
        flash('A semester with this name already exists.', 'error')
        return redirect(url_for('admin.semesters'))

    sem = Semester(name=name, start_date=start_date, end_date=end_date)
    db.session.add(sem)
    db.session.commit()
    flash(f'Semester "{name}" created ({start_date} to {end_date}).', 'success')
    return redirect(url_for('admin.semesters'))


@admin_bp.route('/semesters/<int:sem_id>/activate', methods=['POST'])
@admin_required
def activate_semester(sem_id):
    """Set a semester as the active one."""
    Semester.query.update({'is_active': False})
    sem = Semester.query.get_or_404(sem_id)
    sem.is_active = True
    db.session.commit()
    flash(f'Semester "{sem.name}" is now active.', 'success')
    return redirect(url_for('admin.semesters'))


# ─── PROGRAMS ────────────────────────────────────────────────
@admin_bp.route('/programs')
@admin_required
def programs():
    """List all programs."""
    all_programs = Program.query.order_by(Program.degree_type, Program.name).all()
    return render_template('admin/programs.html', programs=all_programs)


@admin_bp.route('/programs/add', methods=['POST'])
@admin_required
def add_program():
    """Create a new program."""
    name = request.form.get('name', '').strip()
    code = request.form.get('code', '').strip()
    degree_type = request.form.get('degree_type', '').strip()

    if not all([name, code, degree_type]):
        flash('All fields are required.', 'error')
        return redirect(url_for('admin.programs'))

    prog = Program(name=name, code=code, degree_type=degree_type)
    db.session.add(prog)
    db.session.commit()
    flash(f'Program "{name}" created.', 'success')
    return redirect(url_for('admin.programs'))


# ─── FACULTY ─────────────────────────────────────────────────
@admin_bp.route('/faculty')
@admin_required
def faculty_list():
    """List all faculty."""
    all_faculty = Faculty.query.order_by(Faculty.full_name).all()
    return render_template('admin/faculty.html', faculty=all_faculty)


@admin_bp.route('/faculty/add', methods=['POST'])
@admin_required
def add_faculty():
    """Add a faculty member."""
    full_name = request.form.get('full_name', '').strip()
    abbreviation = request.form.get('abbreviation', '').strip().upper()
    email = request.form.get('email', '').strip() or None
    role = request.form.get('role', 'faculty').strip()

    if not all([full_name, abbreviation]):
        flash('Name and abbreviation are required.', 'error')
        return redirect(url_for('admin.faculty_list'))

    existing = Faculty.query.filter_by(abbreviation=abbreviation).first()
    if existing:
        flash(f'Abbreviation "{abbreviation}" already exists.', 'error')
        return redirect(url_for('admin.faculty_list'))

    fac = Faculty(full_name=full_name, abbreviation=abbreviation, email=email, role=role)
    db.session.add(fac)
    db.session.commit()
    flash(f'Faculty "{full_name}" added.', 'success')
    return redirect(url_for('admin.faculty_list'))


@admin_bp.route('/faculty/<int:fac_id>/delete', methods=['POST'])
@admin_required
def delete_faculty(fac_id):
    """Delete a faculty member."""
    fac = Faculty.query.get_or_404(fac_id)
    db.session.delete(fac)
    db.session.commit()
    flash(f'Faculty "{fac.full_name}" deleted.', 'success')
    return redirect(url_for('admin.faculty_list'))


# ─── ROOMS ───────────────────────────────────────────────────
@admin_bp.route('/rooms')
@admin_required
def rooms():
    """List all rooms."""
    all_rooms = Room.query.order_by(Room.capacity.desc()).all()
    return render_template('admin/rooms.html', rooms=all_rooms)


@admin_bp.route('/rooms/add', methods=['POST'])
@admin_required
def add_room():
    """Add a room."""
    name = request.form.get('name', '').strip()
    capacity = request.form.get('capacity', '0').strip()
    building = request.form.get('building', '').strip() or None
    room_type = request.form.get('room_type', 'lecture').strip()

    if not name or not capacity.isdigit() or int(capacity) <= 0:
        flash('Valid room name and capacity are required.', 'error')
        return redirect(url_for('admin.rooms'))

    room = Room(name=name, capacity=int(capacity), building=building, room_type=room_type)
    db.session.add(room)
    db.session.commit()
    flash(f'Room "{name}" added.', 'success')
    return redirect(url_for('admin.rooms'))


@admin_bp.route('/rooms/<int:room_id>/delete', methods=['POST'])
@admin_required
def delete_room(room_id):
    """Delete a room."""
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    flash(f'Room "{room.name}" deleted.', 'success')
    return redirect(url_for('admin.rooms'))


# ─── COURSES ─────────────────────────────────────────────────
@admin_bp.route('/courses')
@admin_required
def courses():
    """List courses for the active semester."""
    active = Semester.query.filter_by(is_active=True).first()
    if active:
        all_courses = Course.query.filter_by(semester_id=active.id).order_by(Course.code).all()
    else:
        all_courses = Course.query.order_by(Course.code).all()
    semesters = Semester.query.all()
    return render_template('admin/courses.html', courses=all_courses, active_semester=active, semesters=semesters)


@admin_bp.route('/courses/<int:course_id>/update-capacity', methods=['POST'])
@admin_required
def update_course_capacity(course_id):
    """Update required seats (capacity override) for a specific course/section."""
    course = Course.query.get_or_404(course_id)
    capacity = request.form.get('capacity_override', '').strip()
    
    if not capacity:
        course.capacity_override = None
        flash(f'Cleared override for {course.code} {course.name}. Will use sum of batches.', 'success')
    elif capacity.isdigit():
        course.capacity_override = int(capacity)
        flash(f'Set required seats for {course.code} {course.name} to {capacity}.', 'success')
    else:
        flash('Invalid capacity value.', 'error')
        
    db.session.commit()
    return redirect(url_for('admin.courses'))


@admin_bp.route('/courses/bulk-capacity', methods=['POST'])
@admin_required
def bulk_set_capacity():
    """Bulk-set capacity overrides based on section patterns in course names."""
    active = Semester.query.filter_by(is_active=True).first()
    if not active:
        flash('No active semester.', 'error')
        return redirect(url_for('admin.courses'))

    sec_a = request.form.get('sec_a_strength', '').strip()
    sec_b = request.form.get('sec_b_strength', '').strip()
    cs_only = request.form.get('cs_only_strength', '').strip()
    no_sec = request.form.get('no_sec_strength', '').strip()

    courses = Course.query.filter_by(semester_id=active.id).all()
    updated = 0

    for c in courses:
        if sec_a and sec_a.isdigit() and '(Sec A)' in c.name:
            c.capacity_override = int(sec_a)
            updated += 1
        elif sec_b and sec_b.isdigit() and '(Sec B)' in c.name:
            c.capacity_override = int(sec_b)
            updated += 1
        elif cs_only and cs_only.isdigit():
            # Check if course belongs to a CS-Only batch
            batch_names = [cb.name for cb in c.batches.all()]
            if any('CS-Only' in bn for bn in batch_names):
                c.capacity_override = int(cs_only)
                updated += 1
        elif no_sec and no_sec.isdigit() and '(Sec' not in c.name:
            # Only set default if no override already exists
            if not c.capacity_override:
                batch_names = [cb.name for cb in c.batches.all()]
                if not any('CS-Only' in bn for bn in batch_names):
                    c.capacity_override = int(no_sec)
                    updated += 1

    db.session.commit()
    flash(f'Updated capacity for {updated} courses.', 'success')
    return redirect(url_for('admin.courses'))


@admin_bp.route('/courses/add', methods=['POST'])
@admin_required
def add_course():
    """Manually add a course to the active semester."""
    active = Semester.query.filter_by(is_active=True).first()
    if not active:
        flash('No active semester. Activate one first.', 'error')
        return redirect(url_for('admin.courses'))

    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    lectures = request.form.get('lectures', '0').strip()
    tutorials = request.form.get('tutorials', '0').strip()
    practicals = request.form.get('practicals', '0').strip()
    credits = request.form.get('credits', '0').strip()
    course_type = request.form.get('course_type', 'Core').strip()
    slot_id = request.form.get('slot_id', '').strip()
    faculty_abbr = request.form.get('faculty_abbr', '').strip().upper()
    capacity = request.form.get('capacity_override', '').strip()

    if not code or not name:
        flash('Course code and name are required.', 'error')
        return redirect(url_for('admin.courses'))

    # Check for duplicates
    existing = Course.query.filter_by(code=code, name=name, semester_id=active.id).first()
    if existing:
        flash(f'Course {code} "{name}" already exists in this semester.', 'error')
        return redirect(url_for('admin.courses'))

    course = Course(
        code=code,
        name=name,
        semester_id=active.id,
        lectures_per_week=int(lectures) if lectures.isdigit() else 0,
        tutorials_per_week=int(tutorials) if tutorials.isdigit() else 0,
        practicals_per_week=int(practicals) if practicals.isdigit() else 0,
        credits=int(credits) if credits.isdigit() else 0,
        course_type=course_type,
        capacity_override=int(capacity) if capacity and capacity.isdigit() else None,
    )
    db.session.add(course)
    db.session.flush()  # get course.id

    # Assign to slot if provided
    if slot_id and slot_id.isdigit():
        slot = Slot.query.get(int(slot_id))
        if slot:
            sc = SlotCourse(slot_id=slot.id, course_id=course.id)
            db.session.add(sc)

    # Link faculty if provided
    if faculty_abbr:
        fac = Faculty.query.filter_by(abbreviation=faculty_abbr).first()
        if fac:
            cf = CourseFaculty(course_id=course.id, faculty_id=fac.id)
            db.session.add(cf)

    db.session.commit()
    flash(f'Course {code} "{name}" added successfully.', 'success')
    return redirect(url_for('admin.courses'))

# ─── BATCHES ─────────────────────────────────────────────────
@admin_bp.route('/batches')
@admin_required
def batches():
    """List all batches for the active semester."""
    active = Semester.query.filter_by(is_active=True).first()
    if active:
        all_batches = Batch.query.filter_by(semester_id=active.id).order_by(Batch.name).all()
    else:
        all_batches = Batch.query.order_by(Batch.name).all()

    # Pre-compute batch→courses mapping
    batch_courses = {}
    for b in all_batches:
        courses = db.session.query(Course).join(CourseBatch, CourseBatch.course_id == Course.id)\
            .filter(CourseBatch.batch_id == b.id).order_by(Course.code).all()
        batch_courses[b.id] = courses

    return render_template('admin/batches.html', batches=all_batches,
                           batch_courses=batch_courses, active_semester=active)


@admin_bp.route('/batches/<int:batch_id>/update-count', methods=['POST'])
@admin_required
def update_batch_count(batch_id):
    """Update student count for a batch."""
    batch = Batch.query.get_or_404(batch_id)
    count = request.form.get('student_count', '0').strip()
    if count.isdigit():
        batch.student_count = int(count)
        db.session.commit()
        flash(f'Updated {batch.name} to {count} students.', 'success')
    else:
        flash('Invalid student count.', 'error')
    return redirect(url_for('admin.batches'))



@admin_bp.route('/upload', methods=['GET', 'POST'])
@admin_required
def upload():
    """Upload Excel files for data ingestion."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('admin.upload'))

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('admin.upload'))

        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            flash('Only Excel (.xlsx, .xls) and CSV files are accepted.', 'error')
            return redirect(url_for('admin.upload'))

        # Save the file
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        upload_type = request.form.get('upload_type', 'slots')

        try:
            if upload_type == 'slots':
                from services.excel_parser import parse_slots_file
                result = parse_slots_file(filepath)
                flash(f'Slots file processed: {result}', 'success')
            elif upload_type == 'rooms':
                from services.excel_parser import parse_rooms_file
                result = parse_rooms_file(filepath)
                flash(f'Rooms file processed: {result}', 'success')
            elif upload_type == 'faculty_mapping':
                from services.excel_parser import parse_faculty_mapping
                result = parse_faculty_mapping(filepath)
                flash(f'Faculty mapping processed: {result}', 'success')
            elif upload_type == 'section_strengths':
                from services.excel_parser import parse_section_strengths
                result = parse_section_strengths(filepath)
                flash(f'Section strengths processed: {result}', 'success')
            elif upload_type == 'course_strengths':
                from services.excel_parser import parse_course_strengths
                result = parse_course_strengths(filepath)
                flash(f'Course strengths processed: {result}', 'success')
            else:
                flash('Unknown upload type.', 'error')
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')

        return redirect(url_for('admin.upload'))

    return render_template('admin/upload.html')


# ─── TIMETABLE ───────────────────────────────────────────────
@admin_bp.route('/timetable')
@admin_required
def timetable():
    """View the master timetable."""
    active = Semester.query.filter_by(is_active=True).first()
    entries = []
    time_slots = TimeSlot.query.order_by(TimeSlot.day, TimeSlot.period).all()
    batches = []

    if active:
        entries = TimetableEntry.query.filter_by(semester_id=active.id).all()
        batches = Batch.query.filter_by(semester_id=active.id).order_by(Batch.name).all()

    return render_template('admin/timetable.html',
                           entries=entries, time_slots=time_slots,
                           batches=batches, active_semester=active)


@admin_bp.route('/generate', methods=['POST'])
@admin_required
def generate_timetable():
    """Trigger the scheduling algorithm."""
    active = Semester.query.filter_by(is_active=True).first()
    if not active:
        flash('No active semester set. Please activate a semester first.', 'error')
        return redirect(url_for('admin.dashboard'))

    try:
        from services.scheduler import generate_schedule
        result = generate_schedule(active.id)
        flash(f'Timetable generated: {result}', 'success')
    except Exception as e:
        flash(f'Scheduling failed: {str(e)}', 'error')

    return redirect(url_for('admin.timetable'))


# ─── VIOLATIONS LOG ─────────────────────────────────────────
@admin_bp.route('/violations')
@admin_required
def violations():
    """View scheduling violations and logs."""
    active = Semester.query.filter_by(is_active=True).first()
    if active:
        all_violations = SchedulingViolation.query.filter_by(semester_id=active.id) \
            .order_by(SchedulingViolation.created_at.desc()).all()
    else:
        all_violations = SchedulingViolation.query.order_by(SchedulingViolation.created_at.desc()).all()
    return render_template('admin/violations.html', violations=all_violations, active_semester=active)


@admin_bp.route('/violations/<int:vid>/resolve', methods=['POST'])
@admin_required
def resolve_violation(vid):
    """Mark a violation as resolved."""
    v = SchedulingViolation.query.get_or_404(vid)
    v.resolved = True
    db.session.commit()
    flash('Violation marked as resolved.', 'success')
    return redirect(url_for('admin.violations'))


# ─── API ENDPOINTS ───────────────────────────────────────────
@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    """JSON stats for dashboard widgets."""
    active = Semester.query.filter_by(is_active=True).first()
    return jsonify({
        'semesters': Semester.query.count(),
        'programs': Program.query.count(),
        'batches': Batch.query.filter_by(semester_id=active.id).count() if active else 0,
        'faculty': Faculty.query.count(),
        'rooms': Room.query.count(),
        'courses': Course.query.filter_by(semester_id=active.id).count() if active else 0,
        'entries': TimetableEntry.query.filter_by(semester_id=active.id).count() if active else 0,
        'violations_open': SchedulingViolation.query.filter_by(resolved=False).count(),
    })


# ─── SLOT GRID VIEW ─────────────────────────────────────────
@admin_bp.route('/slot-grid')
@admin_required
def slot_grid():
    """View the slot-to-time mapping grid."""
    from services.scheduler import SlotTimeMapping
    active = Semester.query.filter_by(is_active=True).first()
    mappings = []
    slots = []
    time_slots = TimeSlot.query.order_by(TimeSlot.day, TimeSlot.period).all()

    if active:
        mappings = SlotTimeMapping.query.filter_by(semester_id=active.id).all()
        slots = Slot.query.filter(
            Slot.semester_id == active.id,
            Slot.slot_number.isnot(None)
        ).order_by(Slot.slot_number).all()

    # Build a grid lookup: (day, period) -> slot_label
    grid = {}
    mapping_ids = {}
    for m in mappings:
        key = (m.time_slot.day, m.time_slot.period)
        grid[key] = m.slot.slot_label
        mapping_ids[key] = m.id

    return render_template('admin/slot_grid.html',
                           grid=grid, mapping_ids=mapping_ids,
                           slots=slots, time_slots=time_slots,
                           active_semester=active)


@admin_bp.route('/slot-grid/swap', methods=['POST'])
@admin_required
def swap_slots():
    """Swap two slot-time block assignments."""
    from services.scheduler import swap_slot_time_blocks
    mapping_id_1 = request.form.get('mapping_id_1', type=int)
    mapping_id_2 = request.form.get('mapping_id_2', type=int)

    if not mapping_id_1 or not mapping_id_2:
        flash('Select two time blocks to swap.', 'error')
        return redirect(url_for('admin.slot_grid'))

    try:
        result = swap_slot_time_blocks(mapping_id_1, mapping_id_2)
        # Regenerate entries after swap
        active = Semester.query.filter_by(is_active=True).first()
        if active:
            from services.scheduler import generate_entries_from_mappings
            generate_entries_from_mappings(active.id)
        flash(f'Swap complete: {result}. Timetable entries regenerated.', 'success')
    except Exception as e:
        flash(f'Swap failed: {str(e)}', 'error')

    return redirect(url_for('admin.slot_grid'))





# ─── ADMIN SLOT OVERRIDE ────────────────────────────────────
@admin_bp.route('/api/course/change-slot', methods=['POST'])
@admin_required
def api_change_course_slot():
    """Admin overrides a course's slot assignment."""
    from services.scheduler import change_course_slot

    data = request.get_json()
    slot_course_id = data.get('slot_course_id')
    new_slot_id = data.get('new_slot_id')

    active = Semester.query.filter_by(is_active=True).first()
    if not active:
        return jsonify({'success': False, 'error': 'No active semester'}), 400

    result = change_course_slot(slot_course_id, new_slot_id, active.id)
    return jsonify(result)


# ─── ICS DOWNLOAD (Admin for any faculty) ────────────────────
@admin_bp.route('/download-faculty-ics/<int:faculty_id>')
@admin_required
def download_faculty_ics(faculty_id):
    """Admin downloads a specific faculty member's ICS calendar."""
    from services.ics_generator import generate_faculty_ics

    faculty = Faculty.query.get_or_404(faculty_id)

    try:
        ics_bytes = generate_faculty_ics(faculty_id)
    except Exception as e:
        flash(f'ICS generation failed: {str(e)}', 'error')
        return redirect(url_for('admin.faculty_list'))

    response = make_response(ics_bytes)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = \
        f'attachment; filename=Timetable_{faculty.abbreviation}.ics'
    return response


