# 🔧 Faculty Issues & Solutions

## 🔍 Issues You Discovered

### Issue 1: Faculty Names Swapped ❌
**Problem:** Some faculty have full name in abbreviation column and vice versa

**Example from your screenshot:**
```
NAME (should be full)    | ABBR (should be short)
-------------------------|------------------------
(VF)                     | VISITING_FACULTY  ❌ SWAPPED!
AB                       | AB                ❌ SWAPPED!
Abhishek Gupta (AG1)     | AG1               ✅ CORRECT
```

**Root Cause:** Excel file has inconsistent data format

---

### Issue 2: No Emails ❌
**Problem:** Most faculty records have no email addresses

**Impact:**
- Cannot create Firebase accounts
- Cannot generate temporary passwords
- Faculty cannot login

---

### Issue 3: Cannot Add Emails Without Deleting ❌
**Problem:** No way to bulk-add emails to existing faculty

**Current workflow:**
1. Delete faculty ❌
2. Re-add with email ❌
3. Lose all course assignments ❌

---

### Issue 4: Deleted Faculty Loses Courses ❌
**Problem:** When you delete and re-add faculty, their timetable shows 0 courses

**Why:** Course-faculty links are deleted when faculty is deleted

---

## ✅ Solutions

### Solution 1: Fix Faculty Names in Excel

**Option A: Fix the Excel File (Recommended)**

Open `Faculty names.xlsx` and ensure format:
```
Column A: Full Name       | Column B: Abbreviation | Column C: Email (optional)
--------------------------|------------------------|---------------------------
Visiting Faculty          | VF                     | vf@dau.ac.in
Abhishek Gupta            | AG1                    | ag1@dau.ac.in
Ankush Chander            | AC                     | ac@dau.ac.in
```

**Rules:**
- Column A = Full proper name (e.g., "Dr. John Smith")
- Column B = Short code (e.g., "JS", "JDS")
- Column C = Email address (optional but recommended)

---

**Option B: Fix in Database (Quick Fix)**

I'll create a script to swap incorrectly formatted names:

```python
# fix_faculty_names.py
from app import create_app
from models import db, Faculty

app = create_app()
with app.app_context():
    # Find faculty where abbreviation looks like a full name
    for fac in Faculty.query.all():
        # If abbreviation is longer than 10 chars, probably swapped
        if len(fac.abbreviation) > 10:
            # Swap them
            temp = fac.full_name
            fac.full_name = fac.abbreviation
            fac.abbreviation = temp
            print(f"Fixed: {fac.full_name} ({fac.abbreviation})")
    
    db.session.commit()
    print("Done!")
```

---

### Solution 2: Add Emails to Existing Faculty

**I'll create a bulk email update feature:**

#### Method 1: Update via Admin Panel (New Feature)

Add an "Edit" button to faculty list that allows updating email without deleting.

#### Method 2: Bulk Update Script

```python
# add_faculty_emails.py
from app import create_app
from models import db, Faculty

app = create_app()
with app.app_context():
    # Read email mapping from CSV
    import pandas as pd
    df = pd.read_csv('faculty_emails.csv')
    
    for _, row in df.iterrows():
        abbr = row['abbreviation']
        email = row['email']
        
        fac = Faculty.query.filter_by(abbreviation=abbr).first()
        if fac:
            fac.email = email
            print(f"Added email for {fac.full_name}: {email}")
    
    db.session.commit()
    print("Done!")
```

**Create `faculty_emails.csv`:**
```csv
abbreviation,email
AG1,ag1@dau.ac.in
AC,ac@dau.ac.in
AJ,aj@dau.ac.in
```

---

#### Method 3: Re-upload Faculty Mapping with Emails

**Fix your Excel file to include emails, then re-upload:**

The `parse_faculty_mapping()` function UPDATES existing faculty:
```python
# It won't create duplicates, just updates existing records
if fac:
    fac.full_name = full_name
    if email:
        fac.email = email  # ← Adds email to existing faculty
    updated += 1
```

**Steps:**
1. Open `Faculty names.xlsx`
2. Add email column (Column C)
3. Fill in emails for each faculty
4. Save file
5. Go to Admin → Upload
6. Upload Type: "Faculty Mapping"
7. Upload file

