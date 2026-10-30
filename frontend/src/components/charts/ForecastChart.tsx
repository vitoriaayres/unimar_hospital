'use client';

import {
  Area,
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { cn, formatNumber } from '@/lib/utils';

export const BRAND_BLUE = '#193D6F';
export const BRAND_TEAL = '#12A89D';

const tooltipStyle = {
  backgroundColor: 'hsl(var(--card))',
  border: '1px solid hsl(var(--border))',
  borderRadius: '8px',
};

function shortDate(value: string) {
  return new Date(value + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

interface ForecastChartProps {
  /** Pontos com consumo real (histórico) e/ou previsão com faixa esperada */
  data: Array<{
    date: string;
    actual?: number | null;
    predicted?: number | null;
    lower?: number | null;
    upper?: number | null;
  }>;
  className?: string;
  height?: number;
}

export function ForecastChart({ data, className, height = 300 }: ForecastChartProps) {
  if (!data.length) {
    return (
      <div className={cn('flex items-center justify-center', className)} style={{ height }}>
        <p className="text-muted-foreground">Nenhum dado disponível para exibição</p>
      </div>
    );
  }

  // Area com par [mínimo, máximo] desenha só a faixa entre os dois
  const rows = data.map((d) => ({
    ...d,
    range: d.lower != null && d.upper != null ? [d.lower, d.upper] : null,
  }));
  const hasActual = data.some((d) => d.actual != null);
  const hasPredicted = data.some((d) => d.predicted != null);

  return (
    <div className={cn('w-full', className)}>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={rows} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fontSize: 12 }} interval="preserveStartEnd" minTickGap={24} />
          <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => formatNumber(v)} width={56} />
          <Tooltip
            formatter={(value: number | number[], name: string) =>
              Array.isArray(value)
                ? [`${formatNumber(Math.round(value[0]))} – ${formatNumber(Math.round(value[1]))}`, name]
                : [formatNumber(Math.round(value)), name]
            }
            labelFormatter={(v) =>
              new Date(v + 'T00:00:00').toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' })
            }
            contentStyle={tooltipStyle}
          />
          <Legend />
          {hasPredicted && (
            <Area type="monotone" dataKey="range" name="Faixa esperada" stroke="none" fill={BRAND_TEAL} fillOpacity={0.15} />
          )}
          {hasActual && (
            <Line type="monotone" dataKey="actual" name="Consumo real" stroke={BRAND_BLUE} strokeWidth={2} dot={false} connectNulls={false} />
          )}
          {hasPredicted && (
            <Line type="monotone" dataKey="predicted" name="Previsão" stroke={BRAND_TEAL} strokeWidth={2} strokeDasharray="5 4" dot={false} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

interface BarChartProps {
  data: Array<{ name: string; value: number }>;
  className?: string;
  height?: number;
  unit?: string;
}

export function BarChart({ data, className, height = 300, unit = 'unidades' }: BarChartProps) {
  if (!data.length) {
    return (
      <div className={cn('flex items-center justify-center', className)} style={{ height }}>
        <p className="text-muted-foreground">Nenhum dado disponível</p>
      </div>
    );
  }

  return (
    <div className={cn('w-full', className)}>
      <ResponsiveContainer width="100%" height={height}>
        <RechartsBarChart data={data} layout="vertical" margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 12 }} tickFormatter={(v) => formatNumber(v)} />
          <YAxis dataKey="name" type="category" tick={{ fontSize: 12 }} width={110} />
          <Tooltip formatter={(value: number) => [formatNumber(value), unit]} contentStyle={tooltipStyle} />
          <Bar dataKey="value" fill={BRAND_BLUE} radius={[0, 4, 4, 0]} maxBarSize={36} />
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}
