# 🧪 Step-by-Step Testing Guide for Firebase Authentication

## Prerequisites

Before testing, ensure:
- ✅ Flask app is running (`python app.py`)
- ✅ Firebase credentials are configured in `.env`
- ✅ Database is initialized
- ✅ You have admin access (at least one admin faculty record)

---

## 🚀 Quick Start Testing

### Step 1: Run the Password Policy Tester

```bash
cd TT-Generator
python test_firebase_auth.py
```

**What this does:**
- Generates sample temporary passwords
- Tests invalid passwords (should fail)
- Tests valid passwords (should pass)
- Allows interactive password testing

**Expected Output:**
```
🔐 FIREBASE AUTHENTICATION TESTING TOOL
============================================================

📝 Test 1: Generating Temporary Passwords
------------------------------------------------------------
Generated #1: aB3!xYz9Qw12 - ✅ Valid
Generated #2: P@ssw0rd123X - ✅ Valid
Generated #3: Xy9!mNpQ2rSt - ✅ Valid

📝 Test 2: Testing Invalid Passwords (Should Fail)
------------------------------------------------------------
short                → ❌ Correctly Rejected (Too short)
alllowercase123!     → ❌ Correctly Rejected (No uppercase)
...
```

---

## 🔥 Firebase Console Setup (One-Time)

### 1. Access Firebase Console

1. Go to https://console.firebase.google.com/
2. Select your project
3. Click "Authentication" in left sidebar
4. Click "Sign-in method" tab
5. Ensure "Email/Password" is **Enabled**

### 2. Verify Service Account

1. Go to Project Settings (gear icon)
2. Click "Service accounts" tab
3. Verify `firebase-credentials.json` matches this project
4. If not, download new credentials and update `.env`

---

## 📋 Complete Testing Workflow

### Test Case 1: Admin Creates Faculty Account

**Objective:** Verify admin can create faculty accounts with secure passwords

**Steps:**

1. **Login as Admin**
   ```
   URL: http://localhost:5000/login
   Method: Dev Login
   Abbreviation: [Your admin abbreviation, e.g., "ADMIN"]
   ```

2. **Navigate to Faculty Management**
   ```
   Click: Admin → Faculty
   Or go to: http://localhost:5000/admin/faculty
   ```

3. **Add New Faculty**
   ```
   Click: "Add Faculty" button
   Fill form:
   ┌─────────────────────────────────────┐
   │ Full Name:     Test Faculty User    │
   │ Abbreviation:  TFU                  │
   │ Email:         testfaculty@test.com │
   │ Role:          faculty              │
   └─────────────────────────────────────┘
   Click: "Add Faculty"
   ```

4. **Capture Temporary Password**
   ```
   ⚠️ IMPORTANT: Copy the password shown in success message
   Example: "Faculty 'Test Faculty User' added. Temporary password: aB3!xYz9Qw12"
   
   Save this password: ___________________________
   ```

5. **Verify in Firebase Console**
   ```
   Go to: Firebase Console → Authentication → Users
   Look for: testfaculty@test.com
   Status: Should show as created
   ```

6. **Verify in Database**
   ```sql
   SELECT full_name, email, firebase_uid, must_reset_password 
   FROM faculty 
   WHERE email = 'testfaculty@test.com';
   
   Expected:
   ┌──────────────────────┬────────────────────────┬──────────────┬────────────────────────┐
   │ full_name            │ email                  │ firebase_uid │ must_reset_password    │
   ├──────────────────────┼────────────────────────┼──────────────┼────────────────────────┤
   │ Test Faculty User    │ testfaculty@test.com   │ [Firebase ID]│ true                   │
   └──────────────────────┴────────────────────────┴──────────────┴────────────────────────┘
   ```

**✅ Success Criteria:**
- Green success message appears
- Temporary password is displayed (12 characters)
- User appears in Firebase Console
- Database record created with `must_reset_password = true`

---

### Test Case 2: First Login with Temporary Password

**Objective:** Verify user can login with temporary password and is forced to change it

**Steps:**

1. **Logout from Admin**
   ```
   Click: Logout button
   Or go to: http://localhost:5000/logout
   ```

2. **Login with New Account**
   ```
   URL: http://localhost:5000/login
   
   Fill form:
   ┌─────────────────────────────────────┐
   │ Email:    testfaculty@test.com      │
   │ Password: [temporary password]      │
   └─────────────────────────────────────┘
   Click: "🔐 Sign in"
   ```

