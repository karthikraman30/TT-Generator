"""
Per-Faculty PDF & ICS Timetable Generator
==========================================
Generates:
  1. A clean, branded PDF timetable for a single faculty member
  2. An RFC 5545 compliant ICS calendar file for Google Calendar / Outlook / iCal

Key improvements over the original:
  - Uses full professor name (from faculty_name_map or faculty.name)
  - Shows course name + code + batch + room in each cell
  - Cleans verbose batch labels (removes "BTech Sem-II" prefix)
  - Deduplicates repeated entries per cell
  - ICS generates recurring weekly events for the full semester

Usage:
    from faculty_pdf import generate_faculty_pdf, generate_faculty_ics
    pdf_bytes = generate_faculty_pdf(db, 'PMJ')
    ics_bytes = generate_faculty_ics(db, 'PMJ', semester_start='2026-01-06')
"""

import io
import re
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer)


DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
PERIODS = ['08:00', '09:00', '10:00', '11:00', '12:00']
PERIOD_LABELS = [
    '8:00 – 8:50',
    '9:00 – 9:50',
    '10:00 – 10:50',
    '11:00 – 11:50',
    '12:00 – 12:50',
]

# Day name -> Python weekday index (Monday=0)
DAY_INDEX = {
    'Monday': 0, 'Tuesday': 1, 'Wednesday': 2,
    'Thursday': 3, 'Friday': 4,
}


def _get_full_name(db, faculty_short_name):
    """Resolve short name to full academic name via DB lookups."""
    try:
        # Try faculty_name_map first (most reliable)
        db.cur.execute(
            "SELECT full_name FROM faculty_name_map WHERE short_name = %s",
            (faculty_short_name,)
        )
        row = db.cur.fetchone()
        if row and row[0]:
            return row[0]

        # Fall back to faculty.name
        db.cur.execute(
            "SELECT name FROM faculty WHERE short_name = %s",
            (faculty_short_name,)
        )
        row = db.cur.fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        pass

    # Final fallback: use short name
    return faculty_short_name


def _clean_batch(sub_batch):
    """Clean verbose batch labels for PDF display.

    'BTech Sem-II (ICT + CS)' -> 'ICT+CS'
    'BTech Sem-IV (MnC)' -> 'MnC'
    'MTech Sem-II (ICT-ML)' -> 'ICT-ML'
    """
    # Extract the program name from parentheses
    match = re.search(r'\(([^)]+)\)', sub_batch)
    if match:
        return match.group(1).strip()
    # Remove common prefixes
    cleaned = re.sub(r'BTech\s+Sem-\w+\s*', '', sub_batch).strip()
    cleaned = re.sub(r'MTech\s+Sem-\w+\s*', '', cleaned).strip()
    return cleaned or sub_batch


def _build_schedule(entries):
    """Build a lookup: (day, period_hour) -> list of entries."""
    schedule = defaultdict(list)
    for e in entries:
        day = e.get('day_of_week', '')
        start = e.get('start_time', '')
        # Normalize time: could be a time object or string
        if hasattr(start, 'strftime'):
            hour_key = start.strftime('%H:%M')
        else:
            hour_key = str(start).strip()[:5]
        schedule[(day, hour_key)].append(e)
    return schedule


# ============================================================================
# PDF Generator
# ============================================================================

