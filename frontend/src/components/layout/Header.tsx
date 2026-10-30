'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Bell, User, Menu, LogOut, Settings } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useKPIs } from '@/hooks/useDashboard';

const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrador',
  manager: 'Gestor',
  pharmacist: 'Farmacêutico',
};

interface HeaderProps {
  user: { full_name: string; email: string; role: string };
  onMenuClick: () => void;
  onLogout: () => void;
}

export function Header({ user, onMenuClick, onLogout }: HeaderProps) {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { data: kpis } = useKPIs();
  const pending = kpis?.alerts_unacknowledged ?? 0;

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 lg:px-6">
      <button className="lg:hidden p-2" onClick={onMenuClick} aria-label="Abrir menu">
        <Menu className="h-5 w-5" />
      </button>

      <div className="flex-1" />

      <div className="flex items-center gap-2 sm:gap-4">
        <Link href="/alerts?acknowledged=false" aria-label={`${pending} alertas pendentes`}>
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-5 w-5" />
            {pending > 0 && (
              <span className="absolute -top-1 -right-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-medium text-destructive-foreground">
                {pending > 99 ? '99+' : pending}
              </span>
            )}
          </Button>
        </Link>

        <div className="relative">
          <Button
            variant="ghost"
            className="flex items-center gap-2"
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            aria-expanded={userMenuOpen}
            aria-haspopup="true"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-medium">
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <span className="hidden lg:block">{user.full_name}</span>
            <User className="h-4 w-4" />
          </Button>

          {userMenuOpen && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setUserMenuOpen(false)}
                aria-hidden="true"
              />
              <div className="absolute right-0 mt-2 w-56 rounded-md border bg-popover p-1 shadow-lg z-50">
                <div className="px-3 py-2 border-b">
                  <p className="text-sm font-medium">{user.full_name}</p>
                  <p className="text-xs text-muted-foreground">{user.email}</p>
                  <p className="text-xs text-muted-foreground">{ROLE_LABELS[user.role] ?? user.role}</p>
                </div>
                <Link
                  href="/settings"
                  onClick={() => setUserMenuOpen(false)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent rounded-md"
                >
                  <Settings className="h-4 w-4" />
                  Configurações
                </Link>
                <button
                  onClick={onLogout}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent rounded-md"
                >
                  <LogOut className="h-4 w-4" />
                  Sair
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
