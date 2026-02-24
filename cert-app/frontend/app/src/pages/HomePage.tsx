import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Search,
  Award,
  TrendingUp,
  Star,
  ArrowRight,
  CheckCircle2,
  Briefcase,
  ChevronRight,
  Target,
  Sparkles
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useRouter } from '@/lib/router';
import { getTrendingCerts } from '@/lib/api';
import type { TrendingQualification } from '@/types';

export function HomePage() {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [trendingCerts, setTrendingCerts] = useState<TrendingQualification[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasRequestedTrending, setHasRequestedTrending] = useState(false);
  const trendingSectionRef = useRef<HTMLElement>(null);
  const fetchStartedRef = useRef(false);

  const fetchTrendingData = useCallback(async () => {
    if (fetchStartedRef.current) return;
    fetchStartedRef.current = true;
    setHasRequestedTrending(true);
    setLoading(true);
    try {
      const res = await getTrendingCerts(6);
      setTrendingCerts(res.items);
    } catch (error) {
      console.error('Failed to fetch trending data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const el = trendingSectionRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) fetchTrendingData();
      },
      { rootMargin: '120px', threshold: 0 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [fetchTrendingData]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (search.trim()) {
      router.navigate(`/certs?q=${encodeURIComponent(search)}`);
    } else {
      router.navigate('/certs');
    }
  };

  return (
    <div className="flex flex-col gap-20 pb-20 overflow-hidden">
      {/* Hero Section */}
      <section className="relative min-h-[85vh] flex items-center pt-20">
        {/* Background Decorative Elements */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full -z-10">
          <div className="absolute top-20 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[100px] animate-pulse" />
          <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-[100px] animate-pulse delay-700" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 brightness-50 contrast-150" />
        </div>

        <div className="container mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
          <div className="space-y-8 text-center lg:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-medium animate-fade-in">
              <Sparkles className="w-4 h-4" />
              <span>Next-Gen Career Analysis Platform</span>
            </div>

            <h1 className="text-5xl lg:text-7xl font-extrabold tracking-tight text-white leading-[1.1]">
              데이터로 설계하는<br />
              <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 text-transparent bg-clip-text">
                당신의 커리어 경로
              </span>
            </h1>

            <p className="text-slate-400 text-lg lg:text-xl max-w-xl mx-auto lg:mx-0 leading-relaxed">
              국가 기술 자격증의 합격 확률, 난이도 분석, 그리고 맞춤형 직무 추천까지.
              검증된 데이터를 통해 최적의 목표를 설정하세요.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start pt-4">
              <form onSubmit={handleSearch} className="relative group flex-1 max-w-md">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200" />
                <div className="relative">
                  <label htmlFor="home-cert-search" className="sr-only">자격증 검색</label>
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 w-5 h-5" />
                  <input
                    id="home-cert-search"
                    name="q"
                    type="text"
                    placeholder="관심 있는 자격증을 검색하세요..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full h-14 pl-12 pr-4 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  />
                </div>
              </form>
              <Button
                onClick={() => router.navigate('/recommendation')}
                className="h-14 px-8 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-lg shadow-lg shadow-blue-900/20 transition-all hover:scale-105"
              >
                전공별 추천 시작
              </Button>
            </div>

            <div className="flex items-center justify-center lg:justify-start gap-8 pt-8 text-slate-500 text-sm font-medium">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" /> 1,000+ 자격증 데이터
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" /> 실시간 합격률 분석
              </div>
            </div>
          </div>

          <div className="relative hidden lg:block">
            {/* Visual element representing data/analytics */}
            <div className="relative z-10 p-1 bg-gradient-to-br from-slate-800 to-slate-900 rounded-3xl border border-slate-700 shadow-2xl overflow-hidden group">
              <div className="absolute inset-0 bg-blue-600/5 group-hover:bg-blue-600/10 transition-colors" />
              <div className="relative bg-slate-950 rounded-[22px] p-8 space-y-6">
                <div className="flex justify-between items-center">
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-blue-400 uppercase tracking-widest">Global Statistics</p>
                    <h3 className="text-xl font-bold text-white">Trend Analysis</h3>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg">
                    <TrendingUp className="w-5 h-5 text-indigo-400" />
                  </div>
                </div>

                {/* Simulated Chart/Data visualization */}
                <div className="h-48 w-full flex items-end gap-2 px-2">
                  {[40, 70, 45, 90, 65, 80, 55, 95].map((h, i) => (
                    <div
                      key={i}
                      className="flex-1 bg-gradient-to-t from-blue-600 to-indigo-400 rounded-t-sm transition-all duration-1000 hover:brightness-125"
                      style={{ height: `${h}%` }}
                    />
                  ))}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                    <p className="text-xs text-slate-500 mb-1">Pass Rate</p>
                    <p className="text-2xl font-bold text-emerald-400">74.2%</p>
                  </div>
                  <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                    <p className="text-xs text-slate-500 mb-1">Growth</p>
                    <p className="text-2xl font-bold text-blue-400">+12%</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Floatables */}
            <div className="absolute -top-6 -right-6 p-4 bg-slate-900 border border-slate-800 rounded-2xl shadow-xl animate-bounce-slow z-20">
              <Star className="w-6 h-6 text-yellow-500 fill-yellow-500" />
            </div>
            <div className="absolute -bottom-8 -left-8 p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-xl animate-float z-20">
              <Award className="w-8 h-8 text-blue-500" />
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="container mx-auto px-6">
        <div className="text-center space-y-4 mb-16">
          <Badge variant="outline" className="border-blue-500/30 text-blue-400 px-4 py-1">Core Modules</Badge>
          <h2 className="text-3xl md:text-4xl font-bold text-white">핵심 서비스 안내</h2>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {[
            {
              title: "맞춤형 추천 시스템",
              desc: "당신의 전공과 경력을 분석하여 가장 적합한 자격증 로드맵을 제안합니다.",
              icon: Target,
              color: "text-blue-400",
              bg: "bg-blue-400/5",
              border: "group-hover:border-blue-500/50",
              link: "/recommendation"
            },
            {
              title: "진로 및 직무 매칭",
              desc: "자격증 취득 후 가질 수 있는 직업의 전망과 연봉 정보를 상세히 제공합니다.",
              icon: Briefcase,
              color: "text-indigo-400",
              bg: "bg-indigo-400/5",
              border: "group-hover:border-indigo-500/50",
              link: "/jobs"
            },
            {
              title: "자격증 탐색 및 상세 정보",
              desc: "전체 국가기술자격증 목록을 검색하고, 각 자격증의 상세 통계와 취득 정보를 탐색하세요.",
              icon: Search,
              color: "text-purple-400",
              bg: "bg-purple-400/5",
              border: "group-hover:border-purple-500/50",
              link: "/certs"
            }
          ].map((feature, i) => (
            <Card
              key={i}
              onClick={() => router.navigate(feature.link)}
              className={`group bg-slate-900/40 border-slate-800 hover:bg-slate-900/80 transition-all cursor-pointer overflow-hidden ${feature.border}`}
            >
              <CardContent className="p-8 space-y-6">
                <div className={`w-14 h-14 rounded-2xl ${feature.bg} flex items-center justify-center transition-transform group-hover:scale-110 duration-500`}>
                  <feature.icon className={`w-7 h-7 ${feature.color}`} />
                </div>
                <div className="space-y-3">
                  <h3 className="text-xl font-bold text-white group-hover:text-white flex items-center gap-2">
                    {feature.title}
                    <ArrowRight className="w-4 h-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                  </h3>
                  <p className="text-slate-400 leading-relaxed">
                    {feature.desc}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Top Certs Section - 데이터는 이 섹션이 뷰포트에 들어올 때 로드 */}
      <section ref={trendingSectionRef} className="bg-slate-900/30 py-24 border-y border-slate-800/50">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-end gap-6 mb-12">
            <div className="space-y-4">
              <Badge variant="outline" className="border-indigo-500/30 text-indigo-400 px-4 py-1">Recent Trends</Badge>
              <h2 className="text-3xl md:text-4xl font-bold text-white">최근 주목받는 자격증</h2>
              <p className="text-slate-400">실시간 데이터가 반영된 최신 인기 트렌드를 확인하세요.</p>
            </div>
            <Button
              variant="ghost"
              onClick={() => router.navigate('/certs')}
              className="text-blue-400 hover:text-blue-300 hover:bg-blue-400/5 flex items-center gap-2"
            >
              전체 보기 <ChevronRight className="w-4 h-4" />
            </Button>
          </div>

          {loading ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3, 4, 5, 6].map(i => (
                <div key={i} className="h-48 rounded-2xl bg-slate-900/50 animate-pulse" />
              ))}
            </div>
          ) : trendingCerts.length > 0 ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {trendingCerts.map((cert, index) => (
                <div
                  key={cert.qual_id}
                  onClick={() => router.navigate(`/certs/${cert.qual_id}`)}
                  className="group relative p-6 bg-slate-900 border border-slate-800 rounded-2xl hover:border-blue-500/50 hover:bg-slate-900/80 transition-all cursor-pointer overflow-hidden shadow-lg card-hover-effect"
                >
                  <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-blue-600/5 to-transparent rounded-bl-full group-hover:from-blue-600/10 transition-colors" />

                  {/* Rank Badge */}
                  <div className="absolute -top-1 -left-1 w-8 h-8 bg-blue-600 text-white rounded-br-xl flex items-center justify-center font-bold text-xs z-10">
                    {index + 1}
                  </div>

                  <div className="relative space-y-4">
                    <div className="flex justify-between items-start">
                      <Badge className="bg-slate-800 text-slate-300 border-none px-2 py-0">{cert.qual_type}</Badge>
                      <div className="flex items-center gap-1 text-blue-400 text-sm font-bold bg-blue-400/5 px-2 py-1 rounded-lg border border-blue-400/10">
                        <TrendingUp className="w-3 h-3" />
                        {cert.score.toFixed(1)}
                      </div>
                    </div>

                    <h3 className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors line-clamp-1">
                      {cert.qual_name}
                    </h3>

                    <div className="flex items-center gap-3 text-xs text-slate-500 font-medium">
                      <span className="flex items-center gap-1">
                        <Award className="w-3 h-3" /> {cert.main_field || "정보 없음"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="col-span-full py-12 text-center text-slate-500 bg-slate-900/20 rounded-2xl border border-dashed border-slate-800">
                {hasRequestedTrending
                  ? '데이터 집계 중입니다... 자격증을 검색하거나 상세 페이지를 조회해보세요!'
                  : '스크롤하면 최근 주목받는 자격증을 불러옵니다.'}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-6">
        <div className="relative rounded-[2rem] overflow-hidden bg-gradient-to-r from-blue-600 to-indigo-700 p-12 md:p-20 text-center">
          <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay" />
          <div className="relative z-10 space-y-8 max-w-3xl mx-auto">
            <h2 className="text-3xl md:text-5xl font-extrabold text-white leading-tight">
              커리어의 다음 단계를<br />지금 바로 설계해 보세요
            </h2>
            <p className="text-blue-100 text-lg opacity-80">
              전문가 수준의 데이터 분석을 통해 당신의 성공 가능성을 획기적으로 높여드립니다.
              회원가입 없이 모든 분석 기능을 무료로 이용할 수 있습니다.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
              <Button
                onClick={() => router.navigate('/recommendation')}
                size="lg"
                className="bg-white text-blue-600 hover:bg-blue-50 text-lg font-bold rounded-xl h-14 px-10 shadow-xl"
              >
                전공별 자격증 추천
              </Button>
              <Button
                onClick={() => router.navigate('/jobs')}
                variant="outline"
                size="lg"
                className="border-white/30 text-white hover:bg-white/10 text-lg font-bold rounded-xl h-14 px-10 backdrop-blur-sm"
              >
                직업 전망 분석하기
              </Button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
