import React, { useState } from 'react';
import { User, LogIn, LogOut, ChevronDown, Bookmark, Activity, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { supabase } from '@/lib/supabase';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';
import { checkUserId } from '@/lib/api';
import { useRouter } from '@/lib/router';
import { useMajors } from '@/hooks/useRecommendations';

export function UserMenu() {
    const router = useRouter();
    const { user, signOut } = useAuth();
    const [isLoginOpen, setIsLoginOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [isSignUp, setIsSignUp] = useState(false);
    const [signupStep, setSignupStep] = useState(1); // 1: Email, 2: Code + Details
    const [showMajorSuggestions, setShowMajorSuggestions] = useState(false);
    const { majors: availableMajors } = useMajors();

    // Form States
    const [email, setEmail] = useState('');
    const [userid, setUserid] = useState('');
    const [password, setPassword] = useState('');
    const [passwordConfirm, setPasswordConfirm] = useState('');
    const [name, setName] = useState('');
    const [birthDate, setBirthDate] = useState('');
    const [major, setMajor] = useState('');
    const [verificationCode, setVerificationCode] = useState('');
    const [isIdAvailable, setIsIdAvailable] = useState<boolean | null>(null);

    const API_BASE = import.meta.env.VITE_API_BASE_URL ||
        (import.meta as any).env?.VITE_API_BASE_URL ||
        (import.meta as any).env?.NEXT_PUBLIC_API_URL ||
        'https://certweb-xzpx.onrender.com/api/v1';

    const handleSendOTP = async () => {
        if (!email) return toast.error('이메일을 입력해주세요.');
        setLoading(true);
        try {
            // Use Supabase native OTP sending
            const { error } = await supabase.auth.signInWithOtp({
                email,
                options: {
                    shouldCreateUser: true,
                }
            });

            if (error) throw error;

            toast.success('인증 코드가 발송되었습니다. (코드가 아닌 링크가 오면 Supabase 설정에서 전송 방식을 Token으로 바꿔야 합니다)');
            setSignupStep(2);
        } catch (error: any) {
            toast.error(error.message || '인증 코드 발송 실패');
        } finally {
            setLoading(false);
        }
    };

    const handleCheckUserId = async () => {
        if (!userid) return toast.error('아이디를 입력해주세요.');
        if (userid.length < 4) return toast.error('아이디는 최소 4자 이상이어야 합니다.');

        setLoading(true);
        try {
            const result = await checkUserId(userid);
            if (result.available) {
                setIsIdAvailable(true);
                toast.success(result.message);
            } else {
                setIsIdAvailable(false);
                toast.error(result.message);
            }
        } catch (error: any) {
            toast.error(error.message || '아이디 중복 확인 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const handleSignupCompleteWithVerify = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!verificationCode) return toast.error('인증 코드를 입력해주세요.');
        if (password !== passwordConfirm) return toast.error('비밀번호가 일치하지 않습니다.');
        if (isIdAvailable !== true) return toast.error('아이디 중복 확인을 해주세요.');

        setLoading(true);
        try {
            // 1. Verify OTP using Supabase SDK
            const { error: verifyError } = await supabase.auth.verifyOtp({
                email,
                token: verificationCode,
                type: 'email'
            });

            if (verifyError) {
                // Try 'signup' type as fallback
                const { error: retryError } = await supabase.auth.verifyOtp({
                    email,
                    token: verificationCode,
                    type: 'signup'
                });
                if (retryError) throw retryError;
            }

            // 2. Finalize registration via Backend
            const { data: { session } } = await supabase.auth.getSession();
            const token = session?.access_token;

            const signupRes = await fetch(`${API_BASE}/auth/signup-complete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    name,
                    userid,
                    email,
                    password,
                    password_confirm: passwordConfirm,
                    birth_date: birthDate,
                    detail_major: major
                })
            });
            const signupData = await signupRes.json();
            if (!signupRes.ok) throw new Error(typeof signupData.detail === 'string' ? signupData.detail : '가입 완료 처리 중 오류가 발생했습니다.');

            // 3. Refresh session to get updated metadata (userid, etc.)
            await supabase.auth.refreshSession();

            toast.success('회원가입이 완료되었습니다! 반갑습니다.');
            setIsSignUp(false);
            setSignupStep(1);
            setIsLoginOpen(false); // Close dialog on success
        } catch (error: any) {
            toast.error(error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userid, password })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || '로그인 실패');

            const { error } = await supabase.auth.setSession({
                access_token: data.access_token,
                refresh_token: data.refresh_token || ''
            });

            if (error) throw error;
            toast.success('반갑습니다! 로그인되었습니다.');
            setIsLoginOpen(false);
        } catch (error: any) {
            console.error('Login error:', error);
            toast.error(error.message || '로그인 중 오류가 발생했습니다. 서버 연결을 확인해주세요.');
        } finally {
            setLoading(false);
        }
    };

    const getRedirectUrl = () => {
        const currentPath = window.location.pathname;
        // If on a specific cert detail page, redirect back there.
        if (currentPath.startsWith('/certs/')) {
            return window.location.origin + currentPath;
        }
        // Otherwise, redirect to the home page or a default dashboard.
        return window.location.origin;
    };

    const handleGoogleLogin = async () => {
        setLoading(true);
        try {
            const { error } = await supabase.auth.signInWithOAuth({
                provider: 'google',
                options: {
                    redirectTo: getRedirectUrl(),
                }
            });
            if (error) throw error;
        } catch (error: any) {
            toast.error(error.message || '구글 로그인 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const resetStates = () => {
        setIsSignUp(false);
        setSignupStep(1);
        setEmail('');
        setUserid('');
        setPassword('');
        setPasswordConfirm('');
        setName('');
        setBirthDate('');
        setMajor('');
        setVerificationCode('');
    };

    if (user) {
        return (
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="relative flex items-center gap-2 px-2 hover:bg-slate-800/50 transition-all duration-200 rounded-xl group">
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500/20 to-indigo-500/20 flex items-center justify-center border border-blue-500/20 group-hover:border-blue-500/40 transition-colors">
                            <User className="w-5 h-5 text-blue-400" />
                        </div>
                        <div className="hidden sm:block text-left">
                            <p className="text-sm font-semibold text-slate-100 truncate max-w-[120px]">
                                {user.user_metadata?.userid || user.email?.split('@')[0]}
                            </p>
                            <p className="text-[10px] text-blue-400 font-medium tracking-wide">USER ACCOUNT</p>
                        </div>
                        <ChevronDown className="w-4 h-4 text-slate-500 group-hover:text-slate-300 transition-colors" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-60 bg-slate-900/95 backdrop-blur-xl border-slate-800 p-2 rounded-2xl shadow-2xl">
                    <DropdownMenuLabel className="text-slate-500 font-bold text-[10px] px-3 py-2 uppercase tracking-[0.2em] opacity-70">Account</DropdownMenuLabel>
                    <DropdownMenuSeparator className="bg-slate-800/50 mx-1" />
                    <DropdownMenuItem
                        onClick={() => router.navigate('/mypage')}
                        className="focus:bg-blue-500/10 focus:text-blue-400 rounded-xl cursor-pointer transition-colors py-3 px-3 font-bold text-blue-400 group/item"
                    >
                        <User className="w-4 h-4 mr-3 transition-transform group-hover/item:scale-110" />
                        마이페이지
                    </DropdownMenuItem>
                    <DropdownMenuItem
                        onClick={() => router.navigate('/certs?filter=bookmarks')}
                        className="focus:bg-blue-500/10 focus:text-blue-400 rounded-xl cursor-pointer transition-colors py-3 px-3 font-medium text-slate-300"
                    >
                        <Bookmark className="w-4 h-4 mr-3 text-slate-500" />
                        내 관심 자격증
                    </DropdownMenuItem>
                    <DropdownMenuItem
                        onClick={() => router.navigate('/recommendations')}
                        className="focus:bg-blue-500/10 focus:text-blue-400 rounded-xl cursor-pointer transition-colors py-3 px-3 font-medium text-slate-300"
                    >
                        <Activity className="w-4 h-4 mr-3 text-slate-500" />
                        나의 커리어 분석
                    </DropdownMenuItem>
                    <DropdownMenuSeparator className="bg-slate-800/50 mx-1" />
                    <DropdownMenuItem
                        onClick={() => { signOut(); setIsSignUp(false); }}
                        className="text-red-400 focus:bg-red-400/10 focus:text-red-400 rounded-lg cursor-pointer transition-colors py-2.5"
                    >
                        <LogOut className="w-4 h-4 mr-2" />
                        로그아웃
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        );
    }

    return (
        <>
            <Button
                variant="ghost"
                onClick={() => { resetStates(); setIsLoginOpen(true); }}
                className="text-slate-300 hover:text-white hover:bg-slate-800/50 flex items-center gap-2 rounded-xl transition-all font-medium"
            >
                <LogIn className="w-4 h-4" />
                로그인
            </Button>

            <Dialog open={isLoginOpen} onOpenChange={(open) => { if (!open) resetStates(); setIsLoginOpen(open); }}>
                <DialogContent
                    className="bg-slate-950/98 backdrop-blur-2xl border-slate-800 text-slate-200 sm:max-w-[420px] rounded-[2rem] shadow-2xl p-0 overflow-hidden"
                    onPointerDownOutside={(e) => e.preventDefault()}
                    onEscapeKeyDown={(e) => e.preventDefault()}
                >
                    <div className="p-8 space-y-6">
                        <DialogHeader>
                            <DialogTitle className="text-3xl font-extrabold tracking-tight">
                                {isSignUp ? (
                                    <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
                                        새로운 시작
                                    </span>
                                ) : (
                                    <span className="bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                                        환영합니다
                                    </span>
                                )}
                            </DialogTitle>
                            <DialogDescription className="text-slate-400 text-sm font-medium mt-1">
                                {isSignUp ? '간단한 정보를 입력하고 커리어를 시작하세요.' : '아이디와 비밀번호를 입력하여 로그인하세요.'}
                            </DialogDescription>
                        </DialogHeader>

                        {isSignUp ? (
                            <div className="space-y-6">
                                <div className="space-y-2">
                                    <Label className="text-slate-300 text-xs font-bold uppercase tracking-wider">이메일 인증</Label>
                                    <div className="flex gap-2">
                                        <Input
                                            type="email"
                                            placeholder="verified@example.com"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            disabled={signupStep > 1}
                                            className="bg-slate-900/50 border-slate-800 h-11 focus:ring-blue-500/20"
                                        />
                                        {signupStep === 1 && (
                                            <Button
                                                onClick={handleSendOTP}
                                                className="bg-blue-600 hover:bg-blue-500 text-white h-11 px-4 rounded-lg transition-all"
                                                disabled={loading}
                                            >
                                                {loading ? '발송..' : '인증'}
                                            </Button>
                                        )}
                                    </div>
                                </div>

                                {signupStep >= 2 && (
                                    <form onSubmit={handleSignupCompleteWithVerify} className="space-y-4 animate-in fade-in slide-in-from-top-4 duration-500">
                                        <div className="p-4 bg-slate-900/40 rounded-2xl border border-slate-800/50 space-y-4">
                                            <div className="space-y-2">
                                                <Label className="text-slate-400 text-[11px] font-bold uppercase">인증 코드</Label>
                                                <Input
                                                    placeholder="숫자 코드 입력"
                                                    value={verificationCode}
                                                    onChange={(e) => setVerificationCode(e.target.value)}
                                                    className="bg-slate-950 border-slate-800 h-11 text-center tracking-[0.2em] font-mono text-xl"
                                                />
                                            </div>

                                            <div className="grid grid-cols-2 gap-4">
                                                <div className="space-y-2">
                                                    <Label className="text-slate-400 text-[11px] font-bold uppercase">이름</Label>
                                                    <Input value={name} onChange={(e) => setName(e.target.value)} className="bg-slate-950 border-slate-800 h-11" required />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label className="text-slate-400 text-[11px] font-bold uppercase">생년월일</Label>
                                                    <Input placeholder="YYMMDD" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} className="bg-slate-950 border-slate-800 h-11" required />
                                                </div>
                                            </div>

                                            <div className="space-y-2">
                                                <Label className="text-slate-400 text-[11px] font-bold uppercase">아이디</Label>
                                                <div className="flex gap-2">
                                                    <Input
                                                        value={userid}
                                                        onChange={(e) => {
                                                            setUserid(e.target.value);
                                                            setIsIdAvailable(null); // Reset on change
                                                        }}
                                                        className={`bg-slate-950 h-11 transition-all ${isIdAvailable === true ? 'border-green-500/50 focus-visible:ring-green-500/20' : isIdAvailable === false ? 'border-red-500/50 focus-visible:ring-red-500/20' : 'border-slate-800'}`}
                                                        required
                                                    />
                                                    <Button
                                                        type="button"
                                                        onClick={handleCheckUserId}
                                                        disabled={loading || !userid || isIdAvailable === true}
                                                        className={`h-11 px-4 whitespace-nowrap rounded-lg text-sm font-bold transition-all ${isIdAvailable === true ? 'bg-green-600/20 text-green-400 hover:bg-green-600/20' : 'bg-slate-800 hover:bg-slate-700 text-slate-300'}`}
                                                    >
                                                        {isIdAvailable === true ? <><CheckCircle2 className="w-4 h-4 mr-1.5" /> 사용 가능</> : '중복 확인'}
                                                    </Button>
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-2 gap-4">
                                                <div className="space-y-2">
                                                    <Label className="text-slate-400 text-[11px] font-bold uppercase">비밀번호</Label>
                                                    <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="bg-slate-950 border-slate-800 h-11" required />
                                                </div>
                                                <div className="space-y-2 relative">
                                                    <div className="flex justify-between items-center">
                                                        <Label className="text-slate-400 text-[11px] font-bold uppercase">비밀번호 확인</Label>
                                                        {password && passwordConfirm && password === passwordConfirm && (
                                                            <CheckCircle2 className="w-4 h-4 text-green-400 absolute right-3 top-[34px]" />
                                                        )}
                                                    </div>
                                                    <Input
                                                        type="password"
                                                        value={passwordConfirm}
                                                        onChange={(e) => setPasswordConfirm(e.target.value)}
                                                        className={`bg-slate-950 h-11 transition-all pr-10 ${password && passwordConfirm && password === passwordConfirm ? 'border-green-500/50' : 'border-slate-800'}`}
                                                        required
                                                    />
                                                </div>
                                            </div>

                                            <div className="space-y-2 relative">
                                                <Label className="text-slate-400 text-[11px] font-bold uppercase">전공 (선택)</Label>
                                                <div className="relative">
                                                    <Input
                                                        value={major}
                                                        onChange={(e) => {
                                                            setMajor(e.target.value);
                                                            setShowMajorSuggestions(true);
                                                        }}
                                                        onFocus={() => setShowMajorSuggestions(true)}
                                                        onBlur={() => setTimeout(() => setShowMajorSuggestions(false), 200)}
                                                        className="bg-slate-950 border-slate-800 h-11"
                                                        placeholder="예: 컴퓨터공학"
                                                    />
                                                    {showMajorSuggestions && major.length > 0 && (
                                                        <div className="absolute bottom-full left-0 right-0 mb-2 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-[100] max-h-48 overflow-y-auto">
                                                            {availableMajors
                                                                .filter(m => m.toLowerCase().includes(major.toLowerCase()))
                                                                .slice(0, 10)
                                                                .map(m => (
                                                                    <div
                                                                        key={m}
                                                                        onMouseDown={() => {
                                                                            setMajor(m);
                                                                            setShowMajorSuggestions(false);
                                                                        }}
                                                                        className="px-4 py-2 hover:bg-slate-800 cursor-pointer text-sm text-slate-300 border-b border-slate-800/50 last:border-0"
                                                                    >
                                                                        {m}
                                                                    </div>
                                                                ))
                                                            }
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>

                                        <Button type="submit" className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 h-12 rounded-xl text-lg font-bold shadow-lg shadow-blue-500/20" disabled={loading}>
                                            {loading ? '가입 처리 중...' : '회원가입 완료'}
                                        </Button>
                                        <button type="button" onClick={() => setSignupStep(1)} className="w-full text-xs text-slate-500 hover:text-slate-300 transition-colors">이메일 수정하기</button>
                                    </form>
                                )}
                            </div>
                        ) : (
                            <form onSubmit={handleLogin} className="space-y-5">
                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <Label className="text-slate-300 text-xs font-bold uppercase tracking-wider">사용자 아이디</Label>
                                        <Input
                                            placeholder="아이디를 입력하세요"
                                            value={userid}
                                            onChange={(e) => setUserid(e.target.value)}
                                            className="bg-slate-900/50 border-slate-800 h-12 focus:ring-blue-500/20"
                                            required
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-slate-300 text-xs font-bold uppercase tracking-wider">비밀번호</Label>
                                        <Input
                                            type="password"
                                            placeholder="비밀번호를 입력하세요"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            className="bg-slate-900/50 border-slate-800 h-12 focus:ring-blue-500/20"
                                            autoComplete="current-password"
                                            required
                                        />
                                    </div>
                                </div>
                                <Button type="submit" className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 h-12 rounded-xl text-lg font-bold shadow-lg shadow-blue-500/20" disabled={loading}>
                                    {loading ? '로그인 중...' : '로그인'}
                                </Button>
                            </form>
                        )}

                        {(!isSignUp || signupStep === 1) && (
                            <>
                                <div className="relative my-6">
                                    <div className="absolute inset-0 flex items-center">
                                        <span className="w-full border-t border-slate-800/80"></span>
                                    </div>
                                    <div className="relative flex justify-center text-[10px] uppercase font-bold text-slate-500 tracking-widest">
                                        <span className="bg-slate-900 px-4">Or continue with</span>
                                    </div>
                                </div>

                                <Button
                                    type="button"
                                    onClick={handleGoogleLogin}
                                    disabled={loading}
                                    className="w-full flex items-center justify-center gap-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 h-12 rounded-xl text-lg font-bold shadow-lg shadow-blue-500/20 text-white border-none hover:-translate-y-0.5 transition-all duration-300"
                                >
                                    <div className="bg-white rounded-full p-0.5 mr-1">
                                        <svg className="w-5 h-5" viewBox="0 0 24 24">
                                            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                                            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                                        </svg>
                                    </div>
                                    구글 계정으로 로그인
                                </Button>
                            </>
                        )}


                        <div className="pt-4 flex flex-col items-center gap-4">
                            <div className="w-full h-px bg-slate-800/50" />
                            <p className="text-sm text-slate-400">
                                {isSignUp ? '이미 계정이 있으신가요?' : '아직 계정이 없으신가요?'}
                                <button
                                    type="button"
                                    onClick={() => { setIsSignUp(!isSignUp); setSignupStep(1); }}
                                    className="ml-2 text-blue-400 hover:text-blue-300 underline font-bold transition-colors"
                                >
                                    {isSignUp ? '로그인하기' : '회원가입하기'}
                                </button>
                            </p>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </>
    );
}
