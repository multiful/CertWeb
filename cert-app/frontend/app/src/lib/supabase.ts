import { createClient } from '@supabase/supabase-js';

// Supabase client initialization with validation
const supabaseUrl =
    import.meta.env.VITE_SUPABASE_URL ||
    (import.meta as any).env?.VITE_SUPABASE_URL ||
    (import.meta as any).env?.NEXT_PUBLIC_SUPABASE_URL ||
    "";
const supabaseAnonKey =
    import.meta.env.VITE_SUPABASE_ANON_KEY ||
    (import.meta as any).env?.VITE_SUPABASE_ANON_KEY ||
    (import.meta as any).env?.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    "";

/**
 * Get the appropriate redirect URL for Auth
 * Handles local dev, Vercel preview, and production.
 */
export const getRedirectUrl = () => {
    let url = window?.location?.origin || 'http://localhost:5173';
    // Ensure it doesn't have a trailing slash
    url = url.replace(/\/$/, '');
    return url;
};

// Fail-safe initialization to prevent white-screen crashes
const createSafeClient = () => {
    if (!supabaseUrl || !supabaseAnonKey || !supabaseUrl.startsWith('http')) {
        console.error('Supabase configuration error: Missing environment variables. Please check your Vercel settings.');

        const mockAuth = {
            getSession: async () => ({ data: { session: null }, error: null }),
            onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => { } } } }),
            signInWithPassword: async () => ({ data: { session: null }, error: new Error('Auth settings required') }),
            signInWithOAuth: async () => ({ data: { url: null }, error: new Error('Auth settings required') }),
            signUp: async () => ({ data: { session: null }, error: new Error('Auth settings required') }),
            signOut: async () => ({ error: null })
        };
        return {
            auth: mockAuth,
            from: () => ({
                select: () => ({ eq: () => ({ eq: () => ({ maybeSingle: async () => ({ data: null, error: null }) }) }) }),
                insert: async () => ({ data: null, error: null }),
                delete: () => ({ eq: () => ({ eq: async () => ({ data: null, error: null }) }) })
            })
        } as any;
    }

    return createClient(supabaseUrl, supabaseAnonKey, {
        auth: {
            storage: window.localStorage,
            persistSession: true,
            autoRefreshToken: true,
            detectSessionInUrl: true,
            flowType: 'pkce'
        }
    });
};

export const supabase = createSafeClient();
