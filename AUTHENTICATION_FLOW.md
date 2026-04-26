# 🔄 Authentication Flow Diagrams

## 📊 Visual Guide to Your Firebase Authentication System

---

## 1️⃣ Admin Creates Faculty Account

```
┌─────────────────────────────────────────────────────────────────┐
│                        ADMIN PANEL                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Admin fills form │
                    │ - Full Name      │
                    │ - Abbreviation   │
                    │ - Email          │
                    │ - Role           │
                    └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION CODE                        │
│                    (routes/admin.py)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Generate Temp Password       │
                │ _generate_temp_password(12)  │
                │                              │
                │ Example: "aB3!xYz9Qw12"      │
                │                              │
                │ ✓ 12 characters              │
                │ ✓ 1 uppercase                │
                │ ✓ 1 lowercase                │
                │ ✓ 1 digit                    │
                │ ✓ 1 special                  │
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FIREBASE ADMIN SDK                           │
│                    firebase_auth.create_user()                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Firebase creates user        │
                │ - Email: user@example.com    │
                │ - Password: aB3!xYz9Qw12     │
                │ - UID: xyz123abc456          │
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR DATABASE                                │
│                    (faculty table)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ INSERT INTO faculty          │
                │ - full_name                  │
                │ - abbreviation               │
                │ - email                      │
                │ - firebase_uid: xyz123abc456 │
                │ - role: faculty              │
                │ - must_reset_password: TRUE  │
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ADMIN SEES SUCCESS                           │
│                                                                 │
│  ✅ Faculty "User Name" added.                                  │
│     Temporary password: aB3!xYz9Qw12                            │
│                                                                 │
│  ⚠️  SAVE THIS PASSWORD - shown only once!                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ User First Login

```
┌─────────────────────────────────────────────────────────────────┐
│                        LOGIN PAGE                               │
│                    (templates/login.html)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ User enters:                 │
                │ - Email: user@example.com    │
                │ - Password: aB3!xYz9Qw12     │
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FIREBASE CLIENT SDK                          │
│                    (JavaScript in browser)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ signInWithEmailAndPassword() │
                │                              │
                │ Firebase verifies:           │
                │ ✓ Email exists               │
                │ ✓ Password matches           │
                └──────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Firebase returns:            │
                │ - ID Token (JWT)             │
                │ - User UID                   │
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR BACKEND                                 │
│                    (routes/auth.py - verify_token)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Verify ID Token              │
                │ firebase_auth.verify_id_token│
                │                              │
                │ ✓ Token is valid             │
                │ ✓ Not expired                │
                │ ✓ Signed by Firebase         │
                └──────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Look up user in database     │
                │ SELECT * FROM faculty        │
                │ WHERE firebase_uid = '...'   │
                └──────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Check must_reset_password    │
                │                              │
                │ If TRUE:                     │
                │   → Redirect to /change-pwd  │
                │                              │
                │ If FALSE:                    │
                │   → Redirect to dashboard    │
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CHANGE PASSWORD PAGE                         │
│                    (First login only)                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3️⃣ Password Change Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHANGE PASSWORD PAGE                         │
│                    (templates/change_password.html)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ User enters:                 │
                │ - New Password: ValidPass123!│
                │ - Confirm: ValidPass123!     │
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT-SIDE VALIDATION                       │
│                    (JavaScript)                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Validate with regex:         │
                │ /^(?=.*[a-z])(?=.*[A-Z])     │
                │   (?=.*\d)(?=.*[^A-Za-z0-9]) │
                │   .{8,}$/                    │
                │                              │
                │ ✓ Length >= 8                │
                │ ✓ Has uppercase              │
                │ ✓ Has lowercase              │
                │ ✓ Has digit                  │
                │ ✓ Has special                │
                └──────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Valid?           │
                    └──────────────────┘
                       │           │
                   NO  │           │  YES
                       ▼           ▼
            ┌──────────────┐   ┌──────────────┐
            │ Show error   │   │ Submit form  │
            │ Don't submit │   │ to backend   │
            └──────────────┘   └──────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SERVER-SIDE VALIDATION                       │
│                    (routes/auth.py - change_password)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Validate with regex (again): │
                │ ^(?=.*[a-z])(?=.*[A-Z])      │
                │  (?=.*\d)(?=.*[^A-Za-z0-9])  │
                │  .{8,}$                      │
                │                              │
                │ ✓ Double-check all rules     │
                └──────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Valid?           │
                    └──────────────────┘
                       │           │
                   NO  │           │  YES
                       ▼           ▼
            ┌──────────────┐   ┌──────────────┐
            │ Return error │   │ Update       │
            │ to user      │   │ Firebase     │
            └──────────────┘   └──────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FIREBASE ADMIN SDK                           │
│                    firebase_auth.update_user()                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Firebase updates password    │
                │ - UID: xyz123abc456          │
                │ - New Password: ValidPass123!│
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR DATABASE                                │
│                    UPDATE faculty                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ UPDATE faculty               │
                │ SET must_reset_password=FALSE│
                │ WHERE id = ...               │
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SUCCESS                                      │
│                                                                 │
│  ✅ Password updated successfully                               │
│     Redirecting to dashboard...                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4️⃣ Subsequent Logins