**Result:** Emails added to existing faculty without deleting!

---

### Solution 3: Generate Temporary Passwords for Existing Faculty

**After adding emails, generate passwords:**

I'll create a script to generate passwords for faculty who have emails but no Firebase account:

```python
# generate_passwords_for_existing.py
from app import create_app
from models import db, Faculty
from routes.admin import _generate_temp_password, _ensure_firebase_admin
from firebase_admin import auth as firebase_auth

app = create_app()
with app.app_context():
    _ensure_firebase_admin()
    
    # Find faculty with email but no firebase_uid
    faculty_without_firebase = Faculty.query.filter(
        Faculty.email.isnot(None),
        Faculty.firebase_uid.is_(None)
    ).all()
    
    print(f"Found {len(faculty_without_firebase)} faculty without Firebase accounts\n")
    
    passwords = []
    for fac in faculty_without_firebase:
        try:
            # Generate password
            temp_password = _generate_temp_password()
            
            # Create Firebase user
            try:
                user = firebase_auth.get_user_by_email(fac.email)
                # User exists, update password
                firebase_auth.update_user(user.uid, password=temp_password)
            except firebase_auth.UserNotFoundError:
                # Create new user
                user = firebase_auth.create_user(
                    email=fac.email,
                    password=temp_password
                )
            
            # Update database
            fac.firebase_uid = user.uid
            fac.must_reset_password = True
            
            passwords.append({
                'name': fac.full_name,
                'abbr': fac.abbreviation,
                'email': fac.email,
                'password': temp_password
            })
            
            print(f"✅ {fac.full_name} ({fac.abbreviation})")
            
        except Exception as e:
            print(f"❌ {fac.full_name}: {e}")
    
    db.session.commit()
    
    # Print all passwords
    print("\n" + "="*60)
    print("TEMPORARY PASSWORDS")
    print("="*60 + "\n")
    
    for p in passwords:
        print(f"Name: {p['name']}")
        print(f"Abbreviation: {p['abbr']}")
        print(f"Email: {p['email']}")
        print(f"Password: {p['password']}")
        print("-" * 60)
```

---

### Solution 4: Fix Deleted Faculty Course Assignments

**Problem:** When you delete faculty and re-add them, course assignments are lost.

**Why:** Database foreign key constraint:
```sql
CREATE TABLE course_faculty (
    course_id INTEGER,
    faculty_id INTEGER,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
);
```

`ON DELETE CASCADE` means: "When faculty is deleted, delete all their course assignments"

---

**Solution A: Don't Delete Faculty (Recommended)**

Instead of deleting, just update the record:

**Add an "Edit Faculty" feature:**

```python
@admin_bp.route('/faculty/<int:fac_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_faculty(fac_id):
    """Edit faculty details without deleting."""
    fac = Faculty.query.get_or_404(fac_id)
    
    if request.method == 'POST':
        fac.full_name = request.form.get('full_name', '').strip()
        fac.abbreviation = request.form.get('abbreviation', '').strip().upper()
        fac.email = request.form.get('email', '').strip() or None
        fac.role = request.form.get('role', 'faculty').strip()
        
        # If email added and no Firebase account, create one
        if fac.email and not fac.firebase_uid:
            from firebase_admin import auth as firebase_auth
            try:
                _ensure_firebase_admin()
                temp_password = _generate_temp_password()
                
                try:
                    user = firebase_auth.get_user_by_email(fac.email)
                    firebase_auth.update_user(user.uid, password=temp_password)
                except firebase_auth.UserNotFoundError:
                    user = firebase_auth.create_user(email=fac.email, password=temp_password)
                
                fac.firebase_uid = user.uid
                fac.must_reset_password = True
                
                flash(f'Faculty updated. Temporary password: {temp_password}', 'success')
            except Exception as e:
                flash(f'Faculty updated but Firebase error: {e}', 'warning')
        else:
            flash(f'Faculty "{fac.full_name}" updated successfully.', 'success')
        
        db.session.commit()
        return redirect(url_for('admin.faculty_list'))
    
    return render_template('admin/edit_faculty.html', faculty=fac)
```

---

**Solution B: Backup and Restore Course Assignments**

If you must delete and re-add:

