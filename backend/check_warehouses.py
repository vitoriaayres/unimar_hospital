import psycopg2
conn = psycopg2.connect('postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict')
cur = conn.cursor()
cur.execute("SELECT id, name FROM warehouses")
for r in cur.fetchall(): print(r)
conn.close()
