"""Recalcula os niveis e o saldo de estoque a partir do consumo registrado.

O gerador sintetico define minimo/maximo como 0,15x e 2,5x a demanda DIARIA da
classe, o que deixa todo produto com ~2 dias de cobertura e faz o painel apontar
risco de falta em 100% do catalogo. Este script corrige isso sem tocar no
historico de consumo:

  estoque de seguranca = z * sqrt(L * sigma_d^2 + d^2 * sigma_L^2)  -> minimo
  ponto de pedido      = d * L + estoque de seguranca
  estoque maximo       = ponto de pedido + d * periodo de revisao

O saldo atual sai da reproducao dos ultimos dias de consumo real sob essa
politica, com prazos de entrega sorteados (semente fixa), em vez de ser escolhido.

Uso (a partir de backend/):
  python ml/ajustar_estoque.py             # simula e mostra o resultado
  python ml/ajustar_estoque.py --aplicar   # grava niveis e saldos
  python ml/run_pipeline.py                # retreina e gera previsoes
  python ml/ajustar_estoque.py --alertas   # refaz os alertas de falta
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from math import ceil, sqrt
from pathlib import Path
from statistics import NormalDist
from uuid import uuid4

import numpy as np
import psycopg2
import psycopg2.extras
import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CONFIG_PATH = Path(__file__).parent / 'config' / 'data_generation.yaml'
DB_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict',
)
DEMAND_WINDOW_DAYS = 90
REPLAY_DAYS = 180
SEED = 42


def load_policy() -> dict:
    with open(CONFIG_PATH, encoding='utf-8') as f:
        config = yaml.safe_load(f)
    policy = config['inventory_policy']
    return {
        'z': NormalDist().inv_cdf(policy['service_level']),
        'review_days': policy['review_period_days'],
        'lead_time_std': config['products']['lead_time_days']['std'],
    }


def load_daily_consumption(cur) -> dict[str, np.ndarray]:
    """Serie diaria dos ultimos REPLAY_DAYS por produto (dias sem consumo = 0)."""
    cur.execute('SELECT max(consumption_date) FROM consumption')
    last_day = cur.fetchone()[0]
    cur.execute(
        """
        SELECT product_id::text, %s - consumption_date, sum(quantity)
        FROM consumption
        WHERE consumption_date > %s - %s::int
        GROUP BY 1, 2
        """,
        (last_day, last_day, REPLAY_DAYS),
    )
    series: dict[str, np.ndarray] = {}
    for product_id, days_ago, quantity in cur.fetchall():
        values = series.setdefault(product_id, np.zeros(REPLAY_DAYS))
        values[REPLAY_DAYS - 1 - days_ago] = quantity
    return series


def compute_levels(daily: np.ndarray, lead_time: int, policy: dict) -> dict:
    recent = daily[-DEMAND_WINDOW_DAYS:]
    demand, sigma = float(recent.mean()), float(recent.std())
    safety = policy['z'] * sqrt(
        lead_time * sigma**2 + demand**2 * policy['lead_time_std'] ** 2
    )
    reorder_point = demand * lead_time + safety
    maximum = reorder_point + demand * policy['review_days']
    return {
        'min': max(1, ceil(safety)),
        'reorder_point': ceil(reorder_point),
        'max': max(2, ceil(maximum)),
    }


def replay_stock(
    daily: np.ndarray, levels: dict, lead_time: int, policy: dict, rng: np.random.Generator
) -> int:
    """Reproduz o consumo real sob a politica e devolve o saldo do ultimo dia."""
    # Comeca em um ponto aleatorio do ciclo para os produtos nao andarem em fase
    stock = int(rng.integers(levels['reorder_point'], levels['max'] + 1))
    pending: list[tuple[int, int]] = []

    for day, consumed in enumerate(daily):
        stock += sum(qty for arrival, qty in pending if arrival == day)
        pending = [order for order in pending if order[0] > day]
        stock = max(0, stock - int(consumed))

        if not pending and stock <= levels['reorder_point']:
            delay = max(1, round(rng.normal(lead_time, policy['lead_time_std'])))
            pending.append((day + delay, levels['max'] - stock))

    return stock


def build_plan(cur) -> list[dict]:
    policy = load_policy()
    series = load_daily_consumption(cur)
    rng = np.random.default_rng(SEED)

    cur.execute(
        """
        SELECT p.id::text, p.name, p.lead_time_days, pr.predicted_quantity
        FROM products p
        LEFT JOIN predictions pr ON pr.product_id = p.id
        WHERE p.is_active
        ORDER BY p.sku
        """
    )
    plan = []
    for product_id, name, lead_time, predicted_7d in cur.fetchall():
        daily = series.get(product_id)
        if daily is None:
            print(f'   Sem consumo recente, mantido como esta: {name}')
            continue
        levels = compute_levels(daily, lead_time, policy)
        plan.append(
            {
                'product_id': product_id,
                'name': name,
                'stock': replay_stock(daily, levels, lead_time, policy, rng),
                'predicted_7d': predicted_7d or 0,
                'daily': float(daily[-DEMAND_WINDOW_DAYS:].mean()),
                **levels,
            }
        )
    return plan


def print_summary(plan: list[dict]) -> None:
    coverage = np.array([p['stock'] / p['daily'] for p in plan if p['daily'] > 0])
    risk = sum(p['stock'] < p['predicted_7d'] for p in plan)
    below_min = sum(p['stock'] <= p['min'] for p in plan)
    zero = sum(p['stock'] == 0 for p in plan)
    print(f'   Produtos:            {len(plan)}')
    print(f'   Risco de falta (7d): {risk} ({risk / len(plan):.0%})')
    print(f'   Abaixo do minimo:    {below_min}')
    print(f'   Sem estoque:         {zero}')
    print(f'   Cobertura mediana:   {np.median(coverage):.1f} dias')
    print(f'   Cobertura p10/p90:   {np.percentile(coverage, [10, 90]).round(1)} dias')
    print(f'   Unidades em estoque: {sum(p["stock"] for p in plan):,}')


def apply_plan(cur, plan: list[dict]) -> None:
    cur.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY created_at LIMIT 1")
    admin = cur.fetchone()
    admin_id = admin[0] if admin else None

    for item in plan:
        cur.execute(
            'UPDATE products SET min_stock_level = %s, max_stock_level = %s WHERE id = %s',
            (item['min'], item['max'], item['product_id']),
        )
        # Lote com saldo e validade mais longa recebe o saldo; os demais ficam zerados
        cur.execute(
            """
            SELECT id, quantity FROM inventory_batches
            WHERE product_id = %s AND status = 'available'
            ORDER BY (quantity > 0) DESC, expiry_date DESC
            """,
            (item['product_id'],),
        )
        batches = cur.fetchall()
        if not batches:
            print(f'   Sem lote disponivel, saldo nao ajustado: {item["name"]}')
            continue

        for index, (batch_id, quantity) in enumerate(batches):
            target = item['stock'] if index == 0 else 0
            if target == quantity:
                continue
            cur.execute(
                'UPDATE inventory_batches SET quantity = %s, updated_at = now() WHERE id = %s',
                (target, batch_id),
            )
            cur.execute(
                """
                INSERT INTO stock_movements
                    (id, batch_id, user_id, quantity_change, movement_type, reference_type, notes)
                VALUES (%s, %s, %s, %s, 'adjustment', 'inventory_rebalance', %s)
                """,
                (
                    str(uuid4()),
                    batch_id,
                    admin_id,
                    target - quantity,
                    'Ajuste de saldo pela politica de estoque (ml/ajustar_estoque.py)',
                ),
            )


def rebuild_shortage_alerts(cur) -> None:
    """Refaz os alertas de falta com o mesmo criterio do KPI do painel."""
    cur.execute(
        """
        SELECT p.id::text, p.max_stock_level, pr.predicted_quantity,
               coalesce(sum(b.quantity) FILTER (WHERE b.status = 'available'), 0)
        FROM products p
        JOIN predictions pr ON pr.product_id = p.id
        LEFT JOIN inventory_batches b ON b.product_id = p.id
        WHERE p.is_active
        GROUP BY 1, 2, 3
        """
    )
    rows = cur.fetchall()
    cur.execute("DELETE FROM alerts WHERE alert_type = 'shortage_risk'")
    removed = cur.rowcount

    created = {'critical': 0, 'warning': 0}
    for product_id, max_level, predicted_7d, stock in rows:
        if predicted_7d <= 0 or stock >= predicted_7d:
            continue
        daily = predicted_7d / 7
        days = stock / daily
        # int() como em get_stockout_risk, para o painel e os alertas contarem igual
        severity = 'critical' if int(days) <= 3 else 'warning'
        created[severity] += 1
        cur.execute(
            """
            INSERT INTO alerts
                (id, product_id, alert_type, severity, message, alert_metadata, acknowledged)
            VALUES (%s, %s, 'shortage_risk', %s, %s, %s, false)
            """,
            (
                str(uuid4()),
                product_id,
                severity,
                f'Risco de falta: estoque atual durará ~{int(days)} dias',
                psycopg2.extras.Json(
                    {
                        'current_stock': int(stock),
                        'daily_avg_consumption': round(daily, 1),
                        'days_until_stockout': round(days, 1),
                        'recommended_order_qty': max(0, max_level - int(stock)),
                    }
                ),
            ),
        )
    print(f'   Removidos: {removed}')
    print(f'   Criados:   {created["critical"]} criticos, {created["warning"]} de atencao')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--aplicar', action='store_true', help='grava niveis e saldos no banco')
    parser.add_argument('--alertas', action='store_true', help='refaz os alertas de falta')
    args = parser.parse_args()

    with psycopg2.connect(DB_URL) as conn, conn.cursor() as cur:
        if args.alertas:
            print('=== Refazendo alertas de falta ===')
            rebuild_shortage_alerts(cur)
            return

        print('=== Politica de estoque ===')
        plan = build_plan(cur)
        print_summary(plan)
        if args.aplicar:
            apply_plan(cur, plan)
            print('\n   Niveis e saldos gravados.')
        else:
            print('\n   Simulacao: nada foi gravado. Use --aplicar para gravar.')


if __name__ == '__main__':
    main()
