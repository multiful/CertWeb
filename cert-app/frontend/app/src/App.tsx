import { useEffect, useMemo, useState, lazy, Suspense } from 'react';
import { Layout } from '@/components/layout/Layout';
import { Toaster } from '@/components/ui/sonner';
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

    const handleLocationChange = () => {
      const newState = getRouteFromPath(window.location.pathname, window.location.search);
      RouterContext.currentRoute = newState;
      setRouteState(newState);
    };

    window.addEventListener('popstate', handleLocationChange);
    const unsubscribe = RouterContext.subscribe((newState) => {
      setRouteState(newState);
      window.scrollTo(0, 0); // Always scroll to top on navigation
    });

    return () => {
      unsubscribe();
      window.removeEventListener('popstate', handleLocationChange);
    };
  }, []);

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
    <Layout>
      <div key={RouterContext.getCurrentPath()}>
        <Suspense fallback={fallback}>
          {renderPage}
        </Suspense>
      </div>
      <Toaster />
    </Layout>
  );
}

export default App;
