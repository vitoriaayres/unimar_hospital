'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useProduct } from '@/hooks/useProducts';
import { getMovementTypeConfig, getStatusConfig } from '@/hooks/useInventory';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { ForecastChart, BarChart } from '@/components/charts/ForecastChart';
import { Package, Tag, Truck, AlertTriangle, CheckCircle, ChevronLeft, Loader2, Barcode } from 'lucide-react';
import { cn, formatCurrency, formatNumber, formatDate, formatDateTime, getCategoryLabel } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Tipos dos endpoints consumidos (espelham os schemas do backend)
// ---------------------------------------------------------------------------

interface ForecastResponse {
  model_version: string;
  predictions: { forecast_date: string; predicted_quantity: number; confidence_lower: number; confidence_upper: number }[];
  summary: { avg_daily?: number; total_predicted?: number; wape?: number | null };
}

interface InventoryBatchRow {
  id: string;
  batch_number: string;
  quantity: number;
  expiry_date: string;
  manufacture_date: string | null;
  unit_cost: number | string;
  status: string;
  received_at: string;
  days_until_expiry: number | null;
}

interface InventorySummaryRow {
  product_id: string;
  available_quantity: number;
  total_value: number | string;
  batches_count: number;
  batches_expiring_30d: number;
}

interface StockMovementRow {
  id: string;
  quantity_change: number;
  movement_type: string;
  reference_type: string | null;
  notes: string | null;
  created_at: string;
}

interface ConsumptionTrendPoint {
  date: string;
  total_quantity: number;
  by_department: Record<string, number>;
}

const DEPARTMENT_LABELS: Record<string, string> = {
  icu: 'UTI',
  er: 'Emergência',
  ward: 'Enfermaria',
  outpatient: 'Ambulatório',
};

const REFERENCE_LABELS: Record<string, string> = {
  purchase_order: 'Pedido de compra',
  consumption: 'Consumo',
  dispensation: 'Dispensação',
  adjustment: 'Ajuste',
};

const METADATA_LABELS: Record<string, string> = {
  form: 'Forma farmacêutica',
  strength: 'Concentração',
  atc_class: 'Classe ATC',
  class_name: 'Classe terapêutica',
  base_demand_per_day: 'Demanda base (un/dia)',
};

function InfoRow({ icon: Icon, label, value, iconClass }: { icon: typeof Package; label: string; value: React.ReactNode; iconClass?: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg bg-muted/50 p-3">
      <div className="flex items-center gap-3">
        <Icon className={cn('h-5 w-5 text-muted-foreground', iconClass)} />
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <div className="font-medium">{children}</div>
    </div>
  );
}

