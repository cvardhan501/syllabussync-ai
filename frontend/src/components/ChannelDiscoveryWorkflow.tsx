import React, { useState } from 'react';
import {
  Languages,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Loader2,
  ChevronUp,
  ChevronDown,
  Compass,
  Sliders,
  ShieldCheck
} from 'lucide-react';
import type {
  ChannelDiscoveryResponse,
  PreviewStrategyResponse,
  ResourceDiscoveryResponse
} from '../types';
import { apiService } from '../services/api';

const PRIORITY_LANGUAGES = [
  'English',
  'Telugu',
  'Kannada',
  'Tamil',
  'Hindi',
  'Malayalam',
  'Bengali',
  'Marathi',
  'Gujarati',
  'Punjabi',
  'Urdu',
  'Odia',
  'Assamese',
  'Spanish',
  'French',
  'German',
  'Other',
];

interface ChannelDiscoveryWorkflowProps {
  syllabusId: string;
  courseName: string;
  courseCode?: string;
  initialLanguages?: string[];
  initialStrategy?: 'one_channel' | 'two_channels' | 'different_per_topic' | 'custom';
  onCompleted: (confirmedData: ResourceDiscoveryResponse) => void;
  onCancel?: () => void;
}

export const ChannelDiscoveryWorkflow: React.FC<ChannelDiscoveryWorkflowProps> = ({
  syllabusId,
  courseName,
  courseCode,
  initialLanguages = ['English'],
  initialStrategy = 'two_channels',
  onCompleted,
  onCancel,
}) => {
  // Wizard Steps: 1: Languages, 2: Channel Discovery & Strategy, 3: Distribution Preview & Confirm
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);

  // Step 1: Multilingual Priority Ordering
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(() => {
    const list = [...initialLanguages];
    if (!list.includes('English')) list.push('English');
    return list;
  });

  // Step 2: Channel Discovery State
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [discoveryResult, setDiscoveryResult] = useState<ChannelDiscoveryResponse | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<'one_channel' | 'two_channels' | 'different_per_topic' | 'custom'>(initialStrategy);
  const [selectedChannelNames, setSelectedChannelNames] = useState<string[]>([]);
  const [customAssignments, setCustomAssignments] = useState<Record<string, string>>({});

  // Step 3: Distribution Preview State
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [previewResult, setPreviewResult] = useState<PreviewStrategyResponse | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Reorder priority languages
  const moveLanguage = (index: number, direction: 'up' | 'down') => {
    const nextList = [...selectedLanguages];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= nextList.length) return;
    const temp = nextList[index];
    nextList[index] = nextList[targetIndex];
    nextList[targetIndex] = temp;
    setSelectedLanguages(nextList);
  };

  const toggleLanguage = (lang: string) => {
    if (selectedLanguages.includes(lang)) {
      if (selectedLanguages.length === 1) return; // keep at least 1
      setSelectedLanguages(selectedLanguages.filter((l) => l !== lang));
    } else {
      setSelectedLanguages([...selectedLanguages, lang]);
    }
  };

  // Run Discovery (Transition from Step 1 to Step 2)
  const handleProceedToDiscovery = async () => {
    setIsDiscovering(true);
    setErrorMessage(null);
    try {
      const res = await apiService.discoverChannels(syllabusId, selectedLanguages, false);
      setDiscoveryResult(res);

      // Pre-select top candidate channels based on discovery
      const topChannels = res.discovered_channels.slice(0, 3).map((c) => c.channel_title);
      setSelectedChannelNames(topChannels);
      setCurrentStep(2);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to discover educational channels for syllabus.');
    } finally {
      setIsDiscovering(false);
    }
  };

  // Run Preview (Transition from Step 2 to Step 3)
  const handleProceedToPreview = async () => {
    setIsPreviewing(true);
    setErrorMessage(null);
    try {
      const res = await apiService.previewStrategy(
        syllabusId,
        selectedStrategy,
        selectedLanguages,
        selectedChannelNames,
        selectedStrategy === 'custom' ? customAssignments : undefined
      );
      setPreviewResult(res);
      setCurrentStep(3);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to generate channel strategy preview.');
    } finally {
      setIsPreviewing(false);
    }
  };

  // Confirm Final Strategy and build persistent Video Library
  const handleConfirmStrategy = async () => {
    setIsConfirming(true);
    setErrorMessage(null);
    try {
      const res = await apiService.confirmStrategy(
        syllabusId,
        selectedStrategy,
        selectedLanguages,
        selectedChannelNames,
        selectedStrategy === 'custom' ? customAssignments : undefined
      );
      onCompleted(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to confirm channel strategy.');
    } finally {
      setIsConfirming(false);
    }
  };

  return (
    <div className="rounded-3xl bg-[#0b1429] border border-[#18284e] p-6 sm:p-8 space-y-8 shadow-2xl">
      {/* Workflow Header & Step Breadcrumbs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#18284e] pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-blue-600/20 text-blue-400 border border-blue-500/30 text-xs font-semibold uppercase tracking-wider">
              Channel Discovery & Selection
            </span>
            {courseCode && (
              <span className="px-2 py-0.5 rounded-md bg-[#070e20] text-blue-300 font-mono text-xs font-bold border border-[#1b2b52]">
                {courseCode}
              </span>
            )}
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-white mt-1 m-0">
            {courseName}
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5 m-0">
            Discover accredited YouTube educators, pick your channel strategy, and review topic distribution before generating your library.
          </p>
        </div>

        {/* Step Indicators */}
        <div className="flex items-center gap-2 text-xs font-semibold">
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border ${
            currentStep === 1 ? 'bg-blue-600 text-white border-blue-500' : 'bg-[#070e20] text-slate-400 border-[#18284e]'
          }`}>
            <span>1. Languages</span>
          </div>
          <span className="text-slate-600">→</span>
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border ${
            currentStep === 2 ? 'bg-blue-600 text-white border-blue-500' : 'bg-[#070e20] text-slate-400 border-[#18284e]'
          }`}>
            <span>2. Strategy</span>
          </div>
          <span className="text-slate-600">→</span>
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border ${
            currentStep === 3 ? 'bg-blue-600 text-white border-blue-500' : 'bg-[#070e20] text-slate-400 border-[#18284e]'
          }`}>
            <span>3. Distribution</span>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-rose-400 hover:text-white font-bold px-2 py-0.5"
          >
            ✕
          </button>
        </div>
      )}

      {/* =========================================================================
          STEP 1: Multilingual Priority Selector (14+ Languages)
         ========================================================================= */}
      {currentStep === 1 && (
        <div className="space-y-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Languages className="w-5 h-5 text-blue-400" />
              <h3 className="text-base sm:text-lg font-bold text-white m-0">
                Step 1: Select Preferred Learning Languages (Priority-Ordered)
              </h3>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 m-0">
              Select one or more languages for your course videos. Drag or use arrows to adjust priority order. SyllabusSync AI searches higher-priority languages first.
            </p>
          </div>

          {/* Active Priority Order List */}
          <div className="p-5 rounded-2xl bg-[#070e20] border border-[#18284e] space-y-3">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider m-0">
              Active Priority Order (First Match Wins):
            </h4>
            <div className="space-y-2">
              {selectedLanguages.map((lang, idx) => (
                <div
                  key={lang}
                  className="flex items-center justify-between p-3 rounded-xl bg-[#0b1429] border border-[#1b2b52] text-xs font-semibold text-white"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center font-mono text-xs">
                      #{idx + 1}
                    </span>
                    <span className="text-sm font-bold text-slate-100">{lang}</span>
                    {idx === 0 && (
                      <span className="px-2 py-0.5 rounded-md bg-blue-950/60 text-blue-300 border border-blue-800/40 text-[10px]">
                        Primary Language
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => moveLanguage(idx, 'up')}
                      disabled={idx === 0}
                      className="p-1 rounded-lg bg-[#070e20] hover:bg-[#122044] border border-[#1b2b52] text-slate-300 disabled:opacity-30 cursor-pointer"
                      title="Move up in priority"
                    >
                      <ChevronUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => moveLanguage(idx, 'down')}
                      disabled={idx === selectedLanguages.length - 1}
                      className="p-1 rounded-lg bg-[#070e20] hover:bg-[#122044] border border-[#1b2b52] text-slate-300 disabled:opacity-30 cursor-pointer"
                      title="Move down in priority"
                    >
                      <ChevronDown className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => toggleLanguage(lang)}
                      disabled={selectedLanguages.length === 1}
                      className="ml-2 text-rose-400 hover:text-rose-300 text-xs px-2 py-1 disabled:opacity-30 cursor-pointer"
                      title="Remove from search"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Add Additional Languages Pills */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider m-0">
              Add More Languages from Catalog:
            </h4>
            <div className="flex flex-wrap gap-2">
              {PRIORITY_LANGUAGES.map((lang) => {
                const isSelected = selectedLanguages.includes(lang);
                return (
                  <button
                    key={lang}
                    onClick={() => toggleLanguage(lang)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer border ${
                      isSelected
                        ? 'bg-blue-600/20 text-blue-300 border-blue-500/50 shadow-sm'
                        : 'bg-[#070e20] hover:bg-[#101d3d] text-slate-400 border-[#18284e]'
                    }`}
                  >
                    {isSelected ? `✓ ${lang}` : `+ ${lang}`}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Next Action */}
          <div className="flex items-center justify-between pt-4 border-t border-[#18284e]">
            {onCancel ? (
              <button
                onClick={onCancel}
                className="px-4 py-2 rounded-xl bg-transparent hover:bg-[#132247] text-slate-400 hover:text-white text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
            ) : <div />}

            <button
              onClick={handleProceedToDiscovery}
              disabled={isDiscovering || selectedLanguages.length === 0}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-lg shadow-blue-600/30 transition cursor-pointer disabled:opacity-50"
            >
              {isDiscovering ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Auditing YouTube Channels...</span>
                </>
              ) : (
                <>
                  <span>Audit Channels for Syllabus</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          STEP 2: Channel Discovery Audit & 4 Strategy Selection Cards
         ========================================================================= */}
      {currentStep === 2 && discoveryResult && (
        <div className="space-y-8">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Compass className="w-5 h-5 text-blue-400" />
              <h3 className="text-base sm:text-lg font-bold text-white m-0">
                Step 2: Choose Your Channel Strategy
              </h3>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 m-0">
              Discovered {discoveryResult.discovered_channels.length} qualifying YouTube channels across {discoveryResult.total_topics} topics. Select how you prefer to distribute educators across your syllabus.
            </p>
          </div>

          {/* Candidate Channels Audit Grid */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider m-0 flex items-center justify-between">
              <span>Audited Candidate Educators:</span>
              <span className="text-[11px] text-blue-400 font-normal">
                {discoveryResult.discovered_channels.length} accredited educators analyzed
              </span>
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {discoveryResult.discovered_channels.map((ch) => {
                const isSelected = selectedChannelNames.includes(ch.channel_title);
                return (
                  <div
                    key={ch.channel_title}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedChannelNames(selectedChannelNames.filter((n) => n !== ch.channel_title));
                      } else {
                        setSelectedChannelNames([...selectedChannelNames, ch.channel_title]);
                      }
                    }}
                    className={`p-4 rounded-2xl border transition cursor-pointer flex flex-col justify-between ${
                      isSelected
                        ? 'bg-[#122044] border-blue-500/70 shadow-lg shadow-blue-600/15 ring-1 ring-blue-500/40'
                        : 'bg-[#070e20] border-[#18284e] hover:bg-[#0e1a38]'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h5 className="text-sm font-bold text-white m-0 flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4 text-blue-400 inline shrink-0" />
                            <span>{ch.channel_title}</span>
                          </h5>
                          <span className="text-[11px] text-slate-400">
                            {ch.subscriber_count_approx || 'Accredited Educator'} • {ch.language}
                          </span>
                        </div>

                        <span className="px-2 py-0.5 rounded-md bg-blue-950/60 text-blue-300 font-mono text-[10px] font-bold border border-blue-800/40">
                          {Math.round(ch.fit_score * 100)}% Fit
                        </span>
                      </div>

                      <div className="space-y-1 text-xs">
                        <div className="flex items-center justify-between text-slate-300">
                          <span>Syllabus Coverage:</span>
                          <span className="font-bold text-white">
                            {ch.topics_covered.length} of {discoveryResult.total_topics} topics
                          </span>
                        </div>
                        <div className="w-full bg-[#040814] h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-blue-500 h-full rounded-full transition-all"
                            style={{
                              width: `${(ch.topics_covered.length / Math.max(1, discoveryResult.total_topics)) * 100}%`,
                            }}
                          />
                        </div>
                      </div>

                      {/* Example video if available */}
                      {ch.example_videos && ch.example_videos.length > 0 && (
                        <div className="pt-2 text-[11px] text-slate-400 border-t border-[#152342] line-clamp-1">
                          <span className="text-slate-500">Sample: </span>
                          <span className="text-slate-300">{ch.example_videos[0].title}</span>
                        </div>
                      )}
                    </div>

                    <div className="pt-3 mt-2 border-t border-[#152342] flex items-center justify-between text-xs">
                      <span className="text-slate-400 text-[11px]">
                        {ch.match_notes || 'High topic density'}
                      </span>
                      <span className={`font-semibold text-xs ${isSelected ? 'text-blue-400' : 'text-slate-500'}`}>
                        {isSelected ? '✓ Selected' : '+ Select'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* The 4 Student Channel Strategies Selection Cards */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider m-0">
              Select Distribution Strategy:
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Option 1: One Channel */}
              <div
                onClick={() => setSelectedStrategy('one_channel')}
                className={`p-5 rounded-2xl border transition cursor-pointer flex flex-col justify-between ${
                  selectedStrategy === 'one_channel'
                    ? 'bg-[#122044] border-blue-500 shadow-xl shadow-blue-600/20 ring-2 ring-blue-500/50'
                    : 'bg-[#070e20] border-[#18284e] hover:bg-[#0e1a38]'
                }`}
              >
                <div className="space-y-2">
                  <span className="px-2 py-0.5 rounded-md bg-blue-950/60 text-blue-300 text-[10px] font-bold border border-blue-800/40 uppercase">
                    Option 1
                  </span>
                  <h4 className="text-sm font-bold text-white m-0">
                    One Channel for All Topics
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed m-0">
                    Maps the entire syllabus to a single primary creator (e.g. Gate Smashers) for consistent teaching flow. Any uncovered topics are highlighted clearly.
                  </p>
                </div>
                <div className="pt-4 mt-2 border-t border-[#18284e] text-xs font-semibold text-blue-400">
                  {selectedStrategy === 'one_channel' ? '● Active Choice' : 'Choose Single Channel'}
                </div>
              </div>

              {/* Option 2: Two Channels (~50:50) */}
              <div
                onClick={() => setSelectedStrategy('two_channels')}
                className={`p-5 rounded-2xl border transition cursor-pointer flex flex-col justify-between ${
                  selectedStrategy === 'two_channels'
                    ? 'bg-[#122044] border-blue-500 shadow-xl shadow-blue-600/20 ring-2 ring-blue-500/50'
                    : 'bg-[#070e20] border-[#18284e] hover:bg-[#0e1a38]'
                }`}
              >
                <div className="space-y-2">
                  <span className="px-2 py-0.5 rounded-md bg-emerald-950/60 text-emerald-300 text-[10px] font-bold border border-emerald-800/40 uppercase">
                    Option 2 (Recommended)
                  </span>
                  <h4 className="text-sm font-bold text-white m-0">
                    Two Channels (~50:50 Balanced)
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed m-0">
                    Pairs two complementary instructors (e.g. Gate Smashers + Knowledge Gate) sharing ~50% workload each without topic repetition.
                  </p>
                </div>
                <div className="pt-4 mt-2 border-t border-[#18284e] text-xs font-semibold text-emerald-400">
                  {selectedStrategy === 'two_channels' ? '● Active Choice' : 'Choose 2 Channels'}
                </div>
              </div>

              {/* Option 3: Different Channel per Topic */}
              <div
                onClick={() => setSelectedStrategy('different_per_topic')}
                className={`p-5 rounded-2xl border transition cursor-pointer flex flex-col justify-between ${
                  selectedStrategy === 'different_per_topic'
                    ? 'bg-[#122044] border-blue-500 shadow-xl shadow-blue-600/20 ring-2 ring-blue-500/50'
                    : 'bg-[#070e20] border-[#18284e] hover:bg-[#0e1a38]'
                }`}
              >
                <div className="space-y-2">
                  <span className="px-2 py-0.5 rounded-md bg-purple-950/60 text-purple-300 text-[10px] font-bold border border-purple-800/40 uppercase">
                    Option 3
                  </span>
                  <h4 className="text-sm font-bold text-white m-0">
                    Different Channel per Topic
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed m-0">
                    Optimizes topic-by-topic for highest individual educational relevance across top YouTube educators in your preferred languages.
                  </p>
                </div>
                <div className="pt-4 mt-2 border-t border-[#18284e] text-xs font-semibold text-purple-400">
                  {selectedStrategy === 'different_per_topic' ? '● Active Choice' : 'Choose Multi-Channel'}
                </div>
              </div>

              {/* Option 4: Custom Channel Selection */}
              <div
                onClick={() => setSelectedStrategy('custom')}
                className={`p-5 rounded-2xl border transition cursor-pointer flex flex-col justify-between ${
                  selectedStrategy === 'custom'
                    ? 'bg-[#122044] border-blue-500 shadow-xl shadow-blue-600/20 ring-2 ring-blue-500/50'
                    : 'bg-[#070e20] border-[#18284e] hover:bg-[#0e1a38]'
                }`}
              >
                <div className="space-y-2">
                  <span className="px-2 py-0.5 rounded-md bg-amber-950/60 text-amber-300 text-[10px] font-bold border border-amber-800/40 uppercase">
                    Option 4
                  </span>
                  <h4 className="text-sm font-bold text-white m-0">
                    Custom Channel Selection
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed m-0">
                    Select exactly which candidate educators to include and customize assignments topic-by-topic in the distribution preview.
                  </p>
                </div>
                <div className="pt-4 mt-2 border-t border-[#18284e] text-xs font-semibold text-amber-400">
                  {selectedStrategy === 'custom' ? '● Active Choice' : 'Choose Custom'}
                </div>
              </div>
            </div>
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center justify-between pt-4 border-t border-[#18284e]">
            <button
              onClick={() => setCurrentStep(1)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#070e20] hover:bg-[#132247] border border-[#1b2b52] text-slate-300 hover:text-white text-xs font-semibold cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Languages</span>
            </button>

            <button
              onClick={handleProceedToPreview}
              disabled={isPreviewing}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-lg shadow-blue-600/30 transition cursor-pointer disabled:opacity-50"
            >
              {isPreviewing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Generating Distribution Preview...</span>
                </>
              ) : (
                <>
                  <span>Review Distribution Preview</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          STEP 3: Channel Distribution Preview Table & Confirmation
         ========================================================================= */}
      {currentStep === 3 && previewResult && (
        <div className="space-y-8">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Sliders className="w-5 h-5 text-blue-400" />
              <h3 className="text-base sm:text-lg font-bold text-white m-0">
                Step 3: Preview Channel Distribution & Confirm
              </h3>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 m-0">
              {previewResult.strategy_explanation}
            </p>
          </div>

          {/* Coverage Summary Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-2xl bg-[#070e20] border border-[#18284e]">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Total Topics
              </span>
              <span className="text-xl sm:text-2xl font-black text-white mt-1 block">
                {previewResult.coverage.total_topics}
              </span>
              <span className="text-[10px] text-slate-500">Extracted from syllabus</span>
            </div>

            <div className="p-4 rounded-2xl bg-[#070e20] border border-[#18284e]">
              <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider block">
                Verified Matches
              </span>
              <span className="text-xl sm:text-2xl font-black text-emerald-300 mt-1 block">
                {previewResult.coverage.topics_with_verified}
              </span>
              <span className="text-[10px] text-emerald-400/80">
                {previewResult.coverage.verified_coverage_percentage}% verified
              </span>
            </div>

            <div className="p-4 rounded-2xl bg-[#070e20] border border-[#18284e]">
              <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider block">
                Probable Matches
              </span>
              <span className="text-xl sm:text-2xl font-black text-amber-300 mt-1 block">
                {previewResult.coverage.topics_with_probable}
              </span>
              <span className="text-[10px] text-amber-400/80">
                Secondary/Course review
              </span>
            </div>

            <div className="p-4 rounded-2xl bg-[#070e20] border border-[#18284e]">
              <span className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider block">
                Missing Resources
              </span>
              <span className="text-xl sm:text-2xl font-black text-rose-300 mt-1 block">
                {previewResult.coverage.topics_with_no_resource}
              </span>
              <span className="text-[10px] text-rose-400/80">
                No video verified
              </span>
            </div>
          </div>

          {/* Missing Topics Honest Warning if any */}
          {previewResult.missing_topics && previewResult.missing_topics.length > 0 && (
            <div className="p-4 rounded-2xl bg-amber-950/30 border border-amber-800/50 text-xs text-amber-300 space-y-1.5">
              <div className="flex items-center gap-2 font-bold">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                <span>Notice: {previewResult.missing_topics.length} syllabus topics currently lack verified candidate videos:</span>
              </div>
              <p className="text-[11px] text-amber-300/80 m-0">
                {previewResult.missing_topics.join(' • ')}
              </p>
              <p className="text-[11px] text-slate-400 m-0">
                SyllabusSync AI never fabricates 100% coverage. You can find replacement videos or study via reference textbooks.
              </p>
            </div>
          )}

          {/* Distribution Preview Table */}
          <div className="rounded-2xl border border-[#18284e] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#070e20] border-b border-[#18284e] text-slate-400 text-[11px] font-semibold uppercase tracking-wider">
                    <th className="p-3.5">Topic & Module</th>
                    <th className="p-3.5">Assigned Educator</th>
                    <th className="p-3.5">Candidate Video</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5">Relevance Explanation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#152342] bg-[#0b1429]">
                  {previewResult.preview_items.map((item, idx) => (
                    <tr key={item.topic_id} className="hover:bg-[#0f1b38] transition-colors">
                      <td className="p-3.5 max-w-[220px]">
                        <div className="font-bold text-white leading-snug">
                          {idx + 1}. {item.topic_title}
                        </div>
                        <span className="text-[10px] text-slate-400 block mt-0.5">
                          {item.module_title}
                        </span>
                      </td>

                      <td className="p-3.5 whitespace-nowrap">
                        {selectedStrategy === 'custom' && item.available_channels.length > 1 ? (
                          <select
                            value={customAssignments[item.topic_id] || item.selected_channel}
                            onChange={(e) => setCustomAssignments((prev) => ({ ...prev, [item.topic_id]: e.target.value }))}
                            className="bg-[#070e20] border border-[#1b2b52] text-white text-xs px-2.5 py-1 rounded-lg focus:outline-hidden focus:border-blue-500 cursor-pointer"
                          >
                            {item.available_channels.map((ch) => (
                              <option key={ch} value={ch}>{ch}</option>
                            ))}
                          </select>
                        ) : (
                          <div className="flex items-center gap-1.5 font-semibold text-slate-200">
                            <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                            <span>{customAssignments[item.topic_id] || item.selected_channel}</span>
                          </div>
                        )}
                      </td>

                      <td className="p-3.5 max-w-[240px]">
                        {item.candidate_video_title ? (
                          <div className="space-y-0.5">
                            <span className="font-medium text-slate-200 line-clamp-2">
                              {item.candidate_video_title}
                            </span>
                            {item.duration_formatted && (
                              <span className="text-[10px] font-mono text-slate-400">
                                Duration: {item.duration_formatted}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-500 italic">No video assigned</span>
                        )}
                      </td>

                      <td className="p-3.5 whitespace-nowrap">
                        <span
                          className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                            item.match_status === 'verified'
                              ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/50'
                              : item.match_status === 'probable'
                              ? 'bg-amber-950/60 text-amber-300 border border-amber-800/50'
                              : 'bg-rose-950/60 text-rose-300 border border-rose-800/50'
                          }`}
                        >
                          {item.match_status === 'verified'
                            ? 'VERIFIED MATCH'
                            : item.match_status === 'probable'
                            ? 'PROBABLE MATCH'
                            : 'NO VERIFIED VIDEO FOUND'}
                        </span>
                      </td>

                      <td className="p-3.5 max-w-[260px] text-[11px] text-slate-300 leading-relaxed">
                        {item.relevance_explanation}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bottom Confirmation Action */}
          <div className="flex items-center justify-between pt-4 border-t border-[#18284e]">
            <button
              onClick={() => setCurrentStep(2)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#070e20] hover:bg-[#132247] border border-[#1b2b52] text-slate-300 hover:text-white text-xs font-semibold cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Strategy</span>
            </button>

            <button
              onClick={handleConfirmStrategy}
              disabled={isConfirming}
              className="inline-flex items-center gap-2 px-8 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-xl shadow-blue-600/30 transition cursor-pointer disabled:opacity-50"
            >
              {isConfirming ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Saving & Building Video Library...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4 text-cyan-300" />
                  <span>Confirm Strategy & Build Video Library</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
