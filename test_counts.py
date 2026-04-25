import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
try:
    conn = psycopg2.connect(dbname=os.getenv('DB_NAME', 'timetable_generator_db'), user=os.getenv('DB_USER', 'postgres'), password=os.getenv('DB_PASSWORD', ''), host=os.getenv('DB_HOST', 'localhost'), port=os.getenv('DB_PORT', '5432'))
    cur = conn.cursor()
    tables = ['faculty', 'course', 'student_batch', 'time_slot', 'faculty_course_map', 'room', 'master_timetable']
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t};")
        print(f"{t}: {cur.fetchone()[0]}")
except Exception as e:
    print('Error:', e)