```python
# backup_faculty_courses.py
from app import create_app
from models import db, Faculty, CourseFaculty

app = create_app()
with app.app_context():
    # Before deleting, backup course assignments
    fac = Faculty.query.filter_by(abbreviation='AG1').first()
    
    if fac:
        # Get all course IDs
        course_ids = [cf.course_id for cf in CourseFaculty.query.filter_by(faculty_id=fac.id).all()]
        print(f"Faculty {fac.full_name} teaches {len(course_ids)} courses")
        print(f"Course IDs: {course_ids}")
        
        # Save to file
        with open('faculty_AG1_courses.txt', 'w') as f:
            f.write(','.join(map(str, course_ids)))
```

Then after re-adding:

```python
# restore_faculty_courses.py
from app import create_app
from models import db, Faculty, CourseFaculty

app = create_app()
with app.app_context():
    # After re-adding, restore course assignments
    fac = Faculty.query.filter_by(abbreviation='AG1').first()
    
    if fac:
        # Read course IDs from file
        with open('faculty_AG1_courses.txt', 'r') as f:
            course_ids = list(map(int, f.read().split(',')))
        
        # Re-link courses
        for course_id in course_ids:
            existing = CourseFaculty.query.filter_by(
                course_id=course_id,
                faculty_id=fac.id
            ).first()
            
            if not existing:
                cf = CourseFaculty(course_id=course_id, faculty_id=fac.id)
                db.session.add(cf)
        
        db.session.commit()
        print(f"Restored {len(course_ids)} course assignments")
```

---

## 🎯 Recommended Workflow

### For Your Current Situation:

**Step 1: Fix Faculty Names**
```bash
# Option A: Fix Excel and re-upload
# Edit Faculty names.xlsx to have correct format
# Upload via Admin → Upload → Faculty Mapping

# Option B: Run fix script
python fix_faculty_names.py
```

**Step 2: Add Emails**
```bash
# Create faculty_emails.csv with abbreviation,email columns
# Run bulk update script
python add_faculty_emails.py

# OR add email column to Faculty names.xlsx and re-upload
```

**Step 3: Generate Firebase Accounts**
```bash
# Generate passwords for all faculty with emails
python generate_passwords_for_existing.py

# Save the output - it contains all temporary passwords
```

**Step 4: Add Edit Faculty Feature**
```bash
# I'll create the edit faculty route and template
# This prevents future deletion issues
```

---

## 🛠️ Implementation: Edit Faculty Feature

Let me create the edit faculty feature now:

### 1. Add Route to admin.py

```python
@admin_bp.route('/faculty/<int:fac_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_faculty(fac_id):
    """Edit faculty member details."""
    fac = Faculty.query.get_or_404(fac_id)
    
    if request.method == 'GET':
        return render_template('admin/edit_faculty.html', faculty=fac)
    
    # POST - update faculty
    full_name = request.form.get('full_name', '').strip()
    abbreviation = request.form.get('abbreviation', '').strip().upper()
    email = request.form.get('email', '').strip() or None
    role = request.form.get('role', 'faculty').strip()
    
    if not all([full_name, abbreviation]):
        flash('Name and abbreviation are required.', 'error')
        return redirect(url_for('admin.edit_faculty', fac_id=fac_id))
    
    # Check if abbreviation changed and conflicts with another faculty
    if abbreviation != fac.abbreviation:
        existing = Faculty.query.filter_by(abbreviation=abbreviation).first()
        if existing:
            flash(f'Abbreviation "{abbreviation}" already exists.', 'error')
            return redirect(url_for('admin.edit_faculty', fac_id=fac_id))
    
    # Check if email changed and conflicts
    if email and email != fac.email:
        existing_email = Faculty.query.filter_by(email=email).first()
        if existing_email and existing_email.id != fac.id:
            flash(f'Email "{email}" already exists.', 'error')
            return redirect(url_for('admin.edit_faculty', fac_id=fac_id))
    
    # Update basic info
    fac.full_name = full_name
    fac.abbreviation = abbreviation
    fac.role = role
    
    # Handle email and Firebase account
    temp_password = None
    if email and email != fac.email:
        # Email added or changed
        fac.email = email
        
        if not fac.firebase_uid:
            # No Firebase account yet, create one
            from firebase_admin import auth as firebase_auth
            from firebase_admin import exceptions as firebase_exceptions
            
            try:
                _ensure_firebase_admin()
                temp_password = _generate_temp_password()
                
                try:
                    user = firebase_auth.get_user_by_email(email)
                    # User exists in Firebase, link it
                    firebase_auth.update_user(user.uid, password=temp_password)
                    fac.firebase_uid = user.uid
                except firebase_auth.UserNotFoundError:
                    # Create new Firebase user
                    user = firebase_auth.create_user(email=email, password=temp_password)
                    fac.firebase_uid = user.uid
                
                fac.must_reset_password = True
                
            except firebase_exceptions.FirebaseError as exc:
                flash(f'Faculty updated but Firebase error: {exc}', 'warning')
    
    db.session.commit()
    
    if temp_password:
        flash(f'Faculty "{full_name}" updated. Temporary password: {temp_password}', 'success')
    else:
        flash(f'Faculty "{full_name}" updated successfully.', 'success')
    
    return redirect(url_for('admin.faculty_list'))
```

