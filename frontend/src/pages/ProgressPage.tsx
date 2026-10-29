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
  SyllabusAnalysisResponse,
  StudyPlanResponse,
  ResourceDiscoveryResponse 
} from '../types';

interface ProgressPageProps {
  uploadedSyllabus: SyllabusUploadResponse | null;
  analyzedSyllabus?: SyllabusAnalysisResponse | null;
  studyPlan?: StudyPlanResponse | null;
  discoveryData?: ResourceDiscoveryResponse | null;
  onNavigate: (tab: NavigationTab) => void;
}

export const ProgressPage: React.FC<ProgressPageProps> = ({
  uploadedSyllabus,
  analyzedSyllabus,
  studyPlan,
  discoveryData,
  onNavigate,
}) => {
  const [timeRange, setTimeRange] = useState<'7days' | '30days' | 'all'>('7days');
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  const hasRealSyllabus = Boolean(analyzedSyllabus || uploadedSyllabus);

  // Real Metric 1: Coverage
  const totalTopics = analyzedSyllabus?.total_topics_count || discoveryData?.coverage.total_topics || 0;
  const coveragePercent = discoveryData?.coverage.coverage_percentage ?? 0;
  const topicsWithVideos = discoveryData?.coverage.topics_with_relevant ?? 0;

  // Real Metric 2: Study Progress
  const totalTasks = studyPlan?.total_tasks_count || 0;
  const completedTasks = studyPlan?.completed_tasks_count || 0;
  const studyProgressPercent = studyPlan?.progress_percentage ?? 0;

  // Real Metric 3: Learning Confidence (Practice Checkpoints)
  // Check how many practice tasks were completed
  const allTasks = (studyPlan?.daily_schedules || []).flatMap((g) => g.tasks);
  const practiceTasks = allTasks.filter((t) => t.task_type === 'Practice');
  const completedPractice = practiceTasks.filter((t) => t.status === 'completed');
  const confidenceScore = practiceTasks.length > 0 
    ? Math.round((completedPractice.length / practiceTasks.length) * 100) 
    : 0;

  // Real Metric 4: Exam Readiness
  let readinessLabel = 'Not enough data';
  let readinessSubtext = 'Requires active study roadmap';
  if (studyPlan) {
    if (studyPlan.feasibility_status === 'impossible') {
      readinessLabel = 'Shortfall';
      readinessSubtext = `-${studyPlan.shortfall_hours}h before exam`;
    } else if (studyPlan.feasibility_status === 'tight') {
      readinessLabel = 'Tight Pace';
      readinessSubtext = `Target: ${studyPlan.exam_date}`;
    } else if (studyPlan.progress_percentage >= 80) {
      readinessLabel = 'High Readiness';
      readinessSubtext = '80%+ workload mastered';
    } else if (studyPlan.completed_tasks_count > 0) {
      readinessLabel = 'On Track';
      readinessSubtext = `${studyPlan.completed_tasks_count} tasks done`;
    } else {
      readinessLabel = 'Roadmap Ready';
      readinessSubtext = `0 of ${studyPlan.total_tasks_count} tasks started`;
    }
  }

  // Real Metric 5: Resource Gaps
  const resourceGaps = discoveryData ? discoveryData.coverage.topics_with_no_resource : 0;

  // Real Module-wise Progress Calculation
  const modulesList = analyzedSyllabus && analyzedSyllabus.modules.length > 0
    ? analyzedSyllabus.modules.map((m, idx) => {
        const modId = m.id;
        const modTasks = allTasks.filter((t) => t.module_id === modId || t.module_id?.endsWith(modId));
        const modCompleted = modTasks.filter((t) => t.status === 'completed').length;
        const modProgress = modTasks.length > 0 ? Math.round((modCompleted / modTasks.length) * 100) : 0;

        return {
          id: m.id || `mod-${idx + 1}`,
          title: `Module ${idx + 1}: ${m.title}`,
          progress: modProgress,
          completedTasks: modCompleted,
          totalTasks: modTasks.length || m.topics.length,
        };
      })
    : [
        { id: '1', title: 'Module 1: Introduction to Programming', progress: 0, completedTasks: 0, totalTasks: 8 },
        { id: '2', title: 'Module 2: Data Structures and Algorithms', progress: 0, completedTasks: 0, totalTasks: 10 },
        { id: '3', title: 'Module 3: Database Management Systems', progress: 0, completedTasks: 0, totalTasks: 8 },
        { id: '4', title: 'Module 4: Computer Networks', progress: 0, completedTasks: 0, totalTasks: 7 },
        { id: '5', title: 'Module 5: Web Technologies', progress: 0, completedTasks: 0, totalTasks: 6 },
      ];

  // Upcoming Pending Tasks
  const todayIso = new Date().toISOString().split('T')[0];
  const upcomingTasks = allTasks
    .filter((t) => t.status === 'pending' && t.scheduled_date >= todayIso)
    .slice(0, 3);

  // Dynamic Next Recommended Action
  let nextActionTitle = 'Upload your syllabus';
  let nextActionDescription = 'Upload your syllabus to get AI-powered insights and a personalized study plan.';
  let nextActionTab: NavigationTab = 'syllabus';
  let nextActionBtnText = 'Go to My Syllabus';

  if (!hasRealSyllabus) {
    nextActionTitle = 'Upload your syllabus';
    nextActionDescription = 'Upload your college syllabus (PDF or DOCX) to get a structured topic breakdown.';
    nextActionTab = 'syllabus';
    nextActionBtnText = 'Upload Syllabus';
  } else if (!discoveryData || discoveryData.coverage.topics_with_relevant === 0) {
    nextActionTitle = 'Match Educational Videos';
    nextActionDescription = 'Discover verified YouTube video playlists matching your approved course topics.';
    nextActionTab = 'videos';
    nextActionBtnText = 'Discover YouTube Videos';
  } else if (!studyPlan) {
    nextActionTitle = 'Build Study Plan';
    nextActionDescription = 'Generate a personalized daily timetable with tasks and deadline pacing.';
    nextActionTab = 'study-plan';
    nextActionBtnText = 'Generate Study Plan';
  } else if (upcomingTasks.length > 0) {
    nextActionTitle = "Today's Study Block";
    nextActionDescription = `You have ${upcomingTasks.length} pending tasks scheduled for today. Complete them to maintain consistency!`;
    nextActionTab = 'study-plan';
    nextActionBtnText = "Start Today's Tasks";
  } else {
    nextActionTitle = 'All Caught Up!';
    nextActionDescription = 'All current study tasks are complete. Review your revision notes or check upcoming modules.';
    nextActionTab = 'study-plan';
    nextActionBtnText = 'View Study Plan';
  }

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

      {/* 5 Real Metric Cards in a Grid */}
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
            <div className="text-2xl font-bold text-white tracking-tight">{coveragePercent}%</div>
            <p className="text-[10px] text-slate-400 mt-1 m-0">
              {topicsWithVideos} of {totalTopics || 0} topics with videos
            </p>
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
            <div className="text-2xl font-bold text-white tracking-tight">{studyProgressPercent}%</div>
            <p className="text-[10px] text-slate-400 mt-1 m-0">
              {completedTasks} of {totalTasks || 0} tasks completed
            </p>
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
            <div className="text-2xl font-bold text-white tracking-tight">
              {practiceTasks.length > 0 ? `${confidenceScore}%` : 'Not assessed'}
            </div>
            <p className="text-[10px] text-slate-400 mt-1 m-0">
              {practiceTasks.length > 0
                ? `${completedPractice.length} of ${practiceTasks.length} checkpoints passed`
                : 'Awaiting practice completion'}
            </p>
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
            <div className="text-sm font-semibold text-white tracking-tight leading-tight pt-1">
              {readinessLabel}
            </div>
            <p className="text-[10px] text-slate-400 mt-1.5 m-0 truncate">
              {readinessSubtext}
            </p>
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
            <div className="text-sm font-semibold text-white tracking-tight leading-tight pt-1">
              {discoveryData ? `${resourceGaps} Gaps` : 'Not assessed'}
            </div>
            <p className="text-[10px] text-slate-400 mt-1.5 m-0">
              {discoveryData ? `${resourceGaps} topics without video` : 'Requires video discovery'}
            </p>
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
                    {mod.progress}% ({mod.completedTasks}/{mod.totalTasks})
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
                <h4 className="text-xs font-bold text-white m-0 mb-1">{nextActionTitle}</h4>
                <p className="text-xs text-slate-300 font-medium leading-relaxed m-0">
                  {nextActionDescription}
                </p>
              </div>
            </div>

            <button
              onClick={() => onNavigate(nextActionTab)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/20 transition cursor-pointer"
            >
              <span>{nextActionBtnText}</span>
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
                View Full Plan
              </button>
            </div>

            {/* Real or Honest Empty State */}
            {upcomingTasks.length > 0 ? (
              <div className="space-y-2">
                {upcomingTasks.map((t) => (
                  <div key={t.id} className="p-2.5 rounded-xl bg-[#091122] border border-[#18284e] flex items-center justify-between text-xs">
                    <div className="space-y-0.5">
                      <p className="font-semibold text-white m-0 line-clamp-1">{t.title}</p>
                      <span className="text-[10px] text-slate-400">{t.task_type} • {t.duration_minutes} min</span>
                    </div>
                    <span className="text-[10px] text-blue-400 font-mono font-medium">{t.scheduled_date}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-xl bg-[#091122] border border-[#18284e] p-6 text-center space-y-2">
                <div className="w-10 h-10 rounded-full bg-slate-800/80 border border-slate-700/60 flex items-center justify-center mx-auto text-slate-400">
                  <FileText className="w-5 h-5" />
                </div>
                <p className="text-xs font-bold text-slate-300 m-0">
                  {studyPlan ? 'All tasks complete!' : 'No tasks yet'}
                </p>
                <p className="text-[11px] text-slate-400 max-w-xs mx-auto m-0 leading-relaxed">
                  {studyPlan ? 'You are ahead of schedule. Review notes or rest!' : 'Generate your study plan to schedule upcoming tasks.'}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
