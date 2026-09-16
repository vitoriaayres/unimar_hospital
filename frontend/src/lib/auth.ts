'use client';

import Cookies from 'js-cookie';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiEndpoints } from './api';

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

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export function getAccessToken(): string | undefined {
  return Cookies.get(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | undefined {
  return Cookies.get(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  Cookies.set(ACCESS_TOKEN_KEY, accessToken, { expires: 1 / 96, secure: process.env.NODE_ENV === 'production', sameSite: 'lax' });
  Cookies.set(REFRESH_TOKEN_KEY, refreshToken, { expires: 7, secure: process.env.NODE_ENV === 'production', sameSite: 'lax' });
}

export function clearTokens(): void {
  Cookies.remove(ACCESS_TOKEN_KEY);
  Cookies.remove(REFRESH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    async function fetchUser() {
      if (!isAuthenticated()) {
        setLoading(false);
        return;
      }

      try {
        const response = await apiEndpoints.auth.me();
        setUser(response.data);
      } catch {
        clearTokens();
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    fetchUser();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await apiEndpoints.auth.login({ email, password });
    const { access_token, refresh_token } = response.data;
    setTokens(access_token, refresh_token);
    const userResponse = await apiEndpoints.auth.me();
    setUser(userResponse.data);
    return userResponse.data;
  };

  const logout = async () => {
    try {
      await apiEndpoints.auth.logout();
    } finally {
      clearTokens();
      setUser(null);
      router.push('/login');
    }
  };

  return { user, loading, login, logout, isAuthenticated: !!user };
}

export function useRequireAuth(allowedRoles?: string[]) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!user) {
        router.push('/login');
      } else if (allowedRoles && !allowedRoles.includes(user.role)) {
        router.push('/unauthorized');
      }
    }
  }, [user, loading, allowedRoles, router]);

  return { user, loading };
}