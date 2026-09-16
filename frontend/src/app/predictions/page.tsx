'use client';

import React from 'react';
import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { usePredictions, useModels, useGenerateForecast, Prediction, PredictionListParams, ModelInfo, formatPredictionDate } from '@/hooks/usePredictions';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { ForecastChart } from '@/components/charts/ForecastChart';
import { Package, Search, Filter, ChevronLeft, ChevronRight, Loader2, Download, Zap, Brain, TrendingUp, Settings } from 'lucide-react';
import { cn, formatNumber, formatCurrency } from '@/lib/utils';
import { debounce } from 'lodash-es';

export default function PredictionsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [modelVersion, setModelVersion] = useState(searchParams.get('modelVersion') || '');
  const [productId, setProductId] = useState(searchParams.get('productId') || '');
  const [horizonDays, setHorizonDays] = useState(Number(searchParams.get('horizonDays')) || 30);
  const [page, setPage] = useState(Number(searchParams.get('page')) || 1);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [showGenerateModal, setShowGenerateModal] = useState(false);

  const params: PredictionListParams = {
    page,
    size: 20,
    model_version: modelVersion || undefined,
    product_id: productId || undefined,
    horizon_days: horizonDays,
  };

  const { data: predictions, isLoading, error, refetch } = usePredictions(params);
  const { data: models, isLoading: modelsLoading } = useModels();
  const generateMutation = useGenerateForecast();

  const handleFilterChange = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value);
    else params.delete(key);
    params.set('page', '1');
    router.push(`/predictions?${params.toString()}`);
  };

  const handleHorizonChange = (value: string) => {
    const numValue = Number(value) || 30;
    setHorizonDays(numValue);
    const params = new URLSearchParams(searchParams);
    params.set('horizonDays', numValue.toString());
    params.set('page', '1');
    router.push(`/predictions?${params.toString()}`);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    const params = new URLSearchParams(searchParams);
    params.set('page', newPage.toString());
    router.push(`/predictions?${params.toString()}`);
  };

  const handleGenerateForecast = async () => {
    if (!selectedProductId) return;
    try {
      await generateMutation.mutateAsync({
        product_ids: [selectedProductId],
        horizon_days: horizonDays,
        model_version: modelVersion || undefined,
      });
      setShowGenerateModal(false);
      refetch();
    } catch (err) {
      console.error('Erro ao gerar previsão:', err);
    }
  };

  const getProductPredictions = (productId: string) => {
    return predictions?.items.filter(p => p.product_id === productId) || [];
  };

  const uniqueProducts = React.useMemo(() => {
    const seen = new Set();
    return predictions?.items.filter(p => {
      if (p.product_id && !seen.has(p.product_id)) {
        seen.add(p.product_id);
        return true;
      }
      return false;
    }) || [];
  }, [predictions]);

  if (isLoading && !predictions) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-2" />
            <p className="text-muted-foreground">Carregando previsões...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Previsões de Demanda</h1>
          <p className="text-muted-foreground">Visualização e comparação de modelos de previsão</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Exportar CSV
          </Button>
          <Button onClick={() => setShowGenerateModal(true)}>
            <Zap className="mr-2 h-4 w-4" />
            Gerar Previsão
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total de Previsões</p>
                <p className="text-3xl font-bold">{formatNumber(predictions?.total || 0)}</p>
              </div>
              <div className="p-3 rounded-full bg-primary/10 text-primary">
                <Brain className="h-6 w-6" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Produtos com Previsão</p>
                <p className="text-3xl font-bold">{uniqueProducts.length}</p>
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
                <p className="text-sm font-medium text-muted-foreground">Modelos Disponíveis</p>
                <p className="text-3xl font-bold">{models?.length || 0}</p>
              </div>
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                <Settings className="h-6 w-6" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Horizonte Atual</p>
                <p className="text-3xl font-bold">{horizonDays} dias</p>
              </div>
              <div className="p-3 rounded-full bg-amber-100 text-amber-600">
                <TrendingUp className="h-6 w-6" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="table" className="space-y-4">
        <TabsList>
          <TabsTrigger value="table">Tabela Comparativa</TabsTrigger>
          <TabsTrigger value="chart">Gráficos</TabsTrigger>
          <TabsTrigger value="models">Modelos</TabsTrigger>
        </TabsList>

        <TabsContent value="table">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex flex-col sm:flex-row gap-4">
                <Select value={modelVersion} onValueChange={(v) => handleFilterChange('modelVersion', v)}>
                  <SelectTrigger className="w-full sm:w-[200px]">
                    <SelectValue placeholder="Todos os modelos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos os modelos</SelectItem>
                    {models?.map((m) => (
                      <SelectItem key={m.version} value={m.version}>
                        {m.name} (v{m.version}) - MAPE: {m.mape.toFixed(1)}%
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={productId} onValueChange={(v) => handleFilterChange('productId', v)}>
                  <SelectTrigger className="w-full sm:w-[250px]">
                    <SelectValue placeholder="Todos os produtos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos os produtos</SelectItem>
                    {uniqueProducts.map((p) => (
                      <SelectItem key={p.product_id} value={p.product_id}>
                        {p.product?.name} ({p.product?.sku})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={horizonDays.toString()} onValueChange={handleHorizonChange}>
                  <SelectTrigger className="w-full sm:w-[150px]">
                    <SelectValue placeholder="Horizonte" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="7">7 dias</SelectItem>
                    <SelectItem value="15">15 dias</SelectItem>
                    <SelectItem value="30">30 dias</SelectItem>
                    <SelectItem value="60">60 dias</SelectItem>
                    <SelectItem value="90">90 dias</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {predictions?.items.length === 0 ? (
                <div className="text-center py-12">
                  <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-1">Nenhuma previsão encontrada</h3>
                  <p className="text-muted-foreground mb-4">
                    {modelVersion || productId ? 'Tente ajustar os filtros' : 'Gere a primeira previsão'}
                  </p>
                  <Button onClick={() => setShowGenerateModal(true)}>
                    <Zap className="mr-2 h-4 w-4" />
                    Gerar Previsão
                  </Button>
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Produto</TableHead>
                          <TableHead>Data Prevista</TableHead>
                          <TableHead className="text-right">Previsto</TableHead>
                          <TableHead className="text-right">IC Inferior</TableHead>
                          <TableHead className="text-right">IC Superior</TableHead>
                          <TableHead>Modelo</TableHead>
                          <TableHead className="text-right">MAPE</TableHead>
                          <TableHead>Criado em</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {predictions?.items.map((pred) => (
                          <TableRow key={pred.id} className="hover:bg-muted/50">
                            <TableCell>
                              <div>
                                <p className="font-medium">{pred.product?.name || 'Produto não encontrado'}</p>
                                <p className="text-xs text-muted-foreground font-mono">{pred.product?.sku}</p>
                              </div>
                            </TableCell>
                            <TableCell>{formatPredictionDate(pred.forecast_date)}</TableCell>
                            <TableCell className="text-right font-medium">{formatNumber(pred.predicted_quantity)}</TableCell>
                            <TableCell className="text-right text-muted-foreground">{formatNumber(pred.confidence_lower)}</TableCell>
                            <TableCell className="text-right text-muted-foreground">{formatNumber(pred.confidence_upper)}</TableCell>
                            <TableCell>
                              <Badge variant="secondary" className="text-xs">
                                v{pred.model_version}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">
                              {pred.mape_score !== null ? (
                                <span className={cn(
                                  'font-medium',
                                  pred.mape_score < 10 ? 'text-green-600' : pred.mape_score < 15 ? 'text-amber-600' : 'text-destructive'
                                )}>
                                  {pred.mape_score.toFixed(1)}%
                                </span>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">
                              {new Date(pred.created_at).toLocaleString('pt-BR')}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {predictions && predictions.pages > 1 && (
                    <div className="flex items-center justify-between mt-4">
                      <p className="text-sm text-muted-foreground">
                        Página {predictions.page} de {predictions.pages} — {predictions.total} previsões
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
                          disabled={page >= predictions.pages}
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

        <TabsContent value="chart">
          {uniqueProducts.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">Selecione um produto para ver o gráfico</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-6">
              <div className="flex items-center gap-4">
                <label className="text-sm font-medium">Produto:</label>
                <Select value={selectedProductId || ''} onValueChange={setSelectedProductId}>
                  <SelectTrigger className="w-[300px]">
                    <SelectValue placeholder="Selecione um produto" />
                  </SelectTrigger>
                  <SelectContent>
                    {uniqueProducts.map((p) => (
                      <SelectItem key={p.product_id} value={p.product_id}>
                        {p.product?.name} ({p.product?.sku})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {selectedProductId && (
                <>
                  <Card>
                    <CardHeader>
                      <CardTitle>
                        {uniqueProducts.find(p => p.product_id === selectedProductId)?.product?.name}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ForecastChart
                        data={getProductPredictions(selectedProductId).map(p => ({
                          date: p.forecast_date,
                          actual: null,
                          predicted: p.predicted_quantity,
                          lower: p.confidence_lower,
                          upper: p.confidence_upper,
                        }))}
                        height={400}
                      />
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Detalhamento por Modelo</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Modelo</TableHead>
                              <TableHead className="text-right">Média Prevista (30d)</TableHead>
                              <TableHead className="text-right">Total Previsto (30d)</TableHead>
                              <TableHead className="text-right">MAPE Médio</TableHead>
                              <TableHead>Última Atualização</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {React.useMemo(() => {
                              const byModel = new Map<string, Prediction[]>();
                              getProductPredictions(selectedProductId).forEach(p => {
                                if (!byModel.has(p.model_version)) byModel.set(p.model_version, []);
                                byModel.get(p.model_version)!.push(p);
                              });
                              return Array.from(byModel.entries()).map(([model, preds]) => ({
                                model,
                                avgPredicted: preds.reduce((s, p) => s + p.predicted_quantity, 0) / preds.length,
                                totalPredicted: preds.reduce((s, p) => s + p.predicted_quantity, 0),
                                avgMape: preds.filter(p => p.mape_score !== null).reduce((s, p) => s + (p.mape_score || 0), 0) / Math.max(1, preds.filter(p => p.mape_score !== null).length),
                                lastUpdate: Math.max(...preds.map(p => new Date(p.created_at).getTime())),
                              }));
                            }, [selectedProductId]).map((row) => (
                              <TableRow key={row.model} className="hover:bg-muted/50">
                                <TableCell>
                                  <Badge variant="secondary">v{row.model}</Badge>
                                </TableCell>
                                <TableCell className="text-right">{row.avgPredicted.toFixed(1)}</TableCell>
                                <TableCell className="text-right">{formatNumber(row.totalPredicted)}</TableCell>
                                <TableCell className="text-right">
                                  {row.avgMape > 0 ? (
                                    <span className={cn(
                                      'font-medium',
                                      row.avgMape < 10 ? 'text-green-600' : row.avgMape < 15 ? 'text-amber-600' : 'text-destructive'
                                    )}>
                                      {row.avgMape.toFixed(1)}%
                                    </span>
                                  ) : (
                                    <span className="text-muted-foreground">—</span>
                                  )}
                                </TableCell>
                                <TableCell className="text-sm text-muted-foreground">
                                  {new Date(row.lastUpdate).toLocaleString('pt-BR')}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>
                </>
              )}
            </div>
          )}
        </TabsContent>

        <TabsContent value="models">
          <Card>
            <CardHeader>
              <CardTitle>Modelos Disponíveis</CardTitle>
            </CardHeader>
            <CardContent>
              {modelsLoading ? (
                <div className="py-12 text-center">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-2" />
                  <p className="text-muted-foreground">Carregando modelos...</p>
                </div>
              ) : models?.length === 0 ? (
                <div className="text-center py-12">
                  <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-1">Nenhum modelo cadastrado</h3>
                  <p className="text-muted-foreground">Treine modelos no pipeline de ML</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {models?.map((model) => (
                    <div key={model.version} className="flex items-center justify-between p-4 rounded-lg border">
                      <div className="flex items-center gap-4">
                        <div className="p-3 rounded-lg bg-primary/10">
                          <Brain className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">{model.name}</p>
                          <p className="text-sm text-muted-foreground">
                            v{model.version} • {model.algorithm} • {model.is_active ? 'Ativo' : 'Inativo'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground">MAPE</p>
                          <p className={cn(
                            'font-bold',
                            model.mape < 10 ? 'text-green-600' : model.mape < 15 ? 'text-amber-600' : 'text-destructive'
                          )}>
                            {model.mape.toFixed(1)}%
                          </p>
                        </div>
                        <Badge variant={model.is_active ? 'success' : 'secondary'} className="text-xs">
                          {model.is_active ? 'Produção' : 'Homologação'}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {showGenerateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-background w-full max-w-md rounded-lg border p-6 shadow-lg">
            <h2 className="text-xl font-bold mb-4">Gerar Nova Previsão</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Produto</label>
                <Select value={selectedProductId || ''} onValueChange={setSelectedProductId}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Selecione um produto" />
                  </SelectTrigger>
                  <SelectContent>
                    {uniqueProducts.map((p) => (
                      <SelectItem key={p.product_id} value={p.product_id}>
                        {p.product?.name} ({p.product?.sku})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Horizonte (dias)</label>
                <Select value={horizonDays.toString()} onValueChange={handleHorizonChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="7">7 dias</SelectItem>
                    <SelectItem value="15">15 dias</SelectItem>
                    <SelectItem value="30">30 dias</SelectItem>
                    <SelectItem value="60">60 dias</SelectItem>
                    <SelectItem value="90">90 dias</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Modelo</label>
                <Select value={modelVersion} onValueChange={(v) => handleFilterChange('modelVersion', v)}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Auto (melhor modelo)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Auto (melhor modelo)</SelectItem>
                    {models?.map((m) => (
                      <SelectItem key={m.version} value={m.version}>
                        {m.name} (v{m.version})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <Button variant="outline" onClick={() => setShowGenerateModal(false)}>
                Cancelar
              </Button>
              <Button
                onClick={handleGenerateForecast}
                disabled={generateMutation.isPending || !selectedProductId}
              >
                {generateMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Gerando...
                  </>
                ) : (
                  'Gerar Previsão'
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}