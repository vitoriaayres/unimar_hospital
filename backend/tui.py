"""ABHU TUI - Terminal interface for hospital pharmacy management."""

import urllib.request
import urllib.error
import json as _json
from datetime import date
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, DataTable, Label, Button, Sparkline, Input, Rule
from textual.css.query import NoMatches
from textual import on

API_URL = "http://localhost:8000/api/v1"
_token = None


def _try_refresh_token():
    global _token
    do_login()


def _make_request(url, method="GET", data=None, content_type=None):
    global _token
    headers = {"Authorization": f"Bearer {_token}"}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return _json.loads(resp.read())


def api_get(path, params=None):
    global _token
    if not _token:
        _try_refresh_token()
    if not _token:
        return None
    try:
        url = f"{API_URL}{path}"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            url = f"{url}?{qs}"
        return _make_request(url)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            _try_refresh_token()
            if _token:
                try:
                    return _make_request(url)
                except Exception:
                    pass
        return None
    except Exception:
        return None


def api_post(path, data):
    global _token
    if not _token:
        _try_refresh_token()
    if not _token:
        return None, "Nao autenticado"
    try:
        url = f"{API_URL}{path}"
        body = _json.dumps(data).encode("utf-8")
        return _make_request(url, method="POST", data=body, content_type="application/json"), None
    except urllib.error.HTTPError as e:
        if e.code == 401:
            _try_refresh_token()
            if _token:
                try:
                    return _make_request(url, method="POST", data=body, content_type="application/json"), None
                except urllib.error.HTTPError as e2:
                    try:
                        return None, _json.loads(e2.read()).get("detail", str(e2))
                    except Exception:
                        return None, str(e2)
        try:
            err_body = _json.loads(e.read())
            msg = err_body.get("detail", str(e))
        except Exception:
            msg = str(e)
        return None, msg
    except Exception as e:
        return None, str(e)


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


