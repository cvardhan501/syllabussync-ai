import React, { useState, useEffect } from 'react';
import { 
  GraduationCap, 
  Sparkles, 
  BookOpen, 
  PlaySquare, 
  CalendarDays, 
  ShieldCheck, 
  AlertCircle,
  ArrowRight,
  Loader2
} from 'lucide-react';
import { signInWithGoogle, isSupabaseConfigured } from '../services/supabase';
import type { HealthResponse } from '../types';

interface LoginPageProps {
  onBypassDevMode?: () => void;
  health?: HealthResponse | null;
  healthError?: string | null;
}

export const LoginPage: React.FC<LoginPageProps> = ({ 
  onBypassDevMode,
  health,
  healthError,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Inspect URL search params for OAuth redirect errors
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const errorParam = params.get('error_description') || params.get('error');
    if (errorParam) {
      setAuthError(decodeURIComponent(errorParam));
    }
  }, []);

  const handleGoogleSignIn = async () => {
    setAuthError(null);
    setIsLoading(true);
    try {
      const { error } = await signInWithGoogle();
      if (error) {
        setAuthError(error.message || 'Failed to initialize Google Sign-In.');
        setIsLoading(false);
      }
      // Note: On success, Supabase initiates a browser redirect to Google OAuth
    } catch (err: any) {
      setAuthError(err.message || 'An unexpected error occurred during Google Sign-In.');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col justify-between antialiased selection:bg-blue-600 selection:text-white relative overflow-hidden">
      {/* Background Radial Glow Accents */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-blue-600/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-0 right-10 w-[500px] h-[300px] bg-indigo-600/10 blur-[140px] rounded-full pointer-events-none" />

      {/* Top Navigation / Brand */}
      <header className="px-6 sm:px-12 py-6 flex items-center justify-between border-b border-[#152342]/60 z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-600/30 text-white">
            <GraduationCap className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-lg tracking-tight text-white block leading-tight">
              SyllabusSync <span className="text-blue-400">AI</span>
            </span>
            <p className="text-[11px] text-slate-400 font-medium m-0">Smart Learning Agent & Study Companion</p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs font-medium">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <span>ECC (ES256) Security</span>
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-8 z-10">
        <div className="w-full max-w-md">
          {/* Main Card */}
          <div className="rounded-3xl bg-[#0d172e] border border-[#1b2b52] shadow-2xl p-7 sm:p-9 relative">
            <div className="text-center space-y-2 mb-8">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                Welcome Future Techie! 🚀
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-sm mx-auto">
                Sign in with your Google account to access your personalized syllabus roadmaps and YouTube study plans.
              </p>
            </div>

            {/* Error Banner */}
            {authError && (
              <div className="mb-6 p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-3">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold text-rose-200 m-0">Authentication Failed</p>
                  <p className="text-rose-300/90 leading-tight m-0">{authError}</p>
                </div>
              </div>
            )}

            {/* Google Login Action */}
            <div className="space-y-4">
              <button
                onClick={handleGoogleSignIn}
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-3.5 px-5 py-3.5 rounded-2xl bg-[#111d38] hover:bg-[#162548] border border-[#213566] hover:border-blue-500/50 text-white font-semibold text-sm transition-all shadow-lg hover:shadow-blue-500/10 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed group"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                    <span>Connecting to Google...</span>
                  </>
                ) : (
                  <>
                    {/* Official Multi-Color Google G Logo */}
                    <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
                      <path
                        fill="#4285F4"
                        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z"
                      />
                      <path
                        fill="#34A853"
                        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24Z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15Z"
                      />
                      <path
                        fill="#EA4335"
                        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98Z"
                      />
                    </svg>
                    <span>Continue with Google</span>
                    <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-400 group-hover:translate-x-0.5 transition" />
                  </>
                )}
              </button>

              {/* Offline / Development Mode Bypass Button */}
              {onBypassDevMode && (
                <div className="pt-2 text-center">
                  <button
                    onClick={onBypassDevMode}
                    type="button"
                    className="text-xs text-slate-400 hover:text-slate-200 transition font-medium cursor-pointer underline decoration-slate-600 hover:decoration-slate-300"
                  >
                    {!isSupabaseConfigured 
                      ? 'Continue in Local Development Mode (Unauthenticated Dev)' 
                      : 'Continue as Local Guest (Dev Exploration)'}
                  </button>
                </div>
              )}

              {/* Live Backend Status Footer */}
              <div className="pt-3 flex items-center justify-center gap-1.5 text-[11px] font-mono">
                <span className="text-slate-500">Backend:</span>
                {health?.status === 'healthy' || health?.status === 'ok' ? (
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>FastAPI Online (v{health.version})</span>
                  </span>
                ) : healthError ? (
                  <span className="inline-flex items-center gap-1 text-rose-400 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                    <span>FastAPI Offline</span>
                  </span>
                ) : (
                  <span className="text-slate-500">Checking connection...</span>
                )}
              </div>
            </div>

            {/* Feature Highlights Grid */}
            <div className="mt-8 pt-6 border-t border-[#1b2b52] grid grid-cols-3 gap-2.5 text-center">
              <div className="p-2 rounded-xl bg-[#091122] border border-[#162548]">
                <BookOpen className="w-4 h-4 text-blue-400 mx-auto mb-1" />
                <span className="text-[10px] text-slate-300 font-medium block">AI Extraction</span>
              </div>
              <div className="p-2 rounded-xl bg-[#091122] border border-[#162548]">
                <PlaySquare className="w-4 h-4 text-indigo-400 mx-auto mb-1" />
                <span className="text-[10px] text-slate-300 font-medium block">Real Videos</span>
              </div>
              <div className="p-2 rounded-xl bg-[#091122] border border-[#162548]">
                <CalendarDays className="w-4 h-4 text-purple-400 mx-auto mb-1" />
                <span className="text-[10px] text-slate-300 font-medium block">Daily Plans</span>
              </div>
            </div>
          </div>

          {/* Security Notice Footer */}
          <div className="mt-6 text-center space-y-1">
            <div className="inline-flex items-center gap-1.5 text-xs text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Protected with Supabase Auth & Asymmetric ES256 Signatures</span>
            </div>
            <p className="text-[11px] text-slate-400 m-0">
              Your academic data is securely isolated to your authenticated account.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-6 py-4 text-center text-xs text-slate-400 border-t border-[#152342]/60 z-10">
        SyllabusSync AI • Built with AWS Strands Agents SDK & Supabase Auth
      </footer>
    </div>
  );
};

