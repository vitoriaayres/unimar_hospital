'use client';

import { useCallback } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

/**
 * Filtros e paginação guardados na URL (a tela lê sempre daqui, então
 * voltar/avançar no navegador e links como /alerts?acknowledged=false funcionam).
 */
export function useUrlParams() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const get = useCallback((key: string) => searchParams.get(key) ?? '', [searchParams]);

  const set = useCallback(
    (updates: Record<string, string | number | null | undefined>, { resetPage = true } = {}) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value === null || value === undefined || value === '') params.delete(key);
        else params.set(key, String(value));
      }
      if (resetPage && !('page' in updates)) params.delete('page');
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [router, pathname, searchParams]
  );

  const page = Math.max(1, Number(searchParams.get('page')) || 1);

  return { get, set, page };
}
