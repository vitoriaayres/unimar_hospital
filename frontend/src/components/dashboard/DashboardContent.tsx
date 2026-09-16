'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ForecastChart } from '@/components/charts/ForecastChart';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import {
  Package,
  AlertTriangle,
  TrendingUp,
  Clock,
  DollarSign,
  Target,
  ChevronRight,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  TrendingDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useDashboard, DashboardKPIs, StockoutRiskItem, ExpiryTimelineItem, ConsumptionTrendPoint } from '@/hooks/useDashboard';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const kpiConfig = [
  { key: 'total_skus', name: 'Total de SKUs', icon: Package, color: 'text-primary bg-primary/10', formatter: (v: number) => v.toLocaleString('pt-BR') },
  { key: 'low_stock_count', name: 'Estoque Baixo', icon: AlertTriangle, color: 'text-amber-600 bg-amber-100', formatter: (v: number) => v.toLocaleString('pt-BR') },
  { key: 'stockout_risk_count', name: 'Risco de Falta', icon: TrendingUp, color: 'text-destructive bg-destructive/10', formatter: (v: number) => v.toLocaleString('pt-BR') },
  { key: 'expiring_soon_count', name: 'Vencendo (30d)', icon: Clock, color: 'text-purple-600 bg-purple-100', formatter: (v: number) => v.toLocaleString('pt-BR') },
  { key: 'total_inventory_value', name: 'Valor Total Estoque', icon: DollarSign, color: 'text-green-600 bg-green-100', formatter: (v: number) => `R$ ${(v / 1e6).toFixed(1)}M` },
  { key: 'average_mape', name: 'Precisão Média (MAPE)', icon: Target, color: 'text-indigo-600 bg-indigo-100', formatter: (v: number) => `${(v * 100).toFixed(1)}%` },
];

function getRiskBadgeVariant(risk: string) {
  switch (risk) {
    case 'critical': return 'destructive';
    case 'high': return 'destructive';
    case 'medium': return 'warning';
    case 'low': return 'success';
    default: return 'secondary';
  }
}

function getRiskLabel(risk: string) {
  switch (risk) {
    case 'critical': return 'Crítico';
    case 'high': return 'Alto';
    case 'medium': return 'Médio';
    case 'low': return 'Baixo';
    default: return risk;
  }
}

function getRiskIcon(risk: string) {
  switch (risk) {
    case 'critical': return <AlertCircle className="h-4 w-4 text-destructive" />;
    case 'high': return <AlertCircle className="h-4 w-4 text-destructive" />;
    case 'medium': return <TrendingUp className="h-4 w-4 text-amber-600" />;
    case 'low': return <CheckCircle className="h-4 w-4 text-green-600" />;
    default: return <AlertCircle className="h-4 w-4 text-muted-foreground" />;
  }
}

