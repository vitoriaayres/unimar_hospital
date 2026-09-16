"""ABHU TUI - Terminal interface for hospital pharmacy management."""

import urllib.request
import urllib.error
import json as _json
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, Label, Button, Sparkline
from textual.css.query import NoMatches

API_URL = "http://localhost:8000/api/v1"
_token = None


def api_get(path, params=None):
    global _token
    if not _token:
        return None
    try:
        url = f"{API_URL}{path}"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            url = f"{url}?{qs}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {_token}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return _json.loads(resp.read())
    except Exception:
        return None


def do_login():
    global _token
    try:
        data = "username=admin@hospital.gov.br&password=admin123".encode()
        req = urllib.request.Request(
            f"{API_URL}/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = _json.loads(resp.read())
            _token = result["access_token"]
            return True
    except Exception:
        return False


def _get_items(data):
    if isinstance(data, dict):
        return data.get("items", [])
    if isinstance(data, list):
        return data
    return []


def _bar(value, max_val, width=20):
    if max_val <= 0:
        return ""
    filled = int((value / max_val) * width)
    return "\u2588" * filled + "\u2591" * (width - filled)


def _mini_bar(value, max_val, width=12):
    if max_val <= 0:
        return ""
    filled = int((value / max_val) * width)
    return "[green]" + "\u2588" * filled + "[/]" + "[dim]" + "\u2591" * (width - filled) + "[/]"


# --------------- Views ---------------


class DashboardView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Dashboard", classes="view-title")
        yield DataTable(id="tbl")
        yield Label("", id="sparkline-label")
        yield Sparkline([], id="spark")

    def on_mount(self) -> None:
        try:
            t = self.query_one("#tbl", DataTable)
            t.add_columns("Indicador", "Valor", "")
            d = api_get("/dashboard/kpis")
            if d:
                rows = [
                    ("Total de SKUs", f"{d['total_skus']:,}", _mini_bar(d["total_skus"], 500, 15)),
                    ("Estoque Baixo", str(d["low_stock_count"]), _mini_bar(d["low_stock_count"], 100, 15)),
                    ("Risco de Falta", str(d["stockout_risk_count"]), f"[red]{_mini_bar(d['stockout_risk_count'], 500, 15)}[/]"),
                    ("Vencendo (30d)", str(d["expiring_soon_count"]), f"[yellow]{_mini_bar(d['expiring_soon_count'], 100, 15)}[/]"),
                    ("Valor Estoque", f"R$ {d['total_inventory_value']:,.2f}", ""),
                    ("MAPE Medio", f"{d['average_mape']:.2f}%", ""),
                    ("Previsoes Hoje", str(d["predictions_generated_today"]), ""),
                    ("Alertas Nao Lidos", str(d["alerts_unacknowledged"]), f"[red]{_mini_bar(d['alerts_unacknowledged'], 1000, 15)}[/]"),
                ]
                for k, v, bar in rows:
                    t.add_row(k, v, bar)

                try:
                    import psycopg2
                    conn = psycopg2.connect("postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict")
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT SUM(quantity) FROM consumption "
                        "GROUP BY consumption_date ORDER BY consumption_date DESC LIMIT 30"
                    )
                    vals = [int(row[0]) for row in cur.fetchall()]
                    conn.close()
                    vals.reverse()
                    if vals:
                        spark = self.query_one("#spark", Sparkline)
                        spark.data = vals
                        self.query_one("#sparkline-label", Label).update("  [dim]Consumo diario (ultimos 30 dias)[/]")
                except Exception:
                    pass
        except Exception:
            pass


class ProdutosView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Produtos - Risco de Estoque", classes="view-title")
        yield DataTable(id="tbl")

    def on_mount(self) -> None:
        try:
            t = self.query_one("#tbl", DataTable)
            t.add_columns("#", "Produto", "SKU", "Estoque", "Consumo 7d", "Dias", "Risco", "Nivel")
            d = api_get("/dashboard/stockout-risk", params={"limit": 30})
            if d:
                max_stock = max((item["current_stock"] for item in d), default=1) or 1
                for i, item in enumerate(d, 1):
                    risk = item["risk_level"]
                    c = {"critical": "red", "high": "red", "medium": "yellow", "low": "green"}.get(risk, "white")
                    stock = item["current_stock"]
                    level = f"[{c}]{_bar(stock, max_stock, 12)}[/]"
                    t.add_row(
                        str(i), (item["product_name"] or "")[:25], item["product_sku"],
                        f"{stock:,}", f"{item['predicted_consumption_7d']:,}",
                        str(item["days_until_stockout"]) if item["days_until_stockout"] else "-",
                        f"[{c}]{risk.upper()}[/]", level,
                    )
        except Exception:
            pass


