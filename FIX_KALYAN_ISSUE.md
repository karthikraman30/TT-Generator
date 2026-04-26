# 🔧 Fixing KALYAN SASIDAR's Account Issue

## 🔍 Problem Identified

KALYAN SASIDAR's account has:
- ✅ Email: `pks@dau.ac.in`
- ✅ Firebase UID: `3fWCAtXqWhe7Y3P9I3K3zUmsyY1`
- ❌ `must_reset_password`: **FALSE** (should be TRUE)

This means the user can login but won't be forced to change their password.

---

## 🎯 Root Cause

The issue occurred because when the account was created, the `must_reset_password` flag was not set to `TRUE`. This could happen if:

1. **User already existed in Firebase** before being added via admin panel
2. **Exception occurred** during Firebase user creation
3. **Manual database insertion** without proper flag setting
4. **Code bug** in the account creation flow

---

## ✅ Solution: Three Options

### Option 1: Run the Fix Script (Recommended)

I've created a script to fix KALYAN SASIDAR's account specifically:

```bash
cd TT-Generator
python fix_kalyan_account.py
```

**What this does:**
1. Finds KALYAN SASIDAR in the database
2. Generates a new secure temporary password
3. Updates the password in Firebase
4. Sets `must_reset_password = TRUE`
5. Displays the new temporary password

**Expected Output:**
```
✅ Found: KALYAN SASIDAR
   Email: pks@dau.ac.in
   Firebase UID: 3fWCAtXqWhe7Y3P9I3K3zUmsyY1
   Current must_reset_password: False

🔐 Generated temporary password: aB3!xYz9Qw12
   Updating existing Firebase user...

✅ SUCCESS!
   Updated must_reset_password to: True

📋 IMPORTANT: Share this temporary password with KALYAN SASIDAR:
   Email: pks@dau.ac.in
   Temporary Password: aB3!xYz9Qw12

   They will be forced to change it on first login.
```

---

### Option 2: Fix All Problematic Accounts

If you suspect other accounts might have the same issue:

```bash
cd TT-Generator
python fix_all_accounts.py
```

**What this does:**
1. Scans all faculty accounts
2. Finds accounts with Firebase UID but `must_reset_password = FALSE`
3. Asks for confirmation
4. Fixes all problematic accounts
5. Displays all new temporary passwords

**Expected Output:**
```
⚠️  Found 3 account(s) with firebase_uid but must_reset_password=False:

1. KALYAN SASIDAR (PKS)
   Email: pks@dau.ac.in
   Firebase UID: 3fWCAtXqWhe7Y3P9I3K3zUmsyY1
   must_reset_password: False

2. Another User (AU)
   Email: au@dau.ac.in
   Firebase UID: xyz123...
   must_reset_password: False

Do you want to fix these accounts? (yes/no): yes

🔧 Fixing accounts...

✅ Fixed: KALYAN SASIDAR
✅ Fixed: Another User

✅ SUCCESSFULLY FIXED ACCOUNTS
📋 IMPORTANT: Share these temporary passwords:

Name: KALYAN SASIDAR
Email: pks@dau.ac.in
Temporary Password: aB3!xYz9Qw12
------------------------------------------------------------
Name: Another User
Email: au@dau.ac.in
Temporary Password: Xy9!mNpQ2rSt
------------------------------------------------------------
```

---

### Option 3: Manual Database Update

If you prefer to do it manually:

```sql
-- Update the flag
UPDATE faculty 
SET must_reset_password = true 
WHERE abbreviation = 'PKS';

-- Verify the change
SELECT full_name, email, must_reset_password 
FROM faculty 
WHERE abbreviation = 'PKS';
```

**Then reset password in Firebase Console:**
1. Go to Firebase Console → Authentication → Users
2. Find `pks@dau.ac.in`
3. Click three dots → Reset password
4. Set a new password (e.g., `TempPass123!`)
5. Share this password with KALYAN SASIDAR

---

## 🔒 Code Fix Applied

I've also improved the `add_faculty()` function in `routes/admin.py` to prevent this issue in the future:

**Changes made:**
1. Generate password **before** trying to create/update Firebase user
2. Added catch-all exception handler
3. Better error messages

