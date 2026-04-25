-- ============================================================================
-- University Timetable Generator — PostgreSQL Schema
-- Database: timetable_generator_db
-- Design: Third Normal Form (3NF) with composite UNIQUE constraints
-- ============================================================================

-- Drop tables in reverse dependency order (for clean re-runs)
DROP TABLE IF EXISTS timetable_snapshot CASCADE;
DROP TABLE IF EXISTS batch_overlap_rule CASCADE;
DROP TABLE IF EXISTS elective_enrollment CASCADE;
DROP TABLE IF EXISTS user_role CASCADE;
DROP TABLE IF EXISTS constraint_violation_log CASCADE;
DROP TABLE IF EXISTS master_timetable CASCADE;
DROP TABLE IF EXISTS batch_course_map CASCADE;
DROP TABLE IF EXISTS faculty_course_map CASCADE;
DROP TABLE IF EXISTS time_slot CASCADE;
DROP TABLE IF EXISTS room CASCADE;
DROP TABLE IF EXISTS student_batch CASCADE;
DROP TABLE IF EXISTS course CASCADE;
DROP TABLE IF EXISTS faculty CASCADE;
DROP TABLE IF EXISTS scheduling_constraint CASCADE;

-- Drop views
DROP VIEW IF EXISTS v_master_timetable CASCADE;
DROP VIEW IF EXISTS v_faculty_schedule CASCADE;
DROP VIEW IF EXISTS v_room_utilization CASCADE;

