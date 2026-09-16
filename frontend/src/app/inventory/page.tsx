'use client';

import React from 'react';
import { useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useInventoryBatches, useInventorySummary, InventoryBatch, InventoryListParams, BATCH_STATUSES, getStatusConfig } from '@/hooks/useInventory';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Package, Search, Filter, ChevronLeft, ChevronRight, Loader2, AlertTriangle, Calendar, TrendingUp, Download } from 'lucide-react';
import { cn, formatCurrency, formatNumber, formatDate, formatDateTime } from '@/lib/utils';
import { debounce } from 'lodash-es';

export default function InventoryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [status, setStatus] = useState(searchParams.get('status') || '');
  const [expiryFilter, setExpiryFilter] = useState(searchParams.get('expiryFilter') || '');
  const [page, setPage] = useState(Number(searchParams.get('page')) || 1);
  const [debouncedSearch, setDebouncedSearch] = useState(search);
  const [viewMode, setViewMode] = useState<'table' | 'expiry'>('table');

  const debouncedSetSearch = React.useMemo(
    () => debounce((value: string) => {
      setDebouncedSearch(value);
      const params = new URLSearchParams(searchParams);
      if (value) params.set('search', value);
      else params.delete('search');
      params.set('page', '1');
      router.push(`/inventory?${params.toString()}`);
    }, 300),
    [router, searchParams]
  );

  const params: InventoryListParams = {
    page,
    size: 20,
    search: debouncedSearch,
    status: status || undefined,
  };

  const { data: batches, isLoading, error, refetch } = useInventoryBatches(params);
  const { data: summary, isLoading: summaryLoading } = useInventorySummary();

  const handleSearchChange = (value: string) => {
    setSearch(value);
    debouncedSetSearch(value);
  };

  const handleFilterChange = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value);
    else params.delete(key);
    params.set('page', '1');
    router.push(`/inventory?${params.toString()}`);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    const params = new URLSearchParams(searchParams);
    params.set('page', newPage.toString());
    router.push(`/inventory?${params.toString()}`);
  };

  const getDaysUntilExpiry = (expiryDate: string) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const expiry = new Date(expiryDate);
    expiry.setHours(0, 0, 0, 0);
    return Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  };

  const getExpiryStatus = (days: number) => {
    if (days < 0) return { label: 'Vencido', variant: 'destructive' as const, icon: AlertTriangle };
    if (days <= 7) return { label: `Vence em ${days}d`, variant: 'destructive' as const, icon: AlertTriangle };
    if (days <= 30) return { label: `${days}d`, variant: 'warning' as const, icon: Calendar };
    if (days <= 90) return { label: `${days}d`, variant: 'secondary' as const, icon: Calendar };
    return { label: `${days}d`, variant: 'success' as const, icon: Calendar };
  };

  if (isLoading && !batches) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-2" />
            <p className="text-muted-foreground">Carregando estoque...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Estoque</h1>
          <p className="text-muted-foreground">Controle de lotes, validades (FEFO) e movimentações</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Exportar CSV
          </Button>
        </div>
      </div>

      {!summaryLoading && summary && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total de Lotes</p>
                  <p className="text-3xl font-bold">{formatNumber(summary.total_batches)}</p>
                </div>
                <div className="p-3 rounded-full bg-primary/10 text-primary">
                  <Package className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Quantidade Total</p>
                  <p className="text-3xl font-bold">{formatNumber(summary.total_quantity)}</p>
                </div>
                <div className="p-3 rounded-full bg-green-100 text-green-600">
                  <Package className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Valor Total</p>
                  <p className="text-3xl font-bold">{formatCurrency(summary.total_value)}</p>
                </div>
                <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                  <TrendingUp className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Vencendo (30d)</p>
                  <p className="text-3xl font-bold text-amber-600">{formatNumber(summary.expiring_30d)}</p>
                </div>
                <div className="p-3 rounded-full bg-amber-100 text-amber-600">
                  <Calendar className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Vencendo (90d)</p>
                  <p className="text-3xl font-bold text-blue-600">{formatNumber(summary.expiring_90d)}</p>
                </div>
                <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                  <Calendar className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Vencidos</p>
                  <p className="text-3xl font-bold text-destructive">{formatNumber(summary.expired_count)}</p>
                </div>
                <div className="p-3 rounded-full bg-destructive/10 text-destructive">
                  <AlertTriangle className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue="table" className="space-y-4">
        <TabsList>
          <TabsTrigger value="table">Lotes (Tabela)</TabsTrigger>
          <TabsTrigger value="expiry">Timeline Validades</TabsTrigger>
        </TabsList>

        <TabsContent value="table">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1 max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Buscar por lote, produto, SKU..."
                    value={search}
                    onChange={(e) => handleSearchChange(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <Select value={status} onValueChange={(v) => handleFilterChange('status', v)}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Todos os status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos os status</SelectItem>
                    {BATCH_STATUSES.map((s) => (
                      <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={expiryFilter} onValueChange={(v) => handleFilterChange('expiryFilter', v)}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Validade" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todas</SelectItem>
                    <SelectItem value="expired">Vencidos</SelectItem>
                    <SelectItem value="7">Próximos 7 dias</SelectItem>
                    <SelectItem value="30">Próximos 30 dias</SelectItem>
                    <SelectItem value="90">Próximos 90 dias</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {batches?.items.length === 0 ? (
                <div className="text-center py-12">
                  <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-1">Nenhum lote encontrado</h3>
                  <p className="text-muted-foreground mb-4">
                    {search || status ? 'Tente ajustar os filtros' : 'Nenhum lote cadastrado'}
                  </p>
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Produto</TableHead>
                          <TableHead>Lote</TableHead>
                          <TableHead className="text-right">Quantidade</TableHead>
                          <TableHead>Validade</TableHead>
                          <TableHead>Fabricação</TableHead>
                          <TableHead className="text-right">Custo Unit.</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Recebido</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {batches?.items.map((batch) => {
                          const daysUntil = getDaysUntilExpiry(batch.expiry_date);
                          const expiryStatus = getExpiryStatus(daysUntil);
                          const statusConfig = getStatusConfig(batch.status);
                          return (
                            <TableRow key={batch.id} className="hover:bg-muted/50">
                              <TableCell>
                                <div>
                                  <p className="font-medium">{batch.product?.name || 'Produto não encontrado'}</p>
                                  <p className="text-xs text-muted-foreground font-mono">{batch.product?.sku}</p>
                                </div>
                              </TableCell>
                              <TableCell className="font-mono">{batch.batch_number}</TableCell>
                              <TableCell className="text-right font-medium">{formatNumber(batch.quantity)}</TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  <expiryStatus.icon className={cn('h-4 w-4', expiryStatus.variant === 'destructive' && 'text-destructive', expiryStatus.variant === 'warning' && 'text-amber-600', expiryStatus.variant === 'success' && 'text-green-600')} />
                                  <span className={cn('font-medium', daysUntil < 0 && 'text-destructive', daysUntil <= 7 && 'text-amber-600')}>
                                    {formatDate(batch.expiry_date)}
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell>{batch.manufacture_date ? formatDate(batch.manufacture_date) : '—'}</TableCell>
                              <TableCell className="text-right font-mono">{formatCurrency(batch.unit_cost)}</TableCell>
                              <TableCell>
                                <Badge variant={statusConfig.color as any} className="text-xs">
                                  {statusConfig.label}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-muted-foreground text-sm">
                                {formatDateTime(batch.received_at)}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>

                  {batches && batches.pages > 1 && (
                    <div className="flex items-center justify-between mt-4">
                      <p className="text-sm text-muted-foreground">
                        Página {batches.page} de {batches.pages} — {batches.total} lotes
                      </p>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handlePageChange(page - 1)}
                          disabled={page <= 1}
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handlePageChange(page + 1)}
                          disabled={page >= batches.pages}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="expiry">
          <Card>
            <CardHeader>
              <CardTitle>Timeline de Validades (FEFO - First Expired, First Out)</CardTitle>
            </CardHeader>
            <CardContent>
              {batches?.items.length === 0 ? (
                <div className="text-center py-12">
                  <Calendar className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">Nenhum lote para exibir</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {batches?.items
                    .filter(b => b.status === 'available')
                    .sort((a, b) => new Date(a.expiry_date).getTime() - new Date(b.expiry_date).getTime())
                    .map((batch) => {
                      const daysUntil = getDaysUntilExpiry(batch.expiry_date);
                      const expiryStatus = getExpiryStatus(daysUntil);
                      const progress = Math.min(100, Math.max(0, (90 - daysUntil) / 90 * 100));
                      return (
                        <div
                          key={batch.id}
                          className={cn(
                            'p-4 rounded-lg border transition-colors',
                            daysUntil < 0 && 'bg-destructive/5 border-destructive/20',
                            daysUntil <= 7 && 'bg-amber-50 border-amber-200',
                            daysUntil <= 30 && 'bg-blue-50 border-blue-200'
                          )}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4 flex-1 min-w-0">
                              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                                <Package className="h-6 w-6 text-primary" />
                              </div>
                              <div className="min-w-0">
                                <p className="font-medium truncate">{batch.product?.name}</p>
                                <p className="text-sm text-muted-foreground">
                                  SKU: {batch.product?.sku} • Lote: {batch.batch_number}
                                </p>
                              </div>
                              <div className="flex items-center gap-3 flex-wrap">
                                <Badge variant={expiryStatus.variant as any} className="text-xs">
                                  {expiryStatus.label}
                                </Badge>
                                <Badge variant="secondary" className="text-xs">
                                  {formatNumber(batch.quantity)} un
                                </Badge>
                              </div>
                            </div>
                            <div className="flex items-center gap-4 ml-4 flex-shrink-0">
                              <div className="w-48">
                                <div className="h-2 bg-muted rounded-full overflow-hidden">
                                  <div
                                    className={cn(
                                      'h-full rounded-full transition-all',
                                      daysUntil < 0 && 'bg-destructive',
                                      daysUntil <= 7 && 'bg-amber-500',
                                      daysUntil <= 30 && 'bg-blue-500',
                                      'bg-green-500'
                                    )}
                                    style={{ width: `${progress}%` }}
                                  />
                                </div>
                                <p className="text-xs text-muted-foreground mt-1 text-right">
                                  {daysUntil < 0 ? 'Vencido' : `${daysUntil} dias restantes`}
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}