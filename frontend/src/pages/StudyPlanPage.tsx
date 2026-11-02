import React, { useState, useEffect, useRef } from 'react';
import { 
  CalendarDays, 
  Check, 
  ListTodo,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  FileText,
  ExternalLink,
  Loader2,
  X,
  Save,
  CheckCircle2,
  Clock
} from 'lucide-react';
import type { 
  NavigationTab, 
  SyllabusAnalysisResponse, 
  StudyPlanResponse,
  TaskItemSchema,
  Course
} from '../types';
import { apiService, ApiErrorResponse } from '../services/api';
import { SproutingPlantIllustration } from '../components/Illustrations';

interface StudyPlanPageProps {
  analyzedSyllabus: SyllabusAnalysisResponse | null;
  onNavigate: (tab: NavigationTab) => void;
  examDate?: string;
  initialPlan?: StudyPlanResponse | null;
  onPlanUpdated?: (plan: StudyPlanResponse | null) => void;
  courses?: Course[];
  activeCourse?: Course | null;
  onSelectCourse?: (course: Course) => void;
}

export const StudyPlanPage: React.FC<StudyPlanPageProps> = ({
  analyzedSyllabus,
  onNavigate,
  examDate,
  initialPlan,
  onPlanUpdated,
  courses = [],
  activeCourse,
  onSelectCourse,
}) => {
  const currentSyllabusId = activeCourse?.syllabus_id || analyzedSyllabus?.syllabus_id || activeCourse?.id;
  const currentCourseName = activeCourse?.course_name || analyzedSyllabus?.course_name || 'Course';
  const currentCourseCode = activeCourse?.course_code || analyzedSyllabus?.course_code;

  const [plan, setPlan] = useState<StudyPlanResponse | null>(() => initialPlan || null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRescheduling, setIsRescheduling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadSeqRef = useRef(0);

  // User-selected target exam date: prioritize syllabus plan date, prop, or 60 days in future
  const getInitialExamDate = () => {
    if (examDate && examDate > new Date().toISOString().split('T')[0]) {
      return examDate;
    }
    const d = new Date();
    d.setDate(d.getDate() + 60);
    return d.toISOString().split('T')[0];
  };

  const [targetExamDate, setTargetExamDate] = useState<string>(getInitialExamDate);

  // Sync targetExamDate when plan or examDate prop updates
  useEffect(() => {
    if (plan?.exam_date) {
      setTargetExamDate(plan.exam_date);
    } else if (examDate && examDate > new Date().toISOString().split('T')[0]) {
      setTargetExamDate(examDate);
    }
  }, [plan?.exam_date, examDate]);

  const todayIso = new Date().toISOString().split('T')[0];
  const minFutureDate = new Date(Date.now() + 86400000).toISOString().split('T')[0];
  const isExamDateInPast = Boolean(targetExamDate && targetExamDate <= todayIso);

  const [viewMode, setViewMode] = useState<'daily' | 'weekly'>('daily');
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    if (initialPlan?.daily_schedules?.length) {
      const today = new Date().toISOString().split('T')[0];
      const hasToday = initialPlan.daily_schedules.some((d) => d.date === today);
      return hasToday ? today : initialPlan.daily_schedules[0]?.date || '';
    }
    return '';
  });

  // Notes Modal State
  const [activeNoteTask, setActiveNoteTask] = useState<TaskItemSchema | null>(null);
  const [noteContent, setNoteContent] = useState('');
  const [isSavingNote, setIsSavingNote] = useState(false);

  // Load active course study plan with sequence guard and race condition immunity
  useEffect(() => {
    let isMounted = true;
    const reqSeq = ++loadSeqRef.current;

    if (!currentSyllabusId) {
      setPlan(null);
      setIsLoading(false);
      return;
    }

    // Immediately clear previous course's plan so no stale tasks are visible while switching
    setPlan(null);
    setIsLoading(true);
    setError(null);

    const loadPlan = async () => {
      try {
        const data = await apiService.getStudyPlan(currentSyllabusId);
        if (isMounted && reqSeq === loadSeqRef.current) {
          setPlan(data);
          if (onPlanUpdated) onPlanUpdated(data);
          // Set selectedDate to today or first day
          const today = new Date().toISOString().split('T')[0];
          const hasToday = data.daily_schedules.some((d) => d.date === today);
          setSelectedDate(hasToday ? today : data.daily_schedules[0]?.date || '');
        }
      } catch (err: any) {
        if (isMounted && reqSeq === loadSeqRef.current) {
          if (err instanceof ApiErrorResponse) {
            if (err.status === 404) {
              // Clean empty state for course that does not yet have a generated study plan
              setPlan(null);
            } else {
              setError(err.message || 'Failed to load study plan.');
            }
          } else {
            setError(err?.message || 'Failed to load study plan.');
          }
        }
      } finally {
        if (isMounted && reqSeq === loadSeqRef.current) {
          setIsLoading(false);
        }
      }
    };

    loadPlan();
    return () => {
      isMounted = false;
    };
  }, [currentSyllabusId]);

  // Generate / Regenerate Study Plan
  const handleGeneratePlan = async () => {
    if (!currentSyllabusId) return;
    const today = new Date().toISOString().split('T')[0];
    if (!targetExamDate || targetExamDate <= today) {
      setError(`Exam date (${targetExamDate || 'empty'}) cannot be in the past. Please select a future exam date.`);
      return;
    }
    setIsGenerating(true);
    setError(null);
    try {
      const data = await apiService.createStudyPlan(currentSyllabusId, {
        exam_date: targetExamDate,
        daily_target_minutes: 120,
        preserve_completed: true,
      });
      setPlan(data);
      if (onPlanUpdated) onPlanUpdated(data);
      const hasToday = data.daily_schedules.some((d) => d.date === today);
      setSelectedDate(hasToday ? today : data.daily_schedules[0]?.date || '');
    } catch (err: any) {
      setError(err.message || 'Failed to generate study timetable.');
    } finally {
      setIsGenerating(false);
    }
  };

  // Toggle task completion in real-time
  const handleToggleTask = async (task: TaskItemSchema) => {
    if (!plan) return;
    const newCompleted = task.status !== 'completed';

    // Optimistic UI update
    setPlan((prev) => {
      if (!prev) return prev;
      const updatedSchedules = prev.daily_schedules.map((group) => {
        const updatedTasks = group.tasks.map((t) =>
          t.id === task.id ? { ...t, status: newCompleted ? ('completed' as const) : ('pending' as const) } : t
        );
        const compMin = updatedTasks.reduce(
          (sum, t) => sum + (t.status === 'completed' ? t.duration_minutes : 0),
          0
        );
        return { ...group, tasks: updatedTasks, completed_minutes: compMin };
      });

      const totalCompletedTasks = updatedSchedules.reduce(
        (sum, g) => sum + g.tasks.filter((t) => t.status === 'completed').length,
        0
      );
      const totalCompMinutes = updatedSchedules.reduce((sum, g) => sum + g.completed_minutes, 0);
      const progress = prev.total_planned_minutes > 0
        ? Math.round((totalCompMinutes / prev.total_planned_minutes) * 100)
        : 0;

      const nextPlan = {
        ...prev,
        daily_schedules: updatedSchedules,
        completed_tasks_count: totalCompletedTasks,
        completed_minutes: totalCompMinutes,
        progress_percentage: progress,
      };
      if (onPlanUpdated) onPlanUpdated(nextPlan);
      return nextPlan;
    });

    try {
      await apiService.updateTaskStatus(plan.id, task.id, newCompleted);
    } catch {
      // Revert on failure
      const refreshed = await apiService.getStudyPlan(plan.syllabus_id);
      setPlan(refreshed);
      if (onPlanUpdated) onPlanUpdated(refreshed);
    }
  };

  // Reschedule missed sessions
  const handleReschedule = async () => {
    if (!plan) return;
    setIsRescheduling(true);
    setError(null);
    try {
      const updated = await apiService.reschedulePlan(plan.id);
      setPlan(updated);
      if (onPlanUpdated) onPlanUpdated(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to reschedule missed tasks.');
    } finally {
      setIsRescheduling(false);
    }
  };

  // Open Notes Modal
  const handleOpenNotes = (task: TaskItemSchema) => {
    setActiveNoteTask(task);
    setNoteContent(task.notes || '');
  };

  // Save Notes
  const handleSaveNotes = async () => {
    if (!plan || !activeNoteTask) return;
    setIsSavingNote(true);
    try {
      await apiService.saveTaskNote(plan.id, activeNoteTask.id, noteContent);
      setPlan((prev) => {
        if (!prev) return prev;
        const updatedSchedules = prev.daily_schedules.map((group) => ({
          ...group,
          tasks: group.tasks.map((t) =>
            t.id === activeNoteTask.id ? { ...t, notes: noteContent } : t
          ),
        }));
        const nextPlan = { ...prev, daily_schedules: updatedSchedules };
        if (onPlanUpdated) onPlanUpdated(nextPlan);
        return nextPlan;
      });
      setActiveNoteTask(null);
    } catch (err: any) {
      setError(err.message || 'Failed to save notes.');
    } finally {
      setIsSavingNote(false);
    }
  };

  // Active Schedule Day
  const activeDayGroup = plan?.daily_schedules.find((d) => d.date === selectedDate) 
    || plan?.daily_schedules[0];

  const activeTasks = activeDayGroup?.tasks || [];
  const completedTodayCount = activeTasks.filter((t) => t.status === 'completed').length;
  const progressPercentToday = activeTasks.length > 0 
    ? Math.round((completedTodayCount / activeTasks.length) * 100) 
    : 0;

  // Check if any overdue uncompleted tasks exist before today
  const hasOverdueTasks = (plan?.daily_schedules || []).some(
    (g) => g.date < todayIso && g.tasks.some((t) => t.status !== 'completed')
  );

  // SVG Gauge
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progressPercentToday / 100) * circumference;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          {courses.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap mb-1.5">
              {courses.length > 1 && onSelectCourse && (
                <div className="relative inline-block mr-1">
                  <select
                    value={activeCourse?.id || ''}
                    onChange={(e) => {
                      const c = courses.find((item) => item.id === e.target.value);
                      if (c) onSelectCourse(c);
                    }}
                    className="text-xs bg-[#0b1429] border border-[#1b2b52] text-white px-3 py-1 rounded-xl focus:outline-hidden focus:border-blue-500 cursor-pointer font-medium"
                    aria-label="Select course for study plan"
                  >
                    {courses.map((c) => (
                      <option key={c.id} value={c.id} className="bg-[#0b1429] text-white">
                        {c.course_code ? `[${c.course_code}] ${c.course_name}` : c.course_name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {currentCourseCode && (
                <span className="px-2.5 py-0.5 rounded-lg bg-blue-600/20 text-blue-300 border border-blue-500/40 font-mono text-xs font-bold uppercase tracking-wider">
                  {currentCourseCode}
                </span>
              )}
              <span className="text-xs text-slate-400 font-semibold truncate max-w-[280px]">
                {currentCourseName}
              </span>
            </div>
          )}

          <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight m-0">
            Your Personalized Study Plan
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5 m-0">
            Stay consistent. One step at a time.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Exam Date Picker Pill */}
          <div className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-semibold ${
            isExamDateInPast
              ? 'bg-amber-950/40 border-amber-500/60 text-amber-300'
              : 'bg-[#0e1a38] border-[#1e3262] text-blue-300'
          }`}>
            <CalendarDays className={`w-4 h-4 ${isExamDateInPast ? 'text-amber-400' : 'text-blue-400'}`} />
            <span className="text-slate-400 font-medium">Exam Date:</span>
            <input
              type="date"
              min={minFutureDate}
              value={targetExamDate}
              onChange={(e) => {
                setTargetExamDate(e.target.value);
                setError(null);
              }}
              className="bg-transparent text-white font-semibold focus:outline-hidden cursor-pointer"
              title="Click to change target exam date"
            />
          </div>

          {currentSyllabusId && plan && (
            <button
              onClick={handleGeneratePlan}
              disabled={isGenerating}
              className="px-3.5 py-1.5 rounded-xl bg-[#0b1429] hover:bg-[#132247] border border-[#1b2b52] text-xs font-semibold text-slate-200 hover:text-white transition cursor-pointer"
            >
              {isGenerating ? 'Regenerating...' : 'Regenerate Plan'}
            </button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="rounded-xl bg-rose-950/40 border border-rose-800/60 p-3.5 text-xs text-rose-300 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200">Dismiss</button>
        </div>
      )}

      {/* Feasibility Warning Banner */}
      {plan?.feasibility_status === 'impossible' && (
        <div className="rounded-2xl bg-rose-950/30 border border-rose-600/50 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-rose-600/20 border border-rose-500/40 flex items-center justify-center text-rose-400 shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-rose-200 m-0">Impossible Deadline Warning</h4>
              <p className="text-xs text-rose-300/90 m-0 mt-0.5 leading-relaxed">
                {plan.feasibility_warning}
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('settings')}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shrink-0 cursor-pointer shadow transition"
          >
            Adjust Availability in Settings
          </button>
        </div>
      )}

      {plan?.feasibility_status === 'tight' && (
        <div className="rounded-2xl bg-amber-950/30 border border-amber-600/50 p-4 flex items-center gap-3 text-xs text-amber-200">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
          <span>{plan.feasibility_warning}</span>
        </div>
      )}

      {/* Missed Day Recovery Banner */}
      {hasOverdueTasks && (
        <div className="rounded-2xl bg-blue-950/30 border border-blue-500/40 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <RotateCcw className="w-4 h-4 text-blue-400 shrink-0" />
            <p className="text-xs text-blue-200 m-0">
              You have unfinished tasks from previous days. Redistribute them into future available study slots?
            </p>
          </div>
          <button
            onClick={handleReschedule}
            disabled={isRescheduling}
            className="px-4 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shrink-0 cursor-pointer shadow transition flex items-center gap-1.5"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isRescheduling ? 'animate-spin' : ''}`} />
            <span>{isRescheduling ? 'Rescheduling...' : 'Reschedule Missed Sessions'}</span>
          </button>
        </div>
      )}

      {/* Empty State: No Syllabus */}
      {!currentSyllabusId && !isLoading && (
        <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-600/15 border border-blue-500/30 text-blue-400 flex items-center justify-center mx-auto">
            <ListTodo className="w-7 h-7" />
          </div>
          <div className="space-y-1 max-w-md mx-auto">
            <h3 className="text-base font-bold text-white m-0">Upload Syllabus to Generate Plan</h3>
            <p className="text-xs text-slate-400 m-0">
              Your personalized timetable will map out daily study blocks, matched video lessons, and practice questions once your syllabus is parsed.
            </p>
          </div>
          <button
            onClick={() => onNavigate('syllabus')}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/30 transition cursor-pointer"
          >
            Go to My Syllabus
          </button>
        </div>
      )}

      {/* Empty State: Syllabus Exists but Plan not yet created */}
      {currentSyllabusId && !plan && !isLoading && (
        <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-600/15 border border-blue-500/30 text-blue-400 flex items-center justify-center mx-auto">
            <Sparkles className="w-7 h-7" />
          </div>
          <div className="space-y-1 max-w-lg mx-auto">
            <h3 className="text-base font-bold text-white m-0">
              Ready to Build Your Study Roadmap
            </h3>
            <p className="text-xs text-slate-400 m-0">
              Generate a timetable for <span className="font-semibold text-white">{currentCourseName}</span> targeting your exam on {targetExamDate}.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <div className={`flex items-center gap-2 px-3.5 py-2 rounded-xl border text-xs ${
              isExamDateInPast
                ? 'bg-amber-950/20 border-amber-500/40 text-amber-300'
                : 'bg-[#070e20] border-[#1b2b52] text-slate-300'
            }`}>
              <CalendarDays className={`w-4 h-4 shrink-0 ${isExamDateInPast ? 'text-amber-400' : 'text-blue-400'}`} />
              <span className="text-slate-400 text-[11px]">Exam Date:</span>
              <input
                type="date"
                min={minFutureDate}
                value={targetExamDate}
                onChange={(e) => {
                  setTargetExamDate(e.target.value);
                  setError(null);
                }}
                className="bg-transparent text-white font-semibold focus:outline-hidden cursor-pointer"
                title="Select your target exam date"
              />
            </div>

            <button
              onClick={handleGeneratePlan}
              disabled={isGenerating}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/30 transition cursor-pointer"
            >
              <Sparkles className="w-4 h-4 text-cyan-300" />
              <span>{isGenerating ? 'Building Schedule...' : 'Generate Personalized Study Plan'}</span>
            </button>
          </div>

          {isExamDateInPast && (
            <div className="p-3 max-w-md mx-auto rounded-xl bg-amber-950/30 border border-amber-600/40 text-xs text-amber-300 flex items-center justify-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>The current exam date ({targetExamDate}) is in the past. Please choose a future date above to build your study schedule.</span>
            </div>
          )}
        </div>
      )}

      {isLoading && (
        <div className="p-12 text-center rounded-2xl bg-[#0b1429] border border-[#18284e] space-y-2">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Loading your study roadmap...</p>
        </div>
      )}

      {/* Main Schedule Content */}
      {plan && !isLoading && (
        <>
          {/* View Toggle & Calendar Days Bar */}
          <div className="p-3.5 rounded-2xl bg-[#0b1429] border border-[#18284e] flex flex-col md:flex-row md:items-center justify-between gap-4">
            {/* View Mode Toggle */}
            <div className="flex items-center p-1 bg-[#070e20] border border-[#1b2b54] rounded-xl self-start">
              <button
                onClick={() => setViewMode('daily')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                  viewMode === 'daily'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Daily View
              </button>
              <button
                onClick={() => setViewMode('weekly')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                  viewMode === 'weekly'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Weekly View
              </button>
            </div>

            {/* Date Selector Row */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 max-w-full">
              {plan.daily_schedules.map((group) => {
                const isSelected = group.date === selectedDate;
                const isAllCompleted = group.tasks.length > 0 && group.tasks.every((t) => t.status === 'completed');

                return (
                  <button
                    key={group.date}
                    onClick={() => setSelectedDate(group.date)}
                    className={`flex flex-col items-center justify-center min-w-[56px] py-2 px-2.5 rounded-xl transition cursor-pointer shrink-0 border ${
                      isSelected
                        ? 'bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-600/30'
                        : group.is_today
                        ? 'bg-[#111e3b] text-blue-300 border-blue-500/40 hover:bg-[#162548]'
                        : 'bg-[#070e20] text-slate-400 border-[#18284e] hover:border-slate-700 hover:text-slate-200'
                    }`}
                  >
                    <span className="text-[10px] font-semibold uppercase">{group.day_name}</span>
                    <span className="text-sm font-extrabold mt-0.5">{group.formatted_date.split(' ')[0]}</span>
                    {isAllCompleted && (
                      <CheckCircle2 className="w-3 h-3 text-emerald-400 mt-0.5" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Two-Column Workspace */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Tasks List (8 cols) */}
            <div className="lg:col-span-8 rounded-2xl bg-[#0b1429] border border-[#18284e] p-5 sm:p-6 space-y-4 shadow-md">
              <div className="flex items-center justify-between border-b border-[#18284e] pb-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-white m-0">
                    Tasks for {activeDayGroup?.formatted_date || 'Today'}
                  </h3>
                  <span className="text-xs text-blue-400 font-medium px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20">
                    {activeTasks.length} {activeTasks.length === 1 ? 'task' : 'tasks'}
                  </span>
                </div>

                <span className="text-xs text-slate-400">
                  {activeDayGroup?.total_minutes || 0} min total planned
                </span>
              </div>

              {/* Tasks List */}
              <div className="space-y-3 pt-1">
                {activeTasks.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-400 bg-[#070e20] rounded-xl border border-[#18284e]">
                    No study tasks scheduled for this date. Rest day or revision!
                  </div>
                ) : (
                  activeTasks.map((task) => {
                    const isCompleted = task.status === 'completed';

                    return (
                      <div
                        key={task.id}
                        className={`p-3.5 rounded-xl border transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                          isCompleted
                            ? 'bg-[#070e20]/60 border-[#152342] opacity-80'
                            : 'bg-[#091122] border-[#18284e] hover:border-blue-500/40 shadow-xs'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          {/* Checkbox */}
                          <button
                            onClick={() => handleToggleTask(task)}
                            className={`w-5 h-5 rounded-md border flex items-center justify-center shrink-0 mt-0.5 transition cursor-pointer ${
                              isCompleted
                                ? 'bg-emerald-600 border-emerald-500 text-white'
                                : 'border-[#2d4272] hover:border-blue-400 bg-[#070e20]'
                            }`}
                            title={isCompleted ? 'Mark pending' : 'Mark completed'}
                          >
                            {isCompleted && <Check className="w-3.5 h-3.5" />}
                          </button>

                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              {/* Task Type Pill */}
                              <span
                                className={`text-[10px] font-semibold px-2 py-0.5 rounded-md uppercase tracking-wider ${
                                  task.task_type === 'Video'
                                    ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                                    : task.task_type === 'Practice'
                                    ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                                    : 'bg-blue-500/15 text-blue-300 border border-blue-500/30'
                                }`}
                              >
                                {task.task_type}
                              </span>

                              <span className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                                <Clock className="w-3 h-3 text-slate-500" />
                                {task.duration_minutes} min
                              </span>

                              {task.notes && (
                                <span className="text-[10px] text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded-sm">
                                  Notes saved
                                </span>
                              )}
                            </div>

                            <p
                              className={`text-xs font-semibold m-0 leading-snug ${
                                isCompleted ? 'line-through text-slate-500' : 'text-white'
                              }`}
                            >
                              {task.title}
                            </p>
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                          {task.video_url && (
                            <button
                              onClick={() => window.open(task.video_url, '_blank')}
                              className="px-2.5 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 text-[11px] font-medium flex items-center gap-1 cursor-pointer transition"
                              title="Watch Lecture"
                            >
                              <span>Lecture</span>
                              <ExternalLink className="w-3 h-3" />
                            </button>
                          )}

                          <button
                            onClick={() => handleOpenNotes(task)}
                            className="px-2.5 py-1.5 rounded-lg bg-[#111e3b] hover:bg-[#182c56] text-slate-300 border border-[#1b2f5c] text-[11px] font-medium flex items-center gap-1 cursor-pointer transition"
                            title="Open Study Notes"
                          >
                            <FileText className="w-3 h-3 text-blue-400" />
                            <span>Notes</span>
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Right Column: Gauges & Motivation (4 cols) */}
            <div className="lg:col-span-4 space-y-4">
              {/* Daily Progress Radial Gauge Card */}
              <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-5 text-center space-y-4 shadow-md">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider m-0">
                  Daily Workload Gauge
                </h4>

                {/* Circular Gauge */}
                <div className="relative w-28 h-28 mx-auto flex items-center justify-center">
                  <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                    <circle
                      cx="50"
                      cy="50"
                      r={radius}
                      stroke="#162548"
                      strokeWidth="8"
                      fill="none"
                    />
                    <circle
                      cx="50"
                      cy="50"
                      r={radius}
                      stroke="#3b82f6"
                      strokeWidth="8"
                      strokeDasharray={circumference}
                      strokeDashoffset={strokeDashoffset}
                      strokeLinecap="round"
                      fill="none"
                      className="transition-all duration-500 ease-out"
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-xl font-extrabold text-white">{progressPercentToday}%</span>
                  </div>
                </div>

                <div>
                  <p className="text-xs font-bold text-white m-0">Today's Progress</p>
                  <p className="text-[11px] text-slate-400 mt-0.5 m-0">
                    {completedTodayCount} of {activeTasks.length} tasks completed
                  </p>
                </div>

                {/* Overall Course Plan Progress Bar */}
                <div className="pt-2 border-t border-[#18284e] space-y-1.5 text-left">
                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>Course Roadmap Progress</span>
                    <span className="font-mono text-blue-400 font-bold">{plan.progress_percentage}%</span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-[#132247] overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all duration-500"
                      style={{ width: `${plan.progress_percentage}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>{plan.completed_tasks_count} / {plan.total_tasks_count} tasks</span>
                    <span>{Math.round(plan.completed_minutes / 60)}h / {Math.round(plan.total_planned_minutes / 60)}h</span>
                  </div>
                </div>
              </div>

              {/* Motivation Card */}
              <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-5 text-center space-y-2 shadow-md">
                <SproutingPlantIllustration className="w-16 h-16 mx-auto" />
                <h4 className="text-xs font-bold text-white m-0">Consistency builds confidence!</h4>
                <p className="text-[11px] text-slate-400 m-0 leading-relaxed">
                  Complete your daily study block to maintain continuous momentum before exam day.
                </p>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Task Notes Modal */}
      {activeNoteTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="rounded-2xl bg-[#0c162e] border border-[#1e305e] max-w-lg w-full p-6 space-y-4 shadow-2xl relative">
            <button
              onClick={() => setActiveNoteTask(null)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#162548] cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <div>
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-400" />
                <h3 className="text-base font-bold text-white m-0">Study Notes</h3>
              </div>
              <p className="text-xs text-slate-400 mt-1 m-0">
                {activeNoteTask.title}
              </p>
            </div>

            <textarea
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              placeholder="Record your insights, formulas, code snippets, or revision questions..."
              rows={6}
              className="w-full p-3 rounded-xl bg-[#070e20] border border-[#1b2b52] text-xs text-white placeholder-slate-500 focus:outline-hidden focus:border-blue-500 resize-none font-sans leading-relaxed"
            />

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-[#18284e]">
              <button
                onClick={() => setActiveNoteTask(null)}
                className="px-4 py-2 rounded-xl bg-[#0f1b36] hover:bg-[#182c56] text-slate-300 text-xs font-medium cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveNotes}
                disabled={isSavingNote}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md cursor-pointer"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{isSavingNote ? 'Saving...' : 'Save Notes'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
