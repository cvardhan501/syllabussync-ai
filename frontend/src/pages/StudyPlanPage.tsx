import React, { useState } from 'react';
import { 
  CalendarDays, 
  Clock, 
  Sparkles, 
  Video, 
  CheckCircle2, 
  ArrowRight,
  BookOpen
} from 'lucide-react';
import type { NavigationTab, SyllabusUploadResponse } from '../types';

interface StudyPlanPageProps {
  uploadedSyllabus: SyllabusUploadResponse | null;
  onNavigate: (tab: NavigationTab) => void;
}

export const StudyPlanPage: React.FC<StudyPlanPageProps> = ({
  uploadedSyllabus,
  onNavigate,
}) => {
  const [activeFilter, setActiveFilter] = useState<'all' | 'today' | 'upcoming' | 'completed'>('all');

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header with Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight m-0">
            Adaptive Study Roadmap
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 m-0">
            Daily study sessions scheduled around real educational video lectures and review checkpoints.
          </p>
        </div>

        {/* Filter Tabs (Structure Ready) */}
        <div className="flex items-center gap-1 p-1 bg-slate-900 border border-slate-800 rounded-xl self-start sm:self-auto">
          {(['all', 'today', 'upcoming', 'completed'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer capitalize ${
                activeFilter === filter
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {/* Main Empty State Container */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-8 sm:p-12 text-center flex flex-col items-center justify-center">
        <div className="w-16 h-16 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4">
          <CalendarDays className="w-8 h-8" />
        </div>

        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/80 text-slate-300 text-xs font-semibold mb-3">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>Status: Awaiting Plan Generation</span>
        </div>

        <h3 className="text-lg sm:text-xl font-bold text-white mb-2">
          {uploadedSyllabus ? 'Syllabus Ready for Study Plan Structuring' : 'No Active Study Plan Available'}
        </h3>

        <p className="text-xs sm:text-sm text-slate-400 max-w-lg mb-6 leading-relaxed">
          {uploadedSyllabus
            ? `Extracted text from '${uploadedSyllabus.filename}' is loaded. The adaptive study roadmap engine will be wired in Phase 2 & 3 to schedule real YouTube lectures and daily study targets.`
            : 'To create your personalized study schedule, upload your course syllabus first. SyllabusSync AI will map each topic to verified educational videos.'}
        </p>

        {!uploadedSyllabus ? (
          <button
            onClick={() => onNavigate('syllabus')}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs sm:text-sm font-medium transition shadow-lg shadow-indigo-600/25 cursor-pointer"
          >
            <BookOpen className="w-4 h-4" />
            <span>Upload Syllabus Document</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        ) : (
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-950/60 border border-indigo-800/60 text-indigo-300 text-xs font-medium">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span>Topic extraction agent interface active in Phase 2</span>
          </div>
        )}
      </div>

      {/* Planned Feature Blueprint */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Planned Study Plan Architecture (Phases 2 – 4)
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-xl bg-slate-900/40 border border-slate-800/80 p-4 space-y-2">
            <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold">
              <Video className="w-4 h-4" />
              <span>Channel Matching Policy</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed m-0">
              Matches topics with 1 primary channel first, adding up to 2 complementary channels, and asking the student before introducing a 3rd.
            </p>
          </div>

          <div className="rounded-xl bg-slate-900/40 border border-slate-800/80 p-4 space-y-2">
            <div className="flex items-center gap-2 text-violet-400 text-xs font-semibold">
              <Clock className="w-4 h-4" />
              <span>Adaptive Rescheduling</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed m-0">
              Dynamically spreads out remaining study topics when study days are missed, recalculating daily required study minutes.
            </p>
          </div>

          <div className="rounded-xl bg-slate-900/40 border border-slate-800/80 p-4 space-y-2">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              <span>Exam Feasibility Flags</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed m-0">
              Evaluates whether the remaining syllabus is realistic before exam day based on student daily pace and video duration.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
