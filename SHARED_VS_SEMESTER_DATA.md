# 🗄️ Shared vs Semester-Specific Data

## ❓ Your Question

> "I created a new semester (Summer) and uploaded files. When I check `SELECT * FROM faculty` in pgAdmin, it still shows the old data from Winter. Why?"

## ✅ Answer: This is CORRECT Behavior!

**Faculty is SHARED across all semesters!**

---

## 📊 Database Structure: Two Types of Data

### Type 1: SHARED Data (No semester_id)
**Same data used by ALL semesters**

```sql
-- Faculty Table (NO semester_id column)
CREATE TABLE faculty (
    id INTEGER PRIMARY KEY,
    full_name VARCHAR(200),
    abbreviation VARCHAR(50),
    email VARCHAR(200),
    role VARCHAR(20)
    -- ❌ NO semester_id column!
);

-- Rooms Table (NO semester_id column)
CREATE TABLE rooms (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50),
    capacity INTEGER,
    building VARCHAR(100)
    -- ❌ NO semester_id column!
);

-- Programs Table (NO semester_id column)
CREATE TABLE programs (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    code VARCHAR(30),
    degree_type VARCHAR(20)
    -- ❌ NO semester_id column!
);
```

**Why?** Because these resources are permanent:
- Professors don't disappear between semesters
- Classrooms don't change between semesters
- Degree programs are permanent

---

### Type 2: SEMESTER-SPECIFIC Data (Has semester_id)
**Different data for each semester**

```sql
-- Courses Table (HAS semester_id column)
CREATE TABLE courses (
    id INTEGER PRIMARY KEY,
    code VARCHAR(20),
    name VARCHAR(250),
    semester_id INTEGER,  -- ✅ Links to specific semester
    FOREIGN KEY (semester_id) REFERENCES semesters(id)
);

-- Batches Table (HAS semester_id column)
CREATE TABLE batches (
    id INTEGER PRIMARY KEY,
    name VARCHAR(150),
    semester_id INTEGER,  -- ✅ Links to specific semester
    FOREIGN KEY (semester_id) REFERENCES semesters(id)
);

-- Timetable Entries (HAS semester_id column)
CREATE TABLE timetable_entries (
    id INTEGER PRIMARY KEY,
    course_id INTEGER,
    semester_id INTEGER,  -- ✅ Links to specific semester
    FOREIGN KEY (semester_id) REFERENCES semesters(id)
);

-- Slots Table (HAS semester_id column)
CREATE TABLE slots (
    id INTEGER PRIMARY KEY,
    slot_label VARCHAR(20),
    semester_id INTEGER,  -- ✅ Links to specific semester
    FOREIGN KEY (semester_id) REFERENCES semesters(id)
);
```

**Why?** Because these change every semester:
- Different courses offered each semester
- Different student batches each semester
- Different timetable each semester
- Slot structure might change

---

## 🎯 Real-World Example

### Scenario: Winter 2025-26 → Summer 2026

**SHARED Data (Same in both semesters):**

```sql
-- Faculty Table
SELECT * FROM faculty;
```

| id | full_name | abbreviation | email |
|----|-----------|--------------|-------|
| 1 | Dr. Smith | DS | ds@uni.edu |
| 2 | Dr. Jones | DJ | dj@uni.edu |
| 3 | Dr. Brown | DB | db@uni.edu |

**This is the SAME for both Winter and Summer!**
- Dr. Smith teaches in Winter ✅
- Dr. Smith teaches in Summer ✅
- Same faculty, different courses

---

**SEMESTER-SPECIFIC Data (Different per semester):**

```sql
-- Courses Table
SELECT * FROM courses;
```

| id | code | name | semester_id |
|----|------|------|-------------|
| 1 | CS101 | Intro to CS | 1 (Winter) |
| 2 | CS102 | Data Structures | 1 (Winter) |
| 3 | CS201 | Algorithms | 2 (Summer) |
| 4 | CS202 | Databases | 2 (Summer) |

**Different courses for each semester!**
- Winter has CS101, CS102
- Summer has CS201, CS202

---

## 🔍 What Happens When You Upload Files

### When You Upload to Summer Semester:

**1. Faculty Mapping File Upload**
```python
# In excel_parser.py
def parse_faculty_mapping(filepath):
    # Reads faculty from Excel
    for row in excel:
        faculty = Faculty.query.filter_by(abbreviation=row['abbr']).first()
        if not faculty:
            # Create NEW faculty (no semester_id)
            faculty = Faculty(
                full_name=row['name'],
                abbreviation=row['abbr']
                # ❌ NO semester_id!
            )
            db.session.add(faculty)
        else:
            # Faculty already exists, skip or update
            pass
```

