"""ABHU TUI - Terminal interface for hospital pharmacy management."""

import urllib.request
import urllib.error
import json as _json
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, Label, Button, Sparkline, Input
from textual.css.query import NoMatches
from textual import on, work

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


# ---- Rich formatters ----

def bar(value, max_val, width=15, color="green"):
    if max_val <= 0:
        return ""
    ratio = min(value / max_val, 1.0)
    filled = int(ratio * width)
    empty = width - filled
    pct = int(ratio * 100)
    return f"[{color}]{'█' * filled}{'░' * empty}[/] {pct}%"


# ---- Table helper ----

def _fill_table(table, cols, rows):
    table.clear()
    if not table.columns:
        table.add_columns(*cols)
    for row in rows:
        table.add_row(*row)


# ---- Detail panel builder ----

def _detail_box(title, lines):
    """Build a styled detail string with title and key:value lines."""
    parts = [f"  [bold cyan]{title}[/]"]
    for key, val in lines:
        parts.append(f"  [bold]{key}:[/] {val}")
    return "\n".join(parts)


# --------------- Views ---------------


class DashboardView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  [bold]Dashboard[/]", classes="view-title")
        yield DataTable(id="tbl")
        yield Label("", id="sparkline-label")
        yield Sparkline([], id="spark")

    def on_mount(self) -> None:
        try:
            t = self.query_one("#tbl", DataTable)
            t.add_columns("Indicador", "Valor", "Nivel")
            t.cursor_type = "row"
            d = api_get("/dashboard/kpis")
            if d:
                rows = [
                    ("Total de SKUs", f"[bold]{d['total_skus']:,}[]", bar(d["total_skus"], 500, 15, "green")),
                    ("Estoque Baixo", f"[yellow]{d['low_stock_count']}[]", bar(d["low_stock_count"], 100, 15, "yellow")),
                    ("Risco de Falta", f"[red]{d['stockout_risk_count']}[]", bar(d["stockout_risk_count"], 500, 15, "red")),
                    ("Vencendo (30d)", f"[yellow]{d['expiring_soon_count']}[]", bar(d["expiring_soon_count"], 100, 15, "yellow")),
                    ("Valor Estoque", f"[bold green]R$ {d['total_inventory_value']:,.2f}[]", ""),
                    ("MAPE Medio", f"[cyan]{d['average_mape']:.2f}%[]", bar(d["average_mape"] * 100, 500, 15, "blue")),
                    ("Previsoes Hoje", f"[bold]{d['predictions_generated_today']}[]", ""),
                    ("Alertas Nao Lidos", f"[red]{d['alerts_unacknowledged']}[]", bar(d["alerts_unacknowledged"], 1000, 15, "red")),
                ]
                for k, v, b in rows:
                    t.add_row(k, v, b)

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
                        self.query_one("#spark", Sparkline).data = vals
                        self.query_one("#sparkline-label", Label).update(
                            "  [bold cyan]Consumo diario[] [dim](ultimos 30 dias)[]"
                        )
                except Exception:
                    pass
        except Exception:
            pass


