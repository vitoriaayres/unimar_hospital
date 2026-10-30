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
  Brain,
  X,
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Produtos', href: '/products', icon: Package },
  { name: 'Estoque', href: '/inventory', icon: Box },
  { name: 'Previsões', href: '/predictions', icon: TrendingUp },
  { name: 'Modelo', href: '/model', icon: Brain },
  { name: 'Alertas', href: '/alerts', icon: AlertTriangle },
  { name: 'Relatórios', href: '/reports', icon: FileText },
  { name: 'Usuários', href: '/users', icon: Users, roles: ['admin'] },
  { name: 'Configurações', href: '/settings', icon: Settings },
];

interface SidebarProps {
  userRole?: string;
  open: boolean;
  onClose: () => void;
  onLogout: () => void;
}

export function Sidebar({ userRole = 'pharmacist', open, onClose, onLogout }: SidebarProps) {
  const pathname = usePathname();

  return (
    <>
      {/* Fundo escuro do menu no celular */}
      {open && (
        <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={onClose} aria-hidden="true" />
      )}

      <aside
        className={cn(
          'fixed left-0 top-0 z-50 h-screen w-64 border-r bg-card transition-transform duration-200 lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-full flex-col">
          <div className="flex h-16 items-center gap-3 border-b px-4">
            <img
              src="/logo-hospital.jpg"
              alt="Hospital Beneficente Unimar"
              className="h-9 w-auto rounded"
            />
            <span className="text-lg font-bold text-primary truncate">PharmaPredict</span>
            <button className="ml-auto p-1 lg:hidden" onClick={onClose} aria-label="Fechar menu">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="px-3 py-2 border-b text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Hospital Beneficente Unimar
          </div>

          <nav className="flex-1 space-y-1 overflow-y-auto p-4" aria-label="Navegação principal">
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
              onClick={onLogout}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <LogOut className="h-5 w-5" aria-hidden="true" />
              Sair
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
