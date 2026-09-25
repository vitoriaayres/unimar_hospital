"""Regenerate synthetic data with realistic distribution."""

import random
from datetime import date, timedelta

import psycopg2

random.seed(42)

CONN = 'postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict'


def main():
    conn = psycopg2.connect(CONN)
    cur = conn.cursor()

    print('1. Limpando dados antigos...')
    cur.execute('DELETE FROM alerts')
    cur.execute('DELETE FROM consumption')
    cur.execute('DELETE FROM stock_movements')
    cur.execute('DELETE FROM predictions')
    cur.execute('DELETE FROM inventory_batches')

    print('2. Atualizando niveis de estoque dos produtos...')
    cur.execute('SELECT id, min_stock_level, max_stock_level FROM products')
    products = cur.fetchall()

    for prod_id, min_stock, max_stock in products:
        # Distribuicao realista:
        # 15% - estoque critico (abaixo do minimo)
        # 20% - estoque baixo (perto do minimo)
        # 40% - estoque normal (entre min e max)
        # 25% - estoque alto (acima do max)
        roll = random.random()
        if roll < 0.15:
            stock = random.randint(0, max(1, min_stock - 1))
        elif roll < 0.35:
            stock = random.randint(min_stock, min_stock + (max_stock - min_stock) // 3)
        elif roll < 0.75:
            stock = random.randint(min_stock + (max_stock - min_stock) // 3, max_stock)
        else:
            stock = random.randint(max_stock, max_stock * 2)

        cur.execute('UPDATE products SET min_stock_level = %s WHERE id = %s', (min_stock, prod_id))

    print('3. Criando lotes com distribuicao realista...')
    # 500 products, each gets 1-3 batches
    batch_count = 0
    today = date.today()

    # Warehouses existentes
    warehouses = [
        'f896a7dd-0c06-4b13-8533-08efe043eb12',
        'f3bccb24-1c63-467d-ab6c-bb389143cf40',
        '92ec22bb-ee89-4c4c-81c3-dd66b66c706c',
        'c5923594-7462-4a7e-b14b-a85651fc0172',
    ]

    for prod_id, min_stock, max_stock in products:
        num_batches = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
        total_stock = 0

        for b in range(num_batches):
            wh = random.choice(warehouses)
            # Distribuicao de vencimento:
            roll = random.random()
            if roll < 0.05:
                expiry = today - timedelta(days=random.randint(1, 90))
                status = 'expired'
            elif roll < 0.15:
                expiry = today + timedelta(days=random.randint(1, 30))
                status = 'available'
            elif roll < 0.30:
                expiry = today + timedelta(days=random.randint(31, 60))
                status = 'available'
            elif roll < 0.50:
                expiry = today + timedelta(days=random.randint(61, 90))
                status = 'available'
            elif roll < 0.75:
                expiry = today + timedelta(days=random.randint(91, 180))
                status = 'available'
            else:
                expiry = today + timedelta(days=random.randint(181, 365))
                status = 'available'

            # Quantidade
            if status == 'expired':
                qty = 0
            elif (expiry - today).days <= 30:
                qty = random.randint(10, 100)
            elif (expiry - today).days <= 60:
                qty = random.randint(50, 200)
            else:
                qty = random.randint(100, 500)

            total_stock += qty
            cost = round(random.uniform(5, 200), 2)
            batch_num = f'L{today.year}{random.randint(1000, 9999)}{chr(97 + b)}'

            cur.execute(
                """INSERT INTO inventory_batches
                   (id, product_id, warehouse_id, batch_number, quantity, unit_cost, expiry_date, status,
                    created_at, updated_at)
                   VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                (prod_id, wh, batch_num, qty, cost, expiry, status),
            )
            batch_count += 1

    print(f'   Criados {batch_count} lotes')

    print('4. Criando movimentacoes de estoque...')
    cur.execute(
        'SELECT id, product_id, quantity FROM inventory_batches WHERE quantity > 0 LIMIT 200'
    )
    batches = cur.fetchall()

    mov_count = 0
    for batch_id, prod_id, qty in batches:
        # Entrada do lote
        cur.execute(
            """INSERT INTO stock_movements
               (id, batch_id, movement_type, quantity_change, notes, created_at)
               VALUES (gen_random_uuid(), %s, 'in', %s, 'Entrada inicial', NOW())""",
            (batch_id, qty),
        )
        mov_count += 1

        # Algumas saidas
        if random.random() < 0.3:
            out_qty = min(random.randint(5, 50), qty)
            cur.execute(
                """INSERT INTO stock_movements
                   (id, batch_id, movement_type, quantity_change, notes, created_at)
                   VALUES (gen_random_uuid(), %s, 'out', %s, 'Saida para dispensacao', NOW())""",
                (batch_id, -out_qty),
            )
            mov_count += 1

    print(f'   Criadas {mov_count} movimentacoes')

    print('5. Gerando consumo historico (2024)...')
    cons_count = 0
    # Consumo mais realista: 200 produtos ativos, 1 ano de dados
    active_products = random.sample([p[0] for p in products], min(200, len(products)))

    start_date = date(2024, 1, 1)
    end_date = date(2024, 12, 31)
    current = start_date

    while current <= end_date:
        # 10-30 produtos consumidos por dia
        num_products = random.randint(10, 30)
        day_products = random.sample(active_products, min(num_products, len(active_products)))

        for prod_id in day_products:
            qty = random.randint(1, 100)
            department = random.choice(['icu', 'er', 'ward', 'outpatient'])

            cur.execute(
                """INSERT INTO consumption
                   (id, product_id, quantity, department, consumption_date, created_at)
                   VALUES (gen_random_uuid(), %s, %s, %s, %s, NOW())""",
                (prod_id, qty, department, current),
            )
            cons_count += 1

        current += timedelta(days=1)

    print(f'   Criados {cons_count} registros de consumo')

    print('6. Gerando alertas com distribuicao realista...')
    cur.execute("""
        SELECT p.id, p.name, p.sku,
               COALESCE(SUM(ib.quantity), 0) as total_stock,
               p.min_stock_level, p.max_stock_level
        FROM products p
        LEFT JOIN inventory_batches ib ON ib.product_id = p.id AND ib.status = 'available'
        GROUP BY p.id, p.name, p.sku, p.min_stock_level, p.max_stock_level
    """)
    prods = cur.fetchall()

    alert_count = 0
    for prod_id, name, sku, stock, min_lvl, max_lvl in prods:
        # Alerta de estoque baixo
        if stock < min_lvl and random.random() < 0.8:
            severity = 'critical' if stock < min_lvl * 0.5 else 'warning'
            cur.execute(
                """INSERT INTO alerts
                   (id, product_id, alert_type, severity, message, acknowledged, alert_metadata, created_at)
                   VALUES (gen_random_uuid(), %s, 'shortage_risk', %s, %s, false, '{}', NOW())""",
                (prod_id, severity, f'Estoque de {name} abaixo do minimo ({stock} < {min_lvl})'),
            )
            alert_count += 1

        # Alerta de vencimento
        cur.execute(
            "SELECT COUNT(*) FROM inventory_batches WHERE product_id = %s AND status = 'available' AND expiry_date <= CURRENT_DATE + INTERVAL '30 days'",
            (prod_id,),
        )
        expiring = cur.fetchone()[0]
        if expiring > 0:
            cur.execute(
                """INSERT INTO alerts
                   (id, product_id, alert_type, severity, message, acknowledged, alert_metadata, created_at)
                   VALUES (gen_random_uuid(), %s, 'expiry_risk', %s, %s, false, '{}', NOW())""",
                (prod_id, 'warning', f'{expiring} lotes de {name} vencendo em 30 dias'),
            )
            alert_count += 1

        # Alerta de sobreestoque
        if stock > max_lvl * 1.5 and random.random() < 0.3:
            cur.execute(
                """INSERT INTO alerts
                   (id, product_id, alert_type, severity, message, acknowledged, alert_metadata, created_at)
                   VALUES (gen_random_uuid(), %s, 'overstock', 'info', %s, false, '{}', NOW())""",
                (prod_id, f'Estoque de {name} acima do nivel maximo ({stock} > {max_lvl})'),
            )
            alert_count += 1

    print(f'   Criados {alert_count} alertas')

    conn.commit()
    conn.close()
    print('\nDados regenerados com sucesso!')


if __name__ == '__main__':
    main()
