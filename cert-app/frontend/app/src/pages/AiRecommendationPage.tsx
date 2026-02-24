
import React, { useState, useMemo } from 'react';
import {
    Sparkles,
    Tag,
    Search,
    GraduationCap,
    BrainCircuit,
    MessageSquare,
    ChevronRight,
    Info
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
        if (!token) {
            toast.error('AI 추천은 로그인 후 이용할 수 있습니다.');
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const res = await getHybridRecommendations(major, interest, 10, token);
            setResults(res);
        } catch (err: any) {
            console.error(err);
            toast.error('추천 결과를 가져오는데 실패했습니다.');
        } finally {
            setLoading(false);
        }
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

                            <div className="space-y-2">
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
                    <div className="flex items-center justify-between">
                        <div className="space-y-1">
                            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                                <Sparkles className="w-6 h-6 text-yellow-500" />
                                분석 결과
                            </h2>
                            <p className="text-slate-400">
                                {results.major} 전공과 {results.interest ? `"${results.interest}"` : "시스템 데이터"}를 결합한 추천입니다.
                            </p>
                        </div>
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
                                        <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                                            정합성 {Math.round(res.hybrid_score * 100)}%
                                        </Badge>
                                    </div>
                                    <CardTitle className="text-xl font-bold text-white mt-4 group-hover:text-blue-400 transition-colors line-clamp-2">
                                        {res.qual_name}
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex items-start gap-2 bg-slate-950/50 p-3 rounded-xl border border-slate-800">
                                        <Info className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
                                        <p className="text-sm text-slate-400 leading-relaxed italic line-clamp-3">
                                            {res.reason || "귀하의 전공 역량과 관심사를 고려하여 추천된 자격증입니다."}
                                        </p>
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
                </div>
            )}

            {/* Help Section */}
            {!results && !loading && (
                <div className="grid md:grid-cols-2 gap-8 items-center pt-8 border-t border-slate-800/50">
                    <div className="space-y-6">
                        <h3 className="text-2xl font-bold text-white">추천 원리</h3>
                        <ul className="space-y-6">
                            <li className="flex gap-4 items-start">
                                <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 shrink-0 font-bold border border-blue-500/20">1</div>
                                <div>
                                    <h4 className="font-bold text-slate-200">전공 분야 분석</h4>
                                    <p className="text-sm text-slate-500 mt-1">대학 전공별 이수 과목과 자격증의 핵심 기술을 매칭합니다.</p>
                                </div>
                            </li>
                            <li className="flex gap-4 items-start">
                                <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 shrink-0 font-bold border border-purple-500/20">2</div>
                                <div>
                                    <h4 className="font-bold text-slate-200">인공지능 시멘틱 검색</h4>
                                    <p className="text-sm text-slate-500 mt-1">사용자가 적은 관심사 키워드를 AI가 문맥적으로 파악하여 가장 가까운 자격증을 찾습니다.</p>
                                </div>
                            </li>
                            <li className="flex gap-4 items-start">
                                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 shrink-0 font-bold border border-indigo-500/20">3</div>
                                <div>
                                    <h4 className="font-bold text-slate-200">맞춤형 우선순위</h4>
                                    <p className="text-sm text-slate-500 mt-1">전공 연관성과 주관적 관심도를 조합하여 가장 유리한 자격증 순서대로 보여줍니다.</p>
                                </div>
                            </li>
                        </ul>
                    </div>
                    <div>
                        <div className="bg-slate-900/60 border border-slate-800 p-8 rounded-3xl relative overflow-hidden group">
                            <div className="absolute inset-0 bg-blue-500/5 blur-3xl rounded-full group-hover:bg-blue-500/10 transition-colors" />

                            <div className="relative space-y-6">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center border border-slate-700">
                                        <Search className="w-6 h-6 text-blue-400" />
                                    </div>
                                    <div className="space-y-2 flex-1">
                                        <div className="h-3 w-3/4 bg-slate-800 rounded-full animate-pulse" />
                                        <div className="h-3 w-1/2 bg-slate-800 rounded-full animate-pulse delay-75" />
                                    </div>
                                </div>

                                <div className="flex justify-end pr-4">
                                    <div className="bg-indigo-600/20 text-indigo-400 text-[10px] font-bold px-3 py-1 rounded-full border border-indigo-600/30">
                                        Deep Analysis...
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 pt-4 border-t border-slate-800">
                                    <div className="w-10 h-10 rounded-full bg-blue-900/30 border border-blue-500/30 flex items-center justify-center text-blue-400 animate-bounce">
                                        <BrainCircuit className="w-5 h-5" />
                                    </div>
                                    <div className="flex-1 space-y-1.5">
                                        <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                                            <div className="h-full w-2/3 bg-blue-500 animate-ping opacity-20" />
                                        </div>
                                        <div className="h-2 w-4/5 bg-slate-800 rounded-full" />
                                    </div>
                                </div>

                                <div className="flex gap-2 pt-2">
                                    <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20" />
                                    <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20" />
                                    <div className="w-8 h-8 rounded-lg bg-orange-500/10 border border-orange-500/20" />
                                    <div className="w-12 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] text-slate-500">+1.2k</div>
                                </div>

                                <p className="text-slate-400 text-sm italic leading-relaxed pt-2">
                                    &quot;AI가 수천 개의 자격증 문서와 직무 명세서를 <br />
                                    실시간으로 분석하여 최적의 결과를 도출합니다.&quot;
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
