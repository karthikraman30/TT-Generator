import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-fallback-key-change-me')
    # Use SQLite for local dev if DATABASE_URL is not set or is the default placeholder
    _default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'timetable.db')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f'sqlite:///{_default_db}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')

    # Timetable grid constants
    TIME_SLOTS = [
        {'period': 1, 'start': '08:00', 'end': '09:00'},
        {'period': 2, 'start': '09:00', 'end': '10:00'},
        {'period': 3, 'start': '10:00', 'end': '11:00'},
        {'period': 4, 'start': '11:00', 'end': '12:00'},
        {'period': 5, 'start': '12:00', 'end': '13:00'},
    ]
    WORKING_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
