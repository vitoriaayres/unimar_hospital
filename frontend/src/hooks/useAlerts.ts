'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface Alert {
  id: string;
  product_id: string;
  alert_type: 'shortage_risk' | 'expiry_risk' | 'overstock' | 'reorder_point';
  severity: 'info' | 'warning' | 'critical';
  message: string;
  alert_metadata: Record<string, unknown>;
  acknowledged: boolean;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  created_at: string;
  product?: {
    id: string;
    sku: string;
    name: string;
    generic_name: string | null;
    category: string;
  };
}

export interface AlertListParams {
  page?: number;
  size?: number;
  alert_type?: string;
  severity?: string;
  acknowledged?: boolean;
  product_id?: string;
}

export interface AlertListResponse {
  items: Alert[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface AlertRule {
  id: string;
  alert_type: 'shortage_risk' | 'expiry_risk' | 'overstock' | 'reorder_point';
  enabled: boolean;
  threshold_days: number; // 0 = regra sem prazo
  severity: 'info' | 'warning' | 'critical';
  notify_roles: string[];
  created_at: string;
  updated_at: string;
}

async function fetchAlerts(params: AlertListParams = {}): Promise<AlertListResponse> {
  const response = await api.get<AlertListResponse>('/alerts', { params });
  return response.data;
}

async function acknowledgeAlert(id: string): Promise<Alert> {
  const response = await api.post<Alert>(`/alerts/${id}/acknowledge`, { acknowledged: true });
  return response.data;
}

async function bulkAcknowledgeAlerts(ids: string[]): Promise<{ acknowledged: number }> {
  const response = await api.post<{ acknowledged: number }>('/alerts/bulk-acknowledge', { ids });
  return response.data;
}

async function fetchAlertRules(): Promise<AlertRule[]> {
  const response = await api.get<AlertRule[]>('/alerts/rules');
  return response.data;
}

async function updateAlertRule(id: string, data: Partial<AlertRule>): Promise<AlertRule> {
  const response = await api.patch<AlertRule>(`/alerts/rules/${id}`, data);
  return response.data;
}

export function useAlerts(params: AlertListParams = {}) {
  return useQuery<AlertListResponse>({
    queryKey: ['alerts', params],
    queryFn: () => fetchAlerts(params),
    placeholderData: (previousData) => previousData,
    refetchInterval: 30000,
  });
}

// Contagens de alertas aparecem no dashboard e no sino do cabeçalho
function invalidateAlertQueries(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ['alerts'] });
  queryClient.invalidateQueries({ queryKey: ['dashboard'] });
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: acknowledgeAlert,
    onSuccess: () => invalidateAlertQueries(queryClient),
  });
}

export function useBulkAcknowledgeAlerts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: bulkAcknowledgeAlerts,
    onSuccess: () => invalidateAlertQueries(queryClient),
  });
}

/** Total de alertas para um filtro (usa só o campo total da paginação). */
export function useAlertCount(params: Omit<AlertListParams, 'page' | 'size'>) {
  return useQuery<number>({
    queryKey: ['alerts', 'count', params],
    queryFn: async () => (await fetchAlerts({ ...params, page: 1, size: 1 })).total,
    refetchInterval: 30000,
  });
}

export function useAlertRules() {
  return useQuery<AlertRule[]>({
    queryKey: ['alerts', 'rules'],
    queryFn: fetchAlertRules,
    refetchInterval: 60000,
  });
}

export function useUpdateAlertRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AlertRule> }) => updateAlertRule(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts', 'rules'] });
    },
  });
}

export const ALERT_TYPES = [
  { value: 'shortage_risk', label: 'Risco de Falta', icon: '⚠️', color: 'destructive' },
  { value: 'expiry_risk', label: 'Risco de Validade', icon: '⏰', color: 'warning' },
  { value: 'overstock', label: 'Excesso de Estoque', icon: '📦', color: 'info' },
  { value: 'reorder_point', label: 'Ponto de Reposição', icon: '🔄', color: 'secondary' },
] as const;

export const ALERT_SEVERITIES = [
  { value: 'critical', label: 'Crítico', color: 'destructive' },
  { value: 'warning', label: 'Atenção', color: 'warning' },
  { value: 'info', label: 'Informativo', color: 'info' },
] as const;

export function getAlertTypeConfig(type: string) {
  return ALERT_TYPES.find(t => t.value === type) || { label: type, color: 'secondary', icon: '' };
}

export function getSeverityConfig(severity: string) {
  return ALERT_SEVERITIES.find(s => s.value === severity) || { label: severity, color: 'secondary' };
}

export function formatAlertDate(date: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
}