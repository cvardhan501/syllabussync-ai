import React, { useState } from 'react';
import { 
  Search, 
  Bookmark, 
  BookmarkCheck, 
  ExternalLink, 
  Sparkles, 
  CheckCircle2, 
  Eye
} from 'lucide-react';
import type { SyllabusAnalysisResponse, VideoResourceItem } from '../types';

const YouTubeIcon: React.FC<{ className?: string }> = ({ className = 'w-4 h-4' }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

interface VideoLibraryPageProps {
  analyzedSyllabus: SyllabusAnalysisResponse | null;
  onNavigateToSyllabus: () => void;
}

// Sample preview resources matching the reference screen cards for layout preview
const REFERENCE_SAMPLE_VIDEOS: VideoResourceItem[] = [
  {
    id: 'vid-1',
    title: 'C Programming Full Course for Beginners - [in Hindi]',
    channelTitle: 'CodeWithHarry',
    thumbnailUrl: 'https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=600&auto=format&fit=crop&q=80',
    durationFormatted: '3:45:12',
    durationSeconds: 13512,
    language: 'Hindi',
    difficulty: 'easy',
    matchedTopicTitle: 'Basics of C Programming',
    matchedModuleTitle: 'Module 1: Introduction to Programming',
    videoUrl: 'https://youtube.com',
  },
  {
    id: 'vid-2',
    title: 'C Programming Tutorial for Beginners',
    channelTitle: 'freeCodeCamp',
    thumbnailUrl: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=600&auto=format&fit=crop&q=80',
    durationFormatted: '5:12:34',
    durationSeconds: 18754,
    language: 'English',
    difficulty: 'medium',
    matchedTopicTitle: 'Functions, Control Structures',
    matchedModuleTitle: 'Module 1: Introduction to Programming',
    videoUrl: 'https://youtube.com',
  },
  {
    id: 'vid-3',
    title: 'Data Structures and Algorithms Full Course',
    channelTitle: 'Take U Forward',
    thumbnailUrl: 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=600&auto=format&fit=crop&q=80',
    durationFormatted: '8:39:15',
    durationSeconds: 31155,
    language: 'English',
    difficulty: 'hard',
    matchedTopicTitle: 'Data Structures, Algorithms',
    matchedModuleTitle: 'Module 2: Data Structures',
    videoUrl: 'https://youtube.com',
  },
];

export const VideoLibraryPage: React.FC<VideoLibraryPageProps> = ({
  analyzedSyllabus,
  onNavigateToSyllabus,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModule, setSelectedModule] = useState('all');
  const [selectedLanguage, setSelectedLanguage] = useState('all');
  const [selectedChannel, setSelectedChannel] = useState('all');
  const [showPreviewCards, setShowPreviewCards] = useState(false);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());

  const toggleBookmark = (id: string) => {
    setBookmarkedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filteredVideos = REFERENCE_SAMPLE_VIDEOS.filter((v) => {
    if (searchQuery && !v.title.toLowerCase().includes(searchQuery.toLowerCase()) && !v.matchedTopicTitle.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (selectedLanguage !== 'all' && v.language.toLowerCase() !== selectedLanguage.toLowerCase()) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header (Matches Reference Screen 5) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight m-0">
            Syllabus-Aligned Learning Resources
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5 m-0">
            Real YouTube videos, matched to your syllabus topics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-semibold">
            <YouTubeIcon className="w-4 h-4 text-rose-400" />
            <span>Powered by YouTube</span>
          </div>
        </div>
      </div>

      {/* Filter Bar (Matches Reference Screen 5) */}
      <div className="p-4 rounded-2xl bg-[#0b1429] border border-[#18284e] space-y-3 shadow-md">
        <div className="flex flex-col md:flex-row items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search topics, channels or keywords..."
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-[#070e20] border border-[#1b2b52] text-xs text-white placeholder-slate-500 focus:outline-hidden focus:border-blue-500"
            />
          </div>

          {/* Filter Dropdowns */}
          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            <select
              value={selectedModule}
              onChange={(e) => setSelectedModule(e.target.value)}
              className="text-xs bg-[#070e20] border border-[#1b2b52] text-slate-300 px-3 py-2 rounded-xl focus:outline-hidden focus:border-blue-500 cursor-pointer"
            >
              <option value="all">All Modules</option>
              {analyzedSyllabus?.modules.map((m) => (
                <option key={m.id} value={m.id}>{m.title}</option>
              ))}
            </select>

            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="text-xs bg-[#070e20] border border-[#1b2b52] text-slate-300 px-3 py-2 rounded-xl focus:outline-hidden focus:border-blue-500 cursor-pointer"
            >
              <option value="all">All Languages</option>
              <option value="english">English</option>
              <option value="hindi">Hindi</option>
            </select>

            <select
              value={selectedChannel}
              onChange={(e) => setSelectedChannel(e.target.value)}
              className="text-xs bg-[#070e20] border border-[#1b2b52] text-slate-300 px-3 py-2 rounded-xl focus:outline-hidden focus:border-blue-500 cursor-pointer"
            >
              <option value="all">All Channels</option>
              <option value="codewithharry">CodeWithHarry</option>
              <option value="freecodecamp">freeCodeCamp</option>
              <option value="takeuforward">Take U Forward</option>
            </select>

            <select
              className="text-xs bg-[#070e20] border border-[#1b2b52] text-slate-300 px-3 py-2 rounded-xl focus:outline-hidden focus:border-blue-500 cursor-pointer"
            >
              <option value="all">Duration</option>
              <option value="short">&lt; 30 mins</option>
              <option value="medium">30–90 mins</option>
              <option value="long">&gt; 90 mins</option>
            </select>

            <select
              className="text-xs bg-[#070e20] border border-[#1b2b52] text-slate-300 px-3 py-2 rounded-xl focus:outline-hidden focus:border-blue-500 cursor-pointer"
            >
              <option value="all">Status</option>
              <option value="unwatched">Unwatched</option>
              <option value="bookmarked">Bookmarked</option>
            </select>
          </div>
        </div>
      </div>

      {/* Honest Empty State / Phase 3 Bridge Banner */}
      <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-6 sm:p-8 space-y-4 text-center">
        <div className="w-14 h-14 rounded-2xl bg-blue-600/15 border border-blue-500/30 text-blue-400 flex items-center justify-center mx-auto">
          <YouTubeIcon className="w-7 h-7 text-rose-500" />
        </div>

        <div className="space-y-1.5 max-w-lg mx-auto">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-950/60 text-blue-300 border border-blue-800/60 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <span>Phase 3: YouTube Discovery Engine</span>
          </div>

          <h3 className="text-base sm:text-lg font-bold text-white m-0">
            {analyzedSyllabus
              ? `Topics Verified (${analyzedSyllabus.total_topics_count} Topics Ready)`
              : 'Syllabus Required for Video Matching'}
          </h3>

          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed m-0">
            {analyzedSyllabus
              ? `Your topics for '${analyzedSyllabus.course_name || 'Course'}' are extracted. Real YouTube lectures will be populated here via YouTube Data API v3 in Phase 3 with strict channel consistency.`
              : 'Upload and analyze your course syllabus first. SyllabusSync AI will map each topic to verified educational video playlists.'}
          </p>
        </div>

        <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
          {!analyzedSyllabus ? (
            <button
              onClick={onNavigateToSyllabus}
              className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/30 transition cursor-pointer"
            >
              Upload & Analyze Syllabus First
            </button>
          ) : (
            <button
              onClick={() => setShowPreviewCards(!showPreviewCards)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#111e3b] hover:bg-[#182a52] text-blue-300 text-xs font-semibold border border-blue-500/40 transition cursor-pointer"
            >
              <Eye className="w-4 h-4" />
              <span>{showPreviewCards ? 'Hide Design Preview' : 'Preview Target Card Layout'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Target Video Cards Grid (Matches Reference Screen 5 Exactly) */}
      {showPreviewCards && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Reference Layout Preview (Target Video Cards)
            </span>
            <span className="text-[11px] text-blue-400 bg-blue-950/50 px-2.5 py-0.5 rounded-full border border-blue-800/40">
              Visual UI Preview Mode
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {filteredVideos.map((video) => {
              const isBookmarked = bookmarkedIds.has(video.id);

              return (
                <div
                  key={video.id}
                  className="rounded-2xl bg-[#0b1429] border border-[#18284e] overflow-hidden flex flex-col justify-between hover:border-blue-500/50 transition group shadow-md"
                >
                  <div>
                    {/* Thumbnail with Duration Badge */}
                    <div className="relative aspect-video w-full overflow-hidden bg-slate-900">
                      <img
                        src={video.thumbnailUrl}
                        alt={video.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                      <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md bg-black/85 text-[11px] font-mono font-semibold text-white tracking-wide">
                        {video.durationFormatted}
                      </span>
                    </div>

                    {/* Card Content */}
                    <div className="p-4 space-y-3">
                      <h4 className="text-sm font-bold text-white line-clamp-2 leading-snug m-0 group-hover:text-blue-300 transition-colors">
                        {video.title}
                      </h4>

                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span className="font-semibold text-slate-300 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 inline" />
                          {video.channelTitle}
                        </span>
                      </div>

                      {/* Language & Difficulty Tags */}
                      <div className="flex items-center gap-1.5">
                        <span className="px-2 py-0.5 rounded-md bg-[#111e3b] text-blue-300 border border-[#1b2f5c] text-[10px] font-medium">
                          {video.language}
                        </span>
                        <span className="px-2 py-0.5 rounded-md bg-emerald-950/40 text-emerald-300 border border-emerald-800/50 text-[10px] font-medium capitalize">
                          {video.difficulty}
                        </span>
                      </div>

                      {/* Matched Topic Line */}
                      <p className="text-[11px] text-slate-400 m-0 truncate">
                        <span className="text-slate-500">Matches:</span> {video.matchedTopicTitle}
                      </p>
                    </div>
                  </div>

                  {/* Bottom Actions */}
                  <div className="p-4 pt-0 flex items-center gap-2">
                    <button
                      onClick={() => window.open(video.videoUrl, '_blank')}
                      className="flex-1 py-2 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition cursor-pointer shadow-sm text-center flex items-center justify-center gap-1.5"
                    >
                      <span>Watch on YouTube</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => toggleBookmark(video.id)}
                      className={`p-2 rounded-xl border transition cursor-pointer ${
                        isBookmarked
                          ? 'bg-blue-600/20 text-blue-400 border-blue-500/50'
                          : 'bg-[#0f1b36] hover:bg-[#152549] text-slate-400 border-[#1c2e58]'
                      }`}
                      title={isBookmarked ? 'Remove Bookmark' : 'Bookmark Video'}
                    >
                      {isBookmarked ? <BookmarkCheck className="w-4 h-4 text-blue-400" /> : <Bookmark className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
