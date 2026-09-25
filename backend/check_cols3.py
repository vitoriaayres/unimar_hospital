import psycopg2

conn = psycopg2.connect('postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict')
cur = conn.cursor()
cur.execute(
    "SELECT column_name, is_nullable, column_default FROM information_schema.columns WHERE table_name = 'inventory_batches'"
)
for r in cur.fetchall():
    print(r)
print('---')
# Check if warehouses table exists
cur.execute(
    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'warehouses')"
)
print('warehouses exists:', cur.fetchone()[0])
# Check constraints
cur.execute(
    "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'inventory_batches'::regclass"
)
for r in cur.fetchall():
    print(r)
conn.close()
