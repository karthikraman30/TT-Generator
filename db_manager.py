"""
Database Manager for University Timetable Generator
====================================================
Single module that handles ALL PostgreSQL operations.
Imported by generate_timetable.py — shares the same process & RAM.

The DBManager acts as a MIRROR: it copies in-memory data to PostgreSQL
for persistence, querying, and constraint enforcement. The CSP solver
continues to work on Python objects in RAM as before.

Usage:
    from db_manager import DBManager

    db = DBManager()                      # connect
    db.store_input_data(courses)          # mirror input → DB
    db.store_results(final_courses, ...)  # mirror output → DB
    db.close()                            # disconnect
"""

import os
import re
import sys
from datetime import datetime

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 is not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if present
except ImportError:
    pass  # python-dotenv is optional; environment variables still work


class DBManager:
    """
    Manages PostgreSQL connection and data mirroring for the timetable generator.

    This class is imported into generate_timetable.py and runs in the SAME
    Python process. It never owns the data — it just mirrors in-memory
    Python objects to PostgreSQL for persistence.
    """

    def __init__(self, quiet=False):
        """Open connection to PostgreSQL using environment variables or .env file.
        
        Args:
            quiet: If True, suppress all print output (used by Flask/web contexts).
        """
        self.conn = None
        self.cur = None
        self._quiet = quiet
        self._connect()

        # Cache for ID lookups (avoids redundant SELECTs)
        self._faculty_cache = {}     # short_name → faculty_id
        self._course_cache = {}      # course_code → course_id
        self._room_cache = {}        # room_number → room_id
        self._batch_cache = {}       # (sub_batch, section) → batch_id
        self._assignment_cache = {}  # (faculty_id, course_id) → assignment_id
        self._slot_cache = {}        # (day, start_time_str) → slot_id
        self._slot_group_cache = {}  # slot_group → [slot_id, ...]

    def _log(self, msg):
        """Safe print that won't crash if stdout is unavailable (e.g., background Flask)."""
        if self._quiet:
            return
        try:
            print(msg)
        except (OSError, IOError):
            pass  # stdout unavailable (background process)

    def _connect(self):
        """Establish TCP connection to PostgreSQL."""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 5432)),
                dbname=os.getenv('DB_NAME', 'timetable_generator_db'),
                user=os.getenv('DB_USER', os.getenv('USER', 'postgres')),
                password=os.getenv('DB_PASSWORD', ''),
            )
            self.conn.autocommit = False
            self.cur = self.conn.cursor()

            db_name = os.getenv('DB_NAME', 'timetable_generator_db')
            host = os.getenv('DB_HOST', 'localhost')
            port = os.getenv('DB_PORT', 5432)
            self._log(f"  ✓ Connected to {db_name}@{host}:{port}")
        except psycopg2.OperationalError as e:
            self._log(f"\n  ✗ Could not connect to PostgreSQL: {e}")
            self._log("  Make sure PostgreSQL is running: brew services start postgresql@16")
            self._log("  And the database exists: psql postgres -c \"CREATE DATABASE timetable_generator_db;\"")
            sys.exit(1)

    # =========================================================================
    # CONFIG READERS: Read configuration from DB tables
    # =========================================================================

    def get_room_config(self):
        """Read room capacities from DB. Returns dict: {room_number: capacity}."""
        self.cur.execute("SELECT room_number, capacity FROM room WHERE capacity > 0 ORDER BY room_number")
        return {row[0]: row[1] for row in self.cur.fetchall()}

    def get_batch_config(self):
        """Read batch strengths from DB. Returns dict: {program: total_headcount}."""
        import re
        self.cur.execute("""
            SELECT sub_batch, section, headcount FROM student_batch
            WHERE headcount > 0 ORDER BY sub_batch, section
        """)
        totals = {}
        for sub_batch, section, headcount in self.cur.fetchall():
            match = re.search(r'\(([^)]+)\)', sub_batch)
            if match:
                program = match.group(1).strip()
                if program not in totals:
                    totals[program] = 0
                # Use max across sections as the per-section size
                # For total, we'd sum unique sections but this is per-program
                totals[program] = max(totals[program], headcount)
        return totals

    def get_section_config(self):
        """Read section-level strength overrides. Returns dict: {(program, section): headcount}."""
        import re
        self.cur.execute("""
            SELECT sub_batch, section, headcount FROM student_batch
            WHERE headcount > 0 AND section != 'All' ORDER BY sub_batch, section
        """)
        result = {}
        for sub_batch, section, headcount in self.cur.fetchall():
            match = re.search(r'\(([^)]+)\)', sub_batch)
            if match:
                program = match.group(1).strip()
                result[(program, section)] = headcount
        return result

    def get_elective_enrollment(self):
        """Read elective enrollment from DB. Returns dict: {course_code: enrollment}."""
        self.cur.execute("""
            SELECT course_code, enrollment FROM elective_enrollment
            WHERE semester = 'current' ORDER BY course_code
        """)
        return {row[0]: row[1] for row in self.cur.fetchall()}

    def get_slot_matrix(self):
        """Read slot matrix from DB. Returns dict: {day: {period_str: slot_group}}."""
        self.cur.execute("""
            SELECT day_of_week, start_time, end_time, slot_group
            FROM time_slot ORDER BY day_of_week, start_time
        """)
        matrix = {}
        for day, start, end, slot_group in self.cur.fetchall():
            if day not in matrix:
                matrix[day] = {}
            start_str = start.strftime('%H:%M').lstrip('0') if hasattr(start, 'strftime') else str(start)[:5].lstrip('0')
            end_str = end.strftime('%H:%M').lstrip('0') if hasattr(end, 'strftime') else str(end)[:5].lstrip('0')
            period = f"{start_str} - {end_str}"
            matrix[day][period] = slot_group
        return matrix

    def get_overlap_rules(self):
        """Read batch overlap rules from DB. Returns list of tuples."""
        self.cur.execute("""
            SELECT batch_a, section_a, batch_b, section_b, description
            FROM batch_overlap_rule ORDER BY rule_id
        """)
        return self.cur.fetchall()

    # =========================================================================
    # CONFIG WRITERS: CRUD operations for admin UI
    # =========================================================================

    def update_room_capacity(self, room_number, capacity):
        """Update room capacity. Creates room if it doesn't exist."""
        self.cur.execute("""
            INSERT INTO room (room_number, capacity) VALUES (%s, %s)
            ON CONFLICT (room_number) DO UPDATE SET capacity = EXCLUDED.capacity
        """, (room_number, capacity))
        self.conn.commit()

    def delete_room(self, room_number):
        """Delete a room."""
        self.cur.execute("DELETE FROM room WHERE room_number = %s", (room_number,))
        self.conn.commit()

    def update_batch_headcount(self, batch_id, headcount):
        """Update batch headcount."""
        self.cur.execute("UPDATE student_batch SET headcount = %s WHERE batch_id = %s", (headcount, batch_id))
        self.conn.commit()

    def upsert_elective_enrollment(self, course_code, enrollment):
        """Insert or update elective enrollment."""
        self.cur.execute("""
            INSERT INTO elective_enrollment (course_code, enrollment)
            VALUES (%s, %s)
            ON CONFLICT (course_code, semester) DO UPDATE SET enrollment = EXCLUDED.enrollment
        """, (course_code, enrollment))
        self.conn.commit()

    def delete_elective_enrollment(self, course_code):
        """Delete elective enrollment entry."""
        self.cur.execute("DELETE FROM elective_enrollment WHERE course_code = %s AND semester = 'current'", (course_code,))
        self.conn.commit()

    def upsert_overlap_rule(self, batch_a, section_a, batch_b, section_b, description=''):
        """Insert a new batch overlap rule."""
        self.cur.execute("""
            INSERT INTO batch_overlap_rule (batch_a, section_a, batch_b, section_b, description)
            VALUES (%s, %s, %s, %s, %s)
        """, (batch_a, section_a, batch_b, section_b, description))
        self.conn.commit()

    def delete_overlap_rule(self, rule_id):
        """Delete an overlap rule."""
        self.cur.execute("DELETE FROM batch_overlap_rule WHERE rule_id = %s", (rule_id,))
        self.conn.commit()

    def update_slot_group(self, slot_id, slot_group):
        """Update the slot group for a time slot."""
        self.cur.execute("UPDATE time_slot SET slot_group = %s WHERE slot_id = %s", (slot_group, slot_id))
        self.conn.commit()

    def add_time_slot(self, day_of_week, start_time, end_time, slot_group):
        """Add a new time slot."""
        self.cur.execute("""
            INSERT INTO time_slot (day_of_week, start_time, end_time, slot_group)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (day_of_week, start_time) DO UPDATE SET
                end_time = EXCLUDED.end_time, slot_group = EXCLUDED.slot_group
        """, (day_of_week, start_time, end_time, slot_group))
        self.conn.commit()

    def delete_time_slot(self, slot_id):
        """Delete a time slot."""
        self.cur.execute("DELETE FROM time_slot WHERE slot_id = %s", (slot_id,))
        self.conn.commit()

    # =========================================================================
    # SNAPSHOT METHODS: Timetable versioning
    # =========================================================================

    def save_snapshot(self, label, semester='', source_file='', notes=''):
        """Save the current master_timetable as a JSONB snapshot.

        Captures the full rendered timetable (via v_master_timetable view)
        as a JSON array and stores it in the timetable_snapshot table.
        """
        import json

        # Capture current timetable state from the view
        self.cur.execute("""
            SELECT
                mt.timetable_id,
                c.course_code, c.course_name, c.course_type,
                f.short_name AS faculty,
                sb.sub_batch, sb.section,
                r.room_number,
                ts.day_of_week, ts.start_time::text, ts.end_time::text, ts.slot_group,
                mt.is_moved, mt.original_slot_group
            FROM master_timetable mt
            JOIN faculty_course_map fcm ON mt.assignment_id = fcm.assignment_id
            JOIN course c ON fcm.course_id = c.course_id
            JOIN faculty f ON fcm.faculty_id = f.faculty_id
            JOIN student_batch sb ON mt.batch_id = sb.batch_id
            LEFT JOIN room r ON mt.room_id = r.room_id
            JOIN time_slot ts ON mt.slot_id = ts.slot_id
            ORDER BY ts.day_of_week, ts.start_time
        """)
        columns = [desc[0] for desc in self.cur.description]
        rows = self.cur.fetchall()
        data = [dict(zip(columns, row)) for row in rows]

        # Count violations
        self.cur.execute("SELECT COUNT(*) FROM constraint_violation_log")
        violation_count = self.cur.fetchone()[0]

        self.cur.execute("""
            INSERT INTO timetable_snapshot
                (label, semester, source_file, notes, entry_count, violation_count, snapshot_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING snapshot_id
        """, (label, semester, source_file, notes, len(data), violation_count, json.dumps(data)))
        snapshot_id = self.cur.fetchone()[0]
        self.conn.commit()
        return snapshot_id

    def list_snapshots(self):
        """List all snapshots (without the heavy JSONB data)."""
        self.cur.execute("""
            SELECT snapshot_id, label, semester, source_file, notes,
                   entry_count, violation_count, created_at
            FROM timetable_snapshot
            ORDER BY created_at DESC
        """)
        return self.cur.fetchall()

    def get_snapshot(self, snapshot_id):
        """Get a single snapshot including its data."""
        self.cur.execute("""
            SELECT snapshot_id, label, semester, source_file, notes,
                   entry_count, violation_count, created_at, snapshot_data
            FROM timetable_snapshot
            WHERE snapshot_id = %s
        """, (snapshot_id,))
        return self.cur.fetchone()

    def restore_snapshot(self, snapshot_id):
        """Restore a snapshot as the active timetable.

        Clears the current master_timetable and re-inserts entries from the
        snapshot. Requires that referenced courses, faculties, batches, rooms,
        and time_slots still exist in the database.
        """
        import json

        row = self.get_snapshot(snapshot_id)
        if not row:
            raise ValueError(f"Snapshot {snapshot_id} not found")

        data = row[8]  # snapshot_data (JSONB auto-parsed by psycopg2)
        if isinstance(data, str):
            data = json.loads(data)

        # Clear current timetable
        self.cur.execute("TRUNCATE master_timetable CASCADE;")
        self.cur.execute("TRUNCATE constraint_violation_log CASCADE;")

        restored = 0
        skipped = 0
        for entry in data:
            try:
                # Look up foreign keys
                self.cur.execute("SELECT faculty_id FROM faculty WHERE short_name = %s", (entry['faculty'],))
                fac_row = self.cur.fetchone()
                if not fac_row:
                    skipped += 1
                    continue
                faculty_id = fac_row[0]

                self.cur.execute("SELECT course_id FROM course WHERE course_code = %s", (entry['course_code'],))
                course_row = self.cur.fetchone()
                if not course_row:
                    skipped += 1
                    continue
                course_id = course_row[0]

                # Get or create faculty-course assignment
                self.cur.execute("""
                    INSERT INTO faculty_course_map (faculty_id, course_id)
                    VALUES (%s, %s)
                    ON CONFLICT (faculty_id, course_id) DO NOTHING
                    RETURNING assignment_id
                """, (faculty_id, course_id))
                arow = self.cur.fetchone()
                if not arow:
                    self.cur.execute(
                        "SELECT assignment_id FROM faculty_course_map WHERE faculty_id=%s AND course_id=%s",
                        (faculty_id, course_id))
                    arow = self.cur.fetchone()
                assignment_id = arow[0]

                # Batch
                self.cur.execute(
                    "SELECT batch_id FROM student_batch WHERE sub_batch=%s AND section=%s",
                    (entry['sub_batch'], entry['section']))
                batch_row = self.cur.fetchone()
                if not batch_row:
                    skipped += 1
                    continue
                batch_id = batch_row[0]

                # Room
                room_id = None
                if entry.get('room_number'):
                    self.cur.execute("SELECT room_id FROM room WHERE room_number=%s", (entry['room_number'],))
                    rrow = self.cur.fetchone()
                    if rrow:
                        room_id = rrow[0]

                # Slot
                self.cur.execute(
                    "SELECT slot_id FROM time_slot WHERE day_of_week=%s AND start_time=%s::time",
                    (entry['day_of_week'], entry['start_time']))
                srow = self.cur.fetchone()
                if not srow:
                    skipped += 1
                    continue
                slot_id = srow[0]

                self.cur.execute("""
                    INSERT INTO master_timetable
                        (assignment_id, batch_id, room_id, slot_id, is_moved, original_slot_group)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (assignment_id, batch_id, slot_id) DO NOTHING
                """, (assignment_id, batch_id, room_id, slot_id,
                      entry.get('is_moved', False), entry.get('original_slot_group')))
                restored += 1
            except Exception:
                skipped += 1
                continue

        self.conn.commit()
        return restored, skipped

    def delete_snapshot(self, snapshot_id):
        """Delete a snapshot."""
        self.cur.execute("DELETE FROM timetable_snapshot WHERE snapshot_id = %s", (snapshot_id,))
        self.conn.commit()

    # =========================================================================
    # STORE INPUT DATA: Excel courses → PostgreSQL entity tables
    # =========================================================================

    def store_input_data(self, courses):
        """
        Take the in-memory courses list (from parse_excel) and mirror it to
        PostgreSQL entity tables.

        The courses list stays in RAM — this method only INSERTs copies into
        the database for persistence.

        Args:
            courses: List of course dicts from parse_excel()
                     Each dict has: batch, sub_batch, row_sec, course_code,
                     course_name, ltpc, type, faculty, room, is_core, original_slot
        """
        try:
            # Clear previous run data from result tables only
            self.cur.execute("TRUNCATE master_timetable CASCADE;")
            self.cur.execute("TRUNCATE constraint_violation_log CASCADE;")

            # 1. Extract and insert unique faculties
            faculties = set()
            for c in courses:
                fac = c.get('faculty', '').strip()
                if fac and fac.lower() != 'nan':
                    faculties.add(fac)

            fac_count = 0
            for fac in sorted(faculties):
                self.cur.execute(
                    """INSERT INTO faculty (short_name)
                       VALUES (%s)
                       ON CONFLICT (short_name) DO NOTHING
                       RETURNING faculty_id""",
                    (fac,)
                )
                row = self.cur.fetchone()
                if row:
                    self._faculty_cache[fac] = row[0]
                    fac_count += 1
                else:
                    # Already exists, fetch the ID
                    self.cur.execute(
                        "SELECT faculty_id FROM faculty WHERE short_name = %s",
                        (fac,)
                    )
                    self._faculty_cache[fac] = self.cur.fetchone()[0]

            # 2. Extract and insert unique courses
            course_codes_seen = set()
            course_count = 0
            for c in courses:
                code = c.get('course_code', '').strip()
                if not code or code.lower() == 'nan' or code in course_codes_seen:
                    continue
                course_codes_seen.add(code)

                # Parse L-T-P-C
                ltpc = c.get('ltpc', '').strip()
                l_hrs, t_hrs, p_hrs, creds = 0, 0, 0, 0
                ltpc_match = re.match(r'(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)', ltpc)
                if ltpc_match:
                    l_hrs = int(ltpc_match.group(1))
                    t_hrs = int(ltpc_match.group(2))
                    p_hrs = int(ltpc_match.group(3))
                    creds = int(ltpc_match.group(4))

                # Normalize course type
                c_type = c.get('type', 'Core').strip()
                if c_type.lower() == 'nan' or not c_type:
                    c_type = 'Core'

                # Clean course name (remove section annotations)
                name = c.get('course_name', '').strip()
                clean_name = re.sub(r'\s*\(Sec\s*[A-Za-z0-9]+\)', '', name).strip()
                clean_name = re.sub(r'\s*\[\*Moved from .*?\*\]', '', clean_name).strip()

                self.cur.execute(
                    """INSERT INTO course (course_code, course_name, lecture_hrs,
                       tutorial_hrs, practical_hrs, credits, ltpc, course_type)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (course_code) DO NOTHING
                       RETURNING course_id""",
                    (code, clean_name, l_hrs, t_hrs, p_hrs, creds, ltpc, c_type)
                )
                row = self.cur.fetchone()
                if row:
                    self._course_cache[code] = row[0]
                    course_count += 1
                else:
                    self.cur.execute(
                        "SELECT course_id FROM course WHERE course_code = %s",
                        (code,)
                    )
                    self._course_cache[code] = self.cur.fetchone()[0]

            # 3. Extract and insert unique rooms
            rooms = set()
            for c in courses:
                room = c.get('room', '').strip()
                if room and room.lower() != 'nan':
                    rooms.add(room)

            # Room capacity lookup (imported from generator)
            try:
                from generate_timetable import ROOM_CAPACITIES
            except ImportError:
                ROOM_CAPACITIES = {}

            # Also include all configured rooms so reassigned rooms can always map to room_id
            room_candidates = set(rooms) | set(ROOM_CAPACITIES.keys())

            room_count = 0
            for room in sorted(room_candidates):
                capacity = ROOM_CAPACITIES.get(room, 0)
                if capacity == 0:
                    continue  # Explicitly skip any zero-capacity/dropped rooms (like LAB A-SF)
                
                self.cur.execute(
                    """INSERT INTO room (room_number, capacity)
                       VALUES (%s, %s)
                       ON CONFLICT (room_number) DO UPDATE
                       SET capacity = EXCLUDED.capacity
                       RETURNING room_id""",
                    (room, capacity)
                )
                row = self.cur.fetchone()
                if row:
                    self._room_cache[room] = row[0]
                    room_count += 1
                else:
                    self.cur.execute(
                        "SELECT room_id FROM room WHERE room_number = %s",
                        (room,)
                    )
                    self._room_cache[room] = self.cur.fetchone()[0]

            # Safety net: ensure cache includes all currently persisted rooms
            self.cur.execute("SELECT room_number, room_id FROM room")
            for room_number, room_id in self.cur.fetchall():
                self._room_cache[room_number] = room_id

            # 4. Extract and insert unique batches
            batches = set()
            for c in courses:
                sb = c.get('sub_batch', '').strip()
                sec = c.get('row_sec', 'All').strip()
                batch_name = c.get('batch', '').strip()
                if sb and sb.lower() != 'nan':
                    batches.add((batch_name, sb, sec))

            batch_count = 0
            for (batch_name, sb, sec) in sorted(batches):
                self.cur.execute(
                    """INSERT INTO student_batch (program_name, sub_batch, section)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (sub_batch, section) DO NOTHING
                       RETURNING batch_id""",
                    (batch_name, sb, sec)
                )
                row = self.cur.fetchone()
                if row:
                    self._batch_cache[(sb, sec)] = row[0]
                    batch_count += 1
                else:
                    self.cur.execute(
                        "SELECT batch_id FROM student_batch WHERE sub_batch = %s AND section = %s",
                        (sb, sec)
                    )
                    self._batch_cache[(sb, sec)] = self.cur.fetchone()[0]

            # 5. Build Faculty↔Course mappings
            fac_course_pairs = set()
            for c in courses:
                fac = c.get('faculty', '').strip()
                code = c.get('course_code', '').strip()
                if (fac and fac.lower() != 'nan' and
                        code and code.lower() != 'nan'):
                    fac_course_pairs.add((fac, code))

            assignment_count = 0
            for (fac, code) in sorted(fac_course_pairs):
                fac_id = self._faculty_cache.get(fac)
                course_id = self._course_cache.get(code)
                if fac_id is None or course_id is None:
                    continue

                self.cur.execute(
                    """INSERT INTO faculty_course_map (faculty_id, course_id)
                       VALUES (%s, %s)
                       ON CONFLICT (faculty_id, course_id) DO NOTHING
                       RETURNING assignment_id""",
                    (fac_id, course_id)
                )
                row = self.cur.fetchone()
                if row:
                    self._assignment_cache[(fac_id, course_id)] = row[0]
                    assignment_count += 1
                else:
                    self.cur.execute(
                        """SELECT assignment_id FROM faculty_course_map
                           WHERE faculty_id = %s AND course_id = %s""",
                        (fac_id, course_id)
                    )
                    self._assignment_cache[(fac_id, course_id)] = self.cur.fetchone()[0]

            # 6. Build Batch↔Course mappings
            batch_course_pairs = set()
            for c in courses:
                sb = c.get('sub_batch', '').strip()
                sec = c.get('row_sec', 'All').strip()
                code = c.get('course_code', '').strip()
                if (sb and sb.lower() != 'nan' and
                        code and code.lower() != 'nan'):
                    batch_course_pairs.add((sb, sec, code))

            bc_count = 0
            for (sb, sec, code) in sorted(batch_course_pairs):
                batch_id = self._batch_cache.get((sb, sec))
                course_id = self._course_cache.get(code)
                if batch_id is None or course_id is None:
                    continue

                self.cur.execute(
                    """INSERT INTO batch_course_map (batch_id, course_id)
                       VALUES (%s, %s)
                       ON CONFLICT (batch_id, course_id) DO NOTHING""",
                    (batch_id, course_id)
                )
                bc_count += 1

            # 7. Cache time slot IDs
            self._load_slot_cache()

            self.conn.commit()
            self._log(f"  ✓ {fac_count} faculty, {course_count} courses, "
                  f"{room_count} rooms, {batch_count} batches loaded")
            self._log(f"  ✓ {assignment_count} faculty-course mappings, "
                  f"{bc_count} batch-course mappings created")

        except Exception as e:
            self.conn.rollback()
            self._log(f"  ✗ Error storing input data: {e}")
            raise

    def _load_slot_cache(self):
        """Load time_slot table into memory cache for fast lookups."""
        self.cur.execute(
            "SELECT slot_id, day_of_week, start_time, slot_group FROM time_slot"
        )
        for row in self.cur.fetchall():
            slot_id, day, start_time, slot_group = row
            # Convert time to string for easy matching
            time_str = start_time.strftime('%H:%M') if hasattr(start_time, 'strftime') else str(start_time)[:5]
            self._slot_cache[(day, time_str)] = slot_id

            if slot_group not in self._slot_group_cache:
                self._slot_group_cache[slot_group] = []
            self._slot_group_cache[slot_group].append(slot_id)

    # =========================================================================
    # LOAD ACTIVE CONSTRAINTS: Read constraints from DB for CSP solver
    # =========================================================================

    def load_active_constraints(self):
        """
        Read active scheduling constraints from the database.

        Returns:
            List of constraint dicts with keys:
            - constraint_id, constraint_name, constraint_type, scope,
              rule_description, enforcement_level, is_active, parameters_json
        """
        self.cur.execute(
            """SELECT constraint_id, constraint_name, constraint_type, scope,
                      rule_description, enforcement_level, is_active, parameters_json
               FROM scheduling_constraint
               WHERE is_active = TRUE
               ORDER BY constraint_type, constraint_id"""
        )
        columns = [desc[0] for desc in self.cur.description]
        constraints = []
        for row in self.cur.fetchall():
            constraints.append(dict(zip(columns, row)))
        return constraints

    # =========================================================================
    # STORE RESULTS: Solver output → Master_Timetable + Violation Log
    # =========================================================================

    def store_results(self, final_courses, unresolved, slot_matrix=None, validated_violations=None):
        """
        Take the in-memory solver output and write it to PostgreSQL.

        Args:
            final_courses: List of course dicts with 'final_slot' added by solver
            unresolved: List of unresolved conflict dicts from CSP solver
            slot_matrix: Dict mapping day → {period → slot_group}
            validated_violations: List of violation strings computed by validate()
        """
        try:
            # Clear previous results
            self.cur.execute("TRUNCATE master_timetable CASCADE;")
            self.cur.execute("TRUNCATE constraint_violation_log CASCADE;")

            inserted = 0
            skipped = 0
            deduped = 0
            violations_logged = 0

            # Track seen combinations to avoid duplicate inserts
            seen_entries = set()

            for c in final_courses:
                final_slot = c.get('final_slot', '').strip()
                if not final_slot or final_slot == 'Slot-Free':
                    continue

                fac = c.get('faculty', '').strip()
                code = c.get('course_code', '').strip()
                sb = c.get('sub_batch', '').strip()
                sec = c.get('row_sec', 'All').strip()
                room = c.get('room', '').strip()
                original_slot = c.get('original_slot', '').strip()
                is_moved = c.get('moved', False)

                # Look up IDs from cache
                fac_id = self._faculty_cache.get(fac)
                course_id = self._course_cache.get(code)
                batch_id = self._batch_cache.get((sb, sec))
                room_id = self._room_cache.get(room) if room and room.lower() != 'nan' else None
                if room_id is None and room and room.lower() not in ('nan', 'tbd'):
                    # Fallback in case cache missed a persisted room.
                    self.cur.execute(
                        "SELECT room_id FROM room WHERE room_number = %s",
                        (room,)
                    )
                    row = self.cur.fetchone()
                    if row:
                        room_id = row[0]
                        self._room_cache[room] = room_id

                if fac_id is None or course_id is None or batch_id is None:
                    skipped += 1
                    continue

                assignment_id = self._assignment_cache.get((fac_id, course_id))
                if assignment_id is None:
                    skipped += 1
                    continue

                # Get all slot_ids for this slot group
                slot_ids = self._slot_group_cache.get(final_slot, [])
                if not slot_ids:
                    skipped += 1
                    continue

                # Insert one row per time slot in the slot group
                for slot_id in slot_ids:
                    # Dedup by (assignment_id, batch_id, slot_id) — matches UNIQUE constraint
                    entry_key = (assignment_id, batch_id, slot_id)
                    if entry_key in seen_entries:
                        deduped += 1
                        continue
                    seen_entries.add(entry_key)

                    try:
                        self.cur.execute("SAVEPOINT sp_insert")
                        self.cur.execute(
                            """INSERT INTO master_timetable
                               (assignment_id, batch_id, room_id, slot_id,
                                 is_moved, original_slot_group)
                               VALUES (%s, %s, %s, %s, %s, %s)
                               ON CONFLICT (assignment_id, batch_id, slot_id) DO NOTHING""",
                            (assignment_id, batch_id, room_id, slot_id,
                             is_moved, original_slot)
                        )
                        rows_affected = self.cur.rowcount  # capture BEFORE release
                        self.cur.execute("RELEASE SAVEPOINT sp_insert")
                        if rows_affected > 0:
                            inserted += 1
                        else:
                            deduped += 1
                    except psycopg2.IntegrityError as e:
                        # Unexpected constraint violation — log it
                        self.cur.execute("ROLLBACK TO SAVEPOINT sp_insert")
                        self.cur.execute("RELEASE SAVEPOINT sp_insert")

                        violation_detail = (
                            f"DB constraint rejected: {str(e).strip()}. "
                            f"Course={code}, Faculty={fac}, Batch={sb} {sec}, "
                            f"Slot={final_slot}"
                        )
                        constraint_id = self._match_constraint(str(e))
                        self.cur.execute(
                            """INSERT INTO constraint_violation_log
                               (constraint_id, severity, violation_detail)
                               VALUES (%s, %s, %s)""",
                            (constraint_id, 'ERROR', violation_detail)
                        )
                        violations_logged += 1
                        skipped += 1

            # Log unresolved conflicts from the CSP solver
            for u in unresolved:
                violation_detail = (
                    f"CSP Solver: {u.get('reason', 'Unknown')}. "
                    f"Superblock={u.get('superblock', 'N/A')}, "
                    f"Assigned={u.get('assigned_slot', 'N/A')}, "
                    f"Conflicts with={u.get('conflicts_with', [])}"
                )
                self.cur.execute(
                    """INSERT INTO constraint_violation_log
                       (constraint_id, severity, violation_detail)
                       VALUES (%s, %s, %s)""",
                    (None, 'WARNING', violation_detail)
                )
                violations_logged += 1
            # Log manual violations from validation step
            if validated_violations:
                for v in validated_violations:
                    self.cur.execute(
                        """INSERT INTO constraint_violation_log
                           (constraint_id, severity, violation_detail)
                           VALUES (%s, %s, %s)""",
                        (None, 'ERROR', v)
                    )
                    violations_logged += 1

            self.conn.commit()
            self._log(f"  ✓ {inserted} timetable entries written to Master_Timetable")
            if deduped:
                self._log(f"  ✓ {deduped} duplicate entries de-duplicated")
            if violations_logged:
                self._log(f"  ⚠ {violations_logged} constraint violations logged")
            else:
                self._log(f"  ✓ All hard constraints satisfied!")
            if skipped:
                self._log(f"  ⚠ {skipped} entries skipped (missing FK reference)")

        except Exception as e:
            self.conn.rollback()
            self._log(f"  ✗ Error storing results: {e}")
            raise

    def _match_constraint(self, error_msg):
        """Match a PostgreSQL error message to a scheduling_constraint row."""
        error_lower = error_msg.lower()

        if 'uq_room_slot' in error_lower:
            name = 'No Room Double-Booking'
        elif 'uq_batch_slot' in error_lower:
            name = 'Core Course Non-Overlap'
        elif 'uq_assignment_slot' in error_lower or 'uq_assignment_batch_slot' in error_lower:
            name = 'No Faculty Double-Booking'
        else:
            return None

        self.cur.execute(
            "SELECT constraint_id FROM scheduling_constraint WHERE constraint_name = %s",
            (name,)
        )
        row = self.cur.fetchone()
        return row[0] if row else None

    # =========================================================================
    # QUERY HELPERS (for web UI and ad-hoc queries)
    # =========================================================================

    def get_master_timetable(self, filters=None):
        """
        Query the v_master_timetable view with optional filters.

        Args:
            filters: Dict with optional keys: day_of_week, sub_batch, faculty, room
                     Values can be a single string or a list of strings for multi-select.

        Returns:
            List of dicts representing timetable rows
        """
        query = "SELECT * FROM v_master_timetable WHERE 1=1"
        params = []

        if filters:
            for key, col in [('day_of_week', 'day_of_week'),
                             ('sub_batch', 'sub_batch'),
                             ('faculty', 'faculty_short_name'),
                             ('room', 'room_number')]:
                val = filters.get(key)
                if val:
                    if isinstance(val, list):
                        placeholders = ','.join(['%s'] * len(val))
                        query += f" AND {col} IN ({placeholders})"
                        params.extend(val)
                    else:
                        query += f" AND {col} = %s"
                        params.append(val)

        query += " ORDER BY day_of_week, start_time, sub_batch"

        self.cur.execute(query, params)
        columns = [desc[0] for desc in self.cur.description]
        results = []
        for row in self.cur.fetchall():
            results.append(dict(zip(columns, row)))
        return results

    def get_faculty_schedule(self, faculty_short_name=None):
        """Query the v_faculty_schedule view."""
        if faculty_short_name:
            self.cur.execute(
                "SELECT * FROM v_faculty_schedule WHERE faculty = %s",
                (faculty_short_name,)
            )
        else:
            self.cur.execute("SELECT * FROM v_faculty_schedule")

        columns = [desc[0] for desc in self.cur.description]
        return [dict(zip(columns, row)) for row in self.cur.fetchall()]

    def get_room_utilization(self):
        """Query the v_room_utilization view."""
        self.cur.execute("SELECT * FROM v_room_utilization")
        columns = [desc[0] for desc in self.cur.description]
        return [dict(zip(columns, row)) for row in self.cur.fetchall()]

    def get_violations(self):
        """Get all logged constraint violations."""
        self.cur.execute(
            """SELECT cvl.violation_id, sc.constraint_name, sc.constraint_type,
                      cvl.severity, cvl.violation_detail, cvl.detected_at
               FROM constraint_violation_log cvl
               LEFT JOIN scheduling_constraint sc ON cvl.constraint_id = sc.constraint_id
               ORDER BY cvl.detected_at DESC"""
        )
        columns = [desc[0] for desc in self.cur.description]
        return [dict(zip(columns, row)) for row in self.cur.fetchall()]

    def get_constraints(self):
        """Get all scheduling constraints."""
        self.cur.execute(
            """SELECT constraint_id, constraint_name, constraint_type, scope,
                      rule_description, enforcement_level, is_active, parameters_json
               FROM scheduling_constraint
               ORDER BY constraint_type, constraint_id"""
        )
        columns = [desc[0] for desc in self.cur.description]
        return [dict(zip(columns, row)) for row in self.cur.fetchall()]

    def get_stats(self):
        """Get quick stats about what's in the database."""
        stats = {}
        for table in ['faculty', 'course', 'room', 'student_batch',
                       'faculty_course_map', 'batch_course_map',
                       'master_timetable', 'constraint_violation_log',
                       'scheduling_constraint', 'time_slot']:
            self.cur.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = self.cur.fetchone()[0]
        return stats

    # =========================================================================
    # CRUD: Faculty
    # =========================================================================

    def get_all_faculty(self):
        """Return all faculty rows as list of dicts."""
        self.cur.execute(
            "SELECT faculty_id, short_name, name, department, email FROM faculty ORDER BY short_name")
        columns = [desc[0] for desc in self.cur.description]
        return [dict(zip(columns, row)) for row in self.cur.fetchall()]

    def add_faculty(self, short_name, name=None, department=None, email=None):
        """Insert a new faculty member."""
        self.cur.execute(
            """INSERT INTO faculty (short_name, name, department, email)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (short_name) DO UPDATE SET
                   name = COALESCE(EXCLUDED.name, faculty.name),
                   department = COALESCE(EXCLUDED.department, faculty.department),
                   email = COALESCE(EXCLUDED.email, faculty.email)
               RETURNING faculty_id""",
            (short_name, name, department, email))
        self.conn.commit()
        return self.cur.fetchone()[0]

    def update_faculty(self, faculty_id, **kwargs):
        """Update faculty fields. Accepts short_name, name, department, email."""
        allowed = {'short_name', 'name', 'department', 'email'}
        sets = []
        vals = []
        for k, v in kwargs.items():
            if k in allowed:
                sets.append(f"{k} = %s")
                vals.append(v)
        if not sets:
            return
        vals.append(faculty_id)
        self.cur.execute(f"UPDATE faculty SET {', '.join(sets)} WHERE faculty_id = %s", vals)
        self.conn.commit()

    def delete_faculty(self, faculty_id):
        """Delete a faculty member (cascades to assignments)."""
        self.cur.execute("DELETE FROM faculty WHERE faculty_id = %s", (faculty_id,))
        self.conn.commit()

    # =========================================================================
    # CRUD: Course
    # =========================================================================

    def get_all_courses(self):
        """Return all course rows as list of dicts."""
        self.cur.execute(
            """SELECT course_id, course_code, course_name, lecture_hrs,
                      tutorial_hrs, practical_hrs, credits, ltpc, course_type
               FROM course ORDER BY course_code""")
        columns = [desc[0] for desc in self.cur.description]
        return [dict(zip(columns, row)) for row in self.cur.fetchall()]

    def add_course(self, course_code, course_name, ltpc='', course_type='Core',
                   lecture_hrs=0, tutorial_hrs=0, practical_hrs=0, credits=0):
        """Insert a new course."""
        self.cur.execute(
            """INSERT INTO course (course_code, course_name, lecture_hrs, tutorial_hrs,
                                  practical_hrs, credits, ltpc, course_type)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (course_code) DO UPDATE SET
                   course_name = EXCLUDED.course_name, ltpc = EXCLUDED.ltpc,
                   course_type = EXCLUDED.course_type,
                   lecture_hrs = EXCLUDED.lecture_hrs, tutorial_hrs = EXCLUDED.tutorial_hrs,
                   practical_hrs = EXCLUDED.practical_hrs, credits = EXCLUDED.credits
               RETURNING course_id""",
            (course_code, course_name, lecture_hrs, tutorial_hrs,
             practical_hrs, credits, ltpc, course_type))
        self.conn.commit()
        return self.cur.fetchone()[0]

    def update_course(self, course_id, **kwargs):
        """Update course fields."""
        allowed = {'course_code', 'course_name', 'ltpc', 'course_type',
                   'lecture_hrs', 'tutorial_hrs', 'practical_hrs', 'credits'}
        sets = []
        vals = []
        for k, v in kwargs.items():
            if k in allowed:
                sets.append(f"{k} = %s")
                vals.append(v)
        if not sets:
            return
        vals.append(course_id)
        self.cur.execute(f"UPDATE course SET {', '.join(sets)} WHERE course_id = %s", vals)
        self.conn.commit()

    def delete_course(self, course_id):
        """Delete a course (cascades to assignments and batch maps)."""
        self.cur.execute("DELETE FROM course WHERE course_id = %s", (course_id,))
        self.conn.commit()

    # =========================================================================
    # CRUD: Batch (Student Batch)
    # =========================================================================

    def get_all_batches(self):
        """Return all student_batch rows as list of dicts."""
        self.cur.execute(
            """SELECT batch_id, program_name, sub_batch, section, headcount
               FROM student_batch ORDER BY sub_batch, section""")
        columns = [desc[0] for desc in self.cur.description]
        return [dict(zip(columns, row)) for row in self.cur.fetchall()]

    def add_batch(self, sub_batch, section='All', program_name='', headcount=0):
        """Insert a new student batch."""
        self.cur.execute(
            """INSERT INTO student_batch (sub_batch, section, program_name, headcount)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (sub_batch, section) DO UPDATE SET
                   program_name = EXCLUDED.program_name, headcount = EXCLUDED.headcount
               RETURNING batch_id""",
            (sub_batch, section, program_name, headcount))
        self.conn.commit()
        return self.cur.fetchone()[0]

    def update_batch_fields(self, batch_id, **kwargs):
        """Update batch fields. Accepts sub_batch, section, program_name, headcount."""
        allowed = {'sub_batch', 'section', 'program_name', 'headcount'}
        sets = []
        vals = []
        for k, v in kwargs.items():
            if k in allowed:
                sets.append(f"{k} = %s")
                vals.append(v)
        if not sets:
            return
        vals.append(batch_id)
        self.cur.execute(f"UPDATE student_batch SET {', '.join(sets)} WHERE batch_id = %s", vals)
        self.conn.commit()

    def delete_batch(self, batch_id):
        """Delete a student batch (cascades)."""
        self.cur.execute("DELETE FROM student_batch WHERE batch_id = %s", (batch_id,))
        self.conn.commit()

    # =========================================================================
    # Timetable Entry Move (for drag-and-drop)
    # =========================================================================

    def move_timetable_entries(self, moves):
        """Move timetable entries to new slots.

        Args:
            moves: list of dicts with 'timetable_id' and 'new_slot_id'

        Returns:
            (moved_count, errors)
        """
        moved = 0
        errors = []
        for m in moves:
            try:
                self.cur.execute(
                    """UPDATE master_timetable
                       SET slot_id = %s, is_moved = TRUE
                       WHERE timetable_id = %s""",
                    (m['new_slot_id'], m['timetable_id']))
                if self.cur.rowcount > 0:
                    moved += 1
            except Exception as e:
                errors.append(f"Entry {m['timetable_id']}: {e}")
                self.conn.rollback()
                return moved, errors
        self.conn.commit()
        return moved, errors

    def get_slot_id(self, day_of_week, start_time):
        """Look up a slot_id by day and start time string (e.g. '08:00')."""
        self.cur.execute(
            "SELECT slot_id FROM time_slot WHERE day_of_week = %s AND start_time = %s::time",
            (day_of_week, start_time))
        row = self.cur.fetchone()
        return row[0] if row else None

    # =========================================================================
    # Snapshot preference map (for warm-start seeding)
    # =========================================================================

    def get_snapshot_preference_map(self, snapshot_id):
        """Load a snapshot and return a preference map for warm-starting the CSP solver.

        Returns:
            dict: {(course_code, sub_batch, section): slot_group}
        """
        import json
        row = self.get_snapshot(snapshot_id)
        if not row:
            return {}
        data = row[8]  # snapshot_data
        if isinstance(data, str):
            data = json.loads(data)
        pref = {}
        for entry in data:
            key = (entry.get('course_code', ''),
                   entry.get('sub_batch', ''),
                   entry.get('section', ''))
            sg = entry.get('slot_group', '')
            if key[0] and sg and sg != 'Slot-Free':
                pref[key] = sg
        return pref

    # =========================================================================
    # CONNECTION MANAGEMENT
    # =========================================================================

    def close(self):
        """Close database connection."""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        self._log("  ✓ Database connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
