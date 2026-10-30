'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePredictions, useModels, Prediction, PredictionListParams, formatPredictionDate } from '@/hooks/usePredictions';
import { useUrlParams } from '@/hooks/useUrlParams';
import { fetchAllPages } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatCard } from '@/components/ui/StatCard';
import { SearchInput } from '@/components/ui/SearchInput';
import { Pagination } from '@/components/ui/Pagination';
import { Brain, Package, Target, CalendarDays, Loader2, Download, ChevronRight } from 'lucide-react';
import { formatNumber, getCategoryLabel, downloadCsv } from '@/lib/utils';

const SORTS = {
  demand: { label: 'Maior demanda', sort_by: 'predicted_quantity', sort_order: 'desc' },
  demand_asc: { label: 'Menor demanda', sort_by: 'predicted_quantity', sort_order: 'asc' },
} as const;

type SortKey = keyof typeof SORTS;

function addDays(date: string, days: number) {
  const d = new Date(date + 'T00:00:00');
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function PredictionsPage() {
  const url = useUrlParams();
  const search = url.get('search');
  const sort = (url.get('sort') in SORTS ? url.get('sort') : 'demand') as SortKey;
  const [exporting, setExporting] = useState(false);

  const filters: PredictionListParams = {
    search: search || undefined,
    sort_by: SORTS[sort].sort_by,
    sort_order: SORTS[sort].sort_order,
  };

  const { data: predictions, isLoading, isFetching } = usePredictions({ ...filters, page: url.page, size: 20 });
  const { data: models } = useModels();
  const model = models?.find((m) => m.is_production) ?? models?.[0];
  const baseDate = predictions?.items[0]?.forecast_date;

  const handleExport = async () => {
    setExporting(true);
    try {
      const rows = await fetchAllPages<Prediction>('/predictions', filters);
      downloadCsv(
        `previsoes-7dias-${new Date().toISOString().slice(0, 10)}.csv`,
        [
          { header: 'SKU', value: (p: Prediction) => p.product?.sku },
          { header: 'Produto', value: (p: Prediction) => p.product?.name },
          { header: 'Categoria', value: (p: Prediction) => (p.product ? getCategoryLabel(p.product.category) : '') },
          { header: 'Data base', value: (p: Prediction) => formatPredictionDate(p.forecast_date) },
          { header: 'Previsto 7 dias', value: (p: Prediction) => p.predicted_quantity },
          { header: 'Mínimo esperado', value: (p: Prediction) => p.confidence_lower },
          { header: 'Máximo esperado', value: (p: Prediction) => p.confidence_upper },
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
          <h1 className="text-3xl font-bold tracking-tight">Previsões de demanda</h1>
          <p className="text-muted-foreground">Consumo previsto pelo modelo para os próximos 7 dias de cada produto</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting || !predictions?.total}>
          {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
          Exportar CSV
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard name="Produtos com previsão" value={formatNumber(predictions?.total ?? 0)} icon={Package} color="text-green-600 bg-green-100" loading={isLoading} />
        <StatCard
          name="Janela prevista"
          value={baseDate ? `${formatPredictionDate(addDays(baseDate, 1)).slice(0, 5)} a ${formatPredictionDate(addDays(baseDate, 7)).slice(0, 5)}` : '—'}
          hint={baseDate ? `A partir do consumo até ${formatPredictionDate(baseDate)}` : undefined}
          icon={CalendarDays}
          color="text-amber-600 bg-amber-100"
          loading={isLoading}
        />
        <StatCard name="Modelo" value={model?.model_type ?? '—'} hint={model ? `Treinado em ${formatPredictionDate(model.training_date)}` : undefined} icon={Brain} />
        <StatCard
          name="Acurácia do modelo"
          value={model ? `${((1 - model.wape) * 100).toFixed(1)}%` : '—'}
          hint={model ? `WAPE ${(model.wape * 100).toFixed(1)}% no teste` : undefined}
          icon={Target}
          color="text-indigo-600 bg-indigo-100"
        />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <SearchInput
              value={search}
              onChange={(v) => url.set({ search: v })}
              placeholder="Buscar produto por nome ou SKU..."
              className="flex-1 sm:max-w-md"
            />
            <Select value={sort} onValueChange={(v) => url.set({ sort: v === 'demand' ? null : v })}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(SORTS).map(([key, s]) => (
                  <SelectItem key={key} value={key}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {isFetching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
            <Link href="/model" className="text-sm text-primary hover:underline sm:ml-auto">
              Ver desempenho do modelo
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-12 text-center">
              <Loader2 className="mx-auto mb-2 h-8 w-8 animate-spin text-primary" />
              <p className="text-muted-foreground">Carregando previsões...</p>
            </div>
          ) : !predictions?.items.length ? (
            <div className="py-12 text-center">
              <Brain className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
              <h3 className="mb-1 text-lg font-medium">Nenhuma previsão encontrada</h3>
              <p className="text-muted-foreground">
                {search ? 'Tente outra busca' : <>Gere as previsões com <code>uv run python ml/predict.py</code> no backend</>}
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Produto</TableHead>
                      <TableHead className="hidden md:table-cell">Categoria</TableHead>
                      <TableHead className="text-right">Previsto (7 dias)</TableHead>
                      <TableHead className="hidden text-right sm:table-cell">Por dia</TableHead>
                      <TableHead className="hidden text-right lg:table-cell">Faixa esperada</TableHead>
                      <TableHead className="w-24" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {predictions.items.map((pred) => (
                      <TableRow key={pred.id} className="hover:bg-muted/50">
                        <TableCell>
                          <p className="font-medium">{pred.product?.name ?? 'Produto não encontrado'}</p>
                          <p className="font-mono text-xs text-muted-foreground">{pred.product?.sku}</p>
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          {pred.product && <Badge variant="secondary" className="text-xs">{getCategoryLabel(pred.product.category)}</Badge>}
                        </TableCell>
                        <TableCell className="text-right font-semibold tabular-nums">{formatNumber(pred.predicted_quantity)}</TableCell>
                        <TableCell className="hidden text-right tabular-nums text-muted-foreground sm:table-cell">
                          {formatNumber(Math.round(pred.predicted_quantity / 7))}
                        </TableCell>
                        <TableCell className="hidden text-right tabular-nums text-muted-foreground lg:table-cell">
                          {formatNumber(pred.confidence_lower)} – {formatNumber(pred.confidence_upper)}
                        </TableCell>
                        <TableCell>
                          <Link href={`/products/${pred.product_id}`} className="inline-flex items-center text-sm text-primary hover:underline">
                            Gráfico <ChevronRight className="h-4 w-4" />
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <Pagination
                page={predictions.page}
                pages={predictions.pages}
                total={predictions.total}
                label="produtos"
                onPageChange={(p) => url.set({ page: p }, { resetPage: false })}
              />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
