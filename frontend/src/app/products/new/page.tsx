'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Save } from 'lucide-react';
import { useCreateProduct } from '@/hooks/useProducts';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

export default function NewProductPage() {
  const router = useRouter();
  const createProduct = useCreateProduct();
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

  async function handleSave(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    try {
      await createProduct.mutateAsync({
        name, sku,
        barcode: barcode.trim() || null,
        generic_name: genericName || null,
        atc_code: atcCode || null,
        category: 'other', unit,
        unit_cost: Number(unitCost),
        min_stock_level: Number(minStock),
        max_stock_level: Number(maxStock),
        lead_time_days: Number(leadTime),
        controlled_substance: false,
      });
      router.push('/products');
    } catch { /* exibido abaixo */ }
  }

  return (
    <div className="p-6 space-y-6">
      <Button variant="outline" onClick={() => router.push('/products')}>
        <ArrowLeft className="mr-2 h-4 w-4" /> Voltar
      </Button>
      <Card>
        <CardHeader><CardTitle>Novo medicamento</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            <Input placeholder="Nome do medicamento *" value={name} onChange={(e) => setName(e.target.value)} required />
            <Input placeholder="SKU *" value={sku} onChange={(e) => setSku(e.target.value)} required />
            <Input placeholder="Código de barras (EAN/GTIN)" value={barcode} onChange={(e) => setBarcode(e.target.value)} />
            <Input placeholder="Princípio ativo" value={genericName} onChange={(e) => setGenericName(e.target.value)} />
            <Input placeholder="Código ATC" value={atcCode} onChange={(e) => setAtcCode(e.target.value)} />
            <Input placeholder="Unidade (un, mg, mL)" value={unit} onChange={(e) => setUnit(e.target.value)} required />
            <Input type="number" min="0" step="0.01" placeholder="Custo unitário" value={unitCost} onChange={(e) => setUnitCost(e.target.value)} required />
            <Input type="number" min="0" placeholder="Estoque mínimo" value={minStock} onChange={(e) => setMinStock(e.target.value)} required />
            <Input type="number" min="0" placeholder="Estoque máximo" value={maxStock} onChange={(e) => setMaxStock(e.target.value)} required />
            <Input type="number" min="0" placeholder="Lead time (dias)" value={leadTime} onChange={(e) => setLeadTime(e.target.value)} required />
            {createProduct.isError && (
              <p className="text-sm text-destructive">
                Não foi possível cadastrar. Verifique se o SKU já existe.
              </p>
            )}
            <Button type="submit" disabled={createProduct.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {createProduct.isPending ? 'Salvando...' : 'Cadastrar'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}