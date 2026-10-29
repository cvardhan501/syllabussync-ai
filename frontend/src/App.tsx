import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  BookOpen, 
  PlaySquare, 
  CalendarDays, 
  BarChart3, 
  Settings as SettingsIcon 
} from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { GuideModal } from './components/GuideModal';
import { DashboardPage } from './pages/DashboardPage';
import { SyllabusPage } from './pages/SyllabusPage';
import { VideoLibraryPage } from './pages/VideoLibraryPage';
import { StudyPlanPage } from './pages/StudyPlanPage';
import { ProgressPage } from './pages/ProgressPage';
import { SettingsPage } from './pages/SettingsPage';
import type { 
  NavigationTab, 
  HealthResponse, 
  SyllabusUploadResponse, 
  SyllabusAnalysisResponse,
  UserPreferences 
} from './types';
import { apiService } from './services/api';

const DEFAULT_PREFERENCES: UserPreferences = {
  preferredLanguage: 'English',
  lessonStyle: 'In-depth',
  dailyStudyAvailability: '2-4 hours',
  examDate: '2026-04-25',
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
  const [uploadedSyllabus, setUploadedSyllabus] = useState<SyllabusUploadResponse | null>(null);
  const [analyzedSyllabus, setAnalyzedSyllabus] = useState<SyllabusAnalysisResponse | null>(null);
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

  const handleUpdatePreferences = (newPrefs: UserPreferences) => {
    setPreferences(newPrefs);
    try {
      localStorage.setItem('syllabussync_user_preferences', JSON.stringify(newPrefs));
    } catch {
      // Ignore storage errors
    }
  };

  // Poll or check health on mount
  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      try {
        const data = await apiService.getHealth();
        if (isMounted) {
          setHealth(data);
          setHealthError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setHealth(null);
          setHealthError(err.message || 'API Offline');
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 20000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const mobileNavItems: { id: NavigationTab; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'syllabus', label: 'Syllabus', icon: BookOpen },
    { id: 'videos', label: 'Videos', icon: PlaySquare },
    { id: 'study-plan', label: 'Plan', icon: CalendarDays },
    { id: 'progress', label: 'Progress', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

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
        />

        <main className="flex-1 p-4 sm:p-7 overflow-y-auto pb-24 md:pb-8">
          {currentTab === 'dashboard' && (
            <DashboardPage
              onNavigate={setCurrentTab}
              uploadedSyllabus={uploadedSyllabus}
              analyzedSyllabus={analyzedSyllabus}
            />
          )}

          {currentTab === 'syllabus' && (
            <SyllabusPage
              uploadedSyllabus={uploadedSyllabus}
              onSyllabusUploaded={setUploadedSyllabus}
              analyzedSyllabus={analyzedSyllabus}
              onAnalysisComplete={setAnalyzedSyllabus}
              onNavigateToStudyPlan={() => setCurrentTab('study-plan')}
            />
          )}

          {currentTab === 'videos' && (
            <VideoLibraryPage
              analyzedSyllabus={analyzedSyllabus}
              onNavigateToSyllabus={() => setCurrentTab('syllabus')}
            />
          )}

          {currentTab === 'study-plan' && (
            <StudyPlanPage
              analyzedSyllabus={analyzedSyllabus}
              onNavigate={setCurrentTab}
              examDate={preferences.examDate}
            />
          )}

          {currentTab === 'progress' && (
            <ProgressPage
              uploadedSyllabus={uploadedSyllabus}
              analyzedSyllabus={analyzedSyllabus}
              onNavigate={setCurrentTab}
            />
          )}

          {currentTab === 'settings' && (
            <SettingsPage
              health={health}
              preferences={preferences}
              onSavePreferences={handleUpdatePreferences}
            />
          )}
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
