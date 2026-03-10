import { useEffect, useMemo, useState, lazy, Suspense } from 'react';
import { Layout } from '@/components/layout/Layout';
import { Toaster } from '@/components/ui/sonner';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { getRouteFromPath, RouterContext } from '@/lib/router';
import type { RouteState } from '@/lib/router';

const HomePage = lazy(() => import('@/pages/HomePage').then(m => ({ default: m.HomePage })));
const CertListPage = lazy(() => import('@/pages/CertListPage').then(m => ({ default: m.CertListPage })));
const CertDetailPage = lazy(() => import('@/pages/CertDetailPage').then(m => ({ default: m.CertDetailPage })));
const RecommendationPage = lazy(() => import('@/pages/RecommendationPage').then(m => ({ default: m.RecommendationPage })));
const AiRecommendationPage = lazy(() => import('@/pages/AiRecommendationPage').then(m => ({ default: m.AiRecommendationPage })));
const JobListPage = lazy(() => import('@/pages/JobListPage').then(m => ({ default: m.JobListPage })));
const JobDetailPage = lazy(() => import('@/pages/JobDetailPage').then(m => ({ default: m.JobDetailPage })));
const MyPage = lazy(() => import('@/pages/MyPage').then(m => ({ default: m.MyPage })));
const PrivacyPolicyPage = lazy(() => import('@/pages/PrivacyPolicyPage').then(m => ({ default: m.PrivacyPolicyPage })));
const TermsOfServicePage = lazy(() => import('@/pages/TermsOfServicePage').then(m => ({ default: m.TermsOfServicePage })));
const ContactPage = lazy(() => import('@/pages/ContactPage').then(m => ({ default: m.ContactPage })));


function App() {
  const [routeState, setRouteState] = useState<RouteState>(RouterContext.currentRoute);

  useEffect(() => {
    document.documentElement.classList.add('dark');

    const focusMainHeading = () => {
      try {
        const main = document.getElementById('main-content');
        if (!main) return;
        const heading = main.querySelector('h1, [data-main-heading]') as HTMLElement | null;
        if (!heading) return;
        if (!heading.hasAttribute('tabindex')) {
          heading.setAttribute('tabindex', '-1');
        }
        heading.focus();
      } catch {
        // 포커스 이동 실패는 UX에만 영향, 조용히 무시
      }
    };

    const handleLocationChange = () => {
      const newState = getRouteFromPath(window.location.pathname, window.location.search);
      RouterContext.currentRoute = newState;
      setRouteState(newState);
    };

    window.addEventListener('popstate', handleLocationChange);
    const unsubscribe = RouterContext.subscribe((newState) => {
      setRouteState(newState);
      window.scrollTo(0, 0); // Always scroll to top on navigation
       setTimeout(focusMainHeading, 0);
    });

    return () => {
      unsubscribe();
      window.removeEventListener('popstate', handleLocationChange);
    };
  }, []);

  useEffect(() => {
    const baseTitle = 'CertFinder | 국가자격 통합 분석 시스템';
    let title = baseTitle;

    switch (routeState.route) {
      case 'home':
        title = '홈 | CertFinder 국가자격 통합 분석';
        break;
      case 'certs':
        title = '자격증 탐색 | CertFinder';
        break;
      case 'cert-detail':
        title = '자격증 상세 정보 | CertFinder';
        break;
      case 'recommendations':
        title = '전공별 자격증 추천 | CertFinder';
        break;
      case 'ai-recommendations':
        title = 'AI 추천 엔진 | CertFinder';
        break;
      case 'jobs':
        title = '직무·진로 매칭 | CertFinder';
        break;
      case 'job-detail':
        title = '직무 상세 분석 | CertFinder';
        break;
      case 'mypage':
        title = '마이페이지 | CertFinder';
        break;
      case 'privacy':
        title = '개인정보 처리방침 | CertFinder';
        break;
      case 'terms':
        title = '이용약관 | CertFinder';
        break;
      case 'contact':
        title = '문의하기 | CertFinder';
        break;
      default:
        title = baseTitle;
    }

    document.title = title;
  }, [routeState.route]);

  const renderPage = useMemo(() => {
    switch (routeState.route) {
      case 'home':
        return <HomePage />;
      case 'certs':
        return <CertListPage />;
      case 'cert-detail':
        return <CertDetailPage id={routeState.params?.qualId || ''} />;
      case 'recommendations':
        return <RecommendationPage />;
      case 'ai-recommendations':
        return <AiRecommendationPage />;
      case 'jobs':
        return <JobListPage />;
      case 'job-detail':
        return <JobDetailPage id={routeState.params?.jobId || ''} />;
      case 'mypage':
        return <MyPage />;
      case 'privacy':
        return <PrivacyPolicyPage />;
      case 'terms':
        return <TermsOfServicePage />;
      case 'contact':
        return <ContactPage />;
      default:
        return <HomePage />;
    }
  }, [routeState]);

  const fallback = (
    <div className="min-h-[60vh] flex items-center justify-center bg-slate-950">
      <div className="w-10 h-10 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
    </div>
  );

  return (
    <ErrorBoundary>
      <Layout>
        <div key={RouterContext.getCurrentPath()}>
          <Suspense fallback={fallback}>
            {renderPage}
          </Suspense>
        </div>
        <Toaster />
      </Layout>
    </ErrorBoundary>
  );
}

export default App;
