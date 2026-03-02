import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from '@/lib/router';
import { useMajors, usePopularMajors } from '@/hooks/useRecommendations';
import {
    User, Bookmark, History, ChevronRight,
    Mail, School, Award, Sparkles,
    Search, Settings, PlusCircle, X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogFooter,
} from "@/components/ui/dialog";
import { getFavorites, getRecentViewed, getRecommendations, updateProfile, getProfile, getAcquiredCerts, addAcquiredCert, removeAcquiredCert, getCertifications, getAcquiredCertsSummary } from '@/lib/api';
import type { AcquiredCertItem, AcquiredCertSummary } from '@/lib/api';
import type { QualificationListResponse } from '@/types';
import { toast } from 'sonner';

// Re-importing missing icons (added Activity, Target)
const Target = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></svg>
);

// ─── 티어 정보 ─────────────────────────────────────────────────────────────
const TIER_META: Record<string, { color: string; bg: string; border: string; gem: string }> = {
    Bronze:   { color: '#a97241', bg: 'rgba(169,114,65,0.12)',  border: 'rgba(122,79,37,0.4)',   gem: '🥉' },
    Silver:   { color: '#9da8b3', bg: 'rgba(157,168,179,0.10)', border: 'rgba(107,122,135,0.4)',  gem: '🥈' },
    Gold:     { color: '#f5c518', bg: 'rgba(245,197,24,0.12)',  border: 'rgba(201,162,0,0.4)',    gem: '🥇' },
    Platinum: { color: '#54e0c7', bg: 'rgba(84,224,199,0.10)',  border: 'rgba(42,184,160,0.4)',   gem: '💠' },
    Diamond:  { color: '#b9f2ff', bg: 'rgba(185,242,255,0.10)', border: 'rgba(77,217,255,0.5)',   gem: '💎' },
};

function getTierMeta(tier: string | null | undefined) {
    return TIER_META[tier ?? ''] ?? TIER_META['Bronze'];
}

const MYPAGE_CACHE_KEY = 'certfinder-mypage-cache';
const MYPAGE_CACHE_TTL_MS = 5 * 60 * 1000; // 5분: 탭 전환 후 복귀 시 캐시로 즉시 표시

// ─── 프론트엔드 XP 계산 (백엔드 미배포 상태에서도 동작하는 폴백) ────────────
const LOCAL_LEVEL_THRESHOLDS = [0, 5, 15, 35, 70, 120, 190, 290, 430];

function calcXpFromDiff(difficulty: number | null | undefined): number {
    if (difficulty == null) return 3.0;
    const d = Number(difficulty);
    let bonus: number;
    if (d >= 9.0)      bonus = 12.0;
    else if (d >= 8.0) bonus = 8.0;
    else if (d >= 7.0) bonus = 5.0;
    else if (d >= 6.0) bonus = 2.0;
    else if (d >= 5.0) bonus = 0.0;
    else if (d >= 4.0) bonus = -0.5;
    else if (d >= 3.0) bonus = -1.0;
    else               bonus = -0.5;
    return Math.max(0.5, Math.round((d + bonus) * 100) / 100);
}

function getLevelFromXp(xp: number): number {
    let level = 1;
    LOCAL_LEVEL_THRESHOLDS.forEach((threshold, i) => {
        if (xp >= threshold) level = i + 1;
    });
    return Math.min(level, 9);
}

function getTierFromLevel(level: number): string {
    if (level <= 2) return 'Bronze';
    if (level <= 4) return 'Silver';
    if (level <= 6) return 'Gold';
    if (level <= 8) return 'Platinum';
    return 'Diamond';
}

function computeLocalSummary(certs: AcquiredCertItem[]): AcquiredCertSummary | null {
    if (certs.length === 0) return null;
    const totalXp = certs.reduce((sum, cert) => {
        const diff = (cert.qualification as any)?.avg_difficulty;
        return sum + (diff != null ? calcXpFromDiff(diff) : (cert.xp && cert.xp !== 3 ? cert.xp : 3.0));
    }, 0);
    const level = getLevelFromXp(totalXp);
    const tier = getTierFromLevel(level);
    return {
        total_xp: Math.round(totalXp * 100) / 100,
        level,
        tier,
        tier_color: TIER_META[tier]?.color ?? '#a97241',
        current_level_xp: LOCAL_LEVEL_THRESHOLDS[level - 1],
        next_level_xp: level < 9 ? LOCAL_LEVEL_THRESHOLDS[level] : null,
        cert_count: certs.length,
    };
}

