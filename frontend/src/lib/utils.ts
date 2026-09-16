import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('pt-BR').format(value);
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(date));
}

export function formatDateTime(date: string | Date): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function calculatePercentageChange(current: number, previous: number): number {
  if (previous === 0) return current > 0 ? 100 : 0;
  return ((current - previous) / previous) * 100;
}

export function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'text-destructive bg-destructive/10 border-destructive/20';
    case 'warning':
      return 'text-amber-600 bg-amber-50 border-amber-200';
    case 'info':
      return 'text-primary bg-primary/10 border-primary/20';
    default:
      return 'text-muted-foreground bg-muted border-border';
  }
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'available':
      return 'text-green-600 bg-green-50 border-green-200';
    case 'reserved':
      return 'text-blue-600 bg-blue-50 border-blue-200';
    case 'expired':
      return 'text-destructive bg-destructive/10 border-destructive/20';
    case 'recalled':
      return 'text-amber-600 bg-amber-50 border-amber-200';
    case 'quarantine':
      return 'text-purple-600 bg-purple-50 border-purple-200';
    default:
      return 'text-muted-foreground bg-muted border-border';
  }
}

export const PRODUCT_CATEGORIES = [
  'antibiotic',
  'analgesic',
  'antithrombotic',
  'beta_blocker',
  'ppi',
  'bronchodilator',
  'psycholeptic',
  'ace_inhibitor',
  'corticosteroid',
  'other',
] as const;

export const CATEGORY_LABELS: Record<string, string> = {
  antibiotic: 'Antibiótico',
  analgesic: 'Analgésico',
  antithrombotic: 'Antitrombótico',
  beta_blocker: 'Betabloqueador',
  ppi: 'IBP',
  bronchodilator: 'Broncodilatador',
  psycholeptic: 'Psicoléptico',
  ace_inhibitor: 'IECA',
  corticosteroid: 'Corticoide',
  other: 'Outros',
};

export function getCategoryLabel(category: string): string {
  return CATEGORY_LABELS[category] || category;
}