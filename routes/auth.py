"""
Authentication routes.
Handles login/logout and Firebase token verification.
"""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

auth_bp = Blueprint('auth', __name__)


# ─── DECORATORS ──────────────────────────────────────────────
def login_required(f):
    """Require user to be logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Require user to have admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        if session['user'].get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('faculty.dashboard'))
        return f(*args, **kwargs)
    return decorated


# ─── ROUTES ──────────────────────────────────────────────────
@auth_bp.route('/')
def index():
    """Root redirect."""
    if 'user' in session:
        if session['user'].get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('faculty.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page. Firebase handles auth on the client side."""
    if 'user' in session:
        return redirect(url_for('auth.index'))
    return render_template('login.html')


@auth_bp.route('/auth/verify-token', methods=['POST'])
def verify_token():
    """
    Verify Firebase ID token sent from the client.
    On success, create a server-side session.
    """
    from models import Faculty

    data = request.get_json()
    id_token = data.get('idToken')
    if not id_token:
        return jsonify({'error': 'No token provided'}), 400

    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth

        # Initialize Firebase if not already done
        if not firebase_admin._apps:
            from config import Config
            cred = firebase_admin.credentials.Certificate(Config.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)

        # Verify the token
        decoded_token = firebase_auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')

        # Look up faculty in our DB
        faculty = Faculty.query.filter_by(firebase_uid=uid).first()
        if not faculty:
            # Try by email
            faculty = Faculty.query.filter_by(email=email).first()
            if faculty:
                # Link Firebase UID
                faculty.firebase_uid = uid
                from models import db
                db.session.commit()

        if not faculty:
            return jsonify({'error': 'User not registered in the system. Contact admin.'}), 403

        # Set session
        session['user'] = {
            'id': faculty.id,
            'name': faculty.full_name,
            'abbreviation': faculty.abbreviation,
            'email': faculty.email,
            'role': faculty.role,
            'firebase_uid': uid
        }

        redirect_url = url_for('admin.dashboard') if faculty.role == 'admin' else url_for('faculty.dashboard')
        return jsonify({'success': True, 'redirect': redirect_url})

    except Exception as e:
        return jsonify({'error': f'Token verification failed: {str(e)}'}), 401


@auth_bp.route('/auth/dev-login', methods=['POST'])
def dev_login():
    """
    Development-only login bypass (no Firebase needed).
    Remove this route in production!
    """
    from models import Faculty

    data = request.get_json(silent=True) or request.form
    abbreviation = data.get('abbreviation', '').strip().upper()

    if not abbreviation:
        flash('Please enter a faculty abbreviation.', 'error')
        return redirect(url_for('auth.login'))

    faculty = Faculty.query.filter_by(abbreviation=abbreviation).first()
    if not faculty:
        if request.is_json:
            return jsonify({'error': 'Faculty not found'}), 404
        flash('Faculty not found. Check your abbreviation.', 'error')
        return redirect(url_for('auth.login'))

    session['user'] = {
        'id': faculty.id,
        'name': faculty.full_name,
        'abbreviation': faculty.abbreviation,
        'email': faculty.email,
        'role': faculty.role,
    }

    redirect_url = url_for('admin.dashboard') if faculty.role == 'admin' else url_for('faculty.dashboard')

    if request.is_json:
        return jsonify({'success': True, 'redirect': redirect_url})
    return redirect(redirect_url)


@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to login."""
    session.clear()
    return redirect(url_for('auth.login'))
