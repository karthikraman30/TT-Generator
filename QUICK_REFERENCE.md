# 🚀 Quick Reference Card - Firebase Authentication

## 📋 Password Policy

```
Minimum: 8 characters
Required:
  ✓ At least 1 uppercase (A-Z)
  ✓ At least 1 lowercase (a-z)
  ✓ At least 1 digit (0-9)
  ✓ At least 1 special (!@#$%^&*)

Regex: ^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$
```

**Valid Examples:**
- `ValidPass123!`
- `MyP@ssw0rd`
- `Secure#2024`

**Invalid Examples:**
- `short` (too short)
- `alllowercase123!` (no uppercase)
- `ALLUPPERCASE123!` (no lowercase)
- `NoDigitsHere!` (no digit)
- `NoSpecial123` (no special)

---

## 🔑 Admin Creates Faculty Account

```bash
# 1. Login as admin
URL: http://localhost:5000/login
Method: Dev Login or Firebase Login

# 2. Navigate to Faculty Management
URL: http://localhost:5000/admin/faculty

# 3. Click "Add Faculty"
Fill:
  - Full Name: [Name]
  - Abbreviation: [Short code]
  - Email: [email@domain.com]
  - Role: faculty or admin

# 4. Copy temporary password from success message
Example: "Temporary password: aB3!xYz9Qw12"
⚠️ SAVE THIS - shown only once!
```

---

## 👤 User First Login

```bash
# 1. Go to login page
URL: http://localhost:5000/login

# 2. Enter credentials
Email: [email from admin]
Password: [temporary password]

# 3. Automatic redirect to change password
URL: http://localhost:5000/change-password

# 4. Set new password (must meet policy)
New Password: [8+ chars with complexity]
Confirm: [same password]

# 5. Redirected to dashboard
Faculty: /faculty/dashboard
Admin: /admin/dashboard
```

---

## 🧪 Testing Commands

```bash
# Test password policy
cd TT-Generator
python test_firebase_auth.py

# Start Flask app
python app.py

# Check database
sqlite3 timetable.db
SELECT email, must_reset_password FROM faculty;
```

---

## 🔍 Database Queries

```sql
-- Check all faculty accounts
SELECT full_name, email, role, must_reset_password 
FROM faculty;

-- Check specific user
SELECT * FROM faculty 
WHERE email = 'user@example.com';

-- Force password reset
UPDATE faculty 
SET must_reset_password = true 
WHERE email = 'user@example.com';

-- Check who needs to reset password
SELECT full_name, email 
FROM faculty 
WHERE must_reset_password = true;
```

---

## 🔥 Firebase Console

```
URL: https://console.firebase.google.com/

Navigation:
1. Select your project
2. Authentication → Users
3. View all created users

Manual User Creation (Testing Only):
1. Click "Add User"
2. Enter email + password (6+ chars)
3. Note: This bypasses your app's policy
```

---

## 📁 Important Files

```
Configuration:
  .env                          # Firebase credentials
  firebase-credentials.json     # Service account key

Code:
  routes/auth.py                # Login, password change
  routes/admin.py               # User creation
  models.py                     # Database schema

Templates:
  templates/login.html          # Login page
  templates/change_password.html # Password change page

Testing:
  test_firebase_auth.py         # Password policy tester
  FIREBASE_AUTH_ANALYSIS.md     # Full documentation
  TESTING_GUIDE.md              # Step-by-step tests
```

---

## 🐛 Common Issues

### "Firebase is not configured"
```bash
# Check .env file
cat .env | grep FIREBASE

# Verify all variables set
FIREBASE_API_KEY=...
FIREBASE_AUTH_DOMAIN=...
FIREBASE_PROJECT_ID=...
```

### "User not registered in the system"
```sql
-- Check if user exists
SELECT * FROM faculty WHERE email = 'user@example.com';

-- If not, create via admin panel
```

### "Token verification failed"
```bash
# Check credentials file
ls -la firebase-credentials.json

# Restart Flask app
```

### Can't remember temporary password
```
Option 1: Reset in Firebase Console
  → Authentication → Users → [User] → Reset password

Option 2: Recreate account
  → Delete from Firebase + Database
  → Create new via admin panel
```

---

## 🎯 Testing Checklist

Quick test sequence:

```
□ Run test_firebase_auth.py
□ Login as admin
□ Create test faculty account
□ Copy temporary password
□ Logout
□ Login with temporary password
□ Verify redirect to change password
□ Try invalid password (should fail)
□ Set valid password (should succeed)
□ Verify redirect to dashboard
□ Logout and re-login
□ Verify no password change prompt
```

---

## 📞 Quick Help

**Password not working?**
- Check if it meets policy (8+ chars, upper, lower, digit, special)
- Run `python test_firebase_auth.py` to test

**Can't create user?**
- Check Firebase credentials in `.env`
- Verify `firebase-credentials.json` exists
- Check Flask console for errors

**User can't login?**
- Verify user exists in Firebase Console
- Check database for matching email
- Verify `firebase_uid` is set

**Password change not working?**
- Check browser console for JavaScript errors
- Verify password meets policy
- Check Flask console for backend errors

---

## 🔗 Documentation Links

- **Full Analysis:** `FIREBASE_AUTH_ANALYSIS.md`
- **Testing Guide:** `TESTING_GUIDE.md`
- **Console vs App:** `FIREBASE_CONSOLE_VS_APP.md`
- **This Reference:** `QUICK_REFERENCE.md`

---

## 💡 Pro Tips

1. **Always save temporary passwords** when creating accounts
2. **Use test_firebase_auth.py** to validate passwords before trying
3. **Check Firebase Console** to verify users are created
4. **Check database** to verify `must_reset_password` flag
5. **Use dev login** for quick testing without Firebase
6. **Create test accounts** with obvious names (Test User, etc.)
7. **Document passwords** in a secure password manager

---

## 🎓 Key Concepts

**Temporary Password:**
- Generated by admin panel
- 12 characters, meets policy
- Shown only once
- User must change on first login

**must_reset_password Flag:**
- Set to `true` when account created
- Forces password change on first login
- Cleared after successful password change
- Stored in database, not Firebase

**Password Policy:**
- Enforced by YOUR code, not Firebase
- Validated client-side (JavaScript)
- Validated server-side (Python)
- Firebase accepts any password via Admin SDK

**Two Login Methods:**
- Firebase Login: Production method
- Dev Login: Testing method (bypass Firebase)

---

**Last Updated:** April 26, 2026
**Version:** 1.0

---

**Need more details?** See the full documentation files! 📚
