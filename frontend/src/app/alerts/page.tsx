'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  useAlerts,
  useAlertCount,
  useAcknowledgeAlert,
  useBulkAcknowledgeAlerts,
  useAlertRules,
  useUpdateAlertRule,
  Alert,
  AlertRule,
  AlertListParams,
  ALERT_TYPES,
  ALERT_SEVERITIES,
  getAlertTypeConfig,
  getSeverityConfig,
  formatAlertDate,
} from '@/hooks/useAlerts';
import { useUrlParams } from '@/hooks/useUrlParams';
import { fetchAllPages } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Checkbox } from '@/components/ui/Checkbox';
import { StatCard } from '@/components/ui/StatCard';
import { Pagination } from '@/components/ui/Pagination';
import { AlertTriangle, Clock, Info, Check, Loader2, CheckCircle, XCircle, Download } from 'lucide-react';
import { cn, formatNumber, downloadCsv } from '@/lib/utils';

const RULE_TEXT: Record<AlertRule['alert_type'], { title: string; description: (days: number) => string }> = {
  shortage_risk: {
    title: 'Risco de falta',
    description: (d) => `Avisa quando o estoque previsto acaba em até ${d} dias`,
  },
  expiry_risk: {
    title: 'Risco de validade',
    description: (d) => `Avisa sobre lotes que vencem em até ${d} dias`,
  },
  overstock: {
    title: 'Excesso de estoque',
    description: () => 'Avisa quando o estoque passa de 120% do nível máximo do produto',
  },
  reorder_point: {
    title: 'Ponto de reposição',
    description: () => 'Avisa quando o estoque chega ao nível mínimo do produto',
  },
};

