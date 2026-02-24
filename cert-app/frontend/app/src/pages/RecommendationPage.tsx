
import { useState, useMemo } from 'react';
import { Sparkles, ArrowRight, Award, Building2, Tag, TrendingUp, GraduationCap, CircleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useRecommendations, useMajors, usePopularMajors } from '@/hooks/useRecommendations';
import { useRouter } from '@/lib/router';

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
  const { navigate } = useRouter();

  const { data: recommendations, loading, error } = useRecommendations(
    submitted ? major : '',
    15
  );
  const { majors: availableMajors, loading: majorsLoading } = useMajors();
  const { majors: popularMajorsFromApi } = usePopularMajors(12);

  const filteredMajors = useMemo(() => {
    const list = (availableMajors && availableMajors.length > 0) ? availableMajors : sampleMajors;
    if (!inputValue.trim()) return list.slice(0, 50);
    return list
      .filter(m => m.toLowerCase().includes(inputValue.toLowerCase()))
      .slice(0, 50);
  }, [availableMajors, inputValue]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      setMajor(inputValue.trim());
      setSubmitted(true);
      setShowSuggestions(false);
    }
  };

  const handleMajorClick = (m: string) => {
    setMajor(m);
    setInputValue(m);
    setSubmitted(true);
    setShowSuggestions(false);
  };

  const navigateToCert = (qualId: number) => {
    navigate(`/certs/${qualId}`);
  };

  const popularMajors =
    popularMajorsFromApi.length > 0
      ? popularMajorsFromApi
      : (availableMajors && availableMajors.length > 0)
        ? availableMajors.slice(0, 10)
        : sampleMajors;

  return (
    <div className="space-y-8 pb-10">
      {/* Header */}
      <div className="text-center space-y-4">
        <Badge
          variant="secondary"
          className="bg-purple-500/10 text-purple-400 border-purple-500/20"
        >
          <Sparkles className="w-3 h-3 mr-1" />
          AI 기반 맞춤 추천
        </Badge>
        <h1 className="text-3xl font-bold text-white">
          <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            전공 기반 자격증 추천
          </span>
        </h1>
        <p className="text-slate-300 max-w-lg mx-auto">
          전공을 입력하면 해당 분야에 적합한 자격증을 추천해드립니다.
          합격률, 난이도, 연관성을 실시간 데이터로 분석합니다.
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
              setInputValue(e.target.value);
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
        {showSuggestions && filteredMajors.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50 max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-slate-700 animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="p-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-950/20 border-b border-slate-800">
              전공 검색 결과 ({filteredMajors.length})
            </div>
            {filteredMajors.map((m) => (
              <div
                key={m}
                className="px-4 py-3 hover:bg-slate-800 cursor-pointer text-slate-200 border-b border-slate-800/50 last:border-0 flex items-center justify-between group/item transition-colors"
                onMouseDown={() => handleMajorClick(m)}
              >
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-purple-500/30 group-hover/item:bg-purple-500 transition-colors" />
                  <span className="group-hover/item:text-white">{m}</span>
                </div>
                <ArrowRight className="w-3 h-3 text-slate-600 opacity-0 group-hover/item:opacity-100 -translate-x-2 group-hover/item:translate-x-0 transition-all" />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Major Tags */}
      {!submitted && (
        <div className="max-w-2xl mx-auto text-center">
          <p className="text-sm text-slate-500 mb-4 font-medium uppercase tracking-wider">인기 전공</p>
          <div className="flex flex-wrap justify-center gap-2">
            {majorsLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="w-20 h-8 bg-slate-800 rounded-full" />
              ))
            ) : (
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
              <CardContent className="p-12 text-center flex flex-col items-center gap-4">
                <p className="text-lg text-slate-400">
                  &quot;<span className="text-white font-bold">{major}</span>&quot;에 대한 추천 결과가 없습니다.
                </p>
                <div className="text-sm text-slate-500 max-w-sm">
                  검색어 오타를 확인하거나, 다른 전공 키워드로 다시 시도해보세요.
                </div>
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
                실제 합격률, 응시자 수, 난이도 데이터를 종합적으로 분석하여 신뢰할 수 있는 추천을 제공합니다.
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
                입력하신 전공의 커리큘럼과 자격증 시험 과목의 연관성을 심층 분석하여 최적의 경로를 제시합니다.
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
                단순한 자격증 추천을 넘어, 사용자의 커리어 성장을 위한 단계별 자격증 취득 로드맵을 함께 고민합니다.
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
