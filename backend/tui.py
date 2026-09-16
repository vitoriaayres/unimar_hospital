"""ABHU TUI - Terminal interface for hospital pharmacy management."""

import urllib.request
import urllib.error
import json as _json
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, DataTable, Label, Button, Sparkline, Input, Rule
from textual.css.query import NoMatches
from textual import on

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
    _all_data = []
    _filter_risk = "todos"
    _selected_idx = None

    def compose(self) -> ComposeResult:
        yield Label("  Produtos - Risco de Estoque", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar produto...", id="search", classes="filter-input")
            yield Button("Todos", id="fb-todos", classes="filter-btn -active")
            yield Button("Critical", id="fb-critical", classes="filter-btn")
            yield Button("High", id="fb-high", classes="filter-btn")
            yield Button("Medium", id="fb-medium", classes="filter-btn")
            yield Button("Low", id="fb-low", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("[dim]  Clique em uma linha para ver detalhes[/]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        self._load_data()

    def _load_data(self):
        try:
            self.__class__._all_data = api_get("/dashboard/stockout-risk", params={"limit": 100}) or []
            self._render_table(self._all_data)
        except Exception:
            pass

    def _render_table(self, data):
        try:
            t = self.query_one("#tbl", DataTable)
            t.clear()
            if not data:
                self.query_one("#detail", Label).update("  [dim]Nenhum resultado[/]")
                return
            t.add_columns("#", "Produto", "SKU", "Estoque", "Dias", "Risco")
            max_stock = max((item["current_stock"] for item in data), default=1) or 1
            for i, item in enumerate(data, 1):
                risk = item["risk_level"]
                c = {"critical": "red", "high": "red", "medium": "yellow", "low": "green"}.get(risk, "white")
                t.add_row(
                    str(i),
                    item.get("product_name") or "",
                    item.get("product_sku") or "",
                    str(item.get("current_stock", 0)),
                    str(item.get("days_until_stockout") or "-"),
                    f"[{c}]{risk.upper()}[/]",
                )
        except Exception:
            pass

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        risk = self._filter_risk
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("product_name") or "").lower() or search in (x.get("product_sku") or "").lower()]
        if risk and risk != "todos":
            filtered = [x for x in filtered if x.get("risk_level") == risk]
        self._render_table(filtered)

    @on(DataTable.RowSelected, "#tbl")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        row_idx = event.row_index
        if row_idx is not None and row_idx < len(self._all_data):
            item = self._all_data[row_idx]
            detail = (
                f"  [bold]{item.get('product_name', '-')}[/] ({item.get('product_sku', '-')})\n"
                f"  Estoque atual: [bold]{item.get('current_stock', 0):,}[/]  |  "
                f"Consumo 7d: {item.get('predicted_consumption_7d', 0):,}  |  "
                f"Dias p/ falta: [bold]{item.get('days_until_stockout', '-')}[/]\n"
                f"  Risco: [bold]{item.get('risk_level', '-').upper()}[/]"
            )
            self.query_one("#detail", Label).update(detail)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("fb-"):
            risk = btn_id.replace("fb-", "")
            self._filter_risk = risk
            for btn in self.query(".filter-btn"):
                btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class AlertasView(Static):
    _all_data = []
    _filtered_data = []
    _filter_sev = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  Alertas Ativos", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar mensagem...", id="search", classes="filter-input")
        with Horizontal(id="sev-filters"):
            yield Button("Todos", id="fb-sev-todos", classes="filter-btn -active")
            yield Button("Critical", id="fb-sev-critical", classes="filter-btn")
            yield Button("Warning", id="fb-sev-warning", classes="filter-btn")
            yield Button("Info", id="fb-sev-info", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("", id="summary")
        yield Label("[dim]  Clique em uma linha para ver detalhes[/]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        self._load_data()

    def _load_data(self):
        try:
            d = api_get("/alerts", params={"size": 100})
            self.__class__._all_data = _get_items(d)
            self._apply_filters()
        except Exception:
            pass

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        sev = self._filter_sev
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("message") or "").lower()]
        if sev and sev != "todos":
            filtered = [x for x in filtered if x.get("severity") == sev]
        self.__class__._filtered_data = filtered

        sev_count = {"critical": 0, "warning": 0, "info": 0}
        for item in filtered:
            sev_count[item.get("severity", "info")] = sev_count.get(item.get("severity", "info"), 0) + 1
        try:
            self.query_one("#summary", Label).update(
                f"  [red]\u2588 {sev_count.get('critical',0)} Criticos[/]  "
                f"[yellow]\u2588 {sev_count.get('warning',0)} Avisos[/]  "
                f"[blue]\u2588 {sev_count.get('info',0)} Info[/]  "
                f"[dim]Filtrados: {len(filtered)}/{len(self._all_data)}[/]"
            )
        except Exception:
            pass

        t = self.query_one("#tbl", DataTable)
        t.clear()
        t.add_columns("#", "Tipo", "Severidade", "Mensagem", "Data")
        for i, item in enumerate(filtered[:30], 1):
            sev = item.get("severity", "info")
            c = {"info": "blue", "warning": "yellow", "critical": "red"}.get(sev, "white")
            t.add_row(
                str(i),
                item.get("alert_type") or "-",
                f"[{c}]{sev.upper()}[/]",
                item.get("message") or "-",
                (item.get("created_at") or "-")[:10],
            )

    @on(DataTable.RowSelected, "#tbl")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        row_idx = event.row_index
        if row_idx is not None and row_idx < len(self._filtered_data):
            item = self._filtered_data[row_idx]
            detail = (
                f"  [bold]Tipo:[/] {item.get('alert_type', '-')}  |  "
                f"[bold]Severidade:[/] {item.get('severity', '-').upper()}\n"
                f"  [bold]Mensagem:[/] {item.get('message', '-')}\n"
                f"  [bold]Produto ID:[/] {item.get('product_id', '-')}\n"
                f"  [bold]Criado em:[/] {item.get('created_at', '-')}\n"
                f"  [bold]Reconhecido:[/] {'Sim' if item.get('acknowledged') else 'Nao'}"
            )
            self.query_one("#detail", Label).update(detail)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("fb-sev-"):
            sev = btn_id.replace("fb-sev-", "")
            self._filter_sev = sev
            for btn in self.query("#sev-filters .filter-btn"):
                btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class VencimentoView(Static):
    _all_data = []
    _filtered_data = []
    _filter_urg = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  Lotes Vencendo", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar produto...", id="search", classes="filter-input")
        with Horizontal(id="urg-filters"):
            yield Button("Todos", id="fb-urg-todos", classes="filter-btn -active")
            yield Button("Critico <=30d", id="fb-urg-crit", classes="filter-btn")
            yield Button("Aviso 31-60d", id="fb-urg-warn", classes="filter-btn")
            yield Button("OK >60d", id="fb-urg-ok", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("", id="summary")
        yield Label("[dim]  Clique em uma linha para ver detalhes[/]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        self._load_data()

    def _load_data(self):
        try:
            self.__class__._all_data = api_get("/dashboard/expiry-timeline", params={"days_ahead": 90, "limit": 100}) or []
            self._apply_filters()
        except Exception:
            pass

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        urg = self._filter_urg
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("product_name") or "").lower()]
        if urg and urg != "todos":
            if urg == "crit":
                filtered = [x for x in filtered if x["days_until_expiry"] <= 30]
            elif urg == "warn":
                filtered = [x for x in filtered if 30 < x["days_until_expiry"] <= 60]
            elif urg == "ok":
                filtered = [x for x in filtered if x["days_until_expiry"] > 60]
        self.__class__._filtered_data = filtered

        crit = sum(1 for x in filtered if x["days_until_expiry"] <= 30)
        warn = sum(1 for x in filtered if 30 < x["days_until_expiry"] <= 60)
        try:
            self.query_one("#summary", Label).update(
                f"  [red]\u2588 {crit} Criticos[/]  "
                f"[yellow]\u2588 {warn} Avisos[/]  "
                f"[dim]Filtrados: {len(filtered)}/{len(self._all_data)}[/]"
            )
        except Exception:
            pass

        t = self.query_one("#tbl", DataTable)
        t.clear()
        t.add_columns("#", "Produto", "Lote", "Qtd", "Vencimento", "Dias", "Urgencia")
        for i, item in enumerate(filtered[:30], 1):
            days = item["days_until_expiry"]
            if days <= 30:
                style, urg_str = "red", "\u2588\u2588\u2588 CRITICO"
            elif days <= 60:
                style, urg_str = "yellow", "\u2588\u2588\u2591 AVISO"
            else:
                style, urg_str = "green", "\u2588\u2591\u2591 OK"
            t.add_row(
                str(i),
                item.get("product_name") or "",
                item.get("batch_number") or "",
                str(item.get("quantity", 0)),
                item.get("expiry_date") or "",
                f"[{style}]{days}[/]",
                f"[{style}]{urg_str}[/]",
            )

    @on(DataTable.RowSelected, "#tbl")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        row_idx = event.row_index
        if row_idx is not None and row_idx < len(self._filtered_data):
            item = self._filtered_data[row_idx]
            days = item.get("days_until_expiry", 0)
            if days <= 30:
                urg = "[red]CRITICO[/]"
            elif days <= 60:
                urg = "[yellow]AVISO[/]"
            else:
                urg = "[green]OK[/]"
            detail = (
                f"  [bold]{item.get('product_name', '-')}[/]\n"
                f"  Lote: {item.get('batch_number', '-')}  |  "
                f"Quantidade: {item.get('quantity', 0):,}  |  "
                f"Dias restantes: [bold]{days}[/] ({urg})\n"
                f"  Data de vencimento: {item.get('expiry_date', '-')}"
            )
            self.query_one("#detail", Label).update(detail)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("fb-urg-"):
            urg = btn_id.replace("fb-urg-", "")
            self._filter_urg = urg
            for btn in self.query("#urg-filters .filter-btn"):
                btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class EstoqueView(Static):
    _all_data = []
    _filtered_data = []
    _filter_status = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  Lotes em Estoque", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar produto...", id="search", classes="filter-input")
        with Horizontal(id="status-filters"):
            yield Button("Todos", id="fb-st-todos", classes="filter-btn -active")
            yield Button("Disponivel", id="fb-st-available", classes="filter-btn")
            yield Button("Expirado", id="fb-st-expired", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("[dim]  Clique em uma linha para ver detalhes[/]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        try:
            import psycopg2
            conn = psycopg2.connect("postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict")
            cur = conn.cursor()
            cur.execute(
                "SELECT p.name, ib.batch_number, ib.quantity, ib.unit_cost, ib.expiry_date, ib.status "
                "FROM inventory_batches ib JOIN products p ON ib.product_id = p.id "
                "ORDER BY ib.expiry_date ASC LIMIT 100"
            )
            self.__class__._all_data = [
                {"name": r[0], "batch": r[1], "qty": r[2], "cost": r[3], "expiry": str(r[4]), "status": r[5]}
                for r in cur.fetchall()
            ]
            conn.close()
            self._apply_filters()
        except Exception:
            pass

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        status = self._filter_status
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("name") or "").lower()]
        if status and status != "todos":
            filtered = [x for x in filtered if x.get("status") == status]
        self.__class__._filtered_data = filtered

        t = self.query_one("#tbl", DataTable)
        t.clear()
        t.add_columns("#", "Produto", "Lote", "Qtd", "Custo", "Vencimento", "Status")
        for i, item in enumerate(filtered[:30], 1):
            status_color = "green" if item["status"] == "available" else "red"
            t.add_row(
                str(i),
                item.get("name") or "-",
                item.get("batch") or "-",
                str(item.get("qty", 0)),
                f"R${float(item['cost']):.2f}",
                item.get("expiry") or "-",
                f"[{status_color}]{item.get('status', '-')}[/]",
            )

    @on(DataTable.RowSelected, "#tbl")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        row_idx = event.row_index
        if row_idx is not None and row_idx < len(self._filtered_data):
            item = self._filtered_data[row_idx]
            detail = (
                f"  [bold]{item.get('name', '-')}[/]\n"
                f"  Lote: {item.get('batch', '-')}  |  "
                f"Quantidade: {item.get('qty', 0):,}  |  "
                f"Custo unit.: R${float(item['cost']):.2f}\n"
                f"  Vencimento: {item.get('expiry', '-')}  |  "
                f"Status: {item.get('status', '-')}"
            )
            self.query_one("#detail", Label).update(detail)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("fb-st-"):
            status = btn_id.replace("fb-st-", "")
            self._filter_status = status
            for btn in self.query("#status-filters .filter-btn"):
                btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class ConsumoView(Static):
    _all_data = []

    def compose(self) -> ComposeResult:
        yield Label("  Consumo Historico", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar data (ex: 2024-03)...", id="search", classes="filter-input")
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
            self.__class__._all_data = [{"date": str(r[0]), "qty": int(r[1])} for r in rows]
            self._apply_filters()
        except Exception:
            pass

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in x["date"]]

        vals = [x["qty"] for x in reversed(filtered)]
        dates = [x["date"] for x in reversed(filtered)]

        if vals:
            try:
                spark = self.query_one("#spark", Sparkline)
                spark.data = vals
            except Exception:
                pass
            avg = sum(vals) / len(vals)
            mn, mx = min(vals), max(vals)
            try:
                self.query_one("#stats", Label).update(
                    f"  [dim]Media: {int(avg):,} | Min: {mn:,} | Max: {mx:,} | Dias: {len(vals)}[/]"
                )
            except Exception:
                pass

        t = self.query_one("#tbl", DataTable)
        t.clear()
        t.add_columns("Data", "Quantidade", "Grafico")
        max_val = max(vals) if vals else 1
        display = list(zip(dates, vals))[-20:]
        for date_val, total in display:
            bar = _mini_bar(total, max_val, 25)
            t.add_row(str(date_val), f"{total:,}", bar)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()


