"""Seed the database with generated synthetic data."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import polars as pl
import psycopg2
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path("ml/data/synthetic")
DB_URL = "postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict"
NOW = datetime.now(timezone.utc).isoformat()

# Complete mapping for all enum values used in the project
ENUM_MAP = {
    # UserRole
    "UserRole.PHARMACIST": "pharmacist", "UserRole.P": "pharmacist",
    "UserRole.MANAGER": "manager", "UserRole.M": "manager",
    "UserRole.ADMIN": "admin", "UserRole.A": "admin",
    # BatchStatus
    "BatchStatus.AVAILABLE": "available", "BatchStatus.A": "available",
    "BatchStatus.RESERVED": "reserved", "BatchStatus.R": "reserved",
    "BatchStatus.EXPIRED": "expired", "BatchStatus.E": "expired",
    "BatchStatus.RECALLED": "recalled", "BatchStatus.Q": "quarantine",
    # MovementType
    "MovementType.IN": "in", "MovementType.I": "in",
    "MovementType.OUT": "out", "MovementType.O": "out",
    "MovementType.ADJUSTMENT": "adjustment",
    "MovementType.TRANSFER": "transfer",
    "MovementType.LOSS": "loss",
    "MovementType.EXPIRED": "expired",
    "MovementType.RECALLED": "recalled",
    # AlertType
    "AlertType.SHORTAGE_RISK": "shortage_risk", "AlertType.S": "shortage_risk",
    "AlertType.EXPIRY_RISK": "expiry_risk", "AlertType.E": "expiry_risk",
    "AlertType.OVERSTOCK": "overstock", "AlertType.O": "overstock",
    "AlertType.REORDER_POINT": "reorder_point",
    # AlertSeverity
    "AlertSeverity.INFO": "info", "AlertSeverity.I": "info",
    "AlertSeverity.WARNING": "warning", "AlertSeverity.W": "warning",
    "AlertSeverity.CRITICAL": "critical", "AlertSeverity.C": "critical",
    # PrescriptionType
    "PrescriptionType.ROUTINE": "routine", "PrescriptionType.R": "routine",
    "PrescriptionType.EMERGENCY": "emergency", "PrescriptionType.E": "emergency",
    "PrescriptionType.PROPHYLACTIC": "prophylactic", "PrescriptionType.P": "prophylactic",
    # Department
    "Department.ICU": "icu", "Department.I": "icu",
    "Department.ER": "er", "Department.E": "er",
    "Department.WARD": "ward", "Department.W": "ward",
    "Department.OUTPATIENT": "outpatient", "Department.O": "outpatient",
    # ProductCategory
    "ProductCategory.ANTIBIOTIC": "antibiotic", "ProductCategory.A": "antibiotic",
    "ProductCategory.ANALGESIC": "analgesic",
    "ProductCategory.ANTITHROMBOTIC": "antithrombotic",
    "ProductCategory.BETA_BLOCKER": "beta_blocker",
    "ProductCategory.PPI": "ppi",
    "ProductCategory.BRONCHODILATOR": "bronchodilator",
    "ProductCategory.PSYCHOLEPTIC": "psycholeptic",
    "ProductCategory.ACE_INHIBITOR": "ace_inhibitor",
    "ProductCategory.CORTICOSTEROID": "corticosteroid",
    "ProductCategory.OTHER": "other",
}

def fix_enum(val):
    if val is None:
        return None
    if not isinstance(val, str):
        return val
    if val in ENUM_MAP:
        return ENUM_MAP[val]
    if "." in val:
        return val.rsplit(".", 1)[1].lower()
    return val

def main():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Truncate all tables to start clean
    print("Cleaning existing data...")
    for table in ["alerts", "consumption", "stock_movements", "inventory_batches",
                   "products", "warehouses", "users"]:
        cur.execute(f"TRUNCATE {table} CASCADE")
    print("  Done.\n")

    # Users
    print("Seeding users...")
    df = pl.read_parquet(DATA_DIR / "users.parquet")
    for row in df.iter_rows(named=True):
        cur.execute("""
            INSERT INTO users (id, email, hashed_password, full_name, role, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (row["id"], row["email"], row["hashed_password"], row["full_name"],
              fix_enum(row["role"]), row["is_active"], row.get("created_at") or NOW))
    print(f"  {len(df)} users")

    # Warehouses
    print("Seeding warehouses...")
    df = pl.read_parquet(DATA_DIR / "warehouses.parquet")
    for row in df.iter_rows(named=True):
        cur.execute("""
            INSERT INTO warehouses (id, name, location, is_primary, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (row["id"], row["name"], row["location"], row["is_primary"],
              row.get("created_at") or NOW))
    print(f"  {len(df)} warehouses")

    # Products
    print("Seeding products...")
    df = pl.read_parquet(DATA_DIR / "products.parquet")
    for row in df.iter_rows(named=True):
        cur.execute("""
            INSERT INTO products (id, sku, name, generic_name, category, atc_code, unit,
                unit_cost, min_stock_level, max_stock_level, lead_time_days,
                controlled_substance, is_active, product_metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (row["id"], row["sku"], row["name"], row["generic_name"],
              fix_enum(row["category"]), row["atc_code"], row["unit"],
              row["unit_cost"], row["min_stock_level"], row["max_stock_level"],
              row["lead_time_days"], row["controlled_substance"], row["is_active"],
              row["metadata"], row.get("created_at") or NOW))
    print(f"  {len(df)} products")

    # Inventory batches
    print("Seeding inventory batches...")
    df = pl.read_parquet(DATA_DIR / "inventory_batches.parquet")
    for row in df.iter_rows(named=True):
        cur.execute("""
            INSERT INTO inventory_batches (id, product_id, warehouse_id, batch_number,
                quantity, expiry_date, manufacture_date, unit_cost, status, received_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (row["id"], row["product_id"], row["warehouse_id"], row["batch_number"],
              row["quantity"], row["expiry_date"], row["manufacture_date"],
              row["unit_cost"], fix_enum(row["status"]),
              row["received_at"], row.get("created_at") or NOW))
    print(f"  {len(df)} batches")

    # Stock movements (batch insert)
    print("Seeding stock movements...")
    df = pl.read_parquet(DATA_DIR / "stock_movements.parquet")
    rows = []
    for row in df.iter_rows(named=True):
        rows.append((
            row["id"], row["batch_id"], row.get("user_id"), row["quantity_change"],
            fix_enum(row["movement_type"]), row.get("reference_type"),
            row.get("reference_id"), row.get("notes"), row.get("created_at") or NOW,
        ))
    from psycopg2.extras import execute_values
    execute_values(cur, """
        INSERT INTO stock_movements (id, batch_id, user_id, quantity_change,
            movement_type, reference_type, reference_id, notes, created_at)
        VALUES %s
    """, rows, page_size=5000)
    print(f"  {len(df)} movements")

    # Consumption (batch insert)
    print("Seeding consumption...")
    df = pl.read_parquet(DATA_DIR / "consumption.parquet")
    rows = []
    for row in df.iter_rows(named=True):
        rows.append((
            row["id"], row["product_id"], row["consumption_date"], row["quantity"],
            fix_enum(row["department"]), fix_enum(row["prescription_type"]),
            row["context"], row.get("created_at") or NOW,
        ))
    execute_values(cur, """
        INSERT INTO consumption (id, product_id, consumption_date, quantity,
            department, prescription_type, context, created_at)
        VALUES %s
    """, rows, page_size=10000)
    print(f"  {len(df)} consumption records")

    # Alerts
    print("Seeding alerts...")
    df = pl.read_parquet(DATA_DIR / "alerts.parquet")
    for row in df.iter_rows(named=True):
        cur.execute("""
            INSERT INTO alerts (id, product_id, alert_type, severity, message,
                alert_metadata, acknowledged, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (row["id"], row["product_id"],               fix_enum(row["alert_type"]),
              fix_enum(row["severity"]), row["message"], row.get("metadata"),
              row.get("acknowledged") or False, row.get("created_at") or NOW))
    print(f"  {len(df)} alerts")

    conn.commit()
    print("\nAll data seeded!")

    # Verify
    print("\nVerification:")
    for table in ["users", "warehouses", "products", "inventory_batches",
                   "stock_movements", "consumption", "alerts"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table:25s} {cur.fetchone()[0]:>10,}")

    conn.close()

if __name__ == "__main__":
    main()
