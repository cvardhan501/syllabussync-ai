import React, { useState, useEffect, useMemo } from 'react';
import { 
  Search, 
  Bookmark, 
  BookmarkCheck, 
  ExternalLink, 
  Sparkles, 
  CheckCircle2, 
  AlertTriangle,
  RotateCcw,
  Loader2,
  RefreshCw,
  ThumbsDown,
  Layers,
  Check,
  X,
  HelpCircle,
  GraduationCap,
  ArrowLeft,
  Languages,
  Sliders,
  Compass
} from 'lucide-react';
import type { 
  SyllabusAnalysisResponse, 
  ResourceDiscoveryResponse, 
  TopicResourceMapping, 
  AlternativeResourceItem,
  Course
} from '../types';
import { apiService, ApiErrorResponse } from '../services/api';
import { ChannelDiscoveryWorkflow } from '../components/ChannelDiscoveryWorkflow';

const YouTubeIcon: React.FC<{ className?: string }> = ({ className = 'w-4 h-4' }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

const SUPPORTED_LANGUAGES = [
  'English',
  'Hindi',
  'Spanish',
  'French',
  'German',
  'Tamil',
  'Telugu',
  'Kannada',
  'Bengali',
  'Marathi',
];

export const isValidVideoId = (id?: string): boolean => {
  if (!id) return false;
  if (id === 'test' || id.length !== 11) return false;
  return /^[a-zA-Z0-9_-]{11}$/.test(id);
};

interface VideoLibraryPageProps {
  analyzedSyllabus: SyllabusAnalysisResponse | null;
  onNavigateToSyllabus: () => void;
  preferredLanguage?: string;
  onDiscoveryUpdated?: (data: ResourceDiscoveryResponse) => void;
  courses?: Course[];
  activeCourse?: Course | null;
  onSelectCourse?: (course: Course | null) => void;
}

export const VideoLibraryPage: React.FC<VideoLibraryPageProps> = ({
  analyzedSyllabus,
  onNavigateToSyllabus,
  preferredLanguage: initialLanguage = 'English',
  onDiscoveryUpdated,
  courses = [],
  activeCourse,
  onSelectCourse,
}) => {
  // Course-based view mode: 'course' if focused on an active course/syllabus, 'selection' if browsing all courses
  const [viewMode, setViewMode] = useState<'course' | 'selection'>(() => {
    return activeCourse || analyzedSyllabus ? 'course' : 'selection';
  });

  const [selectedLanguage, setSelectedLanguage] = useState<string>(
    activeCourse?.language || initialLanguage || 'English'
  );

  const [currentSyllabusId, setCurrentSyllabusId] = useState<string | null>(
    activeCourse?.syllabus_id || analyzedSyllabus?.syllabus_id || null
  );

  const [currentCourseName, setCurrentCourseName] = useState<string>(
    activeCourse?.course_name || analyzedSyllabus?.course_name || 'Course'
  );

  const [currentCourseCode, setCurrentCourseCode] = useState<string | undefined>(
    activeCourse?.course_code || analyzedSyllabus?.course_code
  );

  const [discoveryData, setDiscoveryData] = useState<ResourceDiscoveryResponse | null>(null);
  const [showWorkflow, setShowWorkflow] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());

  // Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModule, setSelectedModule] = useState('all');
  const [selectedChannel, setSelectedChannel] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedProvenance, setSelectedProvenance] = useState('all');

  // Alternative Channel Modal State
  const [replaceTargetTopic, setReplaceTargetTopic] = useState<TopicResourceMapping | null>(null);
  const [alternatives, setAlternatives] = useState<AlternativeResourceItem[]>([]);
  const [isLoadingAlternatives, setIsLoadingAlternatives] = useState(false);
  const [isSubmittingReplacement, setIsSubmittingReplacement] = useState(false);
  const [replaceReason, setReplaceReason] = useState('');
  const [replaceError, setReplaceError] = useState<string | null>(null);

  // 3rd Channel Approval State
  const [isApprovingThird, setIsApprovingThird] = useState(false);

  // Sync state when activeCourse or analyzedSyllabus changes
  useEffect(() => {
    if (activeCourse) {
      setCurrentSyllabusId(activeCourse.syllabus_id || null);
      setCurrentCourseName(activeCourse.course_name);
      setCurrentCourseCode(activeCourse.course_code);
      if (activeCourse.language) setSelectedLanguage(activeCourse.language);
      setViewMode('course');
    } else if (analyzedSyllabus) {
      setCurrentSyllabusId(analyzedSyllabus.syllabus_id);
      setCurrentCourseName(analyzedSyllabus.course_name || 'Course');
      setCurrentCourseCode(analyzedSyllabus.course_code);
      setViewMode('course');
    } else if (courses.length > 0) {
      setViewMode('selection');
    }
  }, [activeCourse, analyzedSyllabus, courses.length]);

  // Load existing resources whenever syllabus ID changes
  useEffect(() => {
    let isMounted = true;
    if (!currentSyllabusId) {
      setDiscoveryData(null);
      return;
    }

    const loadExistingResources = async () => {
      const cacheKey = `video_discovery_${currentSyllabusId}_${selectedLanguage}`;
      const cached = sessionStorage.getItem(cacheKey);
      if (cached) {
        try {
          const parsed = JSON.parse(cached);
          if (isMounted) {
            setDiscoveryData(parsed);
            if (onDiscoveryUpdated) onDiscoveryUpdated(parsed);
          }
        } catch {
          // ignore cache parse error
        }
      } else {
        setIsLoading(true);
      }
      setError(null);
      try {
        const data = await apiService.getResources(currentSyllabusId);
        if (isMounted) {
          setDiscoveryData(data);
          sessionStorage.setItem(cacheKey, JSON.stringify(data));
          if (onDiscoveryUpdated) onDiscoveryUpdated(data);
        }
      } catch (err: any) {
        if (isMounted && err instanceof ApiErrorResponse && err.status !== 404) {
          setError(err.message);
        }
        if (isMounted && err instanceof ApiErrorResponse && err.status === 404) {
          setDiscoveryData(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadExistingResources();
    return () => {
      isMounted = false;
    };
  }, [currentSyllabusId, selectedLanguage]);

  // Trigger Resource Discovery (with preferred language)
  const handleDiscoverResources = async (forceRefresh: boolean = false) => {
    if (!currentSyllabusId) return;
    setIsDiscovering(true);
    setError(null);
    try {
      const data = await apiService.discoverResources(currentSyllabusId, {
        preferred_language: selectedLanguage,
        force_refresh: forceRefresh,
      });
      setDiscoveryData(data);
      const cacheKey = `video_discovery_${currentSyllabusId}_${selectedLanguage}`;
      sessionStorage.setItem(cacheKey, JSON.stringify(data));
      if (onDiscoveryUpdated) onDiscoveryUpdated(data);
    } catch (err: any) {
      setError(err.message || 'Failed to match educational videos.');
    } finally {
      setIsDiscovering(false);
    }
  };

  // Change language and refresh resources
  const handleLanguageChange = async (newLang: string) => {
    setSelectedLanguage(newLang);
    if (currentSyllabusId) {
      setIsDiscovering(true);
      setError(null);
      try {
        const data = await apiService.discoverResources(currentSyllabusId, {
          preferred_language: newLang,
          force_refresh: true,
        });
        setDiscoveryData(data);
        if (onDiscoveryUpdated) onDiscoveryUpdated(data);
      } catch (err: any) {
        setError(err.message || `Failed to fetch resources in ${newLang}.`);
      } finally {
        setIsDiscovering(false);
      }
    }
  };

  // Handle selecting a course card in the selection view
  const handlePickCourse = (course: Course) => {
    if (onSelectCourse) onSelectCourse(course);
    setCurrentSyllabusId(course.syllabus_id || null);
    setCurrentCourseName(course.course_name);
    setCurrentCourseCode(course.course_code);
    if (course.language) setSelectedLanguage(course.language);
    setViewMode('course');
  };

  // Open Replace Channel Modal
  const handleOpenReplaceModal = async (topic: TopicResourceMapping) => {
    if (!currentSyllabusId) return;
    setReplaceTargetTopic(topic);
    setAlternatives([]);
    setReplaceReason('');
    setReplaceError(null);
    setIsLoadingAlternatives(true);

    try {
      const data = await apiService.getTopicAlternatives(
        currentSyllabusId,
        topic.topic_id,
        selectedLanguage
      );
      setAlternatives(data.alternatives);
    } catch (err: any) {
      setReplaceError(err.message || 'Failed to search alternative creators.');
    } finally {
      setIsLoadingAlternatives(false);
    }
  };

  // Select Alternative Replacement
  const handleSelectReplacement = async (selectedVideoId: string) => {
    if (!currentSyllabusId || !replaceTargetTopic) return;
    const currentChannel = replaceTargetTopic.resource?.channel_title || 'Current Channel';

    setIsSubmittingReplacement(true);
    setReplaceError(null);
    try {
      await apiService.replaceTopicChannel(
        currentSyllabusId,
        replaceTargetTopic.topic_id,
        {
          rejected_channel: currentChannel,
          selected_video_id: selectedVideoId,
          reason: replaceReason || undefined,
        }
      );

      // Refresh resources from server to re-sync coverage and selected channels
      const refreshed = await apiService.getResources(currentSyllabusId);
      setDiscoveryData(refreshed);
      if (onDiscoveryUpdated) onDiscoveryUpdated(refreshed);

      setReplaceTargetTopic(null);
    } catch (err: any) {
      setReplaceError(err.message || 'Failed to replace channel.');
    } finally {
      setIsSubmittingReplacement(false);
    }
  };

  // Approve 3rd Channel
  const handleApproveThirdChannel = async () => {
    if (!currentSyllabusId) return;
    setIsApprovingThird(true);
    setError(null);
    try {
      const updated = await apiService.approveThirdChannel(currentSyllabusId);
      setDiscoveryData(updated);
      const cacheKey = `video_discovery_${currentSyllabusId}_${selectedLanguage}`;
      sessionStorage.setItem(cacheKey, JSON.stringify(updated));
      if (onDiscoveryUpdated) onDiscoveryUpdated(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to approve third channel.');
    } finally {
      setIsApprovingThird(false);
    }
  };

  const toggleBookmark = (id: string) => {
    setBookmarkedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Derive unique channels and modules for filters
  const allChannels = useMemo(() => {
    return Array.from(
      new Set(
        (discoveryData?.topic_resources || [])
          .map((t) => t.resource?.channel_title)
          .filter(Boolean) as string[]
      )
    );
  }, [discoveryData]);

  const allModules = useMemo(() => {
    return Array.from(
      new Set(
        (discoveryData?.topic_resources || []).map((t) => t.module_title)
      )
    );
  }, [discoveryData]);

  // Filtered List
  const filteredTopicResources = useMemo(() => {
    return (discoveryData?.topic_resources || []).filter((tr) => {
      const titleMatch = 
        tr.topic_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (tr.resource?.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (tr.resource?.channel_title || '').toLowerCase().includes(searchQuery.toLowerCase());

      if (searchQuery && !titleMatch) return false;
      if (selectedModule !== 'all' && tr.module_title !== selectedModule) return false;
      if (selectedChannel !== 'all' && tr.resource?.channel_title !== selectedChannel) return false;
      if (selectedStatus !== 'all' && tr.match_status !== selectedStatus) return false;

      if (selectedProvenance !== 'all') {
        const prov = tr.resource?.provenance || tr.provenance || (discoveryData?.is_fallback ? 'fallback' : 'live');
        if (prov !== selectedProvenance) return false;
      }

      return true;
    });
  }, [discoveryData, searchQuery, selectedModule, selectedChannel, selectedStatus, selectedProvenance]);

  // Group filtered topic resources by module (Part 5 requirement)
  const groupedByModule = useMemo(() => {
    const groups: { [moduleTitle: string]: TopicResourceMapping[] } = {};
    for (const tr of filteredTopicResources) {
      const mod = tr.module_title || 'Module 1 — Core Topics';
      if (!groups[mod]) {
        groups[mod] = [];
      }
      groups[mod].push(tr);
    }
    return groups;
  }, [filteredTopicResources]);

  // Helper to construct channel URL
  const getChannelUrl = (chTitle: string, chId?: string | null, customUrl?: string | null): string => {
    if (customUrl) return customUrl;
    if (chId) return `https://www.youtube.com/channel/${chId}`;
    return `https://www.youtube.com/results?search_query=${encodeURIComponent(chTitle)}`;
  };

  // ---------------------------------------------------------------------------
  // VIEW 1: Course Selection Overview (Part 8)
  // ---------------------------------------------------------------------------
  if (viewMode === 'selection' && courses.length > 0) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto pb-16">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-blue-600/20 text-blue-400 border border-blue-500/30 text-xs font-semibold uppercase tracking-wider">
                Video Libraries
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight mt-1 m-0">
              Select a Course Video Library
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5 m-0">
              Each enrolled course has its dedicated, module-by-module YouTube playlist matching verified syllabus topics.
            </p>
          </div>

          <button
            onClick={onNavigateToSyllabus}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md transition cursor-pointer self-start sm:self-auto"
          >
            <Sparkles className="w-4 h-4 text-cyan-300" />
            <span>Upload New Course Syllabus</span>
          </button>
        </div>

        {/* Course Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {courses.map((course) => {
            const hasSyllabus = Boolean(course.syllabus_id);
            const isCurrentlyActive = activeCourse?.id === course.id;

            return (
              <div
                key={course.id}
                onClick={() => handlePickCourse(course)}
                className={`p-5 rounded-2xl border transition cursor-pointer flex flex-col justify-between group ${
                  isCurrentlyActive
                    ? 'bg-[#122044] border-blue-500/70 shadow-xl shadow-blue-600/15 ring-1 ring-blue-500/40'
                    : 'bg-[#0b1429] border-[#18284e] hover:bg-[#0e1a38] hover:border-blue-500/40 shadow-md'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="p-2.5 rounded-xl bg-blue-600/15 border border-blue-500/30 text-blue-400">
                      <GraduationCap className="w-5 h-5" />
                    </div>
                    {course.course_code && (
                      <span className="px-2.5 py-1 rounded-lg bg-[#070e20] border border-[#1b2b52] font-mono text-xs font-bold text-blue-300 tracking-wider">
                        {course.course_code}
                      </span>
                    )}
                  </div>

                  <div>
                    <h3 className="text-base font-bold text-white group-hover:text-blue-300 transition-colors m-0 line-clamp-2">
                      {course.course_name}
                    </h3>
                    <p className="text-xs text-slate-400 mt-1 m-0">
                      {course.total_topics > 0 ? `${course.total_topics} topics organized into units` : 'Syllabus topics analyzed'}
                    </p>
                  </div>

                  {/* Course Details Pills */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <span className="px-2 py-0.5 rounded-md bg-[#070e20] text-[10px] text-slate-300 border border-[#172545]">
                      {course.language || 'English'}
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-[#070e20] text-[10px] text-slate-300 border border-[#172545]">
                      {course.lesson_style}
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-blue-950/40 text-[10px] text-blue-300 border border-blue-900/40">
                      {course.daily_study_availability}
                    </span>
                  </div>
                </div>

                <div className="pt-4 mt-4 border-t border-[#172545] flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-medium">
                    {hasSyllabus ? 'YouTube Playlist Ready' : 'Setup Required'}
                  </span>
                  <span className="font-semibold text-blue-400 group-hover:translate-x-1 transition-transform inline-flex items-center gap-1">
                    Open Library →
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // VIEW 2: Dedicated Course Video Library (Part 8 + Part 5 + Part 4)
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Navigation & Course Switcher Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            {courses.length > 1 && (
              <button
                onClick={() => setViewMode('selection')}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-[#0b1429] hover:bg-[#132247] border border-[#1b2b52] text-xs font-semibold text-slate-300 hover:text-white transition cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>All Courses</span>
              </button>
            )}

            {currentCourseCode && (
              <span className="px-2.5 py-0.5 rounded-lg bg-blue-600/20 text-blue-300 border border-blue-500/40 font-mono text-xs font-bold uppercase tracking-wider">
                {currentCourseCode}
              </span>
            )}

            {/* Course Switcher Dropdown (Part 8) */}
            {courses.length > 1 && (
              <div className="relative inline-block">
                <select
                  value={activeCourse?.id || ''}
                  onChange={(e) => {
                    const c = courses.find((item) => item.id === e.target.value);
                    if (c) handlePickCourse(c);
                  }}
                  className="text-xs bg-[#0b1429] border border-[#1b2b52] text-white px-3 py-1 rounded-xl focus:outline-hidden focus:border-blue-500 cursor-pointer font-medium"
                >
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>
                      Switch to: {c.course_code ? `${c.course_code} - ` : ''}{c.course_name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight mt-1 m-0">
            {currentCourseCode ? `${currentCourseCode} — ` : ''}{currentCourseName}
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 m-0">
            Intelligent 1-to-2 channel YouTube playlists grouped module-wise by verified syllabus topics.
          </p>
        </div>

        {/* Action Controls & Language Selector (Part 4) */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Preferred Language Selector (Part 4) */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#0b1429] border border-[#1b2b52] text-xs">
            <Languages className="w-4 h-4 text-blue-400 shrink-0" />
            <span className="text-slate-400 text-[11px] hidden sm:inline">Language:</span>
            <select
              value={selectedLanguage}
              onChange={(e) => handleLanguageChange(e.target.value)}
              disabled={isDiscovering}
              className="bg-transparent text-white font-semibold focus:outline-hidden cursor-pointer"
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option key={lang} value={lang} className="bg-[#0c162e] text-white">
                  {lang}
                </option>
              ))}
            </select>
          </div>

          {/* Official YouTube Data API badge */}
          <div className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-semibold">
            <YouTubeIcon className="w-4 h-4 text-rose-400" />
            <span>YouTube Data API v3</span>
          </div>

          {currentSyllabusId && (
            <button
              onClick={() => setShowWorkflow(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[#0b1429] hover:bg-[#132247] border border-[#1b2b52] text-xs font-semibold text-slate-200 hover:text-white transition cursor-pointer"
              title="Change educator selection strategy or preferred languages"
            >
              <Compass className="w-3.5 h-3.5 text-blue-400" />
              <span>Channel Strategy</span>
            </button>
          )}

          {currentSyllabusId && (
            <button
              onClick={() => handleDiscoverResources(true)}
              disabled={isDiscovering}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 border border-blue-500 text-xs font-semibold text-white transition cursor-pointer shadow-md shadow-blue-600/20"
              title="Refresh recommendations and recalculate channel coverage"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isDiscovering ? 'animate-spin' : ''}`} />
              <span>{isDiscovering ? 'Searching...' : 'Refresh'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-2xl bg-rose-950/30 border border-rose-800/50 p-4 text-xs text-rose-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => handleDiscoverResources(false)}
            className="px-3 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* No Syllabus State */}
      {!currentSyllabusId && (
        <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-8 sm:p-12 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-600/15 border border-blue-500/30 text-blue-400 flex items-center justify-center mx-auto">
            <Layers className="w-7 h-7 text-blue-400" />
          </div>
          <div className="space-y-1.5 max-w-md mx-auto">
            <h3 className="text-base sm:text-lg font-bold text-white m-0">
              No Analyzed Syllabus Attached
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed m-0">
              Upload and analyze your course syllabus first. SyllabusSync AI will map each verified topic to accredited educational videos.
            </p>
          </div>
          <button
            onClick={onNavigateToSyllabus}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/30 transition cursor-pointer"
          >
            Go to Syllabus Upload
          </button>
        </div>
      )}

      {/* Channel Discovery Workflow (Interactive Wizard) */}
      {currentSyllabusId && (!discoveryData || showWorkflow) && !isLoading && !isDiscovering && (
        <ChannelDiscoveryWorkflow
          syllabusId={currentSyllabusId}
          courseName={currentCourseName}
          courseCode={currentCourseCode}
          initialLanguages={[selectedLanguage]}
          initialStrategy={(discoveryData?.channel_strategy as any) || 'two_channels'}
          onCompleted={(confirmed) => {
            setDiscoveryData(confirmed);
            const cacheKey = `video_discovery_${currentSyllabusId}_${selectedLanguage}`;
            try {
              sessionStorage.setItem(cacheKey, JSON.stringify(confirmed));
            } catch {
              // Ignore session storage quota error
            }
            setShowWorkflow(false);
            if (onDiscoveryUpdated) onDiscoveryUpdated(confirmed);
          }}
          onCancel={discoveryData ? () => setShowWorkflow(false) : undefined}
        />
      )}

      {/* Loading State with Skeleton Loader Cards */}
      {(isLoading || isDiscovering) && (
        <div className="space-y-6">
          <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-6 text-center space-y-2">
            <div className="flex items-center justify-center gap-2">
              <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
              <p className="text-sm font-bold text-white m-0">Discovering YouTube Learning Resources ({selectedLanguage})...</p>
            </div>
            <p className="text-xs text-slate-400 m-0">
              Querying YouTube Data API v3, parsing teaching quality, balancing channel workload 50:50, and auditing coverage.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="rounded-2xl bg-[#0b1429] border border-[#18284e] overflow-hidden p-0 animate-pulse">
                <div className="aspect-video w-full bg-[#111e3b]" />
                <div className="p-4 space-y-3">
                  <div className="h-4 bg-[#111e3b] rounded-md w-3/4" />
                  <div className="h-3 bg-[#111e3b] rounded-md w-1/2" />
                  <div className="h-8 bg-[#111e3b] rounded-xl w-full mt-3" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Discovered Content Section */}
      {discoveryData && !isLoading && !isDiscovering && !showWorkflow && (
        <>
          {/* =========================================================================
              PART 5: YouTube Learning Dashboard — Channel Selection & Coverage Summary
             ========================================================================= */}
          <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-5 sm:p-6 space-y-5 shadow-lg">
            {/* Top row: Strategy badge & explanation */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#18284e] pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-bold uppercase tracking-wider text-blue-400">
                    Channel Strategy Audit
                  </span>
                  {discoveryData.channel_strategy && (
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-600/25 text-blue-300 border border-blue-500/40">
                      {discoveryData.channel_strategy === 'one_channel'
                        ? 'Option 1: One Channel'
                        : discoveryData.channel_strategy === 'two_channels'
                        ? 'Option 2: Two Channels (~50:50 Balanced)'
                        : discoveryData.channel_strategy === 'different_per_topic'
                        ? 'Option 3: Different per Topic'
                        : 'Option 4: Custom Selection'}
                    </span>
                  )}
                  {discoveryData.is_fallback && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                      Dev Fallback Mode
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-300 m-0 leading-relaxed max-w-3xl">
                  {discoveryData.strategy_explanation}
                </p>
              </div>

              {/* Action Buttons: Change Strategy & Re-balance */}
              <div className="flex items-center gap-2 self-start lg:self-center">
                <button
                  onClick={() => setShowWorkflow(true)}
                  className="px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-md shadow-blue-600/30 transition flex items-center gap-1.5 cursor-pointer"
                >
                  <Sliders className="w-3.5 h-3.5 text-cyan-300" />
                  <span>Change Strategy</span>
                </button>
                <button
                  onClick={() => handleDiscoverResources(true)}
                  className="px-3 py-1.5 rounded-xl bg-[#070e20] hover:bg-[#122044] border border-[#1b2b52] text-xs font-semibold text-slate-300 hover:text-white transition flex items-center gap-1.5 cursor-pointer"
                  title="Rediscover and refresh candidate videos"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {/* Selected Channel Summary Cards (Part 5) */}
            <div className="space-y-2">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Assigned YouTube Instructors & Course Coverage:
              </span>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
                {discoveryData.selected_channels.map((ch, idx) => {
                  const chUrl = getChannelUrl(ch.channel_title, ch.channel_id, ch.channel_url);

                  return (
                    <div
                      key={idx}
                      className={`p-4 rounded-xl border flex flex-col justify-between transition ${
                        ch.is_primary
                          ? 'bg-blue-950/25 border-blue-500/40 shadow-sm'
                          : 'bg-[#070e20] border-[#1b2b54]'
                      }`}
                    >
                      <div className="space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                            ch.is_primary
                              ? 'bg-blue-600/30 text-blue-300 border border-blue-500/40'
                              : 'bg-slate-800 text-slate-300 border border-slate-700'
                          }`}>
                            {idx === 0 ? 'Primary Creator' : idx === 1 ? 'Secondary Creator (~50%)' : 'Supplementary Creator'}
                          </span>
                          <span className="text-xs font-mono font-bold text-blue-400">
                            {ch.percentage_of_course}% Coverage
                          </span>
                        </div>

                        <div>
                          <a
                            href={chUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm font-bold text-white hover:text-blue-300 transition-colors inline-flex items-center gap-1.5"
                          >
                            <span>{ch.channel_title}</span>
                            <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-300" />
                          </a>
                          <p className="text-xs text-slate-400 mt-0.5 m-0">
                            Responsible for {ch.topics_covered} of {discoveryData.coverage.total_topics} syllabus topics
                          </p>
                        </div>
                      </div>

                      <div className="mt-3 pt-2.5 border-t border-[#162548] flex items-center justify-between text-[11px]">
                        <span className="text-slate-500 font-mono">
                          {ch.topics_covered} {ch.topics_covered === 1 ? 'topic' : 'topics'} assigned
                        </span>
                        <a
                          href={chUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:text-blue-300 font-medium inline-flex items-center gap-1"
                        >
                          Visit Channel
                        </a>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Coverage Numbers Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-1">
              <div className="p-3 rounded-xl bg-[#070e20] border border-[#1b2b54]">
                <span className="text-[10px] text-slate-400 block font-medium">Total Topics</span>
                <span className="text-lg font-bold text-white">{discoveryData.coverage.total_topics}</span>
              </div>
              <div className="p-3 rounded-xl bg-[#070e20] border border-[#1b2b54]">
                <span className="text-[10px] text-emerald-400 block font-medium">Verified Matches</span>
                <span className="text-lg font-bold text-emerald-300">
                  {discoveryData.coverage.topics_with_verified ?? discoveryData.coverage.topics_with_relevant}
                </span>
                <span className="text-[9px] text-emerald-400/80 block mt-0.5">
                  {discoveryData.coverage.verified_coverage_percentage ?? discoveryData.coverage.coverage_percentage}% verified
                </span>
              </div>
              <div className="p-3 rounded-xl bg-[#070e20] border border-[#1b2b54]">
                <span className="text-[10px] text-amber-400 block font-medium">Probable Matches</span>
                <span className="text-lg font-bold text-amber-300">
                  {discoveryData.coverage.topics_with_probable ?? discoveryData.coverage.topics_needing_review}
                </span>
                <span className="text-[9px] text-amber-400/80 block mt-0.5">Secondary review</span>
              </div>
              <div className="p-3 rounded-xl bg-[#070e20] border border-[#1b2b54]">
                <span className="text-[10px] text-rose-400 block font-medium">Uncovered Topics</span>
                <span className="text-lg font-bold text-rose-300">{discoveryData.coverage.topics_with_no_resource}</span>
                <span className="text-[9px] text-rose-400/80 block mt-0.5">Missing video</span>
              </div>
              <div className="p-3 rounded-xl bg-[#070e20] border border-[#1b2b54]">
                <span className="text-[10px] text-blue-400 block font-medium">Verified Coverage</span>
                <span className="text-lg font-bold text-blue-300">
                  {discoveryData.coverage.verified_coverage_percentage ?? discoveryData.coverage.coverage_percentage}%
                </span>
                <span className="text-[9px] text-slate-400 block mt-0.5">Honest audit</span>
              </div>
            </div>

            {/* Third Channel Approval Banner (Strategy 3) */}
            {discoveryData.requires_third_channel_approval && (
              <div className="mt-3 p-4 rounded-xl bg-amber-950/30 border border-amber-600/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-start gap-2.5">
                  <HelpCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-xs font-bold text-amber-200 m-0">Student Consent Required for 3rd Channel</h4>
                    <p className="text-[11px] text-amber-300/80 m-0 mt-0.5 leading-relaxed">
                      Two channels leave some syllabus topics uncovered. Would you like to introduce a 3rd channel ({discoveryData.third_channel_candidates.join(', ')}) with ~1:1:1 workload distribution?
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleApproveThirdChannel}
                  disabled={isApprovingThird}
                  className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shrink-0 cursor-pointer shadow transition"
                >
                  {isApprovingThird ? 'Approving...' : 'Approve 3rd Channel'}
                </button>
              </div>
            )}
          </div>

          {/* Filter Bar */}
          <div className="p-4 rounded-2xl bg-[#0b1429] border border-[#18284e] space-y-3 shadow-md">
            <div className="flex flex-col md:flex-row items-center gap-3">
              {/* Search */}
              <div className="relative flex-1 w-full">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search topics, channels or video titles..."
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-[#070e20] border border-[#1b2b52] text-xs text-white placeholder-slate-400 focus:outline-hidden focus:border-blue-500"
                />
              </div>

              {/* Module Filter */}
              <select
                value={selectedModule}
                onChange={(e) => setSelectedModule(e.target.value)}
                className="w-full md:w-auto text-xs bg-[#070e20] border border-[#1b2b52] text-slate-300 px-3 py-2 rounded-xl focus:outline-hidden focus:border-blue-500 cursor-pointer"
              >
                <option value="all">All Modules ({allModules.length})</option>
                {allModules.map((m, idx) => (
                  <option key={idx} value={m}>{m}</option>
                ))}
              </select>

              {/* Channel Filter */}
              <select
                value={selectedChannel}
                onChange={(e) => setSelectedChannel(e.target.value)}
                className="w-full md:w-auto text-xs bg-[#070e20] border border-[#1b2b52] text-slate-300 px-3 py-2 rounded-xl focus:outline-hidden focus:border-blue-500 cursor-pointer"
              >
                <option value="all">All Channels ({allChannels.length})</option>
                {allChannels.map((c, idx) => (
                  <option key={idx} value={c}>{c}</option>
                ))}
              </select>

              {/* Match Status Filter */}
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="w-full md:w-auto text-xs bg-[#070e20] border border-[#1b2b52] text-slate-300 px-3 py-2 rounded-xl focus:outline-hidden focus:border-blue-500 cursor-pointer"
              >
                <option value="all">All Statuses</option>
                <option value="relevant">Relevant Matches</option>
                <option value="needs_review">Needs Review</option>
                <option value="no_resource">No Video Found</option>
              </select>

              {/* Provenance Filter */}
              <select
                value={selectedProvenance}
                onChange={(e) => setSelectedProvenance(e.target.value)}
                className="w-full md:w-auto text-xs bg-[#070e20] border border-[#1b2b52] text-slate-300 px-3 py-2 rounded-xl focus:outline-hidden focus:border-blue-500 cursor-pointer"
              >
                <option value="all">All Sources</option>
                <option value="live">Live YouTube API</option>
                <option value="cache">Cached Result</option>
                <option value="fallback">Dev Fallback</option>
              </select>
            </div>
          </div>

          {/* =========================================================================
              PART 5 & PART 2: Module-Wise Grouped Topic Resource Cards
             ========================================================================= */}
          <div className="space-y-8">
            {Object.keys(groupedByModule).length === 0 ? (
              <div className="p-8 text-center rounded-2xl bg-[#0b1429] border border-[#18284e]">
                <p className="text-sm font-semibold text-slate-300 m-0">No resources matched your filter criteria.</p>
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setSelectedModule('all');
                    setSelectedChannel('all');
                    setSelectedStatus('all');
                  }}
                  className="mt-3 px-4 py-1.5 rounded-xl bg-blue-600 text-white text-xs font-semibold"
                >
                  Reset Filters
                </button>
              </div>
            ) : (
              Object.entries(groupedByModule).map(([moduleTitle, topicsInMod], mIdx) => {
                const coveredInMod = topicsInMod.filter((t) => t.match_status === 'relevant').length;

                return (
                  <div key={moduleTitle} className="space-y-4">
                    {/* Module Section Header */}
                    <div className="flex items-center justify-between border-b border-[#1b2b52] pb-2.5">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center font-bold text-xs">
                          {mIdx + 1}
                        </div>
                        <div>
                          <h3 className="text-base font-bold text-white m-0">
                            {moduleTitle}
                          </h3>
                          <span className="text-xs text-slate-400">
                            {topicsInMod.length} topics • {coveredInMod}/{topicsInMod.length} covered
                          </span>
                        </div>
                      </div>

                      <span className="text-xs font-mono px-2.5 py-0.5 rounded-md bg-[#070e20] text-blue-300 border border-[#172545]">
                        {Math.round((coveredInMod / Math.max(1, topicsInMod.length)) * 100)}% Unit Coverage
                      </span>
                    </div>

                    {/* Module Topics Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                      {topicsInMod.map((tr, tIdx) => {
                        const res = tr.resource;
                        const isBookmarked = res ? bookmarkedIds.has(res.id) : false;
                        const channelUrl = res ? getChannelUrl(res.channel_title, res.channel_id) : '#';

                        return (
                          <div
                            key={tr.topic_id}
                            className="rounded-2xl bg-[#0b1429] border border-[#18284e] overflow-hidden flex flex-col justify-between hover:border-blue-500/50 transition group shadow-md"
                          >
                            <div>
                              {/* Top Thumbnail, Unavailable Banner, or No-Video Banner */}
                              {res && isValidVideoId(res.video_id) ? (
                                <div className="relative aspect-video w-full overflow-hidden bg-slate-900">
                                  <img
                                    src={res.thumbnail_url}
                                    alt={res.title}
                                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                  />
                                  <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md bg-black/85 text-[11px] font-mono font-semibold text-white tracking-wide">
                                    {res.duration_formatted}
                                  </span>
                                  {res.view_count > 0 && (
                                    <span className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-black/75 text-[10px] text-slate-300 font-medium">
                                      {res.view_count.toLocaleString()} views
                                    </span>
                                  )}
                                </div>
                              ) : res && !isValidVideoId(res.video_id) ? (
                                <div className="aspect-video w-full bg-[#180a14] border-b border-rose-900/50 flex flex-col items-center justify-center p-4 text-center space-y-2">
                                  <div className="flex items-center gap-1.5 text-rose-400 font-bold text-xs">
                                    <AlertTriangle className="w-4 h-4 shrink-0" />
                                    <span>Video Unavailable on YouTube</span>
                                  </div>
                                  <p className="text-[11px] text-slate-400 m-0 max-w-xs">
                                    This video link is invalid or no longer active on YouTube.
                                  </p>
                                  <button
                                    onClick={() => handleOpenReplaceModal(tr)}
                                    className="px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md transition cursor-pointer flex items-center gap-1.5"
                                  >
                                    <RefreshCw className="w-3.5 h-3.5" />
                                    <span>Find Replacement</span>
                                  </button>
                                </div>
                              ) : (
                                <div className="aspect-video w-full bg-[#070e20] border-b border-[#18284e] flex flex-col items-center justify-center p-4 text-center">
                                  <AlertTriangle className="w-8 h-8 text-rose-400 mb-1" />
                                  <p className="text-xs font-bold text-slate-300 m-0">No Video Found</p>
                                  <p className="text-[10px] text-slate-500 mt-0.5 m-0">Candidate search pending or creator unavailable</p>
                                </div>
                              )}

                              {/* Card Content */}
                              <div className="p-4 space-y-3">
                                {/* Topic Number & Title (Part 2) */}
                                <div className="space-y-1">
                                  <div className="flex items-center justify-between text-[11px] gap-2">
                                    <div className="flex items-center gap-1.5">
                                      <span className="w-5 h-5 rounded-md bg-[#111e3b] text-blue-300 text-[10px] font-mono font-bold flex items-center justify-center shrink-0">
                                        {tIdx + 1}.
                                      </span>
                                      <span className="text-slate-400 truncate max-w-[140px]">
                                        Topic {tIdx + 1}
                                      </span>
                                    </div>

                                    {/* Match Status Badge & Badges */}
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      {tr.is_shared_video && (
                                        <span className="px-1.5 py-0.5 rounded-md text-[9px] font-bold bg-blue-950/60 text-blue-300 border border-blue-800/40 uppercase">
                                          Shared Course
                                        </span>
                                      )}
                                      <span
                                        className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                                          tr.match_status === 'relevant' || tr.match_status === 'verified'
                                            ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/50'
                                            : tr.match_status === 'needs_review' || tr.match_status === 'probable'
                                            ? 'bg-amber-950/40 text-amber-300 border border-amber-800/50'
                                            : tr.match_status === 'unverified'
                                            ? 'bg-slate-800 text-slate-300 border border-slate-700'
                                            : 'bg-rose-950/40 text-rose-300 border border-rose-800/50'
                                        }`}
                                      >
                                        {tr.match_status === 'relevant' || tr.match_status === 'verified'
                                          ? 'Verified Match'
                                          : tr.match_status === 'needs_review' || tr.match_status === 'probable'
                                          ? 'Probable Match'
                                          : tr.match_status === 'unverified'
                                          ? 'Unverified'
                                          : 'No Verified Video'}
                                      </span>
                                    </div>
                                  </div>

                                  <h4 className="text-sm font-bold text-white leading-snug m-0 group-hover:text-blue-300 transition-colors">
                                    {tr.topic_title}
                                  </h4>
                                </div>

                                {/* Video Title & Channel with direct link */}
                                {res && (
                                  <div className="space-y-1.5 pt-1 border-t border-[#152342]">
                                    <p className="text-xs font-medium text-slate-200 line-clamp-2 leading-relaxed m-0">
                                      {res.title}
                                    </p>
                                    <div className="flex items-center justify-between text-xs text-slate-400">
                                      <a
                                        href={channelUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="font-semibold text-slate-300 hover:text-blue-400 transition-colors flex items-center gap-1"
                                      >
                                        <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 inline shrink-0" />
                                        <span className="truncate max-w-[140px]">{res.channel_title}</span>
                                        <ExternalLink className="w-3 h-3 text-slate-500" />
                                      </a>
                                      <span className="text-[10px] px-1.5 py-0.5 rounded-sm bg-[#111e3b] text-blue-300">
                                        {res.language || selectedLanguage}
                                      </span>
                                    </div>
                                  </div>
                                )}

                                {/* Explanation Note */}
                                <p className="text-[11px] text-slate-400 m-0 leading-relaxed bg-[#070e20] p-2 rounded-lg border border-[#152342]">
                                  <span className="text-slate-500 font-semibold block text-[10px] uppercase">Relevance Audit:</span>
                                  {res?.relevance_explanation || tr.relevance_notes || 'Topic mapped from syllabus outline.'}
                                </p>

                                {/* Excluded Channels Notice if any */}
                                {tr.rejected_channels && tr.rejected_channels.length > 0 && (
                                  <p className="text-[10px] text-slate-500 m-0">
                                    Excluded channels: {tr.rejected_channels.join(', ')}
                                  </p>
                                )}
                              </div>
                            </div>

                            {/* Bottom Action Controls (Part 5) */}
                            <div className="p-4 pt-0 space-y-2">
                              <div className="flex items-center gap-2">
                                {res && (
                                  <button
                                    onClick={() => window.open(res.video_url, '_blank')}
                                    className="flex-1 py-2 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition cursor-pointer shadow-sm text-center flex items-center justify-center gap-1.5"
                                  >
                                    <span>Watch on YouTube</span>
                                    <ExternalLink className="w-3.5 h-3.5" />
                                  </button>
                                )}

                                {/* Find Another Channel / Replace Channel Button */}
                                <button
                                  onClick={() => handleOpenReplaceModal(tr)}
                                  className="py-2 px-3 rounded-xl bg-[#0f1b36] hover:bg-[#182c56] border border-[#1b2f5c] text-slate-300 hover:text-white text-xs font-medium transition cursor-pointer flex items-center gap-1.5"
                                  title="Find another channel or replace current instructor"
                                >
                                  <ThumbsDown className="w-3.5 h-3.5 text-amber-400" />
                                  <span>Replace</span>
                                </button>

                                {res && (
                                  <button
                                    onClick={() => toggleBookmark(res.id)}
                                    className={`p-2 rounded-xl border transition cursor-pointer ${
                                      isBookmarked
                                        ? 'bg-blue-600/20 text-blue-400 border-blue-500/50'
                                        : 'bg-[#0f1b36] hover:bg-[#152549] text-slate-400 border-[#1c2e58]'
                                    }`}
                                    title={isBookmarked ? 'Remove Bookmark' : 'Bookmark Video'}
                                  >
                                    {isBookmarked ? <BookmarkCheck className="w-4 h-4 text-blue-400" /> : <Bookmark className="w-4 h-4" />}
                                  </button>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}

      {/* Alternative Channel Replacement Modal */}
      {replaceTargetTopic && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="rounded-2xl bg-[#0c162e] border border-[#1e305e] max-w-2xl w-full p-6 space-y-5 shadow-2xl relative max-h-[90vh] flex flex-col">
            <button
              onClick={() => setReplaceTargetTopic(null)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#162548] cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <div>
              <div className="flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-blue-400" />
                <h3 className="text-base font-bold text-white m-0">
                  Find Another Channel for Topic
                </h3>
              </div>
              <p className="text-xs text-slate-400 mt-1 m-0">
                Replace instructor for: <span className="text-white font-semibold">{replaceTargetTopic.topic_title}</span>
              </p>
              {replaceTargetTopic.resource && (
                <p className="text-[11px] text-amber-400 mt-0.5 m-0">
                  Current channel '{replaceTargetTopic.resource.channel_title}' will be excluded from this topic.
                </p>
              )}
            </div>

            {replaceError && (
              <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300">
                {replaceError}
              </div>
            )}

            {/* Optional Reason Input */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Reason for changing channel (Optional)
              </label>
              <input
                type="text"
                value={replaceReason}
                onChange={(e) => setReplaceReason(e.target.value)}
                placeholder="e.g., Too fast, prefer a different teaching style, audio clarity..."
                className="w-full px-3.5 py-2 rounded-xl bg-[#070e20] border border-[#1b2b52] text-xs text-white placeholder-slate-500 focus:outline-hidden focus:border-blue-500"
              />
            </div>

            {/* Alternatives List */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {isLoadingAlternatives ? (
                <div className="py-8 text-center space-y-2">
                  <Loader2 className="w-6 h-6 text-blue-400 animate-spin mx-auto" />
                  <p className="text-xs text-slate-400">Searching real alternative creators on YouTube ({selectedLanguage})...</p>
                </div>
              ) : alternatives.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400">
                  No alternative educational channels found for this specific topic query.
                </div>
              ) : (
                alternatives.map((alt) => (
                  <div
                    key={alt.video.id}
                    className="p-3.5 rounded-xl bg-[#070e20] border border-[#1b2b52] hover:border-blue-500/50 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="flex items-start gap-3">
                      <img
                        src={alt.video.thumbnail_url}
                        alt={alt.video.title}
                        className="w-24 aspect-video rounded-lg object-cover shrink-0"
                      />
                      <div className="space-y-1">
                        <h5 className="text-xs font-bold text-white line-clamp-1 m-0">
                          {alt.video.title}
                        </h5>
                        <p className="text-[11px] text-blue-400 font-semibold m-0">
                          {alt.video.channel_title} • {alt.video.duration_formatted}
                        </p>
                        <p className="text-[10px] text-slate-400 m-0 leading-relaxed">
                          {alt.recommendation_reason}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() => handleSelectReplacement(alt.video.video_id)}
                      disabled={isSubmittingReplacement}
                      className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shrink-0 cursor-pointer shadow transition flex items-center justify-center gap-1.5"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>{isSubmittingReplacement ? 'Updating...' : 'Select This Channel'}</span>
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="flex items-center justify-end pt-2 border-t border-[#18284e]">
              <button
                onClick={() => setReplaceTargetTopic(null)}
                className="px-4 py-2 rounded-xl bg-[#0f1b36] hover:bg-[#182c56] text-slate-300 text-xs font-medium cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
