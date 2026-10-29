import React, { useState } from 'react';
import { 
  ShieldCheck, 
  Server, 
  Layers, 
  CheckCircle2, 
  Clock
} from 'lucide-react';
import type { HealthResponse } from '../types';

interface SettingsPageProps {
  health: HealthResponse | null;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ health }) => {
  const [dailyMinutes, setDailyMinutes] = useState(60);
  const [includeWeekends, setIncludeWeekends] = useState(false);
  const [channelLimit, setChannelLimit] = useState<'conservative' | 'balanced' | 'broad'>('conservative');

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight m-0">
          System & Study Settings
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1 m-0">
          Review backend environment configuration, security architecture, and future study planner preferences.
        </p>
      </div>

      {/* Backend & Security Information */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Card 1: Backend Connection */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white m-0">FastAPI Backend Status</h3>
              <p className="text-xs text-slate-400 m-0">Connected service configuration</p>
            </div>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">API Health</span>
              <span className="text-emerald-400 font-medium">
                {health?.status ? `Status: ${health.status}` : 'Offline / Checking'}
              </span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Environment</span>
              <span className="text-slate-200 font-mono">{health?.environment || 'development'}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Max Upload Limit</span>
              <span className="text-slate-200 font-mono">10 MB (Enforced)</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Database Engine</span>
              <span className="text-slate-200 font-mono">SQLite (MVP Local DB)</span>
            </div>
          </div>
        </div>

        {/* Card 2: Security & API Key Guardrails */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white m-0">Security & Key Protection</h3>
              <p className="text-xs text-slate-400 m-0">Zero client-side secrets policy</p>
            </div>
          </div>

          <div className="space-y-2.5 text-xs text-slate-300">
            <p className="m-0 leading-relaxed text-slate-400">
              All external credentials (YouTube Data API v3, Strands SDK) are isolated strictly within
              backend server environment variables (`.env`).
            </p>
            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800/80 space-y-1.5 font-mono text-[11px] text-slate-400">
              <div className="text-emerald-400">✓ No API keys bundled in frontend bundle</div>
              <div className="text-emerald-400">✓ Upload size validated on server boundary</div>
              <div className="text-emerald-400">✓ In-memory parsing; no orphaned disk uploads</div>
            </div>
          </div>
        </div>
      </div>

      {/* Planned Study Preferences */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 space-y-5">
        <div>
          <h3 className="text-base font-bold text-white m-0">
            Study Preferences (Preparation for Phase 3 Planner)
          </h3>
          <p className="text-xs text-slate-400 mt-0.5 m-0">
            These preferences will be passed into the adaptive scheduler when generating daily study blocks.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Daily Target Minutes */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 block">
              Daily Study Target: {dailyMinutes} mins
            </label>
            <input
              type="range"
              min={30}
              max={180}
              step={15}
              value={dailyMinutes}
              onChange={(e) => setDailyMinutes(Number(e.target.value))}
              className="w-full accent-indigo-500 cursor-pointer"
            />
            <span className="text-[11px] text-slate-500 block">
              Recommended: 60 - 90 mins for college courses
            </span>
          </div>

          {/* Weekend Toggle */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 block">
              Weekend Study Blocks
            </label>
            <label className="inline-flex items-center gap-2 cursor-pointer mt-1">
              <input
                type="checkbox"
                checked={includeWeekends}
                onChange={(e) => setIncludeWeekends(e.target.checked)}
                className="w-4 h-4 rounded-md accent-indigo-500 cursor-pointer"
              />
              <span className="text-xs text-slate-300">
                {includeWeekends ? 'Include Saturdays & Sundays' : 'Weekdays only (Mon–Fri)'}
              </span>
            </label>
          </div>

          {/* YouTube Channel Selection Strategy */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 block">
              YouTube Channel Strategy
            </label>
            <select
              value={channelLimit}
              onChange={(e) => setChannelLimit(e.target.value as any)}
              className="w-full text-xs bg-slate-950 border border-slate-800 text-slate-300 p-2 rounded-xl focus:outline-hidden focus:border-indigo-500 cursor-pointer"
            >
              <option value="conservative">1 Primary Channel first (Max consistency)</option>
              <option value="balanced">Up to 2 Complementary Channels</option>
              <option value="broad">Ask student before introducing 3rd channel</option>
            </select>
          </div>
        </div>
      </div>

      {/* Project Roadmap & Phase Tracker */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-indigo-400" />
          <h3 className="text-base font-bold text-white m-0">SyllabusSync AI Development Roadmap</h3>
        </div>

        <div className="space-y-3">
          <div className="flex items-start gap-3 p-3 rounded-xl bg-indigo-950/30 border border-indigo-800/40">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
            <div className="space-y-0.5">
              <p className="text-xs font-bold text-emerald-300 m-0">Phase 1: Project Foundation (Completed)</p>
              <p className="text-xs text-slate-400 m-0">
                React + Vite + Tailwind frontend, FastAPI backend, SQLite models, PDF & DOCX validation and digital text extraction.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-950/40 border border-slate-800/60 opacity-80">
            <Clock className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
            <div className="space-y-0.5">
              <p className="text-xs font-bold text-slate-300 m-0">Phase 2: Topic Extraction & Structuring (Next)</p>
              <p className="text-xs text-slate-400 m-0">
                Strands Agents SDK workflow to parse extracted text into an editable structured topic list with modules and estimated hours.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-950/40 border border-slate-800/60 opacity-80">
            <Clock className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
            <div className="space-y-0.5">
              <p className="text-xs font-bold text-slate-400 m-0">Phase 3: YouTube Discovery & Video Matching</p>
              <p className="text-xs text-slate-500 m-0">
                Real YouTube Data API v3 search with channel consistency (1 channel first, max 2, confirm before 3).
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-950/40 border border-slate-800/60 opacity-80">
            <Clock className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
            <div className="space-y-0.5">
              <p className="text-xs font-bold text-slate-400 m-0">Phase 4: Adaptive Daily Planner & Exam Readiness</p>
              <p className="text-xs text-slate-500 m-0">
                Dynamic rescheduling after missed study sessions, exam deadline feasibility warnings, and topic mastery tracking.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
