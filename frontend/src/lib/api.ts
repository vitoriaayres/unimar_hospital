'use client';

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'pharmacist' | 'manager' | 'admin';
  is_active: boolean;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

class ApiClient {
  private client: AxiosInstance;
  private isRefreshing = false;
  private failedRequestsQueue: Array<{
    resolve: (value: unknown) => void;
    reject: (reason: unknown) => void;
  }> = [];

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,
      timeout: 30000,
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor - add access token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const accessToken = Cookies.get('access_token');
        if (accessToken) {
          config.headers.Authorization = `Bearer ${accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            // Queue the request
            return new Promise((resolve, reject) => {
              this.failedRequestsQueue.push({ resolve, reject });
            }).then(() => this.client(originalRequest));
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            await this.refreshToken();
            // Retry queued requests
            this.failedRequestsQueue.forEach(({ resolve }) => resolve(null));
            this.failedRequestsQueue = [];
            return this.client(originalRequest);
          } catch (refreshError) {
            // Reject queued requests
            this.failedRequestsQueue.forEach(({ reject }) => reject(refreshError));
            this.failedRequestsQueue = [];
            this.logout();
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private async refreshToken() {
    const refreshToken = Cookies.get('refresh_token');
    if (!refreshToken) throw new Error('No refresh token');

    const response = await axios.post(
      `${API_URL}/api/v1/auth/refresh`,
      { refresh_token: refreshToken },
      { withCredentials: true }
    );

    const { access_token, refresh_token } = response.data;
    Cookies.set('access_token', access_token, { expires: 1 / 96 }); // 15 minutes
    Cookies.set('refresh_token', refresh_token, { expires: 7 });
  }

  private logout() {
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }

  // HTTP methods
  get<T>(url: string, params?: object) {
    return this.client.get<T>(url, { params });
  }

  post<T>(url: string, data?: object) {
    return this.client.post<T>(url, data);
  }

  put<T>(url: string, data?: object) {
    return this.client.put<T>(url, data);
  }

  patch<T>(url: string, data?: object) {
    return this.client.patch<T>(url, data);
  }

  delete<T>(url: string) {
    return this.client.delete<T>(url);
  }
}

export const api = new ApiClient();

// Type-safe API helpers
export const apiEndpoints = {
  auth: {
    login: (data: { email: string; password: string }) =>
      api.post<{ access_token: string; refresh_token: string }>('/login', new URLSearchParams({
        username: data.email,
        password: data.password,
      })),
    refresh: (data: { refresh_token: string }) => api.post('/refresh', data),
    logout: () => api.post('/logout'),
    me: () => api.get<User>('/me'),
    register: (data: object) => api.post('/register', data),
    changePassword: (data: object) => api.patch('/me/password', data),
    listUsers: (params?: object) => api.get('/users', params),
    updateUser: (id: string, data: object) => api.patch(`/users/${id}`, data),
  },
  products: {
    list: (params?: object) => api.get('/products', params),
    create: (data: object) => api.post('/products', data),
    get: (id: string) => api.get(`/products/${id}`),
    update: (id: string, data: object) => api.patch(`/products/${id}`, data),
    delete: (id: string) => api.delete(`/products/${id}`),
  },
  inventory: {
    summary: (params?: object) => api.get('/inventory/summary', params),
    batches: {
      list: (params?: object) => api.get('/inventory/batches', params),
      create: (data: object) => api.post('/inventory/batches', data),
      get: (id: string) => api.get(`/inventory/batches/${id}`),
      update: (id: string, data: object) => api.patch(`/inventory/batches/${id}`, data),
    },
    movements: {
      list: (params?: object) => api.get('/inventory/movements', params),
      create: (data: object) => api.post('/inventory/movements', data),
    },
  },
  consumption: {
    list: (params?: object) => api.get('/consumption', params),
    create: (data: object) => api.post('/consumption', data),
    import: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.post('/consumption/import', formData);
    },
  },
  predictions: {
    list: (params?: object) => api.get('/predictions', params),
    forecast: (data: object) => api.post('/predictions/forecast', data),
    get: (id: string) => api.get(`/predictions/${id}`),
    models: () => api.get('/predictions/models'),
  },
  dashboard: {
    kpis: () => api.get('/dashboard/kpis'),
    stockoutRisk: (params?: object) => api.get('/dashboard/stockout-risk', params),
    expiryTimeline: (params?: object) => api.get('/dashboard/expiry-timeline', params),
    consumptionTrends: (params?: object) => api.get('/dashboard/consumption-trends', params),
  },
  alerts: {
    list: (params?: object) => api.get('/alerts', params),
    acknowledge: (id: string) => api.post(`/alerts/${id}/acknowledge`),
    bulkAcknowledge: (ids: string[]) => api.post('/alerts/bulk-acknowledge', { ids }),
    rules: {
      list: () => api.get('/alerts/rules'),
      update: (data: object) => api.patch('/alerts/rules', data),
    },
  },
  reports: {
    list: (params?: object) => api.get('/reports', params),
    generate: (data: object) => api.post('/reports/generate', data),
    download: (id: string) => api.get(`/reports/${id}/download`, { responseType: 'blob' }),
  },
};