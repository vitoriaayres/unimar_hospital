'use client';

import Link from 'next/link';
import { useProducts, ProductListParams, PRODUCT_CATEGORIES, getCategoryLabel } from '@/hooks/useProducts';
import { useUrlParams } from '@/hooks/useUrlParams';
import { Button } from '@/components/ui/Button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { SearchInput } from '@/components/ui/SearchInput';
import { Pagination } from '@/components/ui/Pagination';
import { Package, Plus, Loader2, ScanLine } from 'lucide-react';
import { formatCurrency } from '@/lib/utils';

export default function ProductsPage() {
  const url = useUrlParams();
  const search = url.get('search');
  const category = url.get('category');

  const params: ProductListParams = {
    page: url.page,
    size: 20,
    search: search || undefined,
    category: category || undefined,
  };

  const { data, isLoading, isFetching, error, refetch } = useProducts(params);

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Produtos</h1>
          <p className="text-muted-foreground">Cadastro de medicamentos e insumos</p>
        </div>
        <div className="flex gap-2">
          <Link href="/products/scan">
            <Button variant="outline">
              <ScanLine className="mr-2 h-4 w-4" />
              Ler código
            </Button>
          </Link>
          <Link href="/products/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Novo produto
            </Button>
          </Link>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <SearchInput
              value={search}
              onChange={(v) => url.set({ search: v })}
              placeholder="Buscar por nome, SKU, princípio ativo ou código de barras..."
              className="flex-1 sm:max-w-md"
            />
            <Select value={category} onValueChange={(v) => url.set({ category: v })}>
              <SelectTrigger className="w-full sm:w-[200px]">
                <SelectValue placeholder="Todas as categorias" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Todas as categorias</SelectItem>
                {PRODUCT_CATEGORIES.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {getCategoryLabel(cat)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {isFetching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-12 text-center">
              <Loader2 className="mx-auto mb-2 h-8 w-8 animate-spin text-primary" />
              <p className="text-muted-foreground">Carregando produtos...</p>
            </div>
          ) : error ? (
            <div className="py-12 text-center text-destructive">
              <p>Erro ao carregar produtos</p>
              <Button variant="outline" onClick={() => refetch()} className="mt-2">
                Tentar novamente
              </Button>
            </div>
          ) : !data?.items.length ? (
            <div className="py-12 text-center">
              <Package className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
              <h3 className="mb-1 text-lg font-medium">Nenhum produto encontrado</h3>
              <p className="mb-4 text-muted-foreground">
                {search || category ? 'Tente ajustar os filtros' : 'Cadastre o primeiro produto'}
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Produto</TableHead>
                      <TableHead className="hidden lg:table-cell">Código de barras</TableHead>
                      <TableHead className="hidden md:table-cell">Categoria</TableHead>
                      <TableHead className="hidden xl:table-cell">Controlado</TableHead>
                      <TableHead className="text-right">Custo unit.</TableHead>
                      <TableHead className="hidden text-right sm:table-cell">Estoque mín.</TableHead>
                      <TableHead className="w-28" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.items.map((product) => (
                      <TableRow key={product.id} className="hover:bg-muted/50">
                        <TableCell>
                          <Link href={`/products/${product.id}`} className="font-medium hover:underline">
                            {product.name}
                          </Link>
                          <p className="text-xs text-muted-foreground">
                            <span className="font-mono">{product.sku}</span>
                            {product.generic_name && ` · ${product.generic_name}`}
                          </p>
                        </TableCell>
                        <TableCell className="hidden font-mono text-xs lg:table-cell">{product.barcode || '—'}</TableCell>
                        <TableCell className="hidden md:table-cell">
                          <Badge variant="secondary" className="text-xs">
                            {getCategoryLabel(product.category)}
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden xl:table-cell">
                          {product.controlled_substance ? (
                            <Badge variant="destructive" className="text-xs">Controlado</Badge>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right font-mono">{formatCurrency(product.unit_cost)}</TableCell>
                        <TableCell className="hidden text-right sm:table-cell">{product.min_stock_level}</TableCell>
                        <TableCell>
                          <div className="flex items-center justify-end gap-3 text-sm">
                            <Link href={`/products/${product.id}`} className="text-primary hover:underline">
                              Ver
                            </Link>
                            <Link href={`/products/${product.id}/edit`} className="text-muted-foreground hover:text-foreground">
                              Editar
                            </Link>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <Pagination
                page={data.page}
                pages={data.pages}
                total={data.total}
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
