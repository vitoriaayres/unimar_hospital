'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface InventoryBatch {
  id: string;
  product_id: string;
  warehouse_id: string;
  batch_number: string;
  quantity: number;
  expiry_date: string;
  manufacture_date: string | null;
  unit_cost: number;
  status: 'available' | 'reserved' | 'expired' | 'recalled' | 'quarantine';
  received_at: string;
  created_at: string;
  updated_at: string;
  product?: {
    id: string;
    sku: string;
    name: string;
    generic_name: string | null;
    category: string;
  };
}

export interface StockMovement {
  id: string;
  batch_id: string;
  user_id: string | null;
  quantity_change: number;
  movement_type: 'in' | 'out' | 'adjustment' | 'transfer' | 'loss' | 'expired' | 'recalled';
  reference_type: string | null;
  reference_id: string | null;
  notes: string | null;
  created_at: string;
  batch?: InventoryBatch;
  user?: {
    id: string;
    full_name: string;
  };
}

export interface InventoryListParams {
  page?: number;
  size?: number;
  product_id?: string;
  status?: string;
  expiring_within_days?: number;
  in_stock?: boolean;
  search?: string;
}

export interface InventoryListResponse {
  items: InventoryBatch[];
  total: number;
  page: number;
  size: number;
  pages: number;
}


export interface InventorySummaryRow {
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
  total_value: number | string;   
  min_stock_level: number;
  max_stock_level: number;
  days_of_supply: number | null;
  is_low_stock: boolean;
  is_overstock: boolean;
}


export interface InventorySummary {
  total_batches: number;
  total_quantity: number;
  total_value: number;
  expiring_30d: number;
  expiring_90d: number;
  expired_count: number;
  low_stock_count: number;
}

async function fetchInventoryBatches(params: InventoryListParams = {}): Promise<InventoryListResponse> {
  const response = await api.get<InventoryListResponse>('/inventory/batches', { params });
  return response.data;
}

async function fetchInventoryBatch(id: string): Promise<InventoryBatch> {
  const response = await api.get<InventoryBatch>(`/inventory/batches/${id}`);
  return response.data;
}


async function fetchStockMovements(params: { batch_id?: string; page?: number; size?: number } = {}): Promise<{ items: StockMovement[]; total: number }> {
  const response = await api.get<{ items: StockMovement[]; total: number }>('/inventory/movements', { params });
  return response.data;
}

async function createStockMovement(data: {
  batch_id: string;
  quantity_change: number;
  movement_type: string;
  reference_type?: string;
  reference_id?: string;
  notes?: string;
}): Promise<StockMovement> {
  const response = await api.post<StockMovement>('/inventory/movements', data);
  return response.data;
}

export function useInventoryBatches(params: InventoryListParams = {}) {
  return useQuery<InventoryListResponse>({
    queryKey: ['inventory', 'batches', params],
    queryFn: () => fetchInventoryBatches(params),
    placeholderData: (previousData) => previousData,
  });
}

export function useInventoryBatch(id: string) {
  return useQuery<InventoryBatch>({
    queryKey: ['inventory', 'batches', id],
    queryFn: () => fetchInventoryBatch(id),
    enabled: !!id,
  });
}

export function useInventorySummary() {
  return useQuery<InventorySummary>({
    queryKey: ['inventory', 'summary'],
    queryFn: async () => {
      const response = await api.get<InventorySummaryRow[]>('/inventory/summary');
      const rows = response.data;

      return {
        total_batches: rows.reduce((s, r) => s + r.batches_count, 0),
        total_quantity: rows.reduce((s, r) => s + r.total_quantity, 0),
        total_value: rows.reduce((s, r) => s + Number(r.total_value), 0),
        expiring_30d: rows.reduce((s, r) => s + r.batches_expiring_30d, 0),
        expiring_90d: rows.reduce((s, r) => s + r.batches_expiring_90d, 0),
        expired_count: rows.reduce((s, r) => s + r.expired_quantity, 0),
        low_stock_count: rows.filter((r) => r.is_low_stock).length,
      };
    },
    refetchInterval: 30000,
  });
}

export function useStockMovements(batchId?: string, page = 1, size = 50) {
  return useQuery<{ items: StockMovement[]; total: number }>({
    queryKey: ['inventory', 'movements', batchId, page, size],
    queryFn: () => fetchStockMovements({ batch_id: batchId, page, size }),
    enabled: !!batchId,
  });
}

export function useCreateStockMovement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createStockMovement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
  });
}

export const BATCH_STATUSES = [
  { value: 'available', label: 'Disponível', color: 'success' },
  { value: 'reserved', label: 'Reservado', color: 'info' },
  { value: 'expired', label: 'Vencido', color: 'destructive' },
  { value: 'recalled', label: 'Recolhido', color: 'warning' },
  { value: 'quarantine', label: 'Quarentena', color: 'secondary' },
] as const;

export const MOVEMENT_TYPES = [
  { value: 'in', label: 'Entrada', icon: '⬆️' },
  { value: 'out', label: 'Saída', icon: '⬇️' },
  { value: 'adjustment', label: 'Ajuste', icon: '⚖️' },
  { value: 'transfer', label: 'Transferência', icon: '↔️' },
  { value: 'loss', label: 'Perda', icon: '💸' },
  { value: 'expired', label: 'Vencido', icon: '⏰' },
  { value: 'recalled', label: 'Recolhido', icon: '🚫' },
] as const;

export function getStatusConfig(status: string) {
  return BATCH_STATUSES.find(s => s.value === status) || { label: status, color: 'secondary' };
}

export function getMovementTypeConfig(type: string) {
  return MOVEMENT_TYPES.find(m => m.value === type) || { label: type, icon: '' };
}