class MovimentacoesView(Static):
    _all_data = []
    _filtered_data = []
    _filter_type = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  Movimentacoes de Estoque", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar...", id="search", classes="filter-input")
        with Horizontal(id="type-filters"):
            yield Button("Todas", id="fb-mt-todos", classes="filter-btn -active")
            yield Button("Entrada", id="fb-mt-in", classes="filter-btn")
            yield Button("Saida", id="fb-mt-out", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("", id="summary")
        yield Label("[dim]  Clique em uma linha para ver detalhes[/]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        try:
            d = api_get("/inventory/movements", params={"limit": 100})
            self.__class__._all_data = _get_items(d)
            self._apply_filters()
        except Exception:
            pass

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        mtype = self._filter_type
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("movement_type") or "").lower() or search in (x.get("batch_id") or "").lower()]
        if mtype and mtype != "todos":
            filtered = [x for x in filtered if x.get("movement_type") == mtype]
        self.__class__._filtered_data = filtered

        entradas = sum(1 for x in filtered if x.get("movement_type") == "in")
        saidas = sum(1 for x in filtered if x.get("movement_type") == "out")
        try:
            self.query_one("#summary", Label).update(
                f"  [green]\u2588 {entradas} Entradas[/]  "
                f"[red]\u2588 {saidas} Saidas[/]  "
                f"[dim]Filtrados: {len(filtered)}/{len(self._all_data)}[/]"
            )
        except Exception:
            pass

        t = self.query_one("#tbl", DataTable)
        t.clear()
        t.add_columns("#", "Tipo", "Quantidade", "Lote", "Data")
        for i, item in enumerate(filtered[:30], 1):
            qty = item.get("quantity_change", 0)
            c = "green" if qty > 0 else "red"
            t.add_row(
                str(i),
                item.get("movement_type") or "-",
                f"[{c}]{qty:+,}[/]",
                item.get("batch_id") or "-",
                (item.get("created_at") or "-")[:10],
            )

    @on(DataTable.RowSelected, "#tbl")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        row_idx = event.row_index
        if row_idx is not None and row_idx < len(self._filtered_data):
            item = self._filtered_data[row_idx]
            qty = item.get("quantity_change", 0)
            c = "green" if qty > 0 else "red"
            detail = (
                f"  [bold]Tipo:[/] {item.get('movement_type', '-')}  |  "
                f"[bold]Quantidade:[/] [{c}]{qty:+,}[/]\n"
                f"  [bold]Lote ID:[/] {item.get('batch_id', '-')}\n"
                f"  [bold]Notas:[/] {item.get('notes', '-')}\n"
                f"  [bold]Data:[/] {item.get('created_at', '-')}"
            )
            self.query_one("#detail", Label).update(detail)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("fb-mt-"):
            mtype = btn_id.replace("fb-mt-", "")
            self._filter_type = mtype
            for btn in self.query("#type-filters .filter-btn"):
                btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


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
    "1": DashboardView,
    "2": ProdutosView,
    "3": AlertasView,
    "4": VencimentoView,
    "5": EstoqueView,
    "6": ConsumoView,
    "7": MovimentacoesView,
    "8": UsuariosView,
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
    .filter-input { width: 1fr; margin: 0 1; min-height: 3; }
    .filter-btn {
        min-height: 3;
        min-width: 12;
        margin: 0 1;
        background: $surface;
        color: $text-muted;
        border: solid $primary;
    }
    .filter-btn:hover { background: $primary 20%; }
    .filter-btn.-active { background: $primary 40%; color: $text; text-style: bold; }
    Horizontal { height: auto; }
    #detail {
        width: 100%;
        padding: 1 2;
        background: $panel;
        border: solid $primary;
        margin: 1 2;
    }
    #hint { color: $text-muted; }
    #summary { width: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("[bold cyan]ABHU[/]")
                yield Label("[dim]v1.1[/]")
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