def _get_warehouses():
    try:
        import psycopg2
        conn = psycopg2.connect("postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict")
        cur = conn.cursor()
        cur.execute("SELECT id, name, location FROM warehouses ORDER BY name")
        rows = [{"id": str(r[0]), "name": r[1], "location": r[2] or ""} for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def _resolve_product(search_term):
    d = api_get("/products", params={"search": search_term, "size": 5})
    items = _get_items(d)
    if items:
        return items[0]
    return None


def _get_available_batches():
    d = api_get("/inventory/batches", params={"status": "available", "limit": 50})
    return _get_items(d)


# --------------- Views (Read-Only) ---------------


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


# --------------- Form Views (Write) ---------------


CATEGORIES = ["antibiotic", "analgesic", "antithrombotic", "beta_blocker", "ppi", "bronchodilator", "psycholeptic", "ace_inhibitor", "corticosteroid", "other"]
CATEGORY_LABELS = {
    "antibiotic": "Antibiotico", "analgesic": "Analgesico", "antithrombotic": "Antitrombotico",
    "beta_blocker": "Beta-bloqueador", "ppi": "IBP", "bronchodilator": "Broncodilatador",
    "psycholeptic": "Psicolptico", "ace_inhibitor": "IECA", "corticosteroid": "Corticosteroide",
    "other": "Outro",
}
DEPARTMENTS = [("icu", "UTI"), ("er", "Pronto Socorro"), ("ward", "Enfermaria"), ("outpatient", "Ambulatorio")]
PRESCRIPTION_TYPES = [("routine", "Rotina"), ("emergency", "Emergencia"), ("prophylactic", "Profilaxia")]


class CadastrarProdutoView(Static):
    _selected_category = "other"
    _selected_controlled = False

    def compose(self) -> ComposeResult:
        yield Label("  Cadastrar Novo Produto", classes="view-title")
        with ScrollableContainer(classes="form-scroll"):
            with Horizontal(classes="form-row"):
                yield Label("SKU:", classes="form-label")
                yield Input(placeholder="Ex: AMOX-500", id="f-sku", classes="form-input")
            with Horizontal(classes="form-row"):
                yield Label("Nome:", classes="form-label")
                yield Input(placeholder="Ex: Amoxicilina 500mg", id="f-name", classes="form-input")
            with Horizontal(classes="form-row"):
                yield Label("Generico:", classes="form-label")
                yield Input(placeholder="Ex: Amoxicilina", id="f-generic", classes="form-input")
            with Horizontal(classes="form-row"):
                yield Label("Categoria:", classes="form-label")
                with Horizontal(id="cat-buttons"):
                    for cat in CATEGORIES:
                        active = " -active" if cat == "other" else ""
                        yield Button(CATEGORY_LABELS[cat], id=f"cat-{cat}", classes=f"filter-btn form-btn{active}")
            with Horizontal(classes="form-row"):
                yield Label("ATC Code:", classes="form-label")
                yield Input(placeholder="Ex: J01CA04", id="f-atc", classes="form-input")
            with Horizontal(classes="form-row"):
                yield Label("Unidade:", classes="form-label")
                yield Input(placeholder="un", id="f-unit", classes="form-input", value="un")
            with Horizontal(classes="form-row"):
                yield Label("Custo Unit.:", classes="form-label")
                yield Input(placeholder="0.00", id="f-cost", classes="form-input", value="0.00")
            with Horizontal(classes="form-row"):
                yield Label("Est. Minimo:", classes="form-label")
                yield Input(placeholder="0", id="f-min", classes="form-input", value="0")
            with Horizontal(classes="form-row"):
                yield Label("Est. Maximo:", classes="form-label")
                yield Input(placeholder="100", id="f-max", classes="form-input", value="100")
            with Horizontal(classes="form-row"):
                yield Label("Lead Time:", classes="form-label")
                yield Input(placeholder="7", id="f-lead", classes="form-input", value="7")
            with Horizontal(classes="form-row"):
                yield Label("Controlada:", classes="form-label")
                with Horizontal(id="ctrl-buttons"):
                    yield Button("Nao", id="ctrl-no", classes="filter-btn form-btn -active")
                    yield Button("Sim", id="ctrl-yes", classes="filter-btn form-btn")
            yield Label("")
            with Horizontal(classes="form-actions"):
                yield Button("Confirmar", id="btn-confirm", classes="form-btn-confirm")
                yield Button("Limpar", id="btn-clear", classes="form-btn-clear")
            yield Label("", id="form-status")

    def _collect_data(self):
        sku = self.query_one("#f-sku", Input).value.strip()
        name = self.query_one("#f-name", Input).value.strip()
        if not sku or not name:
            return None, "SKU e Nome sao obrigatorios"
        generic = self.query_one("#f-generic", Input).value.strip() or None
        atc = self.query_one("#f-atc", Input).value.strip() or None
        unit = self.query_one("#f-unit", Input).value.strip() or "un"
        try:
            cost = float(self.query_one("#f-cost", Input).value.strip() or "0")
        except ValueError:
            return None, "Custo invalido"
        try:
            min_s = int(self.query_one("#f-min", Input).value.strip() or "0")
            max_s = int(self.query_one("#f-max", Input).value.strip() or "100")
            lead = int(self.query_one("#f-lead", Input).value.strip() or "7")
        except ValueError:
            return None, "Valores numericos invalidos"
        data = {
            "sku": sku,
            "name": name,
            "category": self._selected_category,
            "unit": unit,
            "unit_cost": cost,
            "min_stock_level": min_s,
            "max_stock_level": max_s,
            "lead_time_days": lead,
            "controlled_substance": self._selected_controlled,
        }
        if generic:
            data["generic_name"] = generic
        if atc:
            data["atc_code"] = atc
        return data, None

    def _clear_form(self):
        for inp_id in ["f-sku", "f-name", "f-generic", "f-atc", "f-cost", "f-min", "f-max", "f-lead"]:
            self.query_one(f"#{inp_id}", Input).value = ""
        self.query_one("#f-unit", Input).value = "un"
        self.query_one("#f-cost", Input).value = "0.00"
        self.query_one("#f-min", Input).value = "0"
        self.query_one("#f-max", Input).value = "100"
        self.query_one("#f-lead", Input).value = "7"
        self._selected_category = "other"
        self._selected_controlled = False
        for btn in self.query("#cat-buttons .filter-btn"):
            btn.classes = "filter-btn form-btn -active" if btn.id == "cat-other" else "filter-btn form-btn"
        self.query_one("#ctrl-no", Button).classes = "filter-btn form-btn -active"
        self.query_one("#ctrl-yes", Button).classes = "filter-btn form-btn"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("cat-"):
            cat = btn_id.replace("cat-", "")
            self._selected_category = cat
            for btn in self.query("#cat-buttons .filter-btn"):
                btn.classes = "filter-btn form-btn -active" if btn.id == btn_id else "filter-btn form-btn"
        elif btn_id == "ctrl-no":
            self._selected_controlled = False
            self.query_one("#ctrl-no").classes = "filter-btn form-btn -active"
            self.query_one("#ctrl-yes").classes = "filter-btn form-btn"
        elif btn_id == "ctrl-yes":
            self._selected_controlled = True
            self.query_one("#ctrl-yes").classes = "filter-btn form-btn -active"
            self.query_one("#ctrl-no").classes = "filter-btn form-btn"
        elif btn_id == "btn-confirm":
            data, err = self._collect_data()
            if err:
                self.query_one("#form-status", Label).update(f"  [red]{err}[/]")
                return
            result, api_err = api_post("/products", data)
            if api_err:
                self.query_one("#form-status", Label).update(f"  [red]Erro: {api_err}[/]")
            else:
                self._clear_form()
                self.query_one("#form-status", Label).update(f"  [green]Produto criado: {result.get('name', '')} (SKU: {result.get('sku', '')})[/]")
        elif btn_id == "btn-clear":
            self._clear_form()
            self.query_one("#form-status", Label).update("")


class RecebimentoView(Static):
    _warehouses = []
    _selected_warehouse = None

    def compose(self) -> ComposeResult:
        yield Label("  Recebimento de Lote", classes="view-title")
        with ScrollableContainer(classes="form-scroll"):
            yield Label("[dim]  Produtos cadastrados (use SKU ou nome para buscar):[/]", classes="form-ref-title")
            yield DataTable(id="ref-products", classes="form-ref-table")
            yield Label("")
            with Horizontal(classes="form-row"):
                yield Label("Produto:", classes="form-label")
                yield Input(placeholder="SKU ou nome do produto", id="f-product", classes="form-input")
            with Horizontal(classes="form-row"):
                yield Label("Deposito:", classes="form-label")
                with Horizontal(id="wh-buttons"):
                    yield Label("[dim]Carregando depositos...[/]", id="wh-loading")
            with Horizontal(classes="form-row"):
                yield Label("Lote:", classes="form-label")
                yield Input(placeholder="Numero do lote", id="f-batch", classes="form-input")
            with Horizontal(classes="form-row"):
                yield Label("Quantidade:", classes="form-label")
                yield Input(placeholder="0", id="f-qty", classes="form-input", value="0")
            with Horizontal(classes="form-row"):
                yield Label("Validade:", classes="form-label")
                yield Input(placeholder="AAAA-MM-DD", id="f-expiry", classes="form-input")
            with Horizontal(classes="form-row"):
                yield Label("Fabricacao:", classes="form-label")
                yield Input(placeholder="AAAA-MM-DD (opcional)", id="f-mfg", classes="form-input")
            with Horizontal(classes="form-row"):
                yield Label("Custo Unit.:", classes="form-label")
                yield Input(placeholder="0.00", id="f-cost", classes="form-input", value="0.00")
            yield Label("")
            with Horizontal(classes="form-actions"):
                yield Button("Confirmar", id="btn-confirm", classes="form-btn-confirm")
                yield Button("Limpar", id="btn-clear", classes="form-btn-clear")
            yield Label("", id="form-status")

    def on_mount(self) -> None:
        self._warehouses = _get_warehouses()
        try:
            self.query_one("#wh-loading", Label).update("")
            wh_box = self.query_one("#wh-buttons")
            for wh in self._warehouses:
                label = wh["name"]
                if wh.get("location"):
                    label += f" ({wh['location']})"
                btn = Button(label, id=f"wh-{wh['id'][:8]}", classes="filter-btn form-btn")
                wh_box.mount(btn)
            if self._warehouses:
                self._selected_warehouse = self._warehouses[0]["id"]
                first_btn = self.query_one(f"#wh-{self._warehouses[0]['id'][:8]}", Button)
                first_btn.classes = "filter-btn form-btn -active"
        except Exception:
            pass
        self._load_products()

    def _load_products(self):
        try:
            t = self.query_one("#ref-products", DataTable)
            t.add_columns("Produto", "SKU", "Categoria")
            d = api_get("/products", params={"size": 20})
            items = _get_items(d)
            for item in items:
                t.add_row(item.get("name", ""), item.get("sku", ""), item.get("category", ""))
        except Exception:
            pass

    def _collect_data(self):
        product_search = self.query_one("#f-product", Input).value.strip()
        if not product_search:
            return None, "Produto e obrigatorio"
        product = _resolve_product(product_search)
        if not product:
            return None, f"Produto nao encontrado: {product_search}"
        batch_num = self.query_one("#f-batch", Input).value.strip()
        if not batch_num:
            return None, "Numero do lote e obrigatorio"
        if not self._selected_warehouse:
            return None, "Selecione um deposito"
        try:
            qty = int(self.query_one("#f-qty", Input).value.strip() or "0")
        except ValueError:
            return None, "Quantidade invalida"
        expiry_str = self.query_one("#f-expiry", Input).value.strip()
        if not expiry_str:
            return None, "Data de validade e obrigatoria"
        try:
            parts = expiry_str.split("-")
            expiry = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            return None, "Formato de data invalido (use AAAA-MM-DD)"
        mfg_str = self.query_one("#f-mfg", Input).value.strip()
        mfg = None
        if mfg_str:
            try:
                parts = mfg_str.split("-")
                mfg = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception:
                return None, "Formato de data de fabricacao invalido"
        try:
            cost = float(self.query_one("#f-cost", Input).value.strip() or "0")
        except ValueError:
            return None, "Custo invalido"
        data = {
            "product_id": product["id"],
            "warehouse_id": self._selected_warehouse,
            "batch_number": batch_num,
            "quantity": qty,
            "expiry_date": expiry.isoformat(),
            "unit_cost": cost,
        }
        if mfg:
            data["manufacture_date"] = mfg.isoformat()
        return data, None

    def _clear_form(self):
        for inp_id in ["f-product", "f-batch", "f-expiry", "f-mfg"]:
            self.query_one(f"#{inp_id}", Input).value = ""
        self.query_one("#f-qty", Input).value = "0"
        self.query_one("#f-cost", Input).value = "0.00"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("wh-"):
            wh_prefix = btn_id.replace("wh-", "")
            for wh in self._warehouses:
                if wh["id"][:8] == wh_prefix:
                    self._selected_warehouse = wh["id"]
                    break
            for btn in self.query("#wh-buttons .filter-btn"):
                btn.classes = "filter-btn form-btn -active" if btn.id == btn_id else "filter-btn form-btn"
        elif btn_id == "btn-confirm":
            data, err = self._collect_data()
            if err:
                self.query_one("#form-status", Label).update(f"  [red]{err}[/]")
                return
            result, api_err = api_post("/inventory/batches", data)
            if api_err:
                self.query_one("#form-status", Label).update(f"  [red]Erro: {api_err}[/]")
            else:
                self._clear_form()
                self.query_one("#form-status", Label).update(
                    f"  [green]Lote criado: {result.get('batch_number', '')} | Qtd: {result.get('quantity', 0)}[/]"
                )
        elif btn_id == "btn-clear":
            self._clear_form()
            self.query_one("#form-status", Label).update("")


class DispensacaoView(Static):
    _batches = []

    def compose(self) -> ComposeResult:
        yield Label("  Dispensacao de Estoque (Saida)", classes="view-title")
        with ScrollableContainer(classes="form-scroll"):
            yield Label("[dim]  Lotes disponiveis (copie o ID do lote):[/]", classes="form-ref-title")
            yield DataTable(id="ref-batches", classes="form-ref-table")
            yield Label("")
            with Horizontal(classes="form-row"):
                yield Label("ID Lote:", classes="form-label")
                yield Input(placeholder="UUID do lote", id="f-batch-id", classes="form-input")
            with Horizontal(classes="form-row"):
                yield Label("Quantidade:", classes="form-label")
                yield Input(placeholder="Quantidade a dispensar", id="f-qty", classes="form-input", value="0")
            with Horizontal(classes="form-row"):
                yield Label("Notas:", classes="form-label")
                yield Input(placeholder="Observacoes (opcional)", id="f-notes", classes="form-input")
            yield Label("")
            with Horizontal(classes="form-actions"):
                yield Button("Confirmar Saida", id="btn-confirm", classes="form-btn-confirm")
                yield Button("Limpar", id="btn-clear", classes="form-btn-clear")
            yield Label("", id="form-status")

    def on_mount(self) -> None:
        self._load_batches()

    def _load_batches(self):
        try:
            self._batches = _get_available_batches()
            t = self.query_one("#ref-batches", DataTable)
            t.add_columns("ID (8chars)", "Produto", "Lote", "Qtd", "Validade")
            for b in self._batches:
                t.add_row(
                    str(b.get("id", ""))[:8],
                    b.get("product_id", "")[:8],
                    b.get("batch_number", ""),
                    str(b.get("quantity", 0)),
                    b.get("expiry_date", ""),
                )
        except Exception:
            pass

    def _collect_data(self):
        batch_id = self.query_one("#f-batch-id", Input).value.strip()
        if not batch_id:
            return None, "ID do lote e obrigatorio"
        if len(batch_id) < 36:
            found = None
            for b in self._batches:
                if str(b.get("id", "")).startswith(batch_id):
                    found = b
                    break
            if found:
                batch_id = found["id"]
            else:
                return None, f"Lote nao encontrado: {batch_id}"
        try:
            qty = int(self.query_one("#f-qty", Input).value.strip() or "0")
        except ValueError:
            return None, "Quantidade invalida"
        if qty <= 0:
            return None, "Quantidade deve ser maior que 0"
        notes = self.query_one("#f-notes", Input).value.strip() or None
        data = {
            "batch_id": batch_id,
            "quantity_change": -qty,
            "movement_type": "out",
        }
        if notes:
            data["notes"] = notes
        return data, None

    def _clear_form(self):
        for inp_id in ["f-batch-id", "f-qty", "f-notes"]:
            self.query_one(f"#{inp_id}", Input).value = ""
        self.query_one("#f-qty", Input).value = "0"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-confirm":
            data, err = self._collect_data()
            if err:
                self.query_one("#form-status", Label).update(f"  [red]{err}[/]")
                return
            result, api_err = api_post("/inventory/movements", data)
            if api_err:
                self.query_one("#form-status", Label).update(f"  [red]Erro: {api_err}[/]")
            else:
                qty = result.get("quantity_change", 0)
                self._clear_form()
                self._load_batches()
                self.query_one("#form-status", Label).update(
                    f"  [green]Saida registrada: {abs(qty)} unidades | Tipo: {result.get('movement_type', '')}[/]"
                )
        elif btn_id == "btn-clear":
            self._clear_form()
            self.query_one("#form-status", Label).update("")


class RegistroConsumoView(Static):
    _selected_department = "outpatient"
    _selected_prescription = "routine"

    def compose(self) -> ComposeResult:
        yield Label("  Registro de Consumo Diario", classes="view-title")
        with ScrollableContainer(classes="form-scroll"):
            yield Label("[dim]  Produtos cadastrados (use SKU ou nome para buscar):[/]", classes="form-ref-title")
            yield DataTable(id="ref-products", classes="form-ref-table")
            yield Label("")
            with Horizontal(classes="form-row"):
                yield Label("Produto:", classes="form-label")
                yield Input(placeholder="SKU ou nome do produto", id="f-product", classes="form-input")
            with Horizontal(classes="form-row"):
                yield Label("Data:", classes="form-label")
                yield Input(placeholder="AAAA-MM-DD", id="f-date", classes="form-input", value=date.today().isoformat())
            with Horizontal(classes="form-row"):
                yield Label("Quantidade:", classes="form-label")
                yield Input(placeholder="0", id="f-qty", classes="form-input", value="0")
            with Horizontal(classes="form-row"):
                yield Label("Departamento:", classes="form-label")
                with Horizontal(id="dept-buttons"):
                    for dept_val, dept_label in DEPARTMENTS:
                        active = " -active" if dept_val == "outpatient" else ""
                        yield Button(dept_label, id=f"dept-{dept_val}", classes=f"filter-btn form-btn{active}")
            with Horizontal(classes="form-row"):
                yield Label("Prescricao:", classes="form-label")
                yield Label("[dim]Prescricao:[/]", classes="form-label-dummy")
            with Horizontal(classes="form-row"):
                yield Label("", classes="form-label")
                with Horizontal(id="presc-buttons"):
                    for ptype, plabel in PRESCRIPTION_TYPES:
                        active = " -active" if ptype == "routine" else ""
                        yield Button(plabel, id=f"presc-{ptype}", classes=f"filter-btn form-btn{active}")
            yield Label("")
            with Horizontal(classes="form-actions"):
                yield Button("Confirmar", id="btn-confirm", classes="form-btn-confirm")
                yield Button("Limpar", id="btn-clear", classes="form-btn-clear")
            yield Label("", id="form-status")

    def on_mount(self) -> None:
        self._load_products()

    def _load_products(self):
        try:
            t = self.query_one("#ref-products", DataTable)
            t.add_columns("Produto", "SKU", "Categoria")
            d = api_get("/products", params={"size": 20})
            items = _get_items(d)
            for item in items:
                t.add_row(item.get("name", ""), item.get("sku", ""), item.get("category", ""))
        except Exception:
            pass

    def _collect_data(self):
        product_search = self.query_one("#f-product", Input).value.strip()
        if not product_search:
            return None, "Produto e obrigatorio"
        product = _resolve_product(product_search)
        if not product:
            return None, f"Produto nao encontrado: {product_search}"
        date_str = self.query_one("#f-date", Input).value.strip()
        if not date_str:
            return None, "Data e obrigatoria"
        try:
            parts = date_str.split("-")
            cons_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            return None, "Formato de data invalido (use AAAA-MM-DD)"
        try:
            qty = int(self.query_one("#f-qty", Input).value.strip() or "0")
        except ValueError:
            return None, "Quantidade invalida"
        if qty <= 0:
            return None, "Quantidade deve ser maior que 0"
        data = {
            "product_id": product["id"],
            "consumption_date": cons_date.isoformat(),
            "quantity": qty,
            "department": self._selected_department,
            "prescription_type": self._selected_prescription,
        }
        return data, None

    def _clear_form(self):
        for inp_id in ["f-product", "f-qty"]:
            self.query_one(f"#{inp_id}", Input).value = ""
        self.query_one("#f-date", Input).value = date.today().isoformat()
        self.query_one("#f-qty", Input).value = "0"
        self._selected_department = "outpatient"
        self._selected_prescription = "routine"
        for btn in self.query("#dept-buttons .filter-btn"):
            btn.classes = "filter-btn form-btn -active" if btn.id == "dept-outpatient" else "filter-btn form-btn"
        for btn in self.query("#presc-buttons .filter-btn"):
            btn.classes = "filter-btn form-btn -active" if btn.id == "presc-routine" else "filter-btn form-btn"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("dept-"):
            dept = btn_id.replace("dept-", "")
            self._selected_department = dept
            for btn in self.query("#dept-buttons .filter-btn"):
                btn.classes = "filter-btn form-btn -active" if btn.id == btn_id else "filter-btn form-btn"
        elif btn_id.startswith("presc-"):
            ptype = btn_id.replace("presc-", "")
            self._selected_prescription = ptype
            for btn in self.query("#presc-buttons .filter-btn"):
                btn.classes = "filter-btn form-btn -active" if btn.id == btn_id else "filter-btn form-btn"
        elif btn_id == "btn-confirm":
            data, err = self._collect_data()
            if err:
                self.query_one("#form-status", Label).update(f"  [red]{err}[/]")
                return
            result, api_err = api_post("/consumption", data)
            if api_err:
                self.query_one("#form-status", Label).update(f"  [red]Erro: {api_err}[/]")
            else:
                self._clear_form()
                self.query_one("#form-status", Label).update(
                    f"  [green]Consumo registrado: {result.get('quantity', 0)} unidades em {result.get('department', '')}[/]"
                )
        elif btn_id == "btn-clear":
            self._clear_form()
            self.query_one("#form-status", Label).update("")


class PrevisoesView(Static):
    """View de Previsoes ML - Mostra previsoes de demanda do modelo treinado."""
    _all_data = []
    _selected_idx = None

    def compose(self) -> ComposeResult:
        yield Label("  Previsoes de Demanda (ML)", classes="view-title")
        with Horizontal(id="pred-filters"):
            yield Input(placeholder="Buscar produto...", id="pred-search", classes="filter-input")
            yield Button("Atualizar", id="pred-refresh", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("[dim]  Clique em uma linha para ver detalhes[/]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        self._load_data()

    def _load_data(self):
        try:
            import psycopg2
            conn = psycopg2.connect("postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict")
            cur = conn.cursor()
            cur.execute("""
                SELECT p.id, p.sku, p.name, p.category, p.atc_code,
                       pr.predicted_quantity, pr.confidence_lower, pr.confidence_upper,
                       pr.mape_score, pr.forecast_date,
                       COALESCE(inv.stock, 0) as current_stock
                FROM predictions pr
                JOIN products p ON pr.product_id = p.id
                LEFT JOIN (
                    SELECT product_id, SUM(quantity) as stock
                    FROM inventory_batches
                    WHERE status = 'available'
                    GROUP BY product_id
                ) inv ON p.id = inv.product_id
                WHERE p.is_active = true
                ORDER BY pr.predicted_quantity DESC
            """)
            rows = cur.fetchall()
            conn.close()

            self.__class__._all_data = []
            for row in rows:
                stock = row[10] or 0
                pred_7d = row[5] or 0
                days_stock = int(stock / (pred_7d / 7)) if pred_7d > 0 and stock > 0 else None

                self.__class__._all_data.append({
                    "product_id": row[0],
                    "sku": row[1],
                    "name": row[2],
                    "category": row[3],
                    "atc_code": row[4],
                    "predicted_7d": pred_7d,
                    "predicted_daily": round(pred_7d / 7, 1) if pred_7d else 0,
                    "confidence_lower": row[6],
                    "confidence_upper": row[7],
                    "mape": row[8],
                    "forecast_date": str(row[9]) if row[9] else "-",
                    "current_stock": stock,
                    "days_of_stock": days_stock,
                })

            self._render_table(self._all_data)
        except Exception as e:
            self.query_one("#detail", Label).update(f"  [red]Erro ao carregar previsoes: {e}[/]")

    def _render_table(self, data):
        try:
            t = self.query_one("#tbl", DataTable)
            t.clear()
            if not data:
                self.query_one("#detail", Label).update("  [dim]Nenhuma previsao encontrada. Execute ml/predict.py[/]")
                return
            t.add_columns("#", "Produto", "Categoria", "Estoque", "Prev Diaria", "Prev 7d", "Dias Estoque", "MAPE")
            for i, item in enumerate(data[:100], 1):
                stock_str = f"{item['current_stock']:,}" if item['current_stock'] else "0"
                days_str = str(item['days_of_stock']) if item['days_of_stock'] is not None else "-"
                mape_str = f"{item['mape']*100:.1f}%" if item['mape'] else "-"
                t.add_row(
                    str(i),
                    item["name"][:35],
                    item["category"][:12],
                    stock_str,
                    f"{item['predicted_daily']:,.0f}",
                    f"{item['predicted_7d']:,}",
                    days_str,
                    mape_str,
                )
            self.query_one("#detail", Label).update(
                f"  [dim]Total: {len(data)} produtos com previsao | "
                f"Media prev 7d: {sum(d['predicted_7d'] for d in data) / len(data):,.0f}[/]"
            )
        except Exception:
            pass

    @on(Input.Changed, "#pred-search")
    def on_search(self):
        search = self.query_one("#pred-search", Input).value.lower().strip()
        if not search:
            filtered = self._all_data
        else:
            filtered = [x for x in self._all_data
                       if search in (x.get("name") or "").lower()
                       or search in (x.get("sku") or "").lower()
                       or search in (x.get("category") or "").lower()]
        self._render_table(filtered)

    @on(DataTable.RowSelected, "#tbl")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        row_idx = event.row_index
        if row_idx is not None and row_idx < len(self._all_data):
            item = self._all_data[row_idx]
            detail = (
                f"  [bold]{item['name']}[/] ({item['sku']})\n"
                f"  Categoria: {item['category']} | ATC: {item['atc_code']}\n"
                f"  Previsao 7d: [bold]{item['predicted_7d']:,}[/] "
                f"(diaria: {item['predicted_daily']:,.0f})\n"
                f"  Intervalo confianca: [{item['confidence_lower']:,} - {item['confidence_upper']:,}]\n"
                f"  Estoque atual: [bold]{item['current_stock']:,}[/] | "
                f"Dias de estoque: [bold]{item['days_of_stock'] or '-'}[/]\n"
                f"  MAPE: {item['mape']*100:.1f}% | Data previsao: {item['forecast_date']}"
            )
            self.query_one("#detail", Label).update(detail)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pred-refresh":
            self._load_data()


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
    "9": CadastrarProdutoView,
    "10": RecebimentoView,
    "11": DispensacaoView,
    "12": RegistroConsumoView,
    "13": PrevisoesView,
}


class ABHUApp(App):
    TITLE = "PharmaPredict"
    SUB_TITLE = "clique para navegar"

    CSS = """
    Screen { background: $surface; }
    #sidebar {
        width: 30;
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

    .form-scroll { height: 1fr; padding: 0 2; }
    .form-row { height: auto; margin: 0 0 1 0; align: left middle; }
    .form-label { width: 14; min-width: 14; text-style: bold; color: $text-muted; }
    .form-label-dummy { width: 14; min-width: 14; }
    .form-input { width: 1fr; min-height: 3; margin: 0 0 0 1; }
    .form-btn {
        min-height: 3;
        min-width: 10;
        margin: 0 1;
        background: $surface;
        color: $text-muted;
        border: solid $primary;
    }
    .form-btn:hover { background: $primary 20%; }
    .form-btn.-active { background: $primary 40%; color: $text; text-style: bold; }
    .form-actions { height: auto; margin: 1 0; }
    .form-btn-confirm {
        min-height: 3;
        min-width: 16;
        margin: 0 1;
        background: $success;
        color: $text;
        border: solid $success;
        text-style: bold;
    }
    .form-btn-confirm:hover { background: $success 80%; }
    .form-btn-clear {
        min-height: 3;
        min-width: 12;
        margin: 0 1;
        background: $surface;
        color: $text-muted;
        border: solid $primary;
    }
    .form-btn-clear:hover { background: $primary 20%; }
    .form-ref-title { color: $text-muted; margin: 0 0 0 2; }
    .form-ref-table { height: 12; margin: 0 0 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("[bold cyan]PharmaPredict[/]")
                yield Label("[dim]v2.0[/]")
                yield Label("")
                yield Label("[bold]Consulta[/]")
                yield Button("1 Dashboard", id="btn-1", classes="-active")
                yield Button("2 Produtos", id="btn-2")
                yield Button("3 Alertas", id="btn-3")
                yield Button("4 Vencimento", id="btn-4")
                yield Button("5 Estoque", id="btn-5")
                yield Button("6 Consumo", id="btn-6")
                yield Button("7 Movimentacoes", id="btn-7")
                yield Button("8 Usuarios", id="btn-8")
                yield Button("13 Previsoes ML", id="btn-13")
                yield Label("")
                yield Label("[bold]Cadastro[/]")
                yield Button("9 Cadastrar Produto", id="btn-9")
                yield Button("10 Recebimento", id="btn-10")
                yield Button("11 Dispensacao", id="btn-11")
                yield Button("12 Consumo Diario", id="btn-12")
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
                yield CadastrarProdutoView(id="v-9", classes="hidden")
                yield RecebimentoView(id="v-10", classes="hidden")
                yield DispensacaoView(id="v-11", classes="hidden")
                yield RegistroConsumoView(id="v-12", classes="hidden")
                yield PrevisoesView(id="v-13", classes="hidden")
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
        for k in VIEW_MAP:
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
