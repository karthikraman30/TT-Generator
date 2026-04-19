"""
Timetable Generator — Web Interface
====================================
A Flask web application to view and query the timetable from PostgreSQL.
Provides interactive views for Master Timetable, Faculty Schedule,
Room Utilization, Constraints, and Violation Log.

Usage:
    python app.py
    # Then open http://localhost:5000 in your browser
"""

import os
import sys
from datetime import time as dt_time

from flask import Flask, render_template_string, request, jsonify

# Import our database manager
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_manager import DBManager

app = Flask(__name__)

# ---------------------------------------------------------------------------
# HTML Template (single-file for simplicity)
# ---------------------------------------------------------------------------
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} — Timetable Generator</title>
    <meta name="description" content="University Timetable Generator - View schedules, room utilization, and constraint enforcement">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0f0f1a;
            --bg-secondary: #1a1a2e;
            --bg-card: #16213e;
            --bg-card-hover: #1a2745;
            --text-primary: #e8e8f0;
            --text-secondary: #8888a8;
            --text-muted: #5a5a7a;
            --accent-blue: #4f8fff;
            --accent-purple: #8b5cf6;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --accent-cyan: #06b6d4;
            --border-color: #2a2a4a;
            --gradient-1: linear-gradient(135deg, #4f8fff, #8b5cf6);
            --gradient-2: linear-gradient(135deg, #10b981, #06b6d4);
            --shadow-glow: 0 0 30px rgba(79, 143, 255, 0.15);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }

        /* ===== NAVIGATION ===== */
        nav {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            padding: 0 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(12px);
        }

        .nav-inner {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            gap: 2rem;
            height: 64px;
        }

        .nav-brand {
            font-weight: 700;
            font-size: 1.1rem;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            white-space: nowrap;
        }

        .nav-links {
            display: flex;
            gap: 0.25rem;
            list-style: none;
            overflow-x: auto;
        }

        .nav-links a {
            text-decoration: none;
            color: var(--text-secondary);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s;
            white-space: nowrap;
        }

        .nav-links a:hover, .nav-links a.active {
            color: var(--text-primary);
            background: rgba(79, 143, 255, 0.1);
        }

        .nav-links a.active {
            background: rgba(79, 143, 255, 0.2);
            color: var(--accent-blue);
        }

        /* ===== MAIN CONTENT ===== */
        main {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        h1 {
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        h1 .icon { margin-right: 0.5rem; }

        .subtitle {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 2rem;
        }

        /* ===== STATS GRID ===== */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
            transition: all 0.3s;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-glow);
            border-color: var(--accent-blue);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .stat-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.25rem;
        }

        /* ===== FILTERS ===== */
        .filters {
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .filter-group label {
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        select, input[type="text"] {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-family: 'Inter', sans-serif;
            min-width: 160px;
            transition: border-color 0.2s;
        }

        select:focus, input[type="text"]:focus {
            outline: none;
            border-color: var(--accent-blue);
        }

        .btn {
            background: var(--gradient-1);
            color: white;
            border: none;
            padding: 0.5rem 1.5rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            align-self: flex-end;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(79, 143, 255, 0.3);
        }

        /* ===== TABLES ===== */
        .table-container {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 2rem;
        }

        .table-header {
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .table-header h2 {
            font-size: 1rem;
            font-weight: 600;
        }

        .table-count {
            font-size: 0.8rem;
            color: var(--text-muted);
            background: var(--bg-secondary);
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
        }

        .table-scroll {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82rem;
        }

        th {
            background: var(--bg-secondary);
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 0.05em;
            padding: 0.75rem 1rem;
            text-align: left;
            white-space: nowrap;
            position: sticky;
            top: 0;
        }

        td {
            padding: 0.65rem 1rem;
            border-top: 1px solid rgba(42, 42, 74, 0.5);
            vertical-align: top;
        }

        tr:hover td {
            background: var(--bg-card-hover);
        }

        /* ===== BADGES ===== */
        .badge {
            display: inline-block;
            padding: 0.15rem 0.6rem;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.03em;
        }

        .badge-hard {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .badge-soft {
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-amber);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .badge-db {
            background: rgba(79, 143, 255, 0.15);
            color: var(--accent-blue);
            border: 1px solid rgba(79, 143, 255, 0.3);
        }

        .badge-app {
            background: rgba(139, 92, 246, 0.15);
            color: var(--accent-purple);
            border: 1px solid rgba(139, 92, 246, 0.3);
        }

        .badge-both {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-active {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
        }

        .badge-inactive {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
        }

        .badge-core {
            background: rgba(6, 182, 212, 0.15);
            color: var(--accent-cyan);
            border: 1px solid rgba(6, 182, 212, 0.3);
        }

        .badge-elective {
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-amber);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .badge-moved {
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-amber);
        }

        /* ===== UTILIZATION BAR ===== */
        .util-bar-bg {
            background: var(--bg-secondary);
            border-radius: 6px;
            height: 8px;
            width: 100px;
            overflow: hidden;
        }

        .util-bar {
            height: 100%;
            border-radius: 6px;
            transition: width 0.5s ease;
        }

        .util-low { background: var(--accent-green); }
        .util-med { background: var(--accent-amber); }
        .util-high { background: var(--accent-red); }

        /* ===== EMPTY STATE ===== */
        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-muted);
        }

        .empty-state .icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }

        /* ===== RESPONSIVE ===== */
        @media (max-width: 768px) {
            nav { padding: 0 1rem; }
            main { padding: 1rem; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .filters { flex-direction: column; }
            .filter-group { width: 100%; }
            select, input[type="text"] { width: 100%; }
        }
    </style>
</head>
<body>
    <nav>
        <div class="nav-inner">
            <div class="nav-brand">📅 Timetable Generator</div>
            <ul class="nav-links">
                <li><a href="/" class="{{ 'active' if active_page == 'dashboard' }}">Dashboard</a></li>
                <li><a href="/timetable" class="{{ 'active' if active_page == 'timetable' }}">Master Timetable</a></li>
                <li><a href="/faculty" class="{{ 'active' if active_page == 'faculty' }}">Faculty Schedule</a></li>
                <li><a href="/rooms" class="{{ 'active' if active_page == 'rooms' }}">Room Utilization</a></li>
                <li><a href="/constraints" class="{{ 'active' if active_page == 'constraints' }}">Constraints</a></li>
                <li><a href="/violations" class="{{ 'active' if active_page == 'violations' }}">Violation Log</a></li>
            </ul>
        </div>
    </nav>
    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Page Templates
# ---------------------------------------------------------------------------

DASHBOARD_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <h1><span class="icon">📊</span>Dashboard</h1>
    <p class="subtitle">University Timetable Generator — Database Overview</p>

    <div class="stats-grid">
        {% for key, val in stats.items() %}
        <div class="stat-card">
            <div class="stat-value">{{ val }}</div>
            <div class="stat-label">{{ key | replace('_', ' ') }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="table-container">
        <div class="table-header">
            <h2>🔒 Active Scheduling Constraints</h2>
            <span class="table-count">{{ constraints | length }} rules</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Scope</th>
                        <th>Enforced By</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for c in constraints %}
                    <tr>
                        <td>{{ c.constraint_id }}</td>
                        <td>{{ c.constraint_name }}</td>
                        <td><span class="badge badge-{{ c.constraint_type | lower }}">{{ c.constraint_type }}</span></td>
                        <td>{{ c.scope }}</td>
                        <td><span class="badge badge-{{ c.enforcement_level | lower }}">{{ c.enforcement_level }}</span></td>
                        <td><span class="badge badge-{{ 'active' if c.is_active else 'inactive' }}">{{ 'ACTIVE' if c.is_active else 'OFF' }}</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    """
)

TIMETABLE_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <h1><span class="icon">📅</span>Master Timetable</h1>
    <p class="subtitle">Complete schedule with batch, faculty, and room details</p>

    <form class="filters" method="GET" action="/timetable">
        <div class="filter-group">
            <label>Day</label>
            <select name="day">
                <option value="">All Days</option>
                {% for d in days %}
                <option value="{{ d }}" {{ 'selected' if d == selected_day }}>{{ d }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="filter-group">
            <label>Batch</label>
            <select name="batch">
                <option value="">All Batches</option>
                {% for b in batches %}
                <option value="{{ b }}" {{ 'selected' if b == selected_batch }}>{{ b }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="filter-group">
            <label>Faculty</label>
            <select name="faculty">
                <option value="">All Faculty</option>
                {% for f in faculties %}
                <option value="{{ f }}" {{ 'selected' if f == selected_faculty }}>{{ f }}</option>
                {% endfor %}
            </select>
        </div>
        <button type="submit" class="btn">Filter</button>
    </form>

    <div class="table-container">
        <div class="table-header">
            <h2>Schedule</h2>
            <span class="table-count">{{ entries | length }} entries</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>Day</th>
                        <th>Time</th>
                        <th>Slot</th>
                        <th>Course Code</th>
                        <th>Course Name</th>
                        <th>Type</th>
                        <th>Faculty</th>
                        <th>Batch</th>
                        <th>Section</th>
                        <th>Room</th>
                        <th>Moved?</th>
                    </tr>
                </thead>
                <tbody>
                    {% if entries %}
                    {% for e in entries %}
                    <tr>
                        <td>{{ e.day_of_week }}</td>
                        <td>{{ e.start_time }}</td>
                        <td>{{ e.slot_group }}</td>
                        <td><strong>{{ e.course_code }}</strong></td>
                        <td>{{ e.course_name }}</td>
                        <td><span class="badge badge-{{ 'core' if 'core' in (e.course_type or '') | lower else 'elective' }}">{{ e.course_type }}</span></td>
                        <td>{{ e.faculty_short_name }}</td>
                        <td>{{ e.sub_batch }}</td>
                        <td>{{ e.section }}</td>
                        <td>{{ e.room_number or '-' }}</td>
                        <td>{% if e.is_moved %}<span class="badge badge-moved">MOVED</span>{% else %}-{% endif %}</td>
                    </tr>
                    {% endfor %}
                    {% else %}
                    <tr><td colspan="11" class="empty-state">
                        <div class="icon">📭</div>
                        <p>No timetable entries found. Run the generator with --use-db first.</p>
                    </td></tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
    """
)

FACULTY_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <h1><span class="icon">👨‍🏫</span>Faculty Schedule</h1>
    <p class="subtitle">Individual teaching schedules for all faculty members</p>

    <form class="filters" method="GET" action="/faculty">
        <div class="filter-group">
            <label>Faculty</label>
            <select name="faculty">
                <option value="">All Faculty</option>
                {% for f in faculties %}
                <option value="{{ f }}" {{ 'selected' if f == selected_faculty }}>{{ f }}</option>
                {% endfor %}
            </select>
        </div>
        <button type="submit" class="btn">Filter</button>
    </form>

    <div class="table-container">
        <div class="table-header">
            <h2>Teaching Schedule</h2>
            <span class="table-count">{{ entries | length }} sessions</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>Faculty</th>
                        <th>Day</th>
                        <th>Time</th>
                        <th>Course Code</th>
                        <th>Course Name</th>
                        <th>Batch</th>
                        <th>Section</th>
                        <th>Room</th>
                    </tr>
                </thead>
                <tbody>
                    {% if entries %}
                    {% for e in entries %}
                    <tr>
                        <td><strong>{{ e.faculty }}</strong></td>
                        <td>{{ e.day_of_week }}</td>
                        <td>{{ e.start_time }}</td>
                        <td>{{ e.course_code }}</td>
                        <td>{{ e.course_name }}</td>
                        <td>{{ e.sub_batch }}</td>
                        <td>{{ e.section }}</td>
                        <td>{{ e.room_number or '-' }}</td>
                    </tr>
                    {% endfor %}
                    {% else %}
                    <tr><td colspan="8" class="empty-state">
                        <div class="icon">📭</div>
                        <p>No schedule data. Run the generator with --use-db first.</p>
                    </td></tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
    """
)

ROOMS_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <h1><span class="icon">🏫</span>Room Utilization</h1>
    <p class="subtitle">Classroom occupancy and utilization rates (out of 25 possible slots/week)</p>

    <div class="table-container">
        <div class="table-header">
            <h2>Utilization Report</h2>
            <span class="table-count">{{ entries | length }} rooms</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>Room</th>
                        <th>Type</th>
                        <th>Capacity</th>
                        <th>Classes/Week</th>
                        <th>Utilization</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {% if entries %}
                    {% for e in entries %}
                    {% set pct = e.utilization_pct | float %}
                    <tr>
                        <td><strong>{{ e.room_number }}</strong></td>
                        <td>{{ e.room_type }}</td>
                        <td>{{ e.capacity }}</td>
                        <td>{{ e.total_classes }} / 25</td>
                        <td>{{ pct }}%</td>
                        <td>
                            <div class="util-bar-bg">
                                <div class="util-bar {{ 'util-low' if pct < 40 else ('util-med' if pct < 75 else 'util-high') }}"
                                     style="width: {{ pct }}%"></div>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                    {% else %}
                    <tr><td colspan="6" class="empty-state">
                        <div class="icon">📭</div>
                        <p>No room data available.</p>
                    </td></tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
    """
)

CONSTRAINTS_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <h1><span class="icon">🔒</span>Scheduling Constraints</h1>
    <p class="subtitle">All scheduling rules — stored as queryable, toggleable database rows</p>

    <div class="table-container">
        <div class="table-header">
            <h2>Constraint Rules</h2>
            <span class="table-count">{{ entries | length }} rules</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Scope</th>
                        <th>Description</th>
                        <th>Enforced By</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for e in entries %}
                    <tr>
                        <td>{{ e.constraint_id }}</td>
                        <td><strong>{{ e.constraint_name }}</strong></td>
                        <td><span class="badge badge-{{ e.constraint_type | lower }}">{{ e.constraint_type }}</span></td>
                        <td>{{ e.scope }}</td>
                        <td style="max-width: 400px; font-size: 0.78rem; color: var(--text-secondary);">{{ e.rule_description }}</td>
                        <td><span class="badge badge-{{ e.enforcement_level | lower }}">{{ e.enforcement_level }}</span></td>
                        <td><span class="badge badge-{{ 'active' if e.is_active else 'inactive' }}">{{ 'ACTIVE' if e.is_active else 'OFF' }}</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    """
)

VIOLATIONS_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <h1><span class="icon">⚠️</span>Constraint Violation Log</h1>
    <p class="subtitle">Audit trail of all violations detected during timetable generation</p>

    <div class="table-container">
        <div class="table-header">
            <h2>Violations</h2>
            <span class="table-count">{{ entries | length }} entries</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Constraint</th>
                        <th>Type</th>
                        <th>Severity</th>
                        <th>Detail</th>
                        <th>Detected At</th>
                    </tr>
                </thead>
                <tbody>
                    {% if entries %}
                    {% for e in entries %}
                    <tr>
                        <td>{{ e.violation_id }}</td>
                        <td>{{ e.constraint_name or 'N/A' }}</td>
                        <td>{{ e.constraint_type or '-' }}</td>
                        <td><span class="badge badge-{{ 'hard' if e.severity == 'ERROR' or e.severity == 'CRITICAL' else 'soft' }}">{{ e.severity }}</span></td>
                        <td style="max-width: 500px; font-size: 0.78rem; color: var(--text-secondary);">{{ e.violation_detail }}</td>
                        <td>{{ e.detected_at }}</td>
                    </tr>
                    {% endfor %}
                    {% else %}
                    <tr><td colspan="6" class="empty-state">
                        <div class="icon">✅</div>
                        <p>No violations detected — all constraints satisfied!</p>
                    </td></tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
    """
)