export default function ProductDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const { data: product, isLoading, error } = useProduct(id);

  const { data: forecast, isLoading: forecastLoading } = useQuery<ForecastResponse>({
    queryKey: ['forecast', id],
    queryFn: async () => (await api.post<ForecastResponse>('/predictions/forecast', { product_id: id, horizon_days: 30 })).data,
    enabled: !!product,
    retry: false, // 404/503 = sem previsão para o produto; não adianta repetir
    staleTime: 5 * 60 * 1000,
  });

  const { data: summary } = useQuery<InventorySummaryRow | null>({
    queryKey: ['inventory', 'summary', id],
    queryFn: async () => {
      const response = await api.get<InventorySummaryRow[]>('/inventory/summary');
      return response.data.find((r) => r.product_id === id) ?? null;
    },
    enabled: !!product,
    staleTime: 30_000,
  });

  const { data: batches } = useQuery<{ items: InventoryBatchRow[]; total: number }>({
    queryKey: ['inventory', 'batches', { product_id: id, in_stock: true }],
    queryFn: async () =>
      (await api.get('/inventory/batches', { params: { product_id: id, in_stock: true, size: 100 } })).data as {
        items: InventoryBatchRow[];
        total: number;
      },
    enabled: !!product,
  });

  const { data: movements } = useQuery<StockMovementRow[]>({
    queryKey: ['inventory', 'movements', { product_id: id }],
    queryFn: async () => (await api.get<StockMovementRow[]>('/inventory/movements', { params: { product_id: id, limit: 50 } })).data,
    enabled: !!product,
  });

  const { data: trends } = useQuery<ConsumptionTrendPoint[]>({
    queryKey: ['dashboard', 'consumption-trends', { product_id: id, days_back: 30 }],
    queryFn: async () =>
      (await api.get<ConsumptionTrendPoint[]>('/dashboard/consumption-trends', { params: { product_id: id, days_back: 30 } })).data,
    enabled: !!product,
  });

  if (isLoading) {
    return (
      <div className="p-4 lg:p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="mx-auto mb-2 h-8 w-8 animate-spin text-primary" />
            <p className="text-muted-foreground">Carregando produto...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="p-4 lg:p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-destructive">Produto não encontrado</p>
            <Link href="/products">
              <Button variant="outline" className="mt-2">
                <ChevronLeft className="mr-2 h-4 w-4" />
                Voltar à lista
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Histórico real seguido da previsão, no mesmo gráfico
  const chartData = [
    ...(trends ?? []).map((t) => ({ date: t.date, actual: t.total_quantity })),
    ...(forecast?.predictions ?? []).map((p) => ({
      date: p.forecast_date,
      predicted: p.predicted_quantity,
      lower: p.confidence_lower,
      upper: p.confidence_upper,
    })),
  ];

  const deptTotals = new Map<string, number>();
  for (const point of trends ?? []) {
    for (const [dept, qty] of Object.entries(point.by_department)) {
      deptTotals.set(dept, (deptTotals.get(dept) ?? 0) + qty);
    }
  }
  const consumptionByDept = Array.from(deptTotals.entries())
    .map(([k, v]) => ({ name: DEPARTMENT_LABELS[k] ?? k, value: v }))
    .sort((a, b) => b.value - a.value);
  const consumed30d = (trends ?? []).reduce((s, t) => s + t.total_quantity, 0);

  const available = summary?.available_quantity ?? 0;
  const dailyForecast = forecast?.summary.avg_daily ?? 0;
  const daysOfCover = dailyForecast > 0 ? Math.floor(available / dailyForecast) : null;
  const metadata = Object.entries(product.product_metadata ?? {});

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <Link href="/products" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ChevronLeft className="h-4 w-4" />
        Produtos
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{product.sku}</Badge>
            <Badge variant="secondary">{getCategoryLabel(product.category)}</Badge>
            {product.controlled_substance && <Badge variant="destructive">Controlado</Badge>}
            {!product.is_active && <Badge variant="outline">Inativo</Badge>}
          </div>
          <h1 className="text-3xl font-bold tracking-tight">{product.name}</h1>
          {product.generic_name && <p className="text-muted-foreground">Princípio ativo: {product.generic_name}</p>}
        </div>
        <Link href={`/products/${product.id}/edit`}>
          <Button variant="outline">Editar</Button>
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Consumo e previsão</CardTitle>
            <Badge variant="secondary" className="text-xs">30 dias reais + 30 previstos</Badge>
          </CardHeader>
          <CardContent>
            {forecastLoading ? (
              <div className="flex h-[350px] items-center justify-center text-muted-foreground">
                <Loader2 className="mr-2 h-6 w-6 animate-spin" />
                Carregando previsão...
              </div>
            ) : (
              <>
                <ForecastChart data={chartData} height={350} />
                {!forecast && (
                  <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
                    <AlertTriangle className="h-4 w-4" />
                    Sem previsão para este produto. Rode <code>uv run python ml/predict.py</code> no backend.
                  </p>
                )}
              </>
            )}
            {forecast && (
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-muted-foreground">Previsão diária</p>
                  <p className="font-semibold">{formatNumber(Math.round(dailyForecast))} un/dia</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-muted-foreground">Previsto em 30 dias</p>
                  <p className="font-semibold">{formatNumber(Math.round(forecast.summary.total_predicted ?? 0))} un</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-muted-foreground">Consumido nos últimos 30 dias</p>
                  <p className="font-semibold">{formatNumber(consumed30d)} un</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Estoque</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-lg bg-muted/50 p-4">
              <p className="text-sm text-muted-foreground">Disponível</p>
              <p className="text-3xl font-bold tabular-nums">{formatNumber(available)} un</p>
              {daysOfCover !== null && (
                <p className={cn('text-sm font-medium', daysOfCover <= 3 ? 'text-destructive' : daysOfCover <= 7 ? 'text-amber-600' : 'text-green-700')}>
                  {daysOfCover === 0 ? 'Não cobre o consumo de hoje' : `Cobre cerca de ${daysOfCover} dia${daysOfCover !== 1 ? 's' : ''}`}
                </p>
              )}
            </div>
            <InfoRow icon={AlertTriangle} iconClass="text-amber-600" label="Nível mínimo" value={`${formatNumber(product.min_stock_level)} un`} />
            <InfoRow icon={CheckCircle} iconClass="text-green-600" label="Nível máximo" value={`${formatNumber(product.max_stock_level)} un`} />
            <InfoRow icon={Truck} label="Prazo de reposição" value={`${product.lead_time_days} dias`} />
            <InfoRow icon={Tag} label="Custo unitário" value={formatCurrency(product.unit_cost)} />
            {summary && <InfoRow icon={Package} label="Valor em estoque" value={formatCurrency(summary.total_value)} />}
            {summary && (
              <InfoRow icon={AlertTriangle} iconClass="text-destructive" label="Lotes vencendo (30d)" value={summary.batches_expiring_30d} />
            )}
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="batches" className="space-y-4">
        <TabsList>
          <TabsTrigger value="batches">Lotes ({batches?.total ?? 0})</TabsTrigger>
          <TabsTrigger value="consumption">Consumo por setor</TabsTrigger>
          <TabsTrigger value="movements">Movimentações</TabsTrigger>
          <TabsTrigger value="details">Cadastro</TabsTrigger>
        </TabsList>

        <TabsContent value="batches">
          <Card>
            <CardContent className="pt-6">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Lote</TableHead>
                      <TableHead className="text-right">Quantidade</TableHead>
                      <TableHead>Validade</TableHead>
                      <TableHead className="hidden md:table-cell">Fabricação</TableHead>
                      <TableHead className="hidden text-right md:table-cell">Custo unit.</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {!batches?.items.length ? (
                      <TableRow>
                        <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                          Nenhum lote com saldo
                        </TableCell>
                      </TableRow>
                    ) : (
                      batches.items.map((batch) => {
                        const statusConfig = getStatusConfig(batch.status);
                        const days = batch.days_until_expiry;
                        return (
                          <TableRow key={batch.id} className="hover:bg-muted/50">
                            <TableCell className="font-mono text-sm">{batch.batch_number}</TableCell>
                            <TableCell className="text-right tabular-nums">{formatNumber(batch.quantity)}</TableCell>
                            <TableCell>
                              <span className={cn(days !== null && days <= 30 && 'font-medium text-amber-600', days !== null && days < 0 && 'text-destructive')}>
                                {formatDate(batch.expiry_date)}
                              </span>
                              {days !== null && <p className="text-xs text-muted-foreground">{days < 0 ? `há ${-days} dias` : `em ${days} dias`}</p>}
                            </TableCell>
                            <TableCell className="hidden md:table-cell">{batch.manufacture_date ? formatDate(batch.manufacture_date) : '—'}</TableCell>
                            <TableCell className="hidden text-right font-mono md:table-cell">{formatCurrency(batch.unit_cost)}</TableCell>
                            <TableCell>
                              <Badge variant={statusConfig.color as 'success'} className="text-xs">{statusConfig.label}</Badge>
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="consumption">
          <Card>
            <CardHeader>
              <CardTitle>Consumo por setor (últimos 30 dias)</CardTitle>
            </CardHeader>
            <CardContent>
              <BarChart data={consumptionByDept} height={260} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="movements">
          <Card>
            <CardContent className="pt-6">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Data</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead className="text-right">Quantidade</TableHead>
                      <TableHead className="hidden md:table-cell">Origem</TableHead>
                      <TableHead className="hidden lg:table-cell">Observações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {!movements?.length ? (
                      <TableRow>
                        <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                          Nenhuma movimentação registrada
                        </TableCell>
                      </TableRow>
                    ) : (
                      movements.map((mv) => {
                        const positive = mv.quantity_change >= 0;
                        return (
                          <TableRow key={mv.id} className="hover:bg-muted/50">
                            <TableCell className="whitespace-nowrap text-sm text-muted-foreground">{formatDateTime(mv.created_at)}</TableCell>
                            <TableCell>
                              <Badge variant="secondary" className="text-xs">{getMovementTypeConfig(mv.movement_type).label}</Badge>
                            </TableCell>
                            <TableCell className={cn('text-right font-medium tabular-nums', positive ? 'text-green-600' : 'text-destructive')}>
                              {positive ? '+' : ''}
                              {formatNumber(mv.quantity_change)}
                            </TableCell>
                            <TableCell className="hidden text-sm text-muted-foreground md:table-cell">
                              {mv.reference_type ? REFERENCE_LABELS[mv.reference_type] ?? mv.reference_type : '—'}
                            </TableCell>
                            <TableCell className="hidden max-w-xs truncate text-sm text-muted-foreground lg:table-cell">{mv.notes ?? '—'}</TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="details">
          <Card>
            <CardContent className="grid gap-6 pt-6 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="SKU"><span className="font-mono">{product.sku}</span></Field>
              <Field label="Código de barras">
                <span className="inline-flex items-center gap-2 font-mono">
                  <Barcode className="h-4 w-4 text-muted-foreground" />
                  {product.barcode || '—'}
                </span>
              </Field>
              <Field label="Código ATC"><span className="font-mono">{product.atc_code || '—'}</span></Field>
              <Field label="Unidade">{product.unit}</Field>
              <Field label="Controlado">{product.controlled_substance ? 'Sim' : 'Não'}</Field>
              <Field label="Status">{product.is_active ? 'Ativo' : 'Inativo'}</Field>
              {metadata.map(([key, value]) => (
                <Field key={key} label={METADATA_LABELS[key] ?? key}>{String(value)}</Field>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
