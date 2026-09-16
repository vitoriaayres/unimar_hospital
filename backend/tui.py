"""ABHU TUI - Terminal interface for hospital pharmacy management."""

import requests
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, Label
from textual.binding import Binding

API_URL = "http://localhost:8000/api/v1"
_token = None


def api_get(path, params=None):
    global _token
    if not _token:
        return None
    try:
        r = requests.get(
            f"{API_URL}{path}",
            headers={"Authorization": f"Bearer {_token}"},
            params=params,
            timeout=30,
        )
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def do_login():
    global _token
    try:
        r = requests.post(
            f"{API_URL}/login",
            data={"username": "admin@hospital.gov.br", "password": "admin123"},
            timeout=10,
        )
        if r.status_code == 200:
            _token = r.json()["access_token"]
            return True
    except Exception:
        pass
    return False


def _get_items(data):
    """Extract items from paginated or list response."""
    if isinstance(data, dict):
        return data.get("items", [])
    if isinstance(data, list):
        return data
    return []


# --------------- Views ---------------


class DashboardView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Dashboard", id="view-title")
        yield DataTable(id="kpi-table")

    def on_mount(self) -> None:
        table = self.query_one("#kpi-table", DataTable)
        table.add_columns("Indicador", "Valor")
        data = api_get("/dashboard/kpis")
        if data:
            rows = [
                ("Total de SKUs", f"{data['total_skus']:,}"),
                ("Estoque Baixo", str(data["low_stock_count"])),
                ("Risco de Falta", str(data["stockout_risk_count"])),
                ("Vencendo (30d)", str(data["expiring_soon_count"])),
                ("Valor Total Estoque", f"R$ {data['total_inventory_value']:,.2f}"),
                ("MAPE Medio", f"{data['average_mape']:.2f}%"),
                ("Previsoes Hoje", str(data["predictions_generated_today"])),
                ("Alertas Nao Lidos", str(data["alerts_unacknowledged"])),
            ]
            for k, v in rows:
                table.add_row(k, v)


class ProdutosView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Produtos - Risco de Estoque", id="view-title")
        yield DataTable(id="tbl")

    def on_mount(self) -> None:
        table = self.query_one("#tbl", DataTable)
        table.add_columns("#", "Produto", "SKU", "Estoque", "Cons. 7d", "Dias", "Risco")
        data = api_get("/dashboard/stockout-risk", params={"limit": 30})
        if data:
            for i, item in enumerate(data, 1):
                risk = item["risk_level"]
                c = {"critical": "red", "high": "red", "medium": "yellow", "low": "green"}.get(risk, "white")
                table.add_row(
                    str(i),
                    (item["product_name"] or "")[:28],
                    item["product_sku"],
                    f"{item['current_stock']:,}",
                    f"{item['predicted_consumption_7d']:,}",
                    str(item["days_until_stockout"]) if item["days_until_stockout"] else "-",
                    f"[{c}]{risk.upper()}[/]",
                )


class AlertasView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Alertas Ativos", id="view-title")
        yield DataTable(id="tbl")

    def on_mount(self) -> None:
        table = self.query_one("#tbl", DataTable)
        table.add_columns("#", "Tipo", "Severidade", "Mensagem", "Data")
        data = api_get("/alerts", params={"size": 30})
        items = _get_items(data)
        for i, item in enumerate(items, 1):
            sev = item.get("severity", "info")
            c = {"info": "blue", "warning": "yellow", "critical": "red"}.get(sev, "white")
            table.add_row(
                str(i),
                item.get("alert_type", "-"),
                f"[{c}]{sev.upper()}[/]",
                (item.get("message") or "-")[:45],
                (item.get("created_at") or "-")[:10],
            )


class VencimentoView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Lotes Vencendo", id="view-title")
        yield DataTable(id="tbl")

    def on_mount(self) -> None:
        table = self.query_one("#tbl", DataTable)
        table.add_columns("#", "Produto", "Lote", "Qtd", "Vencimento", "Dias")
        data = api_get("/dashboard/expiry-timeline", params={"days_ahead": 90, "limit": 30})
        if data:
            for i, item in enumerate(data, 1):
                days = item["days_until_expiry"]
                style = "red" if days <= 30 else "yellow" if days <= 60 else ""
                table.add_row(
                    str(i),
                    (item["product_name"] or "")[:28],
                    item["batch_number"],
                    f"{item['quantity']:,}",
                    item["expiry_date"],
                    f"[{style}]{days}[/]" if style else str(days),
                )


class EstoqueView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Lotes em Estoque", id="view-title")
        yield DataTable(id="tbl")

    def on_mount(self) -> None:
        table = self.query_one("#tbl", DataTable)
        table.add_columns("#", "Produto", "Lote", "Qtd", "Custo", "Vencimento")
        try:
            import psycopg2
            conn = psycopg2.connect(
                "postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict"
            )
            cur = conn.cursor()
            cur.execute(
                "SELECT p.name, ib.batch_number, ib.quantity, ib.unit_cost, ib.expiry_date "
                "FROM inventory_batches ib JOIN products p ON ib.product_id = p.id "
                "WHERE ib.status = 'available' AND ib.quantity > 0 "
                "ORDER BY ib.expiry_date ASC LIMIT 30"
            )
            for i, (name, batch, qty, cost, expiry) in enumerate(cur.fetchall(), 1):
                table.add_row(
                    str(i),
                    (name or "-")[:28],
                    batch or "-",
                    f"{qty:,}",
                    f"R${float(cost):.2f}",
                    str(expiry),
                )
            conn.close()
        except Exception as e:
            table.add_row("-", f"Erro: {e}", "-", "-", "-", "-")


