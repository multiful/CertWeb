import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from '@/lib/router';
import { useMajors } from '@/hooks/useRecommendations';
import {
    User, Bookmark, History, ChevronRight,
    Mail, School, Award, Sparkles,
    Search, Settings
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
import { getFavorites, getRecentViewed, getRecommendations, updateProfile } from '@/lib/api';
import { toast } from 'sonner';

// Re-importing missing icons (added Activity, Target)
const Target = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></svg>
);

export function MyPage() {
    const { user, token, loading: authLoading } = useAuth();
    const router = useRouter();
    const [favorites, setFavorites] = useState<any[]>([]);
    const [recentCerts, setRecentCerts] = useState<any[]>([]);
    const [recommendations, setRecommendations] = useState<any[]>([]);

    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [nickname, setNickname] = useState('');
    const [userMajor, setUserMajor] = useState('');
    const [gradeYear, setGradeYear] = useState<number | null>(null);
    const [isUpdating, setIsUpdating] = useState(false);

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

    const loadData = async () => {
        try {
            if (token) {
                const favRes = await getFavorites(token, 1, 5);
                setFavorites(favRes.items.map((f: any) => f.qualification));

                const recentData = await getRecentViewed(token);
                setRecentCerts(recentData);
            }

            const major = user?.user_metadata?.detail_major;
            if (major) {
                const recRes = await getRecommendations(major, 20);
                setRecommendations(recRes.items || []);
            }
        } catch (err: any) {
            console.error('Failed to load mypage data:', err);
        }
    };

    const handleUpdateProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;

        setIsUpdating(true);
        try {
            await updateProfile(token, {
                nickname: nickname,
                detail_major: userMajor,
                grade_year: gradeYear === null ? 0 : gradeYear
            });
            toast.success('프로필이 업데이트되었습니다.');
            setIsSettingsOpen(false);
            // Refresh local state or force reload
            window.location.reload();
        } catch (err: any) {
            toast.error(err.message || '프로필 업데이트에 실패했습니다.');
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

        loadData();
    }, [user, token, router, authLoading]);

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
                                        {user.user_metadata?.nickname || user.user_metadata?.userid || user.email?.split('@')[0]}
                                    </h1>
                                    <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
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
                                                            onChange={(e) => setNickname(e.target.value)}
                                                            className="bg-slate-950 border-slate-800 rounded-2xl h-12 text-slate-200 focus:ring-blue-500/20"
                                                            placeholder="사용할 닉네임 입력"
                                                        />
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

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                                <div className="p-5 rounded-3xl bg-white/[0.02] border border-white/5 backdrop-blur-md flex flex-col gap-1 group/item hover:bg-white/[0.05] hover:border-blue-500/30 transition-all duration-500">
                                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Major</p>
                                    <div className="flex items-center gap-3">
                                        <School className="w-5 h-5 text-blue-400" />
                                        <p className="text-lg font-bold text-slate-200">{user.user_metadata?.detail_major || '미설정'}</p>
                                    </div>
                                </div>
                                <div className="p-5 rounded-3xl bg-white/[0.02] border border-white/5 backdrop-blur-md flex flex-col gap-1 group/item hover:bg-white/[0.05] hover:border-purple-500/30 transition-all duration-500">
                                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Academic Level</p>
                                    <div className="flex items-center gap-3">
                                        <Award className="w-5 h-5 text-purple-400" />
                                        <p className="text-lg font-bold text-slate-200">
                                            {user.user_metadata?.grade_year === 0 || !user.user_metadata?.grade_year ? 'None' : `${user.user_metadata.grade_year}학년`}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Premium CTA */}
                        <div className="md:self-start lg:pt-2">
                            <Button
                                onClick={() => router.navigate('/recommendations')}
                                className="bg-white text-slate-950 hover:bg-blue-50 rounded-[2rem] px-8 py-8 h-auto font-black text-sm uppercase tracking-widest shadow-[0_20px_40px_rgba(255,255,255,0.1)] transition-all active:scale-95 flex items-center gap-4 group/btn overflow-hidden relative"
                            >
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover/btn:translate-x-full transition-transform duration-1000" />
                                <Sparkles className="w-6 h-6 text-blue-600 animate-pulse" />
                                <span>Career Report</span>
                                <ChevronRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
                            </Button>
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
                                {favorites.length > 0 ? (
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
                                {recentCerts.length > 0 ? (
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
                                        {recommendations.length > 0 ? (
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

                        {/* Quick Analytics Card */}
                        <div className="p-8 rounded-[3rem] bg-gradient-to-br from-blue-600/20 to-indigo-600/10 border border-blue-500/20 space-y-6 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/20 rounded-full blur-3xl -mr-16 -mt-16 group-hover:bg-blue-500/30 transition-all duration-1000" />
                            <h3 className="text-white font-black tracking-tight leading-tight text-xl relative z-10">더 정교한 실시간 데이터가 필요하신가요?</h3>
                            <p className="text-slate-400 text-sm leading-relaxed relative z-10 opacity-80">전국 1000여개 자격증의<br />실시간 합격률 트렌드를 분석하세요.</p>
                            <Button
                                variant="outline"
                                className="w-full rounded-2xl border-blue-500/30 bg-blue-500/10 text-blue-400 font-black text-xs uppercase tracking-widest hover:bg-blue-500/20 hover:text-white transition-all relative z-10"
                                onClick={() => router.navigate('/certs')}
                            >
                                Explorer Directory
                            </Button>
                        </div>
                    </aside>
                </div>
            </div>
        </div>
    );
}
