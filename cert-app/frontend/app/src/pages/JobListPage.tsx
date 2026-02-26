import { useState, useEffect } from 'react';
import {
    Search,
    Briefcase,
    TrendingUp,
    Sparkles,
    BookOpen,
    Star,
    ChevronRight,
    DollarSign,
    Zap
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { getJobs } from '@/lib/api';
import type { Job, JobListResponse } from '@/types';
import { useRouter } from '@/lib/router';
import {
    ResponsiveContainer,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    Radar,
    Tooltip as RechartsTooltip,
    PolarRadiusAxis
} from 'recharts';

export function JobListPage() {
    const router = useRouter();
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalJobs, setTotalJobs] = useState(0);

    const PAGE_SIZE = 20;

    const url = new URL(window.location.href);
    const initialQ = url.searchParams.get('q') || '';
    const initialPage = parseInt(url.searchParams.get('page') || '1', 10) || 1;
    const [searchQuery, setSearchQuery] = useState(initialQ);

    useEffect(() => {
        // URL 초기값을 한 번만 반영
        setPage(initialPage);
    }, []);

    useEffect(() => {
        const fetchJobs = async () => {
            setLoading(true);
            try {
                const res: JobListResponse = await getJobs({
                    q: searchQuery || undefined,
                    page,
                    page_size: PAGE_SIZE,
                });
                const items = res.items ?? [];
                setJobs(items);
                setPage(res.page);
                // 백엔드 total_pages를 쓰되, 한 페이지가 꽉 찼으면 최소 2페이지는 있다고 보고(다음 버튼용)
                const fromBackend = res.total_pages ?? Math.max(1, Math.ceil((res.total || 0) / PAGE_SIZE));
                const inferred = items.length >= PAGE_SIZE ? Math.max(fromBackend, res.page + 1) : fromBackend;
                setTotalPages(inferred);
                setTotalJobs(res.total ?? 0);
            } catch (error) {
                console.error('Failed to fetch jobs:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchJobs();
    }, [searchQuery, page]);

    const goToPage = (nextPage: number) => {
        // totalPages 계산이 보수적으로 잡혀도 번호 클릭은 항상 동작하도록
        if (nextPage < 1 || nextPage === page) return;
        setPage(nextPage);
    };

    const handlePrevPage = () => {
        goToPage(page - 1);
    };

    const handleNextPage = () => {
        goToPage(page + 1);
    };

    const handlePageClick = (p: number) => {
        goToPage(p);
    };
    // searchQuery 또는 page가 바뀔 때마다 URL을 replaceState로 동기화 → 뒤로가기 시 검색어/페이지 복원
    useEffect(() => {
        const urlParams = new URLSearchParams();
        if (searchQuery) urlParams.set('q', searchQuery);
        if (page > 1) urlParams.set('page', String(page));
        const newUrl = `/jobs${urlParams.toString() ? `?${urlParams.toString()}` : ''}`;
        if (newUrl !== window.location.pathname + window.location.search) {
            window.history.replaceState(null, '', newUrl);
        }
    }, [searchQuery, page]);

    const [inputValue, setInputValue] = useState(initialQ);
    const [showSuggestions, setShowSuggestions] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => {
            if (inputValue !== searchQuery) {
                setSearchQuery(inputValue);
                setPage(1);
            }
        }, 400);
        return () => clearTimeout(timer);
    }, [inputValue]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setSearchQuery(inputValue);
        setPage(1);
        setShowSuggestions(false);
    };

    const handleSuggestionClick = (name: string) => {
        setInputValue(name);
        setSearchQuery(name);
        setPage(1);
        setShowSuggestions(false);
    };

    const jobList: Job[] = Array.isArray(jobs) ? jobs : [];

    return (
        <div className="space-y-12 pb-20">
            {/* Hero Banner */}
            <div className="relative rounded-[2.5rem] bg-slate-900 border border-slate-800 p-10 md:p-16">
                {/* Background Effects Container - Clips only the decorative elements */}
                <div className="absolute inset-0 rounded-[2.5rem] overflow-hidden pointer-events-none">
                    <div className="absolute top-0 right-0 w-[60%] h-full bg-gradient-to-l from-indigo-600/10 via-blue-600/5 to-transparent" />
                    <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-blue-500/10 rounded-full blur-[100px]" />
                </div>

                <div className="relative z-10 max-w-2xl space-y-8">
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-600/10 border border-blue-500/20 text-blue-400 text-sm font-bold tracking-wide">
                        <Star className="w-4 h-4 fill-blue-400" />
                        <span>CAREER ANALYTICS ENGINE</span>
                    </div>

                    <div className="space-y-4">
                        <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight leading-[1.2]">
                            커리어를 넘어서,<br />
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">당신의 가치</span>를 발견하세요
                        </h1>
                        <p className="text-slate-400 text-lg leading-relaxed max-w-lg">
                            관심 직무의 전망, 초임 연봉, 그리고 핵심 직무 역량 데이터를
                            정밀 분석 차트와 함께 제공합니다.
                        </p>
                    </div>

                    <form onSubmit={handleSearch} className="flex gap-3 max-w-lg pt-4 relative">
                        <div className="relative flex-1 group z-20">
                            <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-20 group-focus-within:opacity-40 transition" />
                            <div className="relative">
                                <label htmlFor="job-search-input" className="sr-only">직무 검색</label>
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                <Input
                                    id="job-search-input"
                                    name="q"
                                    placeholder="어떤 직무를 고민하고 계신가요?"
                                    value={inputValue}
                                    onFocus={() => setShowSuggestions(true)}
                                    onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                                    onChange={(e) => {
                                        setInputValue(e.target.value);
                                        setShowSuggestions(true);
                                    }}
                                    className="pl-12 bg-black/60 border-slate-800 text-white h-14 rounded-2xl focus:ring-blue-500 text-lg"
                                />
                            </div>
                        </div>
                        <Button type="submit" className="h-14 px-8 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold text-lg shadow-xl shadow-blue-900/30 transition-transform active:scale-95">
                            검색
                        </Button>

                        {/* Suggestions Dropdown */}
                        {showSuggestions && inputValue.length >= 1 && jobList.length > 0 && (
                            <div className="absolute top-full left-0 right-0 mt-3 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl z-50 max-h-60 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700 animate-in fade-in slide-in-from-top-2 duration-200">
                                <div className="p-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-950/20 border-b border-slate-800">
                                    추천 직무 ({jobList.length})
                                </div>
                                {jobList.slice(0, 10).map((job) => (
                                    <div
                                        key={job.job_id}
                                        className="px-5 py-3 hover:bg-slate-800 cursor-pointer text-slate-200 border-b border-slate-800/50 last:border-0 flex items-center justify-between group/item transition-colors"
                                        onMouseDown={() => handleSuggestionClick(job.job_name)}
                                    >
                                        <span className="text-sm font-medium group-hover/item:text-blue-400">{job.job_name}</span>
                                        <TrendingUp className="w-3 h-3 text-slate-600 opacity-0 group-hover/item:opacity-100 transition-all" />
                                    </div>
                                ))}
                            </div>
                        )}
                    </form>
                </div>
            </div>

            {/* Results Grid */}
            <div className="space-y-8">
                <div className="flex items-center justify-between border-b border-slate-800 pb-6">
                    <div className="space-y-1">
                        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                            <Briefcase className="w-6 h-6 text-blue-500" />
                            {searchQuery ? `'${searchQuery}' 분석 결과` : '최신 직무 트렌드'}
                        </h2>
                        <p className="text-slate-500 text-sm">{totalJobs}개의 포지션이 분석됨</p>
                    </div>

                    <div className="flex items-center gap-4 text-xs font-bold text-slate-500 uppercase tracking-widest">
                        <span>Analysis Status: Live</span>
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    </div>
                </div>

                {loading ? (
                    <div className="grid gap-8">
                        {[1, 2, 3].map(i => <Skeleton key={i} className="h-96 rounded-[2rem] bg-slate-900" />)}
                    </div>
                ) : jobList.length === 0 ? (
                    <Card className="bg-slate-900/40 border-slate-800 border-dashed py-32 text-center rounded-[2rem]">
                        <CardContent className="space-y-6">
                            <div className="p-8 bg-slate-900 rounded-full w-fit mx-auto">
                                <Search className="w-16 h-16 text-slate-700" />
                            </div>
                            <div className="space-y-2">
                                <h3 className="text-2xl font-bold text-white">검색된 정보가 없습니다</h3>
                                <p className="text-slate-500">다른 키워드로 직무를 찾아보세요.</p>
                            </div>
                        </CardContent>
                    </Card>
                ) : (
                    <div className="grid gap-10">
                        {jobList.map((job) => {
                            const radarData = [
                                { subject: '보상', A: job.reward || 0, fullMark: 100 },
                                { subject: '안정성', A: job.stability || 0, fullMark: 100 },
                                { subject: '발전', A: job.development || 0, fullMark: 100 },
                                { subject: '환경', A: job.condition || 0, fullMark: 100 },
                                { subject: '전문성', A: job.professionalism || 0, fullMark: 100 },
                                { subject: '평등', A: job.equality || 0, fullMark: 100 },
                            ];

                            return (
                                <Card
                                    key={job.job_id}
                                    onClick={() => router.navigate(`/jobs/${job.job_id}`)}
                                    className="bg-slate-900/50 border-slate-800 hover:border-blue-500/50 hover:bg-slate-900/80 transition-all duration-500 shadow-2xl group overflow-hidden rounded-[2rem] cursor-pointer"
                                >
                                    <div className="absolute top-0 left-0 w-2 h-full bg-blue-600 opacity-50 group-hover:opacity-100 transition-opacity" />
                                    <CardContent className="p-0">
                                        <div className="grid lg:grid-cols-12">
                                            {/* Left Profile Section */}
                                            <div className="lg:col-span-4 p-12 bg-slate-950/40 border-r border-slate-800/50 flex flex-col items-center justify-between space-y-8">
                                                <div className="w-full space-y-6">
                                                    <div className="flex justify-between items-start">
                                                        <div className="p-4 rounded-2xl bg-blue-600/10 border border-blue-500/20">
                                                            <Briefcase className="w-8 h-8 text-blue-400" />
                                                        </div>
                                                        <div className="flex flex-col items-end max-w-[200px]">
                                                            <span className="text-[10px] font-bold text-slate-500 uppercase mb-1 tracking-widest">Similar Occupations</span>
                                                            <div className="flex flex-wrap gap-1 justify-end">
                                                                {(job.similar_jobs || "관련 직무 분석중").split(',').slice(0, 3).map((sj, idx) => (
                                                                    <Badge key={idx} variant="secondary" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px] whitespace-nowrap">
                                                                        {sj.trim()}
                                                                    </Badge>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    </div>

                                                    <div className="space-y-4">
                                                        <h3 className="text-3xl font-black text-white group-hover:text-blue-400 transition-colors">
                                                            {job.job_name}
                                                        </h3>
                                                        <div className="flex items-center gap-2">
                                                            <Badge className="bg-blue-600/10 text-blue-400 border-blue-500/20">분석 완료</Badge>
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Skill Radar */}
                                                <div className="w-full aspect-square relative py-4">
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                                                            <PolarGrid stroke="#1e293b" strokeDasharray="3 3" />
                                                            <PolarAngleAxis
                                                                dataKey="subject"
                                                                tick={{ fill: '#64748b', fontSize: 10, fontWeight: 700 }}
                                                            />
                                                            <Radar
                                                                name="평가 점수"
                                                                dataKey="A"
                                                                stroke="#3b82f6"
                                                                fill="#3b82f6"
                                                                fillOpacity={0.6}
                                                            />
                                                            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                                                            <RechartsTooltip
                                                                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                                                                itemStyle={{ color: '#3b82f6' }}
                                                            />
                                                        </RadarChart>
                                                    </ResponsiveContainer>
                                                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-5">
                                                        <Sparkles className="w-32 h-32 text-blue-500" />
                                                    </div>
                                                </div>

                                                <p className="text-center text-[10px] text-slate-600 font-bold uppercase tracking-[0.2em] border-t border-slate-900 pt-4 w-full">
                                                    Fixed Scale Analytics (0-100)
                                                </p>
                                            </div>

                                            {/* Right Info Section */}
                                            <div className="lg:col-span-8 p-12 space-y-10">
                                                <div className="grid md:grid-cols-2 gap-10">
                                                    <div className="space-y-4">
                                                        <div className="flex items-center gap-3 text-emerald-400 font-black text-xs uppercase tracking-[0.2em]">
                                                            <TrendingUp className="w-4 h-4" />
                                                            직업 전망 분석
                                                        </div>
                                                        <div className="text-emerald-300 text-sm leading-snug bg-emerald-500/5 p-6 rounded-2xl border border-emerald-500/10 min-h-[140px] whitespace-pre-line">
                                                            {job.outlook_summary || job.outlook || '전망 정보 제공 대기중'}
                                                        </div>
                                                    </div>

                                                    <div className="space-y-4">
                                                        <div className="flex items-center gap-3 text-amber-500 font-black text-xs uppercase tracking-[0.2em]">
                                                            <DollarSign className="w-4 h-4" />
                                                            임금 및 만족도 레포트
                                                        </div>
                                                        <div className="text-amber-300 text-sm leading-relaxed bg-amber-500/5 p-6 rounded-2xl border border-amber-500/10 min-h-[140px] whitespace-pre-line">
                                                            {job.entry_salary && (
                                                                <div className="mb-4 pb-4 border-b border-amber-500/10">
                                                                    <span className="text-[10px] font-bold text-amber-500/60 uppercase tracking-widest block mb-1">상세 초임 정보</span>
                                                                    <div className="text-lg font-black text-amber-400">{job.entry_salary}</div>
                                                                </div>
                                                            )}
                                                            {job.salary_info}
                                                        </div>
                                                    </div>
                                                </div>

                                                <div className="space-y-4 pt-6 border-t border-slate-800">
                                                    <div className="flex items-center gap-3 text-indigo-400 font-black text-xs uppercase tracking-[0.2em]">
                                                        <Zap className="w-4 h-4" />
                                                        취업 방법 및 핵심 경로
                                                    </div>
                                                    <div className="text-indigo-300 text-sm leading-snug bg-indigo-500/5 p-6 rounded-2xl border border-indigo-500/10 whitespace-pre-line">
                                                        {(job.employment_path || '취업 경로 정보 업데이트 중').replace(/ - /g, '\n- ').replace(/^- /g, '- ')}
                                                    </div>
                                                </div>

                                                <div className="space-y-6 pt-6 border-t border-slate-800">
                                                    <div className="flex items-center gap-3 text-blue-400 font-black text-xs uppercase tracking-[0.2em]">
                                                        <BookOpen className="w-4 h-4" />
                                                        핵심 적성 및 요구 역량
                                                    </div>
                                                    <div className="relative">
                                                        <div className="absolute -left-6 top-1/2 -translate-y-1/2 w-1 h-12 bg-slate-800 rounded-full" />
                                                        <p className="text-slate-400 text-sm leading-snug pl-2 whitespace-pre-line">
                                                            {(job.aptitude || '상세 업무 정보가 업데이트 예정입니다.').replace(/ - /g, '\n- ').replace(/^- /g, '- ')}
                                                        </p>
                                                    </div>
                                                </div>

                                                <div className="flex justify-end pt-4">
                                                    <Button variant="ghost" className="text-slate-500 hover:text-blue-400 hover:bg-blue-400/5 transition-all text-xs font-bold group">
                                                        상세 분석 리포트 보기 <ChevronRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
                                                    </Button>
                                                </div>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Pagination Controls — 결과가 있으면 항상 표시, 5개 슬롯(1 2 3 4 5), 초과 번호는 비활성 */}
            {!loading && jobList.length > 0 && (
                <div className="flex justify-center items-center gap-4 pt-10">
                    <Button
                        variant="outline"
                        disabled={page === 1}
                        onClick={handlePrevPage}
                        className="border-slate-800 text-white disabled:opacity-30 rounded-xl"
                    >
                        이전
                    </Button>
                    <div className="flex items-center gap-2">
                        {Array.from({ length: 5 }, (_, i) => {
                            const startPage = Math.max(1, Math.min(page - 2, Math.max(1, totalPages - 4)));
                            const p = startPage + i;
                            return (
                                <Button
                                    key={p}
                                    variant={page === p ? "secondary" : "ghost"}
                                    onClick={() => handlePageClick(p)}
                                    className="h-10 w-10 p-0 rounded-xl"
                                >
                                    {p}
                                </Button>
                            );
                        })}
                    </div>
                    <Button
                        variant="outline"
                        disabled={page === totalPages}
                        onClick={handleNextPage}
                        className="border-slate-800 text-white disabled:opacity-30 rounded-xl"
                    >
                        다음
                    </Button>
                </div>
            )}

            {/* Guide Section */}
            <div className="bg-slate-900 border border-slate-800 rounded-[2rem] p-12 text-center space-y-8">
                <div className="max-w-xl mx-auto space-y-4">
                    <h3 className="text-2xl font-bold text-white">데이터 출처 및 기준</h3>
                    <p className="text-slate-400 text-sm leading-relaxed">
                        본 직무 역량 차트와 전망 데이터는 워크넷, 커리어넷 및 국가기술자격 통계를 기반으로
                        알고리즘 분석을 통해 도출되었습니다. 성향 점수(Radar Chart)는 직무의 상대적 특성을
                        나타내며 개인의 역량과는 다를 수 있습니다.
                    </p>
                </div>
                <div className="flex flex-wrap justify-center gap-6">
                    <div className="flex items-center gap-2 text-slate-500 text-xs font-bold">
                        <div className="w-2 h-2 rounded-full bg-blue-500" />
                        워크넷 연계
                    </div>
                    <div className="flex items-center gap-2 text-slate-500 text-xs font-bold">
                        <div className="w-2 h-2 rounded-full bg-indigo-500" />
                        커리어넷 반영
                    </div>
                    <div className="flex items-center gap-2 text-slate-500 text-xs font-bold">
                        <div className="w-2 h-2 rounded-full bg-purple-500" />
                        산업인력공단 데이터
                    </div>
                </div>
            </div>
        </div>
    );
}
