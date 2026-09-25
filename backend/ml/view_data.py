#!/usr/bin/env python
"""Quick viewer for generated synthetic data."""

import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import polars as pl

data_dir = 'ml/data/synthetic'

# Metadata
with open(f'{data_dir}/metadata.json') as f:
    meta = json.load(f)

print('=== METADATA ===')
print(f'Periodo: {meta["period"]["start"]} a {meta["period"]["end"]}')
print(f'Semente: {meta["seed"]}')
print()
print('=== CONTAGEM DE REGISTROS ===')
total = 0
for name, count in meta['counts'].items():
    print(f'  {name:25s} {count:>10,} registros')
    total += count
print(f'  {"TOTAL":25s} {total:>10,} registros')

# Amostras de cada tabela
for table in ['consumption', 'products', 'alerts', 'stock_movements', 'inventory_batches']:
    print(f'\n=== {table.upper()} (5 primeiras linhas) ===')
    df = pl.read_parquet(f'{data_dir}/{table}.parquet')
    print(df.head(5))

# Estatísticas do consumo
print('\n=== ESTATISTICAS DO CONSUMO ===')
df = pl.read_parquet(f'{data_dir}/consumption.parquet')
print(f'  Total de registros:  {len(df):,}')
print(f'  Periodo:             {df["consumption_date"].min()} a {df["consumption_date"].max()}')
print(f'  Quantidade media:    {df["quantity"].mean():.1f}')
print(f'  Quantidade max:      {df["quantity"].max()}')
print(f'  Produtos distintos:  {df["product_id"].n_unique()}')
print(f'  Departamentos:       {df["department"].unique().to_list()}')
print(f'  Tipos prescricao:    {df["prescription_type"].unique().to_list()}')

# Consumo por departamento
print('\n  Consumo por departamento:')
dept_stats = (
    df.group_by('department')
    .agg(
        [
            pl.col('quantity').sum().alias('total'),
            pl.col('quantity').mean().alias('media'),
            pl.len().alias('registros'),
        ]
    )
    .sort('total', descending=True)
)
print(dept_stats)
