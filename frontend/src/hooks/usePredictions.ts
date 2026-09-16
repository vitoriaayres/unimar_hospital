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
  model_version?: string;
  horizon_days?: number;
  start_date?: string;
  end_date?: string;
}

export interface PredictionListResponse {
  items: Prediction[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ModelInfo {
  version: string;
  name: string;
  algorithm: string;
  mape: number;
  created_at: string;
  is_active: boolean;
}

async function fetchPredictions(params: PredictionListParams = {}): Promise<PredictionListResponse> {
  const response = await api.get<PredictionListResponse>('/predictions', { params });
  return response.data;
}

async function fetchModels(): Promise<ModelInfo[]> {
  const response = await api.get<ModelInfo[]>('/predictions/models');
  return response.data;
}

async function generateForecast(data: { product_ids: string[]; horizon_days: number; model_version?: string }): Promise<Prediction[]> {
  const response = await api.post<Prediction[]>('/predictions/forecast', data);
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