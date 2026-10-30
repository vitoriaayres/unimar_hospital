'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useMutation } from '@tanstack/react-query';
import { apiEndpoints, apiErrorMessage } from '@/lib/api';
import { useCurrentUser } from '@/components/layout/DashboardLayout';
import { useModels } from '@/hooks/usePredictions';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Loader2 } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';

const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrador',
  manager: 'Gestor',
  pharmacist: 'Farmacêutico',
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="font-medium">{children}</p>
    </div>
  );
}

export default function SettingsPage() {
  const user = useCurrentUser();
  const { data: models } = useModels();
  const model = models?.find((m) => m.is_production) ?? models?.[0];

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Configurações</h1>
        <p className="text-muted-foreground">Sua conta e informações do sistema</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Perfil</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field label="Nome">{user?.full_name}</Field>
            <Field label="E-mail">{user?.email}</Field>
            <Field label="Perfil de acesso">{user ? ROLE_LABELS[user.role] ?? user.role : ''}</Field>
            <Field label="Último acesso">{user?.last_login ? formatDateTime(user.last_login) : '—'}</Field>
          </CardContent>
        </Card>

        <ChangePasswordCard />

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Sistema</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Hospital">Hospital Beneficente Unimar</Field>
            <Field label="Modelo de previsão">{model ? `${model.model_type} · WAPE ${(model.wape * 100).toFixed(1)}%` : '—'}</Field>
            <Field label="Treinado em">{model ? formatDateTime(model.training_date) : '—'}</Field>
            <Field label="Detalhes do modelo">
              <Link href="/model" className="text-primary hover:underline">Ver relatório</Link>
            </Field>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ChangePasswordCard() {
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const changePassword = useMutation({
    mutationFn: () =>
      apiEndpoints.auth.changePassword({ current_password: form.current_password, new_password: form.new_password }),
    onSuccess: () => {
      setSuccess(true);
      setForm({ current_password: '', new_password: '', confirm: '' });
    },
    onError: (err) => setError(apiErrorMessage(err)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Alterar senha</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            setSuccess(false);
            if (form.new_password !== form.confirm) {
              setError('A confirmação não confere com a nova senha');
              return;
            }
            changePassword.mutate();
          }}
        >
          <Input
            label="Senha atual"
            type="password"
            autoComplete="current-password"
            value={form.current_password}
            onChange={(e) => setForm({ ...form, current_password: e.target.value })}
            required
          />
          <Input
            label="Nova senha"
            type="password"
            autoComplete="new-password"
            value={form.new_password}
            onChange={(e) => setForm({ ...form, new_password: e.target.value })}
            helperText="Mínimo 8 caracteres, com maiúscula, minúscula e número"
            required
          />
          <Input
            label="Confirmar nova senha"
            type="password"
            autoComplete="new-password"
            value={form.confirm}
            onChange={(e) => setForm({ ...form, confirm: e.target.value })}
            required
          />
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert variant="success">
              <AlertDescription>Senha alterada com sucesso.</AlertDescription>
            </Alert>
          )}
          <div className="flex justify-end">
            <Button type="submit" disabled={changePassword.isPending}>
              {changePassword.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Salvar nova senha
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
