"""ABHU TUI - Terminal interface for hospital pharmacy management.
Click rows or press Enter for details. Press 1-9 to navigate views."""

import urllib.request
import urllib.error
import json as _json
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, DataTable, Label, Button, Sparkline, Input, RadioSet, RadioButton
from textual.css.query import NoMatches
from textual.binding import Binding
from textual import on

API_URL = "http://localhost:8000/api/v1"
_token = None
_pg_conn_str = "postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict"


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


def api_post(path, data):
    """POST request to the API. Returns (success, result)."""
    global _token
    if not _token:
        return False, "Nao autenticado"
    try:
        url = f"{API_URL}{path}"
        body = _json.dumps(data).encode()
        req = urllib.request.Request(
            url, data=body,
            headers={
                "Authorization": f"Bearer {_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return True, _json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            err = _json.loads(e.read())
            return False, err.get("detail", str(e))
        except Exception:
            return False, str(e)
    except Exception as e:
        return False, str(e)


def pg_query(sql, params=None):
    """Direct PostgreSQL query for richer data."""
    try:
        import psycopg2
        conn = psycopg2.connect(_pg_conn_str)
        cur = conn.cursor()
        cur.execute(sql, params or ())
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        conn.close()
        return [dict(zip(cols, row)) for row in rows]
    except Exception:
        return []


def do_login():
    global _token
    try:
        data = "username=admin@hospital.gov.br&password=admin123".encode()
        req = urllib.request.Request(
            f"{API_URL}/login", data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            _token = _json.loads(resp.read())["access_token"]
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
    return f"[{color}]{'█' * filled}{'░' * (width - filled)}[/] {int(ratio * 100)}%"


def _fill_table(table, cols, rows):
    """Clear and fill table. Columns added only once."""
    table.clear()
    if not table.columns:
        table.add_columns(*cols)
    for row in rows:
        table.add_row(*row)


# --------------- Views ---------------


class DashboardView(Static):
    def compose(self) -> ComposeResult:
        yield Label("  [bold]Dashboard Geral[/]", classes="view-title")
        yield DataTable(id="tbl")
        yield Label("", id="sparkline-label")
        yield Sparkline([], id="spark")
        yield Label("[dim]  Navegue com 1-8 na barra lateral[/]", id="hint")

    def on_mount(self) -> None:
        try:
            t = self.query_one("#tbl", DataTable)
            t.add_columns("Indicador", "Valor", "Nivel")
            t.cursor_type = "row"
            t.cursor_movement_row = 1
            d = api_get("/dashboard/kpis")
            if d:
                rows = [
                    ("Total de SKUs", f"[bold]{d['total_skus']:,}[/]", bar(d["total_skus"], 500, 15, "green")),
                    ("Estoque Baixo", f"[yellow]{d['low_stock_count']}[/]", bar(d["low_stock_count"], 100, 15, "yellow")),
                    ("Risco de Falta", f"[red]{d['stockout_risk_count']}[/]", bar(d["stockout_risk_count"], 500, 15, "red")),
                    ("Vencendo (30d)", f"[yellow]{d['expiring_soon_count']}[/]", bar(d["expiring_soon_count"], 100, 15, "yellow")),
                    ("Valor Estoque", f"[bold green]R$ {d['total_inventory_value']:,.2f}[/]", ""),
                    ("MAPE Medio", f"[cyan]{d['average_mape']:.2f}%[/]", bar(d["average_mape"] * 100, 500, 15, "blue")),
                    ("Previsoes Hoje", f"[bold]{d['predictions_generated_today']}[/]", ""),
                    ("Alertas Nao Lidos", f"[red]{d['alerts_unacknowledged']}[/]", bar(d["alerts_unacknowledged"], 1000, 15, "red")),
                ]
                for k, v, b in rows:
                    t.add_row(k, v, b)

                # Sparkline: consumo diario
                vals_data = pg_query(
                    "SELECT consumption_date::text as d, SUM(quantity) as total "
                    "FROM consumption GROUP BY consumption_date ORDER BY consumption_date DESC LIMIT 30"
                )
                if vals_data:
                    vals_data.reverse()
                    vals = [int(r["total"]) for r in vals_data]
                    self.query_one("#spark", Sparkline).data = vals
                    avg = sum(vals) // len(vals)
                    self.query_one("#sparkline-label", Label).update(
                        f"  [bold cyan]Consumo diario[/] [dim](ultimos 30 dias) Media: {avg:,}[/]"
                    )
        except Exception:
            pass


class ProdutosView(Static):
    _all_data = []
    _filtered_data = []
    _selected_idx = None
    _filter_risk = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Produtos - Risco de Estoque[/]", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar produto...", id="search", classes="filter-input")
            yield Button("Todos", id="fb-todos", classes="filter-btn -active")
            yield Button("Critical", id="fb-critical", classes="filter-btn")
            yield Button("High", id="fb-high", classes="filter-btn")
            yield Button("Medium", id="fb-medium", classes="filter-btn")
            yield Button("Low", id="fb-low", classes="filter-btn")
        yield DataTable(id="tbl")
        with Horizontal(id="detail-bar"):
            yield Label("[dim]  Use setas + Enter para ver detalhes[/]", id="hint")
            yield Button("Ver Detalhes", id="btn-detail", classes="filter-btn")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        # Query directly from DB for richer data
        self.__class__._all_data = pg_query(
            "SELECT p.id, p.name, p.sku, p.category, p.minimum_stock, p.maximum_stock, "
            "p.supplier_id, s.name as supplier_name, "
            "COALESCE(SUM(ib.quantity), 0) as current_stock "
            "FROM products p "
            "LEFT JOIN inventory_batches ib ON ib.product_id = p.id AND ib.status = 'available' "
            "LEFT JOIN suppliers s ON p.supplier_id = s.id "
            "GROUP BY p.id, p.name, p.sku, p.category, p.minimum_stock, p.maximum_stock, "
            "p.supplier_id, s.name "
            "ORDER BY current_stock ASC"
        )
        # Enrich with risk data from API
        api_risk = api_get("/dashboard/stockout-risk", params={"limit": 200}) or []
        risk_map = {r.get("product_id"): r for r in api_risk}
        for item in self._all_data:
            rid = str(item["id"])
            if rid in risk_map:
                item["risk_level"] = risk_map[rid].get("risk_level", "low")
                item["days_until_stockout"] = risk_map[rid].get("days_until_stockout")
                item["predicted_consumption_7d"] = risk_map[rid].get("predicted_consumption_7d", 0)
            else:
                stock = item["current_stock"]
                min_s = item["minimum_stock"] or 0
                if stock <= 0:
                    item["risk_level"] = "critical"
                elif stock < min_s * 0.3:
                    item["risk_level"] = "critical"
                elif stock < min_s * 0.6:
                    item["risk_level"] = "high"
                elif stock < min_s:
                    item["risk_level"] = "medium"
                else:
                    item["risk_level"] = "low"
                item["days_until_stockout"] = None
                item["predicted_consumption_7d"] = 0
        self._apply_filters()

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        risk = self._filter_risk
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("name") or "").lower() or search in (x.get("sku") or "").lower()]
        if risk and risk != "todos":
            filtered = [x for x in filtered if x.get("risk_level") == risk]
        self.__class__._filtered_data = filtered

        max_stock = max((x.get("current_stock", 0) for x in filtered), default=1) or 1
        cols = ["#", "Produto", "SKU", "Categoria", "Estoque", "Min", "Risco"]
        rows = []
        for i, item in enumerate(filtered, 1):
            risk = item.get("risk_level", "low")
            stock = item.get("current_stock", 0)
            rc = "red" if risk in ("critical", "high") else "yellow" if risk == "medium" else "green"
            rows.append((
                str(i),
                item.get("name", "-")[:35],
                item.get("sku", "-"),
                item.get("category", "-")[:15],
                f"[bold]{int(stock):,}[/]",
                str(int(item.get("minimum_stock", 0) or 0)),
                f"[{rc}]{risk.upper()}[/]",
            ))
        try:
            _fill_table(self.query_one("#tbl"), cols, rows)
        except Exception:
            pass

    def _show_detail(self, idx):
        if idx is None or idx < 0 or idx >= len(self._filtered_data):
            return
        item = self._filtered_data[idx]
        risk = item.get("risk_level", "low")
        rc = "red" if risk in ("critical", "high") else "yellow" if risk == "medium" else "green"
        stock = int(item.get("current_stock", 0))
        min_s = int(item.get("minimum_stock", 0) or 0)
        max_s = int(item.get("maximum_stock", 0) or 0)
        cons7 = int(item.get("predicted_consumption_7d", 0) or 0)
        days = item.get("days_until_stockout", "-")
        pct = int(stock / max(max_s, 1) * 100) if max_s else 0
        stock_bar = bar(stock, max(max_s, 1), 25, rc)
        # Compute consumption last 30 days from DB
        consumption = pg_query(
            "SELECT SUM(quantity) as total FROM consumption WHERE product_id = %s "
            "AND consumption_date >= CURRENT_DATE - INTERVAL '30 days'",
            (str(item["id"]),)
        )
        cons30 = int(consumption[0]["total"]) if consumption and consumption[0]["total"] else 0

        lines = [
            ("SKU", item.get("sku", "-")),
            ("Categoria", item.get("category", "-")),
            ("Fornecedor", item.get("supplier_name", "-") or "-"),
            ("Risco", f"[{rc}][bold]{risk.upper()}[/][/{rc}]"),
            ("Estoque Atual", f"[bold]{stock:,}[/]  {stock_bar}"),
            ("Estoque Min", f"{min_s:,}  {'[red]ABAIXO![/]' if stock < min_s else '[green]OK[/]'}"),
            ("Estoque Max", f"{max_s:,}"),
            ("Pct. Capacidade", f"{pct}%"),
            ("Consumo 7d", f"{cons7:,}" if cons7 else "-"),
            ("Consumo 30d", f"{cons30:,}"),
            ("Dias p/ falta", f"[bold]{days}[/]" if days else "-"),
        ]
        try:
            self.query_one("#detail", Label).update(
                "  [bold cyan]" + item.get("name", "-") + "[/]\n" +
                "\n".join(f"  [bold]{k}:[/] {v}" for k, v in lines)
            )
        except Exception:
            pass

    def _on_detail_click(self):
        """Called by Enter key or button."""
        t = self.query_one("#tbl", DataTable)
        idx = t.cursor_row
        self._selected_idx = idx
        self._show_detail(idx)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-detail":
            self._on_detail_click()
        elif btn_id.startswith("fb-"):
            self._filter_risk = btn_id.replace("fb-", "")
            for btn in self.query(".filter-btn"):
                if btn.id != "btn-detail":
                    btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class AlertasView(Static):
    _all_data = []
    _filtered_data = []
    _selected_idx = None
    _filter_sev = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Alertas Ativos[/]", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar mensagem...", id="search", classes="filter-input")
        with Horizontal(id="sev-filters"):
            yield Button("Todos", id="fb-sev-todos", classes="filter-btn -active")
            yield Button("Critical", id="fb-sev-critical", classes="filter-btn")
            yield Button("Warning", id="fb-sev-warning", classes="filter-btn")
            yield Button("Info", id="fb-sev-info", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("", id="summary")
        with Horizontal(id="detail-bar"):
            yield Label("[dim]  Use setas + Enter ou clique Ver Detalhes[/]", id="hint")
            yield Button("Ver Detalhes", id="btn-detail", classes="filter-btn")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        # Rich query from DB
        self.__class__._all_data = pg_query(
            "SELECT a.id, a.alert_type, a.severity, a.message, a.product_id, "
            "a.acknowledged, a.acknowledged_by, a.created_at::text, a.updated_at::text, "
            "p.name as product_name, p.sku "
            "FROM alerts a "
            "LEFT JOIN products p ON a.product_id = p.id "
            "ORDER BY "
            "CASE a.severity WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END, "
            "a.created_at DESC "
            "LIMIT 100"
        )
        self._apply_filters()

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        sev = self._filter_sev
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("message") or "").lower() or search in (x.get("product_name") or "").lower()]
        if sev and sev != "todos":
            filtered = [x for x in filtered if x.get("severity") == sev]
        self.__class__._filtered_data = filtered

        sc = {"critical": 0, "warning": 0, "info": 0}
        for item in filtered:
            sc[item.get("severity", "info")] = sc.get(item.get("severity", "info"), 0) + 1
        try:
            self.query_one("#summary", Label).update(
                f"  [red]\\u2588 {sc.get('critical',0)} Criticos[/]  "
                f"[yellow]\\u2588 {sc.get('warning',0)} Avisos[/]  "
                f"[blue]\\u2588 {sc.get('info',0)} Info[/]  "
                f"[dim]Filtrados: {len(filtered)}/{len(self._all_data)}[/]"
            )
        except Exception:
            pass

        cols = ["#", "Sev", "Tipo", "Produto", "Mensagem", "Data"]
        rows = []
        for i, item in enumerate(filtered[:30], 1):
            sev = item.get("severity", "info")
            if sev == "critical":
                sc_str = "[red][bold]CRIT[/bold][/]"
            elif sev == "warning":
                sc_str = "[yellow]WARN[/]"
            else:
                sc_str = "[blue]INFO[/]"
            rows.append((
                str(i),
                sc_str,
                item.get("alert_type", "-")[:20],
                (item.get("product_name") or "-")[:25],
                (item.get("message") or "-")[:40],
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
        ack = "[green]Reconhecido[/]" if item.get("acknowledged") else "[red]Pendente[/]"
        # Get product info
        pname = item.get("product_name", "-") or "-"
        psku = item.get("sku", "-") or "-"
        lines = [
            ("Tipo", item.get("alert_type", "-")),
            ("Severidade", f"[{sc}][bold]{sev.upper()}[/][/{sc}]"),
            ("Mensagem", item.get("message", "-")),
            ("Produto", f"{pname} ({psku})"),
            ("Produto ID", str(item.get("product_id", "-"))),
            ("Criado em", item.get("created_at", "-")),
            ("Atualizado", item.get("updated_at", "-") or "-"),
            ("Status", ack),
            ("Reconhecido por", item.get("acknowledged_by") or "-"),
            ("Alerta ID", str(item.get("id", "-"))),
        ]
        try:
            self.query_one("#detail", Label).update(
                "  [bold cyan]Detalhe do Alerta[/]\n" +
                "\n".join(f"  [bold]{k}:[/] {v}" for k, v in lines)
            )
        except Exception:
            pass

    def _on_detail_click(self):
        t = self.query_one("#tbl", DataTable)
        self._show_detail(t.cursor_row)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-detail":
            self._on_detail_click()
        elif btn_id.startswith("fb-sev-"):
            self._filter_sev = btn_id.replace("fb-sev-", "")
            for btn in self.query("#sev-filters .filter-btn"):
                if btn.id != "btn-detail":
                    btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class VencimentoView(Static):
    _all_data = []
    _filtered_data = []
    _selected_idx = None
    _filter_urg = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Lotes Vencendo[/]", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar produto...", id="search", classes="filter-input")
        with Horizontal(id="urg-filters"):
            yield Button("Todos", id="fb-urg-todos", classes="filter-btn -active")
            yield Button("Critico <=30d", id="fb-urg-crit", classes="filter-btn")
            yield Button("Aviso 31-60d", id="fb-urg-warn", classes="filter-btn")
            yield Button("OK >60d", id="fb-urg-ok", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("", id="summary")
        with Horizontal(id="detail-bar"):
            yield Label("[dim]  Use setas + Enter ou clique Ver Detalhes[/]", id="hint")
            yield Button("Ver Detalhes", id="btn-detail", classes="filter-btn")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        self.__class__._all_data = pg_query(
            "SELECT ib.id, ib.batch_number, ib.quantity, ib.expiry_date::text, "
            "ib.status, ib.warehouse_id, w.name as warehouse_name, "
            "p.name as product_name, p.sku, p.category, "
            "(ib.expiry_date - CURRENT_DATE) as days_until_expiry "
            "FROM inventory_batches ib "
            "JOIN products p ON ib.product_id = p.id "
            "LEFT JOIN warehouses w ON ib.warehouse_id = w.id "
            "WHERE ib.expiry_date <= CURRENT_DATE + INTERVAL '90 days' "
            "AND ib.status = 'available' "
            "ORDER BY ib.expiry_date ASC LIMIT 100"
        )
        self._apply_filters()

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        urg = self._filter_urg
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("product_name") or "").lower() or search in (x.get("sku") or "").lower()]
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
        total_qty = sum(x.get("quantity", 0) for x in filtered)
        try:
            self.query_one("#summary", Label).update(
                f"  [red]\\u2588 {crit} Criticos[/]  "
                f"[yellow]\\u2588 {warn} Avisos[/]  "
                f"[green]\\u2588 {ok} OK[/]  "
                f"[dim]Total: {len(filtered)} lotes, {total_qty:,} unidades[/]"
            )
        except Exception:
            pass

        cols = ["#", "Produto", "SKU", "Lote", "Qtd", "Vencimento", "Dias"]
        rows = []
        for i, item in enumerate(filtered[:30], 1):
            days = item["days_until_expiry"]
            if days <= 30:
                sc, label = "red", "CRIT"
            elif days <= 60:
                sc, label = "yellow", "AVISO"
            else:
                sc, label = "green", "OK"
            rows.append((
                str(i),
                (item.get("product_name") or "-")[:30],
                item.get("sku", "-"),
                item.get("batch_number", "-")[:15],
                f"[bold]{item.get('quantity', 0):,}[/]",
                item.get("expiry_date", "-"),
                f"[{sc}][bold]{days}[/][/] {label}",
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
        urg_bar = bar(max(0, 90 - days), 90, 25, sc)
        qty = item.get("quantity", 0)
        cost_data = pg_query(
            "SELECT unit_cost FROM inventory_batches WHERE id = %s", (str(item["id"]),)
        )
        unit_cost = float(cost_data[0]["unit_cost"]) if cost_data else 0
        total_val = qty * unit_cost
        lines = [
            ("Produto", item.get("product_name", "-")),
            ("SKU", item.get("sku", "-")),
            ("Categoria", item.get("category", "-")),
            ("Lote", item.get("batch_number", "-")),
            ("Status", item.get("status", "-")),
            ("Quantidade", f"[bold]{qty:,}[/]"),
            ("Custo Unit.", f"R${unit_cost:.2f}" if unit_cost else "-"),
            ("Valor Total", f"[bold green]R${total_val:,.2f}[/]" if total_val else "-"),
            ("Vencimento", f"[bold]{item.get('expiry_date', '-')}[/]"),
            ("Dias Restantes", f"[{sc}][bold]{days}[/][/] ({label})"),
            ("Urgencia", urg_bar),
            ("Almoxarifado", item.get("warehouse_name", "-") or "-"),
        ]
        try:
            self.query_one("#detail", Label).update(
                "  [bold cyan]Detalhe do Lote[/]\n" +
                "\n".join(f"  [bold]{k}:[/] {v}" for k, v in lines)
            )
        except Exception:
            pass

    def _on_detail_click(self):
        t = self.query_one("#tbl", DataTable)
        self._show_detail(t.cursor_row)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-detail":
            self._on_detail_click()
        elif btn_id.startswith("fb-urg-"):
            self._filter_urg = btn_id.replace("fb-urg-", "")
            for btn in self.query("#urg-filters .filter-btn"):
                if btn.id != "btn-detail":
                    btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class EstoqueView(Static):
    _all_data = []
    _filtered_data = []
    _selected_idx = None
    _filter_status = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Lotes em Estoque[/]", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar produto...", id="search", classes="filter-input")
        with Horizontal(id="status-filters"):
            yield Button("Todos", id="fb-st-todos", classes="filter-btn -active")
            yield Button("Disponivel", id="fb-st-available", classes="filter-btn")
            yield Button("Expirado", id="fb-st-expired", classes="filter-btn")
            yield Button("Consumido", id="fb-st-consumed", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("", id="summary")
        with Horizontal(id="detail-bar"):
            yield Label("[dim]  Use setas + Enter ou clique Ver Detalhes[/]", id="hint")
            yield Button("Ver Detalhes", id="btn-detail", classes="filter-btn")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        self.__class__._all_data = pg_query(
            "SELECT ib.id, ib.batch_number, ib.quantity, ib.unit_cost::float, "
            "ib.expiry_date::text, ib.status, ib.warehouse_id, "
            "w.name as warehouse_name, "
            "p.name as product_name, p.sku, p.category "
            "FROM inventory_batches ib "
            "JOIN products p ON ib.product_id = p.id "
            "LEFT JOIN warehouses w ON ib.warehouse_id = w.id "
            "ORDER BY ib.expiry_date ASC LIMIT 100"
        )
        self._apply_filters()

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        status = self._filter_status
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("name") or "").lower() or search in (x.get("product_name") or "").lower() or search in (x.get("sku") or "").lower()]
        if status and status != "todos":
            filtered = [x for x in filtered if x.get("status") == status]
        self.__class__._filtered_data = filtered

        total_val = sum(x.get("quantity", 0) * (x.get("unit_cost") or 0) for x in filtered)
        avail = sum(1 for x in filtered if x.get("status") == "available")
        exp = sum(1 for x in filtered if x.get("status") == "expired")
        cons = sum(1 for x in filtered if x.get("status") == "consumed")
        try:
            self.query_one("#summary", Label).update(
                f"  [green]\\u2588 {avail} Disponiveis[/]  "
                f"[red]\\u2588 {exp} Expirados[/]  "
                f"[blue]\\u2588 {cons} Consumidos[/]  "
                f"[dim]Valor: R${total_val:,.2f} | Total: {len(filtered)} lotes[/]"
            )
        except Exception:
            pass

        max_qty = max((x.get("quantity", 0) for x in filtered), default=1) or 1
        cols = ["#", "Produto", "SKU", "Lote", "Qtd", "Custo", "Valor", "Vencimento"]
        rows = []
        for i, item in enumerate(filtered[:30], 1):
            sc = "green" if item["status"] == "available" else "red" if item["status"] == "expired" else "blue"
            qty = item.get("quantity", 0)
            cost = item.get("unit_cost") or 0
            valor = qty * cost
            rows.append((
                str(i),
                (item.get("product_name") or "-")[:30],
                item.get("sku", "-"),
                item.get("batch_number", "-")[:15],
                f"[bold]{qty:,}[/]",
                f"R${cost:.2f}",
                f"R${valor:,.2f}",
                f"[{sc}]{item.get('expiry_date', '-')}[/]",
            ))
        try:
            _fill_table(self.query_one("#tbl"), cols, rows)
        except Exception:
            pass

    def _show_detail(self, idx):
        if idx is None or idx < 0 or idx >= len(self._filtered_data):
            return
        item = self._filtered_data[idx]
        sc = "green" if item["status"] == "available" else "red" if item["status"] == "expired" else "blue"
        qty = item.get("quantity", 0)
        cost = item.get("unit_cost") or 0
        valor = qty * cost
        # Count movements for this batch
        movs = pg_query(
            "SELECT COUNT(*) as cnt FROM inventory_movements WHERE batch_id = %s",
            (str(item["id"]),)
        )
        mov_count = movs[0]["cnt"] if movs else 0
        lines = [
            ("Produto", item.get("product_name", "-")),
            ("SKU", item.get("sku", "-")),
            ("Categoria", item.get("category", "-")),
            ("Lote", item.get("batch_number", "-")),
            ("Status", f"[{sc}][bold]{item.get('status', '-')}[/][/{sc}]"),
            ("Quantidade", f"[bold]{qty:,}[/]"),
            ("Custo Unit.", f"R${cost:.2f}" if cost else "-"),
            ("Valor Total", f"[bold green]R${valor:,.2f}[/]" if valor else "-"),
            ("Vencimento", f"[bold]{item.get('expiry_date', '-')}[/]"),
            ("Almoxarifado", item.get("warehouse_name", "-") or "-"),
            ("Movimentacoes", f"{mov_count} registradas"),
            ("ID Lote", str(item.get("id", "-"))),
        ]
        try:
            self.query_one("#detail", Label).update(
                "  [bold cyan]Detalhe do Lote[/]\n" +
                "\n".join(f"  [bold]{k}:[/] {v}" for k, v in lines)
            )
        except Exception:
            pass

    def _on_detail_click(self):
        t = self.query_one("#tbl", DataTable)
        self._show_detail(t.cursor_row)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-detail":
            self._on_detail_click()
        elif btn_id.startswith("fb-st-"):
            self._filter_status = btn_id.replace("fb-st-", "")
            for btn in self.query("#status-filters .filter-btn"):
                if btn.id != "btn-detail":
                    btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class ConsumoView(Static):
    _all_data = []

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Consumo Historico[/]", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar produto...", id="search", classes="filter-input")
        yield DataTable(id="tbl")
        yield Sparkline([], id="spark")
        yield Label("", id="stats")
        with Horizontal(id="detail-bar"):
            yield Label("[dim]  Use setas + Enter para ver detalhes do produto[/]", id="hint")
            yield Button("Ver Detalhes", id="btn-detail", classes="filter-btn")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        # Top products by consumption
        self.__class__._all_data = pg_query(
            "SELECT p.name as product_name, p.sku, p.category, "
            "SUM(c.quantity) as total_qty, COUNT(DISTINCT c.consumption_date) as days, "
            "ROUND(AVG(c.quantity)::numeric, 1) as avg_qty, "
            "MIN(c.quantity) as min_qty, MAX(c.quantity) as max_qty, "
            "p.id as product_id "
            "FROM consumption c "
            "JOIN products p ON c.product_id = p.id "
            "GROUP BY p.id, p.name, p.sku, p.category "
            "ORDER BY total_qty DESC LIMIT 50"
        )
        self._apply_filters()

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("product_name") or "").lower() or search in (x.get("sku") or "").lower()]
        if not filtered:
            filtered = self._all_data

        # Sparkline: daily total consumption
        daily = pg_query(
            "SELECT consumption_date::text as d, SUM(quantity) as total "
            "FROM consumption GROUP BY consumption_date ORDER BY consumption_date DESC LIMIT 60"
        )
        if daily:
            daily.reverse()
            vals = [int(r["total"]) for r in daily]
            try:
                self.query_one("#spark", Sparkline).data = vals
            except Exception:
                pass
            avg = sum(vals) // len(vals)
            mn, mx = min(vals), max(vals)
            try:
                self.query_one("#stats", Label).update(
                    f"  [bold cyan]Consumo[/]  "
                    f"Media: [bold]{avg:,}[/]  |  "
                    f"Min: [green]{mn:,}[/]  |  "
                    f"Max: [red]{mx:,}[/]  |  "
                    f"Dias: [bold]{len(vals)}[/]"
                )
            except Exception:
                pass

        cols = ["#", "Produto", "SKU", "Total", "Dias", "Media", "Min", "Max"]
        rows = []
        for i, item in enumerate(filtered[:30], 1):
            total = int(item.get("total_qty", 0))
            days = int(item.get("days", 1))
            avg = float(item.get("avg_qty", 0) or 0)
            rows.append((
                str(i),
                (item.get("product_name") or "-")[:35],
                item.get("sku", "-"),
                f"[bold]{total:,}[/]",
                str(days),
                f"{avg:,.1f}",
                f"[green]{int(item.get('min_qty', 0) or 0):,}[/]",
                f"[red]{int(item.get('max_qty', 0) or 0):,}[/]",
            ))
        try:
            _fill_table(self.query_one("#tbl"), cols, rows)
        except Exception:
            pass

    def _on_detail_click(self):
        t = self.query_one("#tbl", DataTable)
        idx = t.cursor_row
        if idx < 0 or idx >= len(self._all_data):
            return
        item = self._all_data[idx]
        pid = item.get("product_id")
        # Get daily breakdown for this product
        daily = pg_query(
            "SELECT consumption_date::text as d, SUM(quantity) as total "
            "FROM consumption WHERE product_id = %s "
            "GROUP BY consumption_date ORDER BY consumption_date DESC LIMIT 14",
            (str(pid),)
        )
        daily_str = ", ".join(f"{r['d']}: {r['total']}" for r in daily[:7]) if daily else "-"
        # Get total value
        total_qty = int(item.get("total_qty", 0))
        # Get stock info
        stock_info = pg_query(
            "SELECT COALESCE(SUM(quantity), 0) as stock FROM inventory_batches "
            "WHERE product_id = %s AND status = 'available'",
            (str(pid),)
        )
        current_stock = int(stock_info[0]["stock"]) if stock_info else 0
        lines = [
            ("Produto", item.get("product_name", "-")),
            ("SKU", item.get("sku", "-")),
            ("Categoria", item.get("category", "-")),
            ("Consumo Total", f"[bold]{total_qty:,}[/] unidades"),
            ("Dias com Dados", str(item.get("days", 0))),
            ("Media/Dia", f"{float(item.get('avg_qty', 0) or 0):,.1f}"),
            ("Min/Dia", f"[green]{int(item.get('min_qty', 0) or 0):,}[/]"),
            ("Max/Dia", f"[red]{int(item.get('max_qty', 0) or 0):,}[/]"),
            ("Estoque Atual", f"[bold]{current_stock:,}[/]"),
            ("Dias de Cobertura", f"{current_stock // max(int(float(item.get('avg_qty', 1) or 1)), 1)} dias"),
            ("Ultimos 7 dias", daily_str),
        ]
        try:
            self.query_one("#detail", Label).update(
                "  [bold cyan]Detalhe do Consumo[/]\n" +
                "\n".join(f"  [bold]{k}:[/] {v}" for k, v in lines)
            )
        except Exception:
            pass

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-detail":
            self._on_detail_click()


