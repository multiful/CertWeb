/** Hooks for recommendation data fetching (React Query) */

import { useQuery } from '@tanstack/react-query';
import type { RecommendationListResponse } from '@/types';
import { getRecommendations, getAvailableMajors, getPopularMajors } from '@/lib/api';
import { recommendationKeys } from '@/lib/queryKeys';

interface UseRecommendationsReturn {
  data: RecommendationListResponse | null;
  loading: boolean;
  error: Error | null;
}

export function useRecommendations(
  major: string,
  limit: number = 10
): UseRecommendationsReturn {
  const {
    data,
    isLoading: loading,
    error,
  } = useQuery({
    queryKey: recommendationKeys.byMajor(major, limit),
    queryFn: () => getRecommendations(major, limit),
    enabled: major.trim().length > 0,
  });

  return {
    data: data ?? null,
    loading,
    error: error instanceof Error ? error : error ? new Error(String(error)) : null,
  };
}

interface UseMajorsReturn {
  majors: string[];
  loading: boolean;
  error: Error | null;
}

export function useMajors(): UseMajorsReturn {
  const {
    data,
    isLoading: loading,
    error,
  } = useQuery({
    queryKey: recommendationKeys.majors(),
    queryFn: async () => {
      const res = await getAvailableMajors();
      return res.majors ?? [];
    },
  });

  return {
    majors: data ?? [],
    loading,
    error: error instanceof Error ? error : error ? new Error(String(error)) : null,
  };
}

export function usePopularMajors(limit: number = 12): UseMajorsReturn {
  const {
    data,
    isLoading: loading,
    error,
  } = useQuery({
    queryKey: recommendationKeys.popularMajors(limit),
    queryFn: async () => {
      const res = await getPopularMajors(limit);
      return res.majors ?? [];
    },
  });

  return {
    majors: data ?? [],
    loading,
    error: error instanceof Error ? error : error ? new Error(String(error)) : null,
  };
}
