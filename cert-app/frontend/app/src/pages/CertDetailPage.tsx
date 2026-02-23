import { useState, useMemo, useEffect } from 'react';
import {
  Award,
  TrendingUp,
  Users,
  Calendar,
  ChevronLeft,
  Globe,
  ShieldCheck,
  Zap,
  Briefcase,
  BookOpen,
  Info,
  Target,
  Share2,
  Bookmark,
  ChevronRight,
  DollarSign,
  CheckCircle
} from 'lucide-react';
import { toast } from 'sonner';
import {
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  XAxis,
  YAxis,
  PolarRadiusAxis
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useCertDetail, useCertStats } from '@/hooks/useCerts';
import { useRouter } from '@/lib/router';
import { Skeleton } from '@/components/ui/skeleton';
import { useAuth } from '@/hooks/useAuth';
import { checkFavorite, addFavorite, removeFavorite } from '@/lib/api';

export function CertDetailPage({ id }: { id: string }) {
  const router = useRouter();
  const certId = parseInt(id, 10) || 0;
  const { user, token } = useAuth();
  const { data: cert, loading: certLoading } = useCertDetail(certId, token);
  const { data: statsRes, loading: statsLoading } = useCertStats(certId);
  const [activeTab, setActiveTab] = useState('stats');
  const [isBookmarked, setIsBookmarked] = useState(false);

  // Sync with API or LocalStorage on mount
  useEffect(() => {
    async function checkBookmark() {
      if (user && token) {
        try {
          const res = await checkFavorite(certId, token);
          setIsBookmarked(res.is_favorite);
        } catch (err) {
          console.error('Failed to check bookmark from API:', err);
        }
      } else if (!user) {
        const saved = localStorage.getItem('bookmarks');
        if (saved) {
          try {
            const bookmarks = JSON.parse(saved) as number[];
            setIsBookmarked(bookmarks.includes(certId));
          } catch {
            setIsBookmarked(false);
          }
        }
      }
    }
    checkBookmark();
  }, [user, token, certId]);

  const toggleBookmark = async () => {
    const nextState = !isBookmarked;
    setIsBookmarked(nextState);

    if (user && token) {
      try {
        if (nextState) {
          await addFavorite(certId, token);
        } else {
          await removeFavorite(certId, token);
        }

        toast.success(
          nextState ? "관심 자격증으로 등록되었습니다." : "관심 자격증에서 삭제되었습니다.",
          { description: cert?.qual_name }
        );
      } catch (e: any) {
        console.error('Database Sync Error:', e);
        setIsBookmarked(!nextState); // Rollback
        toast.error(
          nextState ? "관심 자격증 등록 실패" : "관심 자격증 삭제 실패",
          { description: e.message || "다시 시도해주세요." }
        );
      }
    } else {
      // Guest mode or no token
      try {
        const saved = localStorage.getItem('bookmarks');
        let bookmarks = saved ? JSON.parse(saved) as number[] : [];
        if (nextState) {
          if (!bookmarks.includes(certId)) bookmarks.push(certId);
        } else {
          bookmarks = bookmarks.filter(id => id !== certId);
        }
        localStorage.setItem('bookmarks', JSON.stringify(bookmarks));

        toast.success(
          nextState ? "관심 자격증으로 등록되었습니다. (비회원)" : "관심 자격증에서 삭제되었습니다. (비회원)",
          { description: cert?.qual_name }
        );
      } catch (e) {
        console.error('LocalStorage Error:', e);
      }
    }
  };

  const stats = statsRes?.items || [];

  // Multi-series Chart Data
  const [visibleStages, setVisibleStages] = useState<string[]>(['필기', '실기', '면접']);

  const getRoundName = (roundNum: number) => {
    if (!cert) return `${roundNum}회차`;
    const w = cert.written_cnt || 0;
    const p = cert.practical_cnt || 0;
    const i = cert.interview_cnt || 0;
    if (w === 0 && p === 0 && i === 0) {
      if (roundNum === 1) return "필기";
      if (roundNum === 2) return "실기";
      if (roundNum === 3) return "면접";
      return "기타";
    }
    if (roundNum <= w) return "필기";
    if (roundNum <= w + p) return "실기";
    if (roundNum <= w + p + i) return "면접";
    return "기타";
  };

  const chartData = useMemo(() => {
    if (!stats || stats.length === 0) return [];

    // Group stats by year for multi-line comparison
    const yearMap = new Map<number, any>();

    // Sort chronologically first
    const sortedStats = [...stats].sort((a, b) => (a.year * 10 + a.exam_round) - (b.year * 10 + b.exam_round));

    sortedStats.forEach(s => {
      if (!yearMap.has(s.year)) {
        yearMap.set(s.year, { year: s.year, label: `${s.year % 100}년` });
      }
      const entry = yearMap.get(s.year);
      const stage = getRoundName(s.exam_round);

      if (stage === '필기') entry.written = s.pass_rate;
      else if (stage === '실기') entry.practical = s.pass_rate;
      else if (stage === '면접') entry.interview = s.pass_rate;
    });

    return Array.from(yearMap.values()).sort((a, b) => a.year - b.year);
  }, [stats, cert]);

  const hasStage = (stage: string) => {
    if (!cert) return true;
    if (stage === '필기') return (cert.written_cnt || 0) > 0 || stats.some(s => s.exam_round === 1);
    if (stage === '실기') return (cert.practical_cnt || 0) > 0 || Array.from(new Set(stats.map(s => getRoundName(s.exam_round)))).includes('실기');
    if (stage === '면접') return (cert.interview_cnt || 0) > 0 || Array.from(new Set(stats.map(s => getRoundName(s.exam_round)))).includes('면접');
    return false;
  };

  const toggleStage = (stage: string) => {
    setVisibleStages(prev =>
      prev.includes(stage) ? prev.filter(s => s !== stage) : [...prev, stage]
    );
  };


  const latestStat = useMemo(() => {
    if (!stats || stats.length === 0) return null;
    return [...stats].sort((a, b) => (b.year * 10 + b.exam_round) - (a.year * 10 + a.exam_round))[0];
  }, [stats]);

  const handleNativeShare = async () => {
    const shareData = {
      title: `CertFinder - ${cert?.qual_name}`,
      text: `${cert?.qual_name}의 실시간 합격률과 난이도를 확인하세요!`,
      url: window.location.href,
    };

    try {
      if (navigator.share) {
        await navigator.share(shareData);
      } else {
        await navigator.clipboard.writeText(window.location.href);
        toast.success("링크가 클립보드에 복사되었습니다.");
      }
    } catch (err) {
      console.error('Share failed:', err);
    }
  };


  if (certLoading || statsLoading) {
    return (
      <div className="space-y-12 animate-in fade-in duration-500">
        <Skeleton className="h-64 w-full rounded-[2.5rem] bg-slate-900" />
        <div className="grid md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32 rounded-3xl bg-slate-900" />)}
        </div>
        <Skeleton className="h-[500px] w-full rounded-[2.5rem] bg-slate-900" />
      </div>
    );
  }

  if (!cert) {
    return (
      <div className="text-center py-40 space-y-6">
        <div className="p-8 bg-slate-900 rounded-full w-fit mx-auto">
          <Info className="w-16 h-16 text-slate-700" />
        </div>
        <h2 className="text-3xl font-bold text-white">정보를 찾을 수 없습니다</h2>
        <Button onClick={() => router.navigate('/certs')} variant="outline" className="rounded-xl border-slate-800">목록으로 돌아가기</Button>
      </div>
    );
  }

  const avgPassRate = stats.length > 0
    ? (stats.reduce((acc, s) => acc + (s.pass_rate || 0), 0) / stats.length).toFixed(1)
    : "정보 없음";

  const totalCandidates = stats.length > 0
    ? stats.reduce((acc, s) => acc + (s.candidate_cnt || 0), 0).toLocaleString()
    : "정보 없음";

  return (
    <div className="space-y-12 pb-20 max-w-7xl mx-auto">
      {/* Premium Header/Cover */}
      <div className="relative rounded-[2.5rem] overflow-hidden bg-slate-900 border border-slate-800 p-10 md:p-16">
        <div className="absolute top-0 right-0 w-[50%] h-full bg-gradient-to-l from-blue-600/15 via-indigo-600/5 to-transparent pointer-events-none" />
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-500/10 rounded-full blur-[100px]" />

        <div className="relative z-10 space-y-8">
          <Button
            variant="ghost"
            onClick={() => router.navigate('/certs')}
            className="text-slate-500 hover:text-white mb-4 -ml-4 flex items-center gap-2"
          >
            <ChevronLeft className="w-4 h-4" /> Back to Directory
          </Button>

          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-3">
              <Badge className="bg-blue-600/10 text-blue-400 border-blue-500/20 px-3 py-1 font-bold">{cert.qual_type}</Badge>
              {cert.is_active ? (
                <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 px-3 py-1">시행중</Badge>
              ) : (
                <Badge className="bg-red-500/10 text-red-400 border-red-500/20 px-3 py-1">종료</Badge>
              )}
            </div>

            <div className="space-y-4">
              <h1 className="text-4xl md:text-6xl font-black text-white tracking-tight leading-tight">
                {cert.qual_name}
              </h1>
              <div className="flex flex-wrap items-center gap-6 text-slate-400 font-medium">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-blue-500" />
                  <span>{cert.managing_body || "정보 없음"}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Globe className="w-5 h-5 text-indigo-500" />
                  <span>{cert.ncs_large} &gt; {cert.main_field}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Award className="w-5 h-5 text-amber-500" />
                  <span>{cert.grade_code || "등급 없음"}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-6">
            <Button
              onClick={toggleBookmark}
              className={`
                h-12 px-8 rounded-2xl font-bold flex items-center gap-2 transition-all
                ${isBookmarked
                  ? 'bg-amber-500 hover:bg-amber-600 text-white'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'}
              `}
            >
              <Bookmark className={`w-4 h-4 ${isBookmarked ? 'fill-white' : ''}`} />
              {isBookmarked ? '관심 자격증 해제' : '관심 자격증 추가'}
            </Button>
            <Button
              variant="outline"
              onClick={handleNativeShare}
              className="rounded-2xl h-12 w-12 p-0 border-slate-800 text-slate-400 hover:text-white hover:border-slate-600 transition-all"
            >
              <Share2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main Stats Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {(() => {
          const latestVal = cert.latest_pass_rate ?? latestStat?.pass_rate ?? 0;
          const avgVal = stats.length > 0 ? parseFloat(avgPassRate) : 0;

          const getPassRateStyles = (rate: number) => {
            if (rate === 0) return { color: "text-slate-400", bg: "bg-slate-400/5" };
            if (rate < 30) return { color: "text-rose-500", bg: "bg-rose-500/5" };
            if (rate < 60) return { color: "text-amber-400", bg: "bg-amber-400/5" };
            return { color: "text-emerald-400", bg: "bg-emerald-400/5" };
          };

          const latestStyles = getPassRateStyles(latestVal);
          const avgStyles = getPassRateStyles(avgVal);

          return [
            {
              label: "최근 합격률",
              value: (cert.latest_pass_rate !== null && cert.latest_pass_rate !== undefined) ? `${cert.latest_pass_rate}%` : (latestStat?.pass_rate ? `${latestStat.pass_rate}%` : "정보 없음"),
              icon: Zap, ...latestStyles,
              sub: latestStat ? `${latestStat.year}년 ${latestStat.exam_round}회차` : "최신 데이터"
            },
            {
              label: "평균 합격률",
              value: stats.length > 0 ? `${avgPassRate}%` : "정보 없음",
              icon: TrendingUp, ...avgStyles,
              sub: "전체 회차 평균"
            },
            {
              label: "누적 응시자",
              value: (cert.total_candidates ? cert.total_candidates.toLocaleString() : totalCandidates),
              icon: Users, color: "text-indigo-400", bg: "bg-indigo-400/5",
              sub: "최근 3개년 합계"
            },
            {
              label: "권장 난이도",
              value: (cert.avg_difficulty !== null && cert.avg_difficulty !== undefined) ? `${cert.avg_difficulty.toFixed(1)}/10` : "데이터 분석중",
              icon: Target, color: "text-amber-400", bg: "bg-amber-400/5",
              sub: "등급+합격률 기반"
            },
          ].map((stat, i) => (
            <Card key={i} className="bg-slate-900/50 border-slate-800 overflow-hidden group hover:border-blue-500/30 transition-all duration-300">
              <CardContent className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div className={`p-3 rounded-2xl ${stat.bg} transition-colors`}>
                    <stat.icon className={`w-5 h-5 ${stat.color} transition-colors`} />
                  </div>
                  <Badge variant="secondary" className="text-[10px] text-slate-500 font-bold uppercase tracking-widest border-none bg-slate-950/50">{stat.sub}</Badge>
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">{stat.label}</p>
                  <p className="text-2xl font-black text-white tracking-tight">{stat.value}</p>
                </div>
              </CardContent>
            </Card>
          ));
        })()}
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-8">
        <TabsList className="bg-slate-900/80 border border-slate-800 p-1.5 rounded-2xl gap-2 backdrop-blur-md sticky top-6 z-30">
          <TabsTrigger value="stats" className="px-6 py-2.5 rounded-xl font-bold data-[state=active]:bg-blue-600 data-[state=active]:text-white">
            <TrendingUp className="w-4 h-4 mr-2" /> 통계 및 분석
          </TabsTrigger>
          <TabsTrigger value="info" className="px-6 py-2.5 rounded-xl font-bold data-[state=active]:bg-blue-600 data-[state=active]:text-white">
            <BookOpen className="w-4 h-4 mr-2" /> 기본 정보
          </TabsTrigger>
          <TabsTrigger value="jobs" className="px-6 py-2.5 rounded-xl font-bold data-[state=active]:bg-blue-600 data-[state=active]:text-white">
            <Briefcase className="w-4 h-4 mr-2" /> 관련 직무
          </TabsTrigger>
        </TabsList>

        {/* Stats Tab */}
        <TabsContent value="stats" className="space-y-8 focus-visible:outline-none">
          <Card className="bg-slate-900/50 border-slate-800 rounded-[2.5rem] overflow-hidden">
            <CardHeader className="p-10 border-b border-slate-800">
              <div className="flex justify-between items-end">
                <div className="space-y-2">
                  <Badge variant="outline" className="border-blue-500/20 text-blue-400">Time-series Analysis</Badge>
                  <CardTitle className="text-3xl font-black text-white">합격률 변화 추이</CardTitle>
                </div>
                <div className="flex flex-wrap gap-4">
                  {['필기', '실기', '면접'].map(stage => hasStage(stage) && (
                    <button
                      key={stage}
                      onClick={() => toggleStage(stage)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl border transition-all ${visibleStages.includes(stage)
                        ? stage === '필기' ? 'bg-blue-500/10 border-blue-500/50 text-blue-400'
                          : stage === '실기' ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400'
                            : 'bg-amber-500/10 border-amber-500/50 text-amber-400'
                        : 'bg-slate-900 border-slate-800 text-slate-500 opacity-50'
                        }`}
                    >
                      <div className={`w-2 h-2 rounded-full ${stage === '필기' ? 'bg-blue-500' : stage === '실기' ? 'bg-emerald-500' : 'bg-amber-500'
                        }`} />
                      <span className="text-xs font-bold">{stage}</span>
                    </button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-10">
              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="colorWritten" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorPractical" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorInterview" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis
                      dataKey="label"
                      stroke="#475569"
                      fontSize={11}
                      fontWeight={700}
                      tickLine={false}
                      axisLine={false}
                      dy={10}
                    />
                    <YAxis
                      stroke="#475569"
                      fontSize={11}
                      fontWeight={700}
                      tickLine={false}
                      axisLine={false}
                      dx={-10}
                      domain={[0, 100]}
                    />
                    <RechartsTooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '16px', color: '#fff' }}
                    />
                    {visibleStages.includes('필기') && (
                      <Area
                        type="monotone"
                        dataKey="written"
                        name="필기 합격률"
                        stroke="#3b82f6"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorWritten)"
                        animationDuration={1000}
                      />
                    )}
                    {visibleStages.includes('실기') && (
                      <Area
                        type="monotone"
                        dataKey="practical"
                        name="실기 합격률"
                        stroke="#10b981"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorPractical)"
                        animationDuration={1200}
                      />
                    )}
                    {visibleStages.includes('면접') && (
                      <Area
                        type="monotone"
                        dataKey="interview"
                        name="면접 합격률"
                        stroke="#f59e0b"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorInterview)"
                        animationDuration={1400}
                      />
                    )}
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>

          </Card>

          <div className="grid md:grid-cols-2 gap-8">
            <Card className="bg-slate-900/50 border-slate-800 rounded-[2.5rem] p-10">
              <CardTitle className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-indigo-400" /> 상세 회차 정보
              </CardTitle>
              <div className="space-y-4">
                {stats.slice(0, 10).map((s, i) => {
                  const roundName = getRoundName(s.exam_round);
                  const yearLabel = `${s.year}년 ${s.exam_round}차 시험 평균`;

                  const passRateValue = s.pass_rate || 0;
                  const getPassRateColor = (rate: number) => {
                    if (rate < 30) return 'text-rose-500';
                    if (rate < 60) return 'text-amber-400';
                    return 'text-emerald-400';
                  };

                  return (
                    <div key={i} className="flex items-center justify-between p-5 bg-slate-950/40 rounded-[1.5rem] border border-slate-800/50 hover:border-slate-700/80 hover:bg-slate-900/40 transition-all duration-300 group/item">
                      <div className="space-y-1.5">
                        <p className="text-sm font-bold text-white group-hover/item:text-blue-400 transition-colors">{yearLabel}</p>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-slate-700 text-slate-500 font-bold uppercase tracking-wider">
                            {roundName}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex gap-8 text-right">
                        <div>
                          <p className="text-[10px] text-slate-600 font-bold uppercase mb-1 tracking-tighter">합격률</p>
                          <p className={`text-base font-black ${getPassRateColor(passRateValue)}`}>
                            {passRateValue}%
                          </p>
                        </div>
                        <div className="hidden sm:block">
                          <p className="text-[10px] text-slate-600 font-bold uppercase mb-1 tracking-tighter">응시자</p>
                          <p className="text-base font-black text-slate-300">
                            {s.candidate_cnt?.toLocaleString() || '-'}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            <Card className="bg-slate-900 border-indigo-600/20 rounded-[2.5rem] p-10 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-10 opacity-5 group-hover:scale-110 transition-transform duration-700">
                <Award className="w-40 h-40 text-indigo-400" />
              </div>
              <div className="relative z-10 space-y-6">
                <Badge className="bg-indigo-600/10 text-indigo-400 border-indigo-500/20">Analysis Verdict</Badge>
                <div className="space-y-4">
                  <h3 className="text-3xl font-black text-white">데이터 분석 결과</h3>
                  <div className="text-slate-400 leading-relaxed">
                    본 자격증은 최근 {stats.length}개 회차 평균 합격률 <span className="text-white font-bold">{avgPassRate}%</span> 내외를 보이고 있으며,
                    자격 등급과 합격률 추이를 종합 분석한 결과
                    <span className="text-amber-400 font-bold ml-1"> {
                      cert.avg_difficulty && cert.avg_difficulty >= 8.5 ? '최상급 (Expert)' :
                        cert.avg_difficulty && cert.avg_difficulty >= 7.0 ? '심화 (Advanced)' :
                          cert.avg_difficulty && cert.avg_difficulty >= 5.0 ? '중등 (Intermediate)' :
                            cert.avg_difficulty && cert.avg_difficulty >= 3.0 ? '기초 (Basic)' : '입문 (Entry)'
                    }</span> 수준의 난이도로 분류됩니다.
                  </div>
                </div>
                <div className="pt-4 space-y-3">
                  <div className="flex items-center gap-3 text-sm text-slate-300">
                    <CheckCircle className="w-4 h-4 text-emerald-500" /> {cert.grade_code} 레벨의 전문성 요구
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-300">
                    <CheckCircle className="w-4 h-4 text-emerald-500" /> 과거 {stats.length}개 회차 빅데이터 분석 완료
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        {/* Info Tab */}
        <TabsContent value="info" className="space-y-8 focus-visible:outline-none">
          <Card className="bg-slate-900/50 border-slate-800 rounded-[2.5rem] p-10">
            <div className="grid md:grid-cols-2 gap-12">
              <div className="space-y-8">
                <div className="space-y-4">
                  <h3 className="text-2xl font-bold text-white flex items-center gap-2">
                    <Info className="w-6 h-6 text-blue-500" /> 자격 개요
                  </h3>
                  <div className="text-slate-400 leading-relaxed bg-slate-950/40 p-6 rounded-2xl border border-slate-800">
                    {cert.qual_name} 자격은 {cert.ncs_large} 분야의 전문 인력을 양성하기 위해 시행되는 {cert.qual_type}입니다.
                    주로 {cert.main_field} 직무 수행에 필요한 이론 및 실무 역량을 평가하며, 산업 현장에서의 전문성을 인증합니다.
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-6">
                  <div className="p-4 bg-slate-950/40 rounded-2xl border border-slate-800">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">관리부처</p>
                    <p className="text-sm text-white font-medium">{cert.managing_body || "정보 없음"}</p>
                  </div>
                  <div className="p-4 bg-slate-950/40 rounded-2xl border border-slate-800">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">NCS 분류</p>
                    <p className="text-sm text-white font-medium">{cert.ncs_large}</p>
                  </div>
                </div>
              </div>

              <div className="space-y-6">
                <h3 className="text-2xl font-bold text-white">상세 메트릭스</h3>
                <div className="space-y-4">
                  {[
                    { label: "시행 기관", value: cert.managing_body || "정보 없음" },
                    { label: "직무 대분류", value: cert.ncs_large },
                    { label: "직무 중분류", value: cert.main_field },
                    { label: "자격 등급", value: cert.grade_code || "등급 미지정" },
                    { label: "최근 합격률", value: (cert.latest_pass_rate !== null && cert.latest_pass_rate !== undefined) ? `${cert.latest_pass_rate}%` : "정보 없음" },
                    { label: "평균 난이도", value: (cert.avg_difficulty !== null && cert.avg_difficulty !== undefined) ? `${cert.avg_difficulty.toFixed(1)}/10` : "데이터 분석중" },
                  ].map((item, i) => (
                    <div key={i} className="flex justify-between items-center py-3 border-b border-slate-800/50">
                      <span className="text-sm font-medium text-slate-500">{item.label}</span>
                      <span className="text-sm font-bold text-white">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        </TabsContent>

        {/* Related Jobs Tab */}
        <TabsContent value="jobs" className="space-y-10 focus-visible:outline-none">
          {(!cert.jobs || cert.jobs.length === 0) ? (
            <Card className="bg-slate-900/30 border-slate-800 border-dashed py-32 text-center rounded-[2.5rem]">
              <div className="space-y-6 max-w-sm mx-auto">
                <div className="p-6 bg-slate-900 rounded-full w-fit mx-auto">
                  <Briefcase className="w-12 h-12 text-slate-700" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-2xl font-bold text-white">매칭된 직무가 없습니다</h3>
                  <p className="text-slate-500">이 자격증과 직접적으로 연관된 직무 데이터를 분석 중입니다.</p>
                </div>
              </div>
            </Card>
          ) : (
            <div className="grid gap-10">
              {cert.jobs.map((job) => {
                const radarData = [
                  { subject: '보상', A: job.reward || 0, fullMark: 100 },
                  { subject: '안정성', A: job.stability || 0, fullMark: 100 },
                  { subject: '발전', A: job.development || 0, fullMark: 100 },
                  { subject: '환경', A: job.condition || 0, fullMark: 100 },
                  { subject: '전문성', A: job.professionalism || 0, fullMark: 100 },
                  { subject: '평등', A: job.equality || 0, fullMark: 100 },
                ];

                return (
                  <Card key={job.job_id} className="bg-slate-900/50 border-slate-800 group overflow-hidden rounded-[2.5rem] hover:border-slate-600 transition-all shadow-xl">
                    <CardHeader className="bg-slate-950/60 p-10 border-b border-slate-800">
                      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                        <div className="flex items-center gap-4">
                          <div className="p-4 bg-blue-600/10 rounded-2xl border border-blue-500/20">
                            <Briefcase className="w-8 h-8 text-blue-400" />
                          </div>
                          <div className="space-y-1">
                            <div className="text-3xl font-black text-white group-hover:text-blue-400 transition-colors">
                              {job.job_name}
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                              {job.similar_jobs && (
                                <div className="flex flex-wrap gap-1">
                                  {job.similar_jobs.split(',').slice(0, 3).map((sj, i) => (
                                    <Badge key={i} className="bg-indigo-600/10 text-indigo-400 border-indigo-500/20 text-[10px]">{sj.trim()}</Badge>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                        <Button variant="outline" onClick={() => router.navigate('/jobs')} className="rounded-xl border-slate-800 text-slate-400 hover:text-white group-hover:border-blue-500/30 transition-all">
                          직무 목록 보기 <ChevronRight className="w-4 h-4 ml-2" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent className="p-10">
                      <div className="grid lg:grid-cols-12 gap-12">
                        {/* Content */}
                        <div className="lg:col-span-8 space-y-10">
                          <div className="space-y-4">
                            <h4 className="text-xs font-black text-blue-500/80 uppercase tracking-[0.2em] flex items-center gap-2">
                              <BookOpen className="w-4 h-4" /> 핵심 적성 및 요구 역량
                            </h4>
                            <div className="text-slate-300 text-sm leading-relaxed bg-blue-500/5 p-6 rounded-2xl border border-blue-500/10 min-h-[100px] whitespace-pre-line">
                              {(job.aptitude || '적성 정보 업데이트 예정입니다.').replace(/ - /g, '\n- ').replace(/^- /g, '- ')}
                            </div>
                          </div>

                          <div className="grid sm:grid-cols-2 gap-8">
                            <div className="space-y-4">
                              <h4 className="text-xs font-black text-emerald-500/80 uppercase tracking-[0.2em] flex items-center gap-2">
                                <TrendingUp className="w-4 h-4" /> 직업 전망 분석
                              </h4>
                              <div className="text-emerald-300 text-sm leading-relaxed bg-emerald-500/5 p-6 rounded-2xl border border-emerald-500/10 min-h-[140px] whitespace-pre-line">
                                {job.outlook_summary || job.outlook || '전망 정보 제공 대기중'}
                              </div>
                            </div>
                            {(job.entry_salary || job.salary_info) && (
                              <div className="space-y-4">
                                <h4 className="text-xs font-black text-amber-500/80 uppercase tracking-[0.2em] flex items-center gap-2">
                                  <DollarSign className="w-4 h-4" /> 임금 및 만족도
                                </h4>
                                <div className="text-amber-300 text-sm leading-relaxed bg-amber-500/5 p-6 rounded-2xl border border-amber-500/10 min-h-[140px] whitespace-pre-line">
                                  {job.entry_salary && (
                                    <div className="mb-3 pb-3 border-b border-amber-500/10">
                                      <div className="text-lg font-black text-amber-400">{job.entry_salary}</div>
                                    </div>
                                  )}
                                  {job.salary_info}
                                </div>
                              </div>
                            )}
                          </div>

                          <div className="space-y-4 pt-4 border-t border-slate-800/50">
                            <h4 className="text-xs font-black text-indigo-500/80 uppercase tracking-[0.2em] flex items-center gap-2">
                              <Zap className="w-4 h-4" /> 취업 방법 및 핵심 경로
                            </h4>
                            <div className="text-indigo-300 text-sm leading-relaxed bg-indigo-500/5 p-6 rounded-2xl border border-indigo-500/10 whitespace-pre-line">
                              {(job.employment_path || '취업 경로 정보 업데이트 중').replace(/ - /g, '\n- ').replace(/^- /g, '- ')}
                            </div>
                          </div>
                        </div>

                        {/* Analysis Card */}
                        <div className="lg:col-span-4 flex flex-col items-center justify-center p-8 bg-slate-950/40 rounded-3xl border border-slate-800/50">
                          <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mb-4">직무 역량 다이어그램</h4>
                          <div className="h-64 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                                <PolarGrid stroke="#1e293b" />
                                <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10, fontWeight: 700 }} />
                                <Radar
                                  name="역량 지수"
                                  dataKey="A"
                                  stroke="#3b82f6"
                                  fill="#3b82f6"
                                  fillOpacity={0.6}
                                />
                                <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                                <RechartsTooltip
                                  contentStyle={{ backgroundColor: '#020617', border: '1px solid #1e293b', borderRadius: '12px' }}
                                  itemStyle={{ color: '#3b82f6' }}
                                />
                              </RadarChart>
                            </ResponsiveContainer>
                          </div>
                          <p className="text-[10px] text-slate-600 font-bold uppercase tracking-widest mt-4 text-center">Standardized Analysis (0-100 Base)</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
