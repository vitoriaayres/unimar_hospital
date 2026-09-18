"""Feature engineering para previsão de demanda hospitalar.

Lê dados do PostgreSQL e cria features para treino de ML.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Adicionar diretório backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

import polars as pl
import psycopg2

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict",
)
FEATURES_DIR = Path("ml/data")


def _get_connection():
    return psycopg2.connect(DB_URL)


def load_consumption() -> pl.DataFrame:
    conn = _get_connection()
    df = pl.read_database(
        "SELECT id, product_id, consumption_date, quantity, "
        "department, prescription_type, context FROM consumption "
        "ORDER BY product_id, consumption_date",
        conn,
    )
    conn.close()
    return df


def load_products() -> pl.DataFrame:
    conn = _get_connection()
    df = pl.read_database(
        "SELECT id, sku, name, generic_name, category, atc_code, unit, "
        "unit_cost::float, min_stock_level, max_stock_level, lead_time_days, "
        "controlled_substance FROM products WHERE is_active = true",
        conn,
    )
    conn.close()
    return df


def load_inventory() -> pl.DataFrame:
    conn = _get_connection()
    df = pl.read_database(
        "SELECT id, product_id, warehouse_id, batch_number, quantity, "
        "expiry_date, manufacture_date, unit_cost::float, status, received_at "
        "FROM inventory_batches",
        conn,
    )
    conn.close()
    return df


def build_daily_consumption(consumption: pl.DataFrame) -> pl.DataFrame:
    """Agrupa consumo por produto por dia e filtra produtos com consumo muito baixo."""
    daily = (
        consumption
        .group_by(["product_id", "consumption_date"])
        .agg(pl.col("quantity").sum().alias("daily_consumption"))
        .sort(["product_id", "consumption_date"])
    )
    
    # Filter out products with very low total consumption (noise)
    product_totals = (
        daily
        .group_by("product_id")
        .agg(pl.col("daily_consumption").sum().alias("total_consumption"))
    )
    
    # Keep products with at least 200 units total (filter noise)
    min_total = 200
    active_products = product_totals.filter(pl.col("total_consumption") >= min_total)["product_id"]
    daily = daily.filter(pl.col("product_id").is_in(active_products))
    
    print(f"    Produtos ativos (consumo >= {min_total}): {len(active_products)}/{consumption['product_id'].n_unique()}")
    
    return daily


def add_lag_features(df: pl.DataFrame) -> pl.DataFrame:
    """Lag features: consumo nos dias anteriores + diferenças."""
    for lag in [1, 2, 3, 7, 14, 21, 30]:
        df = df.with_columns(
            pl.col("daily_consumption")
            .shift(lag)
            .over("product_id")
            .alias(f"lag_{lag}")
        )
    
    # Add difference features (rate of change)
    df = df.with_columns([
        (pl.col("lag_1") - pl.col("lag_2")).alias("diff_1_2"),
        (pl.col("lag_7") - pl.col("lag_14")).alias("diff_7_14"),
        (pl.col("lag_14") - pl.col("lag_30")).alias("diff_14_30"),
        # Ratio features
        (pl.col("lag_1") / (pl.col("lag_7") + 1e-6)).alias("ratio_1_7"),
        (pl.col("lag_7") / (pl.col("lag_30") + 1e-6)).alias("ratio_7_30"),
    ])
    return df


def add_rolling_features(df: pl.DataFrame) -> pl.DataFrame:
    """Rolling statistics: média, std, min, max em janelas."""
    for window in [7, 14, 30]:
        df = df.with_columns([
            pl.col("daily_consumption")
            .rolling_mean(window_size=window)
            .over("product_id")
            .alias(f"rolling_mean_{window}"),
            pl.col("daily_consumption")
            .rolling_std(window_size=window)
            .over("product_id")
            .alias(f"rolling_std_{window}"),
            pl.col("daily_consumption")
            .rolling_min(window_size=window)
            .over("product_id")
            .alias(f"rolling_min_{window}"),
            pl.col("daily_consumption")
            .rolling_max(window_size=window)
            .over("product_id")
            .alias(f"rolling_max_{window}"),
        ])
    return df


def add_expanding_features(df: pl.DataFrame) -> pl.DataFrame:
    """Estatísticas acumuladas (toda a história até o dia)."""
    df = df.with_columns([
        pl.col("daily_consumption")
        .cum_sum()
        .over("product_id")
        .alias("cumulative_consumption"),
        (pl.col("daily_consumption").cum_sum().over("product_id")
         / pl.col("daily_consumption").cum_count().over("product_id"))
        .alias("expanding_mean"),
    ])
    return df


def add_calendar_features(df: pl.DataFrame) -> pl.DataFrame:
    """Features de calendário expandidas."""
    df = df.with_columns([
        pl.col("consumption_date").dt.weekday().alias("weekday"),
        pl.col("consumption_date").dt.month().alias("month"),
        pl.col("consumption_date").dt.quarter().alias("quarter"),
        pl.col("consumption_date").dt.day().alias("day_of_month"),
        ((pl.col("consumption_date").dt.weekday() >= 6).cast(pl.Int8)).alias("is_weekend"),
        # Cyclical encoding for month (captures seasonality)
        (2 * 3.14159 * pl.col("consumption_date").dt.month() / 12).sin().alias("month_sin"),
        (2 * 3.14159 * pl.col("consumption_date").dt.month() / 12).cos().alias("month_cos"),
    ])
    return df


def add_target(df: pl.DataFrame, horizon_days: int = 7) -> pl.DataFrame:
    """Target: consumo total nos próximos N dias."""
    df = df.with_columns(
        pl.col("daily_consumption")
        .shift(-horizon_days)
        .over("product_id")
        .alias(f"target_{horizon_days}d")
    )
    return df


def add_product_features(df: pl.DataFrame, products: pl.DataFrame) -> pl.DataFrame:
    """Features estáticas do produto (categoria, custo, lead time)."""
    product_features = products.select([
        pl.col("id").alias("product_id"),
        "category",
        "atc_code",
        "unit_cost",
        "min_stock_level",
        "max_stock_level",
        "lead_time_days",
        "controlled_substance",
    ])

    # One-hot encoding para category
    categories = [c for c in products["category"].unique().to_list() if c is not None]
    for cat in categories:
        product_features = product_features.with_columns(
            (pl.col("category") == cat).cast(pl.Int8).alias(f"cat_{cat}")
        )

    # One-hot para atc_code (top classes)
    atc_codes = [a for a in products["atc_code"].unique().to_list() if a is not None]
    for atc in atc_codes:
        product_features = product_features.with_columns(
            (pl.col("atc_code") == atc).cast(pl.Int8).alias(f"atc_{atc}")
        )

    # Log transforms
    product_features = product_features.with_columns([
        pl.col("unit_cost").log1p().alias("unit_cost_log"),
        pl.col("lead_time_days").cast(pl.Float64).log1p().alias("lead_time_log"),
    ])

    return df.join(product_features, on="product_id", how="left")


def add_stock_features(df: pl.DataFrame, inventory: pl.DataFrame) -> pl.DataFrame:
    """Features de estoque atual por produto."""
    stock = (
        inventory
        .filter(pl.col("status") == "available")
        .group_by("product_id")
        .agg([
            pl.col("quantity").sum().alias("current_stock"),
            pl.col("quantity").count().alias("batch_count"),
            pl.col("expiry_date").min().alias("nearest_expiry"),
        ])
    )

    df = df.join(stock, on="product_id", how="left")

    # Dias até vencimento mais próximo
    df = df.with_columns(
        (pl.col("nearest_expiry") - pl.col("consumption_date")).dt.total_days().alias("days_to_expiry")
    )

    return df


def build_features(
    consumption: pl.DataFrame,
    products: pl.DataFrame,
    inventory: pl.DataFrame,
) -> pl.DataFrame:
    """Pipeline completo de feature engineering."""
    print("  [1/7] Agrupando consumo diário...")
    df = build_daily_consumption(consumption)

    print("  [2/7] Adicionando lag features...")
    df = add_lag_features(df)

    print("  [3/7] Adicionando rolling statistics...")
    df = add_rolling_features(df)

    print("  [4/7] Adicionando expanding statistics...")
    df = add_expanding_features(df)

    print("  [5/7] Adicionando features de calendário...")
    df = add_calendar_features(df)

    print("  [6/7] Adicionando target (7 dias)...")
    df = add_target(df, horizon_days=7)

    print("  [7/7] Adicionando features de produto e estoque...")
    df = add_product_features(df, products)
    df = add_stock_features(df, inventory)

    # Remover linhas com NaN (primeiros e últimos dias sem lag/target)
    before = len(df)
    df = df.drop_nulls()
    after = len(df)
    print(f"  Removidas {before - after} linhas com NaN ({before} -> {after})")

    return df


def prepare_train_test(
    features: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame, list[str]]:
    """Split temporal: treino antes de 2024, teste em 2024."""
    cutoff = pl.date(2024, 1, 1)
    train = features.filter(pl.col("consumption_date") < cutoff)
    test = features.filter(pl.col("consumption_date") >= cutoff)

    # Colunas de features (excluir IDs, datas, target, strings)
    exclude = {
        "product_id", "consumption_date", "target_7d",
        "category", "atc_code", "nearest_expiry",
    }
    feature_cols = [c for c in features.columns if c not in exclude]

    print(f"  Treino: {len(train)} linhas, Teste: {len(test)} linhas")
    print(f"  Features: {len(feature_cols)} colunas")

    return train, test, feature_cols


def save_features(features: pl.DataFrame, train: pl.DataFrame, test: pl.DataFrame, feature_cols: list[str]) -> None:
    """Salva features em Parquet e metadados."""
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    features.write_parquet(FEATURES_DIR / "features.parquet")
    train.write_parquet(FEATURES_DIR / "train.parquet")
    test.write_parquet(FEATURES_DIR / "test.parquet")

    metadata = {
        "feature_columns": feature_cols,
        "target_column": "target_7d",
        "total_rows": len(features),
        "train_rows": len(train),
        "test_rows": len(test),
        "n_features": len(feature_cols),
    }
    with open(FEATURES_DIR / "features_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n  Features salvas: {FEATURES_DIR / 'features.parquet'}")
    print(f"  Train salvo: {FEATURES_DIR / 'train.parquet'}")
    print(f"  Test salvo: {FEATURES_DIR / 'test.parquet'}")
    print(f"  Metadata: {FEATURES_DIR / 'features_metadata.json'}")


def main() -> None:
    print("=== Feature Engineering ===\n")

    print("Carregando dados...")
    consumption = load_consumption()
    products = load_products()
    inventory = load_inventory()
    print(f"  Consumption: {len(consumption):,} registros")
    print(f"  Products: {len(products)} registros")
    print(f"  Inventory: {len(inventory):,} registros")

    print("\nConstruindo features...")
    features = build_features(consumption, products, inventory)
    print(f"\n  Shape final: {features.shape}")

    print("\nPreparando train/test split...")
    train, test, feature_cols = prepare_train_test(features)

    print("\nSalvando...")
    save_features(features, train, test, feature_cols)

    print("\n=== Concluído ===")


if __name__ == "__main__":
    main()
