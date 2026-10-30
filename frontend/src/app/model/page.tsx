'use client';

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Brain, Database, Loader2, Target, TrendingDown, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useModelReport } from '@/hooks/usePredictions';
import { cn, formatDate, formatDateTime, formatNumber, getCategoryLabel } from '@/lib/utils';

const BRAND_BLUE = '#193D6F';
const BRAND_TEAL = '#12A89D';

const tooltipStyle = {
  backgroundColor: 'hsl(var(--card))',
  border: '1px solid hsl(var(--border))',
  borderRadius: '8px',
};

// Nomes das variáveis do modelo (ml/features.py) em linguagem de negócio
const FEATURE_LABELS: Record<string, string> = {
  daily_consumption: 'Consumo do dia',
  cumulative_consumption: 'Consumo acumulado',
  expanding_mean: 'Média histórica',
  weekday: 'Dia da semana',
  month: 'Mês',
  quarter: 'Trimestre',
  day_of_month: 'Dia do mês',
  is_weekend: 'Fim de semana',
  month_sin: 'Sazonalidade (seno)',
  month_cos: 'Sazonalidade (cosseno)',
};

function featureLabel(name: string): string {
  if (FEATURE_LABELS[name]) return FEATURE_LABELS[name];
  const lag = name.match(/^lag_(\d+)$/);
  if (lag) return `Consumo de ${lag[1]} dia(s) atrás`;
  const rolling = name.match(/^rolling_(mean|std|min|max)_(\d+)$/);
  if (rolling) {
    const stat = { mean: 'Média', std: 'Variação', min: 'Mínimo', max: 'Máximo' }[rolling[1]];
    return `${stat} dos últimos ${rolling[2]} dias`;
  }
  const ratio = name.match(/^ratio_(\d+)_(\d+)$/);
  if (ratio) return `Razão consumo ${ratio[1]}d / ${ratio[2]}d`;
  const diff = name.match(/^diff_(\d+)_(\d+)$/);
  if (diff) return `Diferença ${diff[1]}d − ${diff[2]}d`;
  return name;
}

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

