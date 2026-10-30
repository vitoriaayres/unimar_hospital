
'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Save } from 'lucide-react';
import { useProduct, useUpdateProduct } from '@/hooks/useProducts';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

export default function EditProductPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: product, isLoading, error } = useProduct(id);
  const updateProduct = useUpdateProduct();

  const [name, setName] = useState('');
  const [sku, setSku] = useState('');
  const [barcode, setBarcode] = useState('');
  const [genericName, setGenericName] = useState('');
  const [atcCode, setAtcCode] = useState('');
  const [unit, setUnit] = useState('un');
  const [unitCost, setUnitCost] = useState('0');
  const [minStock, setMinStock] = useState('0');
  const [maxStock, setMaxStock] = useState('100');
  const [leadTime, setLeadTime] = useState('7');

  useEffect(() => {
    if (!product) return;

    setName(product.name);
    setSku(product.sku);
    setBarcode(product.barcode ?? '');
    setGenericName(product.generic_name ?? '');
    setAtcCode(product.atc_code ?? '');
    setUnit(product.unit);
    setUnitCost(String(product.unit_cost));
    setMinStock(String(product.min_stock_level));
    setMaxStock(String(product.max_stock_level));
    setLeadTime(String(product.lead_time_days));
  }, [product]);

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      await updateProduct.mutateAsync({
        id,
        data: {
          name,
          sku,
          barcode: barcode.trim() || null,
          generic_name: genericName || null,
          atc_code: atcCode || null,
          unit,
          unit_cost: Number(unitCost),
          min_stock_level: Number(minStock),
          max_stock_level: Number(maxStock),
          lead_time_days: Number(leadTime),
        },
      });

      router.push(`/products/${id}`);
    } catch {
      // O erro é apresentado na tela.
    }
  }

  if (isLoading) {
    return <div className="p-6">Carregando produto...</div>;
  }

  if (error || !product) {
    return (
      <div className="p-6 space-y-4">
        <p>Não foi possível carregar o produto.</p>
        <Button onClick={() => router.push('/products')}>
          Voltar aos produtos
        </Button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <Button
        variant="outline"
        onClick={() => router.push(`/products/${id}`)}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Voltar
      </Button>

      <Card>
        <CardHeader>
          <CardTitle>Editar medicamento</CardTitle>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            <Input
              placeholder="Nome do medicamento *"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />

            <Input
              placeholder="SKU *"
              value={sku}
              onChange={(e) => setSku(e.target.value)}
              required
            />

            <Input
              placeholder="Código de barras (EAN/GTIN)"
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
            />

            <Input
              placeholder="Princípio ativo"
              value={genericName}
              onChange={(e) => setGenericName(e.target.value)}
            />

            <Input
              placeholder="Código ATC"
              value={atcCode}
              onChange={(e) => setAtcCode(e.target.value)}
            />

            <label className="block space-y-1">
              <span className="text-sm">Unidade</span>
              <Input
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                required
              />
            </label>

            <label className="block space-y-1">
              <span className="text-sm">Custo unitário</span>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={unitCost}
                onChange={(e) => setUnitCost(e.target.value)}
                required
              />
            </label>

            <label className="block space-y-1">
              <span className="text-sm">Estoque mínimo</span>
              <Input
                type="number"
                min="0"
                value={minStock}
                onChange={(e) => setMinStock(e.target.value)}
                required
              />
            </label>

            <label className="block space-y-1">
              <span className="text-sm">Estoque máximo</span>
              <Input
                type="number"
                min="0"
                value={maxStock}
                onChange={(e) => setMaxStock(e.target.value)}
                required
              />
            </label>

            <label className="block space-y-1">
              <span className="text-sm">Prazo de reposição (dias)</span>
              <Input
                type="number"
                min="0"
                value={leadTime}
                onChange={(e) => setLeadTime(e.target.value)}
                required
              />
            </label>

            {updateProduct.isError && (
              <p className="text-sm text-destructive">
                Não foi possível salvar. Verifique os dados, as permissões
                e se o SKU já está sendo usado por outro produto.
              </p>
            )}

            <Button type="submit" disabled={updateProduct.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {updateProduct.isPending ? 'Salvando...' : 'Salvar alterações'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}