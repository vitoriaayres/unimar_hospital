'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, CheckCircle2, PackageSearch, Save } from 'lucide-react';
import { BarcodeScanner } from '@/components/products/BarcodeScanner';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useCreateProduct, useProductByBarcode, Product } from '@/hooks/useProducts';

export default function ProductScannerPage() {
  const router = useRouter();
  const [barcode, setBarcode] = useState('');
  const [scanned, setScanned] = useState<Product | null>(null);
  const [name, setName] = useState('');
  const [sku, setSku] = useState('');
  const [genericName, setGenericName] = useState('');
  const [atcCode, setAtcCode] = useState('');

  const productQuery = useProductByBarcode(barcode, !!barcode && !scanned);
  const createProduct = useCreateProduct();

  const handleDetected = (code: string) => {
    setScanned(null);
    setBarcode(code);
  };

  const saveProduct = async () => {
    if (!barcode || !name || !sku) {
      return;
    }

    try {
      const product = await createProduct.mutateAsync({
        barcode,
        name,
        sku,
        generic_name: genericName || null,
        atc_code: atcCode || null,
        category: 'other',
        unit: 'un',
        unit_cost: 0,
        min_stock_level: 0,
        max_stock_level: 100,
        lead_time_days: 7,
        controlled_substance: false,
      });

      setScanned(product);
    } catch {
      // O erro da mutation é mostrado abaixo.
    }
  };

  const productFound = productQuery.data;
  
  const errorStatus = (
    productQuery.error as { response?: { status?: number } } | null)?.response?.status;

  const notFound =
    !!barcode &&
    productQuery.isFetched &&
    !productQuery.isFetching &&
    !productQuery.data &&
    errorStatus === 404;

  const searchError =
    !!barcode &&
    productQuery.isError &&
    errorStatus !== 404;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="outline" size="sm" onClick={() => router.push('/products')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Produtos
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Ler código de barras</h1>
          <p className="text-muted-foreground">
            Escaneie o código do medicamento para localizar ou cadastrar o produto.
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <BarcodeScanner onDetected={handleDetected} />

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Código lido</CardTitle>
            </CardHeader>
            <CardContent>
              {barcode ? (
                <div className="rounded-lg bg-muted p-4 font-mono text-lg">
                  {barcode}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Nenhum código foi lido ainda.
                </p>
              )}
            </CardContent>
          </Card>

          {productFound && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  Produto encontrado
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm text-muted-foreground">Nome</p>
                  <p className="font-medium">{productFound.name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">SKU</p>
                  <Badge variant="secondary">{productFound.sku}</Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Código de barras</p>
                  <p className="font-mono">{productFound.barcode}</p>
                </div>
                <Button onClick={() => router.push(`/products/${productFound.id}`)}>
                  Ver produto
                </Button>
              </CardContent>
            </Card>
          )}

          {notFound && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <PackageSearch className="h-5 w-5" />
                  Produto não cadastrado
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  O código não foi encontrado. Preencha os dados básicos para cadastrar o medicamento.
                </p>

                <div className="grid gap-3">
                  <Input
                    placeholder="Nome do medicamento *"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                  />
                  <Input
                    placeholder="SKU *"
                    value={sku}
                    onChange={(event) => setSku(event.target.value)}
                  />
                  <Input
                    placeholder="Princípio ativo"
                    value={genericName}
                    onChange={(event) => setGenericName(event.target.value)}
                  />
                  <Input
                    placeholder="Código ATC"
                    value={atcCode}
                    onChange={(event) => setAtcCode(event.target.value)}
                  />
                </div>

                {createProduct.isError && (
                  <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                    Não foi possível cadastrar. Verifique suas permissões e se o SKU já existe.
                  </p>
                )}

                <Button
                  onClick={() => void saveProduct()}
                  disabled={!name || !sku || createProduct.isPending}
                >
                  <Save className="mr-2 h-4 w-4" />
                  {createProduct.isPending ? 'Salvando...' : 'Cadastrar medicamento'}
                </Button>
              </CardContent>
            </Card>
          )}{searchError && (<p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"> Não foi possível consultar o medicamento. Verifique a conexão com o servidor e tente novamente.</p>)}
        </div>
      </div>
    </div>
  );
}