export default function ModelPage() {
  const { data: report, isLoading, error } = useModelReport();

  if (isLoading) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-2" />
            <p className="text-muted-foreground">Carregando relatório do modelo...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="h-8 w-8 mx-auto text-destructive mb-2" />
            <p className="font-medium">Relatório do modelo indisponível</p>
            <p className="text-sm text-muted-foreground">
              Rode <code>uv run python ml/run_pipeline.py</code> no backend para treinar o modelo.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { metrics } = report;
  const gain = metrics.baseline_wape - metrics.wape;
  const accuracy = 1 - metrics.wape;

  const kpis = [
    { name: 'Acurácia (1 − WAPE)', value: pct(accuracy), hint: `WAPE ${pct(metrics.wape)}`, icon: Target, color: 'text-primary bg-primary/10' },
    { name: 'Erro do método atual', value: pct(metrics.baseline_wape), hint: 'Média móvel de 7 dias', icon: TrendingDown, color: 'text-amber-600 bg-amber-100' },
    { name: 'Redução do erro', value: `${(gain * 100).toFixed(1)} p.p.`, hint: `${pct(gain / metrics.baseline_wape)} menor que o método atual`, icon: Brain, color: 'text-green-600 bg-green-100' },
    { name: 'Registros de treino', value: formatNumber(metrics.n_train + metrics.n_valid), hint: `${metrics.n_features} variáveis`, icon: Database, color: 'text-indigo-600 bg-indigo-100' },
  ];

  const bands = [
    { name: 'Baixo giro', wape: metrics.wape_low * 100 },
    { name: 'Médio giro', wape: metrics.wape_mid * 100 },
    { name: 'Alto giro', wape: metrics.wape_high * 100 },
  ];

  const categories = report.by_category.map((c) => ({
    name: getCategoryLabel(c.category),
    modelo: +(c.wape * 100).toFixed(1),
    atual: +(c.baseline_wape * 100).toFixed(1),
  }));

  const importance = report.feature_importance.slice(0, 10).map((f) => ({
    name: featureLabel(f.feature),
    value: +(f.importance * 100).toFixed(1),
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Modelo de Previsão</h1>
          <p className="text-muted-foreground">
            LightGBM prevendo o consumo dos próximos 7 dias de cada medicamento
          </p>
        </div>
        <div className="text-right space-y-1">
          <Badge variant="success">Em produção</Badge>
          <p className="text-xs text-muted-foreground">
            Treinado em {formatDateTime(metrics.trained_at)}
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <Card key={kpi.name}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{kpi.name}</p>
                  <p className="text-3xl font-bold">{kpi.value}</p>
                  <p className="text-xs text-muted-foreground mt-1">{kpi.hint}</p>
                </div>
                <div className={cn('p-3 rounded-full', kpi.color)}>
                  <kpi.icon className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Consumo real × previsto (período de teste)</CardTitle>
          <p className="text-sm text-muted-foreground">
            Soma semanal de todos os medicamentos, de {formatDate(report.test_period.start)} a{' '}
            {formatDate(report.test_period.end)}. Dados que o modelo não viu no treino.
          </p>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={340}>
            <LineChart data={report.weekly} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="week"
                tickFormatter={(v) => new Date(v).toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' })}
                tick={{ fontSize: 12 }}
                interval="preserveStartEnd"
              />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                formatter={(v: number) => Math.round(v).toLocaleString('pt-BR')}
                labelFormatter={(v) => `Semana de ${new Date(v).toLocaleDateString('pt-BR')}`}
                contentStyle={tooltipStyle}
              />
              <Legend />
              <Line type="monotone" dataKey="actual" name="Consumo real" stroke={BRAND_BLUE} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="predicted" name="Previsão do modelo" stroke={BRAND_TEAL} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="baseline" name="Método atual (média 7 dias)" stroke="hsl(var(--muted-foreground))" strokeWidth={1.5} strokeDasharray="5 5" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Erro por categoria (WAPE)</CardTitle>
            <p className="text-sm text-muted-foreground">Quanto menor, melhor</p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.max(260, categories.length * 42)}>
              <BarChart data={categories} layout="vertical" margin={{ top: 0, right: 30, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis type="number" tick={{ fontSize: 12 }} unit="%" />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 12 }} width={130} />
                <Tooltip formatter={(v: number) => `${v}%`} contentStyle={tooltipStyle} />
                <Legend />
                <Bar dataKey="modelo" name="Modelo" fill={BRAND_TEAL} radius={[0, 4, 4, 0]} />
                <Bar dataKey="atual" name="Método atual" fill="hsl(var(--muted-foreground))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>O que o modelo mais usa para prever</CardTitle>
            <p className="text-sm text-muted-foreground">Importância das 10 principais variáveis</p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.max(260, importance.length * 34)}>
              <BarChart data={importance} layout="vertical" margin={{ top: 0, right: 30, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis type="number" tick={{ fontSize: 12 }} unit="%" />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={190} />
                <Tooltip formatter={(v: number) => `${v}%`} contentStyle={tooltipStyle} />
                <Bar dataKey="value" name="Importância" fill={BRAND_BLUE} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Erro por volume de consumo</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {bands.map((b) => (
              <div key={b.name}>
                <div className="flex justify-between text-sm mb-1">
                  <span>{b.name}</span>
                  <span className="font-medium">{b.wape.toFixed(1)}%</span>
                </div>
                <div className="h-2 rounded-full bg-muted">
                  <div className="h-2 rounded-full" style={{ width: `${Math.min(b.wape * 3, 100)}%`, backgroundColor: BRAND_TEAL }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Como o modelo foi avaliado</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <dt className="text-muted-foreground">Alvo</dt>
              <dd>Consumo dos próximos 7 dias</dd>
              <dt className="text-muted-foreground">Divisão</dt>
              <dd>Temporal (teste = período mais recente)</dd>
              <dt className="text-muted-foreground">Treino / validação / teste</dt>
              <dd>
                {formatNumber(metrics.n_train)} / {formatNumber(metrics.n_valid)} / {formatNumber(metrics.n_test)}
              </dd>
              <dt className="text-muted-foreground">Combinação</dt>
              <dd>
                {pct(metrics.blend_weight)} modelo + {pct(1 - metrics.blend_weight)} média móvel
              </dd>
              <dt className="text-muted-foreground">Iterações</dt>
              <dd>{metrics.best_iteration} (early stopping)</dd>
              <dt className="text-muted-foreground">MAE / RMSE</dt>
              <dd>
                {metrics.mae.toFixed(1)} / {metrics.rmse.toFixed(1)} unidades
              </dd>
            </dl>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
