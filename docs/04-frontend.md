# Frontend

Next.js 14 (App Router) em `frontend/`. Roda em **http://localhost:3000**.

## Organização do código

```
frontend/src/
├── app/                 # uma pasta por tela (rota)
│   ├── page.tsx         # Dashboard
│   ├── login/ products/ inventory/ predictions/ model/ alerts/ ...
│   ├── layout.tsx       # HTML raiz, fonte, providers
│   └── providers.tsx    # React Query
├── components/
│   ├── layout/          # DashboardLayout, Sidebar, Header
│   ├── ui/              # Button, Card, Table, Badge, Tabs, Select, Input...
│   ├── charts/          # ForecastChart (Recharts)
│   ├── dashboard/       # conteúdo do Dashboard
│   └── products/        # BarcodeScanner
├── hooks/               # um hook por recurso da API (useProducts, usePredictions...)
├── lib/                 # api.ts (axios + JWT), auth.ts, utils.ts (formatação)
└── types/
```

## Padrão de uma tela

1. A tela chama um **hook** (`useModelReport`, `useProducts`...).
2. O hook usa **React Query** + `api` (axios), que coloca o token JWT e renova quando expira.
3. A tela monta o layout com os componentes de `components/ui` e os gráficos com **Recharts**.

```tsx
// hooks/usePredictions.ts
export function useModelReport() {
  return useQuery<ModelReport>({
    queryKey: ['predictions', 'model-report'],
    queryFn: fetchModelReport,
  });
}
```

## Identidade visual

| Token | Valor | Uso |
|---|---|---|
| `brand.darkBlue` | `#193D6F` | Cor principal, consumo real nos gráficos |
| `brand.teal` | `#12A89D` | Destaques, previsão do modelo |
| `risk.ok` / `attention` / `critical` | verde / âmbar / vermelho | Status de estoque e alertas |
| Fonte | Inter | Toda a interface |

Os componentes de `components/ui` seguem o padrão shadcn/ui (Tailwind + variáveis CSS em
`globals.css`), com logo do Hospital Beneficente Unimar no menu lateral.

## Comandos

```powershell
cd frontend
npm.cmd install
npm.cmd run dev        # desenvolvimento
npm.cmd run typecheck  # checagem de tipos
npm.cmd test           # testes (Vitest)
npm.cmd run build      # build de produção
```