class MovimentacoesView(Static):
    _all_data = []
    _filtered_data = []
    _selected_idx = None
    _filter_type = "todos"

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Movimentacoes de Estoque[/]", classes="view-title")
        with Horizontal(id="filters"):
            yield Input(placeholder="Buscar...", id="search", classes="filter-input")
        with Horizontal(id="type-filters"):
            yield Button("Todas", id="fb-mt-todos", classes="filter-btn -active")
            yield Button("Entrada", id="fb-mt-in", classes="filter-btn")
            yield Button("Saida", id="fb-mt-out", classes="filter-btn")
        yield DataTable(id="tbl")
        yield Label("", id="summary")
        with Horizontal(id="detail-bar"):
            yield Label("[dim]  Use setas + Enter ou clique Ver Detalhes[/]", id="hint")
            yield Button("Ver Detalhes", id="btn-detail", classes="filter-btn")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        self.__class__._all_data = pg_query(
            "SELECT im.id, im.movement_type, im.quantity_change, im.notes, "
            "im.created_at::text, im.batch_id, "
            "ib.batch_number, ib.quantity as batch_qty, "
            "p.name as product_name, p.sku, "
            "w.name as warehouse_name "
            "FROM inventory_movements im "
            "JOIN inventory_batches ib ON im.batch_id = ib.id "
            "JOIN products p ON ib.product_id = p.id "
            "LEFT JOIN warehouses w ON ib.warehouse_id = w.id "
            "ORDER BY im.created_at DESC LIMIT 100"
        )
        self._apply_filters()

    def _apply_filters(self):
        search = self.query_one("#search", Input).value.lower()
        mtype = self._filter_type
        filtered = self._all_data
        if search:
            filtered = [x for x in filtered if search in (x.get("product_name") or "").lower() or search in (x.get("notes") or "").lower() or search in (x.get("sku") or "").lower()]
        if mtype and mtype != "todos":
            filtered = [x for x in filtered if x.get("movement_type") == mtype]
        self.__class__._filtered_data = filtered

        entradas = sum(1 for x in filtered if x.get("movement_type") == "in")
        saidas = sum(1 for x in filtered if x.get("movement_type") == "out")
        total = len(filtered)
        try:
            self.query_one("#summary", Label).update(
                f"  [green]\\u2588 {entradas} Entradas[/]  "
                f"[red]\\u2588 {saidas} Saidas[/]  "
                f"[dim]Total: {total}[/]"
            )
        except Exception:
            pass

        cols = ["#", "Tipo", "Produto", "Quantidade", "Lote", "Data"]
        rows = []
        for i, item in enumerate(filtered[:30], 1):
            qty = item.get("quantity_change", 0)
            sc = "green" if qty > 0 else "red"
            tipo = "[green]>>>[/]" if qty > 0 else "[red]<<<[/]"
            rows.append((
                str(i),
                f"{tipo} {item.get('movement_type', '-')}",
                (item.get("product_name") or "-")[:30],
                f"[{sc}][bold]{qty:+,}[/][/{sc}]",
                item.get("batch_number", "-")[:15],
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
        lines = [
            ("Tipo", f"[{sc}][bold]{tipo}[/][/{sc}]"),
            ("Produto", item.get("product_name", "-")),
            ("SKU", item.get("sku", "-")),
            ("Quantidade", f"[{sc}][bold]{qty:+,}[/][/{sc}]"),
            ("Lote", item.get("batch_number", "-")),
            ("Qtd Lote", f"{item.get('batch_qty', 0):,}"),
            ("Almoxarifado", item.get("warehouse_name", "-") or "-"),
            ("Notas", item.get("notes", "-") or "-"),
            ("Data", item.get("created_at", "-")),
            ("ID", str(item.get("id", "-"))),
        ]
        try:
            self.query_one("#detail", Label).update(
                "  [bold cyan]Detalhe da Movimentacao[/]\n" +
                "\n".join(f"  [bold]{k}:[/] {v}" for k, v in lines)
            )
        except Exception:
            pass

    def _on_detail_click(self):
        t = self.query_one("#tbl", DataTable)
        self._show_detail(t.cursor_row)

    @on(Input.Changed, "#search")
    def on_search(self):
        self._apply_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-detail":
            self._on_detail_click()
        elif btn_id.startswith("fb-mt-"):
            self._filter_type = btn_id.replace("fb-mt-", "")
            for btn in self.query("#type-filters .filter-btn"):
                if btn.id != "btn-detail":
                    btn.classes = "filter-btn -active" if btn.id == btn_id else "filter-btn"
            self._apply_filters()


class UsuariosView(Static):
    _all_data = []

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Usuarios do Sistema[/]", classes="view-title")
        yield DataTable(id="tbl")
        with Horizontal(id="detail-bar"):
            yield Label("[dim]  Use setas + Enter ou clique Ver Detalhes[/]", id="hint")
            yield Button("Ver Detalhes", id="btn-detail", classes="filter-btn")
        yield Label("", id="detail")

    def on_mount(self) -> None:
        t = self.query_one("#tbl", DataTable)
        t.add_columns("#", "Nome", "E-mail", "Papel", "Ativo", "Criado em")
        t.cursor_type = "row"
        d = api_get("/users")
        items = _get_items(d)
        self.__class__._all_data = items
        for i, item in enumerate(items, 1):
            ativo = "[green]Ativo[/]" if item.get("is_active") else "[red]Inativo[/]"
            role = item.get("role", "-")
            if role == "admin":
                role = "[bold magenta]admin[/]"
            elif role == "pharmacist":
                role = "[cyan]pharmacist[/]"
            else:
                role = f"[dim]{role}[/]"
            t.add_row(
                str(i),
                item.get("full_name", "-"),
                item.get("email", "-"),
                role,
                ativo,
                (item.get("created_at") or "-")[:10],
            )

    def _on_detail_click(self):
        t = self.query_one("#tbl", DataTable)
        idx = t.cursor_row
        if idx < 0 or idx >= len(self._all_data):
            return
        item = self._all_data[idx]
        sc = "green" if item.get("is_active") else "red"
        role = item.get("role", "-")
        if role == "admin":
            role_str = "[bold magenta]Administrador[/]"
        elif role == "pharmacist":
            role_str = "[cyan]Farmaceutico[/]"
        else:
            role_str = f"[dim]{role}[/]"
        # Count alerts acknowledged by this user
        alerts = pg_query(
            "SELECT COUNT(*) as cnt FROM alerts WHERE acknowledged_by = %s",
            (item.get("id"),)
        )
        alert_count = alerts[0]["cnt"] if alerts else 0
        lines = [
            ("Nome", item.get("full_name", "-")),
            ("E-mail", item.get("email", "-")),
            ("Papel", role_str),
            ("Status", f"[{sc}][bold]{'Ativo' if item.get('is_active') else 'Inativo'}[/][/{sc}]"),
            ("Alertas Reconhecidos", f"{alert_count}"),
            ("Criado em", item.get("created_at", "-") or "-"),
            ("Atualizado em", item.get("updated_at", "-") or "-"),
            ("ID", item.get("id", "-")),
        ]
        try:
            self.query_one("#detail", Label).update(
                "  [bold cyan]Detalhe do Usuario[/]\n" +
                "\n".join(f"  [bold]{k}:[/] {v}" for k, v in lines)
            )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-detail":
            self._on_detail_click()


# --------------- Cadastro ---------------

CATEGORIES = [
    "antibiotic", "analgesic", "antithrombotic", "beta_blocker",
    "ppi", "bronchodilator", "psycholeptic", "ace_inhibitor",
    "corticosteroid", "other",
]

MOVEMENT_TYPES = ["in", "out", "adjustment", "transfer", "loss"]


class CadastroView(Static):
    """Tela de cadastro: Produto, Lote, Movimentacao."""
    _current_tab = "produto"
    _products_cache = []
    _warehouses_cache = []
    _selected_product_id = None
    _selected_warehouse_id = None
    _selected_category = "other"
    _selected_movement_type = "in"
    _batches_cache = []

    def compose(self) -> ComposeResult:
        yield Label("  [bold]Cadastro[/]", classes="view-title")
        with Horizontal(id="tab-bar"):
            yield Button("Novo Produto", id="tab-produto", classes="filter-btn -active")
            yield Button("Novo Lote", id="tab-lote", classes="filter-btn")
            yield Button("Nova Movimentacao", id="tab-mov", classes="filter-btn")
        yield Label("", id="msg")
        # --- Tab: Produto ---
        with Vertical(id="form-produto", classes="form-panel"):
            yield Label("[bold]Cadastrar Novo Produto[/]", classes="form-title")
            with Horizontal():
                yield Label("Nome:", classes="field-label")
                yield Input(placeholder="Nome do produto", id="prod-name", classes="field-input")
            with Horizontal():
                yield Label("SKU:", classes="field-label")
                yield Input(placeholder="Codigo SKU", id="prod-sku", classes="field-input")
            with Horizontal():
                yield Label("Nome Generic:", classes="field-label")
                yield Input(placeholder="Nome generico (opcional)", id="prod-generic", classes="field-input")
            with Horizontal():
                yield Label("Categoria:", classes="field-label")
                yield Button("other", id="cat-btn", classes="filter-btn -active")
            with Horizontal():
                yield Label("Custo Unit.:", classes="field-label")
                yield Input(placeholder="0.00", id="prod-cost", classes="field-input")
            with Horizontal():
                yield Label("Est. Min:", classes="field-label")
                yield Input(placeholder="10", id="prod-min", classes="field-input")
                yield Label("Est. Max:", classes="field-label")
                yield Input(placeholder="100", id="prod-max", classes="field-input")
            with Horizontal():
                yield Label("Unidade:", classes="field-label")
                yield Input(placeholder="un", id="prod-unit", classes="field-input")
                yield Label("Prazo Entrega:", classes="field-label")
                yield Input(placeholder="7", id="prod-lead", classes="field-input")
            yield Button("Cadastrar Produto", id="btn-save-product", classes="save-btn")
        # --- Tab: Lote ---
        with Vertical(id="form-lote", classes="form-panel hidden"):
            yield Label("[bold]Cadastrar Novo Lote[/]", classes="form-title")
            yield Label("[dim]Produtos existentes (clique para selecionar):[/]")
            yield DataTable(id="prod-select", classes="select-table")
            yield Label("Produto selecionado: [dim]nenhum[/]", id="selected-prod-label")
            with Horizontal():
                yield Label("Lote:", classes="field-label")
                yield Input(placeholder="Numero do lote", id="batch-num", classes="field-input")
            with Horizontal():
                yield Label("Quantidade:", classes="field-label")
                yield Input(placeholder="100", id="batch-qty", classes="field-input")
            with Horizontal():
                yield Label("Validade:", classes="field-label")
                yield Input(placeholder="2027-12-31", id="batch-expiry", classes="field-input")
            with Horizontal():
                yield Label("Fabricacao:", classes="field-label")
                yield Input(placeholder="2026-01-15 (opcional)", id="batch-mfg", classes="field-input")
            with Horizontal():
                yield Label("Custo Unit.:", classes="field-label")
                yield Input(placeholder="0.00", id="batch-cost", classes="field-input")
            yield Label("[dim]Almoxarifados:[/]")
            yield DataTable(id="wh-select", classes="select-table")
            yield Label("Almoxarifado selecionado: [dim]nenhum[/]", id="selected-wh-label")
            yield Button("Cadastrar Lote", id="btn-save-batch", classes="save-btn")
        # --- Tab: Movimentacao ---
        with Vertical(id="form-mov", classes="form-panel hidden"):
            yield Label("[bold]Registrar Movimentacao[/]", classes="form-title")
            yield Label("[dim]Lotes existentes (clique para selecionar):[/]")
            yield DataTable(id="batch-select", classes="select-table")
            yield Label("Lote selecionado: [dim]nenhum[/]", id="selected-batch-label")
            with Horizontal():
                yield Label("Tipo:", classes="field-label")
                yield Button("in", id="mov-btn", classes="filter-btn -active")
            with Horizontal():
                yield Label("Quantidade:", classes="field-label")
                yield Input(placeholder="+100 ou -50", id="mov-qty", classes="field-input")
            with Horizontal():
                yield Label("Notas:", classes="field-label")
                yield Input(placeholder="Observacoes (opcional)", id="mov-notes", classes="field-input")
            yield Button("Registrar Movimentacao", id="btn-save-mov", classes="save-btn")

    def on_mount(self) -> None:
        # Load products and warehouses for selection
        self.__class__._products_cache = pg_query(
            "SELECT id, name, sku, category FROM products WHERE is_active = true ORDER BY name LIMIT 50"
        )
        self.__class__._warehouses_cache = pg_query(
            "SELECT id, name, location FROM warehouses ORDER BY name"
        )
        self._fill_product_select()
        self._fill_warehouse_select()
        self._fill_batch_select()

    def _fill_product_select(self):
        try:
            t = self.query_one("#prod-select", DataTable)
            t.add_columns("Produto", "SKU", "Categoria")
            t.cursor_type = "row"
            for p in self._products_cache[:30]:
                t.add_row(
                    (p.get("name") or "-")[:35],
                    p.get("sku", "-"),
                    p.get("category", "-"),
                )
        except Exception:
            pass

    def _fill_warehouse_select(self):
        try:
            t = self.query_one("#wh-select", DataTable)
            t.add_columns("Almoxarifado", "Localizacao")
            t.cursor_type = "row"
            for w in self._warehouses_cache:
                t.add_row(
                    w.get("name", "-"),
                    w.get("location", "-") or "-",
                )
        except Exception:
            pass

    def _fill_batch_select(self):
        try:
            batches = pg_query(
                "SELECT ib.id, ib.batch_number, p.name, ib.quantity, ib.status "
                "FROM inventory_batches ib JOIN products p ON ib.product_id = p.id "
                "WHERE ib.status = 'available' ORDER BY p.name LIMIT 50"
            )
            t = self.query_one("#batch-select", DataTable)
            t.add_columns("Produto", "Lote", "Qtd", "Status")
            t.cursor_type = "row"
            for b in batches:
                sc = "green" if b["status"] == "available" else "yellow"
                t.add_row(
                    (b.get("name") or "-")[:30],
                    b.get("batch_number", "-"),
                    f"{b.get('quantity', 0):,}",
                    f"[{sc}]{b.get('status', '-')}[/]",
                )
            self.__class__._batches_cache = batches
        except Exception:
            self.__class__._batches_cache = []

    def _show_tab(self, tab: str):
        self.__class__._current_tab = tab
        for name in ("produto", "lote", "mov"):
            try:
                panel = self.query_one(f"#form-{name}", Vertical)
                panel.classes = "form-panel" if name == tab else "form-panel hidden"
            except NoMatches:
                pass
        for name in ("produto", "lote", "mov"):
            try:
                btn = self.query_one(f"#tab-{name}", Button)
                btn.classes = "filter-btn -active" if name == tab else "filter-btn"
            except NoMatches:
                pass

    def _set_msg(self, text, color="green"):
        try:
            self.query_one("#msg", Label).update(f"  [{color}]{text}[/]")
        except Exception:
            pass

    # ---- Produto ----

    def _save_product(self):
        name = self.query_one("#prod-name", Input).value.strip()
        sku = self.query_one("#prod-sku", Input).value.strip()
        if not name or not sku:
            self._set_msg("Preencha Nome e SKU!", "red")
            return
        generic = self.query_one("#prod-generic", Input).value.strip() or None
        cost = float(self.query_one("#prod-cost", Input).value or "0")
        min_s = int(self.query_one("#prod-min", Input).value or "10")
        max_s = int(self.query_one("#prod-max", Input).value or "100")
        unit = self.query_one("#prod-unit", Input).value.strip() or "un"
        lead = int(self.query_one("#prod-lead", Input).value or "7")
        payload = {
            "sku": sku,
            "name": name,
            "generic_name": generic,
            "category": self._selected_category,
            "unit": unit,
            "unit_cost": str(cost),
            "min_stock_level": min_s,
            "max_stock_level": max_s,
            "lead_time_days": lead,
            "controlled_substance": False,
        }
        ok, result = api_post("/products", payload)
        if ok:
            self._set_msg(f"Produto '{name}' cadastrado com sucesso!")
            self.query_one("#prod-name", Input).value = ""
            self.query_one("#prod-sku", Input).value = ""
            self.query_one("#prod-generic", Input).value = ""
            self.query_one("#prod-cost", Input).value = ""
            # Refresh product list
            self.__class__._products_cache = pg_query(
                "SELECT id, name, sku, category FROM products WHERE is_active = true ORDER BY name LIMIT 50"
            )
        else:
            self._set_msg(f"Erro: {result}", "red")

    # ---- Lote ----

    def _save_batch(self):
        if self._selected_product_id is None:
            self._set_msg("Selecione um produto na tabela!", "red")
            return
        if self._selected_warehouse_id is None:
            self._set_msg("Selecione um almoxarifado na tabela!", "red")
            return
        batch_num = self.query_one("#batch-num", Input).value.strip()
        qty = self.query_one("#batch-qty", Input).value.strip()
        expiry = self.query_one("#batch-expiry", Input).value.strip()
        if not batch_num or not qty or not expiry:
            self._set_msg("Preencha Lote, Quantidade e Validade!", "red")
            return
        mfg = self.query_one("#batch-mfg", Input).value.strip() or None
        cost = float(self.query_one("#batch-cost", Input).value or "0")
        payload = {
            "product_id": self._selected_product_id,
            "warehouse_id": self._selected_warehouse_id,
            "batch_number": batch_num,
            "quantity": int(qty),
            "expiry_date": expiry,
            "manufacture_date": mfg,
            "unit_cost": str(cost),
        }
        ok, result = api_post("/inventory/batches", payload)
        if ok:
            self._set_msg(f"Lote '{batch_num}' cadastrado com sucesso!")
            self.query_one("#batch-num", Input).value = ""
            self.query_one("#batch-qty", Input).value = ""
            self.query_one("#batch-expiry", Input).value = ""
            self.query_one("#batch-mfg", Input).value = ""
            self.query_one("#batch-cost", Input).value = ""
        else:
            self._set_msg(f"Erro: {result}", "red")

    # ---- Movimentacao ----

    def _save_movement(self):
        if not hasattr(self, "_batches_cache") or not self._batches_cache:
            self._set_msg("Nenhum lote disponivel!", "red")
            return
        try:
            t = self.query_one("#batch-select", DataTable)
            idx = t.cursor_row
            if idx < 0 or idx >= len(self._batches_cache):
                self._set_msg("Selecione um lote na tabela!", "red")
                return
            batch_id = str(self._batches_cache[idx]["id"])
        except Exception:
            self._set_msg("Selecione um lote na tabela!", "red")
            return
        qty_str = self.query_one("#mov-qty", Input).value.strip()
        if not qty_str:
            self._set_msg("Preencha a quantidade!", "red")
            return
        qty = int(qty_str)
        mtype = self._selected_movement_type
        if mtype in ("out", "loss") and qty > 0:
            qty = -qty
        elif mtype in ("in",) and qty < 0:
            qty = abs(qty)
        notes = self.query_one("#mov-notes", Input).value.strip() or None
        payload = {
            "batch_id": batch_id,
            "movement_type": mtype,
            "quantity_change": qty,
            "notes": notes,
        }
        ok, result = api_post("/inventory/movements", payload)
        if ok:
            self._set_msg(f"Movimentacao registrada: {mtype} {qty:+d}")
            self.query_one("#mov-qty", Input).value = ""
            self.query_one("#mov-notes", Input).value = ""
        else:
            self._set_msg(f"Erro: {result}", "red")

    # ---- Eventos ----

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        # Tabs
        if btn_id.startswith("tab-"):
            self._show_tab(btn_id.replace("tab-", ""))
            return

        # Category cycle
        if btn_id == "cat-btn":
            cur = self._selected_category
            idx = CATEGORIES.index(cur) if cur in CATEGORIES else 0
            next_cat = CATEGORIES[(idx + 1) % len(CATEGORIES)]
            self.__class__._selected_category = next_cat
            try:
                self.query_one("#cat-btn", Button).label = next_cat
            except Exception:
                pass
            return

        # Movement type cycle
        if btn_id == "mov-btn":
            cur = self._selected_movement_type
            idx = MOVEMENT_TYPES.index(cur) if cur in MOVEMENT_TYPES else 0
            next_mt = MOVEMENT_TYPES[(idx + 1) % len(MOVEMENT_TYPES)]
            self.__class__._selected_movement_type = next_mt
            try:
                self.query_one("#mov-btn", Button).label = next_mt
            except Exception:
                pass
            return

        # Save buttons
        if btn_id == "btn-save-product":
            self._save_product()
        elif btn_id == "btn-save-batch":
            self._save_batch()
        elif btn_id == "btn-save-mov":
            self._save_movement()

    @on(DataTable.RowHighlighted, "#prod-select")
    def on_prod_selected(self, event: DataTable.RowHighlighted) -> None:
        idx = event.cursor_row
        if idx is not None and idx >= 0 and idx < len(self._products_cache):
            p = self._products_cache[idx]
            self.__class__._selected_product_id = str(p["id"])
            try:
                self.query_one("#selected-prod-label", Label).update(
                    f"Produto selecionado: [bold green]{p.get('name', '-')}[/] ({p.get('sku', '-')})"
                )
            except Exception:
                pass

    @on(DataTable.RowHighlighted, "#wh-select")
    def on_wh_selected(self, event: DataTable.RowHighlighted) -> None:
        idx = event.cursor_row
        if idx is not None and idx >= 0 and idx < len(self._warehouses_cache):
            w = self._warehouses_cache[idx]
            self.__class__._selected_warehouse_id = str(w["id"])
            try:
                self.query_one("#selected-wh-label", Label).update(
                    f"Almoxarifado selecionado: [bold green]{w.get('name', '-')}[/]"
                )
            except Exception:
                pass

    @on(DataTable.RowHighlighted, "#batch-select")
    def on_batch_selected(self, event: DataTable.RowHighlighted) -> None:
        idx = event.cursor_row
        if hasattr(self, "_batches_cache") and idx is not None and idx >= 0 and idx < len(self._batches_cache):
            b = self._batches_cache[idx]
            try:
                self.query_one("#selected-batch-label", Label).update(
                    f"Lote selecionado: [bold green]{b.get('name', '-')}[/] Lote: {b.get('batch_number', '-')} Qtd: {b.get('quantity', 0):,}"
                )
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
    "9": CadastroView,
}


class ABHUApp(App):
    TITLE = "ABHU"
    SUB_TITLE = "Sistema de Gestao Farmaceutica Hospitalar"

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
    #detail-bar { padding: 0 2; }
    .form-panel { padding: 0 2; }
    .form-panel.hidden { display: none; }
    .form-title { text-style: bold; color: $accent; margin: 1 0; }
    .field-label { width: 14; min-width: 14; padding: 0 1; color: $text-muted; }
    .field-input { width: 1fr; min-width: 20; margin: 0 1; }
    .save-btn {
        margin: 1 2;
        min-height: 3;
        min-width: 25;
        background: $accent;
        color: $text;
        text-style: bold;
        border: solid $accent;
    }
    .save-btn:hover { background: $accent 80%; }
    .select-table { height: 10; margin: 0 2; }
    #tab-bar { padding: 0 2; }
    """

    BINDINGS = [
        Binding("1", "show_view('1')", "Dashboard", show=True),
        Binding("2", "show_view('2')", "Produtos", show=True),
        Binding("3", "show_view('3')", "Alertas", show=True),
        Binding("4", "show_view('4')", "Vencimento", show=True),
        Binding("5", "show_view('5')", "Estoque", show=True),
        Binding("6", "show_view('6')", "Consumo", show=True),
        Binding("7", "show_view('7')", "Movimentacoes", show=True),
        Binding("8", "show_view('8')", "Usuarios", show=True),
        Binding("9", "show_view('9')", "Cadastro", show=True),
        Binding("q", "quit", "Sair", show=True),
    ]

    def action_show_view(self, key: str):
        if key in VIEW_MAP:
            self._show_view(key)

    def action_quit(self):
        self.exit()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("[bold cyan]ABHU[/]")
                yield Label("[dim]v3.1[/]")
                yield Label("")
                yield Button("1 Dashboard", id="btn-1", classes="-active")
                yield Button("2 Produtos", id="btn-2")
                yield Button("3 Alertas", id="btn-3")
                yield Button("4 Vencimento", id="btn-4")
                yield Button("5 Estoque", id="btn-5")
                yield Button("6 Consumo", id="btn-6")
                yield Button("7 Movimentacoes", id="btn-7")
                yield Button("8 Usuarios", id="btn-8")
                yield Button("9 Cadastro", id="btn-9")
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
                yield CadastroView(id="v-9", classes="hidden")
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
        for k in "123456789":
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