# ---------------------------------------------------------------------------
# Helper: format time objects for display
# ---------------------------------------------------------------------------
def format_entries(entries):
    """Convert time objects to strings for Jinja rendering."""
    for entry in entries:
        for key, val in entry.items():
            if isinstance(val, dt_time):
                entry[key] = val.strftime('%H:%M')
            elif hasattr(val, 'strftime'):
                entry[key] = val.strftime('%Y-%m-%d %H:%M')
    return entries


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def dashboard():
    db = DBManager(quiet=True)
    try:
        stats = db.get_stats()
        constraints = db.get_constraints()
        constraints = format_entries(constraints)
    finally:
        db.close()

    return render_template_string(
        DASHBOARD_TEMPLATE,
        title='Dashboard',
        active_page='dashboard',
        stats=stats,
        constraints=constraints,
    )


@app.route('/timetable')
def timetable():
    selected_day = request.args.get('day', '')
    selected_batch = request.args.get('batch', '')
    selected_faculty = request.args.get('faculty', '')

    filters = {}
    if selected_day:
        filters['day_of_week'] = selected_day
    if selected_batch:
        filters['sub_batch'] = selected_batch
    if selected_faculty:
        filters['faculty'] = selected_faculty

    db = DBManager(quiet=True)
    try:
        entries = db.get_master_timetable(filters if filters else None)
        entries = format_entries(entries)

        # Get unique values for filter dropdowns
        all_entries = db.get_master_timetable()
        all_entries = format_entries(all_entries)
        batches = sorted(set(e['sub_batch'] for e in all_entries if e.get('sub_batch')))
        faculties = sorted(set(e['faculty_short_name'] for e in all_entries if e.get('faculty_short_name')))
    finally:
        db.close()

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    return render_template_string(
        TIMETABLE_TEMPLATE,
        title='Master Timetable',
        active_page='timetable',
        entries=entries,
        days=days,
        batches=batches,
        faculties=faculties,
        selected_day=selected_day,
        selected_batch=selected_batch,
        selected_faculty=selected_faculty,
    )


