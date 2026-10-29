import React, { useState } from 'react';
import { Menu, Search, Bell, Moon, Sun } from 'lucide-react';
import type { NavigationTab } from '../types';

interface HeaderProps {
  currentTab?: NavigationTab;
  onOpenSidebar: () => void;
  hasSyllabus: boolean;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenSidebar,
  hasSyllabus,
  theme,
  onToggleTheme,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showNotifications, setShowNotifications] = useState(false);

  const notifications = [
    { id: 1, title: 'Phase 2 Agent Ready', time: 'Just now', desc: 'Strands syllabus topic hierarchy analyzer is active.' },
    { id: 2, title: 'Study Target', time: 'Today', desc: hasSyllabus ? 'Syllabus loaded. Ready to build your study schedule.' : 'Upload your syllabus to generate a study roadmap.' },
  ];

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between px-4 sm:px-8 py-3.5 bg-[#091122]/90 backdrop-blur-md border-b border-[#152342]">
      {/* Left: Mobile hamburger & optional page indicator */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenSidebar}
          className="md:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-[#111d38] border border-[#1d2f5a] cursor-pointer"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>
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

      {/* Right Controls: Notifications, Theme toggle, Profile Avatar */}
      <div className="flex items-center gap-2.5 relative">
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

        {/* User Profile Avatar (Matches reference: Purple circle with 'S' initial) */}
        <div 
          className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white font-bold text-xs shadow-md shadow-purple-600/30 cursor-pointer select-none"
          title="Student Profile"
        >
          S
        </div>
      </div>
    </header>
  );
};
