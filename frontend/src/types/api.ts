export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'pharmacist' | 'manager' | 'admin';
  is_active: boolean;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  generic_name: string | null;
  category: ProductCategory;
  atc_code: string | null;
  unit: string;
  unit_cost: number;
  min_stock_level: number;
  max_stock_level: number;
  lead_time_days: number;
  controlled_substance: boolean;
  is_active: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export type ProductCategory =
  | 'antibiotic'
  | 'analgesic'
  | 'antithrombotic'
  | 'beta_blocker'
  | 'ppi'
  | 'bronchodilator'
  | 'psycholeptic'
  | 'ace_inhibitor'
  | 'corticosteroid'
  | 'other';

export interface InventoryBatch {
  id: string;
  product_id: string;
  warehouse_id: string;
  batch_number: string;
  quantity: number;
  expiry_date: string;
  manufacture_date: string | null;
  unit_cost: number;
  status: BatchStatus;
  received_at: string;
  created_at: string;
  updated_at: string;
  days_until_expiry: number | null;
  is_expired: boolean;
  is_expiring_soon: boolean;
}

export type BatchStatus = 'available' | 'reserved' | 'expired' | 'recalled' | 'quarantine';

export interface StockMovement {
  id: string;
  batch_id: string;
  user_id: string | null;
  quantity_change: number;
  movement_type: MovementType;
  reference_type: string | null;
  reference_id: string | null;
  notes: string | null;
  created_at: string;
}

export type MovementType = 'in' | 'out' | 'adjustment' | 'transfer' | 'loss' | 'expired' | 'recalled';

export interface InventorySummary {
  product_id: string;
  product_name: string;
  product_sku: string;
  total_quantity: number;
  available_quantity: number;
  reserved_quantity: number;
  expired_quantity: number;
  batches_count: number;
  batches_expiring_30d: number;
  batches_expiring_90d: number;
  total_value: number;
  min_stock_level: number;
  max_stock_level: number;
  days_of_supply: number | null;
  is_low_stock: boolean;
  is_overstock: boolean;
}

export interface Consumption {
  id: string;
  product_id: string;
  consumption_date: string;
  quantity: number;
  department: Department;
  prescription_type: PrescriptionType;
  context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export type Department = 'icu' | 'er' | 'ward' | 'outpatient';
export type PrescriptionType = 'routine' | 'emergency' | 'prophylactic';

export interface PredictionPoint {
  forecast_date: string;
  predicted_quantity: number;
  confidence_lower: number;
  confidence_upper: number;
}

export interface Prediction {
  id: string;
  product_id: string;
  forecast_date: string;
  predicted_quantity: number;
  confidence_lower: number;
  confidence_upper: number;
  model_version: string;
  mape_score: number | null;
  wape_score: number | null;
  created_at: string;
}

export interface ForecastResponse {
  product_id: string;
  product_name: string;
  product_sku: string;
  model_version: string;
  horizon_days: number;
  generated_at: string;
  predictions: PredictionPoint[];
  summary: Record<string, unknown>;
}

export interface ModelComparison {
  model_version: string;
  model_type: string;
  wape: number;
  mape: number;
  rmse: number;
  mae: number;
  smape: number;
  coverage: number;
  interval_width: number;
  training_date: string;
  is_production: boolean;
  is_staging: boolean;
}

export interface Alert {
  id: string;
  product_id: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  message: string;
  metadata: Record<string, unknown>;
  acknowledged: boolean;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  created_at: string;
}

export type AlertType = 'shortage_risk' | 'expiry_risk' | 'overstock' | 'reorder_point';
export type AlertSeverity = 'info' | 'warning' | 'critical';

export interface DashboardKPIs {
  total_skus: number;
  low_stock_count: number;
  stockout_risk_count: number;
  expiring_soon_count: number;
  total_inventory_value: number;
  average_wape: number;
  predictions_generated_today: number;
  alerts_unacknowledged: number;
}

export interface StockoutRiskItem {
  product_id: string;
  product_name: string;
  product_sku: string;
  current_stock: number;
  predicted_consumption_7d: number;
  predicted_consumption_30d: number;
  days_until_stockout: number | null;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  recommended_order_qty: number;
}

export interface ExpiryTimelineItem {
  batch_id: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  batch_number: string;
  quantity: number;
  expiry_date: string;
  days_until_expiry: number;
  status: BatchStatus;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}