import type { LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/Card';
import { cn } from '@/lib/utils';

interface StatCardProps {
  name: string;
  value: string | number;
  icon: LucideIcon;
  /** Classes do círculo do ícone, ex.: 'text-primary bg-primary/10' */
  color?: string;
  /** Classes extras do valor, ex.: 'text-destructive' */
  valueClassName?: string;
  hint?: string;
  loading?: boolean;
}

export function StatCard({
  name,
  value,
  icon: Icon,
  color = 'text-primary bg-primary/10',
  valueClassName,
  hint,
  loading,
}: StatCardProps) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-medium text-muted-foreground truncate">{name}</p>
            {loading ? (
              <div className="mt-1 h-8 w-20 animate-pulse rounded bg-muted" />
            ) : (
              <p className={cn('text-2xl font-bold tabular-nums', valueClassName)}>{value}</p>
            )}
            {hint && <p className="text-xs text-muted-foreground truncate">{hint}</p>}
          </div>
          <div className={cn('shrink-0 rounded-full p-3', color)}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
