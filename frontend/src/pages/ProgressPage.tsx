import React from 'react';
import { 
  BarChart3, 
  Target, 
  Flame, 
  Clock, 
  Award, 
  AlertCircle, 
  ArrowRight,
  BookOpen
} from 'lucide-react';
import type { NavigationTab, SyllabusUploadResponse } from '../types';

interface ProgressPageProps {
  uploadedSyllabus: SyllabusUploadResponse | null;
  onNavigate: (tab: NavigationTab) => void;
}

export const ProgressPage: React.FC<ProgressPageProps> = ({
  uploadedSyllabus,
  onNavigate,
}) => {
  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight m-0">
          Course Progress & Readiness
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1 m-0">
          Track syllabus topic mastery, study pace, exam deadline feasibility, and video completion.
        </p>
      </div>

      {/* Real Zero-State Metric Cards (Strictly no fake data) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Topic Mastery</span>
            <Target className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-2xl font-bold text-slate-300 m-0">0%</p>
          <span className="text-[11px] text-slate-500">0 of 0 topics completed</span>
        </div>

        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Video Hours Watched</span>
            <Clock className="w-4 h-4 text-violet-400" />
          </div>
          <p className="text-2xl font-bold text-slate-300 m-0">0.0 hrs</p>
          <span className="text-[11px] text-slate-500">Awaiting study sessions</span>
        </div>

        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Current Streak</span>
            <Flame className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-slate-300 m-0">0 days</p>
          <span className="text-[11px] text-slate-500">Start studying to ignite streak</span>
        </div>

        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Exam Readiness</span>
            <Award className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-lg font-bold text-slate-400 m-0">Pending</p>
          <span className="text-[11px] text-slate-500">Requires active study roadmap</span>
        </div>
      </div>

      {/* Main Empty State Banner */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-8 sm:p-12 text-center flex flex-col items-center justify-center">
        <div className="w-16 h-16 rounded-2xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center text-violet-400 mb-4">
          <BarChart3 className="w-8 h-8" />
        </div>

        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/80 text-slate-300 text-xs font-semibold mb-3">
          <AlertCircle className="w-3.5 h-3.5 text-slate-400" />
          <span>No Progress Recorded Yet</span>
        </div>

        <h3 className="text-lg sm:text-xl font-bold text-white mb-2">
          Analytics Will Activate With Your Study Roadmap
        </h3>

        <p className="text-xs sm:text-sm text-slate-400 max-w-lg mb-6 leading-relaxed">
          {uploadedSyllabus
            ? `Your syllabus '${uploadedSyllabus.filename}' is parsed. In later phases, completing assigned video lectures and practice checkpoints will populate real-time mastery scores.`
            : 'Upload your syllabus first to establish the learning roadmap. Your real study activity and exam readiness will appear here.'}
        </p>

        {!uploadedSyllabus && (
          <button
            onClick={() => onNavigate('syllabus')}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs sm:text-sm font-medium transition shadow-lg shadow-indigo-600/25 cursor-pointer"
          >
            <BookOpen className="w-4 h-4" />
            <span>Upload Syllabus</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
