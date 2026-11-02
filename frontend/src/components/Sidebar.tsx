import React from 'react';
import { 
  LayoutDashboard, 
  BookOpen, 
  PlaySquare, 
  CalendarDays, 
  BarChart3, 
  Settings, 
  GraduationCap,
  Wifi,
  WifiOff,
  X
} from 'lucide-react';
import type { NavigationTab, HealthResponse } from '../types';
import { StudentAvatarIllustration } from './Illustrations';

interface SidebarProps {
  currentTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  isOpen: boolean;
  onClose: () => void;
  health: HealthResponse | null;
  healthError: string | null;
  onOpenGuideModal: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  isOpen,
  onClose,
  health,
  healthError,
  onOpenGuideModal,
}) => {
  const navItems: { id: NavigationTab; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'courses', label: 'My Courses', icon: GraduationCap },
    { id: 'syllabus', label: 'My Syllabus', icon: BookOpen },
    { id: 'videos', label: 'Video Library', icon: PlaySquare },
    { id: 'study-plan', label: 'Study Plan', icon: CalendarDays },
    { id: 'progress', label: 'Progress', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-xs md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-[#091122] border-r border-[#152342] flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0 md:static ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-[#152342]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-600/30 text-white">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-base tracking-tight text-white block leading-tight">
                SyllabusSync <span className="text-blue-400">AI</span>
              </span>
              <p className="text-[11px] text-slate-400 font-medium m-0">Smart Learning Agent</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="md:hidden text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 cursor-pointer"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id);
                  onClose();
                }}
                className={`w-full flex items-center gap-3.5 px-4 py-2.5 rounded-xl font-medium text-sm transition-all text-left cursor-pointer ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-[#111d38]'
                }`}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Need Help Bottom Card (Matches Reference Exactly) */}
        <div className="p-3 mx-3 mb-3 rounded-2xl bg-[#0e1a34] border border-[#1d2f5a] relative overflow-hidden">
          <div className="flex items-start justify-between gap-2">
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-white m-0">Need help?</h4>
              <p className="text-[11px] text-slate-400 leading-tight m-0">
                Get study tips & guides for better learning.
              </p>
            </div>
            <StudentAvatarIllustration className="w-9 h-9 shrink-0" />
          </div>
          <button
            onClick={onOpenGuideModal}
            className="w-full mt-3 py-1.5 px-3 rounded-xl bg-blue-600/30 hover:bg-blue-600 text-blue-300 hover:text-white border border-blue-500/40 text-xs font-semibold transition cursor-pointer text-center"
          >
            View Guide
          </button>
        </div>

        {/* System Health Status Footer */}
        <div className="px-4 py-2.5 border-t border-[#152342] bg-[#070d1c]">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400 font-medium">FastAPI Backend</span>
            {health?.status === 'healthy' || health?.status === 'ok' ? (
              <span className="inline-flex items-center gap-1.5 text-emerald-400 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <Wifi className="w-3 h-3" />
                <span>Online (v{health.version})</span>
              </span>
            ) : healthError ? (
              <span className="inline-flex items-center gap-1 text-rose-400 font-medium">
                <WifiOff className="w-3 h-3" />
                <span>Offline</span>
              </span>
            ) : (
              <span className="text-slate-500">Connecting...</span>
            )}
          </div>
        </div>
      </aside>
    </>
  );
};
