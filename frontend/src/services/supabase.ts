import { createClient, type SupabaseClient, type Session, type User, type AuthChangeEvent } from '@supabase/supabase-js';

export type { Session, User, AuthChangeEvent };

/**
 * Centralized Supabase Client Configuration
 * =========================================
 * Provides an initialized Supabase JS client for authentication and session management.
 * 
 * Security Architecture:
 * - Uses ONLY the public anonymous key (`VITE_SUPABASE_ANON_KEY`).
 * - Never includes or exposes the service-role key or JWT secret.
 * - Fails safely if environment variables are not configured, allowing local development
 *   to continue without auth errors.
 */

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

/**
 * Returns true if both Supabase URL and anon key are properly defined in the client environment.
 */
export const isSupabaseConfigured: boolean = Boolean(
  supabaseUrl &&
  supabaseAnonKey &&
  supabaseUrl.trim() !== '' &&
  supabaseAnonKey.trim() !== '' &&
  !supabaseUrl.includes('your-project-id') &&
  !supabaseAnonKey.includes('your_supabase_public_anon_key')
);

/**
 * Centralized Supabase client instance.
 * `null` when environment variables are not yet configured.
 */
export const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(supabaseUrl!.trim(), supabaseAnonKey!.trim(), {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        storage: typeof window !== 'undefined' ? window.localStorage : undefined,
      },
    })
  : null;

/**
 * Retrieves the non-null Supabase client or throws a descriptive error.
 */
export function getSupabase(): SupabaseClient {
  if (!supabase) {
    throw new Error(
      'Supabase client is not configured. Please define VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your frontend/.env file.'
    );
  }
  return supabase;
}

/**
 * Safely fetches the current session's JWT access token for attaching to backend requests.
 * Returns null if Supabase is unconfigured or no active session exists.
 */
export async function getSupabaseAccessToken(): Promise<string | null> {
  if (!supabase) {
    return null;
  }
  try {
    const { data, error } = await supabase.auth.getSession();
    if (error || !data.session) {
      return null;
    }
    return data.session.access_token;
  } catch (err) {
    console.warn('[Supabase] Failed to retrieve access token:', err);
    return null;
  }
}

/**
 * Helper to initiate Google OAuth login flow via Supabase.
 * Uses window.location.origin as default redirect target.
 */
export async function signInWithGoogle(redirectTo?: string) {
  const client = getSupabase();
  const callbackUrl = redirectTo || (typeof window !== 'undefined' ? window.location.origin : undefined);
  
  return client.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: callbackUrl,
      queryParams: {
        access_type: 'offline',
        prompt: 'consent',
      },
    },
  });
}

/**
 * Retrieves the currently authenticated Supabase user, or null if unauthenticated.
 */
export async function getCurrentUser(): Promise<User | null> {
  if (!supabase) return null;
  try {
    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user) return null;
    return data.user;
  } catch (err) {
    console.warn('[Supabase] Failed to retrieve current user:', err);
    return null;
  }
}

/**
 * Retrieves the currently active Supabase session, or null if unauthenticated.
 */
export async function getCurrentSession(): Promise<Session | null> {
  if (!supabase) return null;
  try {
    const { data, error } = await supabase.auth.getSession();
    if (error || !data.session) return null;
    return data.session;
  } catch (err) {
    console.warn('[Supabase] Failed to retrieve session:', err);
    return null;
  }
}

/**
 * Helper to terminate the active Supabase session.
 */
export async function signOut() {
  if (!supabase) return;
  return supabase.auth.signOut();
}

/**
 * Subscribes to authentication state changes (e.g. SIGNED_IN, SIGNED_OUT, TOKEN_REFRESHED).
 */
export function onAuthStateChange(
  callback: (event: AuthChangeEvent, session: Session | null) => void
) {
  if (!supabase) {
    return { data: { subscription: { unsubscribe: () => {} } } };
  }
  return supabase.auth.onAuthStateChange(callback);
}

