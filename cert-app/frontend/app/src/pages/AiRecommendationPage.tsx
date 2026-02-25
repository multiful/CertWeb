
import React, { useState, useMemo, useEffect } from 'react';
import {
    Sparkles,
    Tag,
    GraduationCap,
    BrainCircuit,
    MessageSquare,
    ChevronRight,
    ChevronDown,
    Info,
    Lock,
    LogIn,
    RefreshCw,
    Database,
    Target,
    Zap,
    GitMerge,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { getHybridRecommendations, getAvailableMajors } from '@/lib/api';
import { useRouter } from '@/lib/router';
import { useAuth } from '@/hooks/useAuth';
import type { HybridRecommendationResponse } from '@/types';
import { toast } from 'sonner';

const sampleMajors = [
    '컴퓨터공학', '정보통신공학', '전자공학', '전기공학', '기계공학',
    '건축학', '경영학', '회계학', '의학', '간호학', '데이터사이언스'
];

const AI_CACHE_KEY = 'ai-rec-cache';

const POPULAR_MAJORS = ['컴퓨터공학', '경영학', '전기공학', '간호학', '기계공학', '데이터사이언스'];

const AI_STATS = [
    {
        label: '자격증 DB',
        value: '1,103',
        unit: '개',
        icon: Database,
        color: 'blue',
        desc: '임베딩 완료된 국가 자격증',
    },
    {
        label: '평균 정합성',
        value: '87',
        unit: '%',
        icon: Target,
        color: 'green',
        desc: '상위 추천 결과 기준',
    },
    {
        label: '검색 방식',
        value: '하이브리드',
        unit: '',
        icon: GitMerge,
        color: 'purple',
        desc: '키워드 + 시멘틱 융합',
    },
    {
        label: '임베딩 차원',
        value: '1,536',
        unit: 'd',
        icon: BrainCircuit,
        color: 'indigo',
        desc: 'OpenAI text-embedding-3',
    },
] as const;

export function AiRecommendationPage() {
    const [major, setMajor] = useState('');
    const [interest, setInterest] = useState('');
    const [inputValue, setInputValue] = useState('');
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<HybridRecommendationResponse | null>(null);
    const [, setError] = useState<Error | null>(null);
    const { navigate } = useRouter();
    const { token } = useAuth();

    const [availableMajors, setAvailableMajors] = useState<string[]>([]);

    // 전공별 샘플 미리보기 상태
    const [selectedPreviewMajor, setSelectedPreviewMajor] = useState<string | null>(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [previewCache, setPreviewCache] = useState<Map<string, any[]>>(new Map());

    const handlePreviewMajor = async (m: string) => {
        setSelectedPreviewMajor(m);
        if (previewCache.has(m)) return;
        setPreviewLoading(true);
        try {
            const res = await getHybridRecommendations(m, '', 3, null);
            setPreviewCache(prev => new Map(prev).set(m, res.results));
        } catch {
            // 미리보기 실패 시 조용히 무시
        } finally {
            setPreviewLoading(false);
        }
    };

    const handleFillFromPreview = () => {
        if (!selectedPreviewMajor) return;
        setMajor(selectedPreviewMajor);
        setInputValue(selectedPreviewMajor);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    // 마운트 시 sessionStorage에서 이전 검색 상태 복원
    useEffect(() => {
        try {
            const cached = sessionStorage.getItem(AI_CACHE_KEY);
            if (cached) {
                const { major: m, interest: i, results: r } = JSON.parse(cached);
                if (m) { setMajor(m); setInputValue(m); }
                if (i) setInterest(i);
                if (r) setResults(r);
            }
        } catch {
            // 캐시 파싱 실패 시 무시
        }
    }, []);

    React.useEffect(() => {
        getAvailableMajors().then(res => setAvailableMajors(res.majors)).catch(() => { });
    }, []);

    const filteredMajors = useMemo(() => {
        const list = availableMajors.length > 0 ? availableMajors : sampleMajors;
        if (!inputValue.trim()) return list.slice(0, 10);
        return list.filter(m => m.includes(inputValue)).slice(0, 10);
    }, [availableMajors, inputValue]);

    const handleRecommend = async () => {
        if (!major) {
            toast.error('전공을 선택하거나 입력해주세요.');
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const res = await getHybridRecommendations(major, interest, 10, token);
            setResults(res);
            // 결과를 sessionStorage에 캐싱 → 뒤로가기 시 재호출 없이 복원
            try {
                sessionStorage.setItem(AI_CACHE_KEY, JSON.stringify({ major, interest, results: res }));
            } catch {
                // storage 용량 초과 등 무시
            }
        } catch (err: any) {
            console.error(err);
            toast.error('추천 결과를 가져오는데 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const handleReset = () => {
        setMajor('');
        setInterest('');
        setInputValue('');
        setResults(null);
        sessionStorage.removeItem(AI_CACHE_KEY);
    };

    const [expandedReasons, setExpandedReasons] = useState<Set<number>>(new Set());

    const toggleReason = (e: React.MouseEvent, qualId: number) => {
        e.stopPropagation();
        setExpandedReasons(prev => {
            const next = new Set(prev);
            next.has(qualId) ? next.delete(qualId) : next.add(qualId);
            return next;
        });
    };

    const navigateToCert = (qualId: number) => {
        navigate(`/certs/${qualId}`);
    };

    return (
        <div className="max-w-6xl mx-auto space-y-12 pb-20">
            {/* Hero Section */}
            <div className="relative rounded-3xl bg-slate-900 border border-slate-800 p-8 md:p-12 shadow-2xl">
                <div className="absolute top-0 right-0 -mt-20 -mr-20 w-96 h-96 bg-blue-500/10 rounded-full blur-[100px]" />
                <div className="absolute bottom-0 left-0 -mb-20 -ml-20 w-96 h-96 bg-purple-500/10 rounded-full blur-[100px]" />

                <div className="relative z-10 flex flex-col md:flex-row items-center gap-10">
                    <div className="flex-1 space-y-6">
                        <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20 px-3 py-1">
                            <BrainCircuit className="w-4 h-4 mr-2" />
                            AI 추천
                        </Badge>
                        <h1 className="text-4xl md:text-5xl font-extrabold text-white leading-tight">
                            관심사와 전공을 <br />
                            <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
                                하나의 로드맵으로.
                            </span>
                        </h1>
                        <p className="text-slate-400 text-lg max-w-xl">
                            나만의 전공과 커리어 목표에 딱 맞는 자격증을 <br />
                            인공지능이 실시간으로 분석하여 찾아드립니다.
                        </p>
                    </div>

                    <div className="w-full max-w-md bg-slate-950/60 backdrop-blur-md border border-slate-800 p-6 rounded-2xl shadow-inner relative z-30">
                        <div className="space-y-5">
                            <div className="space-y-2 relative">
                                <label htmlFor="major-input" className="text-sm font-bold text-slate-300 flex items-center gap-2">
                                    <GraduationCap className="w-4 h-4 text-blue-400" />
                                    나의 전공
                                </label>
                                <Input
                                    id="major-input"
                                    name="major"
                                    placeholder="예: 컴퓨터공학, 경영학"
                                    value={inputValue}
                                    onChange={(e) => {
                                        setInputValue(e.target.value);
                                        setMajor(e.target.value);
                                        setShowSuggestions(true);
                                    }}
                                    onFocus={() => setShowSuggestions(true)}
                                    className="bg-slate-900/80 border-slate-700 h-12 focus:ring-blue-500/20 text-white"
                                />
                                {showSuggestions && filteredMajors.length > 0 && (
                                    <div className="absolute top-full left-0 right-0 mt-1 bg-slate-900 border border-slate-700 rounded-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[100] max-h-60 overflow-y-auto overflow-x-hidden">
                                        {filteredMajors.map(m => (
                                            <div
                                                key={m}
                                                className="px-4 py-3 hover:bg-slate-800 cursor-pointer text-sm text-slate-300 transition-colors border-b border-slate-800 last:border-0"
                                                onClick={() => {
                                                    setMajor(m);
                                                    setInputValue(m);
                                                    setShowSuggestions(false);
                                                }}
                                            >
                                                {m}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="space-y-3">
                                <label htmlFor="career-interest" className="text-sm font-bold text-slate-300 flex items-center gap-2">
                                    <MessageSquare className="w-4 h-4 text-purple-400" />
                                    어떤 일을 하고 싶나요? (커리어 목표)
                                </label>
                                <textarea
                                    id="career-interest"
                                    name="interest"
                                    placeholder="예: 클라우드 보안 환경에서 일하고 싶어요. 데이터 분석을 금융에 적용하고 싶습니다."
                                    value={interest}
                                    onChange={(e) => setInterest(e.target.value)}
                                    className="w-full bg-slate-900/80 border-slate-700 rounded-lg p-3 text-sm h-28 focus:ring-purple-500/20 border outline-none text-white focus:border-purple-500 transition-all placeholder:text-slate-600 shadow-inner resize-none"
                                />
                                <p className="text-[11px] text-slate-500 leading-relaxed">
                                    AI는 입력한 전공·커리어 목표뿐 아니라, 마이페이지에 저장된
                                    <span className="font-semibold text-slate-300"> 학년, 학과, 관심 자격증, 취득 자격증, 난이도</span>
                                    를 함께 고려해 현재 레벨에 맞는 자격증 난이도를 추천합니다.
                                </p>
                            </div>

                            <Button
                                onClick={handleRecommend}
                                disabled={loading}
                                className="w-full h-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-lg rounded-xl shadow-lg shadow-blue-900/40"
                            >
                                {loading ? <Skeleton className="w-5 h-5 bg-white/30 rounded-full animate-pulse" /> : "AI 분석"}
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Results Section */}
            {loading && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3, 4, 5, 6].map(i => (
                        <Skeleton key={i} className="h-64 rounded-2xl bg-slate-900/50" />
                    ))}
                </div>
            )}

            {results && (
                <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="flex items-center justify-between flex-wrap gap-4">
                        <div className="space-y-1">
                            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                                <Sparkles className="w-6 h-6 text-yellow-500" />
                                분석 결과
                            </h2>
                            <p className="text-slate-400">
                                {results.major} 전공과 {results.interest ? `"${results.interest}"` : "시스템 데이터"}를 결합한 추천입니다.
                                {results.guest_limited && (
                                    <span className="ml-2 text-amber-400 font-medium text-xs">
                                        (비로그인 미리보기 — 상위 3개만 표시)
                                    </span>
                                )}
                            </p>
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleReset}
                            className="border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl"
                        >
                            <RefreshCw className="w-4 h-4 mr-2" />
                            다시 검색
                        </Button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {results.results.map((res, idx) => (
                            <Card
                                key={res.qual_id}
                                onClick={() => navigateToCert(res.qual_id)}
                                className="bg-slate-900/40 border-slate-800 hover:border-blue-500/40 hover:bg-slate-900 transition-all cursor-pointer group rounded-2xl overflow-hidden shadow-sm hover:shadow-blue-500/10"
                            >
                                <div className="h-2 bg-gradient-to-r from-blue-500 to-purple-600 opacity-20 group-hover:opacity-100 transition-opacity" />
                                <CardHeader className="pb-2">
                                    <div className="flex justify-between items-start">
                                        <div className="w-10 h-10 rounded-lg bg-slate-950 flex items-center justify-center text-blue-400 font-bold border border-slate-800">
                                            {idx + 1}
                                        </div>
                                        <div className="flex items-center gap-1.5 flex-wrap justify-end">
                                            {res.llm_reason && (
                                                <Badge className="bg-yellow-500/10 text-yellow-400 border-yellow-500/20 text-[9px] px-1.5 py-0">
                                                    ✦ AI 생성
                                                </Badge>
                                            )}
                                            <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                                                정합성 {Math.round(res.hybrid_score * 100)}%
                                            </Badge>
                                        </div>
                                    </div>
                                    <CardTitle className="text-xl font-bold text-white mt-4 group-hover:text-blue-400 transition-colors line-clamp-2">
                                        {res.qual_name}
                                    </CardTitle>
                                    {res.pass_rate != null && (
                                        <div className="flex items-center gap-2 mt-1">
                                            <span className="text-[11px] text-slate-500">합격률</span>
                                            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden max-w-[80px]">
                                                <div
                                                    className={`h-full rounded-full transition-all ${
                                                        res.pass_rate >= 50 ? 'bg-emerald-500' :
                                                        res.pass_rate >= 25 ? 'bg-yellow-500' : 'bg-red-500'
                                                    }`}
                                                    style={{ width: `${Math.min(res.pass_rate, 100)}%` }}
                                                />
                                            </div>
                                            <span className={`text-[11px] font-bold ${
                                                res.pass_rate >= 50 ? 'text-emerald-400' :
                                                res.pass_rate >= 25 ? 'text-yellow-400' : 'text-red-400'
                                            }`}>
                                                {res.pass_rate.toFixed(1)}%
                                            </span>
                                        </div>
                                    )}
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div
                                        className="flex items-start gap-2 bg-slate-950/50 p-3 rounded-xl border border-slate-800 cursor-pointer hover:border-indigo-500/40 hover:bg-slate-950/80 transition-all"
                                        onClick={(e) => toggleReason(e, res.qual_id)}
                                        title="클릭하면 설명을 펼칩니다"
                                    >
                                        <Info className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
                                        <div className="flex-1 min-w-0">
                                            <p className={`text-sm text-slate-400 leading-relaxed italic ${expandedReasons.has(res.qual_id) ? '' : 'line-clamp-3'}`}>
                                                {res.reason || "귀하의 전공 역량과 관심사를 고려하여 추천된 자격증입니다."}
                                            </p>
                                            <span className="mt-1.5 flex items-center gap-1 text-[11px] font-semibold text-indigo-400/70">
                                                {expandedReasons.has(res.qual_id) ? (
                                                    <>
                                                        <ChevronDown className="w-3 h-3 rotate-180" />
                                                        접기
                                                    </>
                                                ) : (
                                                    <>
                                                        <ChevronDown className="w-3 h-3" />
                                                        더보기
                                                    </>
                                                )}
                                            </span>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between text-xs font-bold text-slate-500 pt-2">
                                        <span className="flex items-center gap-1">
                                            <Tag className="w-3 h-3 text-blue-500" />
                                            전공 연관성
                                        </span>
                                        <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-blue-500 transition-all"
                                                style={{ width: `${res.major_score * 10}%` }}
                                            />
                                        </div>
                                    </div>
                                    <div className="flex items-center justify-between text-xs font-bold text-slate-500">
                                        <span className="flex items-center gap-1">
                                            <BrainCircuit className="w-3 h-3 text-purple-500" />
                                            관심도 일치
                                        </span>
                                        <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-purple-500 transition-all"
                                                style={{ width: `${res.semantic_similarity * 100}%` }}
                                            />
                                        </div>
                                    </div>

                                    <div className="pt-2 flex justify-end">
                                        <Button variant="ghost" size="sm" className="text-blue-400 group-hover:translate-x-1 transition-transform p-0 hover:bg-transparent">
                                            상세보기 <ChevronRight className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>

                    {/* 비로그인 잠금 UI */}
                    {results.guest_limited && (
                        <div className="relative">
                            {/* 블러 처리된 더미 카드들 */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pointer-events-none select-none blur-sm opacity-40">
                                {[4, 5, 6, 7].map(i => (
                                    <Card key={i} className="bg-slate-900/40 border-slate-800 rounded-2xl overflow-hidden">
                                        <div className="h-2 bg-gradient-to-r from-blue-500 to-purple-600 opacity-30" />
                                        <CardHeader className="pb-2">
                                            <div className="flex justify-between items-start">
                                                <div className="w-10 h-10 rounded-lg bg-slate-950 flex items-center justify-center text-blue-400 font-bold border border-slate-800">{i}</div>
                                                <div className="h-6 w-20 bg-slate-800 rounded-full" />
                                            </div>
                                            <div className="h-6 w-3/4 bg-slate-800 rounded-lg mt-4" />
                                        </CardHeader>
                                        <CardContent className="space-y-3">
                                            <div className="h-16 bg-slate-950/50 rounded-xl" />
                                            <div className="h-4 w-full bg-slate-800 rounded" />
                                            <div className="h-4 w-4/5 bg-slate-800 rounded" />
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>

                            {/* 잠금 오버레이 */}
                            <div className="absolute inset-0 flex items-center justify-center">
                                <div className="bg-slate-950/90 backdrop-blur-md border border-slate-700 rounded-3xl p-8 text-center space-y-5 shadow-2xl max-w-sm mx-auto">
                                    <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center mx-auto">
                                        <Lock className="w-7 h-7 text-blue-400" />
                                    </div>
                                    <div className="space-y-2">
                                        <h3 className="text-lg font-bold text-white">더 많은 자격증을 확인하려면</h3>
                                        <p className="text-slate-400 text-sm leading-relaxed">
                                            로그인하면 맞춤형 추천 결과를 <br />
                                            <span className="text-blue-400 font-semibold">최대 10개</span>까지 확인할 수 있습니다.<br />
                                            학년·취득 자격증 기반 난이도 조정도 지원됩니다.
                                        </p>
                                    </div>
                                    <Button
                                        onClick={() => navigate('/auth/login')}
                                        className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-xl"
                                    >
                                        <LogIn className="w-4 h-4 mr-2" />
                                        로그인하고 전체 결과 보기
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* AI 시스템 패널 + 전공별 샘플 미리보기 */}
            {!results && !loading && (
                <div className="space-y-10 pt-8 border-t border-slate-800/50">

                    {/* ── 1. AI 알고리즘 스탯 카드 ── */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-2">
                            <Zap className="w-4 h-4 text-blue-400" />
                            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest">AI 엔진 스펙</h3>
                        </div>
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            {AI_STATS.map((stat) => {
                                const Icon = stat.icon;
                                const colorMap = {
                                    blue: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
                                    green: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
                                    purple: 'bg-purple-500/10 border-purple-500/20 text-purple-400',
                                    indigo: 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400',
                                } as const;
                                return (
                                    <div key={stat.label} className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 space-y-3">
                                        <div className={`w-9 h-9 rounded-xl border flex items-center justify-center ${colorMap[stat.color]}`}>
                                            <Icon className="w-4 h-4" />
                                        </div>
                                        <div>
                                            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">{stat.label}</p>
                                            <p className="text-2xl font-black text-white mt-0.5">
                                                {stat.value}
                                                {stat.unit && <span className="text-sm font-semibold text-slate-500 ml-1">{stat.unit}</span>}
                                            </p>
                                            <p className="text-[11px] text-slate-600 mt-1">{stat.desc}</p>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        {/* 정합성 점수 구성 바 */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-4">
                            <div className="flex items-center justify-between">
                                <p className="text-sm font-bold text-slate-300 flex items-center gap-2">
                                    <GitMerge className="w-4 h-4 text-purple-400" />
                                    정합성 점수 구성 (Hybrid Score)
                                </p>
                                <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20 text-[10px]">
                                    하이브리드 알고리즘
                                </Badge>
                            </div>
                            <div className="space-y-3">
                                <div className="space-y-1.5">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-blue-400 font-semibold flex items-center gap-1.5">
                                            <div className="w-2.5 h-2.5 rounded-sm bg-blue-500" />
                                            전공 연관성 (Major Score)
                                        </span>
                                        <span className="text-blue-400 font-bold">40%</span>
                                    </div>
                                    <div className="h-2.5 bg-slate-800 rounded-full overflow-hidden">
                                        <div className="h-full w-[40%] bg-gradient-to-r from-blue-600 to-blue-400 rounded-full" />
                                    </div>
                                    <p className="text-[11px] text-slate-600">전공 분야와 자격증 출제 범위 간 키워드 매칭 점수</p>
                                </div>
                                <div className="space-y-1.5">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-purple-400 font-semibold flex items-center gap-1.5">
                                            <div className="w-2.5 h-2.5 rounded-sm bg-purple-500" />
                                            AI 시멘틱 유사도 (Semantic Score)
                                        </span>
                                        <span className="text-purple-400 font-bold">60%</span>
                                    </div>
                                    <div className="h-2.5 bg-slate-800 rounded-full overflow-hidden">
                                        <div className="h-full w-[60%] bg-gradient-to-r from-purple-600 to-indigo-400 rounded-full" />
                                    </div>
                                    <p className="text-[11px] text-slate-600">1,536차원 벡터 공간에서 관심사와 자격증 설명의 코사인 유사도</p>
                                </div>
                            </div>
                            <p className="text-[11px] text-slate-500 pt-1 border-t border-slate-800">
                                최종 정합성 = Major Score × 0.4 + Semantic Score × 0.6
                            </p>
                        </div>
                    </div>

                    {/* ── 2. 전공별 AI 추천 미리보기 ── */}
                    <div className="space-y-5">
                        <div className="flex items-center justify-between flex-wrap gap-3">
                            <div className="flex items-center gap-2">
                                <Sparkles className="w-4 h-4 text-yellow-400" />
                                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest">전공별 AI 추천 미리보기</h3>
                            </div>
                            <p className="text-xs text-slate-600">탭을 클릭하면 실제 AI가 분석합니다</p>
                        </div>

                        {/* 전공 탭 */}
                        <div className="flex flex-wrap gap-2">
                            {POPULAR_MAJORS.map((m) => (
                                <button
                                    key={m}
                                    onClick={() => handlePreviewMajor(m)}
                                    className={`px-4 py-2 rounded-xl text-sm font-semibold border transition-all ${
                                        selectedPreviewMajor === m
                                            ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-900/30'
                                            : 'bg-slate-900/50 border-slate-800 text-slate-400 hover:border-blue-500/40 hover:text-slate-200'
                                    }`}
                                >
                                    {m}
                                    {previewCache.has(m) && selectedPreviewMajor !== m && (
                                        <span className="ml-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
                                    )}
                                </button>
                            ))}
                        </div>

                        {/* 미리보기 결과 */}
                        {selectedPreviewMajor && (
                            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                                {previewLoading ? (
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        {[0, 1, 2].map(i => (
                                            <div key={i} className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-3">
                                                <div className="flex justify-between">
                                                    <div className="w-8 h-8 rounded-lg bg-slate-800 animate-pulse" />
                                                    <div className="h-5 w-20 bg-slate-800 rounded-full animate-pulse" />
                                                </div>
                                                <div className="h-5 w-full bg-slate-800 rounded animate-pulse" />
                                                <div className="h-5 w-3/4 bg-slate-800 rounded animate-pulse" />
                                                <div className="h-12 bg-slate-950/50 rounded-xl animate-pulse" />
                                            </div>
                                        ))}
                                    </div>
                                ) : (previewCache.get(selectedPreviewMajor) || []).length > 0 ? (
                                    <>
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                            {(previewCache.get(selectedPreviewMajor) || []).map((res: any, idx: number) => (
                                                <div
                                                    key={res.qual_id}
                                                    onClick={() => navigate(`/certs/${res.qual_id}`)}
                                                    className="group bg-slate-900/40 border border-slate-800 hover:border-blue-500/40 hover:bg-slate-900 rounded-2xl p-5 cursor-pointer transition-all space-y-3"
                                                >
                                                    <div className="flex items-center justify-between">
                                                        <div className="w-8 h-8 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-center text-xs font-bold text-slate-400">
                                                            {idx + 1}
                                                        </div>
                                                        <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20 text-[10px]">
                                                            정합성 {Math.round(res.hybrid_score * 100)}%
                                                        </Badge>
                                                    </div>
                                                    <p className="text-sm font-bold text-white group-hover:text-blue-300 transition-colors line-clamp-2 leading-snug">
                                                        {res.qual_name}
                                                    </p>
                                                    {res.reason && (
                                                        <p className="text-[11px] text-slate-500 leading-relaxed line-clamp-2 italic">
                                                            {res.reason}
                                                        </p>
                                                    )}
                                                    {/* 미니 스코어 바 */}
                                                    <div className="space-y-1.5 pt-1">
                                                        <div className="flex items-center gap-2">
                                                            <div className="w-2 h-2 rounded-sm bg-blue-500 shrink-0" />
                                                            <div className="h-1 flex-1 bg-slate-800 rounded-full overflow-hidden">
                                                                <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${res.major_score * 10}%` }} />
                                                            </div>
                                                            <span className="text-[10px] text-slate-600 w-8 shrink-0">전공</span>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            <div className="w-2 h-2 rounded-sm bg-purple-500 shrink-0" />
                                                            <div className="h-1 flex-1 bg-slate-800 rounded-full overflow-hidden">
                                                                <div className="h-full bg-purple-500 rounded-full transition-all" style={{ width: `${res.semantic_similarity * 100}%` }} />
                                                            </div>
                                                            <span className="text-[10px] text-slate-600 w-8 shrink-0">AI</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        <div className="flex items-center gap-3 pt-1">
                                            <Button
                                                onClick={handleFillFromPreview}
                                                className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-xl text-sm h-10 px-5"
                                            >
                                                <GraduationCap className="w-4 h-4 mr-2" />
                                                {selectedPreviewMajor} 전공으로 상세 분석하기
                                            </Button>
                                            <p className="text-xs text-slate-600">커리어 목표를 추가하면 더 정확해집니다</p>
                                        </div>
                                    </>
                                ) : (
                                    <p className="text-sm text-slate-500 text-center py-8">미리보기 결과를 불러오지 못했습니다.</p>
                                )}
                            </div>
                        )}

                        {!selectedPreviewMajor && (
                            <div className="flex items-center justify-center h-24 rounded-2xl border border-dashed border-slate-800 text-slate-600 text-sm">
                                위 전공 탭을 클릭하면 AI가 실시간으로 추천 결과를 미리 보여드립니다
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
