'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface DashboardKPIs {
  total_skus: number;
  low_stock_count: number;
  stockout_risk_count: number;
  expiring_soon_count: number;
  total_inventory_value: number;
  average_mape: number;
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
  status: string;
}

export interface ConsumptionTrendPoint {
  date: string;
  total_quantity: number;
  by_department: Record<string, number>;
  by_category: Record<string, number>;
}

export interface DashboardResponse {
  kpis: DashboardKPIs;
  stockout_risks: StockoutRiskItem[];
  expiry_timeline: ExpiryTimelineItem[];
  consumption_trends: ConsumptionTrendPoint[];
  generated_at: string;
}

async function fetchDashboard(): Promise<DashboardResponse> {
  const response = await api.get<DashboardResponse>('/dashboard');
  return response.data;
}

async function fetchKPIs(): Promise<DashboardKPIs> {
  const response = await api.get<DashboardKPIs>('/dashboard/kpis');
  return response.data;
}

async function fetchStockoutRisk(limit: number): Promise<StockoutRiskItem[]> {
  const response = await api.get<StockoutRiskItem[]>('/dashboard/stockout-risk', { params: { limit } });
  return response.data;
}

async function fetchExpiryTimeline(daysAhead: number, limit: number): Promise<ExpiryTimelineItem[]> {
  const response = await api.get<ExpiryTimelineItem[]>('/dashboard/expiry-timeline', { params: { days_ahead: daysAhead, limit } });
  return response.data;
}

async function fetchConsumptionTrends(daysBack: number, department?: string): Promise<ConsumptionTrendPoint[]> {
  const params: Record<string, string | number> = { days_back: daysBack };
  if (department) params.department = department;
  const response = await api.get<ConsumptionTrendPoint[]>('/dashboard/consumption-trends', { params });
  return response.data;
}

export function useDashboard() {
  return useQuery<DashboardResponse>({
    queryKey: ['dashboard'],
    queryFn: fetchDashboard,
    refetchInterval: 30000,
  });
}

export function useKPIs() {
  return useQuery<DashboardKPIs>({
    queryKey: ['dashboard', 'kpis'],
    queryFn: fetchKPIs,
    refetchInterval: 30000,
  });
}

export function useStockoutRisk(limit = 20) {
  return useQuery<StockoutRiskItem[]>({
    queryKey: ['dashboard', 'stockout-risk', limit],
    queryFn: () => fetchStockoutRisk(limit),
    refetchInterval: 30000,
  });
}

export function useExpiryTimeline(daysAhead = 90, limit = 50) {
  return useQuery<ExpiryTimelineItem[]>({
    queryKey: ['dashboard', 'expiry-timeline', daysAhead, limit],
    queryFn: () => fetchExpiryTimeline(daysAhead, limit),
    refetchInterval: 30000,
  });
}

export function useConsumptionTrends(daysBack = 30, department?: string) {
  return useQuery<ConsumptionTrendPoint[]>({
    queryKey: ['dashboard', 'consumption-trends', daysBack, department],
    queryFn: () => fetchConsumptionTrends(daysBack, department),
    refetchInterval: 30000,
  });
}