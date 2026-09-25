"""Check current enum types in PostgreSQL."""

import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import psycopg2

conn = psycopg2.connect('postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict')
cur = conn.cursor()
cur.execute("""
    SELECT t.typname, e.enumlabel 
    FROM pg_type t 
    JOIN pg_enum e ON t.oid = e.enumtypid 
    ORDER BY t.typname, e.enumsortorder
""")
for row in cur.fetchall():
    print(f'  {row[0]:25s} {row[1]}')
conn.close()
