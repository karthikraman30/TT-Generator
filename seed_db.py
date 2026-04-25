import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
try:
    conn = psycopg2.connect(dbname=os.getenv('DB_NAME', 'timetable_generator_db'), user=os.getenv('DB_USER', 'postgres'), password=os.getenv('DB_PASSWORD', ''), host=os.getenv('DB_HOST', 'localhost'), port=os.getenv('DB_PORT', '5432'))
    conn.autocommit = True
    cur = conn.cursor()
    
    with open('database/seed_time_slots.sql', 'r') as f:
        cur.execute(f.read())
    print("Seeded time slots.")
    
    with open('database/seed_constraints.sql', 'r') as f:
        cur.execute(f.read())
    print("Seeded constraints.")
    
except Exception as e:
    print('Error:', e)
