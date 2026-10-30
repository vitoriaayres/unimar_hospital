'use client';

import { ReactNode, createContext, useContext, useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { useAuth, User } from '@/lib/auth';

const CurrentUserContext = createContext<User | null>(null);

/** Usuário logado (disponível em qualquer tela dentro do layout). */
export function useCurrentUser() {
  return useContext(CurrentUserContext);
}

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [loading, user, router]);

  // Fecha o menu do celular ao trocar de tela
  useEffect(() => setMenuOpen(false), [pathname]);

  // Só mostra a tela depois de confirmar o login (evita chamadas sem token)
  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <CurrentUserContext.Provider value={user}>
      <div className="min-h-screen bg-background">
        <Sidebar
          userRole={user.role}
          open={menuOpen}
          onClose={() => setMenuOpen(false)}
          onLogout={logout}
        />
        <div className="lg:pl-64">
          <Header user={user} onMenuClick={() => setMenuOpen(true)} onLogout={logout} />
          <main>{children}</main>
        </div>
      </div>
    </CurrentUserContext.Provider>
  );
}
