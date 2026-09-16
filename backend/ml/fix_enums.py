"""Fix enum values in database to use UPPERCASE (what SQLAlchemy expects)."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import psycopg2

conn = psycopg2.connect("postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict")
cur = conn.cursor()

fixes = [
    ("users", "role", "userrole"),
    ("products", "category", "productcategory"),
    ("inventory_batches", "status", "batchstatus"),
    ("stock_movements", "movement_type", "movementtype"),
    ("consumption", "department", "department"),
    ("consumption", "prescription_type", "prescriptiontype"),
    ("alerts", "alert_type", "alerttype"),
    ("alerts", "severity", "alertseverity"),
]

for table, col, enum_type in fixes:
    print(f"Fixing {table}.{col}...")
    # Convert lowercase -> UPPERCASE via TEXT intermediate
    cur.execute(f"""
        ALTER TABLE {table}
        ALTER COLUMN {col} TYPE TEXT
        USING {col}::TEXT
    """)
    cur.execute(f"""
        UPDATE {table} SET {col} = UPPER({col})
    """)
    cur.execute(f"""
        ALTER TABLE {table}
        ALTER COLUMN {col} TYPE {enum_type}
        USING {col}::{enum_type}
    """)
    print(f"  Done")

conn.commit()
print("\nAll enum values fixed to UPPERCASE!")

# Verify
cur.execute("""
    SELECT t.typname, e.enumlabel 
    FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid 
    WHERE t.typname = 'userrole'
""")
print("\nuserrole values:", [row[1] for row in cur.fetchall()])

conn.close()
