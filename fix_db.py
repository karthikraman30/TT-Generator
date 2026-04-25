import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'timetable_generator_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # Drop views
    cur.execute("DROP VIEW IF EXISTS v_master_timetable CASCADE;")
    cur.execute("DROP VIEW IF EXISTS v_faculty_schedule CASCADE;")
    cur.execute("DROP VIEW IF EXISTS v_room_utilization CASCADE;")
    
    # Alter columns
    cur.execute("ALTER TABLE faculty ALTER COLUMN short_name TYPE VARCHAR(100);")
    print("Successfully altered short_name in faculty table.")

    # Recreate views
    view1 = """
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
"""
    cur.execute(view1)
    
    view2 = """
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
"""
    cur.execute(view2)

    view3 = """
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
"""
    cur.execute(view3)

    cur.close()
    conn.close()
    print("Database updated successfully.")
except Exception as e:
    print("Error connecting or altering database:", e)
