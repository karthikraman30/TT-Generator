# Input Validation Rules

This document describes all input validation rules enforced by the Timetable Generator application.

## 📋 Table of Contents

- [General Rules](#general-rules)
- [Semester Management](#semester-management)
- [Program Management](#program-management)
- [Faculty Management](#faculty-management)
- [Room Management](#room-management)
- [Course Management](#course-management)
- [Batch Management](#batch-management)

---

## General Rules

### Text Fields
- **Cannot be empty** (unless marked optional)
- **Cannot be just special characters** like `.`, `,`, `;`, `:`, `-`, etc.
- **Must contain at least one letter** (for names)
- **Excessive special characters rejected** (more than 30% of string)

### Numbers
- **Must be valid integers or decimals** (no text)
- **Range validation** applied where appropriate
- **Negative numbers rejected** for counts and capacities

### Dates
- **Format:** YYYY-MM-DD (e.g., 2025-01-15)
- **Year range:** 1900-2100
- **End date must be after start date** for date ranges

---

## Semester Management

### Semester Name
- **Min length:** 3 characters
- **Max length:** 100 characters
- **Must contain letters**
- **Cannot be just special characters**
- **Examples:**
  - ✅ "Winter 2025-26"
  - ✅ "Summer Semester 2025"
  - ❌ "..." (just special characters)
  - ❌ "WS" (too short)

### Start Date / End Date
- **Format:** YYYY-MM-DD
- **Year range:** Current year - 5 to current year + 10
- **End date must be after start date**
- **Examples:**
  - ✅ Start: 2025-01-15, End: 2025-05-30
  - ❌ Start: 2025-05-30, End: 2025-01-15 (reversed)
  - ❌ Start: 2025-13-01 (invalid month)

---

## Program Management

### Program Name
- **Min length:** 3 characters
- **Max length:** 100 characters
- **Must contain letters**
- **Examples:**
  - ✅ "Bachelor of Technology"
  - ✅ "BTech Computer Science"
  - ❌ "." (just special character)
  - ❌ "BT" (too short)

### Program Code
- **Min length:** 2 characters
- **Max length:** 30 characters
- **Allowed characters:** Letters, numbers, hyphens, underscores
- **No spaces allowed**
- **Automatically converted to UPPERCASE**
- **Cannot be just hyphens or underscores**
- **Examples:**
  - ✅ "BTECH_CS" → BTECH_CS
  - ✅ "MTech-ICT" → MTECH-ICT
  - ❌ "B" (too short)
  - ❌ "---" (just special characters)
  - ❌ "B Tech CS" (contains spaces)

### Degree Type
- **Must be one of:** BTech, MTech, MSc, PhD, Diploma
- **Examples:**
  - ✅ "BTech"
  - ✅ "MTech"
  - ❌ "Bachelor" (not in allowed list)

---

## Faculty Management

### Full Name
- **Min length:** 2 characters
- **Max length:** 200 characters
- **Must contain at least one letter**
- **Cannot be just special characters**
- **Can contain:** Letters, spaces, hyphens, apostrophes
- **Examples:**
  - ✅ "Dr. John Smith"
  - ✅ "Mary O'Brien-Jones"
  - ❌ "." (just special character)
  - ❌ "J" (too short)
  - ❌ "123456" (no letters)

### Abbreviation
- **Min length:** 1 character
- **Max length:** 50 characters
- **Allowed characters:** Letters, numbers, hyphens, underscores
- **No spaces allowed**
- **Automatically converted to UPPERCASE**
- **Cannot be just hyphens or underscores**
- **Examples:**
  - ✅ "PMJ" → PMJ
  - ✅ "DR-SMITH" → DR-SMITH
  - ✅ "JD123" → JD123
  - ❌ "P M J" (contains spaces)
  - ❌ "---" (just special characters)

### Email
- **Required for creating login accounts**
- **Must be valid email format:** name@domain.com
- **Max length:** 200 characters
- **Automatically converted to lowercase**
- **Must be unique** (no duplicate emails)
- **Examples:**
  - ✅ "john.smith@dau.ac.in"
  - ✅ "faculty123@university.edu"
  - ❌ "john.smith" (missing @domain)
  - ❌ "john@" (incomplete domain)
  - ❌ "@domain.com" (missing username)

### Role
- **Must be one of:** admin, faculty
- **Examples:**
  - ✅ "admin"
  - ✅ "faculty"
  - ❌ "teacher" (not in allowed list)

---

## Room Management

### Room Name
- **Min length:** 1 character
- **Max length:** 50 characters
- **Must contain at least one letter or number**
- **Examples:**
  - ✅ "Room 101"
  - ✅ "Lab-A"
  - ✅ "Auditorium"
  - ❌ "." (just special character)

### Capacity
- **Must be a positive integer**
- **Min value:** 1
- **Max value:** 10,000
- **Examples:**
  - ✅ 50
  - ✅ 120
  - ❌ 0 (must be at least 1)
  - ❌ -10 (negative not allowed)
  - ❌ "fifty" (must be a number)

### Building (Optional)
- **Min length:** 1 character (if provided)
- **Max length:** 100 characters
- **Examples:**
  - ✅ "Main Building"
  - ✅ "Block A"
  - ✅ "" (empty is OK, field is optional)

### Room Type
- **Must be one of:** lecture, lab, tutorial, seminar, auditorium
- **Examples:**
  - ✅ "lecture"
  - ✅ "lab"
  - ❌ "classroom" (not in allowed list)

---

## Course Management

### Course Code
- **Min length:** 2 characters
- **Max length:** 20 characters
- **Allowed characters:** Letters, numbers, hyphens, underscores
- **No spaces allowed**
- **Automatically converted to UPPERCASE**
- **Examples:**
  - ✅ "CS101" → CS101
  - ✅ "MATH-201" → MATH-201
  - ❌ "C" (too short)
  - ❌ "CS 101" (contains space)

### Course Name
- **Min length:** 3 characters
- **Max length:** 250 characters
- **Must contain letters**
- **Examples:**
  - ✅ "Data Structures and Algorithms"
  - ✅ "Physics Lab (Sec A)"
  - ❌ "DS" (too short)

### Lectures per Week (L)
- **Must be an integer**
- **Min value:** 0
- **Max value:** 5
- **Examples:**
  - ✅ 3
  - ✅ 0 (if course has only practicals)
  - ❌ 6 (exceeds maximum)
  - ❌ -1 (negative not allowed)

### Tutorials per Week (T)
- **Must be an integer**
- **Min value:** 0
- **Max value:** 3
- **Examples:**
  - ✅ 1
  - ✅ 0
  - ❌ 4 (exceeds maximum)

### Practicals per Week (P)
- **Must be an integer**
- **Min value:** 0
- **Max value:** 6
- **Examples:**
  - ✅ 2
  - ✅ 0
  - ❌ 7 (exceeds maximum)

### Credits (C)
- **Must be a positive number** (can be decimal)
- **Min value:** 0
- **Max value:** 20
- **Examples:**
  - ✅ 3
  - ✅ 3.5
  - ✅ 4.0
  - ❌ -1 (negative not allowed)
  - ❌ 25 (exceeds maximum)

### L-T-P-C Validation
- **At least one of L, T, P must be greater than 0**
- **Cannot have a course with 0-0-0-X**
- **Examples:**
  - ✅ L=3, T=0, P=2, C=4
  - ✅ L=0, T=0, P=6, C=3 (lab-only course)
  - ❌ L=0, T=0, P=0, C=3 (no sessions)

### Course Type
- **Must be one of:** Core, Elective, Lab, Project, Seminar
- **Examples:**
  - ✅ "Core"
  - ✅ "Elective"
  - ❌ "Optional" (not in allowed list)

---

## Batch Management

### Batch Name
- **Min length:** 3 characters
- **Max length:** 150 characters
- **Must contain letters**
- **Examples:**
  - ✅ "BTech Sem-II (ICT + CS)"
  - ✅ "MTech ICT-ML Sec A"
  - ❌ "BT" (too short)

### Semester Number
- **Must be an integer**
- **Min value:** 1
- **Max value:** 10
- **Examples:**
  - ✅ 2
  - ✅ 8
  - ❌ 0 (must be at least 1)
  - ❌ 11 (exceeds maximum)

### Student Count
- **Must be an integer**
- **Min value:** 0
- **Max value:** 500
- **Examples:**
  - ✅ 60
  - ✅ 120
  - ❌ -5 (negative not allowed)
  - ❌ 600 (exceeds maximum)

---

## Error Messages

When validation fails, you'll see clear error messages:

### Examples:
- ❌ "Full name cannot be empty."
- ❌ "Abbreviation can only contain letters, numbers, hyphens, and underscores (no spaces)."
- ❌ "Email must be a valid email address (e.g., name@domain.com)."
- ❌ "Capacity must be at least 1."
- ❌ "End date must be after Start date."
- ❌ "Lectures per week cannot exceed 5."
- ❌ "Course must have at least one lecture, tutorial, or practical session per week."

---

## Tips for Valid Input

1. **Names and Titles:**
   - Use proper capitalization
   - Avoid excessive punctuation
   - Include at least 2-3 characters

2. **Codes and Abbreviations:**
   - Use uppercase letters and numbers
   - Use hyphens or underscores instead of spaces
   - Keep them short but meaningful (e.g., CS101, DR-SMITH)

3. **Emails:**
   - Use institutional email format
   - Double-check for typos
   - Ensure @domain.com is included

4. **Numbers:**
   - Use whole numbers for counts
   - Use decimals only for credits (e.g., 3.5)
   - Stay within reasonable ranges

5. **Dates:**
   - Always use YYYY-MM-DD format
   - Use calendar to avoid invalid dates
   - Ensure end date is after start date

---

## Implementation Details

All validation is handled by the `utils/validators.py` module, which provides:

- **Validators class:** Collection of validation methods
- **ValidationError exception:** Custom exception for validation failures
- **validate_form_data():** Batch validation for multiple fields
- **safe_strip():** Helper for cleaning input

The validation is applied in the admin routes before any database operations, ensuring data integrity and preventing invalid data from entering the system.
