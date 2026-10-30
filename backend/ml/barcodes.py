"""Atribui codigos de barras EAN-13 ficticios aos produtos sem codigo.

O codigo e deterministico pela ordem do SKU (prefixo 789 = Brasil), entao rodar de novo
depois de um reset gera os mesmos codigos. Chamado no fim de ml/full_reset.py.
"""

from __future__ import annotations

import io
import sys

import psycopg2

PREFIX = '789'
DB_URL = 'postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict'


def ean13(seq: int) -> str:
    """EAN-13 valido: prefixo + sequencia de 9 digitos + digito verificador."""
    body = f'{PREFIX}{seq:09d}'
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(body))
    return body + str((10 - total % 10) % 10)


def assign_barcodes(cur) -> int:
    """Preenche products.barcode onde estiver vazio. Retorna quantos foram atualizados."""
    cur.execute('SELECT id, sku FROM products ORDER BY sku')
    rows = cur.fetchall()
    cur.execute('SELECT barcode FROM products WHERE barcode IS NOT NULL')
    taken = {r[0] for r in cur.fetchall()}

    updated = 0
    for seq, (product_id, _sku) in enumerate(rows, start=1):
        code = ean13(seq)
        if code in taken:
            continue
        cur.execute(
            'UPDATE products SET barcode = %s WHERE id = %s AND barcode IS NULL',
            (code, product_id),
        )
        updated += cur.rowcount
    return updated


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    conn = psycopg2.connect(DB_URL)
    with conn, conn.cursor() as cur:
        updated = assign_barcodes(cur)
    conn.close()
    print(f'Codigos de barras atribuidos: {updated}')


if __name__ == '__main__':
    main()
