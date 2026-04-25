import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()
try:
    conn = psycopg2.connect(dbname=os.getenv('DB_NAME', 'timetable_generator_db'), user=os.getenv('DB_USER', 'postgres'), password=os.getenv('DB_PASSWORD', ''), host=os.getenv('DB_HOST', 'localhost'), port=os.getenv('DB_PORT', '5432'))
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM master_timetable;')
    print('master_timetable count:', cur.fetchone()[0])
    cur.execute('SELECT COUNT(*) FROM v_master_timetable;')
    print('v_master_timetable count:', cur.fetchone()[0])
except Exception as e:
    print('Error:', e)
