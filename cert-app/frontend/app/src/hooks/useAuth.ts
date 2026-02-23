import { useState, useEffect, useRef } from 'react';
import { supabase } from '@/lib/supabase';
import type { User } from '@supabase/supabase-js';

// Inactivity timeout in milliseconds (1 hour = 3600000ms)
const INACTIVITY_TIMEOUT = 3600 * 1000;

export function useAuth() {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const resetTimer = () => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
        }

        // Only set timer if user is logged in
        if (user) {
            timeoutRef.current = setTimeout(() => {
                console.warn('Inactivity timeout reached. Signing out...');
                signOut();
            }, INACTIVITY_TIMEOUT);
        }
    };

    useEffect(() => {
        // Check active sessions and sets the user
        supabase.auth.getSession().then(({ data: { session } }: any) => {
            setUser(session?.user ?? null);
            setToken(session?.access_token ?? null);
            setLoading(false);
        });

        // Listen for changes on auth state
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event: string, session: any) => {
            setUser(session?.user ?? null);
            setToken(session?.access_token ?? null);
            setLoading(false);
        });

        // Event listeners for activity tracking
        const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'];
        activityEvents.forEach(event => {
            window.addEventListener(event, resetTimer);
        });

        // Initialize timer
        resetTimer();

        return () => {
            subscription.unsubscribe();
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            activityEvents.forEach(event => {
                window.removeEventListener(event, resetTimer);
            });
        };
    }, [user]); // Re-run when user state changes to start/stop timer

    const signOut = async () => {
        await supabase.auth.signOut();
        setUser(null);
        setToken(null);
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };

    return { user, token, loading, signOut };
}
