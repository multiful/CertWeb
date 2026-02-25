import React, { useState, useMemo, useEffect } from 'react';
import { Award, Search, ThumbsUp, Menu, X, Home, BrainCircuit, Cookie } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link, useRouter } from '@/lib/router';
import { UserMenu } from './UserMenu';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { path: '/', label: '홈', icon: <Home className="w-4 h-4" /> },
  { path: '/certs', label: '자격증 탐색', icon: <Search className="w-4 h-4" /> },
  { path: '/jobs', label: '진로 및 직무 매칭', icon: <Award className="w-4 h-4" /> },
  { path: '/recommendations', label: '전공 탐색', icon: <ThumbsUp className="w-4 h-4" /> },
  { path: '/ai-recommendations', label: 'AI 추천', icon: <BrainCircuit className="w-4 h-4" /> },
];

import { CertLogo } from '../common/CertLogo';

export function Layout({ children }: { children: React.ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [cookieConsent, setCookieConsent] = useState<boolean | null>(null);
  const { route } = useRouter();

  useEffect(() => {
    const stored = localStorage.getItem('cookie_consent');
    setCookieConsent(stored === 'accepted' ? true : stored === 'declined' ? false : null);
  }, []);

  const acceptCookies = () => {
    localStorage.setItem('cookie_consent', 'accepted');
    setCookieConsent(true);
  };

  const declineCookies = () => {
    localStorage.setItem('cookie_consent', 'declined');
    setCookieConsent(false);
  };

  const currentRoutePath = useMemo(() => {
    if (route === 'home') return '/';
    if (route === 'certs' || route === 'cert-detail') return '/certs';
    if (route === 'jobs' || route === 'job-detail') return '/jobs';
    if (route === 'recommendations') return '/recommendations';
    if (route === 'ai-recommendations') return '/ai-recommendations';
    if (route === 'mypage') return '/mypage';
    return '/';
  }, [route]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-blue-500/30 selection:text-blue-200">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="relative">
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
              <CertLogo className="w-9 h-9" />
            </div>
            <span className="font-black text-xl hidden sm:inline tracking-tighter bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">CertFinder</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${currentRoutePath === item.path
                  ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                  }`}
              >
                {item.icon}
                {item.label}
              </Link>
            ))}
            <div className="w-px h-6 bg-slate-800 mx-2" />
            <UserMenu />
          </nav>

          {/* Mobile Menu Button */}
          <div className="flex items-center gap-2 md:hidden">
            <UserMenu />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav className="md:hidden border-t border-slate-800 bg-slate-950 px-4 py-2 animate-in slide-in-from-top duration-200">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-bold transition-colors ${currentRoutePath === item.path
                  ? 'bg-blue-600/10 text-blue-400'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                  }`}
              >
                {item.icon}
                {item.label}
              </Link>
            ))}
          </nav>
        )}
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {children}
      </main>

      {/* Cookie Consent Banner */}
      {cookieConsent === null && (
        <div className="fixed bottom-0 left-0 right-0 z-50 p-4 pointer-events-none">
          <div className="max-w-2xl mx-auto bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-2xl p-5 shadow-2xl pointer-events-auto animate-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-start gap-4">
              <div className="p-2 bg-blue-500/10 rounded-xl border border-blue-500/20 shrink-0 mt-0.5">
                <Cookie className="w-5 h-5 text-blue-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-300 leading-relaxed">
                  CertFinder는 서비스 개선 및 맞춤형 광고 제공을 위해 쿠키를 사용합니다.
                  자세한 내용은{' '}
                  <Link to="/privacy" className="text-blue-400 underline hover:text-blue-300">
                    개인정보 처리방침
                  </Link>을 참고하세요.
                </p>
              </div>
              <div className="flex gap-2 shrink-0">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={declineCookies}
                  className="text-slate-500 hover:text-slate-300 text-xs px-3"
                >
                  거부
                </Button>
                <Button
                  size="sm"
                  onClick={acceptCookies}
                  className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-4 rounded-xl"
                >
                  동의
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-800 mt-auto bg-slate-950/50">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
            <Link to="/" className="flex items-center gap-2 group opacity-60 hover:opacity-100 transition-opacity">
              <div className="relative">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full blur opacity-10 group-hover:opacity-30 transition duration-500"></div>
                <CertLogo className="w-6 h-6" />
              </div>
              <span className="font-black text-sm tracking-tighter bg-gradient-to-r from-white/80 to-slate-500 bg-clip-text text-transparent uppercase">CertFinder</span>
            </Link>
            <p className="text-slate-500 text-sm font-medium">
              2026 CertFinder 국가자격 통합 분석 시스템
            </p>
            <div className="flex gap-4 text-xs font-bold text-slate-600">
              <Link to="/privacy" className="hover:text-slate-400 cursor-pointer transition-colors">개인정보 처리방침</Link>
              <Link to="/terms" className="hover:text-slate-400 cursor-pointer transition-colors">이용약관</Link>
              <Link to="/contact" className="hover:text-slate-400 cursor-pointer transition-colors">문의하기</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