function KPIGrid({ kpis }: { kpis: DashboardKPIs | undefined }) {
  if (!kpis) return null;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {kpiConfig.map((cfg) => {
        const value = kpis[cfg.key as keyof DashboardKPIs] as number;
        return (
          <Card key={cfg.key}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{cfg.name}</p>
                  <p className="text-3xl font-bold">{cfg.formatter(value)}</p>
                </div>
                <div className={cn('p-3 rounded-full', cfg.color)}>
                  <cfg.icon className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function StockoutRiskTable({ data }: { data: StockoutRiskItem[] | undefined }) {
  if (!data) return <div className="h-64 flex items-center justify-center text-muted-foreground">Carregando...</div>;
  if (!data.length) return <div className="h-64 flex items-center justify-center text-muted-foreground">Nenhum risco identificado</div>;

  return (
    <div className="space-y-3">
      {data.slice(0, 5).map((item) => (
        <div key={item.product_id} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
          <div className="flex items-center gap-3">
            {getRiskIcon(item.risk_level)}
            <div>
              <p className="font-medium">{item.product_name}</p>
              <p className="text-sm text-muted-foreground">{item.product_sku}</p>
            </div>
          </div>
          <div className="text-right">
            <Badge variant={getRiskBadgeVariant(item.risk_level)} className="mb-1">
              {getRiskLabel(item.risk_level)}
            </Badge>
            <p className="text-xs text-muted-foreground">
              Estoque: {item.current_stock} | Prev. 7d: {item.predicted_consumption_7d}
              {item.days_until_stockout !== null && ` | Falta em ${item.days_until_stockout}d`}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function DashboardContent() {
  const { data: dashboard, isLoading, error, refetch } = useDashboard();

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
              <p className="text-muted-foreground">Visão geral da farmácia hospitalar</p>
            </div>
            <Button disabled>
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              Atualizando...
            </Button>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {[...Array(6)].map((_, i) => (
              <Card key={i}><CardContent className="p-6 h-24 animate-pulse bg-muted"/></Card>
            ))}
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-96 text-center">
          <AlertCircle className="h-12 w-12 text-destructive mb-4" />
          <h2 className="text-xl font-semibold mb-2">Erro ao carregar dashboard</h2>
          <p className="text-muted-foreground mb-4">{(error as Error).message}</p>
          <Button onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Tentar novamente
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  const kpis = dashboard?.kpis;
  const stockoutRisks = dashboard?.stockout_risks;
  const expiryTimeline = dashboard?.expiry_timeline;
  const consumptionTrends = dashboard?.consumption_trends;

  const forecastData = consumptionTrends?.slice(-15).map((c: ConsumptionTrendPoint) => ({
    date: c.date,
    actual: c.total_quantity,
    predicted: c.total_quantity,
    lower: Math.max(0, c.total_quantity - 10),
    upper: c.total_quantity + 10,
  })) || [];

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Visão geral da farmácia hospitalar</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground hidden sm:block">
            Atualizado: {format(new Date(dashboard?.generated_at || Date.now()), 'HH:mm', { locale: ptBR })}
          </span>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Atualizar
          </Button>
          <Button>
            <ChevronRight className="mr-2 h-4 w-4" />
            Gerar Relatório
          </Button>
        </div>
      </div>

      <KPIGrid kpis={kpis} />

      <div className="grid gap-6 lg:grid-cols-2 mt-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Tendência de Consumo (30 dias)</CardTitle>
            <Badge variant="secondary">Últimos 30 dias</Badge>
          </CardHeader>
          <CardContent>
            <ForecastChart data={forecastData} height={300} showActual />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Top 5 - Risco de Falta de Estoque</CardTitle>
            <a href="/alerts" className="text-sm text-primary hover:underline">Ver todos</a>
          </CardHeader>
          <CardContent>
            <StockoutRiskTable data={stockoutRisks} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 mt-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Próximos Vencimentos (30 dias)</CardTitle>
            <a href="/inventory" className="text-sm text-primary hover:underline">Ver estoque</a>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {expiryTimeline?.slice(0, 10).map((item: ExpiryTimelineItem) => (
                <div key={item.batch_id} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                  <div className="flex items-center gap-3">
                    <Badge variant={item.days_until_expiry <= 7 ? 'destructive' : item.days_until_expiry <= 15 ? 'warning' : 'success'}>
                      {item.days_until_expiry}d
                    </Badge>
                    <div>
                      <p className="font-medium">{item.product_name}</p>
                      <p className="text-sm text-muted-foreground">Lote: {item.batch_number} | {item.quantity} un</p>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground">Vence: {format(new Date(item.expiry_date), 'dd/MM/yyyy', { locale: ptBR })}</span>
                </div>
              ))}
              {!expiryTimeline?.length && <p className="text-center text-muted-foreground py-8">Nenhum vencimento próximo</p>}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Alertas Não Reconhecidos</CardTitle>
            <a href="/alerts" className="text-sm text-primary hover:underline">Ver todos</a>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stockoutRisks?.filter((r: StockoutRiskItem) => r.risk_level === 'critical' || r.risk_level === 'high').slice(0, 5).map((alert: StockoutRiskItem) => (
                <div key={alert.product_id} className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-3">
                    {getRiskIcon(alert.risk_level)}
                    <div>
                      <p className="font-medium">{alert.product_name} <span className="text-muted-foreground">({alert.product_sku})</span></p>
                      <p className="text-sm text-muted-foreground">Estoque atual: {alert.current_stock} | Previsão 7 dias: {alert.predicted_consumption_7d}</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">Reconhecer</Button>
                </div>
              ))}
              {!stockoutRisks?.some((r: StockoutRiskItem) => r.risk_level === 'critical' || r.risk_level === 'high') && (
                <p className="text-center text-muted-foreground py-8">Nenhum alerta crítico no momento</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}