def generate_faculty_pdf(db, faculty_short_name):
    """
    Generate a PDF timetable for one faculty member.

    Args:
        db: A connected DBManager instance (with an open cursor).
        faculty_short_name: The faculty's short_name (e.g., 'PMJ').

    Returns:
        bytes — The PDF content as a byte string (ready to send as a download).
    """
    # Query faculty schedule from the DB view
    entries = db.get_faculty_schedule(faculty_short_name)
    full_name = _get_full_name(db, faculty_short_name)
    schedule = _build_schedule(entries)

    # --- Build PDF ---
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )

    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'FacTitle', parent=styles['Title'],
        fontSize=16, spaceAfter=2 * mm,
        textColor=colors.HexColor('#1a1a2e'),
    )
    subtitle_style = ParagraphStyle(
        'FacSubtitle', parent=styles['Normal'],
        fontSize=10, spaceAfter=6 * mm,
        textColor=colors.HexColor('#555555'),
    )
    cell_style = ParagraphStyle(
        'CellStyle', parent=styles['Normal'],
        fontSize=7, leading=9,
    )
    header_cell_style = ParagraphStyle(
        'HeaderCell', parent=styles['Normal'],
        fontSize=8, leading=10,
        textColor=colors.white,
        alignment=1,  # center
    )

    def make_para(text, style=cell_style):
        return Paragraph(str(text), style)

    # Title — show full name with short code
    if full_name != faculty_short_name:
        title_text = f'📅 {full_name} ({faculty_short_name})'
    else:
        title_text = f'📅 Faculty Timetable — {faculty_short_name}'

    elements.append(Paragraph(title_text, title_style))
    elements.append(Paragraph(
        'DA-IICT Timetable Generator — Individual Faculty Schedule',
        subtitle_style))
    elements.append(Spacer(1, 4 * mm))

    # Table header
    header = ['Period']
    for day in DAYS:
        header.append(day)

    table_data = [[make_para(h, header_cell_style) for h in header]]

    # Table body: one row per period
    for p_idx, period_label in enumerate(PERIOD_LABELS):
        row = [make_para(period_label)]
        hour_key = PERIODS[p_idx]

        for day in DAYS:
            cell_entries = schedule.get((day, hour_key), [])
            if cell_entries:
                # Deduplicate by (course_code, sub_batch, section)
                seen = set()
                lines = []
                for e in cell_entries:
                    code = e.get('course_code', '?')
                    batch = _clean_batch(e.get('sub_batch', ''))
                    sec = e.get('section', '')
                    dedup_key = (code, batch, sec)
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    name = e.get('course_name', '')
                    room = e.get('room_number', '-') or '-'

                    # Truncate long course names for PDF cells
                    if len(name) > 25:
                        name = name[:23] + '…'

                    sec_label = f' [{sec}]' if sec and sec != 'All' else ''
                    lines.append(
                        f'<b>{code}</b><br/>'
                        f'<font size="6">{name}</font><br/>'
                        f'📍 {room} | {batch}{sec_label}'
                    )
                cell_text = '<br/><br/>'.join(lines) if len(lines) > 1 else lines[0]
            else:
                cell_text = '<font color="#aaaaaa">—</font>'
            row.append(make_para(cell_text))

        table_data.append(row)

    # Column widths
    col_widths = [28 * mm] + [45 * mm] * 5

    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Colors
    hdr_bg = colors.HexColor('#1a1a2e')
    grid_color = colors.HexColor('#cccccc')
    alt_row_bg = colors.HexColor('#f4f6f9')

    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), hdr_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, grid_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, alt_row_bg]),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]

    # Thicker vertical separators between days
    for d_idx in range(5):
        col = d_idx + 1
        style_cmds.append(
            ('LINEAFTER', (col, 0), (col, -1), 1.2, colors.HexColor('#888888'))
        )

    t.setStyle(TableStyle(style_cmds))
    elements.append(t)

    # Footer
    elements.append(Spacer(1, 8 * mm))
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#888888'),
    )
    elements.append(Paragraph(
        'Generated by DA-IICT Timetable Generator — '
        'This is a system-generated document.',
        footer_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ============================================================================
# ICS (iCalendar) Generator
# ============================================================================

def _ics_fold(line):
    """Fold a line per RFC 5545 (max 75 octets, continuation with space)."""
    encoded = line.encode('utf-8')
    if len(encoded) <= 75:
        return line
    result = []
    while len(encoded) > 75:
        # Find a safe split point (don't split multi-byte chars)
        cut = 75 if not result else 74  # subsequent lines have leading space
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


def generate_faculty_ics(db, faculty_short_name,
                         semester_start='2026-01-06',
                         semester_weeks=16,
                         timezone='Asia/Kolkata'):
    """
    Generate an ICS calendar file for one faculty member.

    Args:
        db: A connected DBManager instance.
        faculty_short_name: The faculty's short_name (e.g., 'PMJ').
        semester_start: First Monday of the semester (YYYY-MM-DD).
        semester_weeks: Number of weeks to generate events for.
        timezone: IANA timezone name (default: Asia/Kolkata).

    Returns:
        bytes — The ICS content as a byte string (UTF-8).
    """
    entries = db.get_faculty_schedule(faculty_short_name)
    full_name = _get_full_name(db, faculty_short_name)
    schedule = _build_schedule(entries)

    start_date = datetime.strptime(semester_start, '%Y-%m-%d')

    # Build ICS lines
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

        # Parse hour
        hour = int(hour_key.split(':')[0])
        minute = int(hour_key.split(':')[1])

        # Calculate the first occurrence of this day in the semester
        day_offset = DAY_INDEX[day] - start_date.weekday()
        if day_offset < 0:
            day_offset += 7
        first_date = start_date + timedelta(days=day_offset)

        # Deduplicate entries
        seen = set()
        for e in cell_entries:
            code = e.get('course_code', '?')
            batch = _clean_batch(e.get('sub_batch', ''))
            sec = e.get('section', '')
            dedup_key = (code, batch, sec)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            name = e.get('course_name', '')
            room = e.get('room_number', '') or ''

            # Event times
            dtstart = first_date.replace(hour=hour, minute=minute)
            dtend = dtstart + timedelta(minutes=50)

            # Unique ID for this event
            uid_source = f'{faculty_short_name}-{code}-{batch}-{sec}-{day}-{hour_key}'
            uid = hashlib.md5(uid_source.encode()).hexdigest()

            summary = f'{code} — {name}' if name else code
            location = room
            sec_label = f' [{sec}]' if sec and sec != 'All' else ''
            description = f'Course: {code} — {name}\\nBatch: {batch}{sec_label}\\nRoom: {room}\\nFaculty: {full_name}'

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
