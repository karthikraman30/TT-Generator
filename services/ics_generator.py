"""
ICS (iCalendar) Generator Service.
Generates RFC 5545 compliant .ics calendar files for faculty timetables.
Compatible with Google Calendar, Apple Calendar, and Outlook.

Ported from sai/faculty_pdf.py and adapted to work with SPM's
SQLAlchemy ORM models instead of raw SQL queries.
"""

import re
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta

from models import db, Faculty, TimetableEntry, TimeSlot, Semester, \
    CourseBatch, Batch


# ─── CONSTANTS ──────────────────────────────────────────────
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
PERIODS = ['08:00', '09:00', '10:00', '11:00', '12:00']

DAY_INDEX = {
    'Monday': 0, 'Tuesday': 1, 'Wednesday': 2,
    'Thursday': 3, 'Friday': 4,
}


# ─── HELPERS ────────────────────────────────────────────────

def _get_full_name(faculty):
    """Resolve a Faculty ORM object to its full academic name."""
    if faculty is None:
        return 'Unknown'

    # Use faculty's full_name if available
    if faculty.full_name and faculty.full_name != faculty.abbreviation:
        return faculty.full_name

    # Fall back to abbreviation
    return faculty.abbreviation


def _clean_batch(batch_name):
    """Clean verbose batch labels for display.

    'BTech Sem-II (ICT + CS)' → 'ICT+CS'
    'MTech Sem-II (ICT-ML)' → 'ICT-ML'
    """
    match = re.search(r'\(([^)]+)\)', batch_name)
    if match:
        return match.group(1).strip()
    cleaned = re.sub(r'BTech\s+Sem-\w+\s*', '', batch_name).strip()
    cleaned = re.sub(r'MTech\s+Sem-\w+\s*', '', cleaned).strip()
    return cleaned or batch_name


def _ics_fold(line):
    """Fold a line per RFC 5545 (max 75 octets, continuation with space)."""
    encoded = line.encode('utf-8')
    if len(encoded) <= 75:
        return line
    result = []
    while len(encoded) > 75:
        cut = 75 if not result else 74
        while cut > 0 and (encoded[cut] & 0xC0) == 0x80:
            cut -= 1
        if result:
            result.append(' ' + encoded[:cut].decode('utf-8'))
        else:
            result.append(encoded[:cut].decode('utf-8'))
        encoded = encoded[cut:]
    if encoded:
        if result:
            result.append(' ' + encoded.decode('utf-8'))
        else:
            result.append(encoded.decode('utf-8'))
    return '\r\n'.join(result)


def _ics_escape(text):
    """Escape special characters for ICS text fields."""
    return (text
            .replace('\\', '\\\\')
            .replace(';', '\\;')
            .replace(',', '\\,')
            .replace('\n', '\\n'))


# ─── MAIN GENERATOR ────────────────────────────────────────

def generate_faculty_ics(faculty_id, timezone='Asia/Kolkata'):
    """
    Generate an ICS calendar file for one faculty member.

    Args:
        faculty_id: The faculty's DB ID.
        timezone: IANA timezone name (default: Asia/Kolkata).

    Returns:
        bytes — The ICS content as a byte string (UTF-8).
    """
    faculty = Faculty.query.get(faculty_id)
    if not faculty:
        raise ValueError(f"Faculty ID {faculty_id} not found.")

    full_name = _get_full_name(faculty)
    abbr = faculty.abbreviation

    active_sem = Semester.query.filter_by(is_active=True).first()
    if not active_sem:
        raise ValueError("No active semester.")

    # Use semester dates dynamically
    start_date = datetime.combine(active_sem.start_date, datetime.min.time())
    semester_weeks = active_sem.semester_weeks

    # Get all timetable entries for this faculty
    entries = TimetableEntry.query.filter_by(
        faculty_id=faculty_id,
        semester_id=active_sem.id
    ).all()

    # Build schedule lookup: (day, hour_key) → list of entry data
    schedule = defaultdict(list)
    for entry in entries:
        ts = entry.time_slot
        if not ts:
            continue
        hour_key = ts.start_time.strftime('%H:%M')

        # Get batch info
        batch_names = []
        if entry.course:
            cbs = CourseBatch.query.filter_by(course_id=entry.course_id).all()
            for cb in cbs:
                b = Batch.query.get(cb.batch_id)
                if b:
                    batch_names.append(_clean_batch(b.name))

        schedule[(ts.day, hour_key)].append({
            'course_code': entry.course.code if entry.course else '?',
            'course_name': entry.course.name if entry.course else '',
            'room': entry.room.name if entry.room else 'TBA',
            'batches': batch_names,
        })

    # Build ICS
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//DA-IICT Timetable Generator//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        _ics_fold(f'X-WR-CALNAME:Timetable — {full_name}'),
        f'X-WR-TIMEZONE:{timezone}',
    ]

    # VTIMEZONE for Asia/Kolkata (fixed offset, no DST)
    lines.extend([
        'BEGIN:VTIMEZONE',
        f'TZID:{timezone}',
        'BEGIN:STANDARD',
        'DTSTART:19700101T000000',
        'TZOFFSETFROM:+0530',
        'TZOFFSETTO:+0530',
        'TZNAME:IST',
        'END:STANDARD',
        'END:VTIMEZONE',
    ])

    # Generate events
    for (day, hour_key), cell_entries in schedule.items():
        if day not in DAY_INDEX:
            continue

        hour = int(hour_key.split(':')[0])
        minute = int(hour_key.split(':')[1])

        # Calculate first occurrence
        day_offset = DAY_INDEX[day] - start_date.weekday()
        if day_offset < 0:
            day_offset += 7
        first_date = start_date + timedelta(days=day_offset)

        # Deduplicate
        seen = set()
        for e in cell_entries:
            code = e['course_code']
            batches_str = ','.join(sorted(e['batches']))
            dedup_key = (code, batches_str)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            name = e['course_name']
            room = e['room']

            dtstart = first_date.replace(hour=hour, minute=minute)
            dtend = dtstart + timedelta(minutes=50)

            uid_source = f'{abbr}-{code}-{batches_str}-{day}-{hour_key}'
            uid = hashlib.md5(uid_source.encode()).hexdigest()

            summary = f'{code} — {name}' if name else code
            location = room
            description = (
                f'Course: {code} — {name}\\n'
                f'Batch: {batches_str}\\n'
                f'Room: {room}\\n'
                f'Faculty: {full_name}'
            )

            lines.extend([
                'BEGIN:VEVENT',
                f'UID:{uid}@timetable.daiict.ac.in',
                f'DTSTART;TZID={timezone}:{dtstart.strftime("%Y%m%dT%H%M%S")}',
                f'DTEND;TZID={timezone}:{dtend.strftime("%Y%m%dT%H%M%S")}',
                f'RRULE:FREQ=WEEKLY;COUNT={semester_weeks}',
                _ics_fold(f'SUMMARY:{_ics_escape(summary)}'),
                _ics_fold(f'LOCATION:{_ics_escape(location)}'),
                _ics_fold(f'DESCRIPTION:{_ics_escape(description)}'),
                'STATUS:CONFIRMED',
                'END:VEVENT',
            ])

    lines.append('END:VCALENDAR')

    ics_text = '\r\n'.join(lines) + '\r\n'
    return ics_text.encode('utf-8')
