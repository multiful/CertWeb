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

    // Effect 1: Handle Authentication Session
    useEffect(() => {
        // Check active sessions and sets the user
        supabase.auth.getSession().then(({ data: { session } }: any) => {
            const currentUser = session?.user ?? null;
            // Only update if ID is different to avoid object reference loop
            setUser(prev => prev?.id === currentUser?.id ? prev : currentUser);
            setToken(session?.access_token ?? null);
            setLoading(false);
        });

        // Listen for changes on auth state
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event: string, session: any) => {
            const currentUser = session?.user ?? null;
            setUser(prev => prev?.id === currentUser?.id ? prev : currentUser);
            setToken(session?.access_token ?? null);
            setLoading(false);
        });

        return () => {
            subscription.unsubscribe();
        };
    }, []); // Run only on mount

    // Effect 2: Handle Inactivity Timer when user is authenticated
    useEffect(() => {
        if (!user) return;

        const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'];

        const handleActivity = () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            timeoutRef.current = setTimeout(() => {
                console.warn('Inactivity timeout reached. Signing out...');
                signOut();
            }, INACTIVITY_TIMEOUT);
        };

        activityEvents.forEach(event => {
            window.addEventListener(event, handleActivity);
        });

        // Initialize timer
        handleActivity();

        return () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            activityEvents.forEach(event => {
                window.removeEventListener(event, handleActivity);
            });
        };
    }, [user?.id]); // Depend on user ID instead of object reference

    const signOut = async () => {
        await supabase.auth.signOut();
        setUser(null);
        setToken(null);
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };

    return { user, token, loading, signOut };
}
