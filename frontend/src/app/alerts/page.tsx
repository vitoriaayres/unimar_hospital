'use client';

import React from 'react';
import { useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAlerts, useAcknowledgeAlert, useBulkAcknowledgeAlerts, Alert, AlertListParams, ALERT_TYPES, ALERT_SEVERITIES, getAlertTypeConfig, getSeverityConfig, formatAlertDate } from '@/hooks/useAlerts';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Checkbox } from '@/components/ui/Checkbox';
import { AlertTriangle, Clock, Package, Check, ChevronLeft, ChevronRight, Loader2, CheckCircle, XCircle, Filter, Download } from 'lucide-react';
import { cn, formatNumber } from '@/lib/utils';
import { debounce } from 'lodash-es';

export default function AlertsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [alertType, setAlertType] = useState(searchParams.get('alertType') || '');
  const [severity, setSeverity] = useState(searchParams.get('severity') || '');
  const [acknowledged, setAcknowledged] = useState(searchParams.get('acknowledged') === 'true' ? 'true' : searchParams.get('acknowledged') === 'false' ? 'false' : '');
  const [page, setPage] = useState(Number(searchParams.get('page')) || 1);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectAll, setSelectAll] = useState(false);

  const params: AlertListParams = {
    page,
    size: 20,
    alert_type: alertType || undefined,
    severity: severity || undefined,
    acknowledged: acknowledged === 'true' ? true : acknowledged === 'false' ? false : undefined,
  };

  const { data, isLoading, error, refetch } = useAlerts(params);
  const acknowledgeMutation = useAcknowledgeAlert();
  const bulkAcknowledgeMutation = useBulkAcknowledgeAlerts();

  const handleFilterChange = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value);
    else params.delete(key);
    params.set('page', '1');
    router.push(`/alerts?${params.toString()}`);
    setSelectedIds([]);
    setSelectAll(false);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    const params = new URLSearchParams(searchParams);
    params.set('page', newPage.toString());
    router.push(`/alerts?${params.toString()}`);
    setSelectedIds([]);
    setSelectAll(false);
  };

  const handleSelectAll = (checked: boolean) => {
    setSelectAll(checked);
    if (checked && data) {
      setSelectedIds(data.items.map(a => a.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectOne = (id: string, checked: boolean) => {
    if (checked) {
      setSelectedIds(prev => [...prev, id]);
    } else {
      setSelectedIds(prev => prev.filter(i => i !== id));
      setSelectAll(false);
    }
  };

  const handleAcknowledge = async (id: string) => {
    try {
      await acknowledgeMutation.mutateAsync(id);
    } catch (err) {
      console.error('Erro ao reconhecer alerta:', err);
    }
  };

  const handleBulkAcknowledge = async () => {
    if (selectedIds.length === 0) return;
    try {
      await bulkAcknowledgeMutation.mutateAsync(selectedIds);
      setSelectedIds([]);
      setSelectAll(false);
    } catch (err) {
      console.error('Erro ao reconhecer alertas em lote:', err);
    }
  };

  const isPending = acknowledgeMutation.isPending || bulkAcknowledgeMutation.isPending;

  if (isLoading && !data) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-2" />
            <p className="text-muted-foreground">Carregando alertas...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const stats = React.useMemo(() => {
    if (!data) return { critical: 0, warning: 0, info: 0, unacknowledged: 0 };
    return {
      critical: data.items.filter(a => a.severity === 'critical').length,
      warning: data.items.filter(a => a.severity === 'warning').length,
      info: data.items.filter(a => a.severity === 'info').length,
      unacknowledged: data.items.filter(a => !a.acknowledged).length,
    };
  }, [data]);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Alertas</h1>
          <p className="text-muted-foreground">Monitoramento de riscos de estoque e validades</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Exportar
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Críticos</p>
                <p className="text-3xl font-bold text-destructive">{stats.critical}</p>
              </div>
              <div className="p-3 rounded-full bg-destructive/10">
                <AlertTriangle className="h-6 w-6 text-destructive" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Atenção</p>
                <p className="text-3xl font-bold text-amber-600">{stats.warning}</p>
              </div>
              <div className="p-3 rounded-full bg-amber-100">
                <AlertTriangle className="h-6 w-6 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Informativos</p>
                <p className="text-3xl font-bold text-primary">{stats.info}</p>
              </div>
              <div className="p-3 rounded-full bg-primary/10">
                <Package className="h-6 w-6 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Não Reconhecidos</p>
                <p className="text-3xl font-bold">{stats.unacknowledged}</p>
              </div>
              <div className="p-3 rounded-full bg-muted">
                <Clock className="h-6 w-6 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="list" className="space-y-4">
        <TabsList>
          <TabsTrigger value="list">Lista de Alertas</TabsTrigger>
          <TabsTrigger value="rules">Regras de Alerta</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex flex-col sm:flex-row gap-4">
                <Select value={alertType} onValueChange={(v) => handleFilterChange('alertType', v)}>
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
                <Select value={severity} onValueChange={(v) => handleFilterChange('severity', v)}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Todas severidades" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todas severidades</SelectItem>
                    {ALERT_SEVERITIES.map((s) => (
                      <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={acknowledged} onValueChange={(v) => handleFilterChange('acknowledged', v)}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos</SelectItem>
                    <SelectItem value="false">Não reconhecidos</SelectItem>
                    <SelectItem value="true">Reconhecidos</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {data?.items.length === 0 ? (
                <div className="text-center py-12">
                  <AlertTriangle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-1">Nenhum alerta encontrado</h3>
                  <p className="text-muted-foreground">
                    {alertType || severity || acknowledged ? 'Tente ajustar os filtros' : 'Sistema sem alertas no momento'}
                  </p>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <p className="text-sm text-muted-foreground">
                      {data?.total ?? 0} alerta{data?.total !== 1 ? 's' : ''} encontrado{data?.total !== 1 ? 's' : ''}
                    </p>
                    {selectedIds.length > 0 && (
                      <Button
                        variant="default"
                        size="sm"
                        onClick={handleBulkAcknowledge}
                        disabled={isPending}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <CheckCircle className="mr-2 h-4 w-4" />
                        Reconhecer {selectedIds.length} selecionado{selectedIds.length !== 1 ? 's' : ''}
                      </Button>
                    )}
                  </div>

                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-12">
                            <Checkbox
                              checked={selectAll}
                              onCheckedChange={handleSelectAll}
                              disabled={data?.items.length === 0}
                              aria-label="Selecionar todos"
                            />
                          </TableHead>
                          <TableHead>Produto</TableHead>
                          <TableHead>Tipo</TableHead>
                          <TableHead>Severidade</TableHead>
                          <TableHead>Mensagem</TableHead>
                          <TableHead>Data</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="w-32">Ações</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data?.items.map((alert) => {
                          const typeConfig = getAlertTypeConfig(alert.alert_type);
                          const severityConfig = getSeverityConfig(alert.severity);
                          return (
                            <TableRow key={alert.id} className={cn('hover:bg-muted/50', alert.acknowledged && 'opacity-60')}>
                              <TableCell>
                                <Checkbox
                                  checked={selectedIds.includes(alert.id)}
                                  onCheckedChange={(checked) => handleSelectOne(alert.id, checked as boolean)}
                                  disabled={alert.acknowledged}
                                />
                              </TableCell>
                              <TableCell>
                                <div>
                                  <p className="font-medium">{alert.product?.name || 'Produto não encontrado'}</p>
                                  <p className="text-xs text-muted-foreground font-mono">{alert.product?.sku}</p>
                                </div>
                              </TableCell>
                              <TableCell>
                                <Badge variant="secondary" className="text-xs">
                                  {typeConfig.label}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <Badge variant={severityConfig.color as any} className="text-xs font-medium">
                                  {severityConfig.label}
                                </Badge>
                              </TableCell>
                              <TableCell className="max-w-md">
                                <p className="text-sm">{alert.message}</p>
                              </TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                {formatAlertDate(alert.created_at)}
                              </TableCell>
                              <TableCell>
                                {alert.acknowledged ? (
                                  <Badge variant="success" className="text-xs">
                                    <CheckCircle className="mr-1 h-3 w-3" />
                                    Reconhecido
                                  </Badge>
                                ) : (
                                  <Badge variant="destructive" className="text-xs">
                                    <XCircle className="mr-1 h-3 w-3" />
                                    Pendente
                                  </Badge>
                                )}
                              </TableCell>
                              <TableCell>
                                {!alert.acknowledged && (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleAcknowledge(alert.id)}
                                    disabled={isPending}
                                  >
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

                  {data && data.pages > 1 && (
                    <div className="flex items-center justify-between mt-4">
                      <p className="text-sm text-muted-foreground">
                        Página {data.page} de {data.pages} — {data.total} alertas
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
                          disabled={page >= data.pages}
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

        <TabsContent value="rules">
          <Card>
            <CardHeader>
              <CardTitle>Configuração de Regras de Alerta</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground mb-6">
                Configure os limites para geração automática de alertas. As regras são avaliadas a cada 15 minutos.
              </p>
              <div className="space-y-4">
                <AlertRuleCard
                  title="Risco de Falta (Crítico)"
                  description="Alerta quando estoque projetado para acabar em 3 dias ou menos"
                  severity="critical"
                  threshold="3 dias"
                  enabled={true}
                />
                <AlertRuleCard
                  title="Risco de Falta (Atenção)"
                  description="Alerta quando estoque projetado para acabar entre 4 e 7 dias"
                  severity="warning"
                  threshold="7 dias"
                  enabled={true}
                />
                <AlertRuleCard
                  title="Risco de Validade"
                  description="Alerta para lotes com validade entre 15 e 30 dias"
                  severity="warning"
                  threshold="30 dias"
                  enabled={true}
                />
                <AlertRuleCard
                  title="Excesso de Estoque"
                  description="Alerta quando estoque atual excede 40% do nível máximo"
                  severity="info"
                  threshold="40% acima do máx."
                  enabled={true}
                />
                <AlertRuleCard
                  title="Ponto de Reposição"
                  description="Alerta quando estoque atinge o nível mínimo configurado no produto"
                  severity="info"
                  threshold="Nível mínimo"
                  enabled={false}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function AlertRuleCard({ title, description, severity, threshold, enabled }: {
  title: string;
  description: string;
  severity: 'critical' | 'warning' | 'info';
  threshold: string;
  enabled: boolean;
}) {
  const severityColors = {
    critical: 'bg-destructive/10 text-destructive border-destructive/20',
    warning: 'bg-amber-100 text-amber-800 border-amber-200',
    info: 'bg-primary/10 text-primary border-primary/20',
  };

  return (
    <div className="flex items-center justify-between p-4 rounded-lg border">
      <div className="flex items-center gap-4">
        <Badge variant={severity as any} className={cn('text-xs', severityColors[severity])}>
          {severity === 'critical' ? 'Crítico' : severity === 'warning' ? 'Atenção' : 'Info'}
        </Badge>
        <div>
          <p className="font-medium">{title}</p>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm text-muted-foreground">Limite</p>
          <p className="font-mono font-medium">{threshold}</p>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" defaultChecked={enabled} className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary" />
          <span className="text-sm">Ativo</span>
        </label>
      </div>
    </div>
  );
}