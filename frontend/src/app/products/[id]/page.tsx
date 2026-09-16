'use client';

import React from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useProduct } from '@/hooks/useProducts';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { ForecastChart } from '@/components/charts/ForecastChart';
import { BarChart } from '@/components/charts/ForecastChart';
import { Package, Pill, Tag, Truck, Clock, AlertTriangle, CheckCircle, ChevronLeft, Loader2 } from 'lucide-react';
import { cn, formatCurrency, formatNumber, formatDate, getCategoryLabel, getStatusColor } from '@/lib/utils';

export default function ProductDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const { data: product, isLoading, error } = useProduct(id);

  if (isLoading) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-2" />
            <p className="text-muted-foreground">Carregando produto...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center text-destructive">
            <p>Produto não encontrado</p>
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

  const forecastData = [
    { date: '2024-01-01', actual: 42, predicted: 45, lower: 38, upper: 52 },
    { date: '2024-01-02', actual: 38, predicted: 40, lower: 33, upper: 47 },
    { date: '2024-01-03', actual: 45, predicted: 43, lower: 36, upper: 50 },
    { date: '2024-01-04', actual: 41, predicted: 42, lower: 35, upper: 49 },
    { date: '2024-01-05', actual: 39, predicted: 41, lower: 34, upper: 48 },
    { date: '2024-01-06', actual: 44, predicted: 44, lower: 37, upper: 51 },
    { date: '2024-01-07', actual: 40, predicted: 42, lower: 35, upper: 49 },
    { date: '2024-01-08', actual: null, predicted: 43, lower: 36, upper: 50 },
    { date: '2024-01-09', actual: null, predicted: 41, lower: 34, upper: 48 },
    { date: '2024-01-10', actual: null, predicted: 42, lower: 35, upper: 49 },
    { date: '2024-01-11', actual: null, predicted: 44, lower: 37, upper: 51 },
    { date: '2024-01-12', actual: null, predicted: 40, lower: 33, upper: 47 },
    { date: '2024-01-13', actual: null, predicted: 39, lower: 32, upper: 46 },
    { date: '2024-01-14', actual: null, predicted: 41, lower: 34, upper: 48 },
    { date: '2024-01-15', actual: null, predicted: 43, lower: 36, upper: 50 },
  ];

  const consumptionByDept = [
    { name: 'UTI', value: 120 },
    { name: 'Emergência', value: 85 },
    { name: 'Enfermaria', value: 200 },
    { name: 'Ambulatório', value: 60 },
  ];

  const consumptionByCategory = [
    { name: 'Antibiótico', value: 180 },
    { name: 'Analgésico', value: 150 },
    { name: 'Cardiovascular', value: 95 },
    { name: 'Outros', value: 40 },
  ];

  return (
    <div className="p-6 space-y-6">
      <Link href="/products" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ChevronLeft className="h-4 w-4" />
        Voltar
      </Link>

      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <Badge variant="secondary" className="text-sm">{product.sku}</Badge>
            {product.controlled_substance && (
              <Badge variant="destructive" className="text-xs">Controlado</Badge>
            )}
            <Badge variant={product.is_active ? 'success' : 'secondary'} className="text-xs">
              {product.is_active ? 'Ativo' : 'Inativo'}
            </Badge>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">{product.name}</h1>
          {product.generic_name && (
            <p className="text-muted-foreground">Princípio ativo: {product.generic_name}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Link href={`/products/${product.id}/edit`}>
            <Button variant="outline">
              Editar
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Previsão de Demanda</CardTitle>
          </CardHeader>
          <CardContent>
            <ForecastChart data={forecastData} height={350} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Resumo do Estoque</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-3">
                <Package className="h-5 w-5 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Estoque Atual</span>
              </div>
              <span className="text-2xl font-bold">1.234 un</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-600" />
                <span className="text-sm text-muted-foreground">Nível Mínimo</span>
              </div>
              <span className="font-medium">{formatNumber(product.min_stock_level)} un</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-3">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span className="text-sm text-muted-foreground">Nível Máximo</span>
              </div>
              <span className="font-medium">{formatNumber(product.max_stock_level)} un</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-3">
                <Truck className="h-5 w-5 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Lead Time</span>
              </div>
              <span className="font-medium">{product.lead_time_days} dias</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-3">
                <Tag className="h-5 w-5 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Custo Unitário</span>
              </div>
              <span className="font-medium">{formatCurrency(product.unit_cost)}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="details" className="space-y-4">
        <TabsList>
          <TabsTrigger value="details">Detalhes</TabsTrigger>
          <TabsTrigger value="consumption">Consumo</TabsTrigger>
          <TabsTrigger value="batches">Lotes</TabsTrigger>
          <TabsTrigger value="movements">Movimentações</TabsTrigger>
        </TabsList>

        <TabsContent value="details">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Informações Básicas</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">SKU</p>
                    <p className="font-mono">{product.sku}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Código ATC</p>
                    <p className="font-mono">{product.atc_code || '—'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Categoria</p>
                    <p>
                      <Badge variant="secondary">{getCategoryLabel(product.category)}</Badge>
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Unidade</p>
                    <p>{product.unit}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Controlado</p>
                    <p>{product.controlled_substance ? 'Sim' : 'Não'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Status</p>
                    <p>
                      <Badge variant={product.is_active ? 'success' : 'secondary'} className={cn('bg-transparent border', product.is_active ? 'text-green-600 border-green-300' : 'text-muted-foreground border-muted')}>
                        {product.is_active ? 'Ativo' : 'Inativo'}
                      </Badge>
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Parâmetros de Estoque</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Estoque Mínimo</p>
                    <p className="text-2xl font-bold">{formatNumber(product.min_stock_level)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Estoque Máximo</p>
                    <p className="text-2xl font-bold">{formatNumber(product.max_stock_level)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Lead Time</p>
                    <p className="text-2xl font-bold">{product.lead_time_days} dias</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Custo Unitário</p>
                    <p className="text-2xl font-bold">{formatCurrency(product.unit_cost)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Metadados</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-muted p-4 rounded overflow-auto">
                  {JSON.stringify(product.product_metadata, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="consumption">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Consumo por Departamento</CardTitle>
              </CardHeader>
              <CardContent>
                <BarChart data={consumptionByDept} height={300} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Consumo por Categoria</CardTitle>
              </CardHeader>
              <CardContent>
                <BarChart data={consumptionByCategory} height={300} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="batches">
          <Card>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Lote</TableHead>
                      <TableHead>Quantidade</TableHead>
                      <TableHead>Validade</TableHead>
                      <TableHead>Fabricação</TableHead>
                      <TableHead>Custo Unit.</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Recebido em</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                        Nenhum lote cadastrado
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="movements">
          <Card>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Data</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Quantidade</TableHead>
                      <TableHead>Lote</TableHead>
                      <TableHead>Referência</TableHead>
                      <TableHead>Usuário</TableHead>
                      <TableHead>Observações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                        Nenhuma movimentação registrada
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}