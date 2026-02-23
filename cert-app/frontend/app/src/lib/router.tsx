import { useState, useEffect, useCallback, useMemo } from 'react';
import type { ReactNode, MouseEvent } from 'react';

export type Route = 'home' | 'certs' | 'cert-detail' | 'recommendations' | 'ai-recommendations' | 'jobs' | 'job-detail' | 'mypage' | 'privacy' | 'terms';

export interface RouteState {
    route: Route;
    params?: Record<string, string | undefined>;
}

export const getRouteFromPath = (path: string, search: string): RouteState => {
    let route: Route = 'home';
    let params: Record<string, string | undefined> = {};

    if (path === '/' || path === '') {
        route = 'home';
    } else if (path === '/privacy') {
        route = 'privacy';
    } else if (path === '/terms') {
        route = 'terms';
    } else if (path.startsWith('/certs/')) {
        route = 'cert-detail';
        params.qualId = path.split('/')[2];
    } else if (path.startsWith('/certs')) {
        route = 'certs';
        new URLSearchParams(search).forEach((val, key) => {
            params[key] = val;
        });
    } else if (path === '/recommendations' || path === '/recommendation') {
        route = 'recommendations';
    } else if (path === '/ai-recommendations') {
        route = 'ai-recommendations';
    } else if (path.startsWith('/jobs/')) {
        route = 'job-detail';
        params.jobId = path.split('/')[2];
    } else if (path === '/jobs') {
        route = 'jobs';
    } else if (path === '/mypage') {
        route = 'mypage';
    }
    return { route, params };
};

// Simple router context
export const RouterContext = {
    currentRoute: getRouteFromPath(window.location.pathname, window.location.search),
    listeners: new Set<(state: RouteState) => void>(),

    navigate(path: string) {
        const newState = getRouteFromPath(path, path.includes('?') ? path.split('?')[1] : '');

        this.currentRoute = newState;
        this.listeners.forEach(listener => listener(this.currentRoute));
        window.history.pushState(newState, '', path);
    },

    getPath(route: Route, params?: Record<string, string | undefined>): string {
        switch (route) {
            case 'home': return '/';
            case 'certs': {
                if (!params) return '/certs';
                const query = new URLSearchParams(params as Record<string, string>).toString();
                return query ? `/certs?${query}` : '/certs';
            }
            case 'cert-detail': return `/certs/${params?.qualId || ''}`;
            case 'recommendations': return '/recommendations';
            case 'ai-recommendations': return '/ai-recommendations';
            case 'jobs': return '/jobs';
            case 'job-detail' as any: return `/jobs/${params?.jobId || ''}`;
            case 'mypage': return '/mypage';
            default: return '/';
        }
    },

    getCurrentPath(): string {
        return window.location.pathname + window.location.search;
    },

    subscribe(listener: (state: RouteState) => void) {
        this.listeners.add(listener);
        return () => { this.listeners.delete(listener); };
    }
};

export function useRouter() {
    const [routeState, setRouteState] = useState<RouteState>(RouterContext.currentRoute);

    useEffect(() => {
        const unsubscribe = RouterContext.subscribe(setRouteState);
        return () => { unsubscribe(); };
    }, []);

    const navigate = useCallback((path: string) => {
        RouterContext.navigate(path);
    }, []);

    return useMemo(() => ({ ...routeState, navigate }), [routeState, navigate]);
}

interface LinkProps {
    to: string;
    children: ReactNode;
    className?: string;
    onClick?: () => void;
}

export function Link({ to, children, className, onClick }: LinkProps) {
    const handleClick = (e: MouseEvent) => {
        // Only intercept left clicks without modifier keys
        if (e.button === 0 && !e.ctrlKey && !e.shiftKey && !e.altKey && !e.metaKey) {
            e.preventDefault();
            RouterContext.navigate(to);
            onClick?.();
        }
    };

    return (
        <a
            href={to}
            onClick={handleClick}
            className={className}
        >
            {children}
        </a>
    );
}
