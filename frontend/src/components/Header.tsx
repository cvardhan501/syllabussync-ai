import React from 'react';
import { Menu, Sparkles, BookOpen, Clock } from 'lucide-react';
import type { NavigationTab } from '../types';

interface HeaderProps {
  currentTab: NavigationTab;
  onOpenSidebar: () => void;
  hasSyllabus: boolean;
}

export const Header: React.FC<HeaderProps> = ({ currentTab, onOpenSidebar, hasSyllabus }) => {
  const titles: Record<NavigationTab, { title: string; subtitle: string }> = {
    dashboard: {
      title: 'Dashboard Overview',
      subtitle: 'Welcome to your AI-guided course roadmap & study assistant',
    },
    syllabus: {
      title: 'My Syllabus',
      subtitle: 'Upload, validate, and inspect course syllabus documents',
    },
    'study-plan': {
      title: 'Adaptive Study Plan',
      subtitle: 'Daily roadmap scheduled around real educational video lectures',
    },
    progress: {
      title: 'Study Progress & Readiness',
      subtitle: 'Track topic mastery, study streaks, and exam deadline feasibility',
    },
    settings: {
      title: 'Settings & Architecture',
      subtitle: 'Configure backend parameters, study pace, and view project phase status',
    },
  };

  const current = titles[currentTab];

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between px-4 sm:px-8 py-4 bg-slate-950/70 backdrop-blur-md border-b border-slate-800/80">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenSidebar}
          className="md:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-900 border border-slate-800 cursor-pointer"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white m-0">
            {current.title}
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5 m-0 hidden sm:block">
            {current.subtitle}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        {hasSyllabus ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-800/60">
            <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
            <span className="hidden sm:inline">Active Syllabus Loaded</span>
            <span className="sm:hidden">Loaded</span>
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-900 text-slate-400 border border-slate-800">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span className="hidden sm:inline">Awaiting Syllabus</span>
            <span className="sm:hidden">Empty</span>
          </span>
        )}

        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-indigo-950/40 border border-indigo-800/40 text-[11px] font-mono text-indigo-300">
          <Sparkles className="w-3 h-3 text-indigo-400" />
          <span>Hackathon MVP</span>
        </div>
      </div>
    </header>
  );
};
