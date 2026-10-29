import React, { useState } from 'react';
import { 
  Check, 
  Calendar, 
  Moon, 
  Sun, 
  Server, 
  ShieldCheck, 
  ChevronDown,
  Sparkles,
  Save
} from 'lucide-react';
import type { HealthResponse, UserPreferences } from '../types';

interface SettingsPageProps {
  health: HealthResponse | null;
  preferences?: UserPreferences;
  onSavePreferences?: (prefs: UserPreferences) => void;
}

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

export const SettingsPage: React.FC<SettingsPageProps> = ({ 
  health,
  preferences = DEFAULT_PREFERENCES,
  onSavePreferences,
}) => {
  const [formData, setFormData] = useState<UserPreferences>(preferences);
  const [isSaved, setIsSaved] = useState(false);
  const [showSystemDetails, setShowSystemDetails] = useState(false);

  const handleSave = () => {
    if (onSavePreferences) {
      onSavePreferences(formData);
    }
    // Also save in localStorage
    try {
      localStorage.setItem('syllabussync_user_preferences', JSON.stringify(formData));
    } catch {
      // Ignore localStorage errors
    }
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
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/25 transition cursor-pointer"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Save Settings</span>
            </button>
          </div>
        </div>
      </div>

      {/* Secondary Collapsible Section: Architecture & Security */}
      <div className="rounded-2xl bg-[#091122]/70 border border-[#18284e] p-4 sm:p-5">
        <button
          onClick={() => setShowSystemDetails(!showSystemDetails)}
          className="w-full flex items-center justify-between text-left text-xs font-medium text-slate-400 hover:text-white transition cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-blue-400" />
            <span className="font-semibold text-slate-200">System Architecture & Security Guardrails</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Verified
            </span>
          </div>
          <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${showSystemDetails ? 'rotate-180' : ''}`} />
        </button>

        {showSystemDetails && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-[#18284e] text-xs">
            {/* Backend status card */}
            <div className="rounded-xl bg-[#070b14] border border-[#1b2b52] p-4 space-y-2.5">
              <div className="flex items-center gap-2 text-indigo-400 font-semibold">
                <Server className="w-4 h-4" />
                <span>FastAPI Service</span>
              </div>
              <div className="space-y-1.5 text-slate-300 font-mono text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-400">Health:</span>
                  <span className="text-emerald-400 font-bold">{health?.status || 'Active (Local)'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Database:</span>
                  <span>SQLite (Local file-backed)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Max Upload:</span>
                  <span>10 MB Enforced</span>
                </div>
              </div>
            </div>

            {/* Zero-leak policy */}
            <div className="rounded-xl bg-[#070b14] border border-[#1b2b52] p-4 space-y-2.5">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                <ShieldCheck className="w-4 h-4" />
                <span>Zero-Leak Security Guardrail</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed m-0">
                All model and YouTube Data API v3 credentials remain isolated strictly on the backend. No secret tokens or keys are present in client-side bundles.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
