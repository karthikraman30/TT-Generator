-- ============================================================
-- Timetable Generator - PostgreSQL Schema (3NF)
-- University-specific: Slot-based scheduling system
-- ============================================================

-- ─── PROGRAMS ────────────────────────────────────────
-- Degree programs: BTech, MTech, MSc
CREATE TABLE IF NOT EXISTS programs (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,          -- 'B-Tech ICT', 'M-Tech ICT-ML'
    code            VARCHAR(30) NOT NULL UNIQUE,    -- 'BTECH_ICT', 'MTECH_ML'
    degree_type     VARCHAR(20) NOT NULL,           -- 'BTech', 'MTech', 'MSc'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── SEMESTERS ───────────────────────────────────────
-- Academic cycle: Winter, Summer, Autumn
CREATE TABLE IF NOT EXISTS semesters (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,          -- 'Winter 2025-26'
    academic_year   VARCHAR(20) NOT NULL,           -- '2025-26'
    season          VARCHAR(20) NOT NULL,           -- 'Winter', 'Summer', 'Autumn'
    is_active       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(academic_year, season)
);

-- ─── BATCHES ─────────────────────────────────────────
-- Specific student cohorts: 'BTech Sem-II (ICT + CS)'
CREATE TABLE IF NOT EXISTS batches (
    id              SERIAL PRIMARY KEY,
    program_id      INTEGER REFERENCES programs(id) ON DELETE SET NULL,
    semester_id     INTEGER REFERENCES semesters(id) ON DELETE CASCADE,
    name            VARCHAR(150) NOT NULL,          -- 'BTech Sem-II (ICT + CS)'
    sem_number      INTEGER NOT NULL,               -- 2, 4, 6, 8
    section         VARCHAR(10),                    -- 'A', 'B', or NULL
    student_count   INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── FACULTY ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS faculty (
    id              SERIAL PRIMARY KEY,
    full_name       VARCHAR(200) NOT NULL,
    abbreviation    VARCHAR(10) NOT NULL UNIQUE,    -- 'PMJ', 'PD', 'RB'
    email           VARCHAR(200) UNIQUE,
    firebase_uid    VARCHAR(200) UNIQUE,
    role            VARCHAR(20) NOT NULL DEFAULT 'faculty',  -- 'admin' or 'faculty'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── ROOMS ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rooms (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(50) NOT NULL UNIQUE,    -- 'LH-101', 'AB-2/301'
    capacity        INTEGER NOT NULL,
    building        VARCHAR(100),
    floor           INTEGER,
    room_type       VARCHAR(20) DEFAULT 'lecture',  -- 'lecture', 'lab', 'seminar'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── COURSES ─────────────────────────────────────────
-- Each course with its L-T-P-C breakdown
CREATE TABLE IF NOT EXISTS courses (
    id                  SERIAL PRIMARY KEY,
    code                VARCHAR(20) NOT NULL,           -- 'IT412', 'HM106'
    name                VARCHAR(250) NOT NULL,          -- 'Data Structures (Sec A)'
    lectures_per_week   INTEGER NOT NULL DEFAULT 0,     -- L
    tutorials_per_week  INTEGER NOT NULL DEFAULT 0,     -- T
    practicals_per_week INTEGER NOT NULL DEFAULT 0,     -- P
    credits             NUMERIC(3,1) NOT NULL DEFAULT 0,-- C (can be 4.5)
    course_type         VARCHAR(40) NOT NULL DEFAULT 'Core',  -- 'Core', 'Elective', 'Open', etc.
    semester_id         INTEGER REFERENCES semesters(id) ON DELETE CASCADE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(code, name, semester_id)
);

-- ─── COURSE ↔ BATCH MAPPING ─────────────────────────
-- Which batches take which course
CREATE TABLE IF NOT EXISTS course_batches (
    id              SERIAL PRIMARY KEY,
    course_id       INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    batch_id        INTEGER REFERENCES batches(id) ON DELETE CASCADE,
    UNIQUE(course_id, batch_id)
);

-- ─── COURSE ↔ FACULTY MAPPING ───────────────────────
-- Who teaches which course (optionally to which section)
CREATE TABLE IF NOT EXISTS course_faculty (
    id              SERIAL PRIMARY KEY,
    course_id       INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    faculty_id      INTEGER REFERENCES faculty(id) ON DELETE CASCADE,
    UNIQUE(course_id, faculty_id)
);

-- ─── SLOTS ───────────────────────────────────────────
-- The bucket system: Slot-1 through Slot-8, Slot-Free
CREATE TABLE IF NOT EXISTS slots (
    id              SERIAL PRIMARY KEY,
    slot_label      VARCHAR(20) NOT NULL,           -- 'Slot-1', 'Slot-Free'
    slot_number     INTEGER,                        -- 1-8, NULL for Slot-Free
    semester_id     INTEGER REFERENCES semesters(id) ON DELETE CASCADE,
    UNIQUE(slot_label, semester_id)
);

-- ─── SLOT ↔ COURSE MAPPING ──────────────────────────
-- Which courses belong to which slot
CREATE TABLE IF NOT EXISTS slot_courses (
    id              SERIAL PRIMARY KEY,
    slot_id         INTEGER REFERENCES slots(id) ON DELETE CASCADE,
    course_id       INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    batch_id        INTEGER REFERENCES batches(id) ON DELETE CASCADE,
    UNIQUE(slot_id, course_id, batch_id)
);

-- ─── TIME SLOTS (THE GRID) ──────────────────────────
-- 5 days × 5 periods = 25 time slots
CREATE TABLE IF NOT EXISTS time_slots (
    id              SERIAL PRIMARY KEY,
    day             VARCHAR(10) NOT NULL,           -- 'Monday' ... 'Friday'
    period          INTEGER NOT NULL,               -- 1-5
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    UNIQUE(day, period)
);

-- ─── TIMETABLE ENTRIES ───────────────────────────────
-- The generated schedule
CREATE TABLE IF NOT EXISTS timetable_entries (
    id              SERIAL PRIMARY KEY,
    slot_id         INTEGER REFERENCES slots(id) ON DELETE CASCADE,
    course_id       INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    faculty_id      INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
    room_id         INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    time_slot_id    INTEGER REFERENCES time_slots(id) ON DELETE CASCADE,
    semester_id     INTEGER REFERENCES semesters(id) ON DELETE CASCADE,
    is_combined     BOOLEAN DEFAULT FALSE,
    combined_strength INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── SCHEDULING VIOLATIONS / LOGS ───────────────────
-- Track all errors, warnings, and constraint violations
CREATE TABLE IF NOT EXISTS scheduling_violations (
    id              SERIAL PRIMARY KEY,
    semester_id     INTEGER REFERENCES semesters(id) ON DELETE CASCADE,
    violation_type  VARCHAR(50) NOT NULL,           -- 'ROOM_CONFLICT', 'FACULTY_CONFLICT', 'CAPACITY_EXCEEDED', 'SLOT_CONFLICT', 'UNASSIGNED'
    severity        VARCHAR(20) NOT NULL DEFAULT 'error',  -- 'error', 'warning', 'info'
    description     TEXT NOT NULL,
    course_id       INTEGER REFERENCES courses(id) ON DELETE SET NULL,
    faculty_id      INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
    room_id         INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    time_slot_id    INTEGER REFERENCES time_slots(id) ON DELETE SET NULL,
    resolved        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── INDEXES FOR PERFORMANCE ─────────────────────────
CREATE INDEX IF NOT EXISTS idx_courses_semester ON courses(semester_id);
CREATE INDEX IF NOT EXISTS idx_batches_semester ON batches(semester_id);
CREATE INDEX IF NOT EXISTS idx_timetable_semester ON timetable_entries(semester_id);
CREATE INDEX IF NOT EXISTS idx_timetable_timeslot ON timetable_entries(time_slot_id);
CREATE INDEX IF NOT EXISTS idx_timetable_faculty ON timetable_entries(faculty_id);
CREATE INDEX IF NOT EXISTS idx_timetable_room ON timetable_entries(room_id);
CREATE INDEX IF NOT EXISTS idx_violations_semester ON scheduling_violations(semester_id);
CREATE INDEX IF NOT EXISTS idx_slot_courses_slot ON slot_courses(slot_id);

-- ─── SEED: TIME SLOTS GRID ──────────────────────────
INSERT INTO time_slots (day, period, start_time, end_time) VALUES
    ('Monday', 1, '08:00', '09:00'), ('Monday', 2, '09:00', '10:00'), ('Monday', 3, '10:00', '11:00'), ('Monday', 4, '11:00', '12:00'), ('Monday', 5, '12:00', '13:00'),
    ('Tuesday', 1, '08:00', '09:00'), ('Tuesday', 2, '09:00', '10:00'), ('Tuesday', 3, '10:00', '11:00'), ('Tuesday', 4, '11:00', '12:00'), ('Tuesday', 5, '12:00', '13:00'),
    ('Wednesday', 1, '08:00', '09:00'), ('Wednesday', 2, '09:00', '10:00'), ('Wednesday', 3, '10:00', '11:00'), ('Wednesday', 4, '11:00', '12:00'), ('Wednesday', 5, '12:00', '13:00'),
    ('Thursday', 1, '08:00', '09:00'), ('Thursday', 2, '09:00', '10:00'), ('Thursday', 3, '10:00', '11:00'), ('Thursday', 4, '11:00', '12:00'), ('Thursday', 5, '12:00', '13:00'),
    ('Friday', 1, '08:00', '09:00'), ('Friday', 2, '09:00', '10:00'), ('Friday', 3, '10:00', '11:00'), ('Friday', 4, '11:00', '12:00'), ('Friday', 5, '12:00', '13:00')
ON CONFLICT DO NOTHING;
