"""
Per-Faculty PDF Timetable Generator
====================================
Generates a clean, branded PDF timetable for a single faculty member.
Uses ReportLab to create a 5-day × 5-period weekly grid.

Usage:
    from faculty_pdf import generate_faculty_pdf
    pdf_bytes = generate_faculty_pdf(db, 'PMJ')
"""

import io
from collections import defaultdict

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

    # Build a lookup: (day, period_hour) → list of entries
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
        fontSize=18, spaceAfter=2 * mm,
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

    # Title
    elements.append(Paragraph(
        f'📅 Faculty Timetable — {faculty_short_name}', title_style))
    elements.append(Paragraph(
        'University Timetable Generator — Individual Faculty Schedule',
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
                grouped = {}
                for e in cell_entries:
                    code = e.get('course_code', '?')
                    room = e.get('room_number', '-') or '-'
                    g_key = (code, room)
                    if g_key not in grouped:
                        grouped[g_key] = []
                    
                    batch = e.get('sub_batch', '')
                    sec = e.get('section', '').strip()
                    sec_clean = sec[4:].strip() if sec.startswith('Sec ') else sec

                    batch_short = batch.replace('BTech Sem-II ', '').replace(
                        'BTech Sem-IV ', '').replace('BTech Sem-VI ', '')
                    batch_str = f"{batch_short}"
                    if sec_clean and sec_clean != 'All':
                        batch_str += f" (Sec {sec_clean})"
                    
                    grouped[g_key].append(batch_str)
                
                lines = []
                for (code, room), batches in grouped.items():
                    batches_joined = ', '.join(batches)
                    lines.append(
                        f'<b>{code}</b> | {room}<br/>'
                        f'{batches_joined}'
                    )
                cell_text = '<br/><br/>'.join(lines)
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
        'Generated by University Timetable Generator — '
        'This is a system-generated document.',
        footer_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
"""
faculty_pdf.py ends here.
"""
