/** Hooks for recommendation data fetching */

import { useState, useEffect } from 'react';
import type { RecommendationListResponse } from '@/types';
import { getRecommendations, getAvailableMajors, getPopularMajors } from '@/lib/api';

interface UseRecommendationsReturn {
  data: RecommendationListResponse | null;
  loading: boolean;
  error: Error | null;
}

export function useRecommendations(
  major: string,
  limit: number = 10
): UseRecommendationsReturn {
  const [data, setData] = useState<RecommendationListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!major.trim()) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    getRecommendations(major, limit)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err : new Error('Unknown error')))
      .finally(() => setLoading(false));
  }, [major, limit]);

  return { data, loading, error };
}

interface UseMajorsReturn {
  majors: string[];
  loading: boolean;
  error: Error | null;
}

export function useMajors(): UseMajorsReturn {
  const [majors, setMajors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    getAvailableMajors()
      .then((data) => setMajors(data.majors))
      .catch((err) => setError(err instanceof Error ? err : new Error('Unknown error')))
      .finally(() => setLoading(false));
  }, []);

  return { majors, loading, error };
}

export function usePopularMajors(limit: number = 12): UseMajorsReturn {
  const [majors, setMajors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    getPopularMajors(limit)
      .then((data) => {
        setMajors(data.majors || []);
        setError(null);
      })
      .catch((err) => {
        setMajors([]);
        setError(err instanceof Error ? err : new Error('Unknown error'));
      })
      .finally(() => setLoading(false));
  }, [limit]);

  return { majors, loading, error };
}