class ProdutosView(Static):
    _all_data = []
    _filtered_data = []
    _filter_risk = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Produtos - Risco de Estoque[]", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar produto...", id="search", classes="filter-input")
            yield Button("Todos", id="fb-todos", classes="filter-btn -active")
            yield Button("Critical", id="fb-critical", classes="filter-btn")
            yield Button("High", id="fb-high", classes="filter-btn")
            yield Button("Medium", id="fb-medium", classes="filter-btn")
            yield Button("Low", id="fb-low", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("[dim]  Clique ou use ↑↓ para ver detalhes[]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        self.__class__._all_data = api_get("/dashboard/stockout-risk", params={"limit": 100}) or []
        self._apply_filters()

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        risk = self._filter_risk
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("product_name") or "").lower() or search in (x.get("product_sku") or "").lower()]
        if risk and risk != "todos":
            filtered = [x for x in filtered if x.get("risk_level") == risk]
        self.__class__._filtered_data = filtered

        max_stock = max((x.get("current_stock", 0) for x in filtered), default=1) or 1
        cols = ["#", "Produto", "Estoque", "Nivel", "Cons. 7d", "Dias", "Risco"]
        rows = []
        for i, item in enumerate(filtered, 1):
            risk = item["risk_level"]
            stock = item.get("current_stock", 0)
            rc = "red" if risk in ("critical", "high") else "yellow" if risk == "medium" else "green"
            nivel = bar(stock, max_stock, 12, rc)
            rows.append((
                str(i),
                item.get("product_name") or "",
                f"[bold]{stock:,}[]",
                nivel,
                f"{item.get('predicted_consumption_7d', 0):,}",
                str(item.get("days_until_stockout") or "-"),
                f"[{rc}]{risk.upper()}[]",
            ))
        try:
            _fill_table(self.query_one("#tbl"), cols, rows)
        except Exception:
            pass

    def _show_detail(self, idx):
        if idx is None or idx < 0 or idx >= len(self._filtered_data):
            return
        item = self._filtered_data[idx]
        risk = item.get("risk_level", "-")
        rc = "red" if risk in ("critical", "high") else "yellow" if risk == "medium" else "green"
        stock = item.get("current_stock", 0)
        cons7 = item.get("predicted_consumption_7d", 0)
        days = item.get("days_until_stockout", "-")
        min_stock = item.get("minimum_stock", 0)
        max_stock = item.get("maximum_stock", 0)
        pct = int(stock / max(max_stock, 1) * 100)
        stock_bar = bar(stock, max_stock, 30, rc)
        try:
            self.query_one("#detail", Label).update(
                _detail_box(item.get("product_name", "-"), [
                    ("SKU", item.get("product_sku", "-")),
                    ("Risco", f"[{rc}][bold]{risk.upper()}[][/{rc}]"),
                    ("Estoque Atual", f"[bold]{stock:,}[]"),
                    ("Estoque Min", f"{min_stock:,}"),
                    ("Estoque Max", f"{max_stock:,}"),
                    ("Pct. Estoque", f"{pct}%  {stock_bar}"),
                    ("Consumo 7d", f"{cons7:,}"),
                    ("Dias p/ falta", f"[bold]{days}[]"),
                    ("Fornecedor", item.get("supplier_name", "-")),
                ])
            )
        except Exception:
            pass

    @on(DataTable.RowHighlighted, "#tbl")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_detail(event.row_index)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("fb-"):
            self._filter_risk = btn_id.replace("fb-", "")
            for btn in self.query(".filter-btn"):
                btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class AlertasView(Static):
    _all_data = []
    _filtered_data = []
    _filter_sev = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Alertas Ativos[]", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar mensagem...", id="search", classes="filter-input")
        with Horizontal(id="sev-filters"):
            yield Button("Todos", id="fb-sev-todos", classes="filter-btn -active")
            yield Button("Critical", id="fb-sev-critical", classes="filter-btn")
            yield Button("Warning", id="fb-sev-warning", classes="filter-btn")
            yield Button("Info", id="fb-sev-info", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("", id="summary")
        yield Label("[dim]  Clique ou use ↑↓ para ver detalhes[]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        d = api_get("/alerts", params={"size": 100})
        self.__class__._all_data = _get_items(d)
        self._apply_filters()

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        sev = self._filter_sev
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("message") or "").lower()]
        if sev and sev != "todos":
            filtered = [x for x in filtered if x.get("severity") == sev]
        self.__class__._filtered_data = filtered

        sc = {"critical": 0, "warning": 0, "info": 0}
        for item in filtered:
            sc[item.get("severity", "info")] = sc.get(item.get("severity", "info"), 0) + 1
        try:
            self.query_one("#summary", Label).update(
                f"  [red]\\u2588 {sc.get('critical',0)} Criticos[]  "
                f"[yellow]\\u2588 {sc.get('warning',0)} Avisos[]  "
                f"[blue]\\u2588 {sc.get('info',0)} Info[]  "
                f"[dim]Filtrados: {len(filtered)}/{len(self._all_data)}[]"
            )
        except Exception:
            pass

        cols = ["#", "Tipo", "Sev", "Mensagem", "Data"]
        rows = []
        for i, item in enumerate(filtered[:30], 1):
            sev = item.get("severity", "info")
            if sev == "critical":
                sc_str = "[red][bold]CRIT[][red]"
            elif sev == "warning":
                sc_str = "[yellow]WARN[]"
            else:
                sc_str = "[blue]INFO[]"
            rows.append((
                str(i),
                item.get("alert_type") or "-",
                sc_str,
                (item.get("message") or "-")[:50],
                (item.get("created_at") or "-")[:10],
            ))
        try:
            _fill_table(self.query_one("#tbl"), cols, rows)
        except Exception:
            pass

    def _show_detail(self, idx):
        if idx is None or idx < 0 or idx >= len(self._filtered_data):
            return
        item = self._filtered_data[idx]
        sev = item.get("severity", "info")
        sc = "red" if sev == "critical" else "yellow" if sev == "warning" else "blue"
        ack = "[green]Reconhecido[]" if item.get("acknowledged") else "[red]Pendente[]"
        try:
            self.query_one("#detail", Label).update(
                _detail_box(f"{item.get('alert_type', '-').upper()} - {sev.upper()}", [
                    ("Mensagem", item.get("message", "-")),
                    ("Produto", item.get("product_id", "-")),
                    ("Criado em", item.get("created_at", "-")),
                    ("Atualizado", item.get("updated_at", "-")),
                    ("Status", ack),
                    ("Reconhecido por", item.get("acknowledged_by", "-") or "-"),
                    ("ID", item.get("id", "-")),
                ])
            )
        except Exception:
            pass

    @on(DataTable.RowHighlighted, "#tbl")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_detail(event.row_index)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("fb-sev-"):
            self._filter_sev = btn_id.replace("fb-sev-", "")
            for btn in self.query("#sev-filters .filter-btn"):
                btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class VencimentoView(Static):
    _all_data = []
    _filtered_data = []
    _filter_urg = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Lotes Vencendo[]", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar produto...", id="search", classes="filter-input")
        with Horizontal(id="urg-filters"):
            yield Button("Todos", id="fb-urg-todos", classes="filter-btn -active")
            yield Button("Critico <=30d", id="fb-urg-crit", classes="filter-btn")
            yield Button("Aviso 31-60d", id="fb-urg-warn", classes="filter-btn")
            yield Button("OK >60d", id="fb-urg-ok", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("", id="summary")
        yield Label("[dim]  Clique ou use ↑↓ para ver detalhes[]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        self.__class__._all_data = api_get("/dashboard/expiry-timeline", params={"days_ahead": 90, "limit": 100}) or []
        self._apply_filters()

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
        ok = len(filtered) - crit - warn
        try:
            self.query_one("#summary", Label).update(
                f"  [red]\\u2588 {crit} Criticos[]  "
                f"[yellow]\\u2588 {warn} Avisos[]  "
                f"[green]\\u2588 {ok} OK[]  "
                f"[dim]Filtrados: {len(filtered)}/{len(self._all_data)}[]"
            )
        except Exception:
            pass

        cols = ["#", "Produto", "Lote", "Qtd", "Vencimento", "Dias", "Status"]
        rows = []
        for i, item in enumerate(filtered[:30], 1):
            days = item["days_until_expiry"]
            if days <= 30:
                sc, label = "red", "CRITICO"
            elif days <= 60:
                sc, label = "yellow", "AVISO"
            else:
                sc, label = "green", "OK"
            urg_bar = bar(max(0, 90 - days), 90, 10, sc)
            rows.append((
                str(i),
                item.get("product_name") or "",
                item.get("batch_number") or "",
                f"[bold]{item.get('quantity', 0):,}[]",
                item.get("expiry_date") or "",
                f"[{sc}][bold]{days}[][]",
                f"{urg_bar} [{sc}]{label}[]",
            ))
        try:
            _fill_table(self.query_one("#tbl"), cols, rows)
        except Exception:
            pass

    def _show_detail(self, idx):
        if idx is None or idx < 0 or idx >= len(self._filtered_data):
            return
        item = self._filtered_data[idx]
        days = item.get("days_until_expiry", 0)
        if days <= 30:
            sc, label = "red", "CRITICO"
        elif days <= 60:
            sc, label = "yellow", "AVISO"
        else:
            sc, label = "green", "OK"
        urg_bar = bar(max(0, 90 - days), 90, 30, sc)
        try:
            self.query_one("#detail", Label).update(
                _detail_box(item.get("product_name", "-"), [
                    ("Lote", item.get("batch_number", "-")),
                    ("Quantidade", f"{item.get('quantity', 0):,}"),
                    ("Vencimento", f"[bold]{item.get('expiry_date', '-')}[]"),
                    ("Dias restantes", f"[{sc}][bold]{days}[][] ({label})"),
                    ("Urgencia", urg_bar),
                    ("Almoxarifado", item.get("warehouse_name", "-")),
                    ("ID Lote", item.get("batch_id", "-")),
                ])
            )
        except Exception:
            pass

    @on(DataTable.RowHighlighted, "#tbl")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_detail(event.row_index)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("fb-urg-"):
            self._filter_urg = btn_id.replace("fb-urg-", "")
            for btn in self.query("#urg-filters .filter-btn"):
                btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class EstoqueView(Static):
    _all_data = []
    _filtered_data = []
    _filter_status = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Lotes em Estoque[]", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar produto...", id="search", classes="filter-input")
        with Horizontal(id="status-filters"):
            yield Button("Todos", id="fb-st-todos", classes="filter-btn -active")
            yield Button("Disponivel", id="fb-st-available", classes="filter-btn")
            yield Button("Expirado", id="fb-st-expired", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("[dim]  Clique ou use ↑↓ para ver detalhes[]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        try:
            import psycopg2
            conn = psycopg2.connect("postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict")
            cur = conn.cursor()
            cur.execute(
                "SELECT p.name, ib.batch_number, ib.quantity, ib.unit_cost, ib.expiry_date, ib.status, "
                "ib.warehouse_id, ib.product_id "
                "FROM inventory_batches ib JOIN products p ON ib.product_id = p.id "
                "ORDER BY ib.expiry_date ASC LIMIT 100"
            )
            self.__class__._all_data = [
                {"name": r[0], "batch": r[1], "qty": r[2], "cost": r[3], "expiry": str(r[4]),
                 "status": r[5], "warehouse_id": str(r[6]), "product_id": str(r[7])}
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

        max_qty = max((x.get("qty", 0) for x in filtered), default=1) or 1
        cols = ["#", "Produto", "Lote", "Qtd", "Nivel", "Custo", "Vencimento"]
        rows = []
        for i, item in enumerate(filtered[:30], 1):
            sc = "green" if item["status"] == "available" else "red"
            nivel = bar(item.get("qty", 0), max_qty, 10, sc)
            rows.append((
                str(i),
                item.get("name") or "-",
                item.get("batch") or "-",
                f"[bold]{item.get('qty', 0):,}[]",
                nivel,
                f"R${float(item['cost']):.2f}",
                f"[{sc}]{item.get('expiry', '-')}[]",
            ))
        try:
            _fill_table(self.query_one("#tbl"), cols, rows)
        except Exception:
            pass

    def _show_detail(self, idx):
        if idx is None or idx < 0 or idx >= len(self._filtered_data):
            return
        item = self._filtered_data[idx]
        sc = "green" if item["status"] == "available" else "red"
        valor = item.get("qty", 0) * float(item.get("cost", 0))
        try:
            self.query_one("#detail", Label).update(
                _detail_box(item.get("name", "-"), [
                    ("Lote", item.get("batch", "-")),
                    ("Status", f"[{sc}][bold]{item.get('status', '-')}[][/{sc}]"),
                    ("Quantidade", f"[bold]{item.get('qty', 0):,}[]"),
                    ("Custo Unit.", f"R${float(item['cost']):.2f}"),
                    ("Valor Total", f"[bold green]R${valor:,.2f}[]"),
                    ("Vencimento", f"[bold]{item.get('expiry', '-')}[]"),
                    ("Almoxarifado", item.get("warehouse_id", "-")),
                    ("Produto ID", item.get("product_id", "-")),
                ])
            )
        except Exception:
            pass

    @on(DataTable.RowHighlighted, "#tbl")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_detail(event.row_index)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("fb-st-"):
            self._filter_status = btn_id.replace("fb-st-", "")
            for btn in self.query("#status-filters .filter-btn"):
                btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class ConsumoView(Static):
    _all_data = []

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Consumo Historico[]", classes="view-title")
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
                self.query_one("#spark", Sparkline).data = vals
            except Exception:
                pass
            avg = sum(vals) / len(vals)
            mn, mx = min(vals), max(vals)
            try:
                self.query_one("#stats", Label).update(
                    f"  [bold cyan]Consumo[]  "
                    f"Media: [bold]{int(avg):,}[]  |  "
                    f"Min: [green]{mn:,}[]  |  "
                    f"Max: [red]{mx:,}[]  |  "
                    f"Dias: [bold]{len(vals)}[]"
                )
            except Exception:
                pass

        max_val = max(vals) if vals else 1
        cols = ["Data", "Quantidade", "Grafico", "Diff Media"]
        rows = []
        display = list(zip(dates, vals))[-20:]
        avg = sum(vals) / len(vals) if vals else 0
        for date_val, total in display:
            sc = "green" if total >= avg else "yellow"
            filled = int((total / max_val) * 20) if max_val > 0 else 0
            bar_str = f"[{sc}]{'█' * filled}{'░' * (20 - filled)}[]"
            diff = total - avg
            diff_str = f"[green]+{int(diff):,}[]" if diff > 0 else f"[red]{int(diff):,}[]" if diff < 0 else "[dim]0[]"
            rows.append((str(date_val), f"[bold]{total:,}[]", bar_str, diff_str))
        try:
            _fill_table(self.query_one("#tbl"), cols, rows)
        except Exception:
            pass

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()


class MovimentacoesView(Static):
    _all_data = []
    _filtered_data = []
    _filter_type = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Movimentacoes de Estoque[]", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar...", id="search", classes="filter-input")
        with Horizontal(id="type-filters"):
            yield Button("Todas", id="fb-mt-todos", classes="filter-btn -active")
            yield Button("Entrada", id="fb-mt-in", classes="filter-btn")
            yield Button("Saida", id="fb-mt-out", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("", id="summary")
        yield Label("[dim]  Clique ou use ↑↓ para ver detalhes[]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        d = api_get("/inventory/movements", params={"limit": 100})
        self.__class__._all_data = _get_items(d)
        self._apply_filters()

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
        total = len(filtered)
        try:
            self.query_one("#summary", Label).update(
                f"  [green]\\u2588 {entradas} Entradas[]  "
                f"[red]\\u2588 {saidas} Saidas[]  "
                f"[dim]Total: {total}[]"
            )
        except Exception:
            pass

        cols = ["#", "Tipo", "Quantidade", "Lote", "Data"]
        rows = []
        for i, item in enumerate(filtered[:30], 1):
            qty = item.get("quantity_change", 0)
            sc = "green" if qty > 0 else "red"
            tipo_icon = "[green]>>>[][green]" if qty > 0 else "[red]<<<[][red]"
            rows.append((
                str(i),
                f"{tipo_icon} {item.get('movement_type') or '-'}",
                f"[{sc}][bold]{qty:+,}[][/{sc}]",
                (item.get("batch_id") or "-")[:20],
                (item.get("created_at") or "-")[:16],
            ))
        try:
            _fill_table(self.query_one("#tbl"), cols, rows)
        except Exception:
            pass

    def _show_detail(self, idx):
        if idx is None or idx < 0 or idx >= len(self._filtered_data):
            return
        item = self._filtered_data[idx]
        qty = item.get("quantity_change", 0)
        sc = "green" if qty > 0 else "red"
        tipo = "ENTRADA" if qty > 0 else "SAIDA"
        try:
            self.query_one("#detail", Label).update(
                _detail_box(f"[{sc}]{tipo}[]", [
                    ("Tipo", item.get("movement_type", "-")),
                    ("Quantidade", f"[{sc}][bold]{qty:+,}[][/{sc}]"),
                    ("Lote", item.get("batch_id", "-")),
                    ("Notas", item.get("notes", "-") or "-"),
                    ("Criado", item.get("created_at", "-")),
                    ("ID", item.get("id", "-")),
                ])
            )
        except Exception:
            pass

    @on(DataTable.RowHighlighted, "#tbl")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_detail(event.row_index)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id.startswith("fb-mt-"):
            self._filter_type = btn_id.replace("fb-mt-", "")
            for btn in self.query("#type-filters .filter-btn"):
                btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class UsuariosView(Static):
    _all_data = []

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Usuarios[]", classes="view-title")
        yield DataTable(id="tbl")
        yield Label("[dim]  Clique ou use ↑↓ para ver detalhes[]", id="hint")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        try:
            t = self.query_one("#tbl", DataTable)
            t.add_columns("#", "Nome", "E-mail", "Papel", "Ativo")
            t.cursor_type = "row"
            d = api_get("/users")
            items = _get_items(d)
            self.__class__._all_data = items
            for i, item in enumerate(items, 1):
                ativo = "[green]Ativo[]" if item.get("is_active") else "[red]Inativo[]"
                role = item.get("role", "-")
                if role == "admin":
                    role = "[bold magenta]admin[]"
                elif role == "pharmacist":
                    role = "[cyan]pharmacist[]"
                else:
                    role = f"[dim]{role}[]"
                t.add_row(str(i), item.get("full_name", "-"), item.get("email", "-"), role, ativo)
        except Exception:
            pass

    def _show_detail(self, idx):
        if idx is None or idx < 0 or idx >= len(self._all_data):
            return
        item = self._all_data[idx]
        sc = "green" if item.get("is_active") else "red"
        role = item.get("role", "-")
        if role == "admin":
            role_str = "[bold magenta]Administrador[]"
        elif role == "pharmacist":
            role_str = "[cyan]Farmaceutico[]"
        else:
            role_str = f"[dim]{role}[]"
        try:
            self.query_one("#detail", Label).update(
                _detail_box(item.get("full_name", "-"), [
                    ("E-mail", item.get("email", "-")),
                    ("Papel", role_str),
                    ("Status", f"[{sc}][bold]{'Ativo' if item.get('is_active') else 'Inativo'}[][/{sc}]"),
                    ("Criado em", item.get("created_at", "-") or "-"),
                    ("ID", item.get("id", "-")),
                ])
            )
        except Exception:
            pass

    @on(DataTable.RowHighlighted, "#tbl")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_detail(event.row_index)


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
        border: tall $primary;
        margin: 1 2;
        min-height: 5;
    }
    #hint { color: $text-muted; padding: 0 2; }
    #summary { width: 100%; padding: 0 2; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("[bold cyan]ABHU[]")
                yield Label("[dim]v2.1[]")
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
