import React from 'react';

export const MountainClimbIllustration: React.FC<{ className?: string }> = ({ className = 'w-48 h-32' }) => (
  <div className={`relative flex items-center justify-center ${className}`}>
    <svg viewBox="0 0 260 160" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      {/* Background glow and stars */}
      <circle cx="130" cy="80" r="70" fill="url(#mountain_glow)" opacity="0.25" />
      <circle cx="40" cy="30" r="1.5" fill="#93c5fd" opacity="0.8" />
      <circle cx="85" cy="18" r="1.2" fill="#c4b5fd" opacity="0.9" />
      <circle cx="190" cy="25" r="1.5" fill="#67e8f9" opacity="0.8" />
      <circle cx="230" cy="45" r="1" fill="#93c5fd" opacity="0.7" />
      <circle cx="160" cy="15" r="1" fill="#fff" opacity="0.9" />

      {/* Mountain silhouettes */}
      <polygon points="10,150 90,65 170,150" fill="#111c38" />
      <polygon points="90,65 115,95 85,98" fill="#1e2d58" />
      
      {/* Main Summit Mountain */}
      <polygon points="70,150 170,35 250,150" fill="#172554" />
      <polygon points="170,35 200,80 155,75" fill="#2563eb" opacity="0.4" />
      <polygon points="170,35 185,55 160,52" fill="#93c5fd" opacity="0.7" />

      {/* Flag at Summit */}
      <line x1="170" y1="35" x2="170" y2="18" stroke="#f59e0b" strokeWidth="2.5" strokeLinecap="round" />
      <polygon points="170,18 190,24 170,30" fill="#f59e0b" />

      {/* Climber Figure */}
      <circle cx="148" cy="62" r="4" fill="#38bdf8" />
      <path d="M148,66 L154,78 M148,70 L142,75 M154,78 L158,90 M154,78 L149,88" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" />

      <defs>
        <radialGradient id="mountain_glow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(130 80) rotate(90) scale(70)">
          <stop stopColor="#3b82f6" />
          <stop offset="1" stopColor="#1e1b4b" stopOpacity="0" />
        </radialGradient>
      </defs>
    </svg>
    <div className="absolute top-2 right-1 text-right">
      <p className="text-[11px] font-semibold text-blue-200/90 leading-tight italic m-0">
        Small steps<br />every day<br />lead to big<br />results 🚀
      </p>
    </div>
  </div>
);

export const RobotMascotIllustration: React.FC<{ className?: string }> = ({ className = 'w-48 h-48' }) => (
  <div className={`relative flex items-center justify-center ${className}`}>
    <svg viewBox="0 0 200 180" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      {/* Glow behind robot */}
      <circle cx="100" cy="90" r="65" fill="#3b82f6" opacity="0.2" filter="blur(15px)" />
      
      {/* Robot Antenna */}
      <line x1="100" y1="42" x2="100" y2="28" stroke="#60a5fa" strokeWidth="3" strokeLinecap="round" />
      <circle cx="100" cy="25" r="5" fill="#38bdf8" />
      <circle cx="100" cy="25" r="2" fill="#fff" />

      {/* Head */}
      <rect x="68" y="42" width="64" height="48" rx="16" fill="#1e293b" stroke="#3b82f6" strokeWidth="2.5" />
      {/* Visor Screen */}
      <rect x="74" y="48" width="52" height="34" rx="10" fill="#090d16" stroke="#1d4ed8" strokeWidth="1.5" />
      
      {/* Glowing Eyes */}
      <circle cx="88" cy="64" r="5.5" fill="#06b6d4" />
      <circle cx="89" cy="63" r="2" fill="#fff" />
      <circle cx="112" cy="64" r="5.5" fill="#06b6d4" />
      <circle cx="113" cy="63" r="2" fill="#fff" />
      {/* Cute Smile */}
      <path d="M96 72 Q100 76 104 72" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" />

      {/* Body */}
      <rect x="76" y="94" width="48" height="42" rx="12" fill="#1e293b" stroke="#3b82f6" strokeWidth="2" />
      <circle cx="100" cy="112" r="7" fill="#2563eb" />
      <path d="M97 112 L103 112 M100 109 L100 115" stroke="#93c5fd" strokeWidth="1.5" strokeLinecap="round" />

      {/* Arms */}
      <path d="M74 102 C60 108 60 120 72 130" stroke="#60a5fa" strokeWidth="4" strokeLinecap="round" />
      <path d="M126 102 C140 108 140 120 128 130" stroke="#60a5fa" strokeWidth="4" strokeLinecap="round" />

      {/* Laptop */}
      <polygon points="62,148 138,148 144,154 56,154" fill="#334155" stroke="#475569" strokeWidth="1.5" />
      <rect x="70" y="124" width="60" height="26" rx="4" fill="#0f172a" stroke="#38bdf8" strokeWidth="2" />
      <circle cx="100" cy="136" r="3" fill="#38bdf8" opacity="0.8" />

      {/* Sparkles around */}
      <polygon points="45,40 47,46 53,48 47,50 45,56 43,50 37,48 43,46" fill="#facc15" />
      <polygon points="155,75 157,79 161,80 157,81 155,85 153,81 149,80 153,79" fill="#38bdf8" />
    </svg>
  </div>
);

