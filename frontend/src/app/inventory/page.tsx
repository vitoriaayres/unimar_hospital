'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  useInventoryBatches,
  useInventorySummary,
  InventoryBatch,
  InventoryListParams,
  BATCH_STATUSES,
  getStatusConfig,
} from '@/hooks/useInventory';
import { useUrlParams } from '@/hooks/useUrlParams';
import { fetchAllPages } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Checkbox } from '@/components/ui/Checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { StatCard } from '@/components/ui/StatCard';
import { SearchInput } from '@/components/ui/SearchInput';
import { Pagination } from '@/components/ui/Pagination';
import { Package, Loader2, AlertTriangle, Calendar, TrendingUp, Download, Boxes } from 'lucide-react';
import { cn, formatCurrency, formatCurrencyCompact, formatNumber, formatDate, formatDateTime, downloadCsv } from '@/lib/utils';

const EXPIRY_FILTERS = [
  { value: 'expired', label: 'Vencidos' },
  { value: '7', label: 'Próximos 7 dias' },
  { value: '30', label: 'Próximos 30 dias' },
  { value: '90', label: 'Próximos 90 dias' },
];

function daysUntil(expiryDate: string) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const expiry = new Date(expiryDate + 'T00:00:00');
  return Math.round((expiry.getTime() - today.getTime()) / 86_400_000);
}

/** Cor por faixa de validade (usada no texto, no selo e na barra). */
function expiryTone(days: number) {
  if (days < 0) return { label: 'Vencido', badge: 'destructive' as const, text: 'text-destructive', bar: 'bg-destructive', row: 'bg-destructive/5 border-destructive/20' };
  if (days <= 7) return { label: `${days}d`, badge: 'destructive' as const, text: 'text-destructive', bar: 'bg-destructive', row: 'bg-destructive/5 border-destructive/20' };
  if (days <= 30) return { label: `${days}d`, badge: 'warning' as const, text: 'text-amber-600', bar: 'bg-amber-500', row: 'bg-amber-50 border-amber-200' };
  if (days <= 90) return { label: `${days}d`, badge: 'info' as const, text: 'text-blue-600', bar: 'bg-blue-500', row: '' };
  return { label: `${days}d`, badge: 'success' as const, text: 'text-green-700', bar: 'bg-green-500', row: '' };
}

