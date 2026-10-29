import React, { useState } from 'react';
import { 
  CalendarDays, 
  Check, 
  ListTodo
} from 'lucide-react';
import type { 
  NavigationTab, 
  SyllabusAnalysisResponse, 
  StudyTaskItem 
} from '../types';
import { SproutingPlantIllustration } from '../components/Illustrations';

interface StudyPlanPageProps {
  analyzedSyllabus: SyllabusAnalysisResponse | null;
  onNavigate: (tab: NavigationTab) => void;
  examDate?: string;
}

export const StudyPlanPage: React.FC<StudyPlanPageProps> = ({
  analyzedSyllabus,
  onNavigate,
  examDate = '25 Apr 2026',
}) => {
  const [viewMode, setViewMode] = useState<'daily' | 'weekly'>('daily');
  const [selectedDayIndex, setSelectedDayIndex] = useState(1); // Tue 22

  const days = [
    { name: 'Mon', date: '21' },
    { name: 'Tue', date: '22' },
    { name: 'Wed', date: '23' },
    { name: 'Thu', date: '24' },
    { name: 'Fri', date: '25' },
    { name: 'Sat', date: '26' },
    { name: 'Sun', date: '27' },
  ];

  // Derive initial tasks from analyzed topics or defaults
  const initialTasks: StudyTaskItem[] = analyzedSyllabus?.modules[0]?.topics?.slice(0, 4).map((t, idx) => ({
    id: t.id || `task_${idx+1}`,
    title: t.title,
    durationMinutes: t.estimated_minutes || 20,
    type: idx % 3 === 0 ? 'Video' : idx % 3 === 1 ? 'Practice' : 'Study',
    completed: idx === 0, // 1st completed by default for demonstration
    topicId: t.id,
  })) || [
    { id: 't1', title: 'Introduction to Core Concepts', durationMinutes: 15, type: 'Video', completed: true },
    { id: 't2', title: 'Syntax & Primitives Breakdown', durationMinutes: 20, type: 'Video', completed: false },
    { id: 't3', title: 'Hands-on Practice Questions', durationMinutes: 30, type: 'Practice', completed: false },
    { id: 't4', title: 'Concept Summary & Quick Revision', durationMinutes: 15, type: 'Study', completed: false },
  ];

  const [tasks, setTasks] = useState<StudyTaskItem[]>(initialTasks);

  const toggleTask = (taskId: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, completed: !t.completed } : t))
    );
  };

  const handleMarkAllCompleted = () => {
    const allDone = tasks.every((t) => t.completed);
    setTasks((prev) => prev.map((t) => ({ ...t, completed: !allDone })));
  };

  // Progress metrics
  const completedCount = tasks.filter((t) => t.completed).length;
  const progressPercent = tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0;

  // SVG circular gauge calculations
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progressPercent / 100) * circumference;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header Row (Matches Reference Screen 6) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight m-0">
            Your Personalized Study Plan
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5 m-0">
            Stay consistent. One step at a time.
          </p>
        </div>

        {/* Exam Date Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#0e1a38] border border-[#1e3262] text-xs font-semibold text-blue-300 self-start sm:self-auto">
          <CalendarDays className="w-4 h-4 text-blue-400" />
          <span>Exam Date: {examDate}</span>
        </div>
      </div>

      {!analyzedSyllabus && (
        <div className="flex items-center justify-between p-3 rounded-xl bg-blue-950/30 border border-blue-800/40 text-xs text-blue-200">
          <span>Using sample curriculum tasks. Upload your syllabus to generate your personalized timetable.</span>
          <button 
            onClick={() => onNavigate('syllabus')}
            className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium ml-3 shrink-0 cursor-pointer"
          >
            Go to Syllabus
          </button>
        </div>
      )}

      {/* View Toggle & Weekdays Row (Matches Reference Screen 6) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-3 rounded-2xl bg-[#0b1429] border border-[#18284e]">
        {/* Daily / Weekly Toggle */}
        <div className="flex items-center p-1 bg-[#070e20] border border-[#1b2b54] rounded-xl self-start sm:self-auto">
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

        {/* Days of the Week Selector */}
        <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto pb-1 sm:pb-0">
          {days.map((day, idx) => {
            const isSelected = selectedDayIndex === idx;

            return (
              <button
                key={day.name}
                onClick={() => setSelectedDayIndex(idx)}
                className={`flex flex-col items-center justify-center w-12 py-2 rounded-xl transition cursor-pointer border ${
                  isSelected
                    ? 'bg-blue-600 border-blue-500 text-white shadow-md shadow-blue-600/30'
                    : 'bg-[#070e20] border-[#18284e] text-slate-400 hover:text-white hover:bg-[#0e1935]'
                }`}
              >
                <span className="text-[10px] font-medium leading-tight">{day.name}</span>
                <span className="text-sm font-bold mt-0.5">{day.date}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Two Column Layout: Today's Tasks (Left) & Study Progress (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column: Today's Tasks (8 cols) */}
        <div className="lg:col-span-8 rounded-2xl bg-[#0b1429] border border-[#18284e] p-5 sm:p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#18284e]">
            <div className="flex items-center gap-2">
              <ListTodo className="w-5 h-5 text-blue-400" />
              <h3 className="text-sm sm:text-base font-bold text-white m-0">
                Today's Tasks ({tasks.length})
              </h3>
            </div>

            <button
              onClick={handleMarkAllCompleted}
              className="text-xs font-semibold text-blue-400 hover:text-blue-300 transition cursor-pointer"
            >
              {tasks.every((t) => t.completed) ? 'Reset Tasks' : '+ Mark All Completed'}
            </button>
          </div>

          {/* Task List */}
          <div className="space-y-3">
            {tasks.map((task, idx) => (
              <div
                key={task.id}
                onClick={() => toggleTask(task.id)}
                className={`p-3.5 rounded-xl border transition cursor-pointer flex items-center justify-between gap-3 ${
                  task.completed
                    ? 'bg-[#081226]/60 border-emerald-900/40 text-slate-400'
                    : 'bg-[#070e20] border-[#162548] hover:border-[#223869] text-white'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className={`w-5 h-5 rounded-md flex items-center justify-center transition border ${
                      task.completed
                        ? 'bg-emerald-500 border-emerald-500 text-white'
                        : 'border-slate-600 bg-[#0c162e]'
                    }`}
                  >
                    {task.completed && <Check className="w-3.5 h-3.5" />}
                  </div>

                  <div className="min-w-0">
                    <p
                      className={`text-xs sm:text-sm font-semibold truncate m-0 ${
                        task.completed ? 'line-through text-slate-400' : 'text-slate-100'
                      }`}
                    >
                      {idx + 1}. {task.title}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[11px] text-slate-400 font-mono">
                    ({task.durationMinutes} min)
                  </span>

                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border ${
                      task.type === 'Video'
                        ? 'bg-blue-950/40 text-blue-300 border-blue-800/40'
                        : task.type === 'Practice'
                        ? 'bg-purple-950/40 text-purple-300 border-purple-800/40'
                        : 'bg-emerald-950/40 text-emerald-300 border-emerald-800/40'
                    }`}
                  >
                    {task.type}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Progress Radial Gauge & Motivation Card (4 cols) */}
        <div className="lg:col-span-4 space-y-5">
          {/* Study Progress Card */}
          <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-5 text-center space-y-4">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider m-0">
              Study Progress
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
                <span className="text-xl font-extrabold text-white">{progressPercent}%</span>
              </div>
            </div>

            <div>
              <p className="text-xs font-bold text-white m-0">Today's Progress</p>
              <p className="text-[11px] text-slate-400 mt-0.5 m-0">
                {completedCount} of {tasks.length} tasks completed
              </p>
            </div>
          </div>

          {/* Motivation Card with Sprouting Seedling (Matches Reference Screen 6) */}
          <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-5 text-center space-y-2">
            <SproutingPlantIllustration className="w-16 h-16 mx-auto" />
            <h4 className="text-xs font-bold text-white m-0">Consistency builds confidence!</h4>
            <p className="text-[11px] text-slate-400 m-0 leading-relaxed">
              Complete your daily tasks to stay on track before exam day.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
