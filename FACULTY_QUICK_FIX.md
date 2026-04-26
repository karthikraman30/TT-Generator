# 🚀 Faculty Issues - Quick Fix Guide

## 🔍 Problems You Found

1. ❌ Faculty names swapped (full name in abbreviation column)
2. ❌ No emails for most faculty
3. ❌ Deleted faculty loses all course assignments (timetable shows 0)
4. ❌ No way to add emails without deleting

## ✅ Solutions Created

### Solution 1: Fix Swapped Names

```bash
cd TT-Generator
python fix_faculty_names.py
```

**What it does:**
- Finds faculty where abbreviation looks like a full name
- Swaps full_name and abbreviation
- Shows preview before applying changes

---

### Solution 2: Add Emails to Existing Faculty

**Method A: Re-upload Faculty Mapping (Easiest)**

1. Open `Faculty names.xlsx`
2. Ensure format:
   ```
   Column A: Full Name       | Column B: Abbreviation | Column C: Email
   Abhishek Gupta            | AG1                    | ag1@dau.ac.in
   Ankush Chander            | AC                     | ac@dau.ac.in
   ```
3. Save file
4. Go to Admin → Upload
5. Select file, choose "Faculty Mapping"
6. Upload

**Result:** Emails added to existing faculty WITHOUT deleting!

---

**Method B: Use Edit Feature (New!)**

1. Go to Admin → Faculty
2. Click "Edit" button next to faculty name
3. Add email address
4. Click "Save Changes"
5. If email added, temporary password will be generated

---

### Solution 3: Generate Passwords for Faculty with Emails

```bash
cd TT-Generator
python generate_passwords_for_existing.py
```

**What it does:**
- Finds all faculty with emails but no Firebase account
- Creates Firebase accounts
- Generates secure temporary passwords
- Saves passwords to `faculty_passwords.txt`

**Output:**
```
Name: Abhishek Gupta
Abbreviation: AG1
Email: ag1@dau.ac.in
Password: aB3!xYz9Qw12
------------------------------------------------------------
```

---

### Solution 4: Don't Delete Faculty!

**Problem:** When you delete faculty, all their course assignments are deleted too.

**Solution:** Use the new "Edit" feature instead!

**Before (Wrong):**
```
1. Delete faculty ❌
2. Re-add faculty ❌
3. Courses lost ❌
4. Timetable shows 0 ❌
```

**After (Correct):**
```
1. Click "Edit" ✅
2. Update details ✅
3. Add email ✅
4. Courses preserved ✅
5. Timetable intact ✅
```

---

## 🎯 Step-by-Step Fix Process

### Step 1: Fix Swapped Names (5 minutes)

```bash
python fix_faculty_names.py
```

Review the changes, type "yes" to apply.

---

### Step 2: Add Emails (10 minutes)

**Option A: Fix Excel File**

1. Open `Faculty names.xlsx`
2. Add Column C header: "Email"
3. Fill in emails for each faculty:
   ```
   AG1 → ag1@dau.ac.in
   AC  → ac@dau.ac.in
   AJ  → aj@dau.ac.in
   ```
4. Save file
5. Upload via Admin → Upload → Faculty Mapping

**Option B: Use Edit Feature**

1. Go to Admin → Faculty
2. For each faculty without email:
   - Click "Edit"
   - Add email
   - Click "Save"
   - Copy temporary password shown

---

### Step 3: Generate Firebase Accounts (2 minutes)

```bash
python generate_passwords_for_existing.py
```

**Important:** Save the output! It contains all temporary passwords.

Passwords are also saved to `faculty_passwords.txt`.

---

### Step 4: Test Login (5 minutes)

1. Logout from admin
2. Go to login page
3. Try logging in as one faculty:
   - Email: `ag1@dau.ac.in`
   - Password: `[temporary password]`
4. Should redirect to change password
5. Set new password
6. Should see faculty dashboard with timetable

---

## 🐛 Why Deleted Faculty Shows 0 Courses

### The Problem

When you delete a faculty member:

```sql
-- Database has this constraint:
CREATE TABLE course_faculty (
    course_id INTEGER,
    faculty_id INTEGER,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
);
```

