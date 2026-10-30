# Testes e qualidade

## Como rodar

```powershell
# Backend (a partir de backend/)
uv run pytest              # testes + cobertura (mínimo 65%)
uv run ruff check app      # lint

# Frontend (a partir de frontend/)
npm.cmd test               # testes (Vitest)
npm.cmd run typecheck      # checagem de tipos (TypeScript)
```

Os testes do backend usam um banco SQLite em memória (`tests/conftest.py`), então **não precisam
do Postgres no ar**.

## O que é testado

### Backend: 22 testes, cobertura de ~70%

| Arquivo | Cobre |
|---|---|
| `tests/unit/test_auth.py` | Login (certo, senha errada, usuário inexistente), perfil `/me`, acesso sem token, renovação do token |
| `tests/unit/test_products.py` | Cadastro, SKU duplicado, listagem com filtros, detalhe, produto inexistente, edição e exclusão |
| `tests/unit/test_dashboard.py` | KPIs com WAPE, lista de modelos, previsões paginadas, relatório da tela Modelo (com e sem arquivo) |
| `tests/unit/test_health.py` | `/health` e `/metrics` |

### Frontend: 19 testes

`tests/unit/components.test.tsx` cobre os componentes básicos (`Button`, `Input`, `Badge`) e as
funções de formatação em português (moeda, número, data, cores de severidade e status).

### Modelo de ML

A qualidade do modelo é medida no período de teste, separado por data, e comparada com o método
atual. Os resultados estão em [05-pipeline-ml.md](05-pipeline-ml.md#resultados). O script
`ml/build_report.py` recalcula o erro a partir do modelo salvo e confere com o do treino.

## Verificação manual

Antes de cada apresentação, com o sistema no ar:

1. Login com `admin@hospital.gov.br` / `admin123`; **Sair** volta ao login.
2. **Dashboard:** os indicadores carregam; **Reconhecer** um alerta crítico some da lista.
3. **Produtos:** busca e filtro de categoria; **Ler código** com `7890000000017` encontra o produto.
4. **Detalhe do produto:** gráfico com consumo real e previsão; abas de lotes e movimentações.
5. **Estoque, Previsões e Alertas:** filtros, paginação e **Exportar CSV**.
6. **Relatórios:** baixar uma planilha e abrir no Excel.
7. **Usuários** (admin) e **Configurações:** trocar perfil de um usuário e alterar a senha.
8. Janela estreita (celular): o menu abre pelo botão e fecha ao escolher uma tela.

## Lacunas conhecidas

- As telas novas (Usuários, Configurações, Relatórios) e os filtros novos da API (busca em lotes e
  previsões, filtros por produto, regras de alerta) ainda **não têm testes automáticos**.
- O ESLint não está configurado no frontend (`npm run lint` pede configuração).
- O CI em `.github/workflows/ci.yml` só dispara nas branches `main` e `develop`; a branch
  principal do repositório é `master`, então ele não roda hoje.
