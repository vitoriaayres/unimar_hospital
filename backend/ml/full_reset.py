"""Full database reset: drop tables, recreate via Alembic, seed with UPPERCASE enums."""

import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import psycopg2

DATA_DIR = Path('ml/data/synthetic')
DB_URL = 'postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict'
NOW = datetime.now(UTC).isoformat()

ENUM_MAP = {
    'UserRole.PHARMACIST': 'pharmacist',
    'UserRole.P': 'pharmacist',
    'pharmacist': 'pharmacist',
    'UserRole.MANAGER': 'manager',
    'UserRole.M': 'manager',
    'manager': 'manager',
    'UserRole.ADMIN': 'admin',
    'UserRole.A': 'admin',
    'admin': 'admin',
    'BatchStatus.AVAILABLE': 'available',
    'BatchStatus.A': 'available',
    'available': 'available',
    'BatchStatus.RESERVED': 'reserved',
    'BatchStatus.R': 'reserved',
    'reserved': 'reserved',
    'BatchStatus.EXPIRED': 'expired',
    'BatchStatus.E': 'expired',
    'expired': 'expired',
    'BatchStatus.RECALLED': 'recalled',
    'BatchStatus.Q': 'quarantine',
    'recalled': 'recalled',
    'quarantine': 'quarantine',
    'MovementType.IN': 'in',
    'MovementType.I': 'in',
    'in': 'in',
    'MovementType.OUT': 'out',
    'MovementType.O': 'out',
    'out': 'out',
    'MovementType.ADJUSTMENT': 'adjustment',
    'adjustment': 'adjustment',
    'MovementType.TRANSFER': 'transfer',
    'transfer': 'transfer',
    'MovementType.LOSS': 'loss',
    'loss': 'loss',
    'MovementType.EXPIRED': 'expired',
    'MovementType.RECALLED': 'recalled',
    'AlertType.SHORTAGE_RISK': 'shortage_risk',
    'AlertType.S': 'shortage_risk',
    'shortage_risk': 'shortage_risk',
    'AlertType.EXPIRY_RISK': 'expiry_risk',
    'AlertType.E': 'expiry_risk',
    'expiry_risk': 'expiry_risk',
    'AlertType.OVERSTOCK': 'overstock',
    'AlertType.O': 'overstock',
    'overstock': 'overstock',
    'AlertType.REORDER_POINT': 'reorder_point',
    'reorder_point': 'reorder_point',
    'AlertSeverity.INFO': 'info',
    'AlertSeverity.I': 'info',
    'info': 'info',
    'AlertSeverity.WARNING': 'warning',
    'AlertSeverity.W': 'warning',
    'warning': 'warning',
    'AlertSeverity.CRITICAL': 'critical',
    'AlertSeverity.C': 'critical',
    'critical': 'critical',
    'PrescriptionType.ROUTINE': 'routine',
    'PrescriptionType.R': 'routine',
    'routine': 'routine',
    'PrescriptionType.EMERGENCY': 'emergency',
    'PrescriptionType.E': 'emergency',
    'emergency': 'emergency',
    'PrescriptionType.PROPHYLACTIC': 'prophylactic',
    'PrescriptionType.P': 'prophylactic',
    'prophylactic': 'prophylactic',
    'Department.ICU': 'icu',
    'Department.I': 'icu',
    'icu': 'icu',
    'Department.ER': 'er',
    'Department.E': 'er',
    'er': 'er',
    'Department.WARD': 'ward',
    'Department.W': 'ward',
    'ward': 'ward',
    'Department.OUTPATIENT': 'outpatient',
    'Department.O': 'outpatient',
    'outpatient': 'outpatient',
    'ProductCategory.ANTIBIOTIC': 'antibiotic',
    'ProductCategory.A': 'antibiotic',
    'antibiotic': 'antibiotic',
    'ProductCategory.ANALGESIC': 'analgesic',
    'analgesic': 'analgesic',
    'ProductCategory.ANTITHROMBOTIC': 'antithrombotic',
    'antithrombotic': 'antithrombotic',
    'ProductCategory.BETA_BLOCKER': 'beta_blocker',
    'beta_blocker': 'beta_blocker',
    'ProductCategory.PPI': 'ppi',
    'ppi': 'ppi',
    'ProductCategory.BRONCHODILATOR': 'bronchodilator',
    'bronchodilator': 'bronchodilator',
    'ProductCategory.PSYCHOLEPTIC': 'psycholeptic',
    'psycholeptic': 'psycholeptic',
    'ProductCategory.ACE_INHIBITOR': 'ace_inhibitor',
    'ace_inhibitor': 'ace_inhibitor',
    'ProductCategory.CORTICOSTEROID': 'corticosteroid',
    'corticosteroid': 'corticosteroid',
    'ProductCategory.OTHER': 'other',
    'other': 'other',
}


