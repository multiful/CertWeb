import { createClient } from '@supabase/supabase-js';

// Supabase client initialization with validation
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Fail-safe initialization to prevent white-screen crashes
const createSafeClient = () => {
    if (!supabaseUrl || !supabaseAnonKey || !supabaseUrl.startsWith('http')) {
        console.error('Supabase configuration error: Missing or invalid environment variables in .env');
        // Return a robust mock object to keep React components from crashing
        const mockAuth = {
            getSession: async () => ({ data: { session: null }, error: null }),
            onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => { } } } }),
            signInWithPassword: async () => ({ data: { session: null }, error: new Error('Settings required') }),
            signUp: async () => ({ data: { session: null }, error: new Error('Settings required') }),
            signOut: async () => ({ error: null })
        };
        return {
            auth: mockAuth,
            from: () => ({
                select: () => ({
                    eq: () => ({
                        eq: () => ({
                            maybeSingle: async () => ({ data: null, error: null })
                        })
                    })
                }),
                insert: async () => ({ data: null, error: null }),
                delete: () => ({
                    eq: () => ({
                        eq: async () => ({ data: null, error: null })
                    })
                })
            })
        } as any;
    }
    return createClient(supabaseUrl, supabaseAnonKey, {
        auth: {
            storage: window.sessionStorage,
            persistSession: true,
            autoRefreshToken: true,
        }
    });
};

export const supabase = createSafeClient();
