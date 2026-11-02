import React, { useState } from 'react';
import { Menu, Search, Bell, Moon, Sun, GraduationCap, ChevronDown, Plus, LogOut, ShieldCheck, Wifi, WifiOff } from 'lucide-react';
import type { NavigationTab, Course, HealthResponse } from '../types';
import type { User } from '../services/supabase';

interface HeaderProps {
  currentTab?: NavigationTab;
  onOpenSidebar: () => void;
  hasSyllabus: boolean;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  activeCourse?: Course | null;
  courses?: Course[];
  onSelectCourse?: (c: Course) => void;
  onNavigateToCourses?: () => void;
  user?: User | null;
  health?: HealthResponse | null;
  healthError?: string | null;
  onSignOut?: () => void;
  onSignIn?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenSidebar,
  hasSyllabus,
  theme,
  onToggleTheme,
  activeCourse,
  courses = [],
  onSelectCourse,
  onNavigateToCourses,
  user,
  health,
  healthError,
  onSignOut,
  onSignIn,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showNotifications, setShowNotifications] = useState(false);
  const [showCourseMenu, setShowCourseMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const notifications = [
    { id: 1, title: 'Phase 2 Agent Ready', time: 'Just now', desc: 'Strands syllabus topic hierarchy analyzer is active.' },
    { id: 2, title: 'Study Target', time: 'Today', desc: hasSyllabus ? 'Syllabus loaded. Ready to build your study schedule.' : 'Upload your syllabus to generate a study roadmap.' },
  ];

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between px-4 sm:px-8 py-3.5 bg-[#091122]/90 backdrop-blur-md border-b border-[#152342]">
      {/* Left: Mobile hamburger & Course Switcher */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenSidebar}
          className="md:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-[#111d38] border border-[#1d2f5a] cursor-pointer"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Active Course Dropdown Switcher */}
        {courses.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setShowCourseMenu(!showCourseMenu)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#0d172e] border border-[#1b2b52] hover:border-blue-500/50 text-xs text-slate-200 transition cursor-pointer"
              title="Switch Active Course"
            >
              <div className="w-2 h-2 rounded-full bg-emerald-400" />
              <GraduationCap className="w-3.5 h-3.5 text-blue-400" />
              <span className="font-semibold text-white max-w-[110px] sm:max-w-[190px] truncate">
                {activeCourse 
                  ? (activeCourse.course_code ? `[${activeCourse.course_code}] ${activeCourse.course_name}` : activeCourse.course_name)
                  : 'Select Course'}
              </span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {showCourseMenu && (
              <div className="absolute left-0 mt-2 w-72 rounded-2xl bg-[#0d172e] border border-[#1b2b52] shadow-2xl p-2 z-50 space-y-1">
                <div className="flex items-center justify-between px-2 py-1.5 border-b border-[#1b2b52] text-[11px] font-semibold text-slate-400">
                  <span>Enrolled Courses</span>
                  {onNavigateToCourses && (
                    <button
                      onClick={() => {
                        setShowCourseMenu(false);
                        onNavigateToCourses();
                      }}
                      className="text-blue-400 hover:text-blue-300 font-medium cursor-pointer"
                    >
                      Manage All
                    </button>
                  )}
                </div>

                <div className="max-h-56 overflow-y-auto space-y-0.5">
                  {courses.filter(c => !c.is_archived).map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        if (onSelectCourse) onSelectCourse(c);
                        setShowCourseMenu(false);
                      }}
                      className={`w-full px-2.5 py-2 rounded-xl text-left text-xs flex items-center justify-between transition cursor-pointer ${
                        activeCourse?.id === c.id
                          ? 'bg-blue-600/20 text-blue-300 font-semibold border border-blue-500/30'
                          : 'text-slate-300 hover:bg-[#132247] hover:text-white'
                      }`}
                    >
                      <div className="truncate pr-2">
                        <p className="truncate font-medium text-white">{c.course_name}</p>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {c.course_code || 'General'} • {c.progress_percentage}% done
                        </span>
                      </div>
                      {activeCourse?.id === c.id && (
                        <div className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
                      )}
                    </button>
                  ))}
                </div>

                {onNavigateToCourses && (
                  <div className="pt-1 border-t border-[#1b2b52]">
                    <button
                      onClick={() => {
                        setShowCourseMenu(false);
                        onNavigateToCourses();
                      }}
                      className="w-full py-1.5 px-2 rounded-lg text-xs text-blue-400 hover:bg-blue-600/10 flex items-center justify-center gap-1.5 font-medium cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add Another Course
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Center: Search Bar (Matches Reference: "Search anything...") */}
      <div className="flex-1 max-w-md mx-4">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search anything..."
            className="w-full pl-9 pr-4 py-2 rounded-full bg-[#0d172e] border border-[#1b2b52] text-xs text-slate-200 placeholder-slate-400 focus:outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
          />
        </div>
      </div>

      {/* Right Controls: Health Pill, Notifications, Theme toggle, Profile Avatar */}
      <div className="flex items-center gap-2.5 relative">
        {/* Backend Health Status Indicator */}
        <div
          className={`hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono border transition-all select-none ${
            health?.status === 'healthy' || health?.status === 'ok'
              ? health?.database_connected === false
                ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : healthError
              ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              : 'bg-slate-500/10 text-slate-400 border-slate-500/30'
          }`}
          title={
            health?.status === 'healthy' || health?.status === 'ok'
              ? health?.database_connected === false
                ? `FastAPI Online (v${health.version}) • Database probe degraded/timed out`
                : `FastAPI Backend Online (v${health.version}) • Database Connected`
              : healthError
              ? `FastAPI Backend Offline: ${healthError}`
              : 'Connecting to FastAPI Backend...'
          }
        >
          {health?.status === 'healthy' || health?.status === 'ok' ? (
            health?.database_connected === false ? (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
            ) : (
              <Wifi className="w-3 h-3 text-emerald-400" />
            )
          ) : healthError ? (
            <WifiOff className="w-3 h-3 text-rose-400" />
          ) : (
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-ping" />
          )}
          <span className="font-semibold uppercase tracking-wider text-[10px]">
            {health?.status === 'healthy' || health?.status === 'ok'
              ? health?.database_connected === false
                ? `Online (v${health.version}) • DB Degraded`
                : `Online (v${health.version})`
              : healthError
              ? 'Offline'
              : 'Connecting...'}
          </span>
        </div>

        {/* Notification Bell */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 rounded-full bg-[#0d172e] hover:bg-[#152449] border border-[#1b2b52] text-slate-300 hover:text-white transition relative cursor-pointer"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="w-2 h-2 rounded-full bg-blue-500 absolute top-1.5 right-1.5 ring-2 ring-[#091122]" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-72 rounded-2xl bg-[#0d172e] border border-[#1b2b52] shadow-2xl p-3 z-50 space-y-2">
              <div className="flex items-center justify-between pb-2 border-b border-[#1b2b52] text-xs font-semibold text-white">
                <span>Notifications</span>
                <span className="text-[10px] text-blue-400 font-mono">2 New</span>
              </div>
              <div className="space-y-2">
                {notifications.map((n) => (
                  <div key={n.id} className="p-2 rounded-xl bg-[#091122] border border-[#162548] text-xs space-y-0.5">
                    <p className="font-semibold text-white m-0">{n.title}</p>
                    <p className="text-[11px] text-slate-400 m-0">{n.desc}</p>
                    <span className="text-[10px] text-slate-500">{n.time}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Theme Toggle Button */}
        <button
          onClick={onToggleTheme}
          className="p-2 rounded-full bg-[#0d172e] hover:bg-[#152449] border border-[#1b2b52] text-slate-300 hover:text-white transition cursor-pointer"
          aria-label="Toggle Theme"
          title="Toggle Dark / Light Theme"
        >
          {theme === 'dark' ? <Moon className="w-4 h-4 text-blue-400" /> : <Sun className="w-4 h-4 text-amber-400" />}
        </button>

        {/* User Profile Avatar & Menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white font-bold text-xs shadow-md shadow-purple-600/30 hover:ring-2 hover:ring-blue-500/50 transition cursor-pointer select-none overflow-hidden"
            title={user ? (user.user_metadata?.full_name || user.email || 'Student Profile') : 'Student Profile'}
          >
            {user?.user_metadata?.avatar_url || user?.user_metadata?.picture ? (
              <img
                src={user.user_metadata?.avatar_url || user.user_metadata?.picture}
                alt="Avatar"
                className="w-full h-full object-cover"
                referrerPolicy="no-referrer"
              />
            ) : (
              <span>
                {user?.user_metadata?.full_name
                  ? user.user_metadata.full_name.charAt(0).toUpperCase()
                  : user?.email
                  ? user.email.charAt(0).toUpperCase()
                  : 'S'}
              </span>
            )}
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-[#0d172e] border border-[#1b2b52] shadow-2xl p-3 z-50 space-y-2">
              {user ? (
                <>
                  <div className="pb-2.5 border-b border-[#1b2b52] space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-blue-600/30 border border-blue-500/40 flex items-center justify-center text-xs font-bold text-blue-300 shrink-0">
                        {user.user_metadata?.full_name
                          ? user.user_metadata.full_name.charAt(0).toUpperCase()
                          : user.email?.charAt(0).toUpperCase() || 'U'}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-white truncate m-0">
                          {user.user_metadata?.full_name || 'Student Account'}
                        </p>
                        <p className="text-[11px] text-slate-400 truncate m-0">
                          {user.email || 'Google User'}
                        </p>
                      </div>
                    </div>
                    <div className="pt-1 flex items-center gap-1.5 text-[10px] text-emerald-400 font-medium">
                      <ShieldCheck className="w-3 h-3" />
                      <span>Google Authenticated (ES256)</span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setShowUserMenu(false);
                      if (onSignOut) onSignOut();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-rose-300 hover:text-rose-200 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/30 transition cursor-pointer text-left"
                  >
                    <LogOut className="w-3.5 h-3.5 text-rose-400" />
                    <span>Sign Out</span>
                  </button>
                </>
              ) : (
                <div className="space-y-2">
                  <div className="pb-2 border-b border-[#1b2b52]">
                    <p className="text-xs font-bold text-white m-0">Local Mode</p>
                    <p className="text-[11px] text-slate-400 m-0">Not signed in</p>
                  </div>
                  {onSignIn && (
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        onSignIn();
                      }}
                      className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition cursor-pointer"
                    >
                      <span>Sign In with Google</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
