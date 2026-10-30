'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

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
  product?: {
    id: string;
    sku: string;
    name: string;
    generic_name: string | null;
    category: string;
  };
}

export interface PredictionListParams {
  page?: number;
  size?: number;
  product_id?: string;
  search?: string;
  model_version?: string;
  start_date?: string;
  end_date?: string;
  sort_by?: 'forecast_date' | 'predicted_quantity' | 'created_at';
  sort_order?: 'asc' | 'desc';
}

export interface PredictionListResponse {
  items: Prediction[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ModelInfo {
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

export interface ForecastResponse {
  product_id: string;
  product_name: string;
  product_sku: string;
  model_version: string;
  horizon_days: number;
  generated_at: string;
  predictions: {
    forecast_date: string;
    predicted_quantity: number;
    confidence_lower: number;
    confidence_upper: number;
  }[];
  summary: Record<string, number>;
}

async function fetchPredictions(params: PredictionListParams = {}): Promise<PredictionListResponse> {
  const response = await api.get<PredictionListResponse>('/predictions', { params });
  return response.data;
}

async function fetchModels(): Promise<ModelInfo[]> {
  const response = await api.get<ModelInfo[]>('/predictions/models');
  return response.data;
}

async function generateForecast(data: { product_id: string; horizon_days: number; model_version?: string }): Promise<ForecastResponse> {
  const response = await api.post<ForecastResponse>('/predictions/forecast', data);
  return response.data;
}

export function usePredictions(params: PredictionListParams = {}) {
  return useQuery<PredictionListResponse>({
    queryKey: ['predictions', params],
    queryFn: () => fetchPredictions(params),
    placeholderData: (previousData) => previousData,
  });
}

export function useModels() {
  return useQuery<ModelInfo[]>({
    queryKey: ['predictions', 'models'],
    queryFn: fetchModels,
    refetchInterval: 60000,
  });
}

export function useGenerateForecast() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: generateForecast,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['predictions'] });
    },
  });
}

export function formatPredictionDate(date: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(date));
}
export interface ModelReport {
  metrics: {
    wape: number;
    mape: number;
    smape: number;
    rmse: number;
    mae: number;
    baseline_wape: number;
    baseline_mape: number;
    wape_low: number;
    wape_mid: number;
    wape_high: number;
    blend_weight: number;
    n_features: number;
    n_train: number;
    n_valid: number;
    n_test: number;
    best_iteration: number;
    trained_at: string;
  };
  test_period: { start: string; end: string };
  weekly: Array<{ week: string; actual: number; predicted: number; baseline: number }>;
  by_category: Array<{ category: string; wape: number; baseline_wape: number; n: number }>;
  feature_importance: Array<{ feature: string; importance: number }>;
}

async function fetchModelReport(): Promise<ModelReport> {
  const response = await api.get<ModelReport>('/predictions/model-report');
  return response.data;
}

export function useModelReport() {
  return useQuery<ModelReport>({
    queryKey: ['predictions', 'model-report'],
    queryFn: fetchModelReport,
  });
}
