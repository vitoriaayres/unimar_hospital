'use client';

import Link from 'next/link';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { StatCard } from '@/components/ui/StatCard';
import {
  Package,
  AlertTriangle,
  TrendingUp,
  Clock,
  DollarSign,
  Target,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Check,
} from 'lucide-react';
import { formatCurrency, formatCurrencyCompact, formatNumber } from '@/lib/utils';
import { useDashboard, StockoutRiskItem, ExpiryTimelineItem } from '@/hooks/useDashboard';
import { useAlerts, useAcknowledgeAlert, getSeverityConfig } from '@/hooks/useAlerts';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const BRAND_BLUE = '#193D6F';

const RISK_CONFIG: Record<string, { label: string; variant: 'destructive' | 'warning' | 'success' | 'secondary' }> = {
  critical: { label: 'Crítico', variant: 'destructive' },
  high: { label: 'Alto', variant: 'destructive' },
  medium: { label: 'Médio', variant: 'warning' },
  low: { label: 'Baixo', variant: 'success' },
};

function RiskIcon({ risk }: { risk: string }) {
  if (risk === 'critical' || risk === 'high') return <AlertCircle className="h-4 w-4 shrink-0 text-destructive" />;
  if (risk === 'medium') return <TrendingUp className="h-4 w-4 shrink-0 text-amber-600" />;
  return <CheckCircle className="h-4 w-4 shrink-0 text-green-600" />;
}

function EmptyState({ children }: { children: React.ReactNode }) {
  return <p className="py-10 text-center text-sm text-muted-foreground">{children}</p>;
}