3. **Observe Redirect**
   ```
   Expected: Automatic redirect to /change-password
   URL should be: http://localhost:5000/change-password
   ```

4. **Verify Change Password Page**
   ```
   Page should show:
   - "Change Password" heading
   - Password policy explanation
   - Two password fields
   - "Set password" button
   ```

**✅ Success Criteria:**
- Login succeeds (no error message)
- Automatically redirected to change password page
- Cannot access dashboard without changing password

---

### Test Case 3: Password Policy Validation

**Objective:** Verify password policy is enforced

**Steps:**

1. **Test Invalid Passwords**

   Try each password below and verify it's **rejected**:

   | Password | Expected Error |
   |----------|----------------|
   | `short` | "Password must be at least 8 characters..." |
   | `alllowercase123!` | "Password must be at least 8 characters..." |
   | `ALLUPPERCASE123!` | "Password must be at least 8 characters..." |
   | `NoDigitsHere!` | "Password must be at least 8 characters..." |
   | `NoSpecial123` | "Password must be at least 8 characters..." |

   **How to test:**
   ```
   On /change-password page:
   1. Enter invalid password in both fields
   2. Click "Set password"
   3. Verify error message appears
   4. Verify password is NOT changed
   ```

2. **Test Valid Password**

   ```
   New Password:     ValidPass123!
   Confirm Password: ValidPass123!
   Click: "Set password"
   ```

**✅ Success Criteria:**
- Invalid passwords are rejected with clear error message
- Valid password is accepted
- Success message appears
- Redirected to dashboard

---

### Test Case 4: Verify Password Change Persisted

**Objective:** Verify password change is saved and flag is cleared

**Steps:**

1. **Check Database**
   ```sql
   SELECT full_name, email, must_reset_password 
   FROM faculty 
   WHERE email = 'testfaculty@test.com';
   
   Expected:
   ┌──────────────────────┬────────────────────────┬────────────────────────┐
   │ full_name            │ email                  │ must_reset_password    │
   ├──────────────────────┼────────────────────────┼────────────────────────┤
   │ Test Faculty User    │ testfaculty@test.com   │ false                  │
   └──────────────────────┴────────────────────────┴────────────────────────┘
   ```

2. **Verify Dashboard Access**
   ```
   Current page: Should be faculty dashboard
   URL: http://localhost:5000/faculty/dashboard
   No password change prompt
   ```

3. **Logout and Re-login**
   ```
   1. Logout
   2. Login with:
      Email: testfaculty@test.com
      Password: ValidPass123!
   3. Should go directly to dashboard (no password change prompt)
   ```

**✅ Success Criteria:**
- `must_reset_password` is `false` in database
- User can access dashboard
- Re-login doesn't prompt for password change
- Old temporary password no longer works

---

### Test Case 5: Admin Role Testing

**Objective:** Verify admin accounts work correctly

**Steps:**

1. **Create Admin Account**
   ```
   Login as existing admin
   Go to: /admin/faculty
   Add Faculty:
   ┌─────────────────────────────────────┐
   │ Full Name:     Test Admin User      │
   │ Abbreviation:  TAU                  │
   │ Email:         testadmin@test.com   │
   │ Role:          admin                │
   └─────────────────────────────────────┘
   ```

2. **Login as New Admin**
   ```
   Logout
   Login with temporary password
   Change password
   ```

3. **Verify Admin Access**
   ```
   Should see:
   - Admin dashboard (not faculty dashboard)
   - Admin menu items
   - Access to /admin/* routes
   ```

**✅ Success Criteria:**
- Admin account created successfully
- Admin can access admin dashboard
- Admin can access all admin routes

---

## 🐛 Troubleshooting Guide

### Issue: "Firebase is not configured"

**Symptoms:**
- Login button disabled
- Error message on login page

**Solution:**
```bash
# 1. Check .env file exists
ls -la TT-Generator/.env

# 2. Verify Firebase config
cat TT-Generator/.env | grep FIREBASE

# 3. Ensure all Firebase variables are set
FIREBASE_API_KEY=...
FIREBASE_AUTH_DOMAIN=...
FIREBASE_PROJECT_ID=...
# etc.

# 4. Restart Flask app
```

---

### Issue: "User not registered in the system"

**Symptoms:**
- Login succeeds in Firebase
- Error message after token verification

**Solution:**
```sql
-- Check if user exists in database
SELECT * FROM faculty WHERE email = 'user@example.com';

-- If not found, create via admin panel
-- Or manually insert:
INSERT INTO faculty (full_name, abbreviation, email, firebase_uid, role, must_reset_password)
VALUES ('User Name', 'UN', 'user@example.com', '[Firebase UID]', 'faculty', false);
```

