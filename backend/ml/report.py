"""Gera os graficos do modelo (PNG) para a documentacao e os slides.

Le ml/data/model_report_production.json (gravado por ml/train.py) e salva em docs/imagens/.
Os mesmos dados aparecem na tela "Modelo" do sistema.
"""

from __future__ import annotations

import io
import json
import sys
from datetime import date
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

REPORT_PATH = Path('ml/data/model_report_production.json')
OUT_DIR = Path(__file__).resolve().parents[2] / 'docs' / 'imagens'

BRAND_BLUE = '#193D6F'
BRAND_TEAL = '#12A89D'
GRAY = '#94A3B8'

CATEGORY_LABELS = {
    'antibiotic': 'Antibióticos',
    'analgesic': 'Analgésicos',
    'antithrombotic': 'Antitrombóticos',
    'beta_blocker': 'Betabloqueadores',
    'ppi': 'Inibidores de bomba',
    'bronchodilator': 'Broncodilatadores',
    'psycholeptic': 'Psicolépticos',
    'ace_inhibitor': 'Inibidores da ECA',
    'corticosteroid': 'Corticosteroides',
    'other': 'Outros',
}

plt.rcParams.update(
    {
        'font.size': 11,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.titleweight': 'bold',
        'axes.titlesize': 13,
        'figure.dpi': 150,
    }
)


def feature_label(name: str) -> str:
    """Mesmos rotulos da tela Modelo (frontend/src/app/model/page.tsx)."""
    fixed = {
        'daily_consumption': 'Consumo do dia',
        'cumulative_consumption': 'Consumo acumulado',
        'expanding_mean': 'Média histórica',
        'weekday': 'Dia da semana',
        'month': 'Mês',
        'day_of_month': 'Dia do mês',
        'is_weekend': 'Fim de semana',
    }
    if name in fixed:
        return fixed[name]
    parts = name.split('_')
    if parts[0] == 'lag' and len(parts) == 2:
        return f'Consumo de {parts[1]} dia(s) atrás'
    if parts[0] == 'rolling' and len(parts) == 3:
        stat = {'mean': 'Média', 'std': 'Variação', 'min': 'Mínimo', 'max': 'Máximo'}[parts[1]]
        return f'{stat} dos últimos {parts[2]} dias'
    return name


def plot_weekly(report: dict) -> Path:
    weeks = [date.fromisoformat(p['week']) for p in report['weekly']]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(weeks, [p['actual'] for p in report['weekly']], color=BRAND_BLUE, lw=2, label='Consumo real')
    ax.plot(weeks, [p['predicted'] for p in report['weekly']], color=BRAND_TEAL, lw=2, label='Previsão do modelo')
    ax.plot(
        weeks,
        [p['baseline'] for p in report['weekly']],
        color=GRAY,
        lw=1.5,
        ls='--',
        label='Método atual (média 7 dias)',
    )
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v / 1000:.0f}k'))
    ax.set_title('Consumo real × previsto no período de teste (soma semanal)')
    ax.grid(alpha=0.3)
    ax.legend(frameon=False)
    return save(fig, 'modelo-real-vs-previsto.png')


def plot_comparison(metrics: dict) -> Path:
    fig, ax = plt.subplots(figsize=(6, 4))
    values = [metrics['baseline_wape'] * 100, metrics['wape'] * 100]
    bars = ax.bar(['Método atual\n(média 7 dias)', 'Modelo\nLightGBM'], values, color=[GRAY, BRAND_TEAL], width=0.55)
    ax.bar_label(bars, fmt='%.1f%%', padding=4, fontweight='bold')
    ax.set_ylabel('Erro (WAPE, %)')
    ax.set_title('Erro da previsão: quanto menor, melhor')
    ax.set_ylim(0, max(values) * 1.25)
    return save(fig, 'modelo-vs-metodo-atual.png')


def plot_categories(report: dict) -> Path:
    rows = sorted(report['by_category'], key=lambda c: c['wape'], reverse=True)
    labels = [CATEGORY_LABELS.get(c['category'], c['category']) for c in rows]
    y = range(len(rows))
    fig, ax = plt.subplots(figsize=(8, 0.5 * len(rows) + 1.5))
    ax.barh([i + 0.2 for i in y], [c['baseline_wape'] * 100 for c in rows], 0.4, color=GRAY, label='Método atual')
    ax.barh([i - 0.2 for i in y], [c['wape'] * 100 for c in rows], 0.4, color=BRAND_TEAL, label='Modelo')
    ax.set_yticks(list(y), labels)
    ax.set_xlabel('Erro (WAPE, %)')
    ax.set_title('Erro por categoria de medicamento')
    ax.legend(frameon=False, loc='lower right')
    return save(fig, 'modelo-erro-por-categoria.png')


def plot_importance(report: dict) -> Path:
    rows = report['feature_importance'][:10][::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh([feature_label(f['feature']) for f in rows], [f['importance'] * 100 for f in rows], color=BRAND_BLUE)
    ax.set_xlabel('Importância (%)')
    ax.set_title('O que o modelo mais usa para prever')
    return save(fig, 'modelo-importancia-variaveis.png')


def save(fig, name: str) -> Path:
    path = OUT_DIR / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'  {path}')
    return path


def main() -> None:
    if not REPORT_PATH.exists():
        sys.exit(f'{REPORT_PATH} não encontrado. Rode antes: uv run python ml/run_pipeline.py')

    with open(REPORT_PATH, encoding='utf-8') as f:
        report = json.load(f)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print('Gerando gráficos do modelo:')
    plot_weekly(report)
    plot_comparison(report['metrics'])
    plot_categories(report)
    plot_importance(report)


if __name__ == '__main__':
    main()