function XpProgressBar({ summary }: { summary: AcquiredCertSummary }) {
    const meta = getTierMeta(summary.tier);
    const curXp = summary.total_xp - summary.current_level_xp;
    const rangeXp = summary.next_level_xp != null
        ? summary.next_level_xp - summary.current_level_xp
        : 1;
    const pct = summary.next_level_xp == null ? 100 : Math.min(100, Math.round((curXp / rangeXp) * 100));
    return (
        <div className="w-full space-y-1">
            <div className="flex justify-between items-center">
                <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: meta.color }}>
                    {summary.tier} Lv.{summary.level}
                </span>
                <span className="text-[9px] text-slate-500 font-bold">
                    {summary.next_level_xp == null ? 'MAX' : `${Math.round(summary.total_xp)} / ${summary.next_level_xp} XP`}
                </span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${pct}%`, background: meta.color, boxShadow: `0 0 6px ${meta.color}` }}
                />
            </div>
        </div>
    );
}

export function MyPage() {
    const { user, token, loading: authLoading } = useAuth();
    const router = useRouter();
    const [favorites, setFavorites] = useState<any[]>([]);
    const [recentCerts, setRecentCerts] = useState<any[]>([]);
    const [recommendations, setRecommendations] = useState<any[]>([]);
    const [profile, setProfile] = useState<any>(null);

    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [nickname, setNickname] = useState('');
    const [userMajor, setUserMajor] = useState('');
    const [gradeYear, setGradeYear] = useState<number | null>(null);
    const [isUpdating, setIsUpdating] = useState(false);
    const [nicknameError, setNicknameError] = useState<string | null>(null);
    const [dataLoading, setDataLoading] = useState(true);
    const [acquiredCerts, setAcquiredCerts] = useState<AcquiredCertItem[]>([]);
    const [xpSummary, setXpSummary] = useState<AcquiredCertSummary | null>(null);
    const [isAcquiredDialogOpen, setIsAcquiredDialogOpen] = useState(false);
    const [certSearchQuery, setCertSearchQuery] = useState('');
    const [certSearchResults, setCertSearchResults] = useState<any[]>([]);
    const [certSearchLoading, setCertSearchLoading] = useState(false);
    const certSearchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // 디바운스 검색: 입력 멈춘 뒤 300ms 후에만 API 호출 (매 키 입력마다 요청하지 않음)
    useEffect(() => {
        if (!isAcquiredDialogOpen) return;
        const q = certSearchQuery.trim();
        if (q.length < 2) {
            setCertSearchResults([]);
            setCertSearchLoading(false);
            return;
        }
        if (certSearchTimeoutRef.current) clearTimeout(certSearchTimeoutRef.current);
        certSearchTimeoutRef.current = setTimeout(() => {
            certSearchTimeoutRef.current = null;
            setCertSearchLoading(true);
            getCertifications({ q, page: 1, page_size: 15 })
                .then((res: QualificationListResponse) => setCertSearchResults(res.items || []))
                .catch(() => setCertSearchResults([]))
                .finally(() => setCertSearchLoading(false));
        }, 300);
        return () => {
            if (certSearchTimeoutRef.current) clearTimeout(certSearchTimeoutRef.current);
        };
    }, [certSearchQuery, isAcquiredDialogOpen]);

    // Sync state when dialog opens
    useEffect(() => {
        if (isSettingsOpen && user) {
            setNickname(user.user_metadata?.nickname || user.user_metadata?.userid || '');
            setUserMajor(user.user_metadata?.detail_major || '');
            setGradeYear(user.user_metadata?.grade_year !== undefined ? Number(user.user_metadata.grade_year) : null);
        }
    }, [isSettingsOpen, user]);

    // Major autocomplete
    const [showMajorSuggestions, setShowMajorSuggestions] = useState(false);
    const { majors: availableMajors } = useMajors();
    const { majors: popularMajorsFromApi } = usePopularMajors(8);
    const popularMajors = popularMajorsFromApi.length > 0
        ? popularMajorsFromApi
        : ['컴퓨터공학', '정보통신공학', '전자공학', '경영학', '경제학', '심리학', '간호학', '교육학'];

    const loadData = async (showLoading = true) => {
        if (showLoading) setDataLoading(true);
        try {
            const majorFromUser = user?.user_metadata?.detail_major;

            if (!token) {
                setDataLoading(false);
                return;
            }

            const [favRes, recentData, profileData, acquiredRes, summaryRes, recRes] = await Promise.all([
                getFavorites(token, 1, 5),
                getRecentViewed(token),
                getProfile(token),
                getAcquiredCerts(token, 1, 200).catch(() => ({ items: [] as AcquiredCertItem[], total: 0 })),
                getAcquiredCertsSummary(token).catch(() => null),
                majorFromUser
                    ? getRecommendations(majorFromUser, 20).catch(() => ({ items: [] as any[] }))
                    : Promise.resolve({ items: [] as any[] }),
            ]);

            setFavorites(favRes.items.map((f: any) => f.qualification));
            setRecentCerts(recentData);
            setProfile(profileData);
            setAcquiredCerts(acquiredRes.items);
            setXpSummary(summaryRes);

            const finalMajor = profileData?.detail_major ?? majorFromUser;
            let recList: any[];
            if (finalMajor && profileData?.detail_major !== majorFromUser) {
                const recResFromProfile = await getRecommendations(finalMajor, 20);
                recList = recResFromProfile.items || [];
            } else {
                recList = recRes.items || [];
            }
            setRecommendations(recList);

            try {
                sessionStorage.setItem(MYPAGE_CACHE_KEY, JSON.stringify({
                    userId: user?.id,
                    ts: Date.now(),
                    favorites: favRes.items.map((f: any) => f.qualification),
                    recentCerts: recentData,
                    profile: profileData,
                    acquiredCerts: acquiredRes.items,
                    xpSummary: summaryRes,
                    recommendations: recList,
                }));
            } catch {
                // sessionStorage 풀 등 무시
            }
        } catch (err: any) {
            console.error('Failed to load mypage data:', err);
        } finally {
            if (showLoading) setDataLoading(false);
        }
    };

    const handleUpdateProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;

        setNicknameError(null);
        setIsUpdating(true);
        try {
            await updateProfile(token, {
                nickname: nickname,
                detail_major: userMajor,
                grade_year: gradeYear === null ? 0 : gradeYear
            });
            toast.success('프로필이 업데이트되었습니다.');
            setIsSettingsOpen(false);
            // 로컬 상태만 즉시 갱신 (refreshSession 제거 - onAuthStateChange가 useEffect를 재트리거해
            // loadData가 이중 호출되어 favorites/acquired_certs가 깜빡이는 레이스컨디션 방지)
            setProfile((p: any) => (p ? { ...p, nickname, detail_major: userMajor, grade_year: gradeYear ?? 0 } : p));
        } catch (err: any) {
            const msg = err?.message || '프로필 업데이트에 실패했습니다.';
            if (msg.includes('중복')) setNicknameError('중복입니다.');
            toast.error(msg);
        } finally {
            setIsUpdating(false);
        }
    };

    useEffect(() => {
        if (authLoading) return;

        if (!user) {
            router.navigate('/');
            return;
        }

        let cached: { userId?: string; ts?: number; favorites?: any[]; recentCerts?: any[]; profile?: any; acquiredCerts?: any[]; xpSummary?: any; recommendations?: any[] };
        try {
            const raw = sessionStorage.getItem(MYPAGE_CACHE_KEY);
            if (raw) cached = JSON.parse(raw);
        } catch {
            cached = {};
        }
        const isCacheValid = cached != null
            && String(cached.userId) === String(user.id)
            && cached.ts != null
            && (Date.now() - cached.ts) < MYPAGE_CACHE_TTL_MS;
        if (isCacheValid && cached) {
            setFavorites(cached.favorites ?? []);
            setRecentCerts(cached.recentCerts ?? []);
            setProfile(cached.profile ?? null);
            setAcquiredCerts(cached.acquiredCerts ?? []);
            setXpSummary(cached.xpSummary ?? null);
            setRecommendations(cached.recommendations ?? []);
            setDataLoading(false);
            const timer = setTimeout(() => loadData(false), 50);
            return () => clearTimeout(timer);
        }
        loadData(true);
    }, [user?.id, token, authLoading]);

    if (authLoading) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
                    <p className="text-slate-400 font-medium animate-pulse">인증 정보 확인 중...</p>
                </div>
            </div>
        );
    }

    if (!user) return null;

    // 백엔드 summary가 없을 때 프론트에서 직접 계산한 폴백 사용
    const effectiveSummary: AcquiredCertSummary | null = xpSummary ?? computeLocalSummary(acquiredCerts);

    const SkeletonCard = () => (
        <div className="p-6 rounded-[2rem] bg-slate-900/40 border border-slate-800/50 animate-pulse flex items-center justify-between">
            <div className="flex items-center gap-6">
                <div className="w-14 h-14 rounded-2xl bg-slate-800" />
                <div className="space-y-2">
                    <div className="h-5 w-40 bg-slate-800 rounded" />
                    <div className="h-3 w-24 bg-slate-800/80 rounded" />
                </div>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-slate-950 px-4 py-12">
            <div className="max-w-6xl mx-auto space-y-12">

                {/* 1. Header & Profile Summary */}
                <div className="relative group p-8 rounded-[3rem] bg-gradient-to-br from-slate-900/60 to-slate-800/20 border border-slate-700/30 backdrop-blur-3xl overflow-hidden shadow-2xl">
                    <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-500/10 rounded-full blur-[120px] -mr-64 -mt-64 transition-all group-hover:bg-blue-500/15 duration-1000" />
                    <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-indigo-500/5 rounded-full blur-[100px] -ml-48 -mb-48" />

                    <div className="flex flex-col md:flex-row items-center md:items-start gap-10 relative z-10">
                        {/* Avatar Section */}
                        <div className="relative">
                            <div className="w-36 h-36 rounded-[2.5rem] bg-gradient-to-br from-blue-600 to-indigo-600 p-1.5 shadow-2xl shadow-blue-500/30 group-hover:scale-105 group-hover:rotate-3 transition-all duration-700">
                                <div className="w-full h-full rounded-[2.2rem] bg-slate-950 flex items-center justify-center border border-white/10 overflow-hidden">
                                    <User className="w-20 h-20 text-white opacity-90" />
                                </div>
                            </div>
                            <div className="absolute -bottom-2 -right-2 bg-emerald-500 w-10 h-10 rounded-full border-[6px] border-slate-950 flex items-center justify-center shadow-lg">
                                <span className="block w-2.5 h-2.5 bg-white rounded-full animate-pulse" />
                            </div>
                        </div>

                        {/* User Basic Info */}
                        <div className="flex-1 space-y-6 text-center md:text-left">
                            <div className="space-y-2">
                                <div className="flex items-center justify-center md:justify-start gap-4 flex-wrap">
                                    <h1 className="text-5xl font-black tracking-tighter bg-gradient-to-r from-white via-blue-50 to-slate-400 bg-clip-text text-transparent">
                                        {profile?.nickname || user.user_metadata?.nickname || user.user_metadata?.userid || user.email?.split('@')[0]}
                                    </h1>
                                    <Dialog open={isSettingsOpen} onOpenChange={(open) => { setIsSettingsOpen(open); if (!open) setNicknameError(null); }}>
                                        <DialogTrigger asChild>
                                            <Button variant="ghost" size="icon" className="text-slate-500 hover:text-blue-400 hover:bg-blue-500/10 rounded-full transition-all">
                                                <Settings className="w-5 h-5" />
                                            </Button>
                                        </DialogTrigger>
                                        <DialogContent className="bg-slate-900 border-slate-800 text-slate-100 sm:max-w-[425px] rounded-[2rem]">
                                            <DialogHeader>
                                                <DialogTitle className="text-2xl font-black tracking-tight text-white">프로필 설정</DialogTitle>
                                                <DialogDescription className="text-sm text-slate-400 mt-1 font-medium italic">
                                                    회원님의 닉네임과 전공 정보를 관리합니다.
                                                </DialogDescription>
                                            </DialogHeader>
                                            <form onSubmit={handleUpdateProfile} className="space-y-6 py-4">
                                                <div className="space-y-4">
                                                    <div className="space-y-2">
                                                        <Label htmlFor="nickname" className="text-xs font-bold text-slate-500 uppercase tracking-widest px-1">닉네임</Label>
                                                        <Input
                                                            id="nickname"
                                                            value={nickname}
                                                            onChange={(e) => {
                                                                setNickname(e.target.value);
                                                                setNicknameError(null);
                                                            }}
                                                            className={`bg-slate-950 rounded-2xl h-12 text-slate-200 focus:ring-blue-500/20 ${nicknameError ? 'border-red-500/60 focus-visible:ring-red-500/30' : 'border-slate-800'}`}
                                                            placeholder="사용할 닉네임 입력"
                                                        />
                                                        {nicknameError && (
                                                            <p className="text-xs text-red-400 font-medium px-1 mt-1">{nicknameError}</p>
                                                        )}
                                                    </div>
                                                    <div className="space-y-2 relative">
                                                        <Label htmlFor="major" className="text-xs font-bold text-slate-500 uppercase tracking-widest px-1">전공</Label>
                                                        <div className="relative">
                                                            <Input
                                                                id="major"
                                                                value={userMajor}
                                                                onChange={(e) => {
                                                                    setUserMajor(e.target.value);
                                                                    setShowMajorSuggestions(true);
                                                                }}
                                                                onFocus={() => setShowMajorSuggestions(true)}
                                                                onBlur={() => setTimeout(() => setShowMajorSuggestions(false), 200)}
                                                                className="bg-slate-950 border-slate-800 rounded-2xl h-12 text-slate-200 focus:ring-blue-500/20"
                                                                placeholder="전공 검색 및 입력"
                                                                autoComplete="off"
                                                            />
                                                            {showMajorSuggestions && userMajor.length > 0 && (
                                                                <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-[100] max-h-48 overflow-y-auto">
                                                                    {availableMajors
                                                                        .filter(m => m.toLowerCase().includes(userMajor.toLowerCase()))
                                                                        .slice(0, 10)
                                                                        .map(m => (
                                                                            <div
                                                                                key={m}
                                                                                onMouseDown={() => {
                                                                                    setUserMajor(m);
                                                                                    setShowMajorSuggestions(false);
                                                                                }}
                                                                                className="px-4 py-3 hover:bg-slate-800 cursor-pointer text-sm text-slate-300 border-b border-slate-800/50 last:border-0 transition-colors font-medium"
                                                                            >
                                                                                {m}
                                                                            </div>
                                                                        ))
                                                                    }
                                                                </div>
                                                            )}
                                                        </div>
                                                        {/* 인기 전공 태그 */}
                                                        <div className="mt-3 space-y-1 px-1">
                                                            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">인기 전공</p>
                                                            <div className="flex flex-wrap gap-2">
                                                                {popularMajors.map((m) => (
                                                                    <button
                                                                        key={m}
                                                                        type="button"
                                                                        onClick={() => {
                                                                            setUserMajor(m);
                                                                            setShowMajorSuggestions(false);
                                                                        }}
                                                                        className="px-3 h-7 rounded-full bg-slate-900 border border-slate-800 text-[11px] text-slate-300 hover:bg-slate-800 hover:text-blue-400 transition-colors"
                                                                    >
                                                                        {m}
                                                                    </button>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div className="space-y-3">
                                                        <Label className="text-xs font-bold text-slate-500 uppercase tracking-widest px-1">학년 / 상태</Label>
                                                        <div className="flex flex-wrap gap-2">
                                                            {[0, 1, 2, 3, 4].map((year) => (
                                                                <button
                                                                    key={year}
                                                                    type="button"
                                                                    onClick={() => setGradeYear(year)}
                                                                    className={`flex-1 min-w-[60px] h-10 rounded-xl font-bold text-sm transition-all border ${gradeYear === year
                                                                        ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-500/20'
                                                                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                                                                        }`}
                                                                >
                                                                    {year === 0 ? 'None' : `${year}학년`}
                                                                </button>
                                                            ))}
                                                        </div>
                                                        <p className="text-[10px] text-slate-500 italic px-1 font-medium">대학 미진학/졸업은 'None'을 선택하세요.</p>
                                                    </div>
                                                </div>
                                                <DialogFooter>
                                                    <Button type="button" variant="ghost" onClick={() => setIsSettingsOpen(false)} className="rounded-2xl font-bold text-slate-400">취소</Button>
                                                    <Button type="submit" disabled={isUpdating} className="bg-blue-600 hover:bg-blue-700 text-white rounded-2xl px-6 font-bold shadow-lg shadow-blue-500/20">
                                                        {isUpdating ? '저장 중...' : '저장하기'}
                                                    </Button>
                                                </DialogFooter>
                                            </form>
                                        </DialogContent>
                                    </Dialog>
                                </div>
                                <p className="text-slate-400 flex items-center justify-center md:justify-start gap-2 text-base font-medium opacity-70">
                                    <Mail className="w-4 h-4 text-blue-400" /> {user.email}
                                </p>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
                                <div className="p-5 rounded-3xl bg-white/[0.02] border border-white/5 backdrop-blur-md flex flex-col gap-1 group/item hover:bg-white/[0.05] hover:border-blue-500/30 transition-all duration-500">
                                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Major</p>
                                    <div className="flex items-center gap-3">
                                        <School className="w-5 h-5 text-blue-400" />
                                        <p className="text-lg font-bold text-slate-200">{profile?.detail_major || user.user_metadata?.detail_major || '미설정'}</p>
                                    </div>
                                </div>
                                <div className="p-5 rounded-3xl bg-white/[0.02] border border-white/5 backdrop-blur-md flex flex-col gap-1 group/item hover:bg-white/[0.05] hover:border-purple-500/30 transition-all duration-500">
                                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Academic Level</p>
                                    <div className="flex items-center gap-3">
                                        <Award className="w-5 h-5 text-purple-400" />
                                        <p className="text-lg font-bold text-slate-200">
                                            {(() => {
                                                const gy = profile?.grade_year !== undefined ? profile.grade_year : user.user_metadata?.grade_year;
                                                return gy === 0 || gy === null || gy === undefined ? 'None' : `${gy}학년`;
                                            })()}
                                        </p>
                                    </div>
                                </div>
                                <div
                                    className="p-5 rounded-3xl bg-white/[0.02] border border-white/5 backdrop-blur-md flex flex-col gap-1 group/item hover:bg-white/[0.05] hover:border-emerald-500/30 transition-all duration-500 cursor-pointer"
                                    onClick={() => router.navigate('/certs?filter=bookmarks')}
                                >
                                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Saved Certs</p>
                                    <div className="flex items-center gap-3">
                                        <Bookmark className="w-5 h-5 text-emerald-400" />
                                        <p className="text-lg font-bold text-slate-200">{favorites.length}개</p>
                                    </div>
                                </div>
                                <Dialog open={isAcquiredDialogOpen} onOpenChange={(open) => {
                                    setIsAcquiredDialogOpen(open);
                                    if (!open) setCertSearchQuery('');
                                }}>
                                    <div
                                        className="p-5 rounded-3xl backdrop-blur-md flex flex-col gap-2 group/item transition-all duration-500 cursor-pointer"
                                        style={{
                                            background: effectiveSummary ? getTierMeta(effectiveSummary.tier).bg : 'rgba(255,255,255,0.02)',
                                            border: `1px solid ${effectiveSummary ? getTierMeta(effectiveSummary.tier).border : 'rgba(255,255,255,0.05)'}`,
                                        }}
                                        onClick={() => setIsAcquiredDialogOpen(true)}
                                    >
                                        <div className="flex items-center justify-between">
                                            <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Acquired Certs</p>
                                            <span className="text-xs text-slate-500 font-bold">{acquiredCerts.length}개</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-2xl">{effectiveSummary ? getTierMeta(effectiveSummary.tier).gem : '🥉'}</span>
                                            <div className="flex-1 min-w-0">
                                                {effectiveSummary ? (
                                                    <XpProgressBar summary={effectiveSummary} />
                                                ) : (
                                                    <p className="text-sm font-bold text-slate-400">자격증을 추가하세요</p>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <DialogContent className="bg-slate-900 border-slate-800 text-slate-100 sm:max-w-lg rounded-[2rem] max-h-[85vh] flex flex-col">
                                        <DialogHeader>
                                            <DialogTitle className="text-xl font-black text-white">취득 자격증 관리</DialogTitle>
                                            <DialogDescription className="text-sm text-slate-400">
                                                DB 자격증 목록에서 검색해 취득한 자격증을 추가하세요.
                                                {effectiveSummary && (
                                                    <span className="ml-2 font-bold" style={{ color: getTierMeta(effectiveSummary.tier).color }}>
                                                        {getTierMeta(effectiveSummary.tier).gem} {effectiveSummary.tier} Lv.{effectiveSummary.level} · {Math.round(effectiveSummary.total_xp)} XP
                                                    </span>
                                                )}
                                            </DialogDescription>
                                        </DialogHeader>
                                        <div className="space-y-4 flex-1 overflow-hidden flex flex-col min-h-0">
                                            <div>
                                                <Label className="text-slate-400 text-xs font-bold uppercase">자격증 검색</Label>
                                                <Input
                                                    placeholder="자격증명 2글자 이상 입력 (예: SQLD)"
                                                    value={certSearchQuery}
                                                    onChange={(e) => setCertSearchQuery(e.target.value)}
                                                    className="mt-1.5 bg-slate-800 border-slate-700"
                                                />
                                                {certSearchQuery.trim().length > 0 && certSearchQuery.trim().length < 2 && (
                                                    <p className="text-[10px] text-slate-500 mt-1">2글자 이상 입력하면 검색됩니다.</p>
                                                )}
                                            </div>
                                            <div className="flex-1 overflow-y-auto space-y-2 min-h-0">
                                                {certSearchLoading && <p className="text-slate-500 text-sm">검색 중...</p>}
                                                {certSearchQuery.trim() && certSearchResults.length > 0 && (
                                                    <div className="space-y-1">
                                                        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">검색 결과에서 추가</p>
                                                        {certSearchResults.map((cert: any) => {
                                                            const already = acquiredCerts.some((a: any) => a.qual_id === cert.qual_id);
                                                            return (
                                                                <div key={cert.qual_id} className="flex items-center justify-between py-2 px-3 rounded-xl bg-slate-800/50 border border-slate-700/50">
                                                                    <span className="text-sm font-medium text-slate-200 truncate">{cert.qual_name}</span>
                                                                    <Button
                                                                        size="sm"
                                                                        className="rounded-lg h-8"
                                                                        disabled={already}
                                                                        onClick={async () => {
                                                                            if (!token || already) return;
                                                                            try {
                                                                                await addAcquiredCert(cert.qual_id, token);
                                                                                toast.success('추가되었습니다.');
                                                                                const [r, s] = await Promise.all([
                                                                                    getAcquiredCerts(token, 1, 200),
                                                                                    getAcquiredCertsSummary(token).catch(() => null),
                                                                                ]);
                                                                                setAcquiredCerts(r.items);
                                                                                setXpSummary(s);
                                                                            } catch (e: any) {
                                                                                toast.error(e?.message || '추가 실패');
                                                                            }
                                                                        }}
                                                                    >
                                                                        {already ? '추가됨' : <><PlusCircle className="w-4 h-4 mr-1" />추가</>}
                                                                    </Button>
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                )}
                                                <div className="space-y-1 pt-2 border-t border-slate-800">
                                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">내 취득 자격증 ({acquiredCerts.length})</p>
                                                    {acquiredCerts.length === 0 ? (
                                                        <p className="text-slate-500 text-sm py-2">추가된 자격증이 없습니다. 위에서 검색해 추가하세요.</p>
                                                    ) : (
                                                        acquiredCerts.map((a: any) => (
                                                            <div key={a.acq_id} className="flex items-center justify-between py-2 px-3 rounded-xl bg-slate-800/30 border border-slate-700/30">
                                                                <span className="text-sm font-medium text-slate-200 truncate">{a.qualification?.qual_name ?? a.qual_id}</span>
                                                                <Button
                                                                    size="sm"
                                                                    variant="ghost"
                                                                    className="text-slate-500 hover:text-red-400 h-8 rounded-lg"
                                                                    onClick={async () => {
                                                                        if (!token) return;
                                                                        try {
                                                                            await removeAcquiredCert(a.qual_id, token);
                                                                            const [r, s] = await Promise.all([
                                                                                getAcquiredCerts(token, 1, 200),
                                                                                getAcquiredCertsSummary(token).catch(() => null),
                                                                            ]);
                                                                            setAcquiredCerts(r.items);
                                                                            setXpSummary(s);
                                                                            toast.success('제거되었습니다.');
                                                                        } catch (e: any) {
                                                                            toast.error(e?.message || '제거 실패');
                                                                        }
                                                                    }}
                                                                >
                                                                    <X className="w-4 h-4" />
                                                                </Button>
                                                            </div>
                                                        ))
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </DialogContent>
                                </Dialog>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 2. Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                    {/* Left: Favorites & History */}
                    <div className="lg:col-span-2 space-y-10">

                        {/* Favorites Section */}
                        <section className="space-y-6">
                            <div className="flex items-center justify-between px-2">
                                <h2 className="text-2xl font-black text-slate-100 flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-2xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                                        <Bookmark className="w-5 h-5 text-blue-400" />
                                    </div>
                                    내 관심 자격증
                                </h2>
                                <Button
                                    variant="ghost"
                                    className="text-xs font-bold text-slate-500 hover:text-white uppercase tracking-widest"
                                    onClick={() => router.navigate('/certs?filter=bookmarks')}
                                >
                                    View All <ChevronRight className="ml-1 w-3 h-3" />
                                </Button>
                            </div>

                            <div className="grid gap-4">
                                {dataLoading ? (
                                    [1, 2].map((i) => <SkeletonCard key={i} />)
                                ) : favorites.length > 0 ? (
                                    favorites.map((cert) => (
                                        <div
                                            key={cert.qual_id}
                                            onClick={() => router.navigate(`/certs/${cert.qual_id}`)}
                                            className="group p-6 rounded-[2rem] bg-slate-900/40 border border-slate-800/50 hover:border-blue-500/40 hover:bg-slate-800/60 transition-all duration-500 cursor-pointer flex items-center justify-between shadow-lg"
                                        >
                                            <div className="flex items-center gap-6">
                                                <div className="w-14 h-14 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-400 group-hover:scale-110 group-hover:rotate-3 transition-all">
                                                    <Award className="w-7 h-7" />
                                                </div>
                                                <div>
                                                    <h3 className="text-lg font-black text-slate-100 group-hover:text-blue-400 transition-colors tracking-tight">{cert.qual_name}</h3>
                                                    <div className="flex gap-2 items-center mt-1">
                                                        <Badge variant="outline" className="text-[9px] border-slate-800 text-slate-500 uppercase">{cert.main_field}</Badge>
                                                        <Badge variant="outline" className="text-[9px] border-slate-800 text-slate-500 uppercase">{cert.qual_type}</Badge>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <div className="hidden sm:block text-right">
                                                    <p className="text-[9px] font-bold text-slate-600 uppercase tracking-tighter">Status</p>
                                                    <p className="text-xs font-bold text-blue-400 uppercase">Tracked</p>
                                                </div>
                                                <div className="w-10 h-10 rounded-full bg-slate-950/50 flex items-center justify-center text-slate-700 group-hover:text-blue-400 group-hover:bg-blue-500/10 transition-all">
                                                    <ChevronRight className="w-5 h-5" />
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="p-16 rounded-[3rem] bg-slate-900/10 border border-dashed border-slate-800/50 flex flex-col items-center justify-center text-center space-y-6">
                                        <div className="w-16 h-16 rounded-[2rem] bg-slate-900 flex items-center justify-center">
                                            <Bookmark className="w-8 h-8 text-slate-700" />
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-slate-200 font-bold">관심 목록이 비어있습니다</p>
                                            <p className="text-slate-500 text-sm">마음에 드는 자격증을 저장하고 관리해보세요.</p>
                                        </div>
                                        <Button variant="outline" className="rounded-2xl border-slate-800 text-slate-400 font-bold hover:bg-slate-900" onClick={() => router.navigate('/certs')}>자격증 탐색하기</Button>
                                    </div>
                                )}
                            </div>
                        </section>

                        {/* Recent History Section */}
                        <section className="space-y-6">
                            <div className="flex items-center justify-between px-2">
                                <h2 className="text-2xl font-black text-slate-100 flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                                        <History className="w-5 h-5 text-indigo-400" />
                                    </div>
                                    최근 본 자격증
                                </h2>
                            </div>

                            <div className="grid gap-4">
                                {dataLoading ? (
                                    [1, 2].map((i) => <SkeletonCard key={`recent-${i}`} />)
                                ) : recentCerts.length > 0 ? (
                                    recentCerts.map((cert) => (
                                        <div
                                            key={cert.qual_id}
                                            onClick={() => router.navigate(`/certs/${cert.qual_id}`)}
                                            className="group p-6 rounded-[2rem] bg-slate-900/40 border border-slate-800/50 hover:border-indigo-500/40 hover:bg-slate-800/60 transition-all duration-500 cursor-pointer flex items-center justify-between"
                                        >
                                            <div className="flex items-center gap-6">
                                                <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition-all">
                                                    <Search className="w-7 h-7" />
                                                </div>
                                                <div>
                                                    <h3 className="text-lg font-black text-slate-100 group-hover:text-indigo-400 transition-colors tracking-tight">{cert.qual_name}</h3>
                                                    <p className="text-xs text-slate-500 font-bold mt-1 uppercase tracking-tight opacity-70">{cert.main_field} · {cert.qual_type}</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <Badge variant="outline" className="hidden sm:inline-flex text-[9px] border-slate-800 text-slate-600 font-black uppercase tracking-widest px-2 py-0.5">Retrieved</Badge>
                                                <ChevronRight className="w-5 h-5 text-slate-700 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all" />
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="p-12 rounded-[3rem] bg-slate-900/10 border border-dashed border-slate-800/30 flex flex-col items-center justify-center text-center space-y-4">
                                        <History className="w-10 h-10 text-slate-800" />
                                        <p className="text-slate-600 text-sm font-bold">최근 확인한 자격증 정보가 없습니다.</p>
                                    </div>
                                )}
                            </div>
                        </section>
                    </div>

                    {/* Right: Recommendations */}
                    <aside className="space-y-8">
                        <div className="p-1.5 rounded-[3.5rem] bg-gradient-to-b from-amber-500/20 to-transparent">
                            <div className="bg-slate-950/80 backdrop-blur-3xl rounded-[3.2rem] p-8 space-y-8 border border-white/5 shadow-2xl">
                                <div className="space-y-6">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 rounded-2xl bg-amber-500/20 flex items-center justify-center text-amber-500 border border-amber-500/30 shadow-[0_0_20px_rgba(245,158,11,0.2)]">
                                            <Sparkles className="w-6 h-6 animate-pulse" />
                                        </div>
                                        <div>
                                            <h2 className="text-xl font-black text-white tracking-tighter">전공 맞춤 추천</h2>
                                            <p className="text-[10px] font-bold text-amber-500/70 uppercase tracking-widest">Tailored for you</p>
                                        </div>
                                    </div>

                                    <div className="space-y-4 max-h-[460px] overflow-y-auto pr-2 custom-scrollbar">
                                        {dataLoading ? (
                                            [1, 2, 3, 4].map((i) => (
                                                <div key={i} className="p-5 rounded-3xl bg-white/[0.02] border border-white/5 animate-pulse">
                                                    <div className="h-4 w-16 bg-slate-800 rounded mb-3" />
                                                    <div className="h-4 w-full bg-slate-800 rounded mb-1" />
                                                    <div className="h-3 w-3/4 bg-slate-800/80 rounded" />
                                                </div>
                                            ))
                                        ) : recommendations.length > 0 ? (
                                            recommendations.map((item) => (
                                                <div
                                                    key={item.qual_id}
                                                    onClick={() => router.navigate(`/certs/${item.qual_id}`)}
                                                    className="p-5 rounded-3xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] hover:border-amber-500/40 hover:shadow-[0_10px_30px_rgba(245,158,11,0.05)] transition-all group cursor-pointer"
                                                >
                                                    <div className="flex justify-between items-start mb-3">
                                                        <Badge variant="outline" className="text-[8px] border-amber-500/30 text-amber-500 font-black uppercase tracking-widest px-2 py-0">Strategic</Badge>
                                                        <div className="text-amber-500 opacity-20 group-hover:opacity-100 transition-opacity">
                                                            <Award className="w-4 h-4" />
                                                        </div>
                                                    </div>
                                                    <h3 className="text-base font-black text-slate-100 mb-1 group-hover:text-amber-400 transition-colors truncate tracking-tight">{item.qual_name}</h3>
                                                    <p className="text-[10px] text-slate-500 font-bold opacity-70">
                                                        "{user.user_metadata?.detail_major}" 추천 자격증
                                                    </p>
                                                </div>
                                            ))
                                        ) : (
                                            <div className="p-10 rounded-[2.5rem] bg-white/[0.01] border border-dashed border-white/10 flex flex-col items-center justify-center text-center space-y-4">
                                                <div className="w-12 h-12 rounded-full bg-slate-900 flex items-center justify-center">
                                                    <Target className="w-6 h-6 text-slate-800" />
                                                </div>
                                                <p className="text-slate-600 text-xs font-bold leading-relaxed px-4">전공 정보를 설정하면<br />맞춤 추천을 분석합니다.</p>
                                                <Button
                                                    variant="ghost"
                                                    className="text-amber-500 hover:text-amber-400 text-xs font-black underline underline-offset-4"
                                                    onClick={() => router.navigate('/recommendations')}
                                                >
                                                    Analysis Start
                                                </Button>
                                            </div>
                                        )}
                                    </div>

                                    <Button
                                        onClick={() => router.navigate('/ai-recommendations')}
                                        className="w-full bg-amber-500 hover:bg-amber-400 text-slate-950 font-black rounded-3xl py-7 shadow-xl shadow-amber-500/20 active:scale-[0.98] transition-all uppercase tracking-widest text-[11px]"
                                    >
                                        AI 심화 추천 받기
                                    </Button>
                                </div>
                            </div>
                        </div>

                        {/* 내가 취득한 자격증 카드 */}
                        {(() => {
                            const tierMeta = getTierMeta(effectiveSummary?.tier ?? null);
                            return (
                                <div
                                    className="rounded-[3rem] overflow-hidden"
                                    style={{ background: `linear-gradient(160deg, ${tierMeta.bg} 0%, rgba(15,15,25,0.95) 100%)`, border: `1px solid ${tierMeta.border}` }}
                                >
                                    <div className="p-8 space-y-5">
                                        {/* Header */}
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <span className="text-2xl">{effectiveSummary ? tierMeta.gem : '🥉'}</span>
                                                <div>
                                                    <h3 className="text-white font-black tracking-tight text-base leading-tight">내가 취득한 자격증</h3>
                                                    <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: tierMeta.color }}>
                                                        {effectiveSummary ? `${effectiveSummary.tier} · Lv.${effectiveSummary.level}` : 'Bronze · Lv.1'}
                                                    </p>
                                                </div>
                                            </div>
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                className="text-xs font-bold uppercase tracking-widest text-slate-500 hover:text-white"
                                                onClick={() => setIsAcquiredDialogOpen(true)}
                                            >
                                                관리 +
                                            </Button>
                                        </div>

                                        {/* XP 게이지 - 항상 표시 */}
                                        {effectiveSummary ? (
                                            <div className="space-y-1.5">
                                                <div className="h-2 rounded-full bg-slate-800/80 overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full transition-all duration-700"
                                                        style={{
                                                            width: effectiveSummary.next_level_xp == null ? '100%' :
                                                                `${Math.min(100, ((effectiveSummary.total_xp - effectiveSummary.current_level_xp) / (effectiveSummary.next_level_xp - effectiveSummary.current_level_xp)) * 100)}%`,
                                                            background: `linear-gradient(90deg, ${tierMeta.color}99, ${tierMeta.color})`,
                                                            boxShadow: `0 0 8px ${tierMeta.color}88`,
                                                        }}
                                                    />
                                                </div>
                                                <div className="flex justify-between items-center">
                                                    <span className="text-[10px] text-slate-500 font-bold">총 {Math.round(effectiveSummary.total_xp)} XP · {effectiveSummary.cert_count}개</span>
                                                    <span className="text-[10px] font-bold" style={{ color: tierMeta.color }}>
                                                        {effectiveSummary.next_level_xp == null ? 'MAX LEVEL' : `다음 Lv: ${effectiveSummary.next_level_xp} XP`}
                                                    </span>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="h-2 rounded-full bg-slate-800/80" />
                                        )}

                                        {/* 취득 자격증 목록 */}
                                        <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1 custom-scrollbar">
                                            {dataLoading ? (
                                                [1, 2].map((i) => (
                                                    <div key={i} className="h-12 rounded-2xl bg-white/[0.03] border border-white/5 animate-pulse" />
                                                ))
                                            ) : acquiredCerts.length > 0 ? (
                                                acquiredCerts.map((cert) => {
                                                    const diff = (cert.qualification as any)?.avg_difficulty ?? null;
                                                    // avg_difficulty가 있으면 프론트에서 직접 계산 (백엔드 미배포 폴백)
                                                    const xp = diff != null ? calcXpFromDiff(diff) : (cert.xp && cert.xp !== 3 ? cert.xp : 3.0);
                                                    return (
                                                        <div
                                                            key={cert.acq_id}
                                                            className="flex items-center justify-between px-4 py-3 rounded-2xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.06] transition-all group cursor-pointer"
                                                            onClick={() => router.navigate(`/certs/${cert.qual_id}`)}
                                                        >
                                                            <div className="flex items-center gap-3 min-w-0">
                                                                <Award className="w-4 h-4 flex-shrink-0" style={{ color: tierMeta.color }} />
                                                                <span className="text-sm font-bold text-slate-200 truncate group-hover:text-white transition-colors">
                                                                    {cert.qualification?.qual_name ?? `자격증 #${cert.qual_id}`}
                                                                </span>
                                                            </div>
                                                            <div className="flex items-center gap-2 flex-shrink-0">
                                                                {diff != null && (
                                                                    <span className="text-[9px] font-bold text-slate-600 hidden sm:block">난이도 {diff}</span>
                                                                )}
                                                                <span
                                                                    className="text-[10px] font-black px-2 py-0.5 rounded-full"
                                                                    style={{ background: `${tierMeta.color}20`, color: tierMeta.color, border: `1px solid ${tierMeta.color}40` }}
                                                                >
                                                                    +{xp} XP
                                                                </span>
                                                            </div>
                                                        </div>
                                                    );
                                                })
                                            ) : (
                                                <div className="py-8 flex flex-col items-center gap-3 text-center">
                                                    <span className="text-3xl opacity-30">🏆</span>
                                                    <p className="text-slate-500 text-xs font-bold">아직 취득한 자격증이 없습니다.</p>
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        className="text-xs font-bold"
                                                        style={{ color: tierMeta.color }}
                                                        onClick={() => setIsAcquiredDialogOpen(true)}
                                                    >
                                                        + 자격증 추가하기
                                                    </Button>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })()}
                    </aside>
                </div>
            </div>
        </div>
    );
}
