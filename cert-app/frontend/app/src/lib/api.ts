
/** API client for backend communication with Mock fallback */

import type {
  QualificationListResponse,
  QualificationDetail,
  QualificationStatsListResponse,
  RecommendationListResponse,
  FilterOptions,
  HealthCheck,
  CertFilterParams,
  UserFavorite,
  Job,
  SemanticSearchResponse,
  HybridRecommendationResponse,
  TrendingQualificationListResponse,
} from '@/types';
import { mockApi } from './mockApi';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://certweb-xzpx.onrender.com/api/v1';

async function apiRequest<T>(path: string, options?: RequestInit, retries = 2): Promise<T> {
  try {
    const response = await fetch(`${BASE_URL}${path}`, options);
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    return await response.json();
  } catch (error: any) {
    if (error.name === 'TypeError' && retries > 0) {
      console.warn(`[Network Retry] Failed to fetch ${path}. Retrying... (${retries} attempts left)`);
      await new Promise(resolve => setTimeout(resolve, 1000));
      return apiRequest<T>(path, options, retries - 1);
    }

    if (error.message && error.message.includes('401')) {
      console.warn(`API Request 401 for ${path}`);
    } else {
      console.error(`API Request failed for ${path}:`, error);
    }
    throw error;
  }
}

// ============== Certification APIs ==============

export async function getCertifications(
  params: CertFilterParams = {}
): Promise<QualificationListResponse> {
  try {
    const query = new URLSearchParams();
    if (params.q) query.append('q', params.q);
    if (params.main_field) query.append('main_field', params.main_field);
    if (params.ncs_large) query.append('ncs_large', params.ncs_large);
    if (params.qual_type) query.append('qual_type', params.qual_type);
    if (params.managing_body) query.append('managing_body', params.managing_body);
    if (params.is_active !== undefined) query.append('is_active', String(params.is_active));
    if (params.sort) query.append('sort', params.sort);
    if (params.sort_desc !== undefined) query.append('sort_desc', String(params.sort_desc));
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());

    return await apiRequest<QualificationListResponse>(`/certs?${query.toString()}`);
  } catch {
    // When using mock, we need to adapt CertFilterParams if property names differ,
    // but here we just pass it as is because we fixed the call site
    // However, mockApi.getCertifications might expect camelCase if defined so.
    // Let's check mockApi definition in Step 538.
    // It expects { q?: string; main_field?: string; ... } which is snake_case.
    // So this is fine.
    return mockApi.getCertifications(params);
  }
}

export async function getCertificationDetail(
  qualId: number,
  token?: string | null
): Promise<QualificationDetail | null> {
  try {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return await apiRequest<QualificationDetail>(`/certs/${qualId}`, { headers });
  } catch {
    return mockApi.getCertificationDetail(qualId);
  }
}

export async function getCertificationStats(
  qualId: number,
  year?: number
): Promise<QualificationStatsListResponse> {
  try {
    const query = year ? `?year=${year}` : '';
    return await apiRequest<QualificationStatsListResponse>(`/certs/${qualId}/stats${query}`);
  } catch {
    return mockApi.getCertificationStats(qualId);
  }
}

export async function getFilterOptions(): Promise<FilterOptions> {
  try {
    return await apiRequest<FilterOptions>('/certs/filter-options');
  } catch {
    return mockApi.getFilterOptions();
  }
}

// ============== Recommendation APIs ==============

export async function getRecommendations(
  major: string,
  limit: number = 10
): Promise<RecommendationListResponse> {
  try {
    return await apiRequest<RecommendationListResponse>(`/recommendations?major=${encodeURIComponent(major)}&limit=${limit}`);
  } catch {
    return mockApi.getRecommendations(major);
  }
}

export async function getTrendingCerts(
  limit: number = 10
): Promise<TrendingQualificationListResponse> {
  try {
    return await apiRequest<TrendingQualificationListResponse>(`/certs/trending/now?limit=${limit}`);
  } catch {
    return { items: [], total: 0 };
  }
}

export async function getHybridRecommendations(
  major: string,
  interest?: string,
  limit: number = 10
): Promise<HybridRecommendationResponse> {
  const query = new URLSearchParams();
  query.append('major', major);
  if (interest) query.append('interest', interest);
  query.append('limit', limit.toString());

  return await apiRequest<HybridRecommendationResponse>(`/recommendations/ai/hybrid-recommendation?${query.toString()}`);
}

export async function semanticSearch(
  query: string,
  limit: number = 10
): Promise<SemanticSearchResponse> {
  return await apiRequest<SemanticSearchResponse>(`/recommendations/ai/semantic-search?query=${encodeURIComponent(query)}&limit=${limit}`);
}

export async function getAvailableMajors(): Promise<{ majors: string[] }> {
  try {
    return await apiRequest<{ majors: string[] }>('/recommendations/majors');
  } catch {
    const majors = await mockApi.getAvailableMajors();
    return { majors };
  }
}

// ============== Job APIs ==============

export async function getJobs(
  params: { q?: string; page?: number; page_size?: number } = {}
): Promise<Job[]> {
  try {
    const query = new URLSearchParams();
    if (params.q) query.append('q', params.q);
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());

    return await apiRequest<Job[]>(`/jobs?${query.toString()}`);
  } catch {
    return []; // No mock for jobs yet
  }
}

export async function getJobDetail(jobId: number): Promise<Job | null> {
  try {
    return await apiRequest<Job>(`/jobs/${jobId}`);
  } catch {
    return null;
  }
}

// ============== Health Check ==============

export async function getHealth(): Promise<HealthCheck> {
  try {
    return await apiRequest<HealthCheck>('/health');
  } catch {
    return mockApi.getHealth();
  }
}

// ============== Favorites APIs (requires auth) ==============

export async function getFavorites(
  token: string,
  page: number = 1,
  pageSize: number = 20
): Promise<{ items: UserFavorite[]; total: number }> {
  try {
    return await apiRequest<{ items: UserFavorite[]; total: number }>(
      `/me/favorites?page=${page}&page_size=${pageSize}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
  } catch {
    return { items: [], total: 0 };
  }
}

export async function addFavorite(
  qualId: number,
  token: string
): Promise<UserFavorite> {
  return await apiRequest<UserFavorite>(
    `/me/favorites/${qualId}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
}

export async function removeFavorite(
  qualId: number,
  token: string
): Promise<void> {
  await apiRequest<void>(
    `/me/favorites/${qualId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
}

export async function checkFavorite(
  qualId: number,
  token: string
): Promise<{ qual_id: number; is_favorite: boolean }> {
  try {
    return await apiRequest<{ qual_id: number; is_favorite: boolean }>(
      `/me/favorites/${qualId}/check`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
  } catch {
    return { qual_id: qualId, is_favorite: false };
  }
}

export async function getRecentViewed(token: string): Promise<any[]> {
  try {
    return await apiRequest<any[]>('/certs/recent/viewed', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
  } catch {
    return [];
  }
}
export async function updateProfile(
  token: string,
  updates: { name?: string; userid?: string; nickname?: string; detail_major?: string }
): Promise<any> {
  return await apiRequest<any>('/auth/profile', {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(updates)
  });
}

export async function checkUserId(userid: string): Promise<{ available: boolean, message: string }> {
  return await apiRequest<{ available: boolean, message: string }>('/auth/check-userid', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userid })
  });
}
