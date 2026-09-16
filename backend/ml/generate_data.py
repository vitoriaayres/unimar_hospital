#!/usr/bin/env python
"""Synthetic Data Generator for PharmaPredict.

Generates realistic hospital pharmacy consumption and inventory data
based on Brazilian hospital patterns and literature.
"""

from __future__ import annotations

import argparse
import enum
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
import polars as pl
import yaml
from faker import Faker

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import (
    Alert,
    AlertSeverity,
    AlertType,
    BatchStatus,
    Consumption,
    Department,
    InventoryBatch,
    MovementType,
    PrescriptionType,
    Product,
    ProductCategory,
    StockMovement,
    User,
    UserRole,
    Warehouse,
)


class SyntheticDataGenerator:
    def __init__(self, config_path: str | Path):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.rng = np.random.default_rng(self.config["simulation"]["random_seed"])
        self.fake = Faker("pt_BR")
        self.fake.seed_instance(self.config["simulation"]["random_seed"])

        self.start_date = date.fromisoformat(self.config["simulation"]["start_date"])
        self.end_date = date.fromisoformat(self.config["simulation"]["end_date"])
        self.date_range = pl.date_range(self.start_date, self.end_date, interval="1d", eager=True)

        # Output containers
        self.users: list[User] = []
        self.warehouses: list[Warehouse] = []
        self.products: list[Product] = []
        self.suppliers: list[dict] = []
        self.batches: list[InventoryBatch] = []
        self.movements: list[StockMovement] = []
        self.consumptions: list[Consumption] = []
        self.predictions: list = []
        self.alerts: list[Alert] = []

        # Index structures for O(1) lookups (avoids scanning full lists)
        self._batches_by_product: dict[UUID, list[InventoryBatch]] = {}
        self._primary_warehouse_id: UUID | None = None
        self._products_by_id: dict[UUID, Product] = {}

    def generate_all(self) -> dict[str, pl.DataFrame]:
        print("[INFO] Iniciando geracao de dados sinteticos para PharmaPredict...")
        print(f"   Período: {self.start_date} a {self.end_date}")
        print(f"   Semente: {self.config['simulation']['random_seed']}")

        self._generate_users()
        self._generate_warehouses()
        self._generate_suppliers()
        self._generate_products()
        self._build_batch_index()
        self._generate_initial_inventory()
        self._simulate_daily_operations()
        self._generate_predictions()
        self._generate_alerts()

        return self._to_dataframes()

    def _generate_users(self) -> None:
        print("   [USERS] Gerando usuarios...")
        roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.PHARMACIST]
        role_weights = [0.05, 0.15, 0.80]

        for i in range(12):
            role = self.rng.choice(roles, p=role_weights)
            user = User(
                id=uuid4(),
                email=f"{self.fake.user_name()}@hospital.gov.br",
                hashed_password="$2b$12$placeholder",  # bcrypt hash of "password123"
                full_name=self.fake.name(),
                role=role,
                is_active=True,
                created_at=self.fake.date_time_between(start_date="-2y", end_date="-1y"),
            )
            self.users.append(user)

        # Ensure at least one admin
        if not any(u.role == UserRole.ADMIN for u in self.users):
            admin = User(
                id=uuid4(),
                email="admin@hospital.gov.br",
                hashed_password="$2b$12$placeholder",
                full_name="Administrador do Sistema",
                role=UserRole.ADMIN,
                is_active=True,
            )
            self.users.append(admin)

        # Ensure at least one pharmacist
        if not any(u.role == UserRole.PHARMACIST for u in self.users):
            pharmacist = User(
                id=uuid4(),
                email="farmaceutico@hospital.gov.br",
                hashed_password="$2b$12$placeholder",
                full_name="Farmaceutico Principal",
                role=UserRole.PHARMACIST,
                is_active=True,
            )
            self.users.append(pharmacist)

        print(f"      {len(self.users)} usuários criados")

    def _generate_warehouses(self) -> None:
        print("   [WAREHOUSE] Gerando almoxarifados...")
        warehouse_data = [
            {"name": "Almoxarifado Central", "location": "Térreo - Bloco A", "is_primary": True},
            {"name": "Farmácia Satélite UTI", "location": "2º Andar - UTI", "is_primary": False},
            {"name": "Farmácia Satélite PS", "location": "Térreo - Pronto Socorro", "is_primary": False},
            {"name": "Almoxarifado de Reserva", "location": "Subsolo - Bloco B", "is_primary": False},
        ]

        for w in warehouse_data:
            warehouse = Warehouse(
                id=uuid4(),
                name=w["name"],
                location=w["location"],
                is_primary=w["is_primary"],
            )
            self.warehouses.append(warehouse)

        print(f"      {len(self.warehouses)} almoxarifados criados")

    def _build_batch_index(self) -> None:
        """Build index structures for O(1) batch lookups."""
        primary = next(w for w in self.warehouses if w.is_primary)
        self._primary_warehouse_id = primary.id
        for wh in self.warehouses:
            # Initialize index for each warehouse
            pass

    def _add_batch_to_index(self, batch: InventoryBatch) -> None:
        """Register a batch in the lookup index."""
        key = (batch.product_id, batch.warehouse_id)
        if key not in self._batches_by_product:
            self._batches_by_product[key] = []
        self._batches_by_product[key].append(batch)

    def _get_available_batches(self, product_id: UUID, warehouse_id: UUID) -> list[InventoryBatch]:
        """Get available batches for a product/warehouse using O(1) index, sorted FEFO."""
        key = (product_id, warehouse_id)
        batches = self._batches_by_product.get(key, [])
        return [b for b in batches if b.status == BatchStatus.AVAILABLE and b.quantity > 0]

    def _generate_suppliers(self) -> None:
        print("   [SUPPLIER] Gerando fornecedores...")
        tier_config = self.config["suppliers"]["tiers"]

        for tier in tier_config:
            for i in range(tier["count"]):
                supplier = {
                    "id": uuid4(),
                    "name": f"{tier['name'].replace('_', ' ').title()} {i+1}",
                    "tier": tier["name"],
                    "lead_time_mean": tier["lead_time_days"]["mean"],
                    "lead_time_std": tier["lead_time_days"]["std"],
                    "lead_time_min": tier["lead_time_days"].get("min", 1),
                    "lead_time_max": tier["lead_time_days"].get("max", 30),
                    "reliability": tier["reliability"],
                    "fill_rate": tier["fill_rate"],
                    "min_order_value": tier["min_order_value"],
                }
                self.suppliers.append(supplier)

        print(f"      {len(self.suppliers)} fornecedores criados")

    def _generate_products(self) -> None:
        print("   [PRODUCT] Gerando produtos (catalogo)...")
        atc_dist = self.config["products"]["atc_distribution"]
        class_demand = self.config["products"]["class_base_demand_per_100_beds"]
        cost_ranges = self.config["products"]["unit_cost_ranges"]
        beds = self.config["hospital"]["beds"]

        atc_descriptions = {
            "J01": ("Antibióticos", ProductCategory.ANTIBIOTIC),
            "N02": ("Analgésicos", ProductCategory.ANALGESIC),
            "B01": ("Antitrombóticos", ProductCategory.ANTITHROMBOTIC),
            "C07": ("Betabloqueadores", ProductCategory.BETA_BLOCKER),
            "A02": ("Inibidores de Bomba de Prótons", ProductCategory.PPI),
            "R03": ("Broncodilatadores", ProductCategory.BRONCHODILATOR),
            "N05": ("Psicolépticos", ProductCategory.PSYCHOLEPTIC),
            "C09": ("Inibidores da ECA", ProductCategory.ACE_INHIBITOR),
            "H02": ("Corticosteroides", ProductCategory.CORTICOSTEROID),
            "OTHER": ("Outros", ProductCategory.OTHER),
        }

        units_by_class = {
            "J01": ["mg", "g", "UI"],
            "N02": ["mg", "g", "mL"],
            "B01": ["mg", "UI"],
            "C07": ["mg"],
            "A02": ["mg"],
            "R03": ["mcg", "mg", "mL"],
            "N05": ["mg", "mL"],
            "C09": ["mg"],
            "H02": ["mg", "mL"],
            "OTHER": ["mg", "mL", "un"],
        }

        product_count = self.config["products"]["count"]
        atc_codes = list(atc_dist.keys())
        atc_weights = list(atc_dist.values())

        for i in range(product_count):
            atc = self.rng.choice(atc_codes, p=atc_weights)
            class_name, category = atc_descriptions.get(atc, ("Outros", ProductCategory.OTHER))

            base_demand = class_demand.get(atc, 20) * (beds / 100)
            cost_range = cost_ranges.get(atc, [5, 100])
            unit = self.rng.choice(units_by_class.get(atc, ["mg"]))

            # Generate realistic SKU
            sku_prefix = atc[:3].upper()
            sku = f"{sku_prefix}-{i+1:04d}"

            # Name generation
            generic_names = self._get_generic_names(atc)
            generic = self.rng.choice(generic_names)
            strength = self._generate_strength(atc)
            form = self._generate_form(atc)
            name = f"{generic} {strength} {form}"

            min_stock = max(1, int(base_demand * self.config["products"]["min_stock_multiplier"]))
            max_stock = max(min_stock * 2, int(base_demand * self.config["products"]["max_stock_multiplier"]))

            lead_time = int(self.rng.normal(
                self.config["products"]["lead_time_days"]["mean"],
                self.config["products"]["lead_time_days"]["std"]
            ))
            lead_time = max(self.config["products"]["lead_time_days"]["min"],
                          min(self.config["products"]["lead_time_days"]["max"], lead_time))

            controlled = self.rng.random() < self.config["products"]["controlled_substance_probability"]

            product = Product(
                id=uuid4(),
                sku=sku,
                name=name,
                generic_name=generic,
                category=category,
                atc_code=atc,
                unit=unit,
                unit_cost=round(self.rng.uniform(cost_range[0], cost_range[1]), 2),
                min_stock_level=min_stock,
                max_stock_level=max_stock,
                lead_time_days=lead_time,
                controlled_substance=controlled,
                is_active=True,
                metadata={
                    "atc_class": atc,
                    "class_name": class_name,
                    "base_demand_per_day": round(base_demand, 1),
                    "strength": strength,
                    "form": form,
                },
            )
            self.products.append(product)

        print(f"      {len(self.products)} produtos criados")
        # Build product index for O(1) lookups
        for p in self.products:
            self._products_by_id[p.id] = p

    def _get_generic_names(self, atc: str) -> list[str]:
        names = {
            "J01": ["Amoxicilina", "Ceftriaxona", "Azitromicina", "Ciprofloxacino", "Meropenem", "Piperacilina/Tazobactam", "Vancomicina", "Linezolida", "Cefepima", "Ertapenem"],
            "N02": ["Dipirona", "Paracetamol", "Ibuprofeno", "Cetorolaco", "Tramadol", "Morfina", "Fentanil", "Codeína", "Naproxeno", "Diclofenaco"],
            "B01": ["Enoxaparina", "Heparina", "Varfarina", "Rivaroxabana", "Apixabana", "Dabigatrana", "Clopidogrel", "Ácido Acetilsalicílico", "Fondaparinux", "Ticagrelor"],
            "C07": ["Propranolol", "Atenolol", "Metoprolol", "Carvedilol", "Bisoprolol", "Nebivolol", "Labetalol", "Sotalol", "Pindolol", "Timolol"],
            "A02": ["Omeprazol", "Pantoprazol", "Esomeprazol", "Lansoprazol", "Rabeprazol", "Dexlansoprazol"],
            "R03": ["Salbutamol", "Formoterol", "Budesonida", "Fluticasona", "Ipratrópio", "Tiotrópio", "Montelucaste", "Teofilina"],
            "N05": ["Haloperidol", "Risperidona", "Olanzapina", "Quetiapina", "Aripiprazol", "Lorazepam", "Midazolam", "Diazepam", "Clonazepam", "Zolpidem"],
            "C09": ["Losartana", "Valsartana", "Captopril", "Enalapril", "Ramipril", "Perindopril", "Telmisartana", "Irbesartana", "Candesartana", "Sacubitril/Valsartana"],
            "H02": ["Dexametasona", "Prednisona", "Metilprednisolona", "Hidrocortisona", "Betametasona", "Triancinolona"],
            "OTHER": ["Glicose", "Soro Fisiológico", "Ringer Lactato", "Albumina", "Complexo B", "Vitamina D", "Ferro", "Ácido Fólico", "Potássio", "Magnésio"],
        }
        return names.get(atc, ["Medicamento Genérico"])

    def _generate_strength(self, atc: str) -> str:
        strengths = {
            "J01": ["250mg", "500mg", "1g", "2g", "500mg/5mL", "1g/10mL"],
            "N02": ["500mg", "1g", "75mg", "50mg", "10mg/mL", "50mg/mL"],
            "B01": ["40mg", "60mg", "20mg", "5mg", "100mg", "25000UI"],
            "C07": ["25mg", "50mg", "100mg", "12.5mg", "200mg"],
            "A02": ["20mg", "40mg", "10mg", "30mg"],
            "R03": ["100mcg", "200mcg", "50mcg", "125mcg", "25mcg", "0.5mg/2mL"],
            "N05": ["1mg", "2mg", "5mg", "10mg", "2mg/mL", "5mg/mL"],
            "C09": ["25mg", "50mg", "100mg", "10mg", "20mg", "40/24mg"],
            "H02": ["4mg", "8mg", "20mg", "50mg", "100mg", "4mg/mL"],
            "OTHER": ["5%", "10%", "500mg", "1g", "10mL", "100mL"],
        }
        return self.rng.choice(strengths.get(atc, ["500mg"]))

    def _generate_form(self, atc: str) -> str:
        forms = {
            "J01": ["Cápsula", "Comprimido", "Pó para Solução Injetável", "Suspensão Oral"],
            "N02": ["Comprimido", "Cápsula", "Solução Injetável", "Supositório", "Gotar"],
            "B01": ["Seringa Pré-preenchida", "Comprimido", "Frasco-ampola", "Solução Injetável"],
            "C07": ["Comprimido", "Comprimido de Liberação Prolongada"],
            "A02": ["Cápsula", "Comprimido", "Pó para Suspensão Oral", "Solução Injetável"],
            "R03": ["Aerossol", "Pó para Inalação", "Solução para Nebulização", "Comprimido"],
            "N05": ["Comprimido", "Solução Injetável", "Comprimido Sublingual", "Gotar"],
            "C09": ["Comprimido", "Comprimido de Liberação Prolongada"],
            "H02": ["Comprimido", "Solução Injetável", "Creme", "Colírio"],
            "OTHER": ["Solução Injetável", "Comprimido", "Cápsula", "Pó para Solução Oral"],
        }
        return self.rng.choice(forms.get(atc, ["Comprimido"]))

    def _generate_initial_inventory(self) -> None:
        print("   [INVENTORY] Gerando estoque inicial...")
        wh_id = self._primary_warehouse_id

        for product in self.products:
            # Initial stock: random between min and max
            initial_qty = self.rng.integers(product.min_stock_level, product.max_stock_level + 1)

            # Create 1-3 initial batches
            num_batches = self.rng.integers(1, 4)
            for b in range(num_batches):
                batch_qty = initial_qty // num_batches + (1 if b < initial_qty % num_batches else 0)
                if batch_qty == 0:
                    continue

                # Expiry: 6-24 months from start
                expiry_days = int(self.rng.integers(180, 730))
                expiry_date = self.start_date + timedelta(days=expiry_days)

                manufacture_date = expiry_date - timedelta(days=int(self.rng.integers(30, 365)))

                batch = InventoryBatch(
                    id=uuid4(),
                    product_id=product.id,
                    warehouse_id=wh_id,
                    batch_number=f"L{self.start_date.strftime('%Y%m')}{b+1:03d}",
                    quantity=batch_qty,
                    expiry_date=expiry_date,
                    manufacture_date=manufacture_date,
                    unit_cost=product.unit_cost * self.rng.uniform(0.85, 1.0),
                    status=BatchStatus.AVAILABLE,
                    received_at=datetime.combine(self.start_date - timedelta(days=int(self.rng.integers(1, 30))), datetime.min.time()),
                )
                self.batches.append(batch)
                self._add_batch_to_index(batch)

        print(f"      {len(self.batches)} lotes iniciais criados")

    def _simulate_daily_operations(self) -> None:
        print("   [SIMULATION] Simulando operacoes diarias (consumo, movimentos, pedidos)...")

        # Pre-compute seasonal factors
        seasonal_factors = self._compute_seasonal_factors()

        # Track current stock per product per warehouse
        current_stock = {p.id: {w.id: 0 for w in self.warehouses} for p in self.products}
        for batch in self.batches:
            current_stock[batch.product_id][batch.warehouse_id] += batch.quantity

        # Track pending orders
        pending_orders: dict[UUID, list[dict]] = {p.id: [] for p in self.products}

        pharmacists = [u for u in self.users if u.role == UserRole.PHARMACIST]
        wh_id = self._primary_warehouse_id

        # Pre-extract config for vectorized generation
        noise_config = self.config["consumption_noise"]
        dispersion = noise_config["dispersion"]
        zero_inflation = noise_config["zero_inflation"]
        dept_configs = self.config["hospital"]["departments"]
        presc_types = list(self.config["prescription_patterns"].keys())
        presc_weights = list(self.config["prescription_patterns"].values())
        presc_indices = np.arange(len(presc_types))

        n_products = len(self.products)
        n_days = len(self.date_range)
        n_depts = len(dept_configs)

        # Pre-build per-product arrays for vectorized operations
        base_demands = np.array([p.metadata["base_demand_per_day"] for p in self.products])
        atc_classes = [p.metadata["atc_class"] for p in self.products]
        product_ids = [p.id for p in self.products]
        dept_ids = [d["id"] for d in dept_configs]
        dept_weights = np.array([d["weight"] for d in dept_configs])
        dept_mults = np.array([d["consumption_multiplier"] for d in dept_configs])

        # Pre-compute seasonal multiplier array: (n_days, n_atc_classes)
        atc_keys = list(self.config["products"]["class_base_demand_per_100_beds"].keys()) + ["OTHER"]
        seasonal_mults = np.ones((n_days, len(atc_keys)), dtype=np.float64)
        atc_index = {atc: i for i, atc in enumerate(atc_keys)}
        for day_idx, sim_date in enumerate(self.date_range.to_list()):
            current_date = sim_date.date() if hasattr(sim_date, 'date') else sim_date
            sm = seasonal_factors.get(current_date, {})
            for atc, val in sm.items():
                if atc in atc_index:
                    seasonal_mults[day_idx, atc_index[atc]] = val

        # Map each product to its ATC seasonal column index
        product_atc_idx = np.array([atc_index.get(atc, len(atc_keys)-1) for atc in atc_classes])

        print(f"      Gerando consumo vetorizado ({n_days} dias x {n_products} produtos x {n_depts} deptos)...")

        # ========== VECTORIZED CONSUMPTION GENERATION ==========
        batch_size = 100  # process in day-batches to manage memory
        total_consumptions = 0
        total_movements = 0

        for batch_start in range(0, n_days, batch_size):
            batch_end = min(batch_start + batch_size, n_days)
            batch_days = batch_end - batch_start

            for d_idx in range(n_depts):
                # Expected demand: (batch_days, n_products)
                seasonal = seasonal_mults[batch_start:batch_end][:, product_atc_idx]  # (batch_days, n_products)
                expected = base_demands[np.newaxis, :] * dept_weights[d_idx] * dept_mults[d_idx] * seasonal

                # Zero inflation mask
                zero_mask = self.rng.random((batch_days, n_products)) < zero_inflation

                # Negative binomial sampling (vectorized)
                n_param = dispersion
                p_param = np.where(expected > 0, dispersion / (dispersion + expected), 1.0)
                quantities = self.rng.negative_binomial(n_param, np.clip(p_param, 1e-10, 1.0))

                # Apply zero inflation and zero expected
                quantities[zero_mask] = 0
                quantities[expected <= 0] = 0

                # Prescription types (vectorized)
                presc_samples = self.rng.choice(presc_indices, size=(batch_days, n_products), p=presc_weights)

                # Find non-zero consumption events
                day_offsets, prod_indices = np.nonzero(quantities > 0)

                for i in range(len(day_offsets)):
                    day_idx = batch_start + day_offsets[i]
                    prod_idx = prod_indices[i]
                    qty = int(quantities[day_offsets[i], prod_indices[i]])

                    if qty <= 0:
                        continue

                    sim_date_val = self.date_range[int(day_idx)]
                    current_date = sim_date_val.date() if hasattr(sim_date_val, 'date') else sim_date_val

                    product = self.products[prod_idx]

                    consumption = Consumption(
                        id=uuid4(),
                        product_id=product_ids[prod_idx],
                        consumption_date=current_date,
                        quantity=qty,
                        department=Department(dept_ids[d_idx]),
                        prescription_type=PrescriptionType(presc_types[presc_samples[day_offsets[i], prod_indices[i]]]),
                        context={
                            "seasonal_multiplier": round(float(seasonal[day_offsets[i], prod_indices[i]]), 3),
                            "department_multiplier": float(dept_mults[d_idx]),
                        },
                    )
                    self.consumptions.append(consumption)
                    total_consumptions += 1

                    # Record dispensing
                    self._record_dispensing(product, qty, current_date, pharmacists, current_stock)

            # Process arrivals and reorder checks per-day within batch
            for day_offset in range(batch_days):
                day_idx = batch_start + day_offset
                sim_date_val = self.date_range[int(day_idx)]
                current_date = sim_date_val.date() if hasattr(sim_date_val, 'date') else sim_date_val

                self._process_arrivals(current_date, pending_orders, current_stock)

                if current_date.weekday() == 0:
                    self._check_reorder_points(current_date, current_stock, pending_orders)

                self._check_expiries(current_date)

            if (batch_start // batch_size) % 10 == 0:
                print(f"      ... {batch_end}/{n_days} dias processados ({total_consumptions} consumos)")

        print(f"      {total_consumptions} registros de consumo")
        print(f"      {len(self.movements)} movimentos de estoque")

    def _compute_seasonal_factors(self) -> dict:
        """Pre-compute seasonal multipliers for each date and product class."""
        factors = {}
        for sim_date in self.date_range.to_list():
            current_date = sim_date.date() if hasattr(sim_date, 'date') else sim_date
            factors[current_date] = self._get_seasonal_multiplier(current_date)
        return factors

    def _get_seasonal_multiplier(self, current_date: date) -> dict[str, float]:
        """Calculate seasonal multiplier for each ATC class."""
        multipliers = {atc: 1.0 for atc in self.config["products"]["class_base_demand_per_100_beds"].keys()}
        multipliers["OTHER"] = 1.0

        # Fourier-based base seasonality
        if self.config["seasonality"]["enabled"]:
            day_of_year = current_date.timetuple().tm_yday
            for k in range(1, self.config["seasonality"]["fourier_terms"] + 1):
                sin_component = np.sin(2 * np.pi * k * day_of_year / 365.25)
                cos_component = np.cos(2 * np.pi * k * day_of_year / 365.25)
                # Base seasonality affects all classes
                base_effect = 0.1 * sin_component + 0.05 * cos_component
                for atc in multipliers:
                    multipliers[atc] *= (1 + base_effect)

        # Holiday effects
        for holiday in self.config["seasonality"]["holidays_br"]:
            for h_date_str in holiday["dates"]:
                h_date = date.fromisoformat(h_date_str)
                delta = (current_date - h_date).days
                if abs(delta) <= holiday["window_days"]:
                    # Distance-based effect
                    distance_factor = 1 - (abs(delta) / (holiday["window_days"] + 1))
                    effect = holiday["effect"] * distance_factor
                    for atc in multipliers:
                        multipliers[atc] *= (1 + effect)

        # Class-specific seasonality
        class_seasonality = self.config["seasonality"].get("class_seasonality", {})
        month = current_date.month

        for atc, patterns in class_seasonality.items():
            if atc in multipliers:
                if "winter_multiplier" in patterns and month in [6, 7, 8]:
                    multipliers[atc] *= patterns["winter_multiplier"]
                if "summer_multiplier" in patterns and month in [12, 1, 2]:
                    multipliers[atc] *= patterns["summer_multiplier"]
                if "november_multiplier" in patterns and month == 11:
                    multipliers[atc] *= patterns["november_multiplier"]
                if "december_multiplier" in patterns and month == 12:
                    multipliers[atc] *= patterns["december_multiplier"]
                if "january_multiplier" in patterns and month == 1:
                    multipliers[atc] *= patterns["january_multiplier"]

        return multipliers

    def _simulate_product_daily_consumption(
        self,
        product: Product,
        current_date: date,
        current_stock: dict,
        pharmacists: list[User],
        seasonal_factors: dict,
    ) -> None:
        """Simulate daily consumption for a single product."""
        base_demand = product.metadata["base_demand_per_day"]
        atc = product.metadata["atc_class"]

        # Get seasonal multiplier
        seasonal_mult = seasonal_factors.get(current_date, {}).get(atc, 1.0)

        # Department mix
        dept_weights = [d["weight"] for d in self.config["hospital"]["departments"]]
        departments = [d["id"] for d in self.config["hospital"]["departments"]]
        dept_multipliers = [d["consumption_multiplier"] for d in self.config["hospital"]["departments"]]

        # Prescription type
        presc_types = list(self.config["prescription_patterns"].keys())
        presc_weights = list(self.config["prescription_patterns"].values())

        # Generate consumption per department
        for dept_id, dept_weight, dept_mult in zip(departments, dept_weights, dept_multipliers):
            # Expected consumption for this department
            expected = base_demand * dept_weight * dept_mult * seasonal_mult

            # Sample from negative binomial (overdispersed count data)
            noise_config = self.config["consumption_noise"]
            dispersion = noise_config["dispersion"]
            zero_inflation = noise_config["zero_inflation"]

            if self.rng.random() < zero_inflation:
                qty = 0
            else:
                # Negative binomial: variance = mean + mean^2/dispersion
                if expected > 0:
                    n = dispersion
                    p = dispersion / (dispersion + expected)
                    qty = max(0, int(self.rng.negative_binomial(n, p)))
                else:
                    qty = 0

            if qty > 0:
                # Record consumption
                consumption = Consumption(
                    id=uuid4(),
                    product_id=product.id,
                    consumption_date=current_date,
                    quantity=qty,
                    department=Department(dept_id),
                    prescription_type=PrescriptionType(self.rng.choice(presc_types, p=presc_weights)),
                    context={
                        "seasonal_multiplier": round(seasonal_mult, 3),
                        "department_multiplier": dept_mult,
                    },
                )
                self.consumptions.append(consumption)

                # Record stock movement (FEFO - First Expired First Out)
                self._record_dispensing(product, qty, current_date, pharmacists, current_stock)

    def _record_dispensing(
        self,
        product: Product,
        quantity: int,
        current_date: date,
        pharmacists: list[User],
        current_stock: dict,
    ) -> None:
        """Record stock movement using FEFO logic with indexed lookups."""
        remaining = quantity
        wh_id = self._primary_warehouse_id

        # O(1) index lookup instead of scanning all batches
        available_batches = self._get_available_batches(product.id, wh_id)
        available_batches.sort(key=lambda b: b.expiry_date)

        pharmacist = self.rng.choice(pharmacists)

        for batch in available_batches:
            if remaining <= 0:
                break

            dispense_qty = min(batch.quantity, remaining)
            batch.quantity -= dispense_qty
            current_stock[product.id][wh_id] -= dispense_qty
            remaining -= dispense_qty

            movement = StockMovement(
                id=uuid4(),
                batch_id=batch.id,
                user_id=pharmacist.id,
                quantity_change=-dispense_qty,
                movement_type=MovementType.OUT,
                reference_type="prescription",
                reference_id=uuid4(),
                notes=f"Dispensação {Department.WARD.value}",
            )
            self.movements.append(movement)

            # Update batch status
            if batch.quantity == 0:
                batch.status = BatchStatus.EXPIRED if batch.expiry_date < current_date else BatchStatus.AVAILABLE

        # If still remaining (stockout), record as emergency/shortage
        if remaining > 0:
            # This triggers a stockout event - would be handled by alert system
            pass

    def _process_arrivals(
        self,
        current_date: date,
        pending_orders: dict,
        current_stock: dict,
    ) -> None:
        """Process purchase order arrivals."""
        wh_id = self._primary_warehouse_id
        for product_id, orders in pending_orders.items():
            arriving = [o for o in orders if o["arrival_date"] == current_date]
            for order in arriving:
                product = self._products_by_id[product_id]

                batch = InventoryBatch(
                    id=uuid4(),
                    product_id=product_id,
                    warehouse_id=wh_id,
                    batch_number=f"RC{current_date.strftime('%Y%m%d')}{str(order['order_id'])[:4]}",
                    quantity=order["quantity"],
                    expiry_date=current_date + timedelta(days=int(self.rng.integers(180, 730))),
                    manufacture_date=current_date - timedelta(days=int(self.rng.integers(30, 180))),
                    unit_cost=product.unit_cost * self.rng.uniform(0.9, 1.1),
                    status=BatchStatus.AVAILABLE,
                    received_at=datetime.combine(current_date, datetime.min.time()),
                )
                self.batches.append(batch)
                self._add_batch_to_index(batch)
                current_stock[product_id][wh_id] += order["quantity"]

                movement = StockMovement(
                    id=uuid4(),
                    batch_id=batch.id,
                    user_id=None,
                    quantity_change=order["quantity"],
                    movement_type=MovementType.IN,
                    reference_type="purchase_order",
                    reference_id=order["order_id"],
                    notes=f"Recebimento pedido {order['order_id']}",
                )
                self.movements.append(movement)

            # Remove arrived orders
            pending_orders[product_id] = [o for o in orders if o["arrival_date"] > current_date]

    def _check_reorder_points(
        self,
        current_date: date,
        current_stock: dict,
        pending_orders: dict,
    ) -> None:
        """Check reorder points and create purchase orders."""
        wh_id = self._primary_warehouse_id

        for product in self.products:
            available = current_stock[product.id][wh_id]

            if available <= product.min_stock_level:
                # Check if there's already a pending order
                has_pending = len(pending_orders[product.id]) > 0

                if not has_pending:
                    # Calculate order quantity (up to max level)
                    order_qty = product.max_stock_level - available
                    order_qty = max(order_qty, product.min_stock_level * 2)

                    # Select supplier
                    supplier = self.rng.choice(self.suppliers)
                    lead_time = int(self.rng.normal(
                        supplier["lead_time_mean"],
                        supplier["lead_time_std"]
                    ))
                    lead_time = max(supplier["lead_time_min"], min(supplier["lead_time_max"], lead_time))

                    arrival_date = current_date + timedelta(days=lead_time)

                    order = {
                        "order_id": uuid4(),
                        "quantity": order_qty,
                        "arrival_date": arrival_date,
                        "supplier_id": supplier["id"],
                    }
                    pending_orders[product.id].append(order)

    def _check_expiries(self, current_date: date) -> None:
        """Check for expiring batches — only scan AVAILABLE batches via index."""
        for key, batch_list in self._batches_by_product.items():
            for batch in batch_list:
                if batch.status != BatchStatus.AVAILABLE:
                    continue
                if batch.expiry_date < current_date:
                    batch.status = BatchStatus.EXPIRED

    def _generate_predictions(self) -> None:
        print("   [PREDICTION] Gerando predicoes historicas (para treino/validacao)...")
        # This would normally be done by the ML pipeline
        # For synthetic data, we generate "historical predictions" that the model would have made
        pass

    def _generate_alerts(self) -> None:
        print("   [ALERT] Gerando alertas...")
        wh_id = self._primary_warehouse_id

        # Stockout risk alerts — use index for O(1) per product
        for product in self.products:
            batches = self._batches_by_product.get((product.id, wh_id), [])
            current_qty = sum(b.quantity for b in batches if b.status == BatchStatus.AVAILABLE)

            # Simple risk calculation
            daily_avg = product.metadata["base_demand_per_day"]
            if daily_avg > 0:
                days_until_stockout = current_qty / daily_avg

                if days_until_stockout <= 7:
                    severity = AlertSeverity.CRITICAL if days_until_stockout <= 3 else AlertSeverity.WARNING
                    alert = Alert(
                        id=uuid4(),
                        product_id=product.id,
                        alert_type=AlertType.SHORTAGE_RISK,
                        severity=severity,
                        message=f"Risco de falta: estoque atual durará ~{int(days_until_stockout)} dias",
                        metadata={
                            "current_stock": current_qty,
                            "daily_avg_consumption": round(daily_avg, 1),
                            "days_until_stockout": round(days_until_stockout, 1),
                            "recommended_order_qty": product.max_stock_level - current_qty,
                        },
                    )
                    self.alerts.append(alert)

                # Expiry alerts — use index
                expiring_batches = [
                    b for b in batches
                    if b.status == BatchStatus.AVAILABLE
                    and 0 <= (b.expiry_date - self.end_date).days <= 90
                ]
                if expiring_batches:
                    total_expiring = sum(b.quantity for b in expiring_batches)
                    alert = Alert(
                        id=uuid4(),
                        product_id=product.id,
                        alert_type=AlertType.EXPIRY_RISK,
                        severity=AlertSeverity.WARNING,
                        message=f"{len(expiring_batches)} lotes vencendo em 90 dias ({total_expiring} unidades)",
                        metadata={
                            "expiring_batches": len(expiring_batches),
                            "total_quantity": total_expiring,
                        },
                    )
                    self.alerts.append(alert)

                # Overstock alerts
                if current_qty >= product.max_stock_level * 1.2:
                    alert = Alert(
                        id=uuid4(),
                        product_id=product.id,
                        alert_type=AlertType.OVERSTOCK,
                        severity=AlertSeverity.INFO,
                        message=f"Estoque {int((current_qty/product.max_stock_level - 1)*100)}% acima do máximo",
                        metadata={
                            "current_stock": current_qty,
                            "max_stock_level": product.max_stock_level,
                            "excess_percentage": round((current_qty/product.max_stock_level - 1)*100, 1),
                        },
                    )
                    self.alerts.append(alert)

        print(f"      {len(self.alerts)} alertas gerados")

    def _to_dataframes(self) -> dict[str, pl.DataFrame]:
        print("   [DATAFRAME] Convertendo para DataFrames Polars...")

        def to_df(objects: list, schema: dict) -> pl.DataFrame:
            if not objects:
                return pl.DataFrame(schema=schema)
            # Build columns directly for speed
            cols: dict[str, list] = {col: [] for col in schema}
            for obj in objects:
                d = obj.__dict__
                for col in schema:
                    val = d.get(col)
                    if val is None:
                        cols[col].append(None)
                    elif isinstance(val, UUID):
                        cols[col].append(str(val))
                    elif isinstance(val, datetime):
                        cols[col].append(val.isoformat())
                    elif isinstance(val, date):
                        cols[col].append(val)
                    elif isinstance(val, enum.Enum):
                        cols[col].append(val.value)
                    elif isinstance(val, dict):
                        cols[col].append(json.dumps(val, default=str))
                    else:
                        cols[col].append(val)
            return pl.DataFrame(cols, schema=schema)

        schemas = {
            "users": {"id": pl.Utf8, "email": pl.Utf8, "hashed_password": pl.Utf8, "full_name": pl.Utf8, "role": pl.Utf8, "is_active": pl.Boolean, "last_login": pl.Utf8, "created_at": pl.Utf8, "updated_at": pl.Utf8},
            "warehouses": {"id": pl.Utf8, "name": pl.Utf8, "location": pl.Utf8, "is_primary": pl.Boolean, "created_at": pl.Utf8, "updated_at": pl.Utf8},
            "products": {"id": pl.Utf8, "sku": pl.Utf8, "name": pl.Utf8, "generic_name": pl.Utf8, "category": pl.Utf8, "atc_code": pl.Utf8, "unit": pl.Utf8, "unit_cost": pl.Float64, "min_stock_level": pl.Int64, "max_stock_level": pl.Int64, "lead_time_days": pl.Int64, "controlled_substance": pl.Boolean, "is_active": pl.Boolean, "metadata": pl.Utf8, "created_at": pl.Utf8, "updated_at": pl.Utf8},
            "inventory_batches": {"id": pl.Utf8, "product_id": pl.Utf8, "warehouse_id": pl.Utf8, "batch_number": pl.Utf8, "quantity": pl.Int64, "expiry_date": pl.Date, "manufacture_date": pl.Date, "unit_cost": pl.Float64, "status": pl.Utf8, "received_at": pl.Utf8, "created_at": pl.Utf8, "updated_at": pl.Utf8},
            "stock_movements": {"id": pl.Utf8, "batch_id": pl.Utf8, "user_id": pl.Utf8, "quantity_change": pl.Int64, "movement_type": pl.Utf8, "reference_type": pl.Utf8, "reference_id": pl.Utf8, "notes": pl.Utf8, "created_at": pl.Utf8},
            "consumption": {"id": pl.Utf8, "product_id": pl.Utf8, "consumption_date": pl.Date, "quantity": pl.Int64, "department": pl.Utf8, "prescription_type": pl.Utf8, "context": pl.Utf8, "created_at": pl.Utf8, "updated_at": pl.Utf8},
            "alerts": {"id": pl.Utf8, "product_id": pl.Utf8, "alert_type": pl.Utf8, "severity": pl.Utf8, "message": pl.Utf8, "metadata": pl.Utf8, "acknowledged": pl.Boolean, "acknowledged_by": pl.Utf8, "acknowledged_at": pl.Utf8, "created_at": pl.Utf8},
        }

        return {
            "users": to_df(self.users, schemas["users"]),
            "warehouses": to_df(self.warehouses, schemas["warehouses"]),
            "products": to_df(self.products, schemas["products"]),
            "inventory_batches": to_df(self.batches, schemas["inventory_batches"]),
            "stock_movements": to_df(self.movements, schemas["stock_movements"]),
            "consumption": to_df(self.consumptions, schemas["consumption"]),
            "alerts": to_df(self.alerts, schemas["alerts"]),
        }


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic data for PharmaPredict")
    parser.add_argument("--config", default="ml/config/data_generation.yaml", help="Path to config YAML")
    parser.add_argument("--output", default="ml/data/synthetic", help="Output directory")
    parser.add_argument("--format", choices=["parquet", "csv", "json"], default="parquet")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = SyntheticDataGenerator(config_path)
    dataframes = generator.generate_all()

    print(f"\n[SAVE] Salvando dados em {output_dir} ({args.format})...")
    for name, df in dataframes.items():
        if df.is_empty():
            print(f"   [WARN] {name}: vazio, pulando")
            continue

        if args.format == "parquet":
            path = output_dir / f"{name}.parquet"
            df.write_parquet(path, compression="snappy")
        elif args.format == "csv":
            path = output_dir / f"{name}.csv"
            df.write_csv(path)
        elif args.format == "json":
            path = output_dir / f"{name}.json"
            df.write_json(path)

        print(f"   [OK] {name}: {len(df)} linhas -> {path}")

    # Save metadata
    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "config": str(config_path),
        "period": {
            "start": generator.start_date.isoformat(),
            "end": generator.end_date.isoformat(),
        },
        "counts": {name: len(df) for name, df in dataframes.items()},
        "seed": generator.config["simulation"]["random_seed"],
    }
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"   [OK] metadata.json salvo")

    print("\n[SUCCESS] Geracao concluida com sucesso!")


if __name__ == "__main__":
    main()