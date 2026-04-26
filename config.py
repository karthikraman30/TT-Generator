import os
from dotenv import load_dotenv

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, '.env'))


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
    FIREBASE_API_KEY = os.getenv('FIREBASE_API_KEY')
    FIREBASE_AUTH_DOMAIN = os.getenv('FIREBASE_AUTH_DOMAIN')
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
    FIREBASE_STORAGE_BUCKET = os.getenv('FIREBASE_STORAGE_BUCKET')
    FIREBASE_MESSAGING_SENDER_ID = os.getenv('FIREBASE_MESSAGING_SENDER_ID')
    FIREBASE_APP_ID = os.getenv('FIREBASE_APP_ID')
    FIREBASE_MEASUREMENT_ID = os.getenv('FIREBASE_MEASUREMENT_ID')

    FIREBASE_WEB_CONFIG = {
        'apiKey': FIREBASE_API_KEY,
        'authDomain': FIREBASE_AUTH_DOMAIN,
        'projectId': FIREBASE_PROJECT_ID,
        'storageBucket': FIREBASE_STORAGE_BUCKET,
        'messagingSenderId': FIREBASE_MESSAGING_SENDER_ID,
        'appId': FIREBASE_APP_ID,
        'measurementId': FIREBASE_MEASUREMENT_ID,
    }

    # Timetable grid constants
    TIME_SLOTS = [
        {'period': 1, 'start': '08:00', 'end': '09:00'},
        {'period': 2, 'start': '09:00', 'end': '10:00'},
        {'period': 3, 'start': '10:00', 'end': '11:00'},
        {'period': 4, 'start': '11:00', 'end': '12:00'},
        {'period': 5, 'start': '12:00', 'end': '13:00'},
    ]
    WORKING_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
