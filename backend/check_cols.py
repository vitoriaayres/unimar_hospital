import psycopg2
conn = psycopg2.connect('postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict')
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'inventory_batches' ORDER BY ordinal_position")
for r in cur.fetchall():
    print(r[0])
conn.close()
