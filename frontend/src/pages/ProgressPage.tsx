import React, { useState } from 'react';
import { 
  Compass,
  CheckCircle2,
  Calendar,
  AlertTriangle,
  ChevronDown,
  Layers,
  Award,
  Sparkles,
  ArrowRight,
  TrendingUp,
  FileText
} from 'lucide-react';
import type { 
  NavigationTab, 
  SyllabusUploadResponse, 
  SyllabusAnalysisResponse 
} from '../types';

interface ProgressPageProps {
  uploadedSyllabus: SyllabusUploadResponse | null;
  analyzedSyllabus?: SyllabusAnalysisResponse | null;
  onNavigate: (tab: NavigationTab) => void;
}

export const ProgressPage: React.FC<ProgressPageProps> = ({
  uploadedSyllabus,
  analyzedSyllabus,
  onNavigate,
}) => {
  const [timeRange, setTimeRange] = useState<'7days' | '30days' | 'all'>('7days');
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  // Derive real module data from analyzed syllabus if present, or provide standard curriculum placeholders
  const modulesList = analyzedSyllabus && analyzedSyllabus.modules.length > 0
    ? analyzedSyllabus.modules.map((m, idx) => ({
        id: m.id || `mod-${idx + 1}`,
        title: `Module ${idx + 1}: ${m.title}`,
        progress: 0,
        topicCount: m.topics.length,
      }))
    : [
        { id: '1', title: 'Module 1: Introduction to Programming', progress: 0, topicCount: 8 },
        { id: '2', title: 'Module 2: Data Structures and Algorithms', progress: 0, topicCount: 10 },
        { id: '3', title: 'Module 3: Database Management Systems', progress: 0, topicCount: 8 },
        { id: '4', title: 'Module 4: Computer Networks', progress: 0, topicCount: 7 },
        { id: '5', title: 'Module 5: Web Technologies', progress: 0, topicCount: 6 },
      ];

  const hasRealSyllabus = Boolean(analyzedSyllabus || uploadedSyllabus);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Page Header with Time Filter Dropdown */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight m-0">
            Your Progress Overview
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 m-0">
            Track your learning, spot gaps, and stay on top of your goals.
          </p>
        </div>

        {/* Time Filter Pill */}
        <div className="relative self-start sm:self-auto">
          <button
            onClick={() => setIsFilterOpen(!isFilterOpen)}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-[#0b1429] border border-[#1b2b52] text-xs font-medium text-slate-300 hover:text-white hover:border-blue-500/50 transition cursor-pointer"
          >
            <Calendar className="w-3.5 h-3.5 text-blue-400" />
            <span>
              {timeRange === '7days' && 'Last 7 Days'}
              {timeRange === '30days' && 'Last 30 Days'}
              {timeRange === 'all' && 'All Time'}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-1" />
          </button>

          {isFilterOpen && (
            <div className="absolute right-0 mt-1.5 w-36 rounded-xl bg-[#091122] border border-[#1b2b52] shadow-xl py-1 z-20">
              <button
                onClick={() => { setTimeRange('7days'); setIsFilterOpen(false); }}
                className={`w-full text-left px-3 py-1.5 text-xs transition ${timeRange === '7days' ? 'text-blue-400 bg-blue-600/10 font-medium' : 'text-slate-300 hover:bg-[#111e3b]'}`}
              >
                Last 7 Days
              </button>
              <button
                onClick={() => { setTimeRange('30days'); setIsFilterOpen(false); }}
                className={`w-full text-left px-3 py-1.5 text-xs transition ${timeRange === '30days' ? 'text-blue-400 bg-blue-600/10 font-medium' : 'text-slate-300 hover:bg-[#111e3b]'}`}
              >
                Last 30 Days
              </button>
              <button
                onClick={() => { setTimeRange('all'); setIsFilterOpen(false); }}
                className={`w-full text-left px-3 py-1.5 text-xs transition ${timeRange === 'all' ? 'text-blue-400 bg-blue-600/10 font-medium' : 'text-slate-300 hover:bg-[#111e3b]'}`}
              >
                All Time
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 5 Metric Cards in a Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        {/* Metric 1: Syllabus Coverage */}
        <div className="rounded-xl bg-[#0b1429]/90 border border-[#18284e] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-slate-300">Syllabus Coverage</span>
            <div className="w-7 h-7 rounded-lg bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Layers className="w-3.5 h-3.5" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white tracking-tight">0%</div>
            <p className="text-[10px] text-slate-400 mt-1 m-0">Topics with resources</p>
          </div>
        </div>

        {/* Metric 2: Study Progress */}
        <div className="rounded-xl bg-[#0b1429]/90 border border-[#18284e] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-slate-300">Study Progress</span>
            <div className="w-7 h-7 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white tracking-tight">0%</div>
            <p className="text-[10px] text-slate-400 mt-1 m-0">Tasks completed</p>
          </div>
        </div>

        {/* Metric 3: Learning Confidence */}
        <div className="rounded-xl bg-[#0b1429]/90 border border-[#18284e] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-slate-300">Learning Confidence</span>
            <div className="w-7 h-7 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white tracking-tight">0%</div>
            <p className="text-[10px] text-slate-400 mt-1 m-0">Practice & assessment</p>
          </div>
        </div>

        {/* Metric 4: Exam Readiness */}
        <div className="rounded-xl bg-[#0b1429]/90 border border-[#18284e] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-slate-300">Exam Readiness</span>
            <div className="w-7 h-7 rounded-lg bg-violet-500/15 border border-violet-500/30 flex items-center justify-center text-violet-400">
              <Award className="w-3.5 h-3.5" />
            </div>
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-300 tracking-tight leading-tight pt-1">
              Not enough data
            </div>
            <p className="text-[10px] text-slate-400 mt-1.5 m-0">Based on your progress</p>
          </div>
        </div>

        {/* Metric 5: Resource Gaps */}
        <div className="col-span-2 sm:col-span-1 rounded-xl bg-[#0b1429]/90 border border-[#18284e] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-slate-300">Resource Gaps</span>
            <div className="w-7 h-7 rounded-lg bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <AlertTriangle className="w-3.5 h-3.5" />
            </div>
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-300 tracking-tight leading-tight pt-1">
              Not enough data
            </div>
            <p className="text-[10px] text-slate-400 mt-1.5 m-0">Topics without resources</p>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Module-wise Progress (7 cols) */}
        <div className="lg:col-span-7 rounded-2xl bg-[#0b1429]/80 border border-[#18284e] p-5 sm:p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm sm:text-base font-bold text-white m-0">
                Module-wise Progress
              </h3>
            </div>
            {analyzedSyllabus && (
              <span className="text-[11px] text-blue-400 font-medium px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20">
                {analyzedSyllabus.modules.length} Modules Active
              </span>
            )}
          </div>

          {!hasRealSyllabus && (
            <div className="text-[11px] text-slate-400 bg-[#091122] border border-[#18284e] rounded-xl p-3 flex items-start gap-2.5">
              <span className="text-blue-400 font-bold mt-0.5">ℹ</span>
              <span>
                Displaying standard curriculum blueprint below. Upload and analyze your college syllabus to replace this with your genuine course modules.
              </span>
            </div>
          )}

          {/* Module Bars List */}
          <div className="space-y-4 pt-1">
            {modulesList.map((mod) => (
              <div key={mod.id} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-200 truncate pr-3">
                    {mod.title}
                  </span>
                  <span className="font-mono text-slate-400 font-medium shrink-0">
                    {mod.progress}%
                  </span>
                </div>
                {/* Progress Track */}
                <div className="w-full h-2 rounded-full bg-[#132247] overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-600 to-indigo-500 rounded-full transition-all duration-500"
                    style={{ width: `${mod.progress}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Next Action + Upcoming Tasks (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Card 1: Next Recommended Action */}
          <div className="rounded-2xl bg-[#0b1429]/80 border border-[#18284e] p-5 space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0">
                <Compass className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400 block mb-0.5">
                  Next Recommended Action
                </span>
                <p className="text-xs text-slate-300 font-medium leading-relaxed m-0">
                  {hasRealSyllabus
                    ? 'Review your analyzed topics to prepare video matching and activate your daily study schedule.'
                    : 'Upload your syllabus to get AI-powered insights and a personalized study plan.'}
                </p>
              </div>
            </div>

            <button
              onClick={() => onNavigate('syllabus')}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/20 transition cursor-pointer"
            >
              <span>Go to My Syllabus</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Card 2: Upcoming Tasks */}
          <div className="rounded-2xl bg-[#0b1429]/80 border border-[#18284e] p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs sm:text-sm font-bold text-white m-0">
                Upcoming Tasks
              </h3>
              <button 
                onClick={() => onNavigate('study-plan')}
                className="text-[11px] text-blue-400 hover:text-blue-300 font-medium transition cursor-pointer"
              >
                View Plan
              </button>
            </div>

            {/* Honest Empty State for Tasks */}
            <div className="rounded-xl bg-[#091122] border border-[#18284e] p-6 text-center space-y-2">
              <div className="w-10 h-10 rounded-full bg-slate-800/80 border border-slate-700/60 flex items-center justify-center mx-auto text-slate-400">
                <FileText className="w-5 h-5" />
              </div>
              <p className="text-xs font-bold text-slate-300 m-0">
                No tasks yet
              </p>
              <p className="text-[11px] text-slate-400 max-w-xs mx-auto m-0 leading-relaxed">
                Complete your syllabus analysis to view your upcoming tasks.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