export default function InventoryPage() {
  const url = useUrlParams();
  const search = url.get('search');
  const status = url.get('status');
  const expiryFilter = url.get('expiryFilter');
  const inStock = url.get('inStock') !== 'false';
  const [exporting, setExporting] = useState(false);

  const params: InventoryListParams = {
    page: url.page,
    size: 20,
    search: search || undefined,
    status: expiryFilter === 'expired' ? 'expired' : status || undefined,
    expiring_within_days: expiryFilter && expiryFilter !== 'expired' ? Number(expiryFilter) : undefined,
    in_stock: inStock || undefined,
  };

  const { data: batches, isLoading, isFetching } = useInventoryBatches(params);
  const { data: summary, isLoading: summaryLoading } = useInventorySummary();
  const hasFilters = !!(search || status || expiryFilter);

  const handleExport = async () => {
    setExporting(true);
    try {
      const rows = await fetchAllPages<InventoryBatch>('/inventory/batches', { ...params, page: undefined, size: undefined });
      downloadCsv(
        `estoque-lotes-${new Date().toISOString().slice(0, 10)}.csv`,
        [
          { header: 'SKU', value: (b: InventoryBatch) => b.product?.sku },
          { header: 'Produto', value: (b: InventoryBatch) => b.product?.name },
          { header: 'Lote', value: (b: InventoryBatch) => b.batch_number },
          { header: 'Quantidade', value: (b: InventoryBatch) => b.quantity },
          { header: 'Validade', value: (b: InventoryBatch) => formatDate(b.expiry_date) },
          { header: 'Fabricação', value: (b: InventoryBatch) => (b.manufacture_date ? formatDate(b.manufacture_date) : '') },
          { header: 'Custo unitário', value: (b: InventoryBatch) => String(b.unit_cost).replace('.', ',') },
          { header: 'Status', value: (b: InventoryBatch) => getStatusConfig(b.status).label },
        ],
        rows
      );
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Estoque</h1>
          <p className="text-muted-foreground">Lotes, validades (FEFO) e saldo por produto</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting || !batches?.total}>
          {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
          Exportar CSV
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        <StatCard name="Lotes" value={formatNumber(summary?.total_batches ?? 0)} icon={Boxes} loading={summaryLoading} />
        <StatCard name="Unidades em estoque" value={formatNumber(summary?.total_quantity ?? 0)} icon={Package} color="text-green-600 bg-green-100" loading={summaryLoading} />
        <StatCard
          name="Valor em estoque"
          value={formatCurrencyCompact(summary?.total_value ?? 0)}
          hint={formatCurrency(summary?.total_value ?? 0)}
          icon={TrendingUp}
          color="text-blue-600 bg-blue-100"
          loading={summaryLoading}
        />
        <StatCard name="Lotes vencendo (30d)" value={formatNumber(summary?.expiring_30d ?? 0)} icon={Calendar} color="text-amber-600 bg-amber-100" valueClassName="text-amber-600" loading={summaryLoading} />
        <StatCard name="Lotes vencendo (90d)" value={formatNumber(summary?.expiring_90d ?? 0)} icon={Calendar} color="text-blue-600 bg-blue-100" loading={summaryLoading} />
        <StatCard name="Abaixo do mínimo" value={formatNumber(summary?.low_stock_count ?? 0)} icon={AlertTriangle} color="text-destructive bg-destructive/10" valueClassName="text-destructive" loading={summaryLoading} />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <SearchInput
              value={search}
              onChange={(v) => url.set({ search: v })}
              placeholder="Buscar por lote, produto ou SKU..."
              className="flex-1 lg:max-w-md"
            />
            <Select value={status} onValueChange={(v) => url.set({ status: v })} disabled={expiryFilter === 'expired'}>
              <SelectTrigger className="w-full lg:w-[180px]">
                <SelectValue placeholder="Todos os status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Todos os status</SelectItem>
                {BATCH_STATUSES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={expiryFilter} onValueChange={(v) => url.set({ expiryFilter: v })}>
              <SelectTrigger className="w-full lg:w-[180px]">
                <SelectValue placeholder="Qualquer validade" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Qualquer validade</SelectItem>
                {EXPIRY_FILTERS.map((f) => (
                  <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <Checkbox checked={inStock} onCheckedChange={(c) => url.set({ inStock: c ? null : 'false' })} />
              Só com saldo
            </label>
            {isFetching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          </div>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="table" className="space-y-4">
            <TabsList>
              <TabsTrigger value="table">Lotes</TabsTrigger>
              <TabsTrigger value="expiry">Linha do tempo de validade</TabsTrigger>
            </TabsList>

            {isLoading ? (
              <div className="py-12 text-center">
                <Loader2 className="mx-auto mb-2 h-8 w-8 animate-spin text-primary" />
                <p className="text-muted-foreground">Carregando estoque...</p>
              </div>
            ) : !batches?.items.length ? (
              <div className="py-12 text-center">
                <Package className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                <h3 className="mb-1 text-lg font-medium">Nenhum lote encontrado</h3>
                <p className="text-muted-foreground">{hasFilters ? 'Tente ajustar os filtros' : 'Nenhum lote cadastrado'}</p>
              </div>
            ) : (
              <>
                <TabsContent value="table">
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Produto</TableHead>
                          <TableHead>Lote</TableHead>
                          <TableHead className="text-right">Quantidade</TableHead>
                          <TableHead>Validade</TableHead>
                          <TableHead className="hidden xl:table-cell">Fabricação</TableHead>
                          <TableHead className="text-right">Custo unit.</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="hidden xl:table-cell">Recebido</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {batches.items.map((batch) => {
                          const days = daysUntil(batch.expiry_date);
                          const tone = expiryTone(days);
                          const statusConfig = getStatusConfig(batch.status);
                          return (
                            <TableRow key={batch.id} className="hover:bg-muted/50">
                              <TableCell>
                                <Link href={`/products/${batch.product_id}`} className="font-medium hover:underline">
                                  {batch.product?.name ?? 'Produto não encontrado'}
                                </Link>
                                <p className="font-mono text-xs text-muted-foreground">{batch.product?.sku}</p>
                              </TableCell>
                              <TableCell className="font-mono text-sm">{batch.batch_number}</TableCell>
                              <TableCell className="text-right font-medium tabular-nums">{formatNumber(batch.quantity)}</TableCell>
                              <TableCell>
                                <span className={cn('font-medium', tone.text)}>{formatDate(batch.expiry_date)}</span>
                                <p className="text-xs text-muted-foreground">{days < 0 ? `há ${-days} dias` : `em ${days} dias`}</p>
                              </TableCell>
                              <TableCell className="hidden xl:table-cell">{batch.manufacture_date ? formatDate(batch.manufacture_date) : '—'}</TableCell>
                              <TableCell className="text-right font-mono">{formatCurrency(batch.unit_cost)}</TableCell>
                              <TableCell>
                                <Badge variant={statusConfig.color as 'success'} className="text-xs">{statusConfig.label}</Badge>
                              </TableCell>
                              <TableCell className="hidden text-sm text-muted-foreground xl:table-cell">{formatDateTime(batch.received_at)}</TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                </TabsContent>

                <TabsContent value="expiry">
                  <div className="space-y-2">
                    {batches.items.map((batch) => {
                      const days = daysUntil(batch.expiry_date);
                      const tone = expiryTone(days);
                      // Barra cheia = vence hoje; vazia = 90 dias ou mais
                      const progress = Math.min(100, Math.max(0, ((90 - days) / 90) * 100));
                      return (
                        <div key={batch.id} className={cn('rounded-lg border p-3', tone.row)}>
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <div className="flex min-w-0 items-center gap-3">
                              <Badge variant={tone.badge} className="w-16 justify-center text-xs">{tone.label}</Badge>
                              <div className="min-w-0">
                                <p className="truncate font-medium">{batch.product?.name}</p>
                                <p className="text-sm text-muted-foreground">
                                  Lote {batch.batch_number} · {formatNumber(batch.quantity)} un · vence {formatDate(batch.expiry_date)}
                                </p>
                              </div>
                            </div>
                            <div className="w-full shrink-0 sm:w-48">
                              <div className="h-2 overflow-hidden rounded-full bg-muted">
                                <div className={cn('h-full rounded-full', tone.bar)} style={{ width: `${progress}%` }} />
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </TabsContent>

                <Pagination
                  page={batches.page}
                  pages={batches.pages}
                  total={batches.total}
                  label="lotes"
                  onPageChange={(p) => url.set({ page: p }, { resetPage: false })}
                />
              </>
            )}
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
