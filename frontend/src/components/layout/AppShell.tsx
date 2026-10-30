'use client';

import { ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

// Telas abertas, sem menu e sem exigir login
const PUBLIC_ROUTES = ['/login'];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (PUBLIC_ROUTES.includes(pathname)) return <>{children}</>;
  return <DashboardLayout>{children}</DashboardLayout>;
}
