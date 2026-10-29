import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardPage } from './pages/DashboardPage';
import { SyllabusPage } from './pages/SyllabusPage';
import { StudyPlanPage } from './pages/StudyPlanPage';
import { ProgressPage } from './pages/ProgressPage';
import { SettingsPage } from './pages/SettingsPage';
import type { 
  NavigationTab, 
  HealthResponse, 
  SyllabusUploadResponse, 
  SyllabusAnalysisResponse 
} from './types';
import { apiService } from './services/api';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavigationTab>('dashboard');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [uploadedSyllabus, setUploadedSyllabus] = useState<SyllabusUploadResponse | null>(null);
  const [analyzedSyllabus, setAnalyzedSyllabus] = useState<SyllabusAnalysisResponse | null>(null);

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

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col md:flex-row">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        health={health}
        healthError={healthError}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          currentTab={currentTab}
          onOpenSidebar={() => setIsSidebarOpen(true)}
          hasSyllabus={!!(uploadedSyllabus || analyzedSyllabus)}
        />

        <main className="flex-1 p-4 sm:p-8 overflow-y-auto">
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

          {currentTab === 'study-plan' && (
            <StudyPlanPage
              uploadedSyllabus={uploadedSyllabus}
              onNavigate={setCurrentTab}
            />
          )}

          {currentTab === 'progress' && (
            <ProgressPage
              uploadedSyllabus={uploadedSyllabus}
              onNavigate={setCurrentTab}
            />
          )}

          {currentTab === 'settings' && (
            <SettingsPage
              health={health}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
