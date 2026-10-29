import React from 'react';
import { 
  UploadCloud, 
  FileText, 
  ArrowRight, 
  Sparkles,
  PlaySquare,
  Check
} from 'lucide-react';
import type { 
  NavigationTab, 
  SyllabusUploadResponse, 
  SyllabusAnalysisResponse 
} from '../types';
import { MountainClimbIllustration } from '../components/Illustrations';

interface DashboardPageProps {
  onNavigate: (tab: NavigationTab) => void;
  uploadedSyllabus: SyllabusUploadResponse | null;
  analyzedSyllabus: SyllabusAnalysisResponse | null;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onNavigate,
  uploadedSyllabus,
  analyzedSyllabus,
}) => {
  // Determine current step in journey
  const currentStep = analyzedSyllabus ? 2 : uploadedSyllabus ? 1 : 0;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* 1. Welcome Banner (Matches Visual Reference Top-Left) */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#0c162f] via-[#101d3d] to-[#0a1226] border border-[#1b2b54] p-6 sm:p-8 shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-4 max-w-xl">
            <div>
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white m-0">
                Hey there, Future Techie! 🎓
              </h2>
              <p className="text-sm text-slate-300 mt-1 m-0">
                Your syllabus. Your pace. Your success.
              </p>
            </div>

            {/* Quick Upload Action Box */}
            <div className="p-4 rounded-2xl bg-[#080e1e]/80 border border-[#1d2f58] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-600/20 text-blue-400 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white m-0">
                    {analyzedSyllabus ? 'Syllabus Analyzed' : 'Upload your syllabus'}
                  </h4>
                  <p className="text-[11px] text-slate-400 m-0">
                    {analyzedSyllabus
                      ? `${analyzedSyllabus.course_name || 'Course'} (${analyzedSyllabus.total_topics_count} topics)`
                      : 'Get AI-powered topic breakdown and personalized study plan.'}
                  </p>
                </div>
              </div>

              <button
                onClick={() => onNavigate('syllabus')}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/30 transition cursor-pointer self-start sm:self-auto shrink-0"
              >
                {analyzedSyllabus ? 'View Topics' : 'Upload Now'}
              </button>
            </div>
          </div>

          {/* Right Side: Mountain Illustration */}
          <div className="hidden lg:block shrink-0">
            <MountainClimbIllustration className="w-64 h-36" />
          </div>
        </div>
      </div>

      {/* 2. Three 3-Step Process Cards (Matches Visual Reference) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Step 1: Upload */}
        <div 
          onClick={() => onNavigate('syllabus')}
          className="rounded-2xl bg-[#0b1429] border border-[#19284d] hover:border-blue-500/50 p-5 transition cursor-pointer group flex items-start gap-4"
        >
          <div className="w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            <UploadCloud className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <span className="text-[11px] font-bold text-cyan-400 uppercase tracking-wider block">1. Upload</span>
            <h4 className="text-sm font-bold text-white m-0">Add your syllabus</h4>
            <p className="text-xs text-slate-400 m-0 leading-relaxed">PDF or DOCX document</p>
          </div>
        </div>

        {/* Step 2: Analyze */}
        <div 
          onClick={() => onNavigate('syllabus')}
          className="rounded-2xl bg-[#0b1429] border border-[#19284d] hover:border-indigo-500/50 p-5 transition cursor-pointer group flex items-start gap-4"
        >
          <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            <Sparkles className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <span className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider block">2. Analyze</span>
            <h4 className="text-sm font-bold text-white m-0">AI topic breakdown</h4>
            <p className="text-xs text-slate-400 m-0 leading-relaxed">Strands Agents SDK structure</p>
          </div>
        </div>

        {/* Step 3: Learn */}
        <div 
          onClick={() => onNavigate('videos')}
          className="rounded-2xl bg-[#0b1429] border border-[#19284d] hover:border-purple-500/50 p-5 transition cursor-pointer group flex items-start gap-4"
        >
          <div className="w-10 h-10 rounded-xl bg-purple-500/15 border border-purple-500/30 text-purple-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            <PlaySquare className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <span className="text-[11px] font-bold text-purple-400 uppercase tracking-wider block">3. Learn</span>
            <h4 className="text-sm font-bold text-white m-0">Find real YouTube videos</h4>
            <p className="text-xs text-slate-400 m-0 leading-relaxed">& create your daily plan</p>
          </div>
        </div>
      </div>

      {/* 3. Your Learning Journey Stepper (Matches Visual Reference) */}
      <div className="rounded-2xl bg-[#0b1429] border border-[#19284d] p-5 sm:p-6 space-y-4">
        <h3 className="text-sm font-bold text-white tracking-tight m-0">
          Your Learning Journey
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { step: 1, label: 'Upload Syllabus', desc: uploadedSyllabus ? 'Document ready' : 'PDF or DOCX' },
            { step: 2, label: 'Analyze Topics', desc: analyzedSyllabus ? `${analyzedSyllabus.total_topics_count} topics` : 'Strands agent' },
            { step: 3, label: 'Get Resources', desc: 'YouTube API v3' },
            { step: 4, label: 'Follow Plan', desc: 'Daily study schedule' },
          ].map((item, idx) => {
            const isCompleted = idx < currentStep;
            const isCurrent = idx === currentStep;

            return (
              <div 
                key={item.step} 
                className={`p-3.5 rounded-xl border flex items-center gap-3 transition ${
                  isCompleted
                    ? 'bg-emerald-950/20 border-emerald-800/40'
                    : isCurrent
                    ? 'bg-blue-950/30 border-blue-600/50'
                    : 'bg-[#080f21] border-[#162548] opacity-60'
                }`}
              >
                <div 
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                    isCompleted
                      ? 'bg-emerald-500 text-white'
                      : isCurrent
                      ? 'bg-blue-600 text-white ring-2 ring-blue-400/40'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {isCompleted ? <Check className="w-3.5 h-3.5" /> : item.step}
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-white truncate m-0">{item.label}</p>
                  <p className="text-[11px] text-slate-400 truncate m-0">{item.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Active Course State or Empty Guidance */}
      {analyzedSyllabus ? (
        <div className="rounded-2xl bg-[#0b1429] border border-[#19284d] p-5 sm:p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-blue-400">
                Active Course Roadmap
              </span>
              <h3 className="text-lg font-bold text-white m-0">
                {analyzedSyllabus.course_name || analyzedSyllabus.filename}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onNavigate('syllabus')}
                className="px-3.5 py-1.5 rounded-xl bg-[#162548] hover:bg-[#1e3466] text-slate-200 text-xs font-medium border border-[#233a72] transition cursor-pointer"
              >
                Edit Topics
              </button>
              <button
                onClick={() => onNavigate('study-plan')}
                className="px-4 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium shadow-md shadow-blue-600/30 transition cursor-pointer flex items-center gap-1.5"
              >
                <span>Study Plan</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl bg-[#070e20] border border-[#162548]">
              <span className="text-[11px] text-slate-400">Total Units</span>
              <p className="text-lg font-bold text-white m-0 mt-0.5">{analyzedSyllabus.modules.length}</p>
            </div>
            <div className="p-3 rounded-xl bg-[#070e20] border border-[#162548]">
              <span className="text-[11px] text-slate-400">Topics Extracted</span>
              <p className="text-lg font-bold text-white m-0 mt-0.5">{analyzedSyllabus.total_topics_count}</p>
            </div>
            <div className="p-3 rounded-xl bg-[#070e20] border border-[#162548]">
              <span className="text-[11px] text-slate-400">Study Duration</span>
              <p className="text-lg font-bold text-blue-400 m-0 mt-0.5">{(analyzedSyllabus.total_estimated_minutes / 60).toFixed(1)} hrs</p>
            </div>
            <div className="p-3 rounded-xl bg-[#070e20] border border-[#162548]">
              <span className="text-[11px] text-slate-400">Engine</span>
              <p className="text-xs font-mono text-slate-300 m-0 mt-1 truncate">{analyzedSyllabus.is_fallback ? 'Dev Fallback' : 'Strands SDK'}</p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