---

### Issue: "Token verification failed"

**Symptoms:**
- Login fails after entering credentials
- Error in Flask console

**Solution:**
```bash
# 1. Check firebase-credentials.json exists
ls -la TT-Generator/firebase-credentials.json

# 2. Verify credentials are valid
# Download fresh credentials from Firebase Console

# 3. Check system time (clock skew)
date

# 4. Restart Flask app
```

---

### Issue: Can't remember temporary password

**Symptoms:**
- Admin created account but didn't save password
- User can't login

**Solutions:**

**Option 1: Reset in Firebase Console**
```
1. Go to Firebase Console → Authentication → Users
2. Find user by email
3. Click three dots → Reset password
4. Enter new password (can be 6+ chars in console)
5. User can login with this password
6. Will still be prompted to change password in app
```

**Option 2: Recreate Account**
```
1. Delete user from Firebase Console
2. Delete from database: DELETE FROM faculty WHERE email = '...';
3. Create new account via admin panel
4. Save temporary password this time
```

---

### Issue: Password policy not enforced

**Symptoms:**
- Weak passwords accepted
- No validation errors

**Solution:**
```bash
# 1. Test password policy
python test_firebase_auth.py

# 2. Check regex in routes/auth.py
grep "policy = " routes/auth.py

# 3. Check JavaScript in templates/change_password.html
grep "policy = " templates/change_password.html

# 4. Verify both match:
# ^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$
```

---

## 📊 Testing Checklist

Use this checklist to track your testing progress:

### Setup
- [ ] Flask app running
- [ ] Firebase configured in `.env`
- [ ] Database initialized
- [ ] Admin account exists

### Password Generation
- [ ] Run `test_firebase_auth.py`
- [ ] Verify generated passwords are valid
- [ ] Verify invalid passwords are rejected

### Account Creation
- [ ] Admin can create faculty account
- [ ] Temporary password displayed
- [ ] User appears in Firebase Console
- [ ] User appears in database
- [ ] `must_reset_password` is `true`

### First Login
- [ ] User can login with temporary password
- [ ] Redirected to change password page
- [ ] Cannot access dashboard without changing password

### Password Change
- [ ] Invalid passwords rejected (< 8 chars)
- [ ] Invalid passwords rejected (no uppercase)
- [ ] Invalid passwords rejected (no lowercase)
- [ ] Invalid passwords rejected (no digit)
- [ ] Invalid passwords rejected (no special)
- [ ] Valid password accepted
- [ ] Success message shown
- [ ] Redirected to dashboard

### Post-Change
- [ ] `must_reset_password` is `false` in database
- [ ] User can access dashboard
- [ ] User can logout and re-login
- [ ] No password change prompt on re-login
- [ ] Old temporary password doesn't work

### Admin Testing
- [ ] Admin account created
- [ ] Admin can access admin dashboard
- [ ] Admin can access admin routes
- [ ] Faculty cannot access admin routes

---

## 🎯 Expected Test Results Summary

| Test | Expected Result | Pass/Fail |
|------|----------------|-----------|
| Generate temp password | 12 chars, meets policy | ⬜ |
| Create faculty account | Success message with password | ⬜ |
| Firebase Console shows user | User visible | ⬜ |
| Database has user | Record with `must_reset_password=true` | ⬜ |
| Login with temp password | Redirect to change password | ⬜ |
| Reject weak password | Error message shown | ⬜ |
| Accept strong password | Success, redirect to dashboard | ⬜ |
| Database flag cleared | `must_reset_password=false` | ⬜ |
| Re-login with new password | Direct to dashboard | ⬜ |
| Old password doesn't work | Login fails | ⬜ |

---

## 📞 Need Help?

If tests fail:

1. **Check Flask Console**
   - Look for Python errors
   - Check Firebase initialization messages

2. **Check Browser Console**
   - Look for JavaScript errors
   - Check network requests (F12 → Network tab)

3. **Check Firebase Console**
   - Verify users are created
   - Check authentication logs

4. **Check Database**
   - Verify faculty records exist
   - Check `must_reset_password` flag

5. **Review Code**
   - `routes/auth.py` - Authentication logic
   - `routes/admin.py` - Account creation
   - `templates/login.html` - Login form
   - `templates/change_password.html` - Password change

---

**Happy Testing! 🚀**
