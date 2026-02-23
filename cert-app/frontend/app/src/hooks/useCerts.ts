/** Hooks for certification data fetching */

import { useState, useEffect, useCallback } from 'react';
import type {
  QualificationListResponse,
  QualificationDetail,
  QualificationStatsListResponse,
  FilterOptions,
  CertFilterParams,
} from '@/types';
import {
  getCertifications,
  getCertificationDetail,
  getCertificationStats,
  getFilterOptions,
} from '@/lib/api';

interface UseCertsReturn {
  data: QualificationListResponse | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useCerts(params: CertFilterParams = {}): UseCertsReturn {
  const [data, setData] = useState<QualificationListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCertifications(params);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
  }, [
    params.q,
    params.main_field,
    params.ncs_large,
    params.qual_type,
    params.managing_body,
    params.is_active,
    params.sort,
    params.sort_desc,
    params.page,
    params.page_size,
  ]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

interface UseCertDetailReturn {
  data: QualificationDetail | null;
  loading: boolean;
  error: Error | null;
}

export function useCertDetail(qualId: number | null, token?: string | null): UseCertDetailReturn {
  const [data, setData] = useState<QualificationDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!qualId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    getCertificationDetail(qualId, token)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err : new Error('Unknown error')))
      .finally(() => setLoading(false));
  }, [qualId, token]);

  return { data, loading, error };
}


interface UseCertStatsReturn {
  data: QualificationStatsListResponse | null;
  loading: boolean;
  error: Error | null;
}

export function useCertStats(
  qualId: number | null,
  year?: number
): UseCertStatsReturn {
  const [data, setData] = useState<QualificationStatsListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!qualId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    getCertificationStats(qualId, year)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err : new Error('Unknown error')))
      .finally(() => setLoading(false));
  }, [qualId, year]);

  return { data, loading, error };
}

interface UseFilterOptionsReturn {
  data: FilterOptions | null;
  loading: boolean;
  error: Error | null;
}

export function useFilterOptions(): UseFilterOptionsReturn {
  const [data, setData] = useState<FilterOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    getFilterOptions()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err : new Error('Unknown error')))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