### 2. Update faculty.html template

Add "Edit" button next to each faculty:

```html
<!-- In templates/admin/faculty.html -->
<td class="actions">
    <a href="{{ url_for('admin.edit_faculty', fac_id=f.id) }}" class="btn btn-secondary">Edit</a>
    <a href="{{ url_for('admin.export_faculty_pdf', fac_id=f.id) }}" class="btn btn-secondary">📄 PDF</a>
    <form action="{{ url_for('admin.delete_faculty', fac_id=f.id) }}" method="POST" style="display:inline;">
        <button type="submit" class="btn btn-danger" onclick="return confirm('Delete this faculty member?')">Delete</button>
    </form>
</td>
```

### 3. Create edit_faculty.html template

```html
<!-- templates/admin/edit_faculty.html -->
{% extends "base.html" %}
{% block title %}Edit Faculty{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Edit Faculty Member</h1>
</div>

<div class="card">
    <form method="POST">
        <div class="form-group">
            <label for="full_name">Full Name *</label>
            <input type="text" id="full_name" name="full_name" value="{{ faculty.full_name }}" required>
        </div>
        
        <div class="form-group">
            <label for="abbreviation">Abbreviation *</label>
            <input type="text" id="abbreviation" name="abbreviation" value="{{ faculty.abbreviation }}" required>
        </div>
        
        <div class="form-group">
            <label for="email">Email</label>
            <input type="email" id="email" name="email" value="{{ faculty.email or '' }}">
            <small>Add email to create login account. Leave empty for no login.</small>
        </div>
        
        <div class="form-group">
            <label for="role">Role</label>
            <select id="role" name="role">
                <option value="faculty" {% if faculty.role == 'faculty' %}selected{% endif %}>Faculty</option>
                <option value="admin" {% if faculty.role == 'admin' %}selected{% endif %}>Admin</option>
            </select>
        </div>
        
        <div class="form-actions">
            <button type="submit" class="btn btn-primary">Save Changes</button>
            <a href="{{ url_for('admin.faculty_list') }}" class="btn btn-secondary">Cancel</a>
        </div>
    </form>
</div>
{% endblock %}
```

---

## 📊 Summary of Solutions

| Issue | Solution | Status |
|-------|----------|--------|
| Names swapped | Fix Excel or run swap script | ✅ Ready |
| No emails | Add email column to Excel, re-upload | ✅ Ready |
| Can't add emails | Use edit feature (I'll create) | ✅ Creating |
| Deleted faculty loses courses | Don't delete, use edit instead | ✅ Ready |
| Need temp passwords | Run password generation script | ✅ Ready |

---

## 🎯 Action Plan for You

**Immediate (Before Demo):**
1. ✅ Fix `Faculty names.xlsx` format
2. ✅ Add email column with faculty emails
3. ✅ Re-upload via Admin → Upload → Faculty Mapping
4. ✅ Run password generation script
5. ✅ Save all temporary passwords

**For Future:**
1. ✅ Use Edit feature instead of Delete
2. ✅ Always include emails in faculty data
3. ✅ Test login for a few faculty members

---

Let me create these scripts for you now!