class ConsumoView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Consumo Historico", id="view-title")
        yield DataTable(id="tbl")

    def on_mount(self) -> None:
        table = self.query_one("#tbl", DataTable)
        table.add_columns("Data", "Quantidade Total")
        try:
            import psycopg2
            conn = psycopg2.connect(
                "postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict"
            )
            cur = conn.cursor()
            cur.execute(
                "SELECT consumption_date, SUM(quantity) FROM consumption "
                "GROUP BY consumption_date ORDER BY consumption_date DESC LIMIT 30"
            )
            rows = cur.fetchall()
            conn.close()
            for date_val, total in reversed(rows):
                table.add_row(str(date_val), f"{int(total):,}")
        except Exception as e:
            table.add_row("Erro", str(e))


class MovimentacoesView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Movimentacoes de Estoque", id="view-title")
        yield DataTable(id="tbl")

    def on_mount(self) -> None:
        table = self.query_one("#tbl", DataTable)
        table.add_columns("#", "Tipo", "Quantidade", "Lote", "Data")
        data = api_get("/inventory/movements", params={"limit": 20})
        items = _get_items(data)
        for i, item in enumerate(items, 1):
            qty = item.get("quantity_change", 0)
            c = "green" if qty > 0 else "red"
            table.add_row(
                str(i),
                item.get("movement_type", "-"),
                f"[{c}]{qty:+,}[/]",
                (item.get("batch_id") or "-")[:12],
                (item.get("created_at") or "-")[:10],
            )


class UsuariosView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Usuarios", id="view-title")
        yield DataTable(id="tbl")

    def on_mount(self) -> None:
        table = self.query_one("#tbl", DataTable)
        table.add_columns("#", "Nome", "E-mail", "Papel", "Ativo")
        data = api_get("/users")
        items = _get_items(data)
        for i, item in enumerate(items, 1):
            ativo = "[green]Sim[/]" if item.get("is_active") else "[red]Nao[/]"
            table.add_row(
                str(i),
                item.get("full_name", "-"),
                item.get("email", "-"),
                item.get("role", "-"),
                ativo,
            )


# --------------- App ---------------


class ABHUApp(App):
    """ABHU - Hospital Pharmacy Management TUI."""

    TITLE = "ABHU"
    SUB_TITLE = "Hospital Pharmacy Management"

    CSS = """
    Screen { background: $surface; }
    #sidebar {
        width: 28;
        background: $panel;
        border-right: solid $primary;
        padding: 1 0;
    }
    #sidebar Label {
        padding: 0 2;
        width: 100%;
    }
    #sidebar .nav-active {
        background: $primary 30%;
        text-style: bold;
    }
    #content {
        width: 1fr;
        padding: 0 2;
    }
    #view-title {
        text-style: bold;
        color: $primary;
        width: 100%;
        margin: 1 0;
    }
    DataTable { height: 1fr; }
    """

    BINDINGS = [
        Binding("1", "go('dashboard')", "Dashboard"),
        Binding("2", "go('produtos')", "Produtos"),
        Binding("3", "go('alertas')", "Alertas"),
        Binding("4", "go('vencimento')", "Vencimento"),
        Binding("5", "go('estoque')", "Estoque"),
        Binding("6", "go('consumo')", "Consumo"),
        Binding("7", "go('movimentacoes')", "Movimentacoes"),
        Binding("8", "go('usuarios')", "Usuarios"),
        Binding("q", "quit", "Sair"),
    ]

    _views = {
        "1": DashboardView,
        "2": ProdutosView,
        "3": AlertasView,
        "4": VencimentoView,
        "5": EstoqueView,
        "6": ConsumoView,
        "7": MovimentacoesView,
        "8": UsuariosView,
    }

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("[bold cyan]ABHU[/]", id="nav-title")
                yield Label("")
                yield Label(" [1] Dashboard", id="nav-1", classes="nav-active")
                yield Label(" [2] Produtos", id="nav-2")
                yield Label(" [3] Alertas", id="nav-3")
                yield Label(" [4] Vencimento", id="nav-4")
                yield Label(" [5] Estoque", id="nav-5")
                yield Label(" [6] Consumo", id="nav-6")
                yield Label(" [7] Movimentacoes", id="nav-7")
                yield Label(" [8] Usuarios", id="nav-8")
                yield Label("")
                yield Label(" [q] Sair", id="nav-q")
            with Vertical(id="content"):
                yield DashboardView(id="view")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = "1-8 navegar  q sair"

    def _highlight(self, key: str):
        for i in "12345678":
            nav = self.query_one(f"#nav-{i}", Label)
            if i == key:
                nav.classes = "nav-active"
            else:
                nav.classes = ""

    def action_go(self, key: str):
        cls = self._views.get(key)
        if not cls:
            return
        content = self.query_one("#content")
        content.remove_children()
        content.mount(cls(id="view"))
        self._highlight(key)


def main():
    do_login()
    app = ABHUApp()
    app.run()


if __name__ == "__main__":
    main()
