'use client';

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';
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
      `${API_URL}/api/v1/refresh`,
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
  // Mesmo formato do axios: api.get(url, { params })
  get<T>(url: string, config?: AxiosRequestConfig) {
    return this.client.get<T>(url, config);
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

// Autenticação (o restante das rotas é chamado pelos hooks em src/hooks)
export const apiEndpoints = {
  auth: {
    login: (data: { email: string; password: string }) =>
      axios.post<{ access_token: string; refresh_token: string }>(
        `${API_URL}/api/v1/login`,
        new URLSearchParams({
          username: data.email,
          password: data.password,
        }),
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          withCredentials: true,
        }
      ),
    logout: () => api.post('/logout'),
    me: () => api.get<User>('/me'),
    changePassword: (data: { current_password: string; new_password: string }) =>
      api.patch('/me/password', data),
  },
};

/** Busca todas as páginas de uma listagem paginada (para exportar). */
export async function fetchAllPages<T>(
  url: string,
  params: object = {},
  { pageSize = 100, maxRows = 10000 } = {}
): Promise<T[]> {
  const rows: T[] = [];
  for (let page = 1; rows.length < maxRows; page++) {
    const { data } = await api.get<{ items: T[]; pages: number }>(url, {
      params: { ...params, page, size: pageSize },
    });
    rows.push(...data.items);
    if (page >= data.pages) break;
  }
  return rows.slice(0, maxRows);
}

const ERROR_TRANSLATIONS: Record<string, string> = {
  'Email already registered': 'Este e-mail já está cadastrado',
  'Current password is incorrect': 'A senha atual está incorreta',
  'Password must contain at least one uppercase letter': 'A senha precisa ter ao menos uma letra maiúscula',
  'Password must contain at least one lowercase letter': 'A senha precisa ter ao menos uma letra minúscula',
  'Password must contain at least one digit': 'A senha precisa ter ao menos um número',
};

/** Mensagem legível de um erro da API (FastAPI devolve `detail` como texto ou lista). */
export function apiErrorMessage(error: unknown, fallback = 'Não foi possível concluir a operação'): string {
  const detail = (error as AxiosError<{ detail?: unknown }>)?.response?.data?.detail;
  const translate = (msg: string) => {
    const clean = msg.replace(/^Value error, /, '');
    return ERROR_TRANSLATIONS[clean] ?? clean;
  };
  if (typeof detail === 'string') return translate(detail);
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    const field = String(first.loc?.[first.loc.length - 1] ?? '');
    if (field.includes('password') && first.msg?.startsWith('String should have at least')) {
      return 'A senha precisa ter ao menos 8 caracteres';
    }
    if (field === 'email') return 'E-mail inválido';
    if (first.msg) return translate(first.msg);
  }
  return fallback;
}
