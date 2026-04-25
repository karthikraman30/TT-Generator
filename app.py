"""
Timetable Generator - Main Flask Application
"""

import os
from datetime import time
from flask import Flask
from config import Config
from models import db, TimeSlot
from services.scheduler import SlotTimeMapping  # ensures table is created


def create_app():
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize database
    db.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.faculty import faculty_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(faculty_bp, url_prefix='/faculty')

    # Global template context: active_semester available on every page
    @app.context_processor
    def inject_active_semester():
        from models import Semester
        return {'active_semester': Semester.query.filter_by(is_active=True).first()}

    # Create tables & seed time slots on first run
    with app.app_context():
        db.create_all()
        _seed_time_slots()

    return app


def _seed_time_slots():
    """Seed the 5×5 time grid if empty (Mon-Fri, 08:00-13:00)."""
    if TimeSlot.query.first() is not None:
        return

    days = Config.WORKING_DAYS
    periods = Config.TIME_SLOTS

    for day in days:
        for p in periods:
            h_start, m_start = map(int, p['start'].split(':'))
            h_end, m_end = map(int, p['end'].split(':'))
            ts = TimeSlot(
                day=day,
                period=p['period'],
                start_time=time(h_start, m_start),
                end_time=time(h_end, m_end)
            )
            db.session.add(ts)

    db.session.commit()
    print(f"[SEED] Inserted {len(days) * len(periods)} time slots.")


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
