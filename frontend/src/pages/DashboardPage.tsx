import React from 'react';
import { 
  UploadCloud, 
  FileText, 
  CalendarDays, 
  BarChart3, 
  CheckCircle2, 
  ArrowRight, 
  Sparkles
} from 'lucide-react';
import type { NavigationTab, SyllabusUploadResponse } from '../types';

interface DashboardPageProps {
  onNavigate: (tab: NavigationTab) => void;
  uploadedSyllabus: SyllabusUploadResponse | null;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onNavigate,
  uploadedSyllabus,
}) => {
  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-950/70 via-slate-900 to-slate-950 border border-indigo-900/40 p-6 sm:p-8 shadow-xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>AI-Powered Course Roadmap</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white m-0">
            Turn your syllabus into an actionable video study plan.
          </h2>
          <p className="text-sm sm:text-base text-slate-300 leading-relaxed m-0">
            SyllabusSync AI bridges the gap between static university syllabi and real, high-quality
            educational YouTube video lectures with an adaptive daily study schedule.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigate('syllabus')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/30 cursor-pointer"
            >
              <UploadCloud className="w-4 h-4" />
              <span>{uploadedSyllabus ? 'View or Replace Syllabus' : 'Upload Syllabus'}</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </button>
            <button
              onClick={() => onNavigate('study-plan')}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-300 border border-slate-700 font-medium text-sm transition-all cursor-pointer"
            >
              <CalendarDays className="w-4 h-4 text-slate-400" />
              <span>Study Plan Preview</span>
            </button>
          </div>
        </div>
      </div>

      {/* Overview Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: Syllabus Status */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800/90 p-5 backdrop-blur-xs flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                1. Syllabus Document
              </span>
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                <FileText className="w-4 h-4" />
              </div>
            </div>

            {uploadedSyllabus ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    {uploadedSyllabus.file_type}
                  </span>
                  <span className="text-sm font-semibold text-white truncate" title={uploadedSyllabus.filename}>
                    {uploadedSyllabus.filename}
                  </span>
                </div>
                <p className="text-xs text-slate-400 m-0">
                  {uploadedSyllabus.word_count.toLocaleString()} words extracted across {uploadedSyllabus.unit_count} {uploadedSyllabus.unit_label}.
                </p>
                <div className="inline-flex items-center gap-1.5 text-xs text-emerald-400 pt-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Parsed & Validated</span>
                </div>
              </div>
            ) : (
              <div className="space-y-1.5 py-1">
                <p className="text-sm font-medium text-slate-300 m-0">No syllabus uploaded</p>
                <p className="text-xs text-slate-500 m-0">
                  Upload a PDF or DOCX file to extract course topics and study modules.
                </p>
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-slate-800/80 mt-4">
            <button
              onClick={() => onNavigate('syllabus')}
              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer"
            >
              <span>{uploadedSyllabus ? 'Inspect Extracted Text' : 'Go to Upload Page'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Card 2: Study Plan Status (Empty State) */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800/90 p-5 backdrop-blur-xs flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                2. Adaptive Study Plan
              </span>
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
                <CalendarDays className="w-4 h-4" />
              </div>
            </div>

            <div className="space-y-1.5 py-1">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-400/80" />
                <p className="text-sm font-medium text-slate-300 m-0">Roadmap Not Generated</p>
              </div>
              <p className="text-xs text-slate-500 m-0">
                {uploadedSyllabus 
                  ? 'Ready for Phase 2: Topics will be structured into daily scheduled blocks.' 
                  : 'A daily study roadmap will be generated once your syllabus is parsed and analyzed.'}
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800/80 mt-4">
            <button
              onClick={() => onNavigate('study-plan')}
              className="text-xs font-semibold text-slate-400 hover:text-slate-300 flex items-center gap-1 cursor-pointer"
            >
              <span>View Study Plan Structure</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Card 3: Progress & Mastery Status (Empty State) */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800/90 p-5 backdrop-blur-xs flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                3. Course Progress
              </span>
              <div className="p-2 rounded-lg bg-violet-500/10 text-violet-400">
                <BarChart3 className="w-4 h-4" />
              </div>
            </div>

            <div className="space-y-1.5 py-1">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-slate-500" />
                <p className="text-sm font-medium text-slate-300 m-0">0% Course Covered</p>
              </div>
              <p className="text-xs text-slate-500 m-0">
                No active progress data. Topic mastery and video completions will track dynamically as you study.
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800/80 mt-4">
            <button
              onClick={() => onNavigate('progress')}
              className="text-xs font-semibold text-slate-400 hover:text-slate-300 flex items-center gap-1 cursor-pointer"
            >
              <span>View Progress Dashboard</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* How SyllabusSync AI Works Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight m-0">
            How SyllabusSync AI Works
          </h3>
          <span className="text-xs text-slate-400">3-Step AI Workflow</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="rounded-2xl bg-slate-900/40 border border-slate-800 p-5 space-y-3">
            <div className="w-8 h-8 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center font-bold text-sm">
              1
            </div>
            <h4 className="text-sm font-semibold text-white m-0">Digital Document Extraction</h4>
            <p className="text-xs text-slate-400 leading-relaxed m-0">
              Upload PDF or DOCX syllabus files. SyllabusSync AI safely inspects document structure,
              extracts readable text, and prepares clean course segments.
            </p>
            <span className="inline-block text-[11px] font-medium text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
              Active in Phase 1
            </span>
          </div>

          <div className="rounded-2xl bg-slate-900/40 border border-slate-800 p-5 space-y-3">
            <div className="w-8 h-8 rounded-xl bg-violet-600/20 text-violet-400 flex items-center justify-center font-bold text-sm">
              2
            </div>
            <h4 className="text-sm font-semibold text-white m-0">Real Educational Video Matching</h4>
            <p className="text-xs text-slate-400 leading-relaxed m-0">
              Autonomous Strands Agents search the YouTube Data API v3 for high-yield lectures from top
              educational channels with channel consistency.
            </p>
            <span className="inline-block text-[11px] font-medium text-indigo-400 bg-indigo-950/40 px-2 py-0.5 rounded border border-indigo-800/40">
              Coming in Phase 2 & 3
            </span>
          </div>

          <div className="rounded-2xl bg-slate-900/40 border border-slate-800 p-5 space-y-3">
            <div className="w-8 h-8 rounded-xl bg-purple-600/20 text-purple-400 flex items-center justify-center font-bold text-sm">
              3
            </div>
            <h4 className="text-sm font-semibold text-white m-0">Adaptive Daily Scheduling</h4>
            <p className="text-xs text-slate-400 leading-relaxed m-0">
              Missed a day? The planner automatically adjusts your daily study load, flags upcoming
              exam deadlines, and tracks concept mastery without stress.
            </p>
            <span className="inline-block text-[11px] font-medium text-indigo-400 bg-indigo-950/40 px-2 py-0.5 rounded border border-indigo-800/40">
              Coming in Phase 4
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