export default function AlertsPage() {
  const url = useUrlParams();
  const alertType = url.get('alertType');
  const severity = url.get('severity');
  const acknowledged = url.get('acknowledged');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [exporting, setExporting] = useState(false);

  const filters: Omit<AlertListParams, 'page' | 'size'> = {
    alert_type: alertType || undefined,
    severity: severity || undefined,
    acknowledged: acknowledged === 'true' ? true : acknowledged === 'false' ? false : undefined,
  };

  const { data, isLoading, isFetching } = useAlerts({ ...filters, page: url.page, size: 20 });
  const acknowledgeMutation = useAcknowledgeAlert();
  const bulkAcknowledgeMutation = useBulkAcknowledgeAlerts();

  // Contagens de todos os pendentes (não só da página atual)
  const criticalCount = useAlertCount({ acknowledged: false, severity: 'critical' });
  const warningCount = useAlertCount({ acknowledged: false, severity: 'warning' });
  const infoCount = useAlertCount({ acknowledged: false, severity: 'info' });
  const pendingCount = useAlertCount({ acknowledged: false });

  const pendingOnPage = data?.items.filter((a) => !a.acknowledged) ?? [];
  const allSelected = pendingOnPage.length > 0 && pendingOnPage.every((a) => selectedIds.includes(a.id));
  const isPending = acknowledgeMutation.isPending || bulkAcknowledgeMutation.isPending;

  const setFilter = (key: string, value: string) => {
    url.set({ [key]: value });
    setSelectedIds([]);
  };

  const handleBulkAcknowledge = async () => {
    if (!selectedIds.length) return;
    await bulkAcknowledgeMutation.mutateAsync(selectedIds);
    setSelectedIds([]);
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const rows = await fetchAllPages<Alert>('/alerts', filters);
      downloadCsv(
        `alertas-${new Date().toISOString().slice(0, 10)}.csv`,
        [
          { header: 'Data', value: (a: Alert) => formatAlertDate(a.created_at) },
          { header: 'SKU', value: (a: Alert) => a.product?.sku },
          { header: 'Produto', value: (a: Alert) => a.product?.name },
          { header: 'Tipo', value: (a: Alert) => getAlertTypeConfig(a.alert_type).label },
          { header: 'Severidade', value: (a: Alert) => getSeverityConfig(a.severity).label },
          { header: 'Mensagem', value: (a: Alert) => a.message },
          { header: 'Status', value: (a: Alert) => (a.acknowledged ? 'Reconhecido' : 'Pendente') },
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
          <h1 className="text-3xl font-bold tracking-tight">Alertas</h1>
          <p className="text-muted-foreground">Riscos de falta, validade e excesso de estoque</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting || !data?.total}>
          {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
          Exportar CSV
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard name="Críticos pendentes" value={formatNumber(criticalCount.data ?? 0)} icon={AlertTriangle} color="text-destructive bg-destructive/10" valueClassName="text-destructive" loading={criticalCount.isLoading} />
        <StatCard name="Atenção pendentes" value={formatNumber(warningCount.data ?? 0)} icon={AlertTriangle} color="text-amber-600 bg-amber-100" valueClassName="text-amber-600" loading={warningCount.isLoading} />
        <StatCard name="Informativos pendentes" value={formatNumber(infoCount.data ?? 0)} icon={Info} loading={infoCount.isLoading} />
        <StatCard name="Total pendente" value={formatNumber(pendingCount.data ?? 0)} icon={Clock} color="text-muted-foreground bg-muted" loading={pendingCount.isLoading} />
      </div>

      <Tabs defaultValue="list" className="space-y-4">
        <TabsList>
          <TabsTrigger value="list">Lista de alertas</TabsTrigger>
          <TabsTrigger value="rules">Regras</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <Select value={alertType} onValueChange={(v) => setFilter('alertType', v)}>
                  <SelectTrigger className="w-full sm:w-[200px]">
                    <SelectValue placeholder="Todos os tipos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos os tipos</SelectItem>
                    {ALERT_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={severity} onValueChange={(v) => setFilter('severity', v)}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Todas as severidades" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todas as severidades</SelectItem>
                    {ALERT_SEVERITIES.map((s) => (
                      <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={acknowledged} onValueChange={(v) => setFilter('acknowledged', v)}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Todos os status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos os status</SelectItem>
                    <SelectItem value="false">Pendentes</SelectItem>
                    <SelectItem value="true">Reconhecidos</SelectItem>
                  </SelectContent>
                </Select>
                {isFetching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                {selectedIds.length > 0 && (
                  <Button size="sm" onClick={handleBulkAcknowledge} disabled={isPending} className="bg-green-600 hover:bg-green-700 sm:ml-auto">
                    <CheckCircle className="mr-2 h-4 w-4" />
                    Reconhecer {selectedIds.length} selecionado{selectedIds.length !== 1 ? 's' : ''}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="py-12 text-center">
                  <Loader2 className="mx-auto mb-2 h-8 w-8 animate-spin text-primary" />
                  <p className="text-muted-foreground">Carregando alertas...</p>
                </div>
              ) : !data?.items.length ? (
                <div className="py-12 text-center">
                  <CheckCircle className="mx-auto mb-4 h-12 w-12 text-green-600" />
                  <h3 className="mb-1 text-lg font-medium">Nenhum alerta encontrado</h3>
                  <p className="text-muted-foreground">
                    {alertType || severity || acknowledged ? 'Tente ajustar os filtros' : 'Sistema sem alertas no momento'}
                  </p>
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-10">
                            <Checkbox
                              checked={allSelected}
                              onCheckedChange={(c) => setSelectedIds(c ? pendingOnPage.map((a) => a.id) : [])}
                              disabled={!pendingOnPage.length}
                              aria-label="Selecionar pendentes da página"
                            />
                          </TableHead>
                          <TableHead>Produto</TableHead>
                          <TableHead>Tipo</TableHead>
                          <TableHead>Severidade</TableHead>
                          <TableHead className="hidden lg:table-cell">Mensagem</TableHead>
                          <TableHead className="hidden md:table-cell">Data</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="w-32" />
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.items.map((alert) => {
                          const severityConfig = getSeverityConfig(alert.severity);
                          return (
                            <TableRow key={alert.id} className={cn('hover:bg-muted/50', alert.acknowledged && 'opacity-60')}>
                              <TableCell>
                                <Checkbox
                                  checked={selectedIds.includes(alert.id)}
                                  onCheckedChange={(c) =>
                                    setSelectedIds((prev) => (c ? [...prev, alert.id] : prev.filter((i) => i !== alert.id)))
                                  }
                                  disabled={alert.acknowledged}
                                  aria-label="Selecionar alerta"
                                />
                              </TableCell>
                              <TableCell>
                                <Link href={`/products/${alert.product_id}`} className="font-medium hover:underline">
                                  {alert.product?.name ?? 'Produto não encontrado'}
                                </Link>
                                <p className="font-mono text-xs text-muted-foreground">{alert.product?.sku}</p>
                              </TableCell>
                              <TableCell>
                                <Badge variant="secondary" className="whitespace-nowrap text-xs">{getAlertTypeConfig(alert.alert_type).label}</Badge>
                              </TableCell>
                              <TableCell>
                                <Badge variant={severityConfig.color as 'info'} className="text-xs">{severityConfig.label}</Badge>
                              </TableCell>
                              <TableCell className="hidden max-w-md text-sm lg:table-cell">{alert.message}</TableCell>
                              <TableCell className="hidden whitespace-nowrap text-sm text-muted-foreground md:table-cell">{formatAlertDate(alert.created_at)}</TableCell>
                              <TableCell>
                                {alert.acknowledged ? (
                                  <Badge variant="success" className="text-xs"><CheckCircle className="mr-1 h-3 w-3" />Reconhecido</Badge>
                                ) : (
                                  <Badge variant="destructive" className="text-xs"><XCircle className="mr-1 h-3 w-3" />Pendente</Badge>
                                )}
                              </TableCell>
                              <TableCell>
                                {!alert.acknowledged && (
                                  <Button variant="outline" size="sm" onClick={() => acknowledgeMutation.mutate(alert.id)} disabled={isPending}>
                                    <Check className="mr-1 h-3 w-3" />
                                    Reconhecer
                                  </Button>
                                )}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                  <Pagination
                    page={data.page}
                    pages={data.pages}
                    total={data.total}
                    label="alertas"
                    onPageChange={(p) => {
                      url.set({ page: p }, { resetPage: false });
                      setSelectedIds([]);
                    }}
                  />
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rules">
          <AlertRules />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function AlertRules() {
  const { data: rules, isLoading } = useAlertRules();
  const updateRule = useUpdateAlertRule();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Regras de alerta</CardTitle>
        <p className="text-sm text-muted-foreground">
          Ative ou desative cada tipo de alerta. As alterações valem até o servidor ser reiniciado.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading && <Loader2 className="mx-auto h-6 w-6 animate-spin text-primary" />}
        {rules?.map((rule) => {
          const text = RULE_TEXT[rule.alert_type];
          const severityConfig = getSeverityConfig(rule.severity);
          return (
            <div key={rule.id} className="flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-4">
                <Badge variant={severityConfig.color as 'info'} className="w-20 justify-center text-xs">{severityConfig.label}</Badge>
                <div>
                  <p className="font-medium">{text?.title ?? rule.alert_type}</p>
                  <p className="text-sm text-muted-foreground">{text?.description(rule.threshold_days)}</p>
                </div>
              </div>
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <Checkbox
                  checked={rule.enabled}
                  disabled={updateRule.isPending}
                  onCheckedChange={(c) => updateRule.mutate({ id: rule.id, data: { enabled: !!c } })}
                />
                Ativa
              </label>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
