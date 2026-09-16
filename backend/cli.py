"""PharmaPredict CLI - Terminal interface for pharmacy management."""

import json
import sys
from pathlib import Path

import click
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

API_URL = "http://localhost:8000/api/v1"
TOKEN_FILE = Path(__file__).parent / ".cli_token"

console = Console()


def get_token():
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return None


def save_token(token):
    TOKEN_FILE.write_text(token)


def clear_token():
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


def headers():
    token = get_token()
    if not token:
        console.print("[red]Nao autenticado. Execute: python cli.py login[/]")
        sys.exit(1)
    return {"Authorization": f"Bearer {token}"}


def api_get(path, params=None):
    try:
        r = requests.get(f"{API_URL}{path}", headers=headers(), params=params, timeout=30)
        if r.status_code == 401:
            console.print("[red]Token expirado. Execute: python cli.py login[/]")
            sys.exit(1)
        if r.status_code >= 400:
            console.print(f"[red]Erro {r.status_code}: {r.text[:200]}[/]")
            sys.exit(1)
        return r.json()
    except requests.exceptions.ConnectionError:
        console.print("[red]Backend offline. Inicie com: uv run uvicorn app.main:app --reload[/]")
        sys.exit(1)


def api_post(path, data=None):
    try:
        r = requests.post(f"{API_URL}{path}", headers=headers(), json=data, timeout=30)
        if r.status_code == 401:
            console.print("[red]Token expirado. Execute: python cli.py login[/]")
            sys.exit(1)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        console.print("[red]Backend offline. Inicie com: uv run uvicorn app.main:app --reload[/]")
        sys.exit(1)


@click.group()
def cli():
    """PharmaPredict - Sistema de gestao de farmacia hospitalar."""
    pass


