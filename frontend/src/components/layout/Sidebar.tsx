'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Package,
  Box,
  TrendingUp,
  AlertTriangle,
  FileText,
  Settings,
  LogOut,
  Users,
  Building2,
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Produtos', href: '/products', icon: Package },
  { name: 'Estoque', href: '/inventory', icon: Box },
  { name: 'Previsões', href: '/predictions', icon: TrendingUp },
  { name: 'Alertas', href: '/alerts', icon: AlertTriangle },
  { name: 'Relatórios', href: '/reports', icon: FileText },
  { name: 'Usuários', href: '/users', icon: Users, roles: ['admin'] },
  { name: 'Configurações', href: '/settings', icon: Settings },
];

export function Sidebar({ userRole = 'pharmacist' }: { userRole?: string }) {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r bg-card transition-all duration-200 lg:translate-x-0">
      <div className="flex h-full flex-col">
        <div className="flex h-16 items-center gap-3 border-b px-4">
          <img
            src="/logo-hospital.jpg"
            alt="Hospital Beneficente Unimar"
            className="h-9 w-auto rounded"
          />
          <span className="text-lg font-bold text-primary truncate">PharmaPredict</span>
        </div>

        <div className="px-3 py-2 border-b text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Hospital Beneficente Unimar
        </div>

        <nav className="flex-1 space-y-1 p-4" aria-label="Navegação principal">
          {navigation
            .filter((item) => !item.roles || item.roles.includes(userRole))
            .map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )}
                >
                  <item.icon className="h-5 w-5" aria-hidden="true" />
                  {item.name}
                </Link>
              );
            })}
        </nav>

        <div className="border-t p-4">
          <button
            className={cn(
              'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground'
            )}
          >
            <LogOut className="h-5 w-5" aria-hidden="true" />
            Sair
          </button>
        </div>
      </div>
    </aside>
  );
}