export const StudentAvatarIllustration: React.FC<{ className?: string }> = ({ className = 'w-10 h-10' }) => (
  <div className={`relative rounded-xl bg-gradient-to-tr from-indigo-600 via-blue-600 to-cyan-500 p-0.5 shrink-0 ${className}`}>
    <div className="w-full h-full rounded-[10px] bg-[#0c1427] flex items-center justify-center overflow-hidden">
      <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        <circle cx="20" cy="15" r="7" fill="#fbcfe8" />
        <path d="M13 14 C13 9 27 9 27 14 C27 15 25 18 20 18 C15 18 13 15 13 14" fill="#312e81" />
        <circle cx="18" cy="15" r="1" fill="#1e1b4b" />
        <circle cx="22" cy="15" r="1" fill="#1e1b4b" />
        <path d="M19 18 Q20 20 21 18" stroke="#e11d48" strokeWidth="0.8" strokeLinecap="round" />
        {/* Headphones */}
        <path d="M11 16 A9 9 0 0 1 29 16" stroke="#38bdf8" strokeWidth="2" fill="none" />
        <rect x="10" y="14" width="3" height="6" rx="1.5" fill="#0284c7" />
        <rect x="27" y="14" width="3" height="6" rx="1.5" fill="#0284c7" />
        {/* Shirt */}
        <path d="M9 36 C9 26 31 26 31 36" fill="#3b82f6" />
        <polygon points="17,26 23,26 20,30" fill="#fbcfe8" />
      </svg>
    </div>
  </div>
);

export const SproutingPlantIllustration: React.FC<{ className?: string }> = ({ className = 'w-16 h-16' }) => (
  <div className={`flex items-center justify-center ${className}`}>
    <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      {/* Pot */}
      <polygon points="26,50 54,50 50,72 30,72" fill="#d97706" />
      <rect x="24" y="46" width="32" height="6" rx="2" fill="#b45309" />
      {/* Soil */}
      <ellipse cx="40" cy="50" rx="12" ry="3" fill="#78350f" />
      {/* Stem */}
      <path d="M40 50 C40 38 42 30 40 24" stroke="#22c55e" strokeWidth="3" strokeLinecap="round" />
      {/* Leaves */}
      <path d="M40 34 C30 30 26 22 36 22 C40 22 40 28 40 34" fill="#4ade80" />
      <path d="M40 28 C48 24 54 18 46 16 C40 16 40 22 40 28" fill="#22c55e" />
      {/* Sparkles */}
      <circle cx="28" cy="18" r="1.5" fill="#facc15" />
      <circle cx="54" cy="26" r="1.5" fill="#facc15" />
    </svg>
  </div>
);
