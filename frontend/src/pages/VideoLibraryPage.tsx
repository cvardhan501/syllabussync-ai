import React, { useState, useEffect } from 'react';
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
  HelpCircle
} from 'lucide-react';
import type { 
  SyllabusAnalysisResponse, 
  ResourceDiscoveryResponse, 
  TopicResourceMapping,
  AlternativeResourceItem 
} from '../types';
import { apiService, ApiErrorResponse } from '../services/api';

const YouTubeIcon: React.FC<{ className?: string }> = ({ className = 'w-4 h-4' }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

interface VideoLibraryPageProps {
  analyzedSyllabus: SyllabusAnalysisResponse | null;
  onNavigateToSyllabus: () => void;
  preferredLanguage?: string;
}

export const VideoLibraryPage: React.FC<VideoLibraryPageProps> = ({
  analyzedSyllabus,
  onNavigateToSyllabus,
  preferredLanguage = 'English',
}) => {
  const [discoveryData, setDiscoveryData] = useState<ResourceDiscoveryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());

  // Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModule, setSelectedModule] = useState('all');
  const [selectedLanguage, setSelectedLanguage] = useState('all');
  const [selectedChannel, setSelectedChannel] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');

  // Alternative Channel Modal State
  const [replaceTargetTopic, setReplaceTargetTopic] = useState<TopicResourceMapping | null>(null);
  const [alternatives, setAlternatives] = useState<AlternativeResourceItem[]>([]);
  const [isLoadingAlternatives, setIsLoadingAlternatives] = useState(false);
  const [isSubmittingReplacement, setIsSubmittingReplacement] = useState(false);
  const [replaceReason, setReplaceReason] = useState('');
  const [replaceError, setReplaceError] = useState<string | null>(null);

  // 3rd Channel Approval State
  const [isApprovingThird, setIsApprovingThird] = useState(false);

  // Auto-fetch existing resources on syllabus change
  useEffect(() => {
    let isMounted = true;
    if (!analyzedSyllabus?.syllabus_id) {
      setDiscoveryData(null);
      return;
    }

    const loadExistingResources = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await apiService.getResources(analyzedSyllabus.syllabus_id);
        if (isMounted) {
          setDiscoveryData(data);
        }
      } catch (err: any) {
        // If not found yet, leave data as null so user can trigger discovery
        if (isMounted && err instanceof ApiErrorResponse && err.status !== 404) {
          setError(err.message);
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
  }, [analyzedSyllabus?.syllabus_id]);

  // Trigger Resource Discovery
  const handleDiscoverResources = async (forceRefresh: boolean = false) => {
    if (!analyzedSyllabus?.syllabus_id) return;
    setIsDiscovering(true);
    setError(null);
    try {
      const data = await apiService.discoverResources(analyzedSyllabus.syllabus_id, {
        preferred_language: preferredLanguage,
        force_refresh: forceRefresh,
      });
      setDiscoveryData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to match educational videos.');
    } finally {
      setIsDiscovering(false);
    }
  };

  // Open Replace Modal
  const handleOpenReplaceModal = async (topic: TopicResourceMapping) => {
    if (!analyzedSyllabus?.syllabus_id) return;
    setReplaceTargetTopic(topic);
    setAlternatives([]);
    setReplaceReason('');
    setReplaceError(null);
    setIsLoadingAlternatives(true);

    try {
      const data = await apiService.getTopicAlternatives(
        analyzedSyllabus.syllabus_id,
        topic.topic_id,
        preferredLanguage
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
    if (!analyzedSyllabus?.syllabus_id || !replaceTargetTopic) return;
    const currentChannel = replaceTargetTopic.resource?.channel_title || 'Current Channel';

    setIsSubmittingReplacement(true);
    setReplaceError(null);
    try {
      const updatedMapping = await apiService.replaceTopicChannel(
        analyzedSyllabus.syllabus_id,
        replaceTargetTopic.topic_id,
        {
          rejected_channel: currentChannel,
          selected_video_id: selectedVideoId,
          reason: replaceReason || undefined,
        }
      );

      // Update local state without refetching everything
      setDiscoveryData((prev) => {
        if (!prev) return prev;
        const updatedList = prev.topic_resources.map((tr) =>
          tr.topic_id === updatedMapping.topic_id ? updatedMapping : tr
        );
        return {
          ...prev,
          topic_resources: updatedList,
        };
      });

      setReplaceTargetTopic(null);
    } catch (err: any) {
      setReplaceError(err.message || 'Failed to replace channel.');
    } finally {
      setIsSubmittingReplacement(false);
    }
  };

  // Approve 3rd Channel
  const handleApproveThirdChannel = async () => {
    if (!analyzedSyllabus?.syllabus_id) return;
    setIsApprovingThird(true);
    setError(null);
    try {
      const updated = await apiService.approveThirdChannel(analyzedSyllabus.syllabus_id);
      setDiscoveryData(updated);
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
  const allChannels = Array.from(
    new Set(
      (discoveryData?.topic_resources || [])
        .map((t) => t.resource?.channel_title)
        .filter(Boolean) as string[]
    )
  );

  const allModules = Array.from(
    new Set(
      (discoveryData?.topic_resources || []).map((t) => t.module_title)
    )
  );

  // Filtered List
  const filteredTopicResources = (discoveryData?.topic_resources || []).filter((tr) => {
    const titleMatch = 
      tr.topic_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (tr.resource?.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (tr.resource?.channel_title || '').toLowerCase().includes(searchQuery.toLowerCase());

    if (searchQuery && !titleMatch) return false;

    if (selectedModule !== 'all' && tr.module_title !== selectedModule) return false;

    if (selectedChannel !== 'all' && tr.resource?.channel_title !== selectedChannel) return false;

    if (selectedLanguage !== 'all' && tr.resource?.language?.toLowerCase() !== selectedLanguage.toLowerCase()) return false;

    if (selectedStatus !== 'all' && tr.match_status !== selectedStatus) return false;

    return true;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight m-0">
            Syllabus-Aligned Learning Resources
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5 m-0">
            Real YouTube educational videos, mapped directly to your confirmed syllabus topics.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-semibold">
            <YouTubeIcon className="w-4 h-4 text-rose-400" />
            <span>Official YouTube Data API v3</span>
          </div>

          {analyzedSyllabus && (
            <button
              onClick={() => handleDiscoverResources(true)}
              disabled={isDiscovering}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[#0b1429] hover:bg-[#132247] border border-[#1b2b52] text-xs font-semibold text-slate-200 hover:text-white transition cursor-pointer"
              title="Re-run matching query"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${isDiscovering ? 'animate-spin' : ''}`} />
              <span>{isDiscovering ? 'Searching...' : 'Refresh Resources'}</span>
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
      {!analyzedSyllabus && (
        <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-8 sm:p-12 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-600/15 border border-blue-500/30 text-blue-400 flex items-center justify-center mx-auto">
            <Layers className="w-7 h-7 text-blue-400" />
          </div>
          <div className="space-y-1.5 max-w-md mx-auto">
            <h3 className="text-base sm:text-lg font-bold text-white m-0">
              No Analyzed Syllabus Found
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed m-0">
              Upload and analyze your course syllabus first. SyllabusSync AI will map each verified topic to accredited educational videos.
            </p>
          </div>
          <button
            onClick={onNavigateToSyllabus}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/30 transition cursor-pointer"
          >
            Go to My Syllabus
          </button>
        </div>
      )}

      {/* Awaiting Discovery Action Banner */}
      {analyzedSyllabus && !discoveryData && !isLoading && !isDiscovering && (
        <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-rose-500/15 border border-rose-500/30 text-rose-400 flex items-center justify-center mx-auto">
            <YouTubeIcon className="w-7 h-7 text-rose-400" />
          </div>
          <div className="space-y-1.5 max-w-lg mx-auto">
            <h3 className="text-base sm:text-lg font-bold text-white m-0">
              Topics Verified ({analyzedSyllabus.total_topics_count} Topics Ready)
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed m-0">
              Your syllabus topics for '{analyzedSyllabus.course_name || 'Course'}' are verified.
              Run the discovery engine to discover genuine YouTube playlists using our 1-to-2 channel strategy.
            </p>
          </div>
          <button
            onClick={() => handleDiscoverResources(false)}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/30 transition cursor-pointer"
          >
            <Sparkles className="w-4 h-4 text-cyan-300" />
            <span>Discover YouTube Learning Resources</span>
          </button>
        </div>
      )}

      {/* Loading State */}
      {(isLoading || isDiscovering) && (
        <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-12 text-center space-y-3">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto" />
          <p className="text-sm font-bold text-white m-0">Discovering YouTube Learning Resources...</p>
          <p className="text-xs text-slate-400 m-0">
            Querying YouTube Data API v3, parsing durations, deduplicating, and auditing channel coverage.
          </p>
        </div>
      )}

      {/* Discovered Content Section */}
      {discoveryData && !isLoading && !isDiscovering && (
        <>
          {/* Section 1: Coverage Audit & Channel Selection Strategy Banner */}
          <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-5 sm:p-6 space-y-4 shadow-md">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#18284e] pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-blue-400">
                    Channel Strategy Audit
                  </span>
                  {discoveryData.is_fallback && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                      Dev Fallback Mode
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-300 m-0 leading-relaxed">
                  {discoveryData.strategy_explanation}
                </p>
              </div>

              {/* Selected Channels Badges */}
              <div className="flex flex-wrap items-center gap-2">
                {discoveryData.selected_channels.map((ch, idx) => (
                  <div
                    key={idx}
                    className={`px-3 py-1.5 rounded-xl border text-xs flex items-center gap-2 ${
                      ch.is_primary
                        ? 'bg-blue-600/20 border-blue-500/40 text-blue-300'
                        : 'bg-[#0f1b36] border-[#1e3262] text-slate-300'
                    }`}
                  >
                    <span className="font-semibold">{ch.channel_title}</span>
                    <span className="text-[10px] font-mono text-slate-400">
                      {ch.topics_covered} topics ({ch.percentage_of_course}%)
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Coverage Numbers Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-1">
              <div className="p-3 rounded-xl bg-[#070e20] border border-[#1b2b54]">
                <span className="text-[10px] text-slate-400 block">Total Topics</span>
                <span className="text-lg font-bold text-white">{discoveryData.coverage.total_topics}</span>
              </div>
              <div className="p-3 rounded-xl bg-[#070e20] border border-[#1b2b54]">
                <span className="text-[10px] text-emerald-400 block">Sufficiently Relevant</span>
                <span className="text-lg font-bold text-emerald-300">{discoveryData.coverage.topics_with_relevant}</span>
              </div>
              <div className="p-3 rounded-xl bg-[#070e20] border border-[#1b2b54]">
                <span className="text-[10px] text-amber-400 block">Needs Review</span>
                <span className="text-lg font-bold text-amber-300">{discoveryData.coverage.topics_needing_review}</span>
              </div>
              <div className="p-3 rounded-xl bg-[#070e20] border border-[#1b2b54]">
                <span className="text-[10px] text-rose-400 block">No Resource</span>
                <span className="text-lg font-bold text-rose-300">{discoveryData.coverage.topics_with_no_resource}</span>
              </div>
              <div className="p-3 rounded-xl bg-[#070e20] border border-[#1b2b54]">
                <span className="text-[10px] text-blue-400 block">Course Coverage</span>
                <span className="text-lg font-bold text-blue-300">{discoveryData.coverage.coverage_percentage}%</span>
              </div>
            </div>

            {/* Third Channel Approval Banner */}
            {discoveryData.requires_third_channel_approval && (
              <div className="mt-3 p-4 rounded-xl bg-amber-950/30 border border-amber-600/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-start gap-2.5">
                  <HelpCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-xs font-bold text-amber-200 m-0">Student Consent Required for 3rd Channel</h4>
                    <p className="text-[11px] text-amber-300/80 m-0 mt-0.5 leading-relaxed">
                      Two channels are insufficient to cover all topics adequately. Would you like to introduce a 3rd channel ({discoveryData.third_channel_candidates.join(', ')})?
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

          {/* Section 2: Filter Bar */}
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
            </div>
          </div>

          {/* Section 3: Topic Resources Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredTopicResources.map((tr) => {
              const res = tr.resource;
              const isBookmarked = res ? bookmarkedIds.has(res.id) : false;

              return (
                <div
                  key={tr.topic_id}
                  className="rounded-2xl bg-[#0b1429] border border-[#18284e] overflow-hidden flex flex-col justify-between hover:border-blue-500/50 transition group shadow-md"
                >
                  <div>
                    {/* Top Thumbnail or No-Video Banner */}
                    {res ? (
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
                    ) : (
                      <div className="aspect-video w-full bg-[#070e20] border-b border-[#18284e] flex flex-col items-center justify-center p-4 text-center">
                        <AlertTriangle className="w-8 h-8 text-rose-400 mb-1" />
                        <p className="text-xs font-bold text-slate-300 m-0">No Video Found</p>
                        <p className="text-[10px] text-slate-500 mt-0.5 m-0">Candidate search pending or creator unavailable</p>
                      </div>
                    )}

                    {/* Card Content */}
                    <div className="p-4 space-y-3">
                      {/* Topic & Module Badges */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-400 truncate max-w-[200px]">
                            {tr.module_title}
                          </span>
                          {/* Match Status Badge */}
                          <span
                            className={`px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wider ${
                              tr.match_status === 'relevant'
                                ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/50'
                                : tr.match_status === 'needs_review'
                                ? 'bg-amber-950/40 text-amber-300 border border-amber-800/50'
                                : 'bg-rose-950/40 text-rose-300 border border-rose-800/50'
                            }`}
                          >
                            {tr.match_status === 'relevant' ? 'Verified Match' : tr.match_status === 'needs_review' ? 'Needs Review' : 'Missing Resource'}
                          </span>
                        </div>

                        <h4 className="text-sm font-bold text-white leading-snug m-0 group-hover:text-blue-300 transition-colors">
                          {tr.topic_title}
                        </h4>
                      </div>

                      {/* Video Title & Channel */}
                      {res && (
                        <div className="space-y-1.5 pt-1 border-t border-[#152342]">
                          <p className="text-xs font-medium text-slate-200 line-clamp-2 leading-relaxed m-0">
                            {res.title}
                          </p>
                          <div className="flex items-center justify-between text-xs text-slate-400">
                            <span className="font-semibold text-slate-300 flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 inline" />
                              {res.channel_title}
                            </span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded-sm bg-[#111e3b] text-blue-300">
                              {res.language || 'English'}
                            </span>
                          </div>
                        </div>
                      )}

                      {/* Explanation Note */}
                      <p className="text-[11px] text-slate-400 m-0 leading-relaxed bg-[#070e20] p-2 rounded-lg border border-[#152342]">
                        <span className="text-slate-500 font-semibold block text-[10px] uppercase">Relevance Audit:</span>
                        {res?.relevance_explanation || tr.relevance_notes || 'Topic mapped from syllabus outline.'}
                      </p>

                      {/* Rejected Channels Notice if any */}
                      {tr.rejected_channels && tr.rejected_channels.length > 0 && (
                        <p className="text-[10px] text-slate-500 m-0">
                          Excluded channels: {tr.rejected_channels.join(', ')}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Bottom Action Controls */}
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

                      <button
                        onClick={() => handleOpenReplaceModal(tr)}
                        className="py-2 px-3 rounded-xl bg-[#0f1b36] hover:bg-[#182c56] border border-[#1b2f5c] text-slate-300 hover:text-white text-xs font-medium transition cursor-pointer flex items-center gap-1.5"
                        title="Dislike creator or request alternative channel"
                      >
                        <ThumbsDown className="w-3.5 h-3.5 text-amber-400" />
                        <span>Replace Channel</span>
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

          {filteredTopicResources.length === 0 && (
            <div className="p-8 text-center rounded-2xl bg-[#0b1429] border border-[#18284e]">
              <p className="text-sm font-semibold text-slate-300 m-0">No resources matched your filter criteria.</p>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedModule('all');
                  setSelectedChannel('all');
                  setSelectedLanguage('all');
                  setSelectedStatus('all');
                }}
                className="mt-3 px-4 py-1.5 rounded-xl bg-blue-600 text-white text-xs font-semibold"
              >
                Reset Filters
              </button>
            </div>
          )}
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
                  Request Alternative Channel
                </h3>
              </div>
              <p className="text-xs text-slate-400 mt-1 m-0">
                Replace creator for: <span className="text-white font-semibold">{replaceTargetTopic.topic_title}</span>
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
                Reason for changing creator (Optional)
              </label>
              <input
                type="text"
                value={replaceReason}
                onChange={(e) => setReplaceReason(e.target.value)}
                placeholder="e.g., Too fast, prefer a different teaching style, audio quality..."
                className="w-full px-3.5 py-2 rounded-xl bg-[#070e20] border border-[#1b2b52] text-xs text-white placeholder-slate-500 focus:outline-hidden focus:border-blue-500"
              />
            </div>

            {/* Alternatives List */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {isLoadingAlternatives ? (
                <div className="py-8 text-center space-y-2">
                  <Loader2 className="w-6 h-6 text-blue-400 animate-spin mx-auto" />
                  <p className="text-xs text-slate-400">Searching real alternative creators on YouTube...</p>
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
