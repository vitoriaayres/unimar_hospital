'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Area, BarChart as RechartsBarChart, Bar } from 'recharts';
import { cn } from '@/lib/utils';

interface ForecastChartProps {
  data: Array<{
    date: string;
    actual?: number | null;
    predicted: number;
    lower?: number;
    upper?: number;
  }>;
  className?: string;
  height?: number;
  showActual?: boolean;
}

export function ForecastChart({ data, className, height = 300, showActual = true }: ForecastChartProps) {
  if (!data.length) {
    return (
      <div className={cn('flex items-center justify-center h-[300px]', className)}>
        <p className="text-muted-foreground">Nenhum dado disponível para exibição</p>
      </div>
    );
  }

  return (
    <div className={cn('w-full', className)}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="date"
            tickFormatter={(value) => new Date(value).toLocaleDateString('pt-BR', { month: 'short', day: '2-digit' })}
            tick={{ fontSize: 12 }}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value: number, name: string) => [
              value.toLocaleString('pt-BR'),
              name === 'actual' ? 'Consumo Real' : name === 'predicted' ? 'Previsão' : 'Intervalo',
            ]}
            labelFormatter={(value) => new Date(value).toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' })}
            contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }}
          />
          <Legend />
          {showActual && (
            <Line
              type="monotone"
              dataKey="actual"
              stroke="hsl(var(--muted-foreground))"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Consumo Real"
            />
          )}
          <Area
            type="monotone"
            dataKey="lower"
            stroke="hsl(var(--primary))"
            fill="hsl(var(--primary))"
            fillOpacity={0.1}
            strokeWidth={0}
            name="Intervalo de Confiança"
          />
          <Area
            type="monotone"
            dataKey="upper"
            stroke="hsl(var(--primary))"
            fill="hsl(var(--primary))"
            fillOpacity={0.1}
            strokeWidth={0}
          />
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={false}
            name="Previsão"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

interface BarChartProps {
  data: Array<{
    name: string;
    value: number;
    color?: string;
  }>;
  className?: string;
  height?: number;
  indexBy?: string;
}

export function BarChart({ data, className, height = 300, indexBy = 'name' }: BarChartProps) {
  if (!data.length) {
    return (
      <div className={cn('flex items-center justify-center h-[300px]', className)}>
        <p className="text-muted-foreground">Nenhum dado disponível</p>
      </div>
    );
  }

  return (
    <div className={cn('w-full', className)}>
      <ResponsiveContainer width="100%" height={height}>
        <RechartsBarChart data={data} layout="vertical" margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis type="number" tick={{ fontSize: 12 }} />
          <YAxis dataKey={indexBy} type="category" tick={{ fontSize: 12 }} width={120} />
          <Tooltip
            formatter={(value: number) => [value.toLocaleString('pt-BR'), 'unidades']}
            contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }}
          />
          <Legend />
          <Bar dataKey="value" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} maxBarSize={40} />
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}

