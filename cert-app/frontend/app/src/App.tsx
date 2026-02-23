import { useEffect, useMemo, useState } from 'react';
import { Layout } from '@/components/layout/Layout';
import { HomePage } from '@/pages/HomePage';
import { CertListPage } from '@/pages/CertListPage';
import { CertDetailPage } from '@/pages/CertDetailPage';
import { RecommendationPage } from '@/pages/RecommendationPage';
import { AiRecommendationPage } from '@/pages/AiRecommendationPage';
import { JobListPage } from '@/pages/JobListPage';
import { JobDetailPage } from '@/pages/JobDetailPage';
import { MyPage } from '@/pages/MyPage';
import { PrivacyPolicyPage } from '@/pages/PrivacyPolicyPage';
import { TermsOfServicePage } from '@/pages/TermsOfServicePage';
import { Toaster } from '@/components/ui/sonner';
import {
  getRouteFromPath,
  RouterContext,
} from '@/lib/router';
import type { RouteState } from '@/lib/router';


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
      default:
        return <HomePage />;
    }
  }, [routeState]);

  return (
    <Layout>
      <div key={RouterContext.getCurrentPath()}>
        {renderPage}
      </div>
      <Toaster />
    </Layout>
  );
}

export default App;