@cli.command()
def login():
    """Autenticar no sistema."""
    try:
        r = requests.post(
            f"{API_URL}/login",
            data={"username": "admin@hospital.gov.br", "password": "admin123"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        save_token(data["access_token"])
        console.print("[green]Login OK.[/]")
    except requests.exceptions.ConnectionError:
        console.print("[red]Backend offline.[/]")
    except requests.exceptions.HTTPError:
        console.print("[red]Credenciais invalidas.[/]")


@cli.command()
def logout():
    """Encerrar sessao."""
    clear_token()
    console.print("[yellow]Sessao encerrada.[/]")


@cli.command(short_help="Usuario atual")
def who():
    """Mostrar usuario atual."""
    data = api_get("/me")
    table = Table(title="Usuario", box=box.ROUNDED)
    table.add_column("Campo", style="cyan")
    table.add_column("Valor")
    table.add_row("Nome", data["full_name"])
    table.add_row("E-mail", data["email"])
    table.add_row("Papel", data["role"])
    table.add_row("Ativo", "Sim" if data["is_active"] else "Nao")
    table.add_row("Ultimo login", data.get("last_login", "-") or "-")
    console.print(table)


@cli.command(short_help="KPIs gerais")
def d():
    """Dashboard."""
    data = api_get("/dashboard/kpis")

    kpi_table = Table(title="Indicadores", box=box.ROUNDED)
    kpi_table.add_column("Indicador", style="cyan")
    kpi_table.add_column("Valor", justify="right", style="green")

    kpi_table.add_row("Total de SKUs", f"{data['total_skus']:,}")
    kpi_table.add_row("Estoque Baixo", str(data["low_stock_count"]))
    kpi_table.add_row("Risco de Falta", str(data["stockout_risk_count"]))
    kpi_table.add_row("Vencendo (30d)", str(data["expiring_soon_count"]))
    kpi_table.add_row("Valor Total Estoque", f"R$ {data['total_inventory_value']:,.2f}")
    kpi_table.add_row("MAPE Medio", f"{data['average_mape']:.2f}%")
    kpi_table.add_row("Previsoes Hoje", str(data["predictions_generated_today"]))
    kpi_table.add_row("Alertas Nao Lidos", str(data["alerts_unacknowledged"]))

    console.print()
    console.print(kpi_table)
    console.print()


@cli.command(short_help="Produtos com risco")
@click.option("--limite", "-l", default=20, help="Quantidade de itens.")
@click.option("--ordenar-por", "-o", type=click.Choice(["nome", "sku", "estoque", "risco"]), default="risco")
def p(limite, ordenar_por):
    """Listar produtos com nivel de estoque."""
    risks = api_get("/dashboard/stockout-risk", params={"limit": limite})

    table = Table(title=f"Produtos - Risco de Estoque (top {limite})", box=box.ROUNDED)
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Produto", style="cyan", max_width=35)
    table.add_column("SKU", style="dim")
    table.add_column("Estoque", justify="right")
    table.add_column("Consumo 7d", justify="right")
    table.add_column("Dias p/ Falta", justify="right")
    table.add_column("Risco", justify="center")

    risk_colors = {"critical": "red", "high": "red", "medium": "yellow", "low": "green"}

    for i, item in enumerate(risks, 1):
        risk = item["risk_level"]
        color = risk_colors.get(risk, "white")
        table.add_row(
            str(i),
            item["product_name"],
            item["product_sku"],
            f"{item['current_stock']:,}",
            f"{item['predicted_consumption_7d']:,}",
            str(item["days_until_stockout"]) if item["days_until_stockout"] else "-",
            f"[{color}]{risk.upper()}[/]",
        )

    console.print(table)


@cli.command(short_help="Lotes vencendo")
@click.option("--dias", "-d", default=90, help="Dias a frente para vencimento.")
@click.option("--limite", "-l", default=30, help="Quantidade de itens.")
def v(dias, limite):
    """Mostrar timeline de vencimento de lotes."""
    data = api_get("/dashboard/expiry-timeline", params={"days_ahead": dias, "limit": limite})

    table = Table(title=f"Lotes vencendo em {dias} dias", box=box.ROUNDED)
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Produto", style="cyan", max_width=30)
    table.add_column("Lote", style="dim")
    table.add_column("Quantidade", justify="right")
    table.add_column("Vencimento", justify="center")
    table.add_column("Dias Restantes", justify="right")

    for i, item in enumerate(data, 1):
        days = item["days_until_expiry"]
        style = "red" if days <= 30 else "yellow" if days <= 60 else ""
        table.add_row(
            str(i),
            item["product_name"],
            item["batch_number"],
            f"{item['quantity']:,}",
            item["expiry_date"],
            f"[{style}]{days}[/]" if style else str(days),
        )

    console.print(table)


@cli.command(short_help="Consumo historico")
@click.option("--dias", "-d", default=30, help="Quantidade de dias para mostrar.")
@click.option("--departamento", "-dep", default=None, help="Filtrar por departamento.")
def c(dias, departamento):
    """Mostrar tendencias de consumo."""
    import psycopg2
    conn = psycopg2.connect("postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict")
    cur = conn.cursor()

    query = """
        SELECT consumption_date, SUM(quantity) as total
        FROM consumption
        GROUP BY consumption_date
        ORDER BY consumption_date DESC
        LIMIT %s
    """
    cur.execute(query, (dias,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]Nenhum dado de consumo encontrado.[/]")
        return

    rows.reverse()  # Chronological order

    table = Table(title=f"Consumo - Ultimos {len(rows)} dias com dados", box=box.ROUNDED)
    table.add_column("Data", style="cyan")
    table.add_column("Quantidade Total", justify="right", style="green")

    for date_val, total in rows:
        table.add_row(str(date_val), f"{int(total):,}")

    console.print(table)


@cli.command(short_help="Alertas ativos")
@click.option("--limite", "-l", default=30, help="Quantidade de alertas.")
@click.option("--tipo", "-t", type=click.Choice(["shortage_risk", "expiry_risk", "overstock", "todos"]), default="todos")
def a(limite, tipo):
    """Mostrar alertas ativos."""
    raw = api_get("/alerts", params={"size": limite})
    data = raw.get("items", raw) if isinstance(raw, dict) else raw

    if tipo != "todos":
        data = [a for a in data if a.get("alert_type") == tipo]

    table = Table(title=f"Alertas ({len(data)} itens)", box=box.ROUNDED)
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Tipo", style="cyan")
    table.add_column("Severidade", justify="center")
    table.add_column("Mensagem", max_width=50)
    table.add_column("Data", style="dim")

    sev_colors = {"info": "blue", "warning": "yellow", "critical": "red"}

    for i, item in enumerate(data[:limite], 1):
        sev = item.get("severity", "info")
        color = sev_colors.get(sev, "white")
        table.add_row(
            str(i),
            item.get("alert_type", "-"),
            f"[{color}]{sev.upper()}[/]",
            (item.get("message", "-") or "-")[:50],
            (item.get("created_at", "-") or "-")[:19],
        )

    console.print(table)


@cli.command(short_help="Lotes em estoque")
@click.option("--limite", "-l", default=20, help="Quantidade de lotes.")
def e(limite):
    """Mostrar lotes em estoque."""
    import psycopg2
    conn = psycopg2.connect("postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict")
    cur = conn.cursor()
    cur.execute("""
        SELECT p.name, ib.batch_number, ib.quantity, ib.unit_cost, ib.expiry_date, ib.status
        FROM inventory_batches ib
        JOIN products p ON ib.product_id = p.id
        WHERE ib.status = 'available' AND ib.quantity > 0
        ORDER BY ib.expiry_date ASC
        LIMIT %s
    """, (limite,))
    rows = cur.fetchall()
    conn.close()

    table = Table(title="Lotes em Estoque", box=box.ROUNDED)
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Produto", style="cyan", max_width=35)
    table.add_column("Lote", style="dim")
    table.add_column("Quantidade", justify="right")
    table.add_column("Custo Unit.", justify="right")
    table.add_column("Vencimento")
    table.add_column("Status")

    for i, (name, batch, qty, cost, expiry, status) in enumerate(rows, 1):
        table.add_row(
            str(i),
            (name or "-")[:35],
            (batch or "-"),
            f"{qty:,}",
            f"R$ {float(cost):.2f}",
            str(expiry),
            status,
        )

    console.print(table)


@cli.command(short_help="Usuarios")
def u():
    """Listar usuarios do sistema."""
    data = api_get("/users")

    table = Table(title="Usuarios", box=box.ROUNDED)
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Nome", style="cyan")
    table.add_column("E-mail")
    table.add_column("Papel", justify="center")
    table.add_column("Ativo", justify="center")

    for i, item in enumerate(data, 1):
        ativo = "[green]Sim[/]" if item["is_active"] else "[red]Nao[/]"
        table.add_row(
            str(i),
            item.get("full_name", "-"),
            item.get("email", "-"),
            item.get("role", "-"),
            ativo,
        )

    console.print(table)


@cli.command(short_help="Movimentacoes")
@click.option("--limite", "-l", default=20, help="Quantidade de movimentacoes.")
def m(limite):
    """Listar movimentacoes de estoque."""
    data = api_get("/inventory/movements", params={"limit": limite})

    table = Table(title="Movimentacoes de Estoque", box=box.ROUNDED)
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Tipo", style="cyan")
    table.add_column("Quantidade", justify="right")
    table.add_column("Lote", style="dim")
    table.add_column("Data", style="dim")

    for i, item in enumerate(data, 1):
        qty = item.get("quantity_change", 0)
        color = "green" if qty > 0 else "red"
        table.add_row(
            str(i),
            item.get("movement_type", "-"),
            f"[{color}]{qty:+,}[/]",
            item.get("batch_id", "-")[:12],
            (item.get("created_at", "-") or "-")[:19],
        )

    console.print(table)


@cli.command()
@click.argument("produto_id", required=False)
def produto(produto_id):
    """Detalhes de um produto. Passar ID ou deixar vazio para listar resumo."""
    if produto_id:
        data = api_get(f"/{produto_id}")
        panel_content = "\n".join([
            f"[cyan]Nome:[/] {data.get('name', '-')}",
            f"[cyan]SKU:[/] {data.get('sku', '-')}",
            f"[cyan]Categoria:[/] {data.get('category', '-')}",
            f"[cyan]Codigo ATC:[/] {data.get('atc_code', '-')}",
            f"[cyan]Unidade:[/] {data.get('unit', '-')}",
            f"[cyan]Custo Unitario:[/] R$ {data.get('unit_cost', 0):.2f}",
            f"[cyan]Estoque Min:[/] {data.get('min_stock_level', 0)}",
            f"[cyan]Estoque Max:[/] {data.get('max_stock_level', 0)}",
            f"[cyan]Lead Time:[/] {data.get('lead_time_days', 0)} dias",
            f"[cyan]Controlado:[/] {'Sim' if data.get('controlled_substance') else 'Nao'}",
        ])
        console.print(Panel(panel_content, title=data.get("name", "Produto"), box=box.ROUNDED))
    else:
        data = api_get("/summary")
        table = Table(title="Resumo de Estoque", box=box.ROUNDED)
        table.add_column("Produto", style="cyan", max_width=35)
        table.add_column("SKU", style="dim")
        table.add_column("Estoque", justify="right")
        table.add_column("Custo Unit.", justify="right")
        table.add_column("Valor Total", justify="right")

        for item in data[:30]:
            qty = item.get("total_stock", 0)
            cost = item.get("unit_cost", 0)
            table.add_row(
                item.get("name", "-")[:35],
                item.get("sku", "-"),
                f"{qty:,}",
                f"R$ {cost:.2f}",
                f"R$ {qty * cost:,.2f}",
            )
        console.print(table)


@cli.command(short_help="Status do backend")
def status():
    """Verificar status do backend."""
    try:
        r = requests.get("http://localhost:8000/health", timeout=5)
        data = r.json()
        console.print(f"[green]Backend: {data['status']}[/] (v{data['version']}, {data['environment']})")
    except requests.exceptions.ConnectionError:
        console.print("[red]Backend offline.[/]")


if __name__ == "__main__":
    cli()
