import { useState, useEffect, useMemo } from 'react';
import {
  Search,
  Filter,
  Award,
  TrendingUp,
  Zap,
  ArrowUpDown,
  ChevronDown,
  LayoutGrid,
  List as ListIcon,
  SearchX,
  RefreshCw,
  Bookmark
} from 'lucide-react';
import { getFavorites, addFavorite, removeFavorite, getTrendingCerts, getCertificationDetail } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select';
import { useCerts, useFilterOptions } from '@/hooks/useCerts';
import { useRouter } from '@/lib/router';
import { Skeleton } from '@/components/ui/skeleton';
import type { CertFilterParams, SortOption } from '@/types';

const ALL_FIELDS = "ALL_FIELDS";
const ALL_NCS = "ALL_NCS";
const ALL_TYPES = "ALL_TYPES";
const ALL_BODIES = "ALL_BODIES";

export function CertListPage() {
  const router = useRouter();
  const searchParams = new URL(window.location.href).searchParams;

  const [params, setParams] = useState<CertFilterParams>({
    q: searchParams.get('q') || '',
    main_field: searchParams.get('main_field') || undefined,
    ncs_large: searchParams.get('ncs_large') || undefined,
    qual_type: searchParams.get('qual_type') || undefined,
    managing_body: searchParams.get('managing_body') || undefined,
    sort: (searchParams.get('sort') as SortOption) || 'name',
    sort_desc: searchParams.get('sort_desc') !== 'false',
    page: 1,
    page_size: searchParams.get('filter') === 'bookmarks' ? 100 : 20
  });
  const [isFavoritesOnly, setIsFavoritesOnly] = useState(searchParams.get('filter') === 'bookmarks');
  const { user, token } = useAuth();
  const [favoriteIds, setFavoriteIds] = useState<number[]>([]);

  const { data, loading, error, refetch } = useCerts(params);
  const { data: filters } = useFilterOptions();
  const [trendingCerts, setTrendingCerts] = useState<any[]>([]);

  // Load trending certs
  useEffect(() => {
    async function loadTrending() {
      try {
        const res = await getTrendingCerts(5);
        setTrendingCerts(res.items);
      } catch (err) {
        console.error('Failed to load trending certs:', err);
      }
    }
    loadTrending();
  }, []);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [inputValue, setInputValue] = useState(params.q || '');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [favoritesItems, setFavoritesItems] = useState<any[]>([]);
  const [favoritesLoading, setFavoritesLoading] = useState(true);

  // Load favorites
  useEffect(() => {
    async function loadFavorites() {
      if (user && token) {
        setFavoritesLoading(true);
        try {
          const res = await getFavorites(token, 1, 1000);
          setFavoriteIds(res.items.map((f: any) => f.qual_id));

          // Build initial certs from qualification field
          let certs: any[] = res.items
            .filter((f: any) => f.qualification)
            .map((f: any) => ({ ...f.qualification }));

          // For items where stats are still null (backend cache issue),
          // fall back to fetching individual cert detail which is always reliable
          const missingStats = certs.filter(
            c => c.latest_pass_rate === null || c.latest_pass_rate === undefined
          );

          if (missingStats.length > 0) {
            const detailResults = await Promise.allSettled(
              missingStats.map(c => getCertificationDetail(c.qual_id, token))
            );
            const detailMap = new Map<number, any>();
            detailResults.forEach((result, idx) => {
              if (result.status === 'fulfilled' && result.value) {
                detailMap.set(missingStats[idx].qual_id, result.value);
              }
            });
            // Merge detail stats into certs
            certs = certs.map(c => {
              const detail = detailMap.get(c.qual_id);
              if (detail) {
                return {
                  ...c,
                  latest_pass_rate: detail.latest_pass_rate,
                  avg_difficulty: detail.avg_difficulty,
                  total_candidates: detail.total_candidates,
                };
              }
              return c;
            });
          }

          setFavoritesItems(certs);
        } catch (err: any) {
          if (err.message && err.message.includes('401')) {
            setFavoriteIds([]);
            setFavoritesItems([]);
          } else {
            console.error('Failed to load favorites:', err);
          }
        } finally {
          setFavoritesLoading(false);
        }
      } else if (!user) {
        const saved = localStorage.getItem('bookmarks');
        if (saved) {
          try {
            setFavoriteIds(JSON.parse(saved));
          } catch {
            setFavoriteIds([]);
          }
        }
        setFavoritesLoading(false);
      } else {
        setFavoritesLoading(false);
      }
    }
    loadFavorites();
  }, [user, token]);

  const toggleFavorite = async (e: React.MouseEvent, cert: any) => {
    e.stopPropagation(); // Card 클릭 방지
    const certId = cert.qual_id;
    const isAdding = !favoriteIds.includes(certId);

    // Optimistic UI update
    if (isAdding) {
      setFavoriteIds([...favoriteIds, certId]);
    } else {
      setFavoriteIds(favoriteIds.filter(id => id !== certId));
    }

    if (user && token) {
      try {
        if (isAdding) {
          await addFavorite(certId, token);
        } else {
          await removeFavorite(certId, token);
        }

        toast.success(isAdding ? "관심 자격증에 추가됨" : "관심 자격증에서 제거됨", {
          description: cert.qual_name
        });
      } catch (err: any) {
        console.error('Favorite sync failed:', err);
        // Rollback optimistic update
        if (isAdding) {
          setFavoriteIds(favoriteIds.filter(id => id !== certId));
        } else {
          setFavoriteIds([...favoriteIds, certId]);
        }
        toast.error(isAdding ? "관심 자격증 추가 실패" : "관심 자격증 제거 실패", {
          description: err.message || "다시 시도해주세요."
        });
      }
    } else {
      // Guest mode
      const saved = localStorage.getItem('bookmarks');
      let bookmarks = saved ? JSON.parse(saved) : [];
      if (isAdding) {
        if (!bookmarks.includes(certId)) bookmarks.push(certId);
      } else {
        bookmarks = bookmarks.filter((id: number) => id !== certId);
      }
      localStorage.setItem('bookmarks', JSON.stringify(bookmarks));

      toast.success(isAdding ? "관심 자격증에 추가됨 (비회원)" : "관심 자격증에서 제거됨 (비회원)", {
        description: cert.qual_name
      });
    }
  };

  // Filter items locally if Favorites Only is active
  const filteredItems = useMemo(() => {
    if (isFavoritesOnly) {
      // If we are logged in, use the full fetched favorites list
      if (user && favoritesItems.length > 0) {
        return favoritesItems;
      }
      // If guest or favoritesData is empty, fallback to current page filtered (limited)
      if (!data) return [];
      return data.items.filter(item => favoriteIds.includes(item.qual_id));
    }
    if (!data) return [];
    return data.items;
  }, [data, isFavoritesOnly, favoriteIds, favoritesItems, user]);

  // Debounce search input - Removed to ensure explicit search action
  /*
  useEffect(() => {
    const timer = setTimeout(() => {
      if (inputValue !== params.q) {
        updateParam('q', inputValue);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [inputValue]);
  */

  const updateParam = (key: keyof CertFilterParams, value: any) => {
    // Handle "All" options
    let finalValue = value;
    if (value === ALL_FIELDS || value === ALL_NCS || value === ALL_TYPES || value === ALL_BODIES) {
      finalValue = undefined;
    }

    setParams(prev => ({
      ...prev,
      [key]: finalValue,
      page: key === 'page' ? finalValue : 1
    }));
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    updateParam('q', inputValue);
    setShowSuggestions(false);
  };

  const handleSuggestionClick = (name: string) => {
    setInputValue(name);
    updateParam('q', name);
    setShowSuggestions(false);
  };

  return (
    <div className="space-y-10 pb-20">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-4">
          <Badge className="bg-blue-600/10 text-blue-400 border-blue-500/20 px-3 py-1">Certification Directory</Badge>
          <h1 className="text-4xl font-bold text-white tracking-tight">자격증 탐색</h1>
          <p className="text-slate-400 max-w-lg">
            대한민국 600여 종류의 국가 기술 및 전문 자격증 데이터를 검색하고<br />
            실시간 합격률과 난이도를 비교 분석하세요.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 p-1 rounded-xl border border-slate-800">
          <Button
            variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('grid')}
            className="h-9 w-9 p-0"
          >
            <LayoutGrid className="w-4 h-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('list')}
            className="h-9 w-9 p-0"
          >
            <ListIcon className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Filter Section */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-3xl p-8 space-y-8 backdrop-blur-sm">
        <form onSubmit={handleSearch} className="grid lg:grid-cols-12 gap-6 items-end">
          <div className="lg:col-span-4 space-y-3 relative">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
              <Search className="w-3 h-3" /> 자격증 명칭
            </label>
            <div className="relative z-20">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input
                placeholder="검색어를 입력하세요..."
                value={inputValue}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                onChange={(e) => {
                  setInputValue(e.target.value);
                  setShowSuggestions(true);
                }}
                className="pl-10 h-11 bg-black/20 border-slate-800 text-white rounded-xl focus:ring-blue-500"
              />
            </div>

            {/* Suggestions Dropdown */}
            {showSuggestions && inputValue.length >= 1 && data && data.items.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-50 max-h-60 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700 animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="p-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-950/20 border-b border-slate-800">
                  추천 검색어 ({data.items.length})
                </div>
                {data.items.slice(0, 10).map((cert) => (
                  <div
                    key={cert.qual_id}
                    className="px-4 py-2.5 hover:bg-slate-800 cursor-pointer text-slate-200 border-b border-slate-800/50 last:border-0 flex items-center justify-between group/item transition-colors"
                    onMouseDown={() => handleSuggestionClick(cert.qual_name)}
                  >
                    <span className="text-sm font-medium group-hover/item:text-blue-400">{cert.qual_name}</span>
                    <TrendingUp className="w-3 h-3 text-slate-600 opacity-0 group-hover/item:opacity-100 transition-all" />
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="lg:col-span-2 space-y-3">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
              <Filter className="w-3 h-3" /> 분야
            </label>
            <Select
              value={params.main_field || ALL_FIELDS}
              onValueChange={(val) => updateParam('main_field', val)}
            >
              <SelectTrigger className="h-11 bg-black/20 border-slate-800 text-white rounded-xl">
                <SelectValue placeholder="전체 분야" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-white max-h-[300px]">
                <SelectItem value={ALL_FIELDS}>전체 분야</SelectItem>
                {filters?.main_fields.map((f: string) => (
                  <SelectItem key={f} value={f}>{f}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="lg:col-span-2 space-y-3">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
              <ArrowUpDown className="w-3 h-3" /> 정렬 기준
            </label>
            <div className="flex gap-2">
              <Select
                value={params.sort}
                onValueChange={(val) => updateParam('sort', val as SortOption)}
              >
                <SelectTrigger className="h-11 bg-black/20 border-slate-800 text-white rounded-xl text-xs sm:text-sm flex-1">
                  <SelectValue placeholder="정렬" />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-800 text-white">
                  <SelectItem value="name">이름순</SelectItem>
                  <SelectItem value="pass_rate">합격률순</SelectItem>
                  <SelectItem value="difficulty">난이도순</SelectItem>
                  <SelectItem value="recent">최신순</SelectItem>
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="outline"
                onClick={() => setParams(prev => ({ ...prev, sort_desc: !prev.sort_desc }))}
                className="h-11 w-11 p-0 border-slate-800 bg-black/20 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl shrink-0"
                title={params.sort_desc ? "내림차순 (높은순)" : "오름차순 (낮은순)"}
              >
                {params.sort_desc ? (
                  <TrendingUp className="w-4 h-4 rotate-180" />
                ) : (
                  <TrendingUp className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>

          <div className="lg:col-span-4 flex gap-3">
            <div className="flex-1 flex items-center justify-center bg-blue-600/5 border border-blue-500/20 rounded-xl px-4 text-[10px] font-bold text-blue-400 uppercase tracking-widest">
              <Zap className="w-3 h-3 mr-2 animate-pulse" /> Real-time Analysis Active
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setInputValue('');
                setParams({ page: 1, page_size: 20, sort: 'name' });
              }}
              className="h-11 px-4 border-slate-800 text-slate-400 hover:bg-slate-800 rounded-xl"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </form>

        {/* Popular Keywords */}
        <div className="flex items-center gap-2 pt-2 px-1 overflow-x-auto pb-2 scrollbar-hide">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest whitespace-nowrap mr-2">
            인기 검색어
          </span>
          {trendingCerts.length > 0 ? (
            trendingCerts.map((cert) => (
              <Badge
                key={cert.qual_id}
                variant="outline"
                className="cursor-pointer bg-slate-900/50 hover:bg-blue-600/20 hover:text-blue-400 hover:border-blue-500/30 transition-all whitespace-nowrap"
                onClick={() => {
                  setInputValue(cert.qual_name);
                  updateParam('q', cert.qual_name);
                }}
              >
                {cert.qual_name}
              </Badge>
            ))
          ) : (
            ["정보처리기사", "산업안전기사", "컴퓨터활용능력1급", "전기기사", "데이터분석준전문가"].map((keyword) => (
              <Badge
                key={keyword}
                variant="outline"
                className="cursor-pointer bg-slate-900/50 hover:bg-blue-600/20 hover:text-blue-400 hover:border-blue-500/30 transition-all whitespace-nowrap"
                onClick={() => {
                  setInputValue(keyword);
                  updateParam('q', keyword);
                }}
              >
                {keyword}
              </Badge>
            ))
          )}
        </div>

        {/* Categories Chips */}
        <div className="flex flex-wrap gap-2 pt-4 border-t border-slate-800/50">
          <Badge
            variant={!params.qual_type ? "secondary" : "outline"}
            className="cursor-pointer px-3 py-1 rounded-full text-xs"
            onClick={() => updateParam('qual_type', ALL_TYPES)}
          >
            전체
          </Badge>
          {filters?.qual_types.map((t: string) => (
            <Badge
              key={t}
              variant={params.qual_type === t ? "secondary" : "outline"}
              className={`cursor-pointer px-3 py-1 rounded-full text-xs transition-all ${params.qual_type === t ? 'bg-blue-600 text-white border-none' : 'hover:border-slate-600'}`}
              onClick={() => updateParam('qual_type', t)}
            >
              {t}
            </Badge>
          ))}
          <Badge
            variant={isFavoritesOnly ? "secondary" : "outline"}
            className={`cursor-pointer px-3 py-1 rounded-full text-xs transition-all ${isFavoritesOnly ? 'bg-amber-500 text-white border-none' : 'hover:border-slate-600 text-amber-500/70'}`}
            onClick={() => {
              const next = !isFavoritesOnly;
              setIsFavoritesOnly(next);
              setParams(prev => ({ ...prev, page_size: next ? 100 : 20 }));
            }}
          >
            <Bookmark className={`w-3 h-3 mr-1 ${isFavoritesOnly ? 'fill-white' : ''}`} />
            관심 자격증만 보기
          </Badge>
        </div>
      </div>

      {/* Error State */}
      {error && !loading && (
        <Card className="bg-red-500/5 border-red-500/20 py-20">
          <CardContent className="flex flex-col items-center justify-center space-y-4">
            <SearchX className="w-12 h-12 text-red-500 opacity-50" />
            <div className="text-center">
              <h3 className="text-xl font-bold text-white">데이터를 불러오지 못했습니다</h3>
              <p className="text-slate-400">네트워크 상태를 확인하거나 잠시 후 다시 시도해주세요.</p>
            </div>
            <Button onClick={() => refetch()} variant="outline" className="border-red-500/30 text-red-400">다시 시도</Button>
          </CardContent>
        </Card>
      )}

      {/* Content Section */}
      <div className="min-h-[400px]">
        {(loading || (isFavoritesOnly && favoritesLoading)) ? (
          <div className={viewMode === 'grid' ? "grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" : "space-y-4"}>
            {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
              <Skeleton key={i} className={`bg-slate-900/50 ${viewMode === 'grid' ? 'h-64 rounded-3xl' : 'h-24 rounded-2xl'}`} />
            ))}
          </div>
        ) : !data || filteredItems.length === 0 ? (
          <Card className="bg-slate-900/30 border-slate-800 border-dashed py-32">
            <CardContent className="flex flex-col items-center justify-center space-y-6">
              <div className="p-6 bg-slate-900 rounded-full">
                <SearchX className="w-16 h-16 text-slate-700" />
              </div>
              <div className="text-center space-y-2">
                <h3 className="text-2xl font-bold text-white">일치하는 자격증을 찾을 수 없습니다</h3>
                <p className="text-slate-500">{isFavoritesOnly ? "관심 자격증으로 등록된 항목이 없습니다." : "다른 검색어나 필터를 사용해 보세요."}</p>
              </div>
              <Button
                variant="outline"
                onClick={() => {
                  setParams({ page: 1, page_size: 20, sort: 'name' });
                  setIsFavoritesOnly(false);
                }}
                className="border-slate-800 text-slate-400 hover:text-white"
              >
                필터 초기화
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className={viewMode === 'grid' ? "grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" : "space-y-4"}>
            {filteredItems.map((cert: any) => (
              <Card
                key={cert.qual_id}
                onClick={() => router.navigate(`/certs/${cert.qual_id}`)}
                className={`group cursor-pointer bg-slate-900 border-slate-800 hover:border-blue-500/40 transition-all duration-300 overflow-hidden ${viewMode === 'list' ? 'flex flex-row items-center py-2' : 'flex flex-col'}`}
              >
                {viewMode === 'grid' ? (
                  <>
                    <div className="h-1.5 w-full bg-slate-800 group-hover:bg-blue-600 transition-colors" />
                    <CardContent className="p-8 space-y-6">
                      <div className="flex justify-between items-start">
                        <Badge className="bg-slate-950 text-slate-400 border-slate-800 px-2 py-0.5 text-xs">{cert.qual_type}</Badge>
                        <div className="flex gap-2">
                          <Bookmark
                            className={`w-4 h-4 cursor-pointer transition-all hover:scale-125 ${favoriteIds.includes(cert.qual_id) ? 'text-amber-500 fill-amber-500' : 'text-slate-600 hover:text-amber-500'}`}
                            onClick={(e) => toggleFavorite(e, cert)}
                          />
                          <Award className={`w-5 h-5 ${cert.latest_pass_rate && cert.latest_pass_rate < 30 ? 'text-orange-500' : 'text-slate-600 group-hover:text-blue-500/50'}`} />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <h3 className="text-xl font-bold text-white group-hover:text-blue-400 transition-colors line-clamp-2 min-h-[56px]">
                          {cert.qual_name}
                        </h3>
                        <p className="text-xs text-slate-500 font-medium tracking-tight">
                          {cert.managing_body || "관리기관 정보 없음"}
                        </p>
                      </div>

                      <div className="grid grid-cols-2 gap-3 pt-4 border-t border-slate-800/50">
                        <div className="space-y-1">
                          <p className="text-[10px] uppercase font-bold text-slate-600 tracking-wider">Pass Rate</p>
                          <p className="text-sm font-bold text-emerald-400 flex items-center gap-1">
                            <Zap className="w-3 h-3 fill-emerald-400" />
                            {(cert.latest_pass_rate !== null && cert.latest_pass_rate !== undefined) ? `${cert.latest_pass_rate}%` : '정보 없음'}
                          </p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-[10px] uppercase font-bold text-slate-600 tracking-wider">Difficulty</p>
                          <p className="text-sm font-bold text-indigo-400 flex items-center gap-1">
                            <TrendingUp className="w-3 h-3" />
                            {(cert.avg_difficulty !== null && cert.avg_difficulty !== undefined) ? `${cert.avg_difficulty}/10` : '정보 없음'}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </>
                ) : (
                  <div className="flex w-full items-center px-8 py-4 gap-6">
                    <div className="p-3 bg-slate-950 rounded-xl group-hover:bg-blue-600/10 transition-colors">
                      <Award className="w-6 h-6 text-slate-500 group-hover:text-blue-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors truncate">
                        {cert.qual_name}
                      </h3>
                      <p className="text-sm text-slate-500">{cert.managing_body} • {cert.qual_type}</p>
                    </div>
                    <div className="flex gap-8 items-center">
                      <div className="text-right hidden sm:block">
                        <p className="text-[10px] uppercase font-bold text-slate-600 mb-0.5">최신 합격률</p>
                        <p className="text-base font-bold text-emerald-400">{(cert.latest_pass_rate !== null && cert.latest_pass_rate !== undefined) ? `${cert.latest_pass_rate}%` : "정보 없음"}</p>
                      </div>
                      <div className="text-right hidden sm:block">
                        <p className="text-[10px] uppercase font-bold text-slate-600 mb-0.5">평균 난이도</p>
                        <p className="text-base font-bold text-indigo-400">{(cert.avg_difficulty !== null && cert.avg_difficulty !== undefined) ? `${cert.avg_difficulty}` : "정보 없음"}</p>
                      </div>
                      <ChevronDown className="w-5 h-5 text-slate-700 -rotate-90 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
                    </div>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Pagination Controls */}
      {!loading && data && data.total_pages > 1 && (
        <div className="flex justify-center items-center gap-4 pt-10">
          <Button
            variant="outline"
            disabled={params.page === 1}
            onClick={() => updateParam('page', params.page! - 1)}
            className="border-slate-800 text-white disabled:opacity-30 rounded-xl"
          >
            이전
          </Button>
          <div className="flex items-center gap-2">
            {Array.from({ length: Math.min(5, data.total_pages) }, (_, i) => {
              // Calculate start page to show a window around current page
              const startPage = Math.max(1, Math.min(params.page! - 2, Math.max(1, data.total_pages - 4)));
              const p = startPage + i;
              if (p > data.total_pages) return null;

              return (
                <Button
                  key={p}
                  variant={params.page === p ? "secondary" : "ghost"}
                  onClick={() => updateParam('page', p)}
                  className="h-10 w-10 p-0 rounded-xl"
                >
                  {p}
                </Button>
              );
            })}
          </div>
          <Button
            variant="outline"
            disabled={params.page === data.total_pages}
            onClick={() => updateParam('page', params.page! + 1)}
            className="border-slate-800 text-white disabled:opacity-30 rounded-xl"
          >
            다음
          </Button>
        </div>
      )}
    </div>
  );
}
