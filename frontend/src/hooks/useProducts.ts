'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface Product {
  id: string;
  sku: string;
  name: string;
  generic_name: string | null;
  category: string;
  atc_code: string | null;
  unit: string;
  unit_cost: number;
  min_stock_level: number;
  max_stock_level: number;
  lead_time_days: number;
  controlled_substance: boolean;
  is_active: boolean;
  product_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ProductListParams {
  page?: number;
  size?: number;
  search?: string;
  category?: string;
  controlled_substance?: boolean;
  is_active?: boolean;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

async function fetchProducts(params: ProductListParams = {}): Promise<ProductListResponse> {
  const response = await api.get<ProductListResponse>('/products', { params });
  return response.data;
}

async function fetchProduct(id: string): Promise<Product> {
  const response = await api.get<Product>(`/products/${id}`);
  return response.data;
}

async function createProduct(data: Partial<Product>): Promise<Product> {
  const response = await api.post<Product>('/products', data);
  return response.data;
}

async function updateProduct(id: string, data: Partial<Product>): Promise<Product> {
  const response = await api.patch<Product>(`/products/${id}`, data);
  return response.data;
}

async function deleteProduct(id: string): Promise<void> {
  await api.delete(`/products/${id}`);
}

export function useProducts(params: ProductListParams = {}) {
  return useQuery<ProductListResponse>({
    queryKey: ['products', params],
    queryFn: () => fetchProducts(params),
    placeholderData: (previousData) => previousData,
  });
}

export function useProduct(id: string) {
  return useQuery<Product>({
    queryKey: ['products', id],
    queryFn: () => fetchProduct(id),
    enabled: !!id,
  });
}

export function useCreateProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

export function useUpdateProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Product> }) => updateProduct(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

export function useDeleteProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

export const PRODUCT_CATEGORIES = [
  'antibiotic',
  'analgesic',
  'antithrombotic',
  'beta_blocker',
  'ppi',
  'bronchodilator',
  'psycholeptic',
  'ace_inhibitor',
  'corticosteroid',
  'other',
] as const;

export const CATEGORY_LABELS: Record<string, string> = {
  antibiotic: 'Antibiótico',
  analgesic: 'Analgésico',
  antithrombotic: 'Antitrombótico',
  beta_blocker: 'Betabloqueador',
  ppi: 'IBP',
  bronchodilator: 'Broncodilatador',
  psycholeptic: 'Psicoléptico',
  ace_inhibitor: 'IECA',
  corticosteroid: 'Corticoide',
  other: 'Outros',
};

export function getCategoryLabel(category: string): string {
  return CATEGORY_LABELS[category] || category;
}