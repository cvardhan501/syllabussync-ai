import React, { useState, useEffect, useCallback, useRef, Suspense, lazy } from 'react';
import { 
  LayoutDashboard, 
  BookOpen, 
  PlaySquare, 
  CalendarDays, 
  BarChart3, 
  Settings as SettingsIcon,
  GraduationCap
} from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { GuideModal } from './components/GuideModal';

// Code-split pages for sub-second bundle loading and optimized initial paint
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const CoursesPage = lazy(() => import('./pages/CoursesPage').then(m => ({ default: m.CoursesPage })));
const SyllabusPage = lazy(() => import('./pages/SyllabusPage').then(m => ({ default: m.SyllabusPage })));
const VideoLibraryPage = lazy(() => import('./pages/VideoLibraryPage').then(m => ({ default: m.VideoLibraryPage })));
const StudyPlanPage = lazy(() => import('./pages/StudyPlanPage').then(m => ({ default: m.StudyPlanPage })));
const ProgressPage = lazy(() => import('./pages/ProgressPage').then(m => ({ default: m.ProgressPage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })));

const PageLoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center min-h-[350px]">
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      <span className="text-xs text-slate-400">Loading view...</span>
    </div>
  </div>
);
import type { 
  NavigationTab, 
  HealthResponse, 
  SyllabusUploadResponse, 
  SyllabusAnalysisResponse,
  UserPreferences,
  StudyPlanResponse,
  ResourceDiscoveryResponse,
  Course
} from './types';
import { apiService, ApiErrorResponse } from './services/api';
import { getCurrentSession, onAuthStateChange, signOut, type User, type Session } from './services/supabase';