**Result:**
- If faculty already exists → Skip (don't duplicate)
- If faculty is new → Add to shared faculty table
- **NO semester_id** because faculty is shared!

---

**2. Slots File Upload**
```python
# In excel_parser.py
def parse_slots_file(filepath):
    active_semester = Semester.query.filter_by(is_active=True).first()
    
    for row in excel:
        slot = Slot(
            slot_label=row['label'],
            semester_id=active_semester.id  # ✅ Links to Summer
        )
        db.session.add(slot)
```

**Result:**
- Slots are created WITH semester_id
- Summer slots are separate from Winter slots

---

**3. Courses File Upload**
```python
# In excel_parser.py
def parse_course_strengths(filepath):
    active_semester = Semester.query.filter_by(is_active=True).first()
    
    for row in excel:
        course = Course(
            code=row['code'],
            name=row['name'],
            semester_id=active_semester.id  # ✅ Links to Summer
        )
        db.session.add(course)
```

**Result:**
- Courses are created WITH semester_id
- Summer courses are separate from Winter courses

---

## 📊 Database State After Upload

### After Uploading to Summer Semester:

```sql
-- SHARED: Faculty (Same for all semesters)
SELECT * FROM faculty;
```
| id | full_name | abbreviation |
|----|-----------|--------------|
| 1 | Dr. Smith | DS |
| 2 | Dr. Jones | DJ |
| 3 | Dr. Brown | DB |

**Count: 3 faculty (shared by Winter AND Summer)**

---

```sql
-- SEMESTER-SPECIFIC: Courses
SELECT * FROM courses;
```
| id | code | name | semester_id |
|----|------|------|-------------|
| 1 | CS101 | Intro | 1 (Winter) |
| 2 | CS102 | Data Struct | 1 (Winter) |
| 3 | CS201 | Algorithms | 2 (Summer) |
| 4 | CS202 | Databases | 2 (Summer) |

**Count: 4 courses total (2 Winter + 2 Summer)**

---

```sql
-- SEMESTER-SPECIFIC: Slots
SELECT * FROM slots;
```
| id | slot_label | semester_id |
|----|------------|-------------|
| 1 | A1 | 1 (Winter) |
| 2 | A2 | 1 (Winter) |
| 3 | B1 | 1 (Winter) |
| 4 | A1 | 2 (Summer) |
| 5 | A2 | 2 (Summer) |
| 6 | B1 | 2 (Summer) |

**Count: 6 slots total (3 Winter + 3 Summer)**

---

## 🎯 How to Query Data Correctly

### ❌ WRONG: Query Faculty by Semester
```sql
-- This will return NOTHING because faculty has no semester_id
SELECT * FROM faculty WHERE semester_id = 2;
-- ERROR: column "semester_id" does not exist
```

### ✅ CORRECT: Query Faculty (All Semesters)
```sql
-- Faculty is shared, just query all
SELECT * FROM faculty;
-- Returns ALL faculty (used by all semesters)
```

---

### ✅ CORRECT: Query Courses by Semester
```sql
-- Courses are semester-specific
SELECT * FROM courses WHERE semester_id = 2;
-- Returns only Summer courses
```

---

### ✅ CORRECT: Query Faculty Teaching in Summer
```sql
-- Join courses with faculty through course_faculty table
SELECT DISTINCT f.full_name, f.abbreviation
FROM faculty f
JOIN course_faculty cf ON f.id = cf.faculty_id
JOIN courses c ON cf.course_id = c.id
WHERE c.semester_id = 2;  -- Summer semester
-- Returns faculty teaching in Summer
```

---

## 📋 Complete Data Type Reference

### SHARED Across All Semesters (No semester_id)

| Table | Why Shared? |
|-------|-------------|
| `faculty` | Professors are permanent staff |
| `rooms` | Classrooms don't change |
| `programs` | Degree programs are permanent |
| `time_slots` | 5x5 grid is standard |

**Query:** `SELECT * FROM faculty;` (no filtering needed)

---

### SEMESTER-SPECIFIC (Has semester_id)

| Table | Why Semester-Specific? |
|-------|------------------------|
| `courses` | Different courses each semester |
| `batches` | Different student groups |
| `slots` | Slot structure may change |
| `timetable_entries` | Schedule is per semester |
| `scheduling_violations` | Issues are per semester |
| `slot_courses` | Course-slot mapping per semester |

**Query:** `SELECT * FROM courses WHERE semester_id = 2;` (filter by semester)

---

## 🧪 Test Queries for Your Database

### Check Faculty (Should be Same for All Semesters)
```sql
-- All faculty
SELECT COUNT(*) as total_faculty FROM faculty;

-- Faculty with their courses in Winter (semester_id = 1)
SELECT f.full_name, COUNT(c.id) as winter_courses
FROM faculty f
LEFT JOIN course_faculty cf ON f.id = cf.faculty_id
LEFT JOIN courses c ON cf.course_id = c.id AND c.semester_id = 1
GROUP BY f.id, f.full_name;

-- Faculty with their courses in Summer (semester_id = 2)
SELECT f.full_name, COUNT(c.id) as summer_courses
FROM faculty f
LEFT JOIN course_faculty cf ON f.id = cf.faculty_id
LEFT JOIN courses c ON cf.course_id = c.id AND c.semester_id = 2
GROUP BY f.id, f.full_name;
```

---

### Check Courses (Should be Different per Semester)
```sql
-- Winter courses
SELECT COUNT(*) as winter_courses 
FROM courses 
WHERE semester_id = 1;

-- Summer courses
SELECT COUNT(*) as summer_courses 
FROM courses 
WHERE semester_id = 2;

-- All courses with semester name
SELECT c.code, c.name, s.name as semester
FROM courses c
JOIN semesters s ON c.semester_id = s.id
ORDER BY s.id, c.code;
```

---

### Check Timetable Entries (Should be Different per Semester)
```sql
-- Winter timetable entries
SELECT COUNT(*) as winter_entries 
FROM timetable_entries 
WHERE semester_id = 1;

-- Summer timetable entries
SELECT COUNT(*) as summer_entries 
FROM timetable_entries 
WHERE semester_id = 2;
```

---

## 💡 Why This Design Makes Sense

### Real-World Analogy

Think of a university:

**Permanent Resources (Shared):**
- 🏫 Buildings and classrooms → `rooms` table
- 👨‍🏫 Faculty members → `faculty` table
- 🎓 Degree programs → `programs` table

**Semester-Specific:**
- 📚 Course offerings → `courses` table
- 👥 Student batches → `batches` table
- 📅 Class schedule → `timetable_entries` table

---

### Benefits:

1. **No Duplication**
   - Don't store same faculty 10 times for 10 semesters
   - One faculty record, used by all semesters

2. **Easy Updates**
   - Update faculty email once, applies to all semesters
   - Add new room once, available for all semesters

3. **Historical Accuracy**
   - Faculty who left still show in old semester timetables
   - Can see which faculty taught which courses when

4. **Efficient Storage**
   - Shared data stored once
   - Only semester-specific data duplicated

---

## 🎯 For Your Demo

### When Showing Database in pgAdmin:

**Show Shared Data:**
```sql
-- "These faculty members teach across all semesters"
SELECT full_name, abbreviation FROM faculty;

-- "These rooms are available for all semesters"
SELECT name, capacity FROM rooms;
```

**Show Semester-Specific Data:**
```sql
-- "These are the courses for Winter semester"
SELECT code, name FROM courses WHERE semester_id = 1;

-- "These are the courses for Summer semester"
SELECT code, name FROM courses WHERE semester_id = 2;

-- "Notice: Different courses, same faculty"
```

**Talking Point:**
> "The system intelligently separates shared resources like faculty and rooms from semester-specific data like courses and schedules. This prevents duplication while maintaining flexibility."

---

## ✅ Summary

| Question | Answer |
|----------|--------|
| Why is faculty data the same? | Faculty is SHARED across all semesters |
| Should faculty have semester_id? | NO - faculty is permanent |
| Will faculty change when I switch semesters? | NO - same faculty for all semesters |
| What about courses? | YES - courses ARE semester-specific |
| What about timetable? | YES - timetable IS semester-specific |

---

## 🔑 Key Takeaway

**When you see the same faculty in pgAdmin after creating a new semester:**

✅ **This is CORRECT!**
- Faculty is shared
- Same professors teach in multiple semesters
- No duplication needed

**What SHOULD be different:**
- Courses (different per semester)
- Batches (different per semester)
- Timetable entries (different per semester)
- Slots (different per semester)

---

**Does this make sense now? 🎓**

The faculty table is like the university's staff directory - it doesn't change every semester. But the course catalog and class schedule DO change every semester!
