# Frontend

Next.js 14 (App Router) em `frontend/`. Roda em **http://localhost:3000**.

## Telas

| Tela | Rota | O que faz |
|---|---|---|
| Login | `/login` | Entrada no sistema (única tela sem menu) |
| Dashboard | `/` | Indicadores, consumo diário, maior risco de falta, vencimentos, alertas críticos |
| Produtos | `/products` | Busca, filtro por categoria, cadastro e edição |
| Ler código | `/products/scan` | Câmera ou digitação do código de barras |
| Detalhe do produto | `/products/{id}` | Consumo real + previsão, cobertura do estoque, lotes, consumo por setor, movimentações |
| Estoque | `/inventory` | Lotes por validade (FEFO), filtros de status e validade, linha do tempo |
| Previsões | `/predictions` | Previsão dos próximos 7 dias por produto |
| Modelo | `/model` | Desempenho do modelo × método atual |
| Alertas | `/alerts` | Lista, reconhecimento (um ou vários) e regras |
| Relatórios | `/reports` | Planilhas CSV: estoque, risco de falta, vencimentos, previsões, alertas |
| Usuários | `/users` | Perfis e acesso (só administrador) |
| Configurações | `/settings` | Perfil, troca de senha, dados do modelo |

Estoque, Previsões e Alertas também exportam CSV do filtro atual. Os CSV usam `;` e acentos
compatíveis com o Excel em português.

## Organização do código

```
frontend/src/
├── app/                 # uma pasta por tela (rota)
│   ├── layout.tsx       # HTML raiz, fonte, providers e AppShell
│   └── providers.tsx    # React Query
├── components/
│   ├── layout/          # AppShell, DashboardLayout, Sidebar, Header
│   ├── ui/              # Button, Card, Table, Badge, Select, StatCard, SearchInput, Pagination...
│   ├── charts/          # ForecastChart e BarChart (Recharts)
│   ├── dashboard/       # conteúdo do Dashboard
│   └── products/        # BarcodeScanner
├── hooks/               # um hook por recurso da API + useUrlParams
├── lib/                 # api.ts (axios + JWT), auth.ts, utils.ts (formatação e CSV)
└── types/
```

## Login e layout

- `AppShell` (no `layout.tsx` raiz) envolve todas as telas, menos `/login`, no `DashboardLayout`.
- O `DashboardLayout` confirma o login antes de mostrar a tela (senão manda para `/login`) e
  disponibiliza o usuário com `useCurrentUser()`.
- O menu lateral esconde **Usuários** de quem não é administrador; o backend também bloqueia.

## Padrão de uma tela

1. Filtros e página ficam **na URL** (`useUrlParams`), então voltar no navegador e links como
   `/alerts?acknowledged=false` funcionam.
2. A tela chama um **hook** (`useProducts`, `useAlerts`...), que usa **React Query** + `api` (axios).
   O `api` coloca o token JWT e renova quando expira.
3. A tela monta o layout com os componentes de `components/ui` e os gráficos com **Recharts**.

```tsx
const url = useUrlParams();
const { data } = useProducts({ page: url.page, search: url.get('search') || undefined });

<SearchInput value={url.get('search')} onChange={(v) => url.set({ search: v })} />
<Pagination page={data.page} pages={data.pages} total={data.total} label="produtos"
  onPageChange={(p) => url.set({ page: p }, { resetPage: false })} />
```

Chamadas à API seguem o formato do axios: `api.get(url, { params })`.

## Identidade visual

| Token | Valor | Uso |
|---|---|---|
| `brand.darkBlue` | `#193D6F` | Cor principal, consumo real nos gráficos |
| `brand.teal` | `#12A89D` | Destaques, previsão do modelo |
| `risk.ok` / `attention` / `critical` | verde / âmbar / vermelho | Status de estoque e alertas |
| Fonte | Inter | Toda a interface |

Os componentes de `components/ui` seguem o padrão shadcn/ui (Tailwind + variáveis CSS em
`globals.css`), com o logo do Hospital Beneficente Unimar no menu lateral. Os indicadores usam o
`StatCard`, igual em todas as telas.

## Comandos

```powershell
cd frontend
npm.cmd install
npm.cmd run dev        # desenvolvimento
npm.cmd run typecheck  # checagem de tipos
npm.cmd test           # testes (Vitest)
npm.cmd run build      # build de produção
```