def fix_enum(val):
    if val is None:
        return None
    if not isinstance(val, str):
        return val
    return ENUM_MAP.get(val, val.upper() if val.isalpha() else val)


def main():
    # Step 1: Drop all data tables AND enum types
    print('Step 1: Dropping everything...')
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    # Drop tables first (they depend on enum types)
    for t in [
        'alerts',
        'consumption',
        'stock_movements',
        'inventory_batches',
        'products',
        'warehouses',
        'users',
        'audit_logs',
        'predictions',
        'alembic_version',
    ]:
        cur.execute(f'DROP TABLE IF EXISTS {t} CASCADE')
    # Now drop all enum types
    for e in [
        'userrole',
        'productcategory',
        'batchstatus',
        'movementtype',
        'alerttype',
        'alertseverity',
        'prescriptiontype',
        'department',
    ]:
        cur.execute(f'DROP TYPE IF EXISTS {e} CASCADE')
    # Verify types are gone
    cur.execute(
        "SELECT typname FROM pg_type WHERE typname IN ('userrole','productcategory','batchstatus','movementtype','alerttype','alertseverity','prescriptiontype','department')"
    )
    remaining = cur.fetchall()
    if remaining:
        print(f'  WARNING: types still exist: {remaining}')
    else:
        print('  All tables and enum types dropped')
    conn.close()
    print('  Done')

    # Step 2: Run Alembic to recreate tables
    print('\nStep 2: Running Alembic migrations...')
    subprocess.run(
        ['uv', 'run', 'alembic', 'upgrade', 'head'],
        cwd=str(Path(__file__).parent.parent),
        check=True,
    )
    print('  Done')

    # Step 3: Seed data with UPPERCASE enums
    print('\nStep 3: Seeding data...')
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Users
    print('  Users...')
    df = pl.read_parquet(DATA_DIR / 'users.parquet')
    for row in df.iter_rows(named=True):
        cur.execute(
            """
            INSERT INTO users (id, email, hashed_password, full_name, role, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """,
            (
                row['id'],
                row['email'],
                row['hashed_password'],
                row['full_name'],
                fix_enum(row['role']),
                row['is_active'],
                row.get('created_at') or NOW,
            ),
        )
    print(f'    {len(df)} users')

    # Warehouses
    print('  Warehouses...')
    df = pl.read_parquet(DATA_DIR / 'warehouses.parquet')
    for row in df.iter_rows(named=True):
        cur.execute(
            """
            INSERT INTO warehouses (id, name, location, is_primary, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """,
            (
                row['id'],
                row['name'],
                row['location'],
                row['is_primary'],
                row.get('created_at') or NOW,
            ),
        )
    print(f'    {len(df)} warehouses')

    # Products
    print('  Products...')
    df = pl.read_parquet(DATA_DIR / 'products.parquet')
    for row in df.iter_rows(named=True):
        cur.execute(
            """
            INSERT INTO products (id, sku, name, generic_name, category, atc_code, unit,
                unit_cost, min_stock_level, max_stock_level, lead_time_days,
                controlled_substance, is_active, product_metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                row['id'],
                row['sku'],
                row['name'],
                row['generic_name'],
                fix_enum(row['category']),
                row['atc_code'],
                row['unit'],
                row['unit_cost'],
                row['min_stock_level'],
                row['max_stock_level'],
                row['lead_time_days'],
                row['controlled_substance'],
                row['is_active'],
                row['metadata'],
                row.get('created_at') or NOW,
            ),
        )
    print(f'    {len(df)} products')

    # Inventory batches
    print('  Batches...')
    df = pl.read_parquet(DATA_DIR / 'inventory_batches.parquet')
    for row in df.iter_rows(named=True):
        cur.execute(
            """
            INSERT INTO inventory_batches (id, product_id, warehouse_id, batch_number,
                quantity, expiry_date, manufacture_date, unit_cost, status, received_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                row['id'],
                row['product_id'],
                row['warehouse_id'],
                row['batch_number'],
                row['quantity'],
                row['expiry_date'],
                row['manufacture_date'],
                row['unit_cost'],
                fix_enum(row['status']),
                row['received_at'],
                row.get('created_at') or NOW,
            ),
        )
    print(f'    {len(df)} batches')

    # Stock movements (batch)
    print('  Stock movements...')
    df = pl.read_parquet(DATA_DIR / 'stock_movements.parquet')
    rows = [
        (
            row['id'],
            row['batch_id'],
            row.get('user_id'),
            row['quantity_change'],
            fix_enum(row['movement_type']),
            row.get('reference_type'),
            row.get('reference_id'),
            row.get('notes'),
            row.get('created_at') or NOW,
        )
        for row in df.iter_rows(named=True)
    ]
    from psycopg2.extras import execute_values

    execute_values(
        cur,
        """
        INSERT INTO stock_movements (id, batch_id, user_id, quantity_change,
            movement_type, reference_type, reference_id, notes, created_at)
        VALUES %s
    """,
        rows,
        page_size=5000,
    )
    print(f'    {len(df)} movements')

    # Consumption (batch)
    print('  Consumption...')
    df = pl.read_parquet(DATA_DIR / 'consumption.parquet')
    rows = [
        (
            row['id'],
            row['product_id'],
            row['consumption_date'],
            row['quantity'],
            fix_enum(row['department']),
            fix_enum(row['prescription_type']),
            row['context'],
            row.get('created_at') or NOW,
        )
        for row in df.iter_rows(named=True)
    ]
    execute_values(
        cur,
        """
        INSERT INTO consumption (id, product_id, consumption_date, quantity,
            department, prescription_type, context, created_at)
        VALUES %s
    """,
        rows,
        page_size=10000,
    )
    print(f'    {len(df)} consumption')

    # Alerts
    print('  Alerts...')
    df = pl.read_parquet(DATA_DIR / 'alerts.parquet')
    for row in df.iter_rows(named=True):
        cur.execute(
            """
            INSERT INTO alerts (id, product_id, alert_type, severity, message,
                alert_metadata, acknowledged, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                row['id'],
                row['product_id'],
                fix_enum(row['alert_type']),
                fix_enum(row['severity']),
                row['message'],
                row['metadata'],
                row.get('acknowledged') or False,
                row.get('created_at') or NOW,
            ),
        )
    print(f'    {len(df)} alerts')

    # Set admin password
    print('\nSetting admin password...')
    import bcrypt

    pwd = bcrypt.hashpw(b'admin123', bcrypt.gensalt(rounds=12)).decode()
    cur.execute(
        'UPDATE users SET hashed_password = %s WHERE email = %s', (pwd, 'admin@hospital.gov.br')
    )
    print('  admin@hospital.gov.br / admin123')

    conn.commit()
    print('\nStep 4: Verifying...')
    for t in [
        'users',
        'warehouses',
        'products',
        'inventory_batches',
        'stock_movements',
        'consumption',
        'alerts',
    ]:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        print(f'  {t:25s} {cur.fetchone()[0]:>10,}')

    conn.close()
    print('\nAll done!')


if __name__ == '__main__':
    main()