const DEFAULT_PREFERENCES: UserPreferences = {
  preferredLanguage: 'English',
  lessonStyle: 'In-depth',
  dailyStudyAvailability: '2-4 hours',
  theme: 'dark',
  studyReminders: true,
  deadlineAlerts: true,
  autoSaveProgress: true,
};

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavigationTab>('dashboard');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isGuideModalOpen, setIsGuideModalOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [activeCourse, setActiveCourseState] = useState<Course | null>(() => {
    try {
      const saved = localStorage.getItem('syllabussync_active_course');
      if (saved) return JSON.parse(saved);
    } catch {
      // Ignore
    }
    return null;
  });

  // Supabase Authentication & Session State
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [isDevBypass, setIsDevBypassState] = useState<boolean>(() => {
    try {
      return localStorage.getItem('syllabussync_dev_bypass') === 'true';
    } catch {
      return false;
    }
  });

  const setIsDevBypass = (val: boolean) => {
    setIsDevBypassState(val);
    try {
      if (val) localStorage.setItem('syllabussync_dev_bypass', 'true');
      else localStorage.removeItem('syllabussync_dev_bypass');
    } catch {}
  };

  const [uploadedSyllabus, setUploadedSyllabus] = useState<SyllabusUploadResponse | null>(null);
  const [analyzedSyllabus, setAnalyzedSyllabusState] = useState<SyllabusAnalysisResponse | null>(() => {
    try {
      const saved = localStorage.getItem('syllabussync_active_syllabus');
      if (saved) return JSON.parse(saved);
    } catch {
      // Ignore parse errors
    }
    return null;
  });

  const setAnalyzedSyllabus = (data: SyllabusAnalysisResponse | null) => {
    setAnalyzedSyllabusState(data);
    try {
      if (data) {
        localStorage.setItem('syllabussync_active_syllabus', JSON.stringify(data));
      } else {
        localStorage.removeItem('syllabussync_active_syllabus');
      }
    } catch {
      // Ignore storage errors
    }
  };

  const [studyPlan, setStudyPlan] = useState<StudyPlanResponse | null>(null);
  const [discoveryData, setDiscoveryData] = useState<ResourceDiscoveryResponse | null>(null);
  const [preferences, setPreferences] = useState<UserPreferences>(() => {
    try {
      const saved = localStorage.getItem('syllabussync_user_preferences');
      if (saved) {
        return { ...DEFAULT_PREFERENCES, ...JSON.parse(saved) };
      }
    } catch {
      // Fallback to defaults
    }
    return DEFAULT_PREFERENCES;
  });

  const setActiveCourse = (course: Course | null) => {
    setActiveCourseState(course);
    setStudyPlan(null); // Clear active study plan so switching courses never displays stale tasks
    try {
      if (course) {
        localStorage.setItem('syllabussync_active_course', JSON.stringify(course));
      } else {
        localStorage.removeItem('syllabussync_active_course');
      }
    } catch {
      // Ignore
    }
  };

  const refreshCourses = async (deletedCourseId?: string) => {
    try {
      const res = await apiService.getCourses(true);
      const updatedCourses = res.courses || [];
      setCourses(updatedCourses);

      const currentActiveId = activeCourse?.id;
      const isCurrentActiveDeleted = Boolean(deletedCourseId && currentActiveId === deletedCourseId);
      const isCurrentActiveMissing = !currentActiveId || !updatedCourses.some((c) => c.id === currentActiveId);

      if (isCurrentActiveDeleted || isCurrentActiveMissing) {
        if (updatedCourses.length > 0) {
          const nextActive = updatedCourses.find((c) => !c.is_archived) || updatedCourses[0];
          setActiveCourse(nextActive);
        } else {
          setActiveCourse(null);
          setAnalyzedSyllabusState(null);
          setStudyPlan(null);
          setDiscoveryData(null);
          localStorage.removeItem('syllabussync_active_course');
          localStorage.removeItem('syllabussync_active_syllabus');
        }
      }
    } catch {
      // Ignore
    }
  };

  // 1. Session Restoration & Auth Listener
  useEffect(() => {
    let isMounted = true;

    const restoreSession = async () => {
      try {
        const initialSession = await getCurrentSession();
        if (isMounted) {
          setSession(initialSession);
          setUser(initialSession?.user ?? null);
        }
      } catch (err) {
        console.warn('[Auth] Failed to restore session:', err);
      } finally {
        if (isMounted) {
          setIsCheckingSession(false);
        }
      }
    };

    restoreSession();

    // Clean OAuth hash fragments from URL (prevents redirect loop / stale tokens in address bar)
    if (typeof window !== 'undefined' && window.location.hash.includes('access_token')) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search);
    }

    // Subscribe to Supabase Auth State Transitions
    const { data: authSubscription } = onAuthStateChange((event, newSession) => {
      if (!isMounted) return;
      setSession(newSession);
      setUser(newSession?.user ?? null);
      setIsCheckingSession(false);

      if (event === 'SIGNED_IN') {
        refreshCourses();
      } else if (event === 'SIGNED_OUT') {
        setCourses([]);
        setActiveCourseState(null);
        setAnalyzedSyllabusState(null);
        localStorage.removeItem('syllabussync_active_course');
        localStorage.removeItem('syllabussync_active_syllabus');
      }
    });

    // Handle 401 Unauthorized from backend
    const handleUnauthorized = () => {
      console.warn('[Auth] Received 401 from backend: re-authentication required.');
      if (session) {
        setSession(null);
        setUser(null);
      }
    };
    window.addEventListener('syllabussync:unauthorized', handleUnauthorized);

    return () => {
      isMounted = false;
      authSubscription?.subscription?.unsubscribe();
      window.removeEventListener('syllabussync:unauthorized', handleUnauthorized);
    };
  }, []);

  // When session or dev bypass changes, refresh courses
  useEffect(() => {
    if (session || isDevBypass) {
      refreshCourses();
    }
  }, [session, isDevBypass]);

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (err) {
      console.warn('[Auth] Error signing out:', err);
    }
    setSession(null);
    setUser(null);
    setIsDevBypass(false);
    setCourses([]);
    setActiveCourse(null);
    setAnalyzedSyllabus(null);
    setCurrentTab('dashboard');
  };

  // Load course syllabus when active course changes
  useEffect(() => {
    let isMounted = true;
    if (!activeCourse) return;
    const targetSid = activeCourse.syllabus_id || activeCourse.id;
    if (!targetSid) return;

    const loadCourseData = async () => {
      try {
        const fresh = await apiService.getSyllabus(targetSid);
        if (isMounted) {
          setAnalyzedSyllabusState(fresh);
          localStorage.setItem('syllabussync_active_syllabus', JSON.stringify(fresh));
        }
      } catch {
        // Fallback
      }
    };

    loadCourseData();
    return () => {
      isMounted = false;
    };
  }, [activeCourse?.id, activeCourse?.syllabus_id]);

  // Re-sync active syllabus with SQLite on mount
  useEffect(() => {
    let isMounted = true;
    if (!analyzedSyllabus?.syllabus_id) return;

    const syncSyllabus = async () => {
      try {
        const fresh = await apiService.getSyllabus(analyzedSyllabus.syllabus_id);
        if (isMounted) {
          setAnalyzedSyllabusState(fresh);
          localStorage.setItem('syllabussync_active_syllabus', JSON.stringify(fresh));
        }
      } catch (err: any) {
        if (isMounted && err instanceof ApiErrorResponse && err.status === 404) {
          setAnalyzedSyllabus(null);
        }
      }
    };

    syncSyllabus();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleUpdatePreferences = (newPrefs: UserPreferences) => {
    setPreferences(newPrefs);
    try {
      localStorage.setItem('syllabussync_user_preferences', JSON.stringify(newPrefs));
    } catch {
      // Ignore storage errors
    }
  };

  // Monotonic sequence and concurrency guard to prevent overlapping polls and stale state overwrite
  const isPollingHealthRef = useRef(false);
  const healthSequenceRef = useRef(0);

  // Poll or check health with sequencing and deduplication
  const checkHealth = useCallback(async (force = false) => {
    if (isPollingHealthRef.current && !force) return;
    isPollingHealthRef.current = true;
    const reqSeq = ++healthSequenceRef.current;

    try {
      const data = await apiService.getHealth(force);
      // Strictly ignore stale responses from earlier requests
      if (reqSeq >= healthSequenceRef.current) {
        setHealth(data);
        setHealthError(null);
      }
    } catch (err: any) {
      if (reqSeq >= healthSequenceRef.current) {
        setHealth(null);
        setHealthError(err?.message || 'FastAPI Backend Offline');
      }
    } finally {
      isPollingHealthRef.current = false;
    }
  }, []);

  useEffect(() => {
    checkHealth(true);
    // Poll every 10 seconds for timely recovery after restart
    const interval = setInterval(() => checkHealth(false), 10000);

    // Recheck on browser window focus or network reconnect without duplicate stacking
    const handleRecheck = () => {
      checkHealth(false);
    };
    window.addEventListener('focus', handleRecheck);
    window.addEventListener('online', handleRecheck);

    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', handleRecheck);
      window.removeEventListener('online', handleRecheck);
    };
  }, [checkHealth]);

  // Fetch active study plan and discovery resources when syllabus changes
  useEffect(() => {
    let isMounted = true;
    if (!analyzedSyllabus?.syllabus_id) {
      setStudyPlan(null);
      setDiscoveryData(null);
      return;
    }

    const loadData = async () => {
      const [planRes, resourcesRes] = await Promise.allSettled([
        apiService.getStudyPlan(analyzedSyllabus.syllabus_id),
        apiService.getResources(analyzedSyllabus.syllabus_id),
      ]);

      if (!isMounted) return;

      if (planRes.status === 'fulfilled') {
        setStudyPlan(planRes.value);
      } else if (planRes.reason instanceof ApiErrorResponse && planRes.reason.status === 404) {
        setStudyPlan(null);
      }

      if (resourcesRes.status === 'fulfilled') {
        setDiscoveryData(resourcesRes.value);
      } else if (resourcesRes.reason instanceof ApiErrorResponse && resourcesRes.reason.status === 404) {
        setDiscoveryData(null);
      }
    };

    loadData();
    return () => {
      isMounted = false;
    };
  }, [analyzedSyllabus?.syllabus_id]);

  const mobileNavItems: { id: NavigationTab; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'courses', label: 'Courses', icon: GraduationCap },
    { id: 'syllabus', label: 'Syllabus', icon: BookOpen },
    { id: 'videos', label: 'Videos', icon: PlaySquare },
    { id: 'study-plan', label: 'Plan', icon: CalendarDays },
    { id: 'progress', label: 'Progress', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

  // 1. Session verification loading state
  if (isCheckingSession) {
    return (
      <div className="min-h-screen bg-[#070b14] flex flex-col items-center justify-center text-slate-100 antialiased p-4">
        <div className="w-12 h-12 rounded-2xl bg-blue-600 flex items-center justify-center shadow-xl shadow-blue-600/30 text-white mb-4 animate-pulse">
          <GraduationCap className="w-6 h-6" />
        </div>
        <h2 className="text-base font-bold text-white tracking-tight mb-1">SyllabusSync AI</h2>
        <p className="text-xs text-slate-400">Verifying session...</p>
      </div>
    );
  }

  // 2. Unauthenticated user gate
  if (!session && !isDevBypass) {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <LoginPage 
          onBypassDevMode={() => setIsDevBypass(true)} 
          health={health} 
          healthError={healthError} 
        />
      </Suspense>
    );
  }

  return (
    <div className={`min-h-screen ${preferences.theme === 'light' ? 'bg-[#f4f7fc] text-slate-900' : 'bg-[#070b14] text-slate-100'} flex flex-col md:flex-row antialiased selection:bg-blue-600 selection:text-white`}>
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        health={health}
        healthError={healthError}
        onOpenGuideModal={() => setIsGuideModalOpen(true)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          currentTab={currentTab}
          onOpenSidebar={() => setIsSidebarOpen(true)}
          hasSyllabus={!!(uploadedSyllabus || analyzedSyllabus)}
          theme={preferences.theme}
          onToggleTheme={() =>
            handleUpdatePreferences({
              ...preferences,
              theme: preferences.theme === 'dark' ? 'light' : 'dark',
            })
          }
          activeCourse={activeCourse}
          courses={courses}
          onSelectCourse={setActiveCourse}
          onNavigateToCourses={() => setCurrentTab('courses')}
          user={user}
          health={health}
          healthError={healthError}
          onSignOut={handleSignOut}
          onSignIn={() => setIsDevBypass(false)}
        />

        <main className="flex-1 p-4 sm:p-7 overflow-y-auto pb-24 md:pb-8">
          <Suspense fallback={<PageLoadingFallback />}>
            {currentTab === 'dashboard' && (
              <DashboardPage
                onNavigate={setCurrentTab}
                uploadedSyllabus={uploadedSyllabus}
                analyzedSyllabus={analyzedSyllabus}
                studyPlan={studyPlan}
                discoveryData={discoveryData}
              />
            )}

            {currentTab === 'courses' && (
              <CoursesPage
                courses={courses}
                activeCourseId={activeCourse?.id || null}
                onSelectCourse={(c) => {
                  setActiveCourse(c);
                  setCurrentTab('syllabus');
                }}
                onOpenUploadWizard={() => {
                  setActiveCourse(null);
                  setUploadedSyllabus(null);
                  setAnalyzedSyllabus(null);
                  setCurrentTab('syllabus');
                }}
                onRefreshCourses={refreshCourses}
                onNavigate={setCurrentTab}
              />
            )}

            {currentTab === 'syllabus' && (
              <SyllabusPage
                uploadedSyllabus={uploadedSyllabus}
                onSyllabusUploaded={setUploadedSyllabus}
                analyzedSyllabus={analyzedSyllabus}
                onAnalysisComplete={setAnalyzedSyllabus}
                onNavigateToStudyPlan={() => setCurrentTab('study-plan')}
                onCourseCreated={(c) => {
                  refreshCourses();
                  setActiveCourse(c);
                }}
              />
            )}

            {currentTab === 'videos' && (
              <VideoLibraryPage
                analyzedSyllabus={analyzedSyllabus}
                onNavigateToSyllabus={() => setCurrentTab('syllabus')}
                preferredLanguage={preferences.preferredLanguage}
                onDiscoveryUpdated={setDiscoveryData}
                courses={courses}
                activeCourse={activeCourse}
                onSelectCourse={setActiveCourse}
              />
            )}

            {currentTab === 'study-plan' && (
              <StudyPlanPage
                analyzedSyllabus={analyzedSyllabus}
                onNavigate={setCurrentTab}
                examDate={activeCourse?.assessments?.find(a => a.assessment_type === 'end_sem' || a.scope === 'end_sem')?.exam_date || activeCourse?.assessments?.[activeCourse.assessments.length - 1]?.exam_date || studyPlan?.exam_date}
                initialPlan={studyPlan}
                onPlanUpdated={setStudyPlan}
                courses={courses}
                activeCourse={activeCourse}
                onSelectCourse={setActiveCourse}
              />
            )}

            {currentTab === 'progress' && (
              <ProgressPage
                uploadedSyllabus={uploadedSyllabus}
                analyzedSyllabus={analyzedSyllabus}
                studyPlan={studyPlan}
                discoveryData={discoveryData}
                onNavigate={setCurrentTab}
                activeCourse={activeCourse}
                courses={courses}
                onSelectCourse={setActiveCourse}
              />
            )}

            {currentTab === 'settings' && (
              <SettingsPage
                health={health}
                onRefreshHealth={() => checkHealth(true)}
                preferences={preferences}
                onSavePreferences={handleUpdatePreferences}
              />
            )}
          </Suspense>
        </main>
      </div>

      {/* Mobile Bottom Navigation Bar (Matches Screen 9) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#070b14]/95 backdrop-blur-md border-t border-[#152342] px-2 py-1 flex items-center justify-around shadow-2xl">
        {mobileNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setCurrentTab(item.id)}
              className={`flex flex-col items-center justify-center py-1.5 px-2 rounded-xl transition cursor-pointer ${
                isActive
                  ? 'text-blue-400 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <div className={`p-1 rounded-lg ${isActive ? 'bg-blue-600/20 text-blue-400' : ''}`}>
                <Icon className="w-4 h-4" />
              </div>
              <span className="text-[10px] mt-0.5 tracking-tight">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Interactive Guide Modal */}
      <GuideModal
        isOpen={isGuideModalOpen}
        onClose={() => setIsGuideModalOpen(false)}
        onNavigate={setCurrentTab}
      />
    </div>
  );
};

export default App;
