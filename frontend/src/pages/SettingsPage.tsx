import React, { useState, useEffect } from 'react';
import { 
  Check, 
  Calendar, 
  Moon, 
  Sun, 
  Server, 
  ShieldCheck, 
  AlertCircle,
  ChevronDown,
  Sparkles, 
  Save, 
  Loader2,
  Activity,
  Play,
  RefreshCw,
  Database,
  Cpu,
  Film
} from 'lucide-react';
import type { 
  HealthResponse, 
  UserPreferences,
  SystemDiagnosticsResponse,
  DiagnosticTestResult 
} from '../types';
import { apiService } from '../services/api';

interface SettingsPageProps {
  health?: HealthResponse | null;
  preferences?: UserPreferences;
  onSavePreferences?: (prefs: UserPreferences) => void;
}

const DEFAULT_PREFERENCES: UserPreferences = {
  preferredLanguage: 'English',
  lessonStyle: 'In-depth',
  dailyStudyAvailability: '2-4 hours',
  examDate: '2026-05-15',
  theme: 'dark',
  studyReminders: true,
  deadlineAlerts: true,
  autoSaveProgress: true,
};

export const SettingsPage: React.FC<SettingsPageProps> = ({ 
  health: _health,
  preferences = DEFAULT_PREFERENCES,
  onSavePreferences,
}) => {
  const [formData, setFormData] = useState<UserPreferences>(preferences);
  const [isSaved, setIsSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Diagnostics state
  const [diagnostics, setDiagnostics] = useState<SystemDiagnosticsResponse | null>(null);
  const [isLoadingDiagnostics, setIsLoadingDiagnostics] = useState(false);
  const [diagnosticsError, setDiagnosticsError] = useState<string | null>(null);
  const [youtubeTestResult, setYoutubeTestResult] = useState<DiagnosticTestResult | null>(null);
  const [isTestingYouTube, setIsTestingYouTube] = useState(false);
  const [strandsTestResult, setStrandsTestResult] = useState<DiagnosticTestResult | null>(null);
  const [isTestingStrands, setIsTestingStrands] = useState(false);

  // Clean up any legacy shared admin key from browser localStorage to enforce security policies
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('syllabussync_admin_key');
    }
  }, []);

  const fetchDiagnostics = async () => {
    setIsLoadingDiagnostics(true);
    setDiagnosticsError(null);
    try {
      const data = await apiService.getDiagnostics();
      setDiagnostics(data);
    } catch (err: any) {
      setDiagnostics(null);
      if (err.status === 401) {
        setDiagnosticsError('Authentication required. Please sign in to view live service diagnostics.');
      } else {
        setDiagnosticsError(err.message || 'Failed to retrieve live system diagnostics.');
      }
    } finally {
      setIsLoadingDiagnostics(false);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  const handleTestYouTube = async () => {
    setIsTestingYouTube(true);
    setYoutubeTestResult(null);
    try {
      const res = await apiService.testYouTubeApi();
      setYoutubeTestResult(res);
      await fetchDiagnostics();
    } catch (err: any) {
      setYoutubeTestResult({
        service: 'YouTube Data API v3',
        tested: true,
        status: 'error',
        message: err.message || 'Live probe failed.',
        latency_ms: 0,
      });
    } finally {
      setIsTestingYouTube(false);
    }
  };

  const handleTestStrands = async () => {
    setIsTestingStrands(true);
    setStrandsTestResult(null);
    try {
      const res = await apiService.testStrandsModel();
      setStrandsTestResult(res);
      await fetchDiagnostics();
    } catch (err: any) {
      setStrandsTestResult({
        service: 'Strands Agents SDK',
        tested: true,
        status: 'error',
        message: err.message || 'Model probe failed.',
        latency_ms: 0,
      });
    } finally {
      setIsTestingStrands(false);
    }
  };

  // Sync with backend SQLite on mount
  useEffect(() => {
    let isMounted = true;
    const fetchBackendSettings = async () => {
      try {
        const backendSettings = await apiService.getSettings();
        if (isMounted) {
          const mapped: UserPreferences = {
            preferredLanguage: backendSettings.preferred_language,
            lessonStyle: backendSettings.lesson_style,
            dailyStudyAvailability: backendSettings.daily_study_availability,
            examDate: backendSettings.exam_date,
            theme: backendSettings.theme,
            studyReminders: backendSettings.study_reminders,
            deadlineAlerts: backendSettings.deadline_alerts,
            autoSaveProgress: backendSettings.auto_save_progress,
          };
          setFormData(mapped);
          if (onSavePreferences) onSavePreferences(mapped);
        }
      } catch {
        // Fallback to local state if backend unreachable
      }
    };

    fetchBackendSettings();
    return () => { isMounted = false; };
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    // Convert availability string to target minutes
    let targetMin = 120;
    if (formData.dailyStudyAvailability.includes('30-60')) targetMin = 60;
    else if (formData.dailyStudyAvailability.includes('1-2')) targetMin = 90;
    else if (formData.dailyStudyAvailability.includes('2-4')) targetMin = 180;
    else if (formData.dailyStudyAvailability.includes('4+')) targetMin = 240;

    try {
      await apiService.updateSettings({
        preferred_language: formData.preferredLanguage,
        lesson_style: formData.lessonStyle,
        daily_study_availability: formData.dailyStudyAvailability,
        daily_target_minutes: targetMin,
        exam_date: formData.examDate,
        study_days: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        theme: formData.theme,
        study_reminders: formData.studyReminders,
        deadline_alerts: formData.deadlineAlerts,
        auto_save_progress: formData.autoSaveProgress,
      });
    } catch {
      // Continue to local save
    }

    if (onSavePreferences) {
      onSavePreferences(formData);
    }
    try {
      localStorage.setItem('syllabussync_user_preferences', JSON.stringify(formData));
    } catch {
      // Ignore
    }

    setIsSaving(false);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* Header */}
      <div>
        <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight m-0">
          Settings
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1 m-0">
          Customize your learning experience.
        </p>
      </div>

      {/* Main 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Learning Preferences */}
        <div className="rounded-2xl bg-[#0b1429]/80 border border-[#18284e] p-5 sm:p-6 space-y-5">
          <div className="flex items-center gap-2 border-b border-[#18284e] pb-3">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm sm:text-base font-bold text-white m-0">
              Learning Preferences
            </h3>
          </div>

          <div className="space-y-4">
            {/* Preferred Video Language */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300 block">
                Preferred Video Language
              </label>
              <div className="relative">
                <select
                  value={formData.preferredLanguage}
                  onChange={(e) => setFormData({ ...formData, preferredLanguage: e.target.value })}
                  className="w-full appearance-none rounded-xl bg-[#070b14] border border-[#1b2b52] px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500 transition cursor-pointer"
                >
                  <option value="English">English</option>
                  <option value="Hindi">Hindi</option>
                  <option value="Spanish">Spanish</option>
                  <option value="French">French</option>
                  <option value="German">German</option>
                  <option value="Tamil">Tamil</option>
                  <option value="Telugu">Telugu</option>
                </select>
                <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            {/* Preferred Lesson Style */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300 block">
                Preferred Lesson Style
              </label>
              <div className="relative">
                <select
                  value={formData.lessonStyle}
                  onChange={(e) => setFormData({ ...formData, lessonStyle: e.target.value })}
                  className="w-full appearance-none rounded-xl bg-[#070b14] border border-[#1b2b52] px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500 transition cursor-pointer"
                >
                  <option value="In-depth">In-depth (Comprehensive theory & code)</option>
                  <option value="Beginner-friendly">Beginner-friendly (Gentle introduction)</option>
                  <option value="Fast-paced">Fast-paced (Crash courses & key points)</option>
                  <option value="Practical">Practical (Hands-on projects & exercises)</option>
                </select>
                <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            {/* Daily Study Availability */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300 block">
                Daily Study Availability
              </label>
              <div className="relative">
                <select
                  value={formData.dailyStudyAvailability}
                  onChange={(e) => setFormData({ ...formData, dailyStudyAvailability: e.target.value })}
                  className="w-full appearance-none rounded-xl bg-[#070b14] border border-[#1b2b52] px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500 transition cursor-pointer"
                >
                  <option value="30-60 mins">30 - 60 mins</option>
                  <option value="1-2 hours">1 - 2 hours</option>
                  <option value="2-4 hours">2 - 4 hours</option>
                  <option value="4+ hours">4+ hours</option>
                </select>
                <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            {/* Exam Date */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300 block">
                Exam Date
              </label>
              <div className="relative">
                <input
                  type="date"
                  value={formData.examDate}
                  onChange={(e) => setFormData({ ...formData, examDate: e.target.value })}
                  className="w-full rounded-xl bg-[#070b14] border border-[#1b2b52] px-3.5 py-2 text-xs text-white focus:outline-none focus:border-blue-500 transition [color-scheme:dark]"
                />
                <Calendar className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
              <p className="text-[10px] text-slate-400 m-0">
                Used to calculate pace and target milestones.
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: App Preferences */}
        <div className="rounded-2xl bg-[#0b1429]/80 border border-[#18284e] p-5 sm:p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-[#18284e] pb-3">
            <h3 className="text-sm sm:text-base font-bold text-white m-0">
              App Preferences
            </h3>
          </div>

          {/* Theme Selector */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-300 block">
              Theme
            </label>
            <div className="inline-flex p-1 rounded-xl bg-[#070b14] border border-[#1b2b52]">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, theme: 'dark' })}
                className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer ${
                  formData.theme === 'dark'
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Moon className="w-3.5 h-3.5" />
                <span>Dark</span>
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, theme: 'light' })}
                className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer ${
                  formData.theme === 'light'
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sun className="w-3.5 h-3.5" />
                <span>Light</span>
              </button>
            </div>
          </div>

          {/* Notifications Toggles */}
          <div className="space-y-4 pt-1">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
              Notifications
            </label>

            {/* Study Reminders */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-slate-200 m-0">Study reminders</p>
                <p className="text-[10px] text-slate-400 m-0">Daily notification for your scheduled study session</p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={formData.studyReminders}
                onClick={() => setFormData({ ...formData, studyReminders: !formData.studyReminders })}
                className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  formData.studyReminders ? 'bg-blue-600' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    formData.studyReminders ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Deadline Alerts */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-slate-200 m-0">Deadline alerts</p>
                <p className="text-[10px] text-slate-400 m-0">Warning as exam date approaches</p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={formData.deadlineAlerts}
                onClick={() => setFormData({ ...formData, deadlineAlerts: !formData.deadlineAlerts })}
                className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  formData.deadlineAlerts ? 'bg-blue-600' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    formData.deadlineAlerts ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Auto-Save Progress */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-slate-200 m-0">Auto-save progress</p>
                <p className="text-[10px] text-slate-400 m-0">Automatically persist task completions and roadmap edits</p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={formData.autoSaveProgress}
                onClick={() => setFormData({ ...formData, autoSaveProgress: !formData.autoSaveProgress })}
                className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  formData.autoSaveProgress ? 'bg-blue-600' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    formData.autoSaveProgress ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Action Row */}
          <div className="pt-3 flex items-center justify-end gap-3">
            {isSaved && (
              <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                <Check className="w-3.5 h-3.5" />
                <span>Saved successfully!</span>
              </span>
            )}
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-blue-600/25 transition cursor-pointer"
            >
              {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
              <span>{isSaving ? 'Saving...' : 'Save Settings'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* System Diagnostics & Live Verification Probes Section */}
      <div className="rounded-2xl bg-[#091122]/90 border border-[#18284e] p-4 sm:p-5 space-y-4 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#18284e] pb-3">
          <div className="flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-blue-400" />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm sm:text-base font-bold text-white m-0">
                  System Diagnostics & Service Health
                </h3>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase tracking-wider ${
                  diagnostics?.status === 'healthy' || diagnostics?.status === 'success'
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    : diagnosticsError
                    ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                    : 'bg-slate-500/15 text-slate-300 border border-slate-500/30'
                }`}>
                  {diagnostics?.status || (diagnosticsError ? 'Unavailable' : 'Checking')}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 m-0">
                Live status and zero-secret probes for backend, database, Strands agent, and YouTube API.
              </p>
            </div>
          </div>

          <button
            onClick={fetchDiagnostics}
            disabled={isLoadingDiagnostics}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#0f1d38] hover:bg-[#162a52] text-slate-300 text-xs font-medium border border-[#1e3462] transition cursor-pointer self-start sm:self-auto shrink-0"
            title="Refresh system diagnostics"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${isLoadingDiagnostics ? 'animate-spin' : ''}`} />
            <span>Refresh Diagnostics</span>
          </button>
        </div>

        {/* Diagnostics Error Banner */}
        {diagnosticsError && (
          <div className="rounded-xl bg-amber-950/20 border border-amber-500/30 p-3.5 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-xs font-semibold text-amber-200 m-0">
                Live Diagnostics Unavailable
              </p>
              <p className="text-[11px] text-amber-300/80 leading-relaxed m-0">
                {diagnosticsError}
              </p>
            </div>
          </div>
        )}

        {/* 4 Diagnostics Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* Card 1: FastAPI Backend */}
          <div className="rounded-xl bg-[#070b14] border border-[#1b2b52] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-indigo-400 font-semibold">
                <Server className="w-4 h-4" />
                <span>FastAPI Service</span>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-md font-mono ${
                diagnostics
                  ? (diagnostics.backend.status === 'ok' || diagnostics.backend.status === 'healthy'
                      ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/50'
                      : 'bg-amber-950/40 text-amber-300 border border-amber-800/50')
                  : 'bg-slate-800 text-slate-400'
              }`}>
                {diagnostics?.backend.status || (isLoadingDiagnostics ? 'checking' : 'unavailable')}
              </span>
            </div>

            <div className="space-y-1.5 text-slate-300 font-mono text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-400">Environment:</span>
                <span className="text-white font-semibold">
                  {diagnostics ? diagnostics.backend.environment : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">App Version:</span>
                <span className="text-white">
                  {diagnostics ? diagnostics.backend.version : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Health Status:</span>
                <span className={diagnostics ? 'text-emerald-400 font-bold' : 'text-slate-500 font-mono'}>
                  {diagnostics ? diagnostics.backend.status : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
            </div>
          </div>

          {/* Card 2: Database */}
          <div className="rounded-xl bg-[#070b14] border border-[#1b2b52] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-blue-400 font-semibold">
                <Database className="w-4 h-4" />
                <span>Database</span>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-md font-mono ${
                diagnostics?.database.status === 'connected'
                  ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/50'
                  : 'bg-slate-800 text-slate-400'
              }`}>
                {diagnostics?.database.status || (isLoadingDiagnostics ? 'checking' : 'unavailable')}
              </span>
            </div>

            <div className="space-y-1.5 text-slate-300 font-mono text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-400">Engine:</span>
                <span className="text-white font-semibold">
                  {diagnostics ? diagnostics.database.engine : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Tables Count:</span>
                <span className="text-white">
                  {diagnostics ? `${diagnostics.database.tables_count} tables` : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Connection:</span>
                <span className={diagnostics?.database.status === 'connected' ? 'text-emerald-400 font-bold' : 'text-slate-500 font-mono'}>
                  {diagnostics ? (diagnostics.database.status === 'connected' ? 'Active & Verified' : 'Error') : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
            </div>
          </div>

          {/* Card 3: Strands Agents SDK */}
          <div className="rounded-xl bg-[#070b14] border border-[#1b2b52] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-violet-400 font-semibold">
                <Cpu className="w-4 h-4" />
                <span>Strands Agents SDK</span>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-md font-mono ${
                diagnostics?.strands.credentials_configured
                  ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/50'
                  : 'bg-slate-800 text-slate-400'
              }`}>
                {diagnostics?.strands.active_mode || (isLoadingDiagnostics ? 'checking' : 'unavailable')}
              </span>
            </div>

            <div className="space-y-1.5 text-slate-300 font-mono text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-400">Provider:</span>
                <span className="text-white">
                  {diagnostics ? diagnostics.strands.provider : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Model:</span>
                <span className="text-white font-semibold truncate max-w-[200px]" title={diagnostics?.strands.model}>
                  {diagnostics ? diagnostics.strands.model : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">AWS Region:</span>
                <span className="text-white">
                  {diagnostics ? (diagnostics.strands.region || '—') : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Credentials:</span>
                <span className={diagnostics?.strands.credentials_configured ? 'text-emerald-400 font-bold' : 'text-slate-400'}>
                  {diagnostics ? diagnostics.strands.credentials_summary : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Connectivity:</span>
                <span className={`font-bold ${
                  diagnostics?.strands.connectivity_status === 'verified'
                    ? 'text-emerald-400'
                    : diagnostics?.strands.connectivity_status === 'unverified'
                    ? 'text-sky-400'
                    : diagnostics?.strands.connectivity_status === 'missing'
                    ? 'text-amber-400'
                    : 'text-rose-400'
                }`}>
                  {diagnostics
                    ? (diagnostics.strands.connectivity_status === 'verified'
                        ? 'Verified (Live)'
                        : diagnostics.strands.connectivity_status === 'unverified'
                        ? 'Configured (Unprobed)'
                        : diagnostics.strands.connectivity_status === 'missing'
                        ? 'Credentials Missing'
                        : 'Connection Failed')
                    : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
            </div>

            {/* Strands Live Probe Button */}
            <div className="pt-2 border-t border-[#142347]">
              <div className="flex items-center justify-between gap-2">
                <button
                  onClick={handleTestStrands}
                  disabled={isTestingStrands}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600/20 hover:bg-violet-600 text-violet-300 hover:text-white border border-violet-500/30 text-[11px] font-medium transition cursor-pointer"
                >
                  {isTestingStrands ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Probing Bedrock...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 text-violet-400" />
                      <span>Test Strands Agent Model</span>
                    </>
                  )}
                </button>

                {strandsTestResult && (
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-md ${
                    strandsTestResult.status === 'success'
                      ? 'bg-emerald-950/50 text-emerald-300'
                      : strandsTestResult.status === 'model_not_available'
                      ? 'bg-amber-950/50 text-amber-300'
                      : 'bg-rose-950/50 text-rose-300'
                  }`}>
                    {strandsTestResult.latency_ms} ms
                  </span>
                )}
              </div>

              {strandsTestResult && (
                <div className={`mt-2 p-2.5 rounded-lg text-[10px] font-mono leading-relaxed ${
                  strandsTestResult.status === 'success'
                    ? 'bg-emerald-950/30 text-emerald-300 border border-emerald-800/40'
                    : strandsTestResult.status === 'model_not_available'
                    ? 'bg-amber-950/30 text-amber-300 border border-amber-800/40'
                    : 'bg-rose-950/30 text-rose-300 border border-rose-800/40'
                }`}>
                  <p className="m-0 font-bold">{strandsTestResult.message}</p>
                  {strandsTestResult.status === 'model_not_available' && (
                    <p className="mt-1.5 text-[9.5px] text-amber-400/90 font-sans">
                      Tip: Confirm Amazon Nova Lite (<code className="text-amber-200">amazon.nova-lite-v1:0</code>) is enabled under Bedrock Model Access in region <code className="text-amber-200">ap-southeast-2</code>.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Card 4: YouTube Data API v3 */}
          <div className="rounded-xl bg-[#070b14] border border-[#1b2b52] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-rose-400 font-semibold">
                <Film className="w-4 h-4" />
                <span>YouTube Data API v3</span>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-md font-mono ${
                diagnostics?.youtube.key_configured
                  ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/50'
                  : 'bg-slate-800 text-slate-400'
              }`}>
                {diagnostics?.youtube.active_mode || (isLoadingDiagnostics ? 'checking' : 'unavailable')}
              </span>
            </div>

            <div className="space-y-1.5 text-slate-300 font-mono text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-400">Active Mode:</span>
                <span className={diagnostics?.youtube.active_mode === 'live' ? 'text-emerald-400 font-bold' : 'text-slate-300'}>
                  {diagnostics
                    ? (diagnostics.youtube.active_mode === 'live' ? 'Live YouTube API' : 'Dev Fallback')
                    : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">API Key:</span>
                <span className={diagnostics?.youtube.key_configured ? 'text-emerald-400 font-bold' : 'text-slate-400'}>
                  {diagnostics ? diagnostics.youtube.key_summary : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Connectivity:</span>
                <span className={`font-bold ${
                  diagnostics?.youtube.connectivity_status === 'verified'
                    ? 'text-emerald-400'
                    : diagnostics?.youtube.connectivity_status === 'unverified'
                    ? 'text-sky-400'
                    : diagnostics?.youtube.connectivity_status === 'quota_exceeded'
                    ? 'text-amber-400'
                    : 'text-rose-400'
                }`}>
                  {diagnostics
                    ? (diagnostics.youtube.connectivity_status === 'verified'
                        ? 'Verified (Live)'
                        : diagnostics.youtube.connectivity_status === 'unverified'
                        ? 'Configured (Unprobed)'
                        : diagnostics.youtube.connectivity_status === 'quota_exceeded'
                        ? 'Quota Exceeded'
                        : diagnostics.youtube.connectivity_status === 'missing'
                        ? 'Key Missing'
                        : 'Invalid / Expired')
                    : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Cached Queries:</span>
                <span className="text-white">
                  {diagnostics ? `${diagnostics.youtube.cached_queries_count} queries` : (isLoadingDiagnostics ? 'Checking...' : 'Unavailable')}
                </span>
              </div>
            </div>

            {/* YouTube Live Probe Button */}
            <div className="pt-2 border-t border-[#142347]">
              <div className="flex items-center justify-between gap-2">
                <button
                  onClick={handleTestYouTube}
                  disabled={isTestingYouTube}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-500/30 text-[11px] font-medium transition cursor-pointer"
                >
                  {isTestingYouTube ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Probing YouTube...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 text-rose-400" />
                      <span>Test YouTube API Live</span>
                    </>
                  )}
                </button>

                {youtubeTestResult && (
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-md ${
                    youtubeTestResult.status === 'success' ? 'bg-emerald-950/50 text-emerald-300' : 'bg-rose-950/50 text-rose-300'
                  }`}>
                    {youtubeTestResult.latency_ms} ms
                  </span>
                )}
              </div>

              {youtubeTestResult && (
                <div className={`mt-2 p-2 rounded-lg text-[10px] font-mono leading-relaxed ${
                  youtubeTestResult.status === 'success' ? 'bg-emerald-950/30 text-emerald-300 border border-emerald-800/40' : 'bg-rose-950/30 text-rose-300 border border-rose-800/40'
                }`}>
                  <p className="m-0 font-bold">{youtubeTestResult.message}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Zero-Leak Security Guardrail Notice */}
        <div className="rounded-xl bg-[#070b14] border border-emerald-500/30 p-3.5 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <h4 className="text-xs font-bold text-white m-0">Zero-Secret Exposure Security Policy</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed m-0">
              Model API keys, Google Cloud tokens, and YouTube credentials are isolated strictly on the local backend server. No secret tokens or raw stack traces are sent to the browser or stored in git.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