@app.route('/faculty')
def faculty_schedule():
    selected_faculty = request.args.get('faculty', '')

    db = DBManager(quiet=True)
    try:
        if selected_faculty:
            entries = db.get_faculty_schedule(selected_faculty)
        else:
            entries = db.get_faculty_schedule()
        entries = format_entries(entries)

        all_entries = db.get_faculty_schedule()
        faculties = sorted(set(e['faculty'] for e in all_entries if e.get('faculty')))
    finally:
        db.close()

    return render_template_string(
        FACULTY_TEMPLATE,
        title='Faculty Schedule',
        active_page='faculty',
        entries=entries,
        faculties=faculties,
        selected_faculty=selected_faculty,
    )


@app.route('/rooms')
def rooms():
    db = DBManager(quiet=True)
    try:
        entries = db.get_room_utilization()
        entries = format_entries(entries)
    finally:
        db.close()

    return render_template_string(
        ROOMS_TEMPLATE,
        title='Room Utilization',
        active_page='rooms',
        entries=entries,
    )


@app.route('/constraints')
def constraints():
    db = DBManager(quiet=True)
    try:
        entries = db.get_constraints()
        entries = format_entries(entries)
    finally:
        db.close()

    return render_template_string(
        CONSTRAINTS_TEMPLATE,
        title='Constraints',
        active_page='constraints',
        entries=entries,
    )


