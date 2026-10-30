'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, apiErrorMessage } from '@/lib/api';
import type { User } from '@/lib/auth';
import { useCurrentUser } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Checkbox } from '@/components/ui/Checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { SearchInput } from '@/components/ui/SearchInput';
import { StatCard } from '@/components/ui/StatCard';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Loader2, Lock, Plus, ShieldCheck, UserCheck, Users } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';

const ROLES = [
  { value: 'pharmacist', label: 'Farmacêutico' },
  { value: 'manager', label: 'Gestor' },
  { value: 'admin', label: 'Administrador' },
] as const;

type Role = (typeof ROLES)[number]['value'];

function roleLabel(role: string) {
  return ROLES.find((r) => r.value === role)?.label ?? role;
}

function useUsers(enabled: boolean) {
  return useQuery<User[]>({
    queryKey: ['users'],
    queryFn: async () => (await api.get<User[]>('/users', { params: { limit: 500 } })).data,
    enabled,
  });
}

export default function UsersPage() {
  const currentUser = useCurrentUser();
  const isAdmin = currentUser?.role === 'admin';
  const queryClient = useQueryClient();
  const { data: users, isLoading } = useUsers(isAdmin);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateUser = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Pick<User, 'role' | 'is_active'>> }) =>
      api.patch<User>(`/users/${id}`, data),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (err) => setError(apiErrorMessage(err)),
  });

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    const list = [...(users ?? [])].sort((a, b) => a.full_name.localeCompare(b.full_name, 'pt-BR'));
    if (!term) return list;
    return list.filter((u) => u.full_name.toLowerCase().includes(term) || u.email.toLowerCase().includes(term));
  }, [users, search]);

  if (!isAdmin) {
    return (
      <div className="p-4 lg:p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <Lock className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
            <h2 className="mb-1 text-lg font-medium">Acesso restrito</h2>
            <p className="text-muted-foreground">Apenas administradores gerenciam usuários.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const activeCount = users?.filter((u) => u.is_active).length ?? 0;
  const adminCount = users?.filter((u) => u.role === 'admin').length ?? 0;

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Usuários</h1>
          <p className="text-muted-foreground">Quem acessa o sistema e com qual perfil</p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)}>
          <Plus className="mr-2 h-4 w-4" />
          Novo usuário
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard name="Usuários" value={users?.length ?? 0} icon={Users} loading={isLoading} />
        <StatCard name="Ativos" value={activeCount} icon={UserCheck} color="text-green-600 bg-green-100" loading={isLoading} />
        <StatCard name="Administradores" value={adminCount} icon={ShieldCheck} color="text-indigo-600 bg-indigo-100" loading={isLoading} />
      </div>

      {showForm && <NewUserForm onDone={() => setShowForm(false)} />}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader className="pb-2">
          <SearchInput value={search} onChange={setSearch} placeholder="Buscar por nome ou e-mail..." className="sm:max-w-md" delay={0} />
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-12 text-center">
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nome</TableHead>
                    <TableHead>Perfil</TableHead>
                    <TableHead className="hidden md:table-cell">Último acesso</TableHead>
                    <TableHead>Ativo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((user) => {
                    const isSelf = user.id === currentUser?.id;
                    return (
                      <TableRow key={user.id} className={user.is_active ? 'hover:bg-muted/50' : 'opacity-60'}>
                        <TableCell>
                          <p className="font-medium">
                            {user.full_name} {isSelf && <Badge variant="secondary" className="ml-1 text-xs">você</Badge>}
                          </p>
                          <p className="text-xs text-muted-foreground">{user.email}</p>
                        </TableCell>
                        <TableCell>
                          <Select
                            value={user.role}
                            disabled={isSelf || updateUser.isPending}
                            onValueChange={(role) => updateUser.mutate({ id: user.id, data: { role: role as Role } })}
                          >
                            <SelectTrigger className="h-9 w-[160px]">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {ROLES.map((r) => (
                                <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell className="hidden text-sm text-muted-foreground md:table-cell">
                          {user.last_login ? formatDateTime(user.last_login) : 'Nunca'}
                        </TableCell>
                        <TableCell>
                          <Checkbox
                            checked={user.is_active}
                            disabled={isSelf || updateUser.isPending}
                            onCheckedChange={(c) => updateUser.mutate({ id: user.id, data: { is_active: !!c } })}
                            aria-label={user.is_active ? 'Desativar usuário' : 'Ativar usuário'}
                          />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {!filtered.length && (
                    <TableRow>
                      <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                        Nenhum usuário encontrado
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function NewUserForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ full_name: '', email: '', role: 'pharmacist' as Role, password: '' });
  const [error, setError] = useState<string | null>(null);

  const createUser = useMutation({
    mutationFn: () => api.post<User>('/register', form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      onDone();
    },
    onError: (err) => setError(apiErrorMessage(err)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Novo usuário</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            createUser.mutate();
          }}
        >
          <Input label="Nome completo" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
          <Input label="E-mail" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          <div>
            <span className="mb-1.5 block text-sm font-medium">Perfil</span>
            <Select value={form.role} onValueChange={(role) => setForm({ ...form, role: role as Role })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLES.map((r) => (
                  <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Input
            label="Senha inicial"
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            helperText="Mínimo 8 caracteres, com maiúscula, minúscula e número"
            required
          />
          {error && (
            <Alert variant="destructive" className="sm:col-span-2">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <div className="flex justify-end gap-2 sm:col-span-2">
            <Button type="button" variant="outline" onClick={onDone}>
              Cancelar
            </Button>
            <Button type="submit" disabled={createUser.isPending}>
              {createUser.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Cadastrar
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
