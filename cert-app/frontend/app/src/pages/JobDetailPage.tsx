
import { useState, useEffect } from 'react';
import {
    Briefcase,
    TrendingUp,
    DollarSign,
    Zap,
    BookOpen,
    Award,
    ChevronLeft,
    ExternalLink,
    LineChart,
    PieChart,
    Users,
    Share2
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getJobDetail } from '@/lib/api';
import type { Job } from '@/types';
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

interface JobDetailPageProps {
    id: string;
}

export function JobDetailPage({ id }: JobDetailPageProps) {
    const router = useRouter();
    const [job, setJob] = useState<Job | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchJob = async () => {
            setLoading(true);
            try {
                const data = await getJobDetail(parseInt(id));
                setJob(data);
            } catch (error) {
                console.error('Failed to fetch job detail:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchJob();
    }, [id]);

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8 space-y-8 animate-pulse">
                <div className="h-10 w-32 bg-slate-800 rounded-lg"></div>
                <div className="h-64 bg-slate-900 rounded-[2.5rem]"></div>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        <div className="h-48 bg-slate-900 rounded-2xl"></div>
                        <div className="h-48 bg-slate-900 rounded-2xl"></div>
                    </div>
                    <div className="h-96 bg-slate-900 rounded-2xl"></div>
                </div>
            </div>
        );
    }

    if (!job) {
        return (
            <div className="text-center py-20 text-white">
                <h2 className="text-2xl font-bold">직무 정보를 찾을 수 없습니다.</h2>
                <Button onClick={() => router.navigate('/jobs')} variant="ghost" className="mt-4">
                    목록으로 돌아가기
                </Button>
            </div>
        );
    }

    const radarData = [
        { subject: '보상', A: job.reward || 0, fullMark: 100 },
        { subject: '안정성', A: job.stability || 0, fullMark: 100 },
        { subject: '발전', A: job.development || 0, fullMark: 100 },
        { subject: '환경', A: job.condition || 0, fullMark: 100 },
        { subject: '전문성', A: job.professionalism || 0, fullMark: 100 },
        { subject: '평등', A: job.equality || 0, fullMark: 100 },
    ];

    const handleShare = async () => {
        const shareData = {
            title: `CertFinder - ${job.job_name} 분석 리포트`,
            text: `${job.job_name}의 연봉, 전망, 자격증 정보를 확인하세요!`,
            url: window.location.href,
        };

        try {
            if (navigator.share) {
                await navigator.share(shareData);
                toast.success('리포트가 공유되었습니다.');
            } else {
                await navigator.clipboard.writeText(window.location.href);
                toast.success('링크가 클립보드에 복사되었습니다.');
            }
        } catch (err) {
            console.error('Share failed:', err);
        }
    };

    return (
        <div className="container mx-auto px-4 py-8 space-y-8 max-w-7xl animate-in fade-in duration-500">
            {/* Header / Nav */}
            <div className="flex items-center gap-4">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => router.navigate('/jobs')}
                    className="text-slate-400 hover:text-white"
                >
                    <ChevronLeft className="w-4 h-4 mr-1" /> 목록으로
                </Button>
                <div className="h-4 w-px bg-slate-800"></div>
                <span className="text-sm font-bold text-slate-500 uppercase tracking-widest">Job Analytics Report</span>
            </div>

            {/* Hero Card */}
            <div className="relative rounded-[2.5rem] bg-slate-900 border border-slate-800 overflow-hidden">
                <div className="absolute top-0 right-0 w-[50%] h-full bg-gradient-to-l from-blue-600/10 via-indigo-600/5 to-transparent pointer-events-none" />
                <div className="p-8 md:p-16 flex flex-col md:flex-row justify-between items-start md:items-center gap-8 relative z-10">
                    <div className="space-y-6 flex-1">
                        <div className="p-4 rounded-2xl bg-blue-600/10 border border-blue-500/20 w-fit">
                            <Briefcase className="w-10 h-10 text-blue-400" />
                        </div>
                        <div className="space-y-2">
                            <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight">
                                {job.job_name}
                            </h1>
                        </div>
                    </div>

                    <div className="flex items-center gap-12 bg-black/20 p-8 rounded-3xl border border-white/5 backdrop-blur-sm">
                        <div className="text-center space-y-2">
                            <div className="text-xs font-bold text-slate-500 uppercase tracking-widest">Average Starting</div>
                            <div className="text-2xl font-black text-white">{job.entry_salary || '협의'}</div>
                        </div>
                        <div className="w-px h-12 bg-slate-800"></div>
                        <div className="text-center space-y-2">
                            <div className="text-xs font-bold text-slate-500 uppercase tracking-widest">Stability Score</div>
                            <div className="text-2xl font-black text-blue-400">{job.stability || 0}/100</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Left Side: Analysis Details */}
                <div className="lg:col-span-8 space-y-8">
                    {/* Perspective & Outlook */}
                    <div className="grid md:grid-cols-2 gap-8">
                        <Card className="bg-slate-900/50 border-slate-800 hover:border-slate-700 transition-colors">
                            <CardContent className="p-8 space-y-6">
                                <div className="flex items-center gap-3 text-emerald-400 font-bold text-sm tracking-widest uppercase">
                                    <TrendingUp className="w-5 h-5" /> 직업 전망
                                </div>
                                <p className="text-slate-300 text-sm leading-snug whitespace-pre-line">
                                    {job.outlook_summary || '전망 정보 분석 중입니다.'}
                                </p>
                            </CardContent>
                        </Card>

                        <Card className="bg-slate-900/50 border-slate-800 hover:border-slate-700 transition-colors">
                            <CardContent className="p-8">
                                <div className="flex items-center gap-3 text-amber-500 font-bold text-sm tracking-widest uppercase mb-4">
                                    <DollarSign className="w-5 h-5" /> 임금 정보
                                </div>
                                <div className="flex flex-col sm:flex-row gap-6 items-start justify-between sm:gap-8">
                                    <div className="flex-1 min-w-0 w-full sm:min-w-0">
                                        <p className="text-slate-300 text-sm leading-relaxed break-words">
                                            {job.salary_info ?? `${job.job_name}의 임금수준은 ${job.entry_salary ?? '협의'} 등으로 조회된다. (자료: 워크넷 직업정보)`}
                                        </p>
                                    </div>
                                    <div className="flex flex-col items-center sm:items-end shrink-0 space-y-1 sm:pl-4">
                                        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Stability Score</div>
                                        <div className="text-2xl font-black text-blue-400">{job.stability ?? 0}/100</div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* How to Get Employed */}
                    <Card className="bg-slate-900/50 border-slate-800 overflow-hidden group">
                        <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500 opacity-20 group-hover:opacity-100 transition-opacity" />
                        <CardContent className="p-8 space-y-6">
                            <div className="flex items-center gap-3 text-indigo-400 font-bold text-sm tracking-widest uppercase">
                                <Zap className="w-5 h-5" /> 취업 방법 및 경로
                            </div>
                            <div className="bg-black/20 p-6 rounded-2xl border border-white/5">
                                <p className="text-slate-300 text-sm leading-snug whitespace-pre-line">
                                    {job.employment_path?.replace(/ - /g, '\n- ').replace(/^- /g, '- ') || '취업 정보가 곧 업데이트됩니다.'}
                                </p>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Core Competencies */}
                    <Card className="bg-slate-900/50 border-slate-800 overflow-hidden group">
                        <div className="absolute top-0 left-0 w-1 h-full bg-blue-500 opacity-20 group-hover:opacity-100 transition-opacity" />
                        <CardContent className="p-8 space-y-6">
                            <div className="flex items-center gap-3 text-blue-400 font-bold text-sm tracking-widest uppercase">
                                <BookOpen className="w-5 h-5" /> 핵심 적성 및 역량
                            </div>
                            <div className="bg-black/20 p-6 rounded-2xl border border-white/5">
                                <p className="text-slate-300 text-sm leading-snug whitespace-pre-line text-justify">
                                    {job.aptitude?.replace(/ - /g, '\n- ').replace(/^- /g, '- ') || '상세 역량 정보 분석 중입니다.'}
                                </p>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Related Qualifications - NEW SECTION */}
                    <section className="space-y-6">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                            <h3 className="text-xl font-bold text-white flex items-center gap-3">
                                <Award className="w-6 h-6 text-yellow-500" />
                                관련 핵심 자격증
                            </h3>
                            <Badge variant="outline" className="border-slate-800 text-slate-500 font-medium">
                                {job.qualifications?.length || 0} Recommended
                            </Badge>
                        </div>

                        {job.qualifications && job.qualifications.length > 0 ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                {job.qualifications.map((qual) => (
                                    <Card
                                        key={qual.qual_id}
                                        onClick={() => router.navigate(`/certs/${qual.qual_id}`)}
                                        className="bg-slate-900 border-slate-800 hover:border-blue-500/50 hover:bg-slate-800/50 cursor-pointer transition-all group"
                                    >
                                        <CardContent className="p-6 flex items-center justify-between">
                                            <div className="space-y-1">
                                                <div className="text-white font-bold group-hover:text-blue-400 transition-colors">
                                                    {qual.qual_name}
                                                </div>
                                                <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                                                    {qual.qual_type} • {qual.main_field}
                                                </div>
                                            </div>
                                            <ExternalLink className="w-4 h-4 text-slate-600 group-hover:text-blue-400 transition-colors" />
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        ) : (
                            <div className="bg-slate-900/40 border border-slate-800 border-dashed rounded-2xl p-12 text-center text-slate-500 italic">
                                관련 자격증 정보를 분석하고 있습니다.
                            </div>
                        )}
                    </section>
                </div>

                {/* Right Side: Radar Chart & Metadata */}
                <div className="lg:col-span-4 space-y-8">
                    <Card className="bg-slate-900/50 border-slate-800 sticky top-24 overflow-hidden">
                        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 via-indigo-600 to-violet-600" />
                        <CardContent className="p-8 space-y-8">
                            <div className="space-y-1 text-center">
                                <h3 className="text-xl font-bold text-white uppercase tracking-tight">직무 특성 레이더</h3>
                                <p className="text-[10px] text-slate-500 font-bold tracking-[0.2em]">CHARACTERISTIC SCALE 0-100</p>
                            </div>

                            <div className="aspect-square relative">
                                <ResponsiveContainer width="100%" height="100%">
                                    <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                                        <PolarGrid stroke="#1e293b" strokeDasharray="3 3" />
                                        <PolarAngleAxis
                                            dataKey="subject"
                                            tick={{ fill: '#64748b', fontSize: 10, fontWeight: 700 }}
                                        />
                                        <Radar
                                            name="점수"
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
                            </div>

                            {/* Stat Breakdown */}
                            <div className="space-y-4 pt-4 border-t border-slate-800">
                                <div className="flex justify-between items-center group">
                                    <div className="flex items-center gap-2 text-slate-400 text-xs font-bold">
                                        <LineChart className="w-4 h-4 text-blue-500" /> 발전 가능성
                                    </div>
                                    <div className="text-white font-black">{job.development}%</div>
                                </div>
                                <div className="flex justify-between items-center group">
                                    <div className="flex items-center gap-2 text-slate-400 text-xs font-bold">
                                        <PieChart className="w-4 h-4 text-emerald-500" /> 전문성 지수
                                    </div>
                                    <div className="text-white font-black">{job.professionalism}%</div>
                                </div>
                                <div className="flex justify-between items-center group">
                                    <div className="flex items-center gap-2 text-slate-400 text-xs font-bold">
                                        <Users className="w-4 h-4 text-indigo-500" /> 고용 평등성
                                    </div>
                                    <div className="text-white font-black">{job.equality}%</div>
                                </div>
                            </div>

                            <Button
                                onClick={handleShare}
                                className="w-full h-14 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl mt-6 flex items-center justify-center gap-2"
                            >
                                <Share2 className="w-5 h-5" />
                                리포트 공유하기
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