function StockoutRiskList({ data }: { data: StockoutRiskItem[] }) {
  if (!data.length) return <EmptyState>Nenhum risco de falta identificado</EmptyState>;

  return (
    <div className="space-y-2">
      {data.slice(0, 5).map((item) => {
        const risk = RISK_CONFIG[item.risk_level] ?? { label: item.risk_level, variant: 'secondary' as const };
        return (
          <Link
            key={item.product_id}
            href={`/products/${item.product_id}`}
            className="flex items-center justify-between gap-3 rounded-lg bg-muted/50 p-3 transition-colors hover:bg-muted"
          >
            <div className="flex min-w-0 items-center gap-3">
              <RiskIcon risk={item.risk_level} />
              <div className="min-w-0">
                <p className="truncate font-medium">{item.product_name}</p>
                <p className="text-xs text-muted-foreground">
                  Estoque {formatNumber(item.current_stock)} · Previsão 7d {formatNumber(item.predicted_consumption_7d)}
                </p>
              </div>
            </div>
            <div className="shrink-0 text-right">
              <Badge variant={risk.variant}>{risk.label}</Badge>
              {item.days_until_stockout !== null && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.days_until_stockout === 0 ? 'Falta hoje' : `Falta em ${item.days_until_stockout}d`}
                </p>
              )}
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function ExpiryList({ data }: { data: ExpiryTimelineItem[] }) {
  if (!data.length) return <EmptyState>Nenhum lote com saldo vence nos próximos 90 dias</EmptyState>;

  return (
    <div className="max-h-96 space-y-2 overflow-y-auto">
      {data.slice(0, 10).map((item) => (
        <div key={item.batch_id} className="flex items-center justify-between gap-3 rounded-lg bg-muted/50 p-3">
          <div className="flex min-w-0 items-center gap-3">
            <Badge variant={item.days_until_expiry <= 7 ? 'destructive' : item.days_until_expiry <= 30 ? 'warning' : 'secondary'}>
              {item.days_until_expiry}d
            </Badge>
            <div className="min-w-0">
              <p className="truncate font-medium">{item.product_name}</p>
              <p className="text-xs text-muted-foreground">
                Lote {item.batch_number} · {formatNumber(item.quantity)} un
              </p>
            </div>
          </div>
          <span className="shrink-0 text-xs text-muted-foreground">
            {format(new Date(item.expiry_date + 'T00:00:00'), 'dd/MM/yyyy', { locale: ptBR })}
          </span>
        </div>
      ))}
    </div>
  );
}

function PendingAlerts() {
  const { data, isLoading } = useAlerts({ acknowledged: false, severity: 'critical', size: 5 });
  const acknowledge = useAcknowledgeAlert();

  if (isLoading) return <EmptyState>Carregando...</EmptyState>;
  if (!data?.items.length) return <EmptyState>Nenhum alerta crítico pendente</EmptyState>;

  return (
    <div className="space-y-2">
      {data.items.map((alert) => (
        <div key={alert.id} className="flex items-center justify-between gap-3 rounded-lg border p-3">
          <div className="flex min-w-0 items-center gap-3">
            <AlertCircle className="h-4 w-4 shrink-0 text-destructive" />
            <div className="min-w-0">
              <p className="truncate font-medium">{alert.product?.name ?? 'Produto'}</p>
              <p className="truncate text-xs text-muted-foreground">{alert.message}</p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="shrink-0"
            disabled={acknowledge.isPending}
            onClick={() => acknowledge.mutate(alert.id)}
            title={getSeverityConfig(alert.severity).label}
          >
            <Check className="mr-1 h-3 w-3" />
            Reconhecer
          </Button>
        </div>
      ))}
    </div>
  );
}

export function DashboardContent() {
  const { data: dashboard, isLoading, error, refetch, isFetching } = useDashboard();

  if (error) {
    return (
      <div className="flex h-96 flex-col items-center justify-center p-6 text-center">
        <AlertCircle className="mb-4 h-12 w-12 text-destructive" />
        <h2 className="mb-2 text-xl font-semibold">Erro ao carregar o dashboard</h2>
        <p className="mb-4 text-muted-foreground">{(error as Error).message}</p>
        <Button onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Tentar novamente
        </Button>
      </div>
    );
  }

  const kpis = dashboard?.kpis;
  const trend = (dashboard?.consumption_trends ?? []).map((c) => ({ date: c.date, total: c.total_quantity }));

  const cards = [
    { name: 'Produtos ativos', value: formatNumber(kpis?.total_skus ?? 0), icon: Package, color: 'text-primary bg-primary/10' },
    { name: 'Abaixo do mínimo', value: formatNumber(kpis?.low_stock_count ?? 0), icon: AlertTriangle, color: 'text-amber-600 bg-amber-100' },
    { name: 'Risco de falta (7d)', value: formatNumber(kpis?.stockout_risk_count ?? 0), icon: TrendingUp, color: 'text-destructive bg-destructive/10' },
    { name: 'Lotes vencendo (30d)', value: formatNumber(kpis?.expiring_soon_count ?? 0), icon: Clock, color: 'text-purple-600 bg-purple-100' },
    { name: 'Valor em estoque', value: formatCurrencyCompact(kpis?.total_inventory_value ?? 0), hint: formatCurrency(kpis?.total_inventory_value ?? 0), icon: DollarSign, color: 'text-green-600 bg-green-100' },
    {
      name: 'Acurácia do modelo',
      value: kpis?.average_wape ? `${((1 - kpis.average_wape) * 100).toFixed(1)}%` : '—',
      hint: kpis?.average_wape ? `WAPE ${(kpis.average_wape * 100).toFixed(1)}%` : 'Sem previsões',
      icon: Target,
      color: 'text-indigo-600 bg-indigo-100',
    },
  ];

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Visão geral da farmácia hospitalar</p>
        </div>
        <div className="flex items-center gap-3">
          {dashboard?.generated_at && (
            <span className="hidden text-xs text-muted-foreground sm:block">
              Atualizado às {format(new Date(dashboard.generated_at), 'HH:mm', { locale: ptBR })}
            </span>
          )}
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={isFetching ? 'mr-2 h-4 w-4 animate-spin' : 'mr-2 h-4 w-4'} />
            Atualizar
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        {cards.map((card) => (
          <StatCard key={card.name} {...card} loading={isLoading} />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Consumo diário do hospital</CardTitle>
            <Badge variant="secondary">Últimos 30 dias</Badge>
          </CardHeader>
          <CardContent>
            {trend.length ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trend} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v) => format(new Date(v + 'T00:00:00'), 'dd/MM')}
                    interval="preserveStartEnd"
                  />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => formatNumber(v)} width={64} />
                  <Tooltip
                    formatter={(v: number) => [formatNumber(v), 'Unidades']}
                    labelFormatter={(v) => format(new Date(v + 'T00:00:00'), "EEE, dd 'de' MMM", { locale: ptBR })}
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8 }}
                  />
                  <Line type="monotone" dataKey="total" stroke={BRAND_BLUE} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState>{isLoading ? 'Carregando...' : 'Sem consumo registrado'}</EmptyState>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Maior risco de falta</CardTitle>
            <Link href="/inventory" className="text-sm text-primary hover:underline">
              Ver estoque
            </Link>
          </CardHeader>
          <CardContent>
            {isLoading ? <EmptyState>Carregando...</EmptyState> : <StockoutRiskList data={dashboard?.stockout_risks ?? []} />}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Próximos vencimentos (90 dias)</CardTitle>
            <Link href="/inventory?expiryFilter=90" className="text-sm text-primary hover:underline">
              Ver lotes
            </Link>
          </CardHeader>
          <CardContent>
            {isLoading ? <EmptyState>Carregando...</EmptyState> : <ExpiryList data={dashboard?.expiry_timeline ?? []} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Alertas críticos pendentes</CardTitle>
            <Link href="/alerts?acknowledged=false" className="text-sm text-primary hover:underline">
              Ver todos ({formatNumber(kpis?.alerts_unacknowledged ?? 0)})
            </Link>
          </CardHeader>
          <CardContent>
            <PendingAlerts />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
