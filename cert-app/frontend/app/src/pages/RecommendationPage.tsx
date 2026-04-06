
import { useState, useMemo } from 'react';
import { Sparkles, ArrowRight, Award, Building2, Tag, TrendingUp, GraduationCap, CircleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription, EmptyContent } from '@/components/ui/empty';
import { useRecommendations, useMajors, usePopularMajors } from '@/hooks/useRecommendations';
import { useRouter } from '@/lib/router';
import { RAG_VERSION_MARK } from '@/lib/ragProductCopy';

const sampleMajors = [
  '컴퓨터공학',
  '정보통신공학',
  '전자공학',
  '전기공학',
  '기계공학',
  '건축학',
  '경영학',
  '회계학',
  '의학',
  '간호학',
];

export function RecommendationPage() {
  const [major, setMajor] = useState('');
  const [inputValue, setInputValue] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [majorExactMode, setMajorExactMode] = useState(false);
  const { navigate } = useRouter();

  const { data: recommendations, loading, error } = useRecommendations(
    submitted ? major : '',
    30,
    5
  );
  const { majors: availableMajors } = useMajors();
  const { majors: popularMajorsFromApi, loading: popularMajorsLoading } = usePopularMajors(12);

  const filteredMajors = useMemo(() => {
    const list = (availableMajors && availableMajors.length > 0) ? availableMajors : sampleMajors;
    const t = inputValue.trim();
    if (!t) return list.slice(0, 40);
    if (majorExactMode) return list.filter(m => m === t);
    return list.filter(m => m.toLowerCase().includes(t.toLowerCase()));
  }, [availableMajors, inputValue, majorExactMode]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setMajorExactMode(false);
    if (inputValue.trim()) {
      setMajor(inputValue.trim());
      setSubmitted(true);
      setShowSuggestions(false);
    }
  };

  const handleMajorClick = (m: string) => {
    setMajorExactMode(false);
    setMajor(m);
    setInputValue(m);
    setSubmitted(true);
    setShowSuggestions(false);
  };

  const navigateToCert = (qualId: number) => {
    navigate(`/certs/${qualId}`);
  };

  // 인기 전공: 백엔드 /recommendations/popular-majors (profiles.detail_major 사용자 수 내림차순) 결과만 사용
  const popularMajors = popularMajorsFromApi;

  return (
    <div className="space-y-8 pb-10">
      {/* Header */}
      <div className="text-center space-y-4">
        <Badge
          variant="secondary"
          className="bg-purple-500/10 text-purple-400 border-purple-500/20"
        >
          <Sparkles className="w-3 h-3 mr-1" />
          전공·DB 매핑 기반 추천
        </Badge>
        <h1 className="text-3xl font-bold text-white">
          <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            전공 기반 자격증 추천
          </span>
        </h1>
        <p className="text-slate-300 max-w-lg mx-auto">
          전공을 입력하면 DB에 축적된 전공–자격증 매핑과 합격률·난이도 데이터를 바탕으로 목록을 구성합니다.
          BM25·시맨틱·Contrastive 하이브리드 RAG({RAG_VERSION_MARK}) 기반 맞춤 추천은 상단 메뉴의{' '}
          <span className="text-purple-300 font-semibold">AI 추천</span>에서 이용할 수 있습니다.
        </p>
      </div>

      {/* Search Form with Custom Dropdown */}
      <div className="max-w-xl mx-auto relative group">
        <form onSubmit={handleSubmit} className="relative z-20">
          <label htmlFor="major-search-input" className="sr-only">전공 검색</label>
          <GraduationCap className="absolute left-4 w-5 h-5 text-slate-400 z-10 top-1/2 -translate-y-1/2" />
          <Input
            id="major-search-input"
            name="major"
            type="text"
            autoComplete="off"
            placeholder="전공을 입력하세요 (예: 컴퓨터공학)"
            value={inputValue}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            onChange={(e) => {
              setMajorExactMode(false);
              setInputValue(e.target.value);
              setShowSuggestions(true);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                setMajorExactMode(false);
                setShowSuggestions(false);
                return;
              }
              if (e.key !== 'Enter') return;
              const t = inputValue.trim();
              if (!t) return;
              const list = (availableMajors && availableMajors.length > 0) ? availableMajors : sampleMajors;
              const exact = list.filter(m => m === t);
              if (exact.length === 1) {
                e.preventDefault();
                handleMajorClick(exact[0]!);
                return;
              }
              e.preventDefault();
              setMajorExactMode(true);
              setShowSuggestions(true);
            }}
            className="pl-12 pr-36 h-14 text-lg bg-slate-900/50 border-slate-700 rounded-xl focus:border-purple-500 focus:ring-purple-500/20 text-white placeholder:text-slate-600 shadow-xl"
          />
          <Button
            type="submit"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 h-11 bg-purple-600 hover:bg-purple-700 px-6 rounded-lg text-white font-semibold transition-all active:scale-95"
            disabled={loading}
          >
            {loading ? (
              <Skeleton className="w-5 h-5 bg-purple-400/50" />
            ) : (
              "전공 탐색"
            )}
          </Button>
        </form>

        {/* Custom Suggestions Dropdown */}
        {showSuggestions && (filteredMajors.length > 0 || majorExactMode) && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50 max-h-[min(22rem,70vh)] overflow-y-auto overflow-x-hidden overscroll-contain scrollbar-thin scrollbar-thumb-slate-700 animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="p-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-950/20 border-b border-slate-800">
              전공 검색 결과 ({filteredMajors.length})
            </div>
            {filteredMajors.length > 0 ? (
              filteredMajors.map((m, idx) => (
                <div
                  key={`${m}__${idx}`}
                  className="px-4 py-3 hover:bg-slate-800 cursor-pointer text-slate-200 border-b border-slate-800/50 last:border-0 flex items-center justify-between group/item transition-colors"
                  onMouseDown={() => handleMajorClick(m)}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-2 h-2 rounded-full bg-purple-500/30 group-hover/item:bg-purple-500 transition-colors shrink-0" />
                    <span className="group-hover/item:text-white break-words">{m}</span>
                  </div>
                  <ArrowRight className="w-3 h-3 text-slate-600 opacity-0 group-hover/item:opacity-100 -translate-x-2 group-hover/item:translate-x-0 transition-all shrink-0" />
                </div>
              ))
            ) : (
              <div className="px-4 py-3 text-sm text-slate-500">
                입력과 정확히 같은 이름의 전공이 없습니다. Esc로 포함 검색으로 돌아가거나 &quot;전공 탐색&quot; 버튼을 눌러 주세요.
              </div>
            )}
            <p className="px-4 py-2 text-[10px] text-slate-600 border-t border-slate-800 bg-slate-950/40">
              {majorExactMode
                ? 'Esc: 포함 검색으로 · 정확 일치만 표시 중'
                : 'Enter: 정확히 일치하는 전공만 목록에 남깁니다 (1건이면 바로 선택)'}
            </p>
          </div>
        )}
      </div>

      {/* Quick Major Tags */}
      {!submitted && (
        <div className="max-w-2xl mx-auto text-center">
          <p className="text-sm text-slate-500 mb-4 font-medium uppercase tracking-wider">인기 전공 (사용자 설정 기준)</p>
          <div className="flex flex-wrap justify-center gap-2">
            {popularMajorsLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="w-20 h-8 bg-slate-800 rounded-full" />
              ))
            ) : popularMajors.length > 0 ? (
              popularMajors.map((m) => (
                <Button
                  key={m}
                  variant="outline"
                  size="sm"
                  onClick={() => handleMajorClick(m)}
                  className="rounded-full bg-slate-800/40 border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-purple-400 h-8 text-sm px-4"
                >
                  {m}
                </Button>
              ))
            ) : (
              <>
                <p className="text-slate-500 text-sm w-full mb-2">아직 사용자 설정 전공이 없어요. 위에서 전공을 검색해 보세요.</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {sampleMajors.map((m) => (
                    <Button
                      key={m}
                      variant="outline"
                      size="sm"
                      onClick={() => handleMajorClick(m)}
                      className="rounded-full bg-slate-800/40 border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-purple-400 h-8 text-sm px-4"
                    >
                      {m}
                    </Button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Results */}
      {submitted && (
        <div className="space-y-6 max-w-4xl mx-auto pt-4">
          {loading ? (
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-28 w-full bg-slate-900/50 rounded-xl border border-slate-800" />
              ))}
            </div>
          ) : error ? (
            <Card className="bg-slate-900 border-slate-800 shadow-xl">
              <CardContent className="p-12 text-center flex flex-col items-center gap-4">
                <CircleAlert className="w-12 h-12 text-red-500 mx-auto" />
                <div className="space-y-2">
                  <p className="text-xl font-bold text-white">결과를 불러올 수 없습니다</p>
                  <p className="text-slate-400">{error.message}</p>
                </div>
                <Button
                  onClick={() => setSubmitted(false)}
                  variant="outline"
                  className="border-slate-700"
                >
                  다시 검색하기
                </Button>
              </CardContent>
            </Card>
          ) : (recommendations?.items.length === 0) ? (
            <Card className="bg-slate-900/50 border-slate-800">
              <CardContent className="p-12">
                <Empty className="flex-col items-center justify-center border-0 p-0 gap-4">
                  <EmptyHeader>
                    <EmptyTitle className="text-lg text-slate-400">
                      &quot;<span className="text-white font-bold">{major}</span>&quot;에 대한 추천 결과가 없습니다.
                    </EmptyTitle>
                    <EmptyDescription className="text-sm text-slate-500 max-w-sm">
                      검색어 오타를 확인하거나, 다른 전공 키워드로 다시 시도해보세요.
                    </EmptyDescription>
                  </EmptyHeader>
                  <EmptyContent>
                    <Button
                      onClick={() => {
                        setSubmitted(false);
                        setInputValue('');
                      }}
                      variant="outline"
                      className="mt-2 border-slate-700"
                    >
                      다른 전공 검색
                    </Button>
                  </EmptyContent>
                </Empty>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="flex items-center justify-between px-2">
                <h2 className="text-xl font-bold text-white">
                  <span className="text-purple-400">&quot;{recommendations?.major}&quot;</span> 추천 자격증
                  <span className="text-slate-500 text-base font-medium ml-2">
                    ({recommendations?.total}개)
                  </span>
                </h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSubmitted(false);
                    setInputValue('');
                  }}
                  className="text-slate-400 hover:text-white"
                >
                  다시 검색
                </Button>
              </div>

              <div className="space-y-4">
                {recommendations?.items.map((rec, index) => (
                  <div
                    key={rec.qual_id}
                    onClick={() => navigateToCert(rec.qual_id)}
                    className="group"
                  >
                    <Card className="bg-slate-900/40 border-slate-800/60 hover:border-purple-500/50 transition-all hover:bg-slate-900/80 cursor-pointer shadow-sm">
                      <CardContent className="p-5">
                        <div className="flex items-start gap-5">
                          {/* Rank */}
                          <div className={`
                            w-12 h-12 rounded-xl flex items-center justify-center font-bold text-xl flex-shrink-0 shadow-lg
                            ${index === 0 ? 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20' :
                              index === 1 ? 'bg-slate-400/10 text-slate-300 border border-slate-400/20' :
                                index === 2 ? 'bg-orange-600/10 text-orange-400 border border-orange-600/20' :
                                  'bg-slate-800/50 text-slate-500 border border-slate-700'}
                          `}>
                            {index + 1}
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                              <div>
                                <h3 className="text-lg font-bold text-white group-hover:text-purple-400 transition-colors">
                                  {rec.qual_name}
                                </h3>
                                <div className="flex flex-wrap items-center gap-2 mt-1.5">
                                  {rec.qual_type && (
                                    <Badge variant="secondary" className="bg-slate-800 text-slate-300 border-slate-700">
                                      <Tag className="w-3 h-3 mr-1" />
                                      {rec.qual_type}
                                    </Badge>
                                  )}
                                  {rec.managing_body && (
                                    <span className="text-xs text-slate-500 flex items-center gap-1">
                                      <Building2 className="w-3.5 h-3.5" />
                                      {rec.managing_body}
                                    </span>
                                  )}
                                </div>
                              </div>

                              <div className="flex items-center gap-6 bg-slate-950/40 px-4 py-2 rounded-lg border border-slate-800/50">
                                {rec.latest_pass_rate !== null && (
                                  <div className="text-right">
                                    <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-0.5">합격률</p>
                                    <p className={`text-sm font-bold ${rec.latest_pass_rate >= 50 ? 'text-green-400' :
                                      rec.latest_pass_rate >= 30 ? 'text-yellow-400' : 'text-red-400'
                                      }`}>
                                      {rec.latest_pass_rate.toFixed(1)}%
                                    </p>
                                  </div>
                                )}
                                <div className="text-right pl-4 border-l border-slate-800">
                                  <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-0.5">추천점수</p>
                                  <p className="text-lg font-bold text-purple-400">{rec.score.toFixed(1)}</p>
                                </div>
                              </div>
                            </div>

                            {rec.reason && (
                              <div className="bg-purple-500/5 border border-purple-500/10 rounded-lg p-3 group-hover:bg-purple-500/10 transition-colors">
                                <p className="text-sm text-slate-400 flex items-start gap-2 leading-relaxed">
                                  <Sparkles className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
                                  {rec.reason}
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Info Cards */}
      {!submitted && (
        <div className="grid md:grid-cols-3 gap-6 pt-12 max-w-5xl mx-auto">
          <Card className="bg-slate-900/40 border-slate-800/80 hover:bg-slate-900/60 transition-colors shadow-sm">
            <CardContent className="p-6 space-y-4">
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-blue-400" />
              </div>
              <h3 className="text-lg font-bold text-white">데이터 기반 분석</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                합격률·응시자 수·난이도 등 실제 시험 데이터와 하이브리드 검색 결과를 반영해 신뢰할 수 있는 추천을 제공합니다.
              </p>
            </CardContent>
          </Card>

          <Card className="bg-slate-900/40 border-slate-800/80 hover:bg-slate-900/60 transition-colors shadow-sm">
            <CardContent className="p-6 space-y-4">
              <div className="w-12 h-12 rounded-xl bg-violet-500/10 flex items-center justify-center">
                <Award className="w-6 h-6 text-violet-400" />
              </div>
              <h3 className="text-lg font-bold text-white">전공 연관성</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                전공·관심사를 반영한 시멘틱 검색과 키워드 매칭을 결합해, 자격증 시험 과목과의 연관성을 분석하여 최적의 취득 경로를 제시합니다.
              </p>
            </CardContent>
          </Card>

          <Card className="bg-slate-900/40 border-slate-800/80 hover:bg-slate-900/60 transition-colors shadow-sm">
            <CardContent className="p-6 space-y-4">
              <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-purple-400" />
              </div>
              <h3 className="text-lg font-bold text-white">맞춤 성장 로드맵</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                학년·취득 자격증을 반영한 난이도 조정과 함께, 전공 맞춤 추천으로 단계별 자격증 취득 로드맵을 제안합니다.
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
