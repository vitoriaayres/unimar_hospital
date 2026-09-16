# ABHU - Guia de Uso

## O que e

ABHU e um sistema de gestao de farmacia hospitalar que roda no terminal (TUI).
Mostra dados de estoque, alertas, vencimentos, consumo e movimentacoes de medicamentos.

---

## Pre-requisitos

- Python 3.13+
- uv (gerenciador de pacotes Python)
- Docker Desktop rodando (PostgreSQL e Redis)

---

## Instalacao

```bash
# 1. Clonar o repositorio
git clone https://github.com/vitoriaayres/unimar_hospital.git
cd unimar_hospital

# 2. Entrar no branch com filtros
git checkout feat/filtros

# 3. Subir o banco de dados
docker compose up -d

# 4. Instalar dependencias do backend
cd backend
uv sync

# 5. Rodar as migracoes e popular dados
uv run python ml/full_reset.py

# 6. Regenerar dados realistas (opcional)
uv run python ml/regenerate_data.py

# 7. Iniciar o backend
uv run uvicorn app.main:app --reload
```

---

## Iniciar a TUI

Em outro terminal (ou depois que o backend estiver rodando):

```bash
cd backend
.\pp
```

Ou diretamente:

```bash
uv run python tui.py
```

---

## Navegacao

A interface tem dois paineis:

- **Esquerda**: Menu com botoes clicaveis
- **Direita**: Conteudo da tela selecionada

### Telas disponiveis

| Tecla | Tela             | O que mostra                                    |
|-------|------------------|-------------------------------------------------|
| 1     | Dashboard        | KPIs gerais, grafico de consumo                 |
| 2     | Produtos         | Produtos com risco de estoque, barras visuais   |
| 3     | Alertas          | Alertas ativos filtrados por severidade         |
| 4     | Vencimento       | Lotes proximos do vencimento com urgencia       |
| 5     | Estoque          | Lotes em estoque com status e nivel             |
| 6     | Consumo          | Historico de consumo com sparkline              |
| 7     | Movimentacoes    | Entradas e saidas de estoque                    |
| 8     | Usuarios         | Lista de usuarios do sistema                    |
| q     | Sair             | Fecha a aplicacao                               |

### Como navegar

- **Clique** nos botoes do menu lateral para trocar de tela
- Use as **setas do teclado** para navegar entre botoes
- Pressione **Tab** para mudar entre os botoes de filtro e a tabela

---

## Filtros

Cada tela tem filtros proprios:

### Produtos (tela 2)
- **Botoes de risco**: Todos / Critical / High / Medium / Low
- **Campo de busca**: digite o nome ou SKU do produto

### Alertas (tela 3)
- **Botoes de severidade**: Todos / Critical / Warning / Info
- **Campo de busca**: digite parte da mensagem do alerta

### Vencimento (tela 4)
- **Botoes de urgencia**: Todos / Critico <=30d / Aviso 31-60d / OK >60d
- **Campo de busca**: digite o nome do produto

### Estoque (tela 5)
- **Botoes de status**: Todos / Disponivel / Expirado
- **Campo de busca**: digite o nome do produto

### Consumo (tela 6)
- **Campo de busca**: digite uma data (ex: 2024-03)

### Movimentacoes (tela 7)
- **Botoes de tipo**: Todas / Entrada / Saida
- **Campo de busca**: digite o tipo ou ID do lote

---

## Painel de Detalhes

Nas telas 2, 3, 4, 5 e 7, clique em qualquer linha da tabela para ver os detalhes completos na parte inferior.

Exemplo: ao clicar em um produto, aparece:
```
Nome do Produto (SKU-001)
Estoque atual: 150  |  Consumo 7d: 200  |  Dias p/ falta: 5
Risco: CRITICAL
```

---

## Dados

### Distribuicao realista

Os dados sinteticos tem distribuicao balanceada:

- **Estoque**: 15% critico, 20% baixo, 40% normal, 25% alto
- **Vencimento**: 5% expirado, 10% ate 30d, 15% 31-60d, 20% 61-90d, 25% 91-180d, 25% 181-365d
- **Alertas**: ~158 com mix de severidades
- **Consumo**: 7315 registros em 2024

### Regenerar dados

Se quiser dados novos:

```bash
uv run python ml/regenerate_data.py
```

---

## Credenciais

- **Email**: admin@hospital.gov.br
- **Senha**: admin123
- Login automatico (nao precisa digitar)

---

## API

O backend roda em http://localhost:8000. Endpoints principais:

- `POST /api/v1/login` - Autenticacao
- `GET /api/v1/dashboard/kpis` - KPIs gerais
- `GET /api/v1/dashboard/stockout-risk` - Risco de falta
- `GET /api/v1/dashboard/expiry-timeline` - Vencimento
- `GET /api/v1/dashboard/consumption-trends` - Tendencias
- `GET /api/v1/alerts` - Alertas
- `GET /api/v1/users` - Usuarios
- `GET /api/v1/inventory/movements` - Movimentacoes

Documentacao interativa: http://localhost:8000/docs

---

## Branches

| Branch     | Descricao                          |
|------------|-------------------------------------|
| master     | Versao original (sem filtros)       |
| feat/filtros | Filtros, detalhes, dados realistas |

---

## Solucao de Problemas

### "Backend offline"
O backend nao esta rodando. Execute:
```bash
uv run uvicorn app.main:app --reload
```

### "Credenciais invalidas"
Execute o login primeiro:
```bash
uv run python cli.py login
```

### Banco de dados vazio
Execute o reset:
```bash
uv run python ml/full_reset.py
```

### TUI nao abre
Verifique se o textual esta instalado:
```bash
uv sync
```
