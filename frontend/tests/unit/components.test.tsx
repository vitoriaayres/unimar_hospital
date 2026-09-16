import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

describe('UI Components', () => {
  describe('Button', () => {
    it('renders correctly', () => {
      render(<Button>Click me</Button>);
      expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
    });

    it('applies variant classes', () => {
      render(<Button variant="destructive">Delete</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-destructive');
    });

    it('applies size classes', () => {
      render(<Button size="lg">Large</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-11');
    });

    it('shows loading state', () => {
      render(<Button loading>Loading</Button>);
      expect(screen.getByRole('button')).toBeDisabled();
      expect(screen.getByText('Carregando...')).toBeInTheDocument();
    });

    it('handles click events', () => {
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Click me</Button>);
      fireEvent.click(screen.getByRole('button'));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Input', () => {
    it('renders with label', () => {
      render(<Input label="Email" placeholder="seu@email.com" />);
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    it('shows error message', () => {
      render(<Input label="Email" error="Email inválido" />);
      expect(screen.getByRole('alert')).toHaveTextContent('Email inválido');
    });

    it('shows helper text', () => {
      render(<Input label="Senha" helperText="Mínimo 8 caracteres" />);
      expect(screen.getByText('Mínimo 8 caracteres')).toBeInTheDocument();
    });
  });

  describe('Badge', () => {
    it('renders with default variant', () => {
      render(<Badge>Default</Badge>);
      expect(screen.getByText('Default')).toHaveClass('bg-primary');
    });

    it('applies variant classes', () => {
      render(<Badge variant="success">Sucesso</Badge>);
      expect(screen.getByText('Sucesso')).toHaveClass('bg-green-100');
    });

    it('applies destructive variant', () => {
      render(<Badge variant="destructive">Erro</Badge>);
      expect(screen.getByText('Erro')).toHaveClass('bg-destructive');
    });
  });
});

describe('Utility Functions', () => {
  describe('cn', () => {
    it('combines class names', () => {
      expect(cn('base', 'extra')).toBe('base extra');
    });

    it('handles conditional classes', () => {
      expect(cn('base', true && 'conditional')).toBe('base conditional');
      expect(cn('base', false && 'conditional')).toBe('base');
    });

    it('merges tailwind classes correctly', () => {
      expect(cn('p-2 p-4')).toBe('p-4');
      expect(cn('text-red-500 text-blue-500')).toBe('text-blue-500');
    });
  });

  describe('formatCurrency', () => {
    it('formats Brazilian currency', () => {
      expect(formatCurrency(1234.56)).toBe('R$ 1.234,56');
      expect(formatCurrency(0)).toBe('R$ 0,00');
      expect(formatCurrency(1000000)).toBe('R$ 1.000.000,00');
    });
  });

  describe('formatNumber', () => {
    it('formats numbers with Brazilian locale', () => {
      expect(formatNumber(1234)).toBe('1.234');
      expect(formatNumber(1000000)).toBe('1.000.000');
    });
  });

  describe('formatDate', () => {
    it('formats dates in Brazilian format', () => {
      expect(formatDate('2024-01-15')).toBe('15/01/2024');
      expect(formatDate(new Date('2024-12-25'))).toBe('25/12/2024');
    });
  });

  describe('getSeverityColor', () => {
    it('returns correct colors for each severity', () => {
      expect(getSeverityColor('critical')).toContain('text-destructive');
      expect(getSeverityColor('warning')).toContain('text-amber-600');
      expect(getSeverityColor('info')).toContain('text-primary');
    });
  });

  describe('getStatusColor', () => {
    it('returns correct colors for each status', () => {
      expect(getStatusColor('available')).toContain('text-green-600');
      expect(getStatusColor('expired')).toContain('text-destructive');
      expect(getStatusColor('reserved')).toContain('text-blue-600');
    });
  });
});