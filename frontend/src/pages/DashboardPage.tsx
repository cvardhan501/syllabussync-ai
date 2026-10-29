import React from 'react';
import { 
  UploadCloud, 
  FileText, 
  ArrowRight, 
  Sparkles,
  PlaySquare,
  Check,
  AlertTriangle,
  Clock,
  CalendarDays
} from 'lucide-react';
import type { 
  NavigationTab, 
  SyllabusUploadResponse, 
  SyllabusAnalysisResponse,
  StudyPlanResponse,
  ResourceDiscoveryResponse 
} from '../types';
import { MountainClimbIllustration } from '../components/Illustrations';

interface DashboardPageProps {
  onNavigate: (tab: NavigationTab) => void;
  uploadedSyllabus: SyllabusUploadResponse | null;
  analyzedSyllabus: SyllabusAnalysisResponse | null;
  studyPlan?: StudyPlanResponse | null;
  discoveryData?: ResourceDiscoveryResponse | null;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onNavigate,
  uploadedSyllabus,
  analyzedSyllabus,
  studyPlan,
  discoveryData,
}) => {
  // Determine current step in journey (0 to 4)
  const currentStep = studyPlan && studyPlan.completed_tasks_count > 0 
    ? 3 
    : discoveryData && discoveryData.coverage.topics_with_relevant > 0
    ? 2
    : analyzedSyllabus
    ? 1
    : 0;

  // Today's tasks
  const todayIso = new Date().toISOString().split('T')[0];
  const todayGroup = studyPlan?.daily_schedules.find((g) => g.date === todayIso);
  const todayTasks = todayGroup?.tasks || [];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* Feasibility Alert Banner if Impossible Deadline */}
      {studyPlan?.feasibility_status === 'impossible' && (
        <div className="rounded-2xl bg-rose-950/30 border border-rose-600/50 p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            <div>
              <h4 className="text-xs font-bold text-rose-200 m-0">Deadline Shortfall Alert</h4>
              <p className="text-[11px] text-rose-300 m-0 mt-0.5">
                {studyPlan.feasibility_warning}
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('settings')}
            className="px-3.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shrink-0 cursor-pointer shadow transition"
          >
            Adjust Availability
          </button>
        </div>
      )}

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
                      ? `${analyzedSyllabus.course_name || 'Course'} (${analyzedSyllabus.total_topics_count} topics verified)`
                      : 'Get AI-powered topic breakdown and personalized study plan.'}
                  </p>
                </div>
              </div>

              <button
                onClick={() => onNavigate('syllabus')}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition cursor-pointer shadow-md shadow-blue-600/30 shrink-0"
              >
                {analyzedSyllabus ? 'Review Topics' : 'Upload now'}
              </button>
            </div>
          </div>

          {/* Right Mountain Illustration (Handcrafted Vector matching Screen 1) */}
          <div className="hidden sm:flex flex-col items-center justify-center relative">
            <MountainClimbIllustration className="w-64 h-44 drop-shadow-2xl" />
          </div>
        </div>
      </div>

      {/* 2. Process Cards (Upload, Analyze, Learn - Matches Reference Screen 1) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Upload */}
        <div 
          onClick={() => onNavigate('syllabus')}
          className="p-5 rounded-2xl bg-[#0c162e] border border-[#1b2b52] hover:border-blue-500/50 transition cursor-pointer group shadow-md flex items-start gap-3.5"
        >
          <div className="w-10 h-10 rounded-xl bg-blue-600/15 border border-blue-500/30 text-blue-400 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
            <UploadCloud className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-bold text-white block">1. Upload</span>
            <p className="text-[11px] text-slate-400 m-0 mt-0.5 leading-relaxed">
              Add your syllabus (PDF / DOCX)
            </p>
          </div>
        </div>

        {/* Card 2: Analyze */}
        <div 
          onClick={() => onNavigate('syllabus')}
          className="p-5 rounded-2xl bg-[#0c162e] border border-[#1b2b52] hover:border-indigo-500/50 transition cursor-pointer group shadow-md flex items-start gap-3.5"
        >
          <div className="w-10 h-10 rounded-xl bg-indigo-600/15 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-bold text-white block">2. Analyze</span>
            <p className="text-[11px] text-slate-400 m-0 mt-0.5 leading-relaxed">
              Get AI topic breakdown with structure
            </p>
          </div>
        </div>

        {/* Card 3: Learn */}
        <div 
          onClick={() => onNavigate('videos')}
          className="p-5 rounded-2xl bg-[#0c162e] border border-[#1b2b52] hover:border-violet-500/50 transition cursor-pointer group shadow-md flex items-start gap-3.5"
        >
          <div className="w-10 h-10 rounded-xl bg-rose-600/15 border border-rose-500/30 text-rose-400 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
            <PlaySquare className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-bold text-white block">3. Learn</span>
            <p className="text-[11px] text-slate-400 m-0 mt-0.5 leading-relaxed">
              Find real YouTube videos & create your plan
            </p>
          </div>
        </div>
      </div>

      {/* 3. Learning Journey Stepper (Matches Reference Screen 1) */}
      <div className="p-5 rounded-2xl bg-[#0c162e] border border-[#1b2b52] space-y-4 shadow-md">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white m-0">Your Learning Journey</h3>
          {studyPlan && (
            <span className="text-[11px] text-blue-400 font-mono">
              Exam: {studyPlan.exam_date}
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-1">
          {/* Step 1 */}
          <div className={`p-3 rounded-xl border flex items-center gap-2.5 transition ${
            currentStep >= 0 ? 'bg-blue-600/15 border-blue-500/50 text-blue-200' : 'bg-[#080e1e] border-[#18284e] text-slate-500'
          }`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              uploadedSyllabus ? 'bg-emerald-500 text-white' : 'bg-blue-600 text-white'
            }`}>
              {uploadedSyllabus ? <Check className="w-3.5 h-3.5" /> : '1'}
            </div>
            <span className="text-xs font-semibold">Upload Syllabus</span>
          </div>

          {/* Step 2 */}
          <div className={`p-3 rounded-xl border flex items-center gap-2.5 transition ${
            currentStep >= 1 ? 'bg-blue-600/15 border-blue-500/50 text-blue-200' : 'bg-[#080e1e] border-[#18284e] text-slate-500'
          }`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              analyzedSyllabus ? 'bg-emerald-500 text-white' : 'bg-blue-600 text-white'
            }`}>
              {analyzedSyllabus ? <Check className="w-3.5 h-3.5" /> : '2'}
            </div>
            <span className="text-xs font-semibold">Analyze Topics</span>
          </div>

          {/* Step 3 */}
          <div className={`p-3 rounded-xl border flex items-center gap-2.5 transition ${
            currentStep >= 2 ? 'bg-blue-600/15 border-blue-500/50 text-blue-200' : 'bg-[#080e1e] border-[#18284e] text-slate-500'
          }`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              discoveryData && discoveryData.coverage.topics_with_relevant > 0 ? 'bg-emerald-500 text-white' : 'bg-blue-600 text-white'
            }`}>
              {discoveryData && discoveryData.coverage.topics_with_relevant > 0 ? <Check className="w-3.5 h-3.5" /> : '3'}
            </div>
            <span className="text-xs font-semibold">Get Resources</span>
          </div>

          {/* Step 4 */}
          <div className={`p-3 rounded-xl border flex items-center gap-2.5 transition ${
            currentStep >= 3 ? 'bg-blue-600/15 border-blue-500/50 text-blue-200' : 'bg-[#080e1e] border-[#18284e] text-slate-500'
          }`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              studyPlan && studyPlan.progress_percentage >= 100 ? 'bg-emerald-500 text-white' : 'bg-blue-600 text-white'
            }`}>
              {studyPlan && studyPlan.progress_percentage >= 100 ? <Check className="w-3.5 h-3.5" /> : '4'}
            </div>
            <span className="text-xs font-semibold">Follow Plan</span>
          </div>
        </div>
      </div>

      {/* 4. Live Today's Tasks & Status Row */}
      {studyPlan && (
        <div className="p-5 rounded-2xl bg-[#0c162e] border border-[#1b2b52] space-y-3 shadow-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CalendarDays className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-bold text-white m-0">Today's Study Session</h3>
            </div>
            <button
              onClick={() => onNavigate('study-plan')}
              className="text-xs text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1 cursor-pointer"
            >
              <span>View Full Timetable</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {todayTasks.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {todayTasks.map((t) => (
                <div
                  key={t.id}
                  className={`p-3 rounded-xl border text-xs flex items-center justify-between ${
                    t.status === 'completed'
                      ? 'bg-[#070e20] border-[#152342] text-slate-500 line-through'
                      : 'bg-[#081022] border-[#18284e] text-slate-200'
                  }`}
                >
                  <div className="space-y-0.5">
                    <p className="font-semibold m-0 truncate max-w-[180px]">{t.title}</p>
                    <span className="text-[10px] text-slate-400 flex items-center gap-1">
                      <Clock className="w-2.5 h-2.5" />
                      {t.duration_minutes} min • {t.task_type}
                    </span>
                  </div>
                  {t.status === 'completed' && <Check className="w-4 h-4 text-emerald-400" />}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 m-0">
              No tasks scheduled for today. Rest day or proceed to upcoming modules!
            </p>
          )}
        </div>
      )}
    </div>
  );
};