class AlertasView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Alertas Ativos", classes="view-title")
        yield DataTable(id="tbl")
        yield Label("", id="summary")

    def on_mount(self) -> None:
        try:
            t = self.query_one("#tbl", DataTable)
            t.add_columns("#", "Tipo", "Severidade", "Mensagem", "Data")
            d = api_get("/alerts", params={"size": 50})
            items = _get_items(d)

            sev_count = {"critical": 0, "warning": 0, "info": 0}
            for item in items:
                sev = item.get("severity", "info")
                sev_count[sev] = sev_count.get(sev, 0) + 1

            total = len(items)
            self.query_one("#summary", Label).update(
                f"  [red]\u2588 {sev_count.get('critical',0)} Criticos[/]  "
                f"[yellow]\u2588 {sev_count.get('warning',0)} Avisos[/]  "
                f"[blue]\u2588 {sev_count.get('info',0)} Info[/]  "
                f"[dim]Total: {total}[/]"
            )

            for i, item in enumerate(items[:30], 1):
                sev = item.get("severity", "info")
                c = {"info": "blue", "warning": "yellow", "critical": "red"}.get(sev, "white")
                t.add_row(
                    str(i), item.get("alert_type", "-"), f"[{c}]{sev.upper()}[/]",
                    (item.get("message") or "-")[:45], (item.get("created_at") or "-")[:10],
                )
        except Exception:
            pass


class VencimentoView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Lotes Vencendo", classes="view-title")
        yield DataTable(id="tbl")
        yield Label("", id="summary")

    def on_mount(self) -> None:
        try:
            t = self.query_one("#tbl", DataTable)
            t.add_columns("#", "Produto", "Lote", "Qtd", "Vencimento", "Dias", "Urgencia")
            d = api_get("/dashboard/expiry-timeline", params={"days_ahead": 90, "limit": 30})
            if d:
                crit = sum(1 for x in d if x["days_until_expiry"] <= 30)
                warn = sum(1 for x in d if 30 < x["days_until_expiry"] <= 60)
                self.query_one("#summary", Label).update(
                    f"  [red]\u2588 {crit} Criticos (<=30d)[/]  "
                    f"[yellow]\u2588 {warn} Avisos (31-60d)[/]  "
                    f"[dim]Total: {len(d)} lotes[/]"
                )

                for i, item in enumerate(d, 1):
                    days = item["days_until_expiry"]
                    if days <= 30:
                        style, urg = "red", "\u2588\u2588\u2588 CRITICO"
                    elif days <= 60:
                        style, urg = "yellow", "\u2588\u2588\u2591 AVISO"
                    else:
                        style, urg = "green", "\u2588\u2591\u2591 OK"
                    t.add_row(
                        str(i), (item["product_name"] or "")[:25], item["batch_number"],
                        f"{item['quantity']:,}", item["expiry_date"],
                        f"[{style}]{days}[/]", f"[{style}]{urg}[/]",
                    )
        except Exception:
            pass


class EstoqueView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Lotes em Estoque", classes="view-title")
        yield DataTable(id="tbl")

    def on_mount(self) -> None:
        try:
            t = self.query_one("#tbl", DataTable)
            t.add_columns("#", "Produto", "Lote", "Qtd", "Custo", "Vencimento", "Nivel")
            import psycopg2
            conn = psycopg2.connect("postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict")
            cur = conn.cursor()
            cur.execute(
                "SELECT p.name, ib.batch_number, ib.quantity, ib.unit_cost, ib.expiry_date "
                "FROM inventory_batches ib JOIN products p ON ib.product_id = p.id "
                "WHERE ib.status = 'available' AND ib.quantity > 0 "
                "ORDER BY ib.expiry_date ASC LIMIT 30"
            )
            rows = cur.fetchall()
            conn.close()
            max_qty = max((r[2] for r in rows), default=1) or 1
            for i, (name, batch, qty, cost, expiry) in enumerate(rows, 1):
                bar = _mini_bar(qty, max_qty, 10)
                t.add_row(str(i), (name or "-")[:25], batch or "-", f"{qty:,}", f"R${float(cost):.2f}", str(expiry), bar)
        except Exception as e:
            try:
                self.query_one("#tbl", DataTable).add_row("-", str(e)[:50], "-", "-", "-", "-", "-")
            except Exception:
                pass


class ConsumoView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Consumo Historico", classes="view-title")
        yield DataTable(id="tbl")
        yield Sparkline([], id="spark")
        yield Label("", id="stats")

    def on_mount(self) -> None:
        try:
            import psycopg2
            conn = psycopg2.connect("postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict")
            cur = conn.cursor()
            cur.execute(
                "SELECT consumption_date, SUM(quantity) FROM consumption "
                "GROUP BY consumption_date ORDER BY consumption_date DESC LIMIT 60"
            )
            rows = cur.fetchall()
            conn.close()

            vals = [int(r[1]) for r in rows]
            vals.reverse()
            dates = [str(r[0]) for r in rows]
            dates.reverse()

            if vals:
                spark = self.query_one("#spark", Sparkline)
                spark.data = vals

                avg = sum(vals) / len(vals)
                mn, mx = min(vals), max(vals)
                self.query_one("#stats", Label).update(
                    f"  [dim]Media: {int(avg):,} | Min: {mn:,} | Max: {mx:,} | Dias: {len(vals)}[/]"
                )

                t = self.query_one("#tbl", DataTable)
                t.add_columns("Data", "Quantidade", "Grafico")
                max_val = max(vals)
                display = list(zip(dates, vals))[-20:]
                for date_val, total in display:
                    bar = _mini_bar(total, max_val, 25)
                    t.add_row(str(date_val), f"{total:,}", bar)
        except Exception:
            pass