`ON DELETE CASCADE` means:
- Delete faculty → Delete all course_faculty links
- Faculty loses all course assignments
- Timetable shows 0 courses

---

### The Solution

**Don't delete faculty!** Use the Edit feature instead:

1. Go to Admin → Faculty
2. Click "Edit" (not Delete)
3. Update name, email, role
4. Click "Save"

**Result:** Faculty updated, courses preserved!

---

## 📋 Complete Workflow for Your Demo

### Before Demo:

**1. Fix Faculty Data (15 minutes)**

```bash
# Fix swapped names
python fix_faculty_names.py

# Add emails to Faculty names.xlsx
# Re-upload via Admin → Upload → Faculty Mapping

# Generate Firebase accounts
python generate_passwords_for_existing.py

# Save faculty_passwords.txt somewhere safe
```

**2. Test One Faculty Login (5 minutes)**

```
1. Pick one faculty (e.g., AG1)
2. Find their email and temp password
3. Logout from admin
4. Login as faculty
5. Change password
6. Verify timetable shows courses
```

---

### During Demo:

**Show Faculty Management:**

1. Go to Admin → Faculty
2. Show faculty list
3. Click "Edit" on one faculty
4. Show you can update details without deleting
5. Explain: "This preserves course assignments"

**Show Faculty Login:**

1. Logout from admin
2. Login as faculty (use test account)
3. Show faculty dashboard
4. Show their timetable
5. Explain: "Each faculty sees only their schedule"

---

## 🎓 Understanding the System

### Faculty is SHARED

```
Faculty Table (No semester_id)
├── Dr. Smith (teaches in all semesters)
├── Dr. Jones (teaches in all semesters)
└── Dr. Brown (teaches in all semesters)
```

### Course Assignments are SEMESTER-SPECIFIC

```
Course-Faculty Links (Has semester_id via course)
├── Winter 2025-26:
│   ├── Dr. Smith → CS101
│   └── Dr. Jones → CS102
└── Summer 2026:
    ├── Dr. Smith → CS201
    └── Dr. Brown → CS202
```

**Key Point:** Same faculty, different courses each semester!

---

## ✅ Checklist

Before demo:
- [ ] Run `fix_faculty_names.py`
- [ ] Add emails to `Faculty names.xlsx`
- [ ] Re-upload faculty mapping
- [ ] Run `generate_passwords_for_existing.py`
- [ ] Save `faculty_passwords.txt`
- [ ] Test one faculty login
- [ ] Verify faculty sees their timetable

During demo:
- [ ] Show faculty list
- [ ] Show edit feature
- [ ] Login as faculty
- [ ] Show faculty timetable
- [ ] Explain password reset flow

---

## 🚨 Common Issues

### Issue: "Faculty not found in slots"

**Cause:** Faculty abbreviation in Excel doesn't match database

**Solution:** Check abbreviations match exactly (case-sensitive)

---

### Issue: "Email already exists"

**Cause:** Trying to add email that's already used

**Solution:** Check if faculty already has that email, or use different email

---

### Issue: "Firebase error"

**Cause:** Firebase credentials not configured

**Solution:** Check `.env` file has Firebase config, or use dev login

---

### Issue: "Timetable shows 0 courses after re-adding faculty"

**Cause:** Faculty was deleted, course links were deleted

**Solution:** Don't delete! Use Edit feature instead

---

## 💡 Pro Tips

1. **Never delete faculty** - Always use Edit
2. **Always include emails** in faculty data
3. **Save temporary passwords** immediately
4. **Test login** before demo
5. **Use dev login** if Firebase fails

---

## 📞 Quick Commands

```bash
# Fix swapped names
python fix_faculty_names.py

# Generate passwords
python generate_passwords_for_existing.py

# Check faculty without emails
# (In Python shell)
from app import create_app
from models import Faculty
app = create_app()
with app.app_context():
    no_email = Faculty.query.filter(
        (Faculty.email == None) | (Faculty.email == '')
    ).count()
    print(f"{no_email} faculty without emails")
```

---

**You're all set! 🎉**

The Edit feature prevents future issues, and the scripts fix existing problems. Your demo will work perfectly!