-- ============================================================================
-- 1. FACULTY TABLE
-- Stores teaching staff with unique short names for timetable display.
-- ============================================================================
CREATE TABLE faculty (
    faculty_id   SERIAL PRIMARY KEY,
    name         VARCHAR(100),
    short_name   VARCHAR(100) NOT NULL UNIQUE,
    department   VARCHAR(100),
    email        VARCHAR(150) UNIQUE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE faculty IS 'Teaching staff records with unique short names for timetable display';
COMMENT ON COLUMN faculty.short_name IS 'Unique code used in timetable (e.g., PMJ, ST, HSJ)';

-- ============================================================================
-- 2. COURSE TABLE
-- Stores subject metadata including the L-T-P-C credit structure.
-- ============================================================================
CREATE TABLE course (
    course_id    SERIAL PRIMARY KEY,
    course_code  VARCHAR(100) NOT NULL UNIQUE,
    course_name  VARCHAR(150) NOT NULL,
    lecture_hrs  INT DEFAULT 0,
    tutorial_hrs INT DEFAULT 0,
    practical_hrs INT DEFAULT 0,
    credits      INT DEFAULT 0,
    ltpc         VARCHAR(15),
    course_type  VARCHAR(80) NOT NULL DEFAULT 'Core',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE course IS 'Academic course catalogue with L-T-P-C credit structure';
COMMENT ON COLUMN course.ltpc IS 'Lecture-Tutorial-Practical-Credits string (e.g., 3-0-0-3)';
COMMENT ON COLUMN course.course_type IS 'Course classification — Core, Technical Elective, HASS Elective, Open Elective, Specialization, etc.';

-- ============================================================================
-- 3. STUDENT BATCH TABLE
-- Defines student cohorts with program, section, and headcount.
-- ============================================================================
CREATE TABLE student_batch (
    batch_id     SERIAL PRIMARY KEY,
    program_name VARCHAR(50),
    sub_batch    VARCHAR(80) NOT NULL,
    section      VARCHAR(20) NOT NULL DEFAULT 'All',
    year         INT,
    headcount    INT DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_batch_identity UNIQUE (sub_batch, section),
    CONSTRAINT chk_headcount CHECK (headcount >= 0)
);

COMMENT ON TABLE student_batch IS 'Student cohorts defined by program, sub-batch, and section';
COMMENT ON COLUMN student_batch.sub_batch IS 'E.g., ICT + CS, CS-Only, MnC';
COMMENT ON COLUMN student_batch.section IS 'E.g., Sec A, Sec B, or All';

-- ============================================================================
-- 4. ROOM TABLE
-- Catalogs physical infrastructure with capacity constraints.
-- ============================================================================
CREATE TABLE room (
    room_id      SERIAL PRIMARY KEY,
    room_number  VARCHAR(30) NOT NULL UNIQUE,
    room_type    VARCHAR(50) DEFAULT 'Lecture Hall',
    capacity     INT DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_capacity CHECK (capacity >= 0)
);

COMMENT ON TABLE room IS 'Physical classrooms and labs with seating capacity';

-- ============================================================================
-- 5. TIME SLOT TABLE
-- Standardizes the university scheduling grid: day × period → slot group.
-- ============================================================================
CREATE TABLE time_slot (
    slot_id      SERIAL PRIMARY KEY,
    day_of_week  VARCHAR(15) NOT NULL,
    start_time   TIME NOT NULL,
    end_time     TIME NOT NULL,
    slot_group   VARCHAR(15) NOT NULL,

    CONSTRAINT uq_day_time UNIQUE (day_of_week, start_time),
    CONSTRAINT chk_day CHECK (
        day_of_week IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')
    ),
    CONSTRAINT chk_time_order CHECK (end_time > start_time)
);

COMMENT ON TABLE time_slot IS 'University scheduling grid: 5 days × 5 periods mapped to 8 slot groups';
COMMENT ON COLUMN time_slot.slot_group IS 'Slot grouping (Slot-1 through Slot-8, or Slot-Free)';

-- ============================================================================
-- 6. FACULTY-COURSE MAP (Junction Table)
-- Authorizes which faculty can teach which courses.
-- The assignment_id is the surrogate key used by Master_Timetable.
-- ============================================================================
CREATE TABLE faculty_course_map (
    assignment_id SERIAL PRIMARY KEY,
    faculty_id   INT NOT NULL REFERENCES faculty(faculty_id) ON DELETE CASCADE,
    course_id    INT NOT NULL REFERENCES course(course_id) ON DELETE CASCADE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_faculty_course UNIQUE (faculty_id, course_id)
);

COMMENT ON TABLE faculty_course_map IS 'Junction table: authorizes faculty-course pairings. assignment_id is used by Master_Timetable';
COMMENT ON COLUMN faculty_course_map.assignment_id IS 'Surrogate key — Master_Timetable references this, NOT faculty_id or course_id directly';

-- ============================================================================
-- 7. BATCH-COURSE MAP (Junction Table)
-- Defines which batches are enrolled in which courses.
-- ============================================================================
CREATE TABLE batch_course_map (
    batch_id   INT NOT NULL REFERENCES student_batch(batch_id) ON DELETE CASCADE,
    course_id  INT NOT NULL REFERENCES course(course_id) ON DELETE CASCADE,

    PRIMARY KEY (batch_id, course_id)
);

COMMENT ON TABLE batch_course_map IS 'Junction table: links student batches to their required courses';

-- ============================================================================
-- 8. SCHEDULING CONSTRAINT TABLE (The "Constraints Table")
-- Stores scheduling rules as queryable, toggleable data rows.
-- ============================================================================
CREATE TABLE scheduling_constraint (
    constraint_id    SERIAL PRIMARY KEY,
    constraint_name  VARCHAR(100) NOT NULL UNIQUE,
    constraint_type  VARCHAR(10) NOT NULL,
    scope            VARCHAR(20) NOT NULL,
    rule_description TEXT NOT NULL,
    enforcement_level VARCHAR(20) NOT NULL DEFAULT 'APPLICATION',
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    parameters_json  JSONB DEFAULT '{}',
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_constraint_type CHECK (constraint_type IN ('HARD', 'SOFT')),
    CONSTRAINT chk_scope CHECK (
        scope IN ('FACULTY', 'ROOM', 'BATCH', 'COURSE', 'GLOBAL')
    ),
    CONSTRAINT chk_enforcement CHECK (
        enforcement_level IN ('DATABASE', 'APPLICATION', 'BOTH')
    )
);

COMMENT ON TABLE scheduling_constraint IS 'Scheduling rules stored as data — queryable, toggleable, auditable';
COMMENT ON COLUMN scheduling_constraint.constraint_type IS 'HARD = must be satisfied; SOFT = optimization goal';
COMMENT ON COLUMN scheduling_constraint.enforcement_level IS 'DATABASE = enforced via UNIQUE/CHECK; APPLICATION = enforced in Python CSP solver';
COMMENT ON COLUMN scheduling_constraint.parameters_json IS 'Rule-specific parameters as JSON (e.g., {"max_consecutive": 2})';

-- ============================================================================
-- 9. MASTER TIMETABLE (Central Fact Table)
-- The final generated schedule. Uses ONLY foreign keys — no raw text.
-- Composite UNIQUE constraints enforce hard scheduling rules at DB level.
-- ============================================================================
CREATE TABLE master_timetable (
    timetable_id   SERIAL PRIMARY KEY,
    assignment_id  INT NOT NULL REFERENCES faculty_course_map(assignment_id) ON DELETE CASCADE,
    batch_id       INT NOT NULL REFERENCES student_batch(batch_id) ON DELETE CASCADE,
    room_id        INT REFERENCES room(room_id) ON DELETE SET NULL,
    slot_id        INT NOT NULL REFERENCES time_slot(slot_id) ON DELETE CASCADE,
    is_moved       BOOLEAN DEFAULT FALSE,
    original_slot_group VARCHAR(15),
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- === DATABASE-LEVEL CONSTRAINT ENFORCEMENT ("Hard Locks") ===

    -- A faculty-course assignment for a specific batch cannot be scheduled
    -- twice in the same slot.
    CONSTRAINT uq_assignment_batch_slot UNIQUE (assignment_id, batch_id, slot_id)

    -- NOTE: UNIQUE(batch_id, slot_id) is NOT here because:
    --   Elective courses CAN share the same time slot for a batch.
    --   This constraint is enforced by the CSP solver (application layer)
    --   which distinguishes between core (no overlap) and elective (overlap OK).

    -- NOTE: UNIQUE(room_id, slot_id) is NOT here because:
    --   Elective courses sharing a slot often share the same room assignment.
    --   Room conflicts for CORE courses are enforced by the CSP solver.
);

COMMENT ON TABLE master_timetable IS 'Central fact table: final generated schedule using FK-only references';
COMMENT ON COLUMN master_timetable.assignment_id IS 'Links to faculty_course_map — inherits pre-approved faculty-course pairing';
COMMENT ON COLUMN master_timetable.is_moved IS 'TRUE if the CSP solver moved this course from its original slot';
COMMENT ON COLUMN master_timetable.original_slot_group IS 'The slot group from the input Excel (before solver reassignment)';

-- ============================================================================
-- 10. CONSTRAINT VIOLATION LOG (Audit Trail)
-- Records every constraint violation detected during timetable generation.
-- ============================================================================
CREATE TABLE constraint_violation_log (
    violation_id    SERIAL PRIMARY KEY,
    timetable_id    INT REFERENCES master_timetable(timetable_id) ON DELETE SET NULL,
    constraint_id   INT REFERENCES scheduling_constraint(constraint_id) ON DELETE SET NULL,
    severity        VARCHAR(20) NOT NULL DEFAULT 'WARNING',
    violation_detail TEXT NOT NULL,
    detected_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_severity CHECK (
        severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')
    )
);

COMMENT ON TABLE constraint_violation_log IS 'Audit log: records every constraint violation with timestamp and details';

-- ============================================================================
-- 11. USER ROLE TABLE (Firebase Authentication)
-- Maps Firebase UIDs to application roles and faculty records.
-- ============================================================================
CREATE TABLE user_role (
    uid              VARCHAR(128) PRIMARY KEY,
    email            VARCHAR(150) NOT NULL UNIQUE,
    role             VARCHAR(20) NOT NULL DEFAULT 'FACULTY',
    faculty_id       INT REFERENCES faculty(faculty_id) ON DELETE SET NULL,
    password_changed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_role CHECK (role IN ('ADMIN', 'FACULTY'))
);

COMMENT ON TABLE user_role IS 'Maps Firebase Auth UIDs to application roles (ADMIN or FACULTY)';
COMMENT ON COLUMN user_role.uid IS 'Firebase UID — primary key, set during account seeding';
COMMENT ON COLUMN user_role.faculty_id IS 'Links FACULTY users to their faculty record for data scoping';
COMMENT ON COLUMN user_role.password_changed IS 'FALSE = must change password on next login; TRUE = normal access';

-- ============================================================================
-- 12. ELECTIVE ENROLLMENT TABLE
-- Tracks actual enrollment numbers for elective courses (overrides batch size).
-- ============================================================================
CREATE TABLE elective_enrollment (
    enrollment_id SERIAL PRIMARY KEY,
    course_code   VARCHAR(100) NOT NULL,
    enrollment    INT NOT NULL DEFAULT 0,
    semester      VARCHAR(20) DEFAULT 'current',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_elective_course UNIQUE (course_code, semester),
    CONSTRAINT chk_enrollment CHECK (enrollment >= 0)
);

COMMENT ON TABLE elective_enrollment IS 'Actual enrollment numbers for elective courses — overrides batch-size heuristic';

-- ============================================================================
-- 13. BATCH OVERLAP RULE TABLE
-- Defines which student batches share students (e.g., ICT+CS minors in ICT Sec B).
-- ============================================================================
CREATE TABLE batch_overlap_rule (
    rule_id     SERIAL PRIMARY KEY,
    batch_a     VARCHAR(80) NOT NULL,
    section_a   VARCHAR(20) NOT NULL DEFAULT 'All',
    batch_b     VARCHAR(80) NOT NULL,
    section_b   VARCHAR(20) NOT NULL DEFAULT 'All',
    description VARCHAR(200),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE batch_overlap_rule IS 'Defines student group overlaps — batch_a students also attend batch_b classes';

-- ============================================================================
-- 14. TIMETABLE SNAPSHOT TABLE
-- Stores complete timetable snapshots for versioning and history.
-- ============================================================================
CREATE TABLE timetable_snapshot (
    snapshot_id     SERIAL PRIMARY KEY,
    label           VARCHAR(100) NOT NULL,
    semester        VARCHAR(50),
    notes           TEXT,
    source_file     VARCHAR(200),
    entry_count     INT DEFAULT 0,
    violation_count INT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    snapshot_data   JSONB NOT NULL
);

COMMENT ON TABLE timetable_snapshot IS 'Complete timetable snapshots for versioning — stores full grid as JSONB';

-- ============================================================================
-- INDEXES (Performance Optimization)
-- ============================================================================

-- Faculty lookups by short name (used during Excel → DB loading)
CREATE INDEX idx_faculty_short_name ON faculty(short_name);

-- Course lookups by code (used during Excel → DB loading)
CREATE INDEX idx_course_code ON course(course_code);

-- Room lookups by number
CREATE INDEX idx_room_number ON room(room_number);

-- Batch lookups by sub_batch + section
CREATE INDEX idx_batch_identity ON student_batch(sub_batch, section);

-- Time slot lookups by slot_group (used to map slot names to IDs)
CREATE INDEX idx_slot_group ON time_slot(slot_group);

-- Master timetable by slot (for schedule queries)
CREATE INDEX idx_timetable_slot ON master_timetable(slot_id);

-- Violation log by timestamp (for recent violations)
CREATE INDEX idx_violation_time ON constraint_violation_log(detected_at DESC);

-- User role lookups by email and role
CREATE INDEX idx_user_role_email ON user_role(email);
CREATE INDEX idx_user_role_role ON user_role(role);

-- ============================================================================
-- VIEWS (Human-Readable Queries)
-- ============================================================================

-- View 1: Master Timetable with all details joined
CREATE VIEW v_master_timetable AS
SELECT
    mt.timetable_id,
    ts.day_of_week,
    ts.start_time,
    ts.end_time,
    ts.slot_group,
    c.course_code,
    c.course_name,
    c.course_type,
    c.ltpc,
    f.short_name AS faculty_short_name,
    f.name AS faculty_full_name,
    sb.sub_batch,
    sb.section,
    sb.program_name,
    r.room_number,
    r.capacity AS room_capacity,
    mt.is_moved,
    mt.original_slot_group
FROM master_timetable mt
JOIN faculty_course_map fcm ON mt.assignment_id = fcm.assignment_id
JOIN faculty f ON fcm.faculty_id = f.faculty_id
JOIN course c ON fcm.course_id = c.course_id
JOIN student_batch sb ON mt.batch_id = sb.batch_id
JOIN time_slot ts ON mt.slot_id = ts.slot_id
LEFT JOIN room r ON mt.room_id = r.room_id;

COMMENT ON VIEW v_master_timetable IS 'Human-readable timetable with all entity details joined';

-- View 2: Faculty Schedule
CREATE VIEW v_faculty_schedule AS
SELECT
    f.short_name AS faculty,
    f.name AS full_name,
    ts.day_of_week,
    ts.start_time,
    ts.end_time,
    c.course_code,
    c.course_name,
    sb.sub_batch,
    sb.section,
    r.room_number
FROM master_timetable mt
JOIN faculty_course_map fcm ON mt.assignment_id = fcm.assignment_id
JOIN faculty f ON fcm.faculty_id = f.faculty_id
JOIN course c ON fcm.course_id = c.course_id
JOIN student_batch sb ON mt.batch_id = sb.batch_id
JOIN time_slot ts ON mt.slot_id = ts.slot_id
LEFT JOIN room r ON mt.room_id = r.room_id
ORDER BY f.short_name, ts.day_of_week, ts.start_time;

COMMENT ON VIEW v_faculty_schedule IS 'Per-faculty schedule view sorted by day and time';

-- View 3: Room Utilization
CREATE VIEW v_room_utilization AS
SELECT
    r.room_number,
    r.room_type,
    r.capacity,
    COUNT(DISTINCT (mt.room_id, mt.slot_id)) AS total_classes,
    ROUND(COUNT(DISTINCT (mt.room_id, mt.slot_id)) * 100.0 / 25, 1) AS utilization_pct
FROM room r
LEFT JOIN master_timetable mt ON r.room_id = mt.room_id
GROUP BY r.room_id, r.room_number, r.room_type, r.capacity
ORDER BY utilization_pct DESC;

COMMENT ON VIEW v_room_utilization IS 'Room utilization statistics — classes per room out of 25 possible slots';

-- ============================================================================
-- Done! Schema created successfully.
-- ============================================================================