class MovimentacoesView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Movimentacoes de Estoque", classes="view-title")
        yield DataTable(id="tbl")
        yield Label("", id="summary")

    def on_mount(self) -> None:
        try:
            t = self.query_one("#tbl", DataTable)
            t.add_columns("#", "Tipo", "Quantidade", "Lote", "Data")
            d = api_get("/inventory/movements", params={"limit": 30})
            items = _get_items(d)

            entradas = sum(1 for x in items if x.get("movement_type") == "in")
            saidas = sum(1 for x in items if x.get("movement_type") == "out")
            self.query_one("#summary", Label).update(
                f"  [green]\u2588 {entradas} Entradas[/]  "
                f"[red]\u2588 {saidas} Saidas[/]  "
                f"[dim]Total: {len(items)}[/]"
            )

            for i, item in enumerate(items, 1):
                qty = item.get("quantity_change", 0)
                c = "green" if qty > 0 else "red"
                t.add_row(
                    str(i), item.get("movement_type", "-"), f"[{c}]{qty:+,}[/]",
                    (item.get("batch_id") or "-")[:12], (item.get("created_at") or "-")[:10],
                )
        except Exception:
            pass


class UsuariosView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  Usuarios", classes="view-title")
        yield DataTable(id="tbl")

    def on_mount(self) -> None:
        try:
            t = self.query_one("#tbl", DataTable)
            t.add_columns("#", "Nome", "E-mail", "Papel", "Ativo")
            d = api_get("/users")
            items = _get_items(d)
            for i, item in enumerate(items, 1):
                ativo = "[green]Sim[/]" if item.get("is_active") else "[red]Nao[/]"
                t.add_row(str(i), item.get("full_name", "-"), item.get("email", "-"), item.get("role", "-"), ativo)
        except Exception:
            pass


# --------------- App ---------------


VIEW_MAP = {
    "1": ("Dashboard", DashboardView),
    "2": ("Produtos", ProdutosView),
    "3": ("Alertas", AlertasView),
    "4": ("Vencimento", VencimentoView),
    "5": ("Estoque", EstoqueView),
    "6": ("Consumo", ConsumoView),
    "7": ("Movimentacoes", MovimentacoesView),
    "8": ("Usuarios", UsuariosView),
}


class ABHUApp(App):
    TITLE = "ABHU"
    SUB_TITLE = "clique para navegar"

    CSS = """
    Screen { background: $surface; }
    #sidebar {
        width: 28;
        background: $panel;
        border-right: solid $primary;
        padding: 1 0;
    }
    #sidebar Label { padding: 0 2; width: 100%; }
    #sidebar Button {
        width: 100%;
        margin: 0;
        min-height: 1;
        background: transparent;
        color: $text;
        border: none;
        text-align: left;
    }
    #sidebar Button:hover { background: $primary 20%; }
    #sidebar Button.-active { background: $primary 40%; text-style: bold; }
    #content { width: 1fr; }
    .view-title { text-style: bold; color: $primary; width: 100%; margin: 1 0 0 2; }
    DataTable { height: 1fr; }
    Sparkline { height: 3; margin: 0 2; color: $primary; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("[bold cyan]ABHU[/]")
                yield Label("[dim]v1.0[/]")
                yield Label("")
                yield Button("1 Dashboard", id="btn-1", classes="-active")
                yield Button("2 Produtos", id="btn-2")
                yield Button("3 Alertas", id="btn-3")
                yield Button("4 Vencimento", id="btn-4")
                yield Button("5 Estoque", id="btn-5")
                yield Button("6 Consumo", id="btn-6")
                yield Button("7 Movimentacoes", id="btn-7")
                yield Button("8 Usuarios", id="btn-8")
                yield Label("")
                yield Button("q Sair", id="btn-q")
            with Vertical(id="content"):
                yield DashboardView(id="v-1")
                yield ProdutosView(id="v-2", classes="hidden")
                yield AlertasView(id="v-3", classes="hidden")
                yield VencimentoView(id="v-4", classes="hidden")
                yield EstoqueView(id="v-5", classes="hidden")
                yield ConsumoView(id="v-6", classes="hidden")
                yield MovimentacoesView(id="v-7", classes="hidden")
                yield UsuariosView(id="v-8", classes="hidden")
        yield Footer()

    def _show_view(self, key: str):
        for k in VIEW_MAP:
            try:
                self.query_one(f"#v-{k}").display = False
            except NoMatches:
                pass
        try:
            self.query_one(f"#v-{key}").display = True
        except NoMatches:
            pass
        for k in "12345678":
            try:
                btn = self.query_one(f"#btn-{k}", Button)
                btn.classes = "-active" if k == key else ""
            except NoMatches:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-q":
            self.exit()
            return
        key = btn_id.replace("btn-", "")
        if key in VIEW_MAP:
            self._show_view(key)


def main():
    do_login()
    app = ABHUApp()
    app.run()


if __name__ == "__main__":
    main()
