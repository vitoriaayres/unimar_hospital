import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { formatNumber } from '@/lib/utils';

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  /** Nome do item no plural, ex.: "lotes" */
  label: string;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pages, total, label, onPageChange }: PaginationProps) {
  if (pages <= 1) {
    return <p className="mt-4 text-sm text-muted-foreground">{formatNumber(total)} {label}</p>;
  }

  return (
    <div className="mt-4 flex items-center justify-between gap-4">
      <p className="text-sm text-muted-foreground">
        Página {page} de {pages} · {formatNumber(total)} {label}
      </p>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => onPageChange(page - 1)} disabled={page <= 1} aria-label="Página anterior">
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="sm" onClick={() => onPageChange(page + 1)} disabled={page >= pages} aria-label="Próxima página">
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