```
┌─────────────────────────────────────────────────────────────────┐
│                        LOGIN PAGE                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ User enters:                 │
                │ - Email: user@example.com    │
                │ - Password: ValidPass123!    │
                │   (new password)             │
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FIREBASE CLIENT SDK                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ signInWithEmailAndPassword() │
                │ ✓ Credentials valid          │
                │ → Returns ID Token           │
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR BACKEND                                 │
│                    (routes/auth.py - verify_token)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Verify token                 │
                │ Look up user in database     │
                │                              │
                │ Check must_reset_password    │
                │ → FALSE (already changed)    │
                └──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DASHBOARD                                    │
│                    (Direct access, no password change)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5️⃣ Password Policy Enforcement

```
┌─────────────────────────────────────────────────────────────────┐
│                    PASSWORD VALIDATION                          │
│                    (Two-Layer Defense)                          │
└─────────────────────────────────────────────────────────────────┘

                    User enters password
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │         LAYER 1: CLIENT-SIDE            │
        │         (JavaScript in browser)         │
        └─────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Regex validation:            │
                │ ^(?=.*[a-z])(?=.*[A-Z])      │
                │  (?=.*\d)(?=.*[^A-Za-z0-9])  │
                │  .{8,}$                      │
                └──────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                INVALID             VALID
                    │                   │
                    ▼                   ▼
        ┌──────────────────┐  ┌──────────────────┐
        │ Show error       │  │ Allow submit     │
        │ Block submission │  │ Send to server   │
        └──────────────────┘  └──────────────────┘
                                        │
                                        ▼
        ┌─────────────────────────────────────────┐
        │         LAYER 2: SERVER-SIDE            │
        │         (Python in Flask)               │
        └─────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Regex validation (again):    │
                │ ^(?=.*[a-z])(?=.*[A-Z])      │
                │  (?=.*\d)(?=.*[^A-Za-z0-9])  │
                │  .{8,}$                      │
                └──────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                INVALID             VALID
                    │                   │
                    ▼                   ▼
        ┌──────────────────┐  ┌──────────────────┐
        │ Return 400 error │  │ Update Firebase  │
        │ Flash message    │  │ Update database  │
        └──────────────────┘  └──────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    WHY TWO LAYERS?                              │
│                                                                 │
│  Client-side: Fast feedback, better UX                         │
│  Server-side: Security enforcement, can't be bypassed          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6️⃣ Firebase Console vs Your App

```
┌─────────────────────────────────────────────────────────────────┐
│                    FIREBASE CONSOLE                             │
│                    (Manual User Creation)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ You manually enter:          │
                │ - Email: user@example.com    │
                │ - Password: abc123           │
                │   (6 chars, no complexity)   │
                └──────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Firebase Console validates:  │
                │ ✓ Length >= 6                │
                │ ✗ No complexity check        │
                │                              │
                │ → User created ✅            │
                └──────────────────────────────┘

                              VS

┌─────────────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                             │
│                    (Programmatic Creation)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Your code generates:         │
                │ - Email: user@example.com    │
                │ - Password: aB3!xYz9Qw12     │
                │   (12 chars, meets policy)   │
                └──────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Your code validates:         │
                │ ✓ Length >= 8                │
                │ ✓ Has uppercase              │
                │ ✓ Has lowercase              │
                │ ✓ Has digit                  │
                │ ✓ Has special                │
                └──────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │ Firebase Admin SDK:          │
                │ create_user(                 │
                │   email='...',               │
                │   password='aB3!xYz9Qw12'    │
                │ )                            │
                │                              │
                │ → User created ✅            │
                └──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    KEY DIFFERENCE                               │
│                                                                 │
│  Console: Firebase enforces 6+ chars (UI validation)           │
│  Your App: YOU enforce 8+ chars + complexity (code validation) │
│                                                                 │
│  Firebase Admin SDK trusts your server-side code!              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7️⃣ Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ADMIN                                    │
│                    (Web Browser)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Creates faculty account
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR FLASK APP                               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ routes/admin.py                                          │  │
│  │ - add_faculty()                                          │  │
│  │ - _generate_temp_password()                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              │ Creates user                     │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Firebase Admin SDK                                       │  │
│  │ - firebase_auth.create_user()                            │  │
│  │ - firebase_auth.update_user()                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              │ Stores user                      │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Database (SQLite/PostgreSQL)                             │  │
│  │ - faculty table                                          │  │
│  │ - must_reset_password flag                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Sends temp password
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ADMIN                                    │
│                    (Sees temp password)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Shares with faculty
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FACULTY USER                             │
│                    (Web Browser)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Logs in
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FIREBASE CLIENT SDK                          │
│                    (JavaScript in browser)                      │
│                                                                 │
│  - signInWithEmailAndPassword()                                 │
│  - Returns ID Token                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Sends token
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR FLASK APP                               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ routes/auth.py                                           │  │
│  │ - verify_token()                                         │  │
│  │ - change_password()                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              │ Verifies token                   │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Firebase Admin SDK                                       │  │
│  │ - firebase_auth.verify_id_token()                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              │ Checks flag                      │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Database                                                 │  │
│  │ - Check must_reset_password                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              │ If TRUE                          │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Redirect to /change-password                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ User changes password
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR FLASK APP                               │
│                                                                 │
│  1. Validate password (YOUR policy)                             │
│  2. Update Firebase (Admin SDK)                                 │
│  3. Clear must_reset_password flag                              │
│  4. Redirect to dashboard                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Points

### 1. Two-Layer Validation
- **Client-side:** Fast feedback, better UX
- **Server-side:** Security enforcement, can't be bypassed

### 2. Firebase is Storage, Not Enforcer
- Firebase stores credentials
- YOUR code enforces password policy
- Firebase Admin SDK trusts your code

### 3. must_reset_password Flag
- Set to TRUE when account created
- Checked on every login
- Cleared after successful password change
- Stored in YOUR database, not Firebase

### 4. Temporary Password
- Generated by YOUR code (12 chars)
- Meets YOUR policy (not Firebase's)
- Shown only once to admin
- User must change on first login

---

**Need more details?** See the full documentation files! 📚
