"""
Input validation utilities for the Timetable Generator.
Provides comprehensive validation for all user inputs.
"""

import re
from datetime import datetime


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class Validators:
    """Collection of validation methods for different input types."""
    
    # ─── TEXT VALIDATORS ─────────────────────────────────────
    
    @staticmethod
    def validate_name(name, field_name="Name", min_length=2, max_length=200):
        """
        Validate a person's name or entity name.
        Rules:
        - Not empty
        - Min/max length
        - No special characters like . , ; : alone
        - Must contain at least one letter
        - Can contain spaces, hyphens, apostrophes
        """
        if not name or not name.strip():
            raise ValidationError(f"{field_name} cannot be empty.")
        
        name = name.strip()
        
        if len(name) < min_length:
            raise ValidationError(f"{field_name} must be at least {min_length} characters long.")
        
        if len(name) > max_length:
            raise ValidationError(f"{field_name} cannot exceed {max_length} characters.")
        
        # Check for invalid single-character names
        if name in ['.', ',', ';', ':', '-', '_', '!', '@', '#', '$', '%', '^', '&', '*']:
            raise ValidationError(f"{field_name} cannot be just a special character.")
        
        # Must contain at least one letter
        if not re.search(r'[a-zA-Z]', name):
            raise ValidationError(f"{field_name} must contain at least one letter.")
        
        # Check for excessive special characters (more than 30% of the string)
        special_count = len(re.findall(r'[^a-zA-Z0-9\s\-\']', name))
        if special_count > len(name) * 0.3:
            raise ValidationError(f"{field_name} contains too many special characters.")
        
        return name
    
    @staticmethod
    def validate_abbreviation(abbr, field_name="Abbreviation", min_length=1, max_length=50):
        """
        Validate an abbreviation (e.g., faculty abbreviation, course code).
        Rules:
        - Not empty
        - Min/max length
        - Alphanumeric, hyphens, underscores only
        - No spaces
        """
        if not abbr or not abbr.strip():
            raise ValidationError(f"{field_name} cannot be empty.")
        
        abbr = abbr.strip().upper()
        
        if len(abbr) < min_length:
            raise ValidationError(f"{field_name} must be at least {min_length} character(s) long.")
        
        if len(abbr) > max_length:
            raise ValidationError(f"{field_name} cannot exceed {max_length} characters.")
        
        # Only alphanumeric, hyphens, underscores
        if not re.match(r'^[A-Z0-9\-_]+$', abbr):
            raise ValidationError(f"{field_name} can only contain letters, numbers, hyphens, and underscores (no spaces).")
        
        # Cannot be just special characters
        if re.match(r'^[\-_]+$', abbr):
            raise ValidationError(f"{field_name} cannot be just hyphens or underscores.")
        
        return abbr
    
    @staticmethod
    def validate_email(email, field_name="Email", required=True):
        """
        Validate an email address.
        Rules:
        - Valid email format
        - Not empty (if required)
        """
        if not email or not email.strip():
            if required:
                raise ValidationError(f"{field_name} is required.")
            return None
        
        email = email.strip().lower()
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError(f"{field_name} must be a valid email address (e.g., name@domain.com).")
        
        if len(email) > 200:
            raise ValidationError(f"{field_name} is too long (max 200 characters).")
        
        return email
    
    # ─── NUMBER VALIDATORS ───────────────────────────────────
    
    @staticmethod
    def validate_integer(value, field_name="Value", min_val=None, max_val=None, required=True):
        """
        Validate an integer value.
        Rules:
        - Must be a valid integer
        - Optional min/max bounds
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                raise ValidationError(f"{field_name} is required.")
            return None
        
        try:
            if isinstance(value, str):
                value = int(value.strip())
            else:
                value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid number.")
        
        if min_val is not None and value < min_val:
            raise ValidationError(f"{field_name} must be at least {min_val}.")
        
        if max_val is not None and value > max_val:
            raise ValidationError(f"{field_name} cannot exceed {max_val}.")
        
        return value
    
    @staticmethod
    def validate_positive_integer(value, field_name="Value", allow_zero=False, required=True):
        """Validate a positive integer (optionally allowing zero)."""
        min_val = 0 if allow_zero else 1
        return Validators.validate_integer(value, field_name, min_val=min_val, required=required)
    
    @staticmethod
    def validate_capacity(value, field_name="Capacity"):
        """Validate room capacity or student count."""
        return Validators.validate_integer(value, field_name, min_val=1, max_val=10000)
    
    @staticmethod
    def validate_credits(value, field_name="Credits"):
        """
        Validate course credits.
        Rules:
        - Must be a positive number
        - Can be decimal (e.g., 3.5, 4.0)
        - Max 20 credits
        """
        if not value or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"{field_name} is required.")
        
        try:
            if isinstance(value, str):
                value = float(value.strip())
            else:
                value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid number.")
        
        if value < 0:
            raise ValidationError(f"{field_name} cannot be negative.")
        
        if value > 20:
            raise ValidationError(f"{field_name} cannot exceed 20.")
        
        return value
    
    # ─── DATE VALIDATORS ─────────────────────────────────────
    
    @staticmethod
    def validate_date(date_str, field_name="Date", date_format='%Y-%m-%d'):
        """
        Validate a date string.
        Rules:
        - Must be in YYYY-MM-DD format
        - Must be a valid date
        """
        if not date_str or not date_str.strip():
            raise ValidationError(f"{field_name} is required.")
        
        date_str = date_str.strip()
        
        try:
            date_obj = datetime.strptime(date_str, date_format).date()
        except ValueError:
            raise ValidationError(f"{field_name} must be in YYYY-MM-DD format (e.g., 2025-01-15).")
        
        # Check for reasonable year range (1900-2100)
        if date_obj.year < 1900 or date_obj.year > 2100:
            raise ValidationError(f"{field_name} year must be between 1900 and 2100.")
        
        return date_obj
    
    @staticmethod
    def validate_date_range(start_date_str, end_date_str, start_field="Start date", end_field="End date"):
        """
        Validate a date range.
        Rules:
        - Both dates must be valid
        - End date must be after start date
        """
        start_date = Validators.validate_date(start_date_str, start_field)
        end_date = Validators.validate_date(end_date_str, end_field)
        
        if end_date <= start_date:
            raise ValidationError(f"{end_field} must be after {start_field}.")
        
        return start_date, end_date
    
    @staticmethod
    def validate_semester_year(year, field_name="Year"):
        """
        Validate a semester year.
        Rules:
        - Must be a 4-digit year
        - Must be within reasonable range (current year - 5 to current year + 10)
        """
        current_year = datetime.now().year
        
        year = Validators.validate_integer(year, field_name, min_val=current_year - 5, max_val=current_year + 10)
        
        return year
    
    # ─── CHOICE VALIDATORS ───────────────────────────────────
    
    @staticmethod
    def validate_choice(value, choices, field_name="Value", required=True):
        """
        Validate that a value is in a list of allowed choices.
        """
        if not value or not value.strip():
            if required:
                raise ValidationError(f"{field_name} is required.")
            return None
        
        value = value.strip()
        
        if value not in choices:
            choices_str = ', '.join(choices)
            raise ValidationError(f"{field_name} must be one of: {choices_str}")
        
        return value
    
    @staticmethod
    def validate_role(role):
        """Validate user role."""
        return Validators.validate_choice(role, ['admin', 'faculty'], "Role")
    
    @staticmethod
    def validate_degree_type(degree_type):
        """Validate degree type."""
        return Validators.validate_choice(degree_type, ['BTech', 'MTech', 'MSc', 'PhD', 'Diploma'], "Degree type")
    
    @staticmethod
    def validate_room_type(room_type):
        """Validate room type."""
        return Validators.validate_choice(room_type, ['lecture', 'lab', 'tutorial', 'seminar', 'auditorium'], "Room type")
    
    @staticmethod
    def validate_course_type(course_type):
        """Validate course type."""
        return Validators.validate_choice(course_type, ['Core', 'Elective', 'Lab', 'Project', 'Seminar'], "Course type")
    
    # ─── LTPC VALIDATORS ─────────────────────────────────────
    
    @staticmethod
    def validate_ltpc(L, T, P, C, course_name="Course"):
        """
        Validate L-T-P-C values for a course.
        Rules:
        - All must be non-negative integers
        - L (lectures) max 5 per week
        - T (tutorials) max 3 per week
        - P (practicals) max 6 per week
        - C (credits) must be positive
        """
        L = Validators.validate_integer(L, "Lectures per week", min_val=0, max_val=5)
        T = Validators.validate_integer(T, "Tutorials per week", min_val=0, max_val=3)
        P = Validators.validate_integer(P, "Practicals per week", min_val=0, max_val=6)
        C = Validators.validate_credits(C, "Credits")
        
        # At least one of L, T, P must be > 0
        if L == 0 and T == 0 and P == 0:
            raise ValidationError(f"{course_name} must have at least one lecture, tutorial, or practical session per week.")
        
        return L, T, P, C
    
    # ─── BATCH VALIDATORS ────────────────────────────────────
    
    @staticmethod
    def validate_semester_number(sem_num, field_name="Semester number"):
        """
        Validate semester number.
        Rules:
        - Must be between 1 and 10
        """
        return Validators.validate_integer(sem_num, field_name, min_val=1, max_val=10)
    
    @staticmethod
    def validate_student_count(count, field_name="Student count"):
        """
        Validate student count.
        Rules:
        - Must be between 0 and 500
        """
        return Validators.validate_integer(count, field_name, min_val=0, max_val=500)


# ─── HELPER FUNCTIONS ────────────────────────────────────────

def safe_strip(value):
    """Safely strip whitespace from a value, returning None if empty."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def validate_form_data(form_data, validators_dict):
    """
    Validate multiple form fields at once.
    
    Args:
        form_data: dict of field_name -> value
        validators_dict: dict of field_name -> (validator_func, *args)
    
    Returns:
        dict of validated values
    
    Raises:
        ValidationError: if any validation fails
    
    Example:
        validated = validate_form_data(
            {'name': 'John Doe', 'age': '25'},
            {
                'name': (Validators.validate_name, 'Full name'),
                'age': (Validators.validate_positive_integer, 'Age')
            }
        )
    """
    validated = {}
    
    for field_name, (validator_func, *args) in validators_dict.items():
        value = form_data.get(field_name)
        try:
            validated[field_name] = validator_func(value, *args)
        except ValidationError as e:
            # Re-raise with field context
            raise ValidationError(str(e))
    
    return validated
