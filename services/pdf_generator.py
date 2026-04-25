import os
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from models import db, TimetableEntry, Semester, Faculty, Course

def _get_periods():
    return [
        {'num': 1, 'label': '08:00\n09:00'},
        {'num': 2, 'label': '09:00\n10:00'},
        {'num': 3, 'label': '10:00\n11:00'},
        {'num': 4, 'label': '11:00\n12:00'},
        {'num': 5, 'label': '12:00\n13:00'}
    ]

def _get_days():
    return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

def _create_timetable_grid(entries, title_text):
    """Generate a Platypus Table for the timetable grid."""
    styles = getSampleStyleSheet()
    
    # Custom styles
    header_style = ParagraphStyle(
        'HeaderStyle', 
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        alignment=1, # Center
        textColor=colors.whitesmoke
    )
    
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        alignment=1, # Center
        leading=10
    )

    days = _get_days()
    periods = _get_periods()

    # Build the table data
    data = [['Time'] + days]

    for p in periods:
        row = [Paragraph(f"<b>{p['label']}</b>", cell_style)]
        for day in days:
            # Find entries for this day and period
            cell_entries = [e for e in entries if e.time_slot and e.time_slot.day == day and e.time_slot.period == p['num']]
            
            if not cell_entries:
                row.append(Paragraph("-", cell_style))
                continue
                
            # Build cell content
            cell_text = []
            for e in cell_entries:
                c_code = e.course.code if e.course else '?'
                f_abbr = e.faculty.abbreviation if e.faculty else '?'
                r_name = e.room.name if e.room else '?'
                
                # Format: IT301<br/>(PMJ) [CEP102]
                cell_text.append(f"<b>{c_code}</b><br/>({f_abbr}) [{r_name}]")
                
            row.append(Paragraph("<br/><br/>".join(cell_text), cell_style))
            
        data.append(row)

    # Calculate column widths
    col_widths = [1.0 * inch] + [(A4[1] - 1.5 * inch) / 5.0] * 5  # A4[1] is landscape width

    table = Table(data, colWidths=col_widths)
    
    # Style the table
    t_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#ecf0f1')), # Time column background
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
    ])
    table.setStyle(t_style)
    
    return table

def generate_master_pdf(semester_id):
    """Generate a master timetable PDF."""
    semester = Semester.query.get(semester_id)
    if not semester:
        return None

    entries = TimetableEntry.query.filter_by(semester_id=semester_id).all()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=1,
        spaceAfter=20
    )
    
    elements = []
    
    # Title
    elements.append(Paragraph(f"Master Timetable — {semester.name}", title_style))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # Table
    table = _create_timetable_grid(entries, "Master Timetable")
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_faculty_pdf(semester_id, faculty_id):
    """Generate a timetable PDF for a specific faculty member."""
    semester = Semester.query.get(semester_id)
    faculty = Faculty.query.get(faculty_id)
    
    if not semester or not faculty:
        return None

    entries = TimetableEntry.query.filter_by(semester_id=semester_id, faculty_id=faculty_id).all()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=1,
        spaceAfter=20
    )
    
    elements = []
    
    # Title
    elements.append(Paragraph(f"Faculty Timetable — {faculty.full_name} ({faculty.abbreviation})", title_style))
    elements.append(Paragraph(f"Semester: {semester.name} | Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # Table
    table = _create_timetable_grid(entries, "Faculty Timetable")
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