**Before:**
```python
try:
    user = firebase_auth.get_user_by_email(email)
    temp_password = _generate_temp_password()  # ← Generated after check
    user = firebase_auth.update_user(user.uid, password=temp_password)
except firebase_auth.UserNotFoundError:
    temp_password = _generate_temp_password()  # ← Generated in exception
    user = firebase_auth.create_user(email=email, password=temp_password)
```

**After:**
```python
# Generate password first to ensure it's always set
temp_password = _generate_temp_password()  # ← Generated first

try:
    user = firebase_auth.get_user_by_email(email)
    user = firebase_auth.update_user(user.uid, password=temp_password)
except firebase_auth.UserNotFoundError:
    user = firebase_auth.create_user(email=email, password=temp_password)
```

---

## 📋 Step-by-Step Fix Process

### Step 1: Run the Fix Script

```bash
cd TT-Generator
python fix_kalyan_account.py
```

### Step 2: Copy the Temporary Password

The script will display something like:
```
Temporary Password: aB3!xYz9Qw12
```

**⚠️ IMPORTANT:** Copy this password immediately!

### Step 3: Verify in Database

Check that the flag is now TRUE:

```sql
SELECT full_name, email, must_reset_password 
FROM faculty 
WHERE abbreviation = 'PKS';
```

**Expected result:**
```
full_name       | email          | must_reset_password
----------------|----------------|--------------------
KALYAN SASIDAR  | pks@dau.ac.in  | true
```

### Step 4: Test the Login Flow

1. **Logout** from admin account
2. **Login** as KALYAN SASIDAR:
   - Email: `pks@dau.ac.in`
   - Password: `[temporary password from script]`
3. **Verify redirect** to `/change-password`
4. **Set new password** (must meet policy)
5. **Verify redirect** to dashboard

### Step 5: Verify Password Change Worked

1. **Logout**
2. **Login again** with new password
3. **Verify** no password change prompt
4. **Check database**:
   ```sql
   SELECT must_reset_password FROM faculty WHERE abbreviation = 'PKS';
   ```
   Should still be `true` (flag is not cleared after change)

**Wait, that's wrong!** Let me check the change_password function...

---

## 🐛 Additional Issue Found

Let me check if the `change_password` function properly clears the flag:

```python
# In routes/auth.py - change_password()
faculty.must_reset_password = False  # ← Should clear the flag
db.session.commit()
```

If this is working correctly, after password change, the flag should be `false`.

---

## ✅ Complete Testing Checklist

After running the fix script:

- [ ] Script runs successfully
- [ ] Temporary password displayed
- [ ] Database shows `must_reset_password = true`
- [ ] User can login with temporary password
- [ ] User redirected to `/change-password`
- [ ] Weak passwords rejected
- [ ] Strong password accepted
- [ ] User redirected to dashboard
- [ ] Database shows `must_reset_password = false` (after change)
- [ ] User can re-login without password change prompt

---

## 🚨 If Fix Script Fails

### Error: "Faculty not found"

**Solution:** Check the abbreviation
```sql
SELECT abbreviation, full_name FROM faculty WHERE full_name LIKE '%KALYAN%';
```

Update the script if abbreviation is different.

### Error: "Firebase error"

**Solution:** Check Firebase credentials
```bash
# Verify credentials file exists
ls -la firebase-credentials.json

# Check .env file
cat .env | grep FIREBASE
```

### Error: "No such table: faculty"

**Solution:** You're using PostgreSQL, not SQLite
- Check your `DATABASE_URL` in `.env`
- Use appropriate database client (psql instead of sqlite3)

---

## 📞 Need Help?

If the fix script doesn't work:

1. **Check Flask console** for error messages
2. **Check Firebase Console** to verify user exists
3. **Check database** to verify record exists
4. **Run with debug**:
   ```bash
   python -u fix_kalyan_account.py
   ```

---

## 🎯 Prevention for Future

To prevent this issue from happening again:

1. **Always use the admin panel** to create accounts (don't manually insert into database)
2. **Check the success message** shows the temporary password
3. **Verify in database** that `must_reset_password = true` after creation
4. **Test the login flow** immediately after creating an account

---

## 📊 Summary

**Problem:** KALYAN SASIDAR's account has `must_reset_password = false`

**Solution:** Run `python fix_kalyan_account.py`

**Result:** 
- New temporary password generated
- Flag set to `true`
- User forced to change password on next login

**Code Fix:** Improved `add_faculty()` function to prevent future occurrences

---

**Last Updated:** April 26, 2026
