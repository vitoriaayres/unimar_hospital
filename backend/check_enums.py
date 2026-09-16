import psycopg2
conn = psycopg2.connect('postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict')
cur = conn.cursor()
cur.execute("SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'department')")
for r in cur.fetchall(): print(r[0])
conn.close()
