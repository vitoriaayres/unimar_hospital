'use client';

import { useState } from 'react';
import { api, fetchAllPages, apiErrorMessage } from '@/lib/api';
import type { InventorySummaryRow, InventoryBatch } from '@/hooks/useInventory';
import type { StockoutRiskItem } from '@/hooks/useDashboard';
import type { Prediction } from '@/hooks/usePredictions';
import { getAlertTypeConfig, getSeverityConfig, formatAlertDate, type Alert as AlertItem } from '@/hooks/useAlerts';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { AlertTriangle, Bell, Boxes, CalendarClock, Download, Loader2, TrendingUp, type LucideIcon } from 'lucide-react';
import { downloadCsv, formatDate, getCategoryLabel } from '@/lib/utils';

const decimal = (v: number | string) => String(v).replace('.', ',');
const today = () => new Date().toISOString().slice(0, 10);

const RISK_LABELS: Record<string, string> = { critical: 'Crítico', high: 'Alto', medium: 'Médio', low: 'Baixo' };

interface Report {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
  color: string;
  build: () => Promise<void>;
}

const REPORTS: Report[] = [
  {
    id: 'stock',
    title: 'Posição de estoque',
    description: 'Saldo, valor e situação de cada produto (abaixo do mínimo, excesso).',
    icon: Boxes,
    color: 'text-primary bg-primary/10',
    build: async () => {
      const { data } = await api.get<InventorySummaryRow[]>('/inventory/summary');
      downloadCsv(
        `posicao-estoque-${today()}.csv`,
        [
          { header: 'SKU', value: (r: InventorySummaryRow) => r.product_sku },
          { header: 'Produto', value: (r: InventorySummaryRow) => r.product_name },
          { header: 'Disponível', value: (r: InventorySummaryRow) => r.available_quantity },
          { header: 'Reservado', value: (r: InventorySummaryRow) => r.reserved_quantity },
          { header: 'Vencido', value: (r: InventorySummaryRow) => r.expired_quantity },
          { header: 'Estoque mínimo', value: (r: InventorySummaryRow) => r.min_stock_level },
          { header: 'Estoque máximo', value: (r: InventorySummaryRow) => r.max_stock_level },
          { header: 'Valor (R$)', value: (r: InventorySummaryRow) => decimal(r.total_value) },
          { header: 'Lotes', value: (r: InventorySummaryRow) => r.batches_count },
          { header: 'Lotes vencendo 30d', value: (r: InventorySummaryRow) => r.batches_expiring_30d },
          {
            header: 'Situação',
            value: (r: InventorySummaryRow) => (r.is_low_stock ? 'Abaixo do mínimo' : r.is_overstock ? 'Excesso' : 'Normal'),
          },
        ],
        data
      );
    },
  },
  {
    id: 'stockout',
    title: 'Risco de falta e sugestão de compra',
    description: 'Os 100 produtos com menor cobertura, com a quantidade sugerida para 14 dias.',
    icon: TrendingUp,
    color: 'text-destructive bg-destructive/10',
    build: async () => {
      const { data } = await api.get<StockoutRiskItem[]>('/dashboard/stockout-risk', { params: { limit: 100 } });
      downloadCsv(
        `risco-de-falta-${today()}.csv`,
        [
          { header: 'SKU', value: (r: StockoutRiskItem) => r.product_sku },
          { header: 'Produto', value: (r: StockoutRiskItem) => r.product_name },
          { header: 'Estoque atual', value: (r: StockoutRiskItem) => r.current_stock },
          { header: 'Previsão 7 dias', value: (r: StockoutRiskItem) => r.predicted_consumption_7d },
          { header: 'Dias até faltar', value: (r: StockoutRiskItem) => r.days_until_stockout ?? '' },
          { header: 'Risco', value: (r: StockoutRiskItem) => RISK_LABELS[r.risk_level] ?? r.risk_level },
          { header: 'Sugestão de compra', value: (r: StockoutRiskItem) => r.recommended_order_qty },
        ],
        data
      );
    },
  },
  {
    id: 'expiry',
    title: 'Lotes a vencer (90 dias)',
    description: 'Lotes com saldo que vencem nos próximos 90 dias, em ordem de validade (FEFO).',
    icon: CalendarClock,
    color: 'text-amber-600 bg-amber-100',
    build: async () => {
      const rows = await fetchAllPages<InventoryBatch>('/inventory/batches', { expiring_within_days: 90, in_stock: true });
      downloadCsv(
        `lotes-a-vencer-${today()}.csv`,
        [
          { header: 'SKU', value: (b: InventoryBatch) => b.product?.sku },
          { header: 'Produto', value: (b: InventoryBatch) => b.product?.name },
          { header: 'Lote', value: (b: InventoryBatch) => b.batch_number },
          { header: 'Quantidade', value: (b: InventoryBatch) => b.quantity },
          { header: 'Validade', value: (b: InventoryBatch) => formatDate(b.expiry_date) },
          { header: 'Custo unitário (R$)', value: (b: InventoryBatch) => decimal(b.unit_cost) },
        ],
        rows
      );
    },
  },
  {
    id: 'forecast',
    title: 'Previsão de demanda (7 dias)',
    description: 'Consumo previsto pelo modelo para a próxima semana, por produto.',
    icon: TrendingUp,
    color: 'text-green-600 bg-green-100',
    build: async () => {
      const rows = await fetchAllPages<Prediction>('/predictions', { sort_by: 'predicted_quantity', sort_order: 'desc' });
      downloadCsv(
        `previsao-7dias-${today()}.csv`,
        [
          { header: 'SKU', value: (p: Prediction) => p.product?.sku },
          { header: 'Produto', value: (p: Prediction) => p.product?.name },
          { header: 'Categoria', value: (p: Prediction) => (p.product ? getCategoryLabel(p.product.category) : '') },
          { header: 'Previsto 7 dias', value: (p: Prediction) => p.predicted_quantity },
          { header: 'Mínimo esperado', value: (p: Prediction) => p.confidence_lower },
          { header: 'Máximo esperado', value: (p: Prediction) => p.confidence_upper },
        ],
        rows
      );
    },
  },
  {
    id: 'alerts',
    title: 'Alertas pendentes',
    description: 'Todos os alertas ainda não reconhecidos, com tipo e severidade.',
    icon: Bell,
    color: 'text-purple-600 bg-purple-100',
    build: async () => {
      const rows = await fetchAllPages<AlertItem>('/alerts', { acknowledged: false });
      downloadCsv(
        `alertas-pendentes-${today()}.csv`,
        [
          { header: 'Data', value: (a: AlertItem) => formatAlertDate(a.created_at) },
          { header: 'SKU', value: (a: AlertItem) => a.product?.sku },
          { header: 'Produto', value: (a: AlertItem) => a.product?.name },
          { header: 'Tipo', value: (a: AlertItem) => getAlertTypeConfig(a.alert_type).label },
          { header: 'Severidade', value: (a: AlertItem) => getSeverityConfig(a.severity).label },
          { header: 'Mensagem', value: (a: AlertItem) => a.message },
        ],
        rows
      );
    },
  },
];

export default function ReportsPage() {
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (report: Report) => {
    setRunning(report.id);
    setError(null);
    try {
      await report.build();
    } catch (err) {
      setError(`${report.title}: ${apiErrorMessage(err, 'falha ao gerar o arquivo')}`);
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Relatórios</h1>
        <p className="text-muted-foreground">Planilhas em CSV com os dados atuais (abrem no Excel)</p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {REPORTS.map((report) => (
          <Card key={report.id} className="flex flex-col">
            <CardContent className="flex flex-1 flex-col gap-4 p-5">
              <div className="flex items-start gap-4">
                <div className={`shrink-0 rounded-full p-3 ${report.color}`}>
                  <report.icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold">{report.title}</p>
                  <p className="text-sm text-muted-foreground">{report.description}</p>
                </div>
              </div>
              <Button variant="outline" className="mt-auto" onClick={() => run(report)} disabled={running !== null}>
                {running === report.id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                Baixar CSV
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
