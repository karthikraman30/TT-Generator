# 🎓 University Timetable Generator

> Automated university timetable scheduling using **CSP (Constraint Satisfaction Problem)** solving with **PostgreSQL** database and a **Flask web dashboard**.

---

## 🔧 What You Need

| Tool | Install Link |
|------|-------------|
| **Python 3.8+** | [python.org/downloads](https://www.python.org/downloads/) |
| **PostgreSQL 14+** | See Step 3 below |

---

## 🚀 Setup Guide (Follow in Order)

### Step 1: Open Terminal and Go to the Project Folder

```bash
# macOS / Linux
cd path/to/"SPM - Copy"

# Windows (Command Prompt)
cd "C:\path\to\SPM - Copy"
```

---

### Step 2: Create Virtual Environment & Install Packages

```bash
# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate          # Windows

# Install all dependencies
pip install -r requirements.txt
```

> **IMPORTANT:** You MUST run `source venv/bin/activate` every time you open a new terminal window before running any commands. You'll see `(venv)` appear at the start of your prompt when it's active.

> **Windows users:** Use `python` instead of `python3` and `venv\Scripts\activate` instead of `source venv/bin/activate`.

---

### Step 3: Install PostgreSQL

#### macOS (Homebrew — recommended):
```bash
brew install postgresql@16
brew services start postgresql@16
```
*Don't have Homebrew? → https://brew.sh or use the [official installer](https://www.postgresql.org/download/macosx/)*

#### Windows:
1. Download from https://www.postgresql.org/download/windows/
2. Run the installer → **use default port 5432**
3. **Set a password** for the `postgres` user (remember it!)
4. ✅ Check **"pgAdmin 4"** during installation

#### Linux (Ubuntu/Debian):
```bash
sudo apt update && sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

---

### Step 4: Create the Database

#### macOS (Homebrew):
```bash
createdb timetable_generator_db
```

#### macOS (Installer) / Windows / Linux:
```bash
psql -U postgres -c "CREATE DATABASE timetable_generator_db;"
```
*(Enter your PostgreSQL password when prompted)*

> **Windows:**
> - If `psql` is not found, use the full path and the PowerShell call operator:
>   ```powershell
>   & "C:\Program Files\PostgreSQL\$(Number)\bin\psql.exe" -U postgres -c "CREATE DATABASE timetable_generator_db;"
>   ```
> - If using Command Prompt (cmd.exe), you can use:
>   ```cmd
>   "C:\Program Files\PostgreSQL\$(Number)\bin\psql.exe" -U postgres -c "CREATE DATABASE timetable_generator_db;"
>   ```

---

### Step 5: Load the Schema & Seed Data

Run these 3 commands in order (make sure you're in the `SPM - Copy` folder):

#### macOS (Homebrew):
```bash
psql -d timetable_generator_db -f database/init_schema.sql
psql -d timetable_generator_db -f database/seed_constraints.sql
psql -d timetable_generator_db -f database/seed_time_slots.sql
```

#### Windows / macOS (Installer) / Linux:
```bash
psql -U postgres -d timetable_generator_db -f database/init_schema.sql
psql -U postgres -d timetable_generator_db -f database/seed_constraints.sql
psql -U postgres -d timetable_generator_db -f database/seed_time_slots.sql
```

You should see output like:
```
CREATE TABLE
CREATE TABLE
...
CREATE VIEW
INSERT 0 11
INSERT 0 25
```

---

### Step 6: Configure Your Database Credentials

```bash
cp .env.example .env
```

Now open `.env` in any text editor and set your values:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=timetable_generator_db
DB_USER=postgres
DB_PASSWORD=your_password_here
```

> **macOS Homebrew users:** Your username is your Mac username (run `whoami` to check), password is blank, port is `5432`.

---

### Step 7: Run the Timetable Generator

Make sure you've activated the virtual environment first (`source venv/bin/activate`), then:

```bash
python3 generate_timetable.py \
  --input Slots_Win_2025-26_15Dec2025.xlsx \
  --reference "Lecture_Time_Table_Win'26_v6.xlsx" \
  --use-db
```

> **Windows:** Use `python` instead of `python3`

#### ✅ Expected Output:
```
============================================================
  University Timetable Generator
  [Database Mode: PostgreSQL mirroring enabled]
============================================================

[1/9] Loading slot matrix...
[2/9] Parsing input...
  Parsed 257 course entries.
[3/9] Connecting to PostgreSQL...
  ✓ Connected to timetable_generator_db@localhost:5432
[4/9] Mirroring input data to database...
  ✓ 76 faculty, 91 courses, 21 rooms, 75 batches loaded
  ✓ 99 faculty-course mappings, 257 batch-course mappings created
[5/9] Building conflict graph...
  89 superblocks, 366 conflict edges.
[6/9] Solving schedule (CSP + backtracking)...
  CSP solved: 89 superblocks assigned (0 unresolved).
[7/9] Optimising soft constraints...
[8/9] Applying assignments & validating...
  ✓ All hard constraints satisfied!
[8/9] Writing results to database...
  ✓ 288 timetable entries written to Master_Timetable
  ✓ All hard constraints satisfied!
[9/9] Exporting...
  Excel saved: 'Generated_Master_Timetable.xlsx'
  PDF saved:   'Generated_Master_Timetable.pdf'
============================================================
```

---

### Step 8: Launch the Web Dashboard

```bash
python3 app.py
```

Open your browser → **http://localhost:5000**

| Page | What It Shows |
|------|--------------|
| 📊 **Dashboard** | Database stats — 76 faculty, 91 courses, 288 schedule entries |
| 📅 **Master Timetable** | Full schedule with filters for day, batch, and faculty |
| 👨‍🏫 **Faculty Schedule** | Per-faculty teaching timetable |
| 🏫 **Room Utilization** | Room usage percentages across all slots |
| 🔒 **Constraints** | All 11 scheduling rules (8 HARD + 3 SOFT) |
| ⚠️ **Violation Log** | Audit trail of constraint violations |

---

### Step 9: Browse the Database in pgAdmin (Optional)

pgAdmin is a GUI to visually explore the database tables.

1. Open **pgAdmin 4** (installed with PostgreSQL)
2. Right-click **"Servers"** → **"Register"** → **"Server..."**
3. **General tab** → Name: `Timetable Generator`
4. **Connection tab:**
   - Host: `localhost`
   - Port: `5432`
   - Database: `timetable_generator_db`
   - Username: `postgres`
   - Password: *(your password)*
5. Click **Save**
6. Expand: `Timetable Generator → Databases → timetable_generator_db → Schemas → public → Tables`
7. Right-click any table → **"View/Edit Data"** → **"All Rows"**

---

## ⚡ Quick Start (After Initial Setup)

Every time you open a new terminal to work with the project:

```bash
# 1. Go to project folder
cd path/to/"SPM - Copy"

# 2. Activate virtual environment (REQUIRED every new terminal!)
source venv/bin/activate     # macOS/Linux
# venv\Scripts\activate       # Windows

# 3. Make sure PostgreSQL is running
# macOS Homebrew:
brew services start postgresql@16
# Linux:
sudo systemctl start postgresql

# 4. Run the solver
python3 generate_timetable.py --input Slots_Win_2025-26_15Dec2025.xlsx --reference "Lecture_Time_Table_Win'26_v6.xlsx" --use-db

# 5. Launch web dashboard
python3 app.py
# → Open http://localhost:5000
```

---

## 📁 Project Structure

```
SPM - Copy/
├── generate_timetable.py       ← Core CSP solver engine
├── db_manager.py               ← PostgreSQL database layer
├── app.py                      ← Flask web dashboard
├── requirements.txt            ← Python dependencies
├── .env.example                ← Database config template
│
├── database/
│   ├── init_schema.sql         ← 10 tables + 3 views + indexes
│   ├── seed_constraints.sql    ← 11 scheduling rules
│   └── seed_time_slots.sql     ← 25 time slots (Mon–Fri)
│
├── Slots_Win_2025-26_15Dec2025.xlsx    ← INPUT data
├── Lecture_Time_Table_Win'26_v6.xlsx   ← Slot reference matrix
│
├── Generated_Master_Timetable.xlsx     ← OUTPUT (Excel)
└── Generated_Master_Timetable.pdf      ← OUTPUT (PDF)
```

> **Note:** The `venv/` folder, `.env`, and `__pycache__/` are NOT included when sharing — your friend creates their own in Step 2 and Step 6.

---

## ❓ Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'pandas'` | Activate venv first: `source venv/bin/activate` |
| `source: no such file or directory: venv/bin/activate` | You're in the wrong folder. Run `cd path/to/"SPM - Copy"` first |
| `could not connect to server` | Make sure PostgreSQL is running (see Step 3) |
| `database 'timetable_generator_db' does not exist` | Run Step 4 again |
| `password authentication failed` | Check your `.env` file — make sure `DB_PASSWORD` is correct |
| `psql: command not found` (Windows) | Use full path: `"C:\Program Files\PostgreSQL\16\bin\psql.exe"` |
| `role "postgres" does not exist` (macOS Homebrew) | Change `DB_USER` in `.env` to your Mac username (run `whoami`) |
| Port 5000 already in use | `pkill -f "python.*app.py"` then retry, OR on macOS disable AirPlay Receiver in System Settings |

---

## 🏗 Database Tables (10 Total)

| Table | Purpose | Rows |
|-------|---------|------|
| `faculty` | Teaching staff | 76 |
| `course` | Course catalogue with L-T-P-C | 91 |
| `student_batch` | Student cohorts | 75 |
| `room` | Classrooms with capacity | 21 |
| `time_slot` | 25 scheduling periods | 25 |
| `faculty_course_map` | Faculty ↔ Course pairings | 99 |
| `batch_course_map` | Batch ↔ Course enrollments | 257 |
| `master_timetable` | **Generated schedule (fact table)** | 288 |
| `scheduling_constraint` | Toggleable scheduling rules | 11 |
| `constraint_violation_log` | Violation audit trail | 0 ✓ |