@app.route('/violations')
def violations():
    db = DBManager(quiet=True)
    try:
        entries = db.get_violations()
        entries = format_entries(entries)
    finally:
        db.close()

    return render_template_string(
        VIOLATIONS_TEMPLATE,
        title='Violation Log',
        active_page='violations',
        entries=entries,
    )


# ---------------------------------------------------------------------------
# API Endpoints (for programmatic access)
# ---------------------------------------------------------------------------

@app.route('/api/stats')
def api_stats():
    db = DBManager(quiet=True)
    try:
        return jsonify(db.get_stats())
    finally:
        db.close()


@app.route('/api/timetable')
def api_timetable():
    filters = {}
    for key in ['day_of_week', 'sub_batch', 'faculty', 'room']:
        val = request.args.get(key)
        if val:
            filters[key] = val

    db = DBManager(quiet=True)
    try:
        entries = db.get_master_timetable(filters if filters else None)
        entries = format_entries(entries)
        return jsonify(entries)
    finally:
        db.close()


@app.route('/api/constraints')
def api_constraints():
    db = DBManager(quiet=True)
    try:
        entries = db.get_constraints()
        entries = format_entries(entries)
        return jsonify(entries)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("  Timetable Generator — Web Interface")
    print("  Open http://localhost:5001 in your browser")
    print("=" * 60)
    app.run(debug=True, port=5001)
