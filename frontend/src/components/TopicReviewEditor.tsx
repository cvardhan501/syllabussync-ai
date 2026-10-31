import React, { useState } from 'react';
import { 
  Sparkles, 
  Save, 
  Plus, 
  Trash2, 
  ArrowUp, 
  ArrowDown, 
  AlertTriangle, 
  Edit3, 
  Check, 
  Loader2,
  ArrowRight,
  ChevronRight,
  ChevronDown,
  Split,
  GitMerge,
  BookOpen,
  GraduationCap,
  X
} from 'lucide-react';
import type { 
  SyllabusAnalysisResponse, 
  ModuleItem, 
  TopicItem, 
  TopicUpdateRequest,
  ValidationReport,
  ValidationWarning
} from '../types';
import { apiService, ApiErrorResponse } from '../services/api';

interface TopicReviewEditorProps {
  analysisData: SyllabusAnalysisResponse;
  onUpdateSuccess: (updated: SyllabusAnalysisResponse) => void;
  onConfirmTopics: () => void;
  onViewSource?: () => void;
}

const cleanModuleTitle = (title: string): string => {
  return title.replace(/^(?:Module|Unit|Chapter|Part)\s*\d+[\s:—\-]+/i, '').trim() || title.trim();
};

const formatModuleTitle = (index: number, title: string): string => {
  const clean = cleanModuleTitle(title);
  return `Module ${index + 1} — ${clean}`;
};

export const TopicReviewEditor: React.FC<TopicReviewEditorProps> = ({
  analysisData,
  onUpdateSuccess,
  onConfirmTopics,
  onViewSource,
}) => {
  const [courseName, setCourseName] = useState(analysisData.course_name || 'Computer Science Course');
  const [modules, setModules] = useState<ModuleItem[]>(analysisData.modules);
  const [activeModuleId, setActiveModuleId] = useState<string>(
    analysisData.modules[0]?.id || ''
  );
  const [ambiguousSections] = useState<string[]>(analysisData.ambiguous_sections);
  const [editingTopicId, setEditingTopicId] = useState<string | null>(null);
  const [newSubtopicInputs, setNewSubtopicInputs] = useState<{ [topicId: string]: string }>({});

  // Quality Validation & Metadata State
  const [validationReport, setValidationReport] = useState<ValidationReport | undefined>(analysisData.validation_report);
  const [showValidationDetails, setShowValidationDetails] = useState(false);
  const [showMetadataDrawer, setShowMetadataDrawer] = useState(false);
  const [showLowConfidenceModal, setShowLowConfidenceModal] = useState(false);
  const [splitModalData, setSplitModalData] = useState<{
    moduleId: string;
    topicId: string;
    originalTitle: string;
    splitTitle1: string;
    splitTitle2: string;
  } | null>(null);

  // UI state
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  // Deletion modal
  const [deleteTarget, setDeleteTarget] = useState<{
    type: 'module' | 'topic';
    moduleId: string;
    topicId?: string;
    title: string;
  } | null>(null);

  // Helpers for warnings
  const getTopicWarnings = (topicId: string): ValidationWarning[] => {
    if (!validationReport?.warnings) return [];
    return validationReport.warnings.filter((w) => w.topic_id === topicId);
  };

  const getModuleWarnings = (moduleId: string): ValidationWarning[] => {
    if (!validationReport?.warnings) return [];
    return validationReport.warnings.filter((w) => w.module_id === moduleId && !w.topic_id);
  };

  // Active Module
  const activeModule = modules.find((m) => m.id === activeModuleId) || modules[0];

  // Module Actions
  const handleAddModule = () => {
    const nextIdx = modules.length + 1;
    const newModId = `mod_custom_${Date.now()}`;
    const newModule: ModuleItem = {
      id: newModId,
      title: `Module ${nextIdx} — New Unit`,
      order_index: modules.length,
      topics: [
        {
          id: `top_custom_${Date.now()}`,
          title: 'Initial Concept',
          explanation: 'Core concept for this module.',
          estimated_minutes: 30,
          difficulty: 'medium',
          prerequisites: [],
          subtopics: [],
          order_index: 0,
        },
      ],
    };
    setModules([...modules, newModule]);
    setActiveModuleId(newModId);
    setIsDirty(true);
  };

  const handleUpdateModuleTitle = (moduleId: string, newTitle: string) => {
    setModules((prev) =>
      prev.map((m) => (m.id === moduleId ? { ...m, title: newTitle } : m))
    );
    setIsDirty(true);
  };

  const handleMoveModule = (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === modules.length - 1) return;

    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    const updated = [...modules];
    const temp = updated[index];
    updated[index] = updated[targetIdx];
    updated[targetIdx] = temp;

    const renumbered = updated.map((m, idx) => ({
      ...m,
      title: formatModuleTitle(idx, m.title),
      order_index: idx,
    }));

    setModules(renumbered);
    setIsDirty(true);
  };

  // Topic Actions
  const handleAddTopic = (moduleId: string) => {
    setModules((prev) =>
      prev.map((mod) => {
        if (mod.id !== moduleId) return mod;
        const nextTopicIdx = mod.topics.length + 1;
        const newTopic: TopicItem = {
          id: `top_custom_${Date.now()}`,
          title: `Topic ${nextTopicIdx}`,
          explanation: 'Study objective for this topic.',
          estimated_minutes: 30,
          difficulty: 'medium',
          prerequisites: [],
          subtopics: [],
          order_index: mod.topics.length,
        };
        return {
          ...mod,
          topics: [...mod.topics, newTopic],
        };
      })
    );
    setIsDirty(true);
  };

  const handleUpdateTopic = (
    moduleId: string,
    topicId: string,
    patch: Partial<TopicItem>
  ) => {
    setModules((prev) =>
      prev.map((mod) => {
        if (mod.id !== moduleId) return mod;
        return {
          ...mod,
          topics: mod.topics.map((top) =>
            top.id === topicId ? { ...top, ...patch } : top
          ),
        };
      })
    );
    setIsDirty(true);
  };

  const handleMoveTopic = (
    moduleId: string,
    topicIndex: number,
    direction: 'up' | 'down'
  ) => {
    setModules((prev) =>
      prev.map((mod) => {
        if (mod.id !== moduleId) return mod;
        if (direction === 'up' && topicIndex === 0) return mod;
        if (direction === 'down' && topicIndex === mod.topics.length - 1) return mod;

        const targetIdx = direction === 'up' ? topicIndex - 1 : topicIndex + 1;
        const updatedTopics = [...mod.topics];
        const temp = updatedTopics[topicIndex];
        updatedTopics[topicIndex] = updatedTopics[targetIdx];
        updatedTopics[targetIdx] = temp;

        updatedTopics.forEach((t, i) => {
          t.order_index = i;
        });

        return { ...mod, topics: updatedTopics };
      })
    );
    setIsDirty(true);
  };

  // Subtopic Management
  const handleAddSubtopic = (moduleId: string, topicId: string, title: string) => {
    if (!title.trim()) return;
    setModules((prev) =>
      prev.map((mod) => {
        if (mod.id !== moduleId) return mod;
        return {
          ...mod,
          topics: mod.topics.map((t) => {
            if (t.id !== topicId) return t;
            const newSub = {
              id: `sub_${Date.now()}`,
              title: title.trim(),
            };
            return {
              ...t,
              subtopics: [...(t.subtopics || []), newSub],
            };
          }),
        };
      })
    );
    setIsDirty(true);
  };

  const handleDeleteSubtopic = (moduleId: string, topicId: string, subIdx: number) => {
    setModules((prev) =>
      prev.map((mod) => {
        if (mod.id !== moduleId) return mod;
        return {
          ...mod,
          topics: mod.topics.map((t) => {
            if (t.id !== topicId) return t;
            const updatedSubs = [...(t.subtopics || [])];
            updatedSubs.splice(subIdx, 1);
            return {
              ...t,
              subtopics: updatedSubs,
            };
          }),
        };
      })
    );
    setIsDirty(true);
  };

  // Auto-Balance Topics in Module based on official duration
  const handleAutoBalance = () => {
    if (!activeModule?.official_minutes || activeModule.topics.length === 0) return;
    const count = activeModule.topics.length;
    const base = Math.floor(activeModule.official_minutes / count);
    const rem = activeModule.official_minutes % count;
    setModules((prev) =>
      prev.map((mod) => {
        if (mod.id !== activeModule.id) return mod;
        const updated = mod.topics.map((t, i) => ({
          ...t,
          estimated_minutes: base + (i < rem ? 1 : 0),
        }));
        return { ...mod, topics: updated };
      })
    );
    setIsDirty(true);
  };

  // Delete Confirmation
  const confirmDelete = () => {
    if (!deleteTarget) return;

    if (deleteTarget.type === 'module') {
      if (modules.length <= 1) {
        setErrorMessage('A syllabus must contain at least one module.');
        setDeleteTarget(null);
        return;
      }
      const remaining = modules.filter((m) => m.id !== deleteTarget.moduleId);
      const renumbered = remaining.map((m, idx) => ({
        ...m,
        title: formatModuleTitle(idx, m.title),
        order_index: idx,
      }));
      setModules(renumbered);
      if (activeModuleId === deleteTarget.moduleId && renumbered[0]) {
        setActiveModuleId(renumbered[0].id);
      }
    } else if (deleteTarget.type === 'topic' && deleteTarget.topicId) {
      setModules((prev) =>
        prev.map((mod) => {
          if (mod.id !== deleteTarget.moduleId) return mod;
          return {
            ...mod,
            topics: mod.topics.filter((t) => t.id !== deleteTarget.topicId),
          };
        })
      );
    }

    setIsDirty(true);
    setDeleteTarget(null);
  };

  // Merge Topic with Previous Topic
  const handleMergeTopicWithPrevious = (moduleId: string, topicIndex: number) => {
    if (topicIndex === 0) return;
    setModules((prev) =>
      prev.map((mod) => {
        if (mod.id !== moduleId) return mod;
        const prevTopic = mod.topics[topicIndex - 1];
        const currTopic = mod.topics[topicIndex];
        const mergedTopic: TopicItem = {
          ...prevTopic,
          title: `${prevTopic.title} & ${currTopic.title}`,
          explanation: [prevTopic.explanation, currTopic.explanation].filter(Boolean).join(' '),
          estimated_minutes: prevTopic.estimated_minutes + currTopic.estimated_minutes,
          subtopics: [...(prevTopic.subtopics || []), ...(currTopic.subtopics || [])],
          prerequisites: Array.from(new Set([...(prevTopic.prerequisites || []), ...(currTopic.prerequisites || [])])),
        };
        const updatedTopics = [...mod.topics];
        updatedTopics.splice(topicIndex - 1, 2, mergedTopic);
        updatedTopics.forEach((t, i) => {
          t.order_index = i;
        });
        return { ...mod, topics: updatedTopics };
      })
    );
    setIsDirty(true);
  };

  // Open Topic Split Modal
  const handleOpenSplitModal = (moduleId: string, topic: TopicItem) => {
    let part1 = topic.title;
    let part2 = 'Continued';
    const delimiters = [' & ', ' and ', ' - ', ' – ', ', ', '; '];
    for (const d of delimiters) {
      if (topic.title.includes(d)) {
        const parts = topic.title.split(d);
        if (parts.length >= 2 && parts[0].trim() && parts[1].trim()) {
          part1 = parts[0].trim();
          part2 = parts.slice(1).join(d).trim();
          break;
        }
      }
    }
    setSplitModalData({
      moduleId,
      topicId: topic.id,
      originalTitle: topic.title,
      splitTitle1: part1,
      splitTitle2: part2,
    });
  };

  // Confirm Split Action
  const handleConfirmSplit = () => {
    if (!splitModalData) return;
    const { moduleId, topicId, splitTitle1, splitTitle2 } = splitModalData;
    setModules((prev) =>
      prev.map((mod) => {
        if (mod.id !== moduleId) return mod;
        const topicIdx = mod.topics.findIndex((t) => t.id === topicId);
        if (topicIdx === -1) return mod;
        const curr = mod.topics[topicIdx];
        const halfMinutes = Math.max(15, Math.round(curr.estimated_minutes / 2));
        const t1: TopicItem = {
          ...curr,
          title: splitTitle1.trim() || `${curr.title} (Part 1)`,
          estimated_minutes: halfMinutes,
        };
        const t2: TopicItem = {
          ...curr,
          id: `top_split_${Date.now()}`,
          title: splitTitle2.trim() || `${curr.title} (Part 2)`,
          estimated_minutes: halfMinutes,
          order_index: topicIdx + 1,
        };
        const updated = [...mod.topics];
        updated.splice(topicIdx, 1, t1, t2);
        updated.forEach((t, i) => {
          t.order_index = i;
        });
        return { ...mod, topics: updated };
      })
    );
    setIsDirty(true);
    setSplitModalData(null);
  };

  // Confirmation Gate for Structure
  const handleConfirmStructure = () => {
    if (validationReport?.needs_confirmation) {
      setShowLowConfidenceModal(true);
    } else {
      onConfirmTopics();
    }
  };

  // Save changes to SQLite backend
  const handleSave = async () => {
    setIsSaving(true);
    setErrorMessage(null);
    setSaveSuccess(false);

    const normalizedModules = modules.map((mod, mIdx) => ({
      ...mod,
      title: formatModuleTitle(mIdx, mod.title),
      order_index: mIdx,
      topics: mod.topics.map((t, tIdx) => ({
        ...t,
        order_index: tIdx,
      })),
    }));

    const payload: TopicUpdateRequest = {
      course_name: courseName,
      course_code: analysisData.course_code,
      credits: analysisData.credits,
      course_objectives: analysisData.course_objectives,
      course_outcomes: analysisData.course_outcomes,
      prerequisites: analysisData.prerequisites,
      textbooks: analysisData.textbooks,
      reference_books: analysisData.reference_books,
      online_resources: analysisData.online_resources,
      assignments: analysisData.assignments,
      lab_experiments: analysisData.lab_experiments,
      has_lab_component: analysisData.has_lab_component,
      assessment_info: analysisData.assessment_info,
      modules: normalizedModules,
      ambiguous_sections: ambiguousSections,
      validation_report: validationReport,
    };

    try {
      const updated = await apiService.updateSyllabusTopics(analysisData.syllabus_id, payload);
      setValidationReport(updated.validation_report);
      onUpdateSuccess(updated);
      setIsDirty(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      if (err instanceof ApiErrorResponse) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(err.message || 'Failed to save topic changes.');
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Header Row with Title, Edit, Save Changes */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight m-0">
            Syllabus Topic Review
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5 m-0">
            Review and edit the extracted structure before we find YouTube resources.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {onViewSource && (
            <button
              onClick={onViewSource}
              className="px-3.5 py-2 rounded-xl bg-[#111e3b] hover:bg-[#182a52] text-slate-300 text-xs font-semibold border border-[#1e3362] transition cursor-pointer"
            >
              View Source
            </button>
          )}

          <button
            onClick={handleSave}
            disabled={isSaving}
            className={`inline-flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold transition cursor-pointer shadow-md ${
              isDirty
                ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/30'
                : 'bg-blue-600/80 hover:bg-blue-600 text-white shadow-blue-600/20'
            }`}
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Saving...</span>
              </>
            ) : saveSuccess ? (
              <>
                <Check className="w-4 h-4 text-emerald-300" />
                <span>Saved</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>Save Changes</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Course Header Banner (Matches Reference Screen 4) */}
      <div className="p-4 sm:p-5 rounded-2xl bg-[#0c162e] border border-[#1b2b54] flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-md">
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center font-extrabold text-lg shrink-0">
            {courseName.charAt(0).toUpperCase() || 'C'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={courseName}
                onChange={(e) => {
                  setCourseName(e.target.value);
                  setIsDirty(true);
                }}
                className="text-base sm:text-lg font-bold text-white bg-transparent border-b border-transparent hover:border-slate-700 focus:border-blue-500 focus:outline-hidden px-1 py-0.5 rounded-sm transition max-w-md"
                title="Click to edit course name"
              />
              <Edit3 className="w-3.5 h-3.5 text-slate-500" />
            </div>
            <p className="text-xs text-slate-400 m-0">
              {analysisData.course_code || 'B.Tech / College Course'} • {analysisData.total_topics_count} topics • {(analysisData.total_estimated_minutes / 60).toFixed(1)} hrs
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {analysisData.ai_status === 'completed' || (!analysisData.is_fallback && !analysisData.ai_status) ? (
            <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5 shadow-xs">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              <span>Analysis completed</span>
            </span>
          ) : analysisData.ai_status === 'temporarily_unavailable' ? (
            <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1.5 shadow-xs" title={analysisData.ai_status_message || 'AI analysis temporarily unavailable'}>
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>AI analysis temporarily unavailable</span>
            </span>
          ) : (
            <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30 flex items-center gap-1.5 shadow-xs" title={analysisData.ai_status_message || 'Local syllabus extraction available'}>
              <BookOpen className="w-3.5 h-3.5 text-blue-400" />
              <span>Local syllabus extraction available</span>
            </span>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="rounded-xl bg-rose-950/40 border border-rose-800/60 p-3 text-xs text-rose-300 flex items-center justify-between">
          <span>{errorMessage}</span>
          <button 
            onClick={() => setErrorMessage(null)} 
            className="text-rose-400 hover:text-rose-200 cursor-pointer font-medium ml-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Structural Validation Report Banner */}
      {validationReport && (
        <div className={`rounded-2xl border p-4 space-y-3 transition ${
          validationReport.quality_score >= 80
            ? 'bg-[#081726]/80 border-emerald-500/30'
            : validationReport.quality_score >= 60
            ? 'bg-[#1a1406]/80 border-amber-500/30'
            : 'bg-[#21090d]/80 border-rose-500/30'
        }`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-xs shrink-0 ${
                validationReport.quality_score >= 80
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : validationReport.quality_score >= 60
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              }`}>
                {validationReport.quality_score}%
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-xs sm:text-sm font-bold text-white m-0">
                    Syllabus Intelligence Audit
                  </h4>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                    validationReport.quality_score >= 80
                      ? 'bg-emerald-500/15 text-emerald-300'
                      : validationReport.quality_score >= 60
                      ? 'bg-amber-500/15 text-amber-300'
                      : 'bg-rose-500/15 text-rose-300'
                  }`}>
                    {validationReport.quality_score >= 80 ? 'High Quality' : validationReport.quality_score >= 60 ? 'Needs Review' : 'Critical Defects Detected'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 m-0 mt-0.5">
                  {validationReport.summary}
                </p>
              </div>
            </div>

            {validationReport.warnings.length > 0 && (
              <button
                onClick={() => setShowValidationDetails(!showValidationDetails)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#0f1d38] hover:bg-[#162a52] text-slate-300 text-xs font-medium border border-[#1e3462] transition cursor-pointer self-start sm:self-auto shrink-0"
              >
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                <span>{validationReport.warnings.length} Audit Issue{validationReport.warnings.length > 1 ? 's' : ''}</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showValidationDetails ? 'rotate-180' : ''}`} />
              </button>
            )}
          </div>

          {/* Collapsible Warnings Details */}
          {showValidationDetails && validationReport.warnings.length > 0 && (
            <div className="pt-3 border-t border-slate-800/60 space-y-2">
              {validationReport.warnings.map((w, idx) => (
                <div
                  key={idx}
                  className="rounded-xl bg-[#070e1c] border border-slate-800 p-2.5 flex items-start justify-between gap-3 text-xs"
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${
                      w.severity === 'error' ? 'text-rose-400' : 'text-amber-400'
                    }`} />
                    <div className="space-y-0.5">
                      <p className="font-semibold text-slate-200 m-0">
                        {w.message}
                      </p>
                      {w.suggested_action && (
                        <p className="text-[11px] text-slate-400 m-0">
                          <span className="text-blue-400 font-medium">Recommended action:</span> {w.suggested_action}
                        </p>
                      )}
                    </div>
                  </div>
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-sm bg-slate-800 text-slate-400 shrink-0">
                    {w.code}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Separated Course Metadata & Objectives Section */}
      {(analysisData.course_objectives?.length || analysisData.course_outcomes?.length || analysisData.textbooks?.length || analysisData.reference_books?.length || analysisData.online_resources?.length || analysisData.assignments?.length || analysisData.lab_experiments?.length || analysisData.credits) && (
        <div className="rounded-2xl bg-[#091224] border border-[#16274e] p-4">
          <button
            onClick={() => setShowMetadataDrawer(!showMetadataDrawer)}
            className="w-full flex items-center justify-between text-left cursor-pointer group"
          >
            <div className="flex items-center gap-2.5">
              <BookOpen className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-bold text-slate-200 group-hover:text-white transition">
                Course Syllabus Specifications & Literature
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/25">
                Segregated from Topics
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-400 group-hover:text-slate-200">
              <span className="text-[11px] font-mono">
                {((analysisData.course_objectives?.length || 0) + (analysisData.course_outcomes?.length || 0) + (analysisData.textbooks?.length || 0) + (analysisData.reference_books?.length || 0) + (analysisData.online_resources?.length || 0) + (analysisData.assignments?.length || 0) + (analysisData.lab_experiments?.length || 0))} items
              </span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showMetadataDrawer ? 'rotate-180' : ''}`} />
            </div>
          </button>

          {showMetadataDrawer && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-[#16274e] text-xs">
              {analysisData.credits && (
                <div className="col-span-full rounded-xl bg-[#070e1c] border border-[#17274b] p-3 flex items-center justify-between">
                  <span className="text-slate-400 font-semibold">Course Credits & Term:</span>
                  <span className="text-white font-mono font-bold">{analysisData.credits}</span>
                </div>
              )}

              {analysisData.course_objectives && analysisData.course_objectives.length > 0 && (
                <div className="rounded-xl bg-[#070e1c] border border-[#17274b] p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 text-blue-400 font-semibold text-xs">
                    <GraduationCap className="w-4 h-4" />
                    <span>Course Objectives ({analysisData.course_objectives.length})</span>
                  </div>
                  <ul className="text-[11px] text-slate-300 space-y-1.5 pl-4 list-disc m-0">
                    {analysisData.course_objectives.map((obj, i) => (
                      <li key={i} className="leading-relaxed">{obj}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analysisData.course_outcomes && analysisData.course_outcomes.length > 0 && (
                <div className="rounded-xl bg-[#070e1c] border border-[#17274b] p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-semibold text-xs">
                    <Check className="w-4 h-4" />
                    <span>Expected Course Outcomes ({analysisData.course_outcomes.length})</span>
                  </div>
                  <ul className="text-[11px] text-slate-300 space-y-1.5 pl-4 list-disc m-0">
                    {analysisData.course_outcomes.map((co, i) => (
                      <li key={i} className="leading-relaxed">{co}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analysisData.assignments && analysisData.assignments.length > 0 && (
                <div className="rounded-xl bg-[#070e1c] border border-[#17274b] p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 text-indigo-400 font-semibold text-xs">
                    <BookOpen className="w-4 h-4" />
                    <span>Assignments & Case Studies ({analysisData.assignments.length})</span>
                  </div>
                  <ul className="text-[11px] text-slate-300 space-y-1.5 pl-4 list-disc m-0">
                    {analysisData.assignments.map((asgn, i) => (
                      <li key={i} className="leading-relaxed">{asgn}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analysisData.textbooks && analysisData.textbooks.length > 0 && (
                <div className="rounded-xl bg-[#070e1c] border border-[#17274b] p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 text-amber-400 font-semibold text-xs">
                    <BookOpen className="w-4 h-4" />
                    <span>Prescribed Textbooks ({analysisData.textbooks.length})</span>
                  </div>
                  <ul className="text-[11px] text-slate-300 space-y-1.5 pl-4 list-disc m-0">
                    {analysisData.textbooks.map((tb, i) => (
                      <li key={i} className="leading-relaxed">{tb}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analysisData.reference_books && analysisData.reference_books.length > 0 && (
                <div className="rounded-xl bg-[#070e1c] border border-[#17274b] p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 text-purple-400 font-semibold text-xs">
                    <BookOpen className="w-4 h-4" />
                    <span>Reference Books ({analysisData.reference_books.length})</span>
                  </div>
                  <ul className="text-[11px] text-slate-300 space-y-1.5 pl-4 list-disc m-0">
                    {analysisData.reference_books.map((rb, i) => (
                      <li key={i} className="leading-relaxed">{rb}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analysisData.online_resources && analysisData.online_resources.length > 0 && (
                <div className="rounded-xl bg-[#070e1c] border border-[#17274b] p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 text-cyan-400 font-semibold text-xs">
                    <BookOpen className="w-4 h-4" />
                    <span>Online & Web Resources ({analysisData.online_resources.length})</span>
                  </div>
                  <ul className="text-[11px] text-slate-300 space-y-1.5 pl-4 list-disc m-0">
                    {analysisData.online_resources.map((url, i) => (
                      <li key={i} className="leading-relaxed font-mono truncate">
                        <a href={url.startsWith('http') ? url : `https://${url}`} target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline">
                          {url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {analysisData.lab_experiments && analysisData.lab_experiments.length > 0 && (
                <div className="col-span-full rounded-xl bg-[#070e1c] border border-[#17274b] p-3.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-emerald-400 font-semibold text-xs">
                      <GraduationCap className="w-4 h-4" />
                      <span>Indicative Lab Experiments ({analysisData.lab_experiments.length})</span>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
                      Segregated from Theory
                    </span>
                  </div>
                  <ol className="text-[11px] text-slate-300 space-y-1.5 pl-4 list-decimal m-0 max-h-48 overflow-y-auto">
                    {analysisData.lab_experiments.map((exp, i) => (
                      <li key={i} className="leading-relaxed">{exp}</li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Ambiguous Sections Alert (Document Ambiguities Only — Never Technical Diagnostics) */}
      {(() => {
        const cleanAmbiguities = ambiguousSections.filter(
          (sec) =>
            !sec.includes('[DEVELOPMENT FALLBACK') &&
            !sec.includes('MODEL_TOOL_USE_ERROR') &&
            !sec.includes('modelStreamErrorException') &&
            !sec.includes('CONFIG_MISSING') &&
            !sec.includes('AUTHORIZATION_FAILURE') &&
            !sec.includes('MODEL_NOT_AVAILABLE')
        );
        if (cleanAmbiguities.length === 0) return null;
        return (
          <div className="rounded-2xl bg-amber-950/20 border border-amber-800/40 p-4 space-y-1.5">
            <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>Syllabus Notes / Ambiguities:</span>
            </div>
            <ul className="text-xs text-amber-200/90 space-y-1 pl-5 list-disc m-0">
              {cleanAmbiguities.map((sec, idx) => (
                <li key={idx} className="leading-relaxed">{sec}</li>
              ))}
            </ul>
          </div>
        );
      })()}

      {/* Two-Pane Layout (Matches Screen 4 Exactly) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Pane: Module List (4 cols) */}
        <div className="lg:col-span-5 space-y-2.5">
          <div className="space-y-2">
            {modules.map((mod, mIdx) => {
              const isSelected = mod.id === activeModule?.id;
              const modMinutes = mod.topics.reduce((acc, t) => acc + t.estimated_minutes, 0);
              const modWarnings = getModuleWarnings(mod.id);

              return (
                <div
                  key={mod.id}
                  onClick={() => setActiveModuleId(mod.id)}
                  className={`p-3.5 rounded-2xl border transition cursor-pointer flex items-center justify-between gap-3 ${
                    isSelected
                      ? 'bg-[#122044] border-blue-500/60 shadow-lg shadow-blue-600/10'
                      : 'bg-[#0b1429] border-[#18284e] hover:bg-[#0f1b36] hover:border-slate-700'
                  }`}
                >
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex items-center gap-1.5">
                      <p className={`text-xs font-bold truncate m-0 ${isSelected ? 'text-white' : 'text-slate-200'}`}>
                        {mod.title}
                      </p>
                      {modWarnings.length > 0 && (
                        <span title={modWarnings[0].message}>
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 m-0">
                      {mod.topics.length} topics • {modMinutes} min
                    </p>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMoveModule(mIdx, 'up');
                      }}
                      disabled={mIdx === 0}
                      className="p-1 rounded-md text-slate-500 hover:text-white disabled:opacity-20 cursor-pointer"
                      title="Move module up"
                    >
                      <ArrowUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMoveModule(mIdx, 'down');
                      }}
                      disabled={mIdx === modules.length - 1}
                      className="p-1 rounded-md text-slate-500 hover:text-white disabled:opacity-20 cursor-pointer"
                      title="Move module down"
                    >
                      <ArrowDown className="w-3.5 h-3.5" />
                    </button>
                    <ChevronRight className={`w-4 h-4 ml-1 transition-transform ${isSelected ? 'text-blue-400 translate-x-0.5' : 'text-slate-600'}`} />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Add Module Button */}
          <button
            onClick={handleAddModule}
            className="w-full py-2.5 rounded-2xl bg-[#0b1429] hover:bg-[#122044] border border-dashed border-[#1e305e] text-blue-400 hover:text-blue-300 text-xs font-semibold flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Add Module</span>
          </button>
        </div>

        {/* Right Pane: Selected Module Detail & Topics (7 cols) */}
        <div className="lg:col-span-7 rounded-2xl bg-[#0b1429] border border-[#18284e] p-5 space-y-4">
          {activeModule ? (() => {
            const allocatedMinutes = activeModule.topics.reduce((acc, t) => acc + t.estimated_minutes, 0);
            const hasMismatch = Boolean(activeModule.official_minutes && allocatedMinutes !== activeModule.official_minutes);

            return (
              <>
                {/* Active Module Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#18284e]">
                  <div className="flex-1 min-w-0">
                    <input
                      type="text"
                      value={activeModule.title}
                      onChange={(e) => handleUpdateModuleTitle(activeModule.id, e.target.value)}
                      className="font-bold text-sm sm:text-base text-white bg-transparent border-b border-transparent hover:border-slate-700 focus:border-blue-500 focus:outline-hidden px-1 py-0.5 rounded-sm transition w-full"
                      title="Click to edit module title"
                    />
                    <div className="flex items-center gap-2 mt-1 px-1">
                      <p className="text-[11px] text-slate-400 m-0">
                        {activeModule.topics.length} topics • {allocatedMinutes} min allocated
                      </p>
                      {activeModule.official_minutes && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30 font-mono">
                          Official: {activeModule.official_hours ? `${activeModule.official_hours}h / ` : ''}{activeModule.official_minutes} min
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {hasMismatch && (
                      <button
                        onClick={handleAutoBalance}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 text-xs font-medium transition cursor-pointer"
                        title="Distribute official module hours evenly across topics"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Auto-Balance</span>
                      </button>
                    )}
                    <button
                      onClick={() => handleAddTopic(activeModule.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600/20 hover:bg-blue-600 text-blue-300 hover:text-white border border-blue-500/30 text-xs font-medium transition cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Topic</span>
                    </button>
                    <button
                      onClick={() =>
                        setDeleteTarget({
                          type: 'module',
                          moduleId: activeModule.id,
                          title: activeModule.title,
                        })
                      }
                      className="p-1.5 rounded-xl text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 transition cursor-pointer"
                      title="Delete this module"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Duration warning alert */}
                {hasMismatch && (
                  <div className="rounded-xl bg-amber-950/30 border border-amber-800/40 p-2.5 text-xs text-amber-300 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                      <span>
                        Topic duration total ({allocatedMinutes} min) {allocatedMinutes < activeModule.official_minutes! ? 'falls short of' : 'exceeds'} official module delivery ({activeModule.official_minutes} min).
                      </span>
                    </div>
                    <button
                      onClick={handleAutoBalance}
                      className="text-[11px] underline font-semibold text-amber-200 hover:text-white cursor-pointer shrink-0"
                    >
                      Auto-Balance to {activeModule.official_minutes}m
                    </button>
                  </div>
                )}

              {/* Topics inside Active Module */}
              <div className="space-y-2.5">
                {activeModule.topics.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500 border border-dashed border-[#18284e] rounded-xl">
                    No topics in this unit yet.{' '}
                    <button
                      onClick={() => handleAddTopic(activeModule.id)}
                      className="text-blue-400 underline hover:text-blue-300 cursor-pointer"
                    >
                      Add the first topic
                    </button>
                  </div>
                ) : (
                  activeModule.topics.map((topic, tIdx) => {
                    const isEditing = editingTopicId === topic.id;

                    return (
                      <div
                        key={topic.id}
                        className="rounded-xl bg-[#070e20] border border-[#162548] p-3 space-y-2.5 transition hover:border-[#223869]"
                      >
                        <div className="flex items-center justify-between gap-3">
                          {/* Topic Number & Title */}
                          <div className="flex items-center gap-2.5 flex-1 min-w-0">
                            <span className="w-6 h-5 rounded-md bg-[#111e3b] text-blue-300 text-[11px] font-mono font-semibold flex items-center justify-center shrink-0">
                              {tIdx + 1}.
                            </span>

                            <input
                              type="text"
                              value={topic.title}
                              onChange={(e) =>
                                handleUpdateTopic(activeModule.id, topic.id, {
                                  title: e.target.value,
                                })
                              }
                              className="text-xs sm:text-sm font-semibold text-slate-200 bg-transparent border-b border-transparent hover:border-slate-700 focus:border-blue-500 focus:outline-hidden px-1 py-0.5 rounded-sm transition flex-1 min-w-0"
                            />
                          </div>

                          {/* Difficulty Pill & Duration & Actions */}
                          <div className="flex items-center gap-2 shrink-0">
                            {/* Difficulty Selector */}
                            <select
                              value={topic.difficulty}
                              onChange={(e) =>
                                handleUpdateTopic(activeModule.id, topic.id, {
                                  difficulty: e.target.value as any,
                                })
                              }
                              className={`text-[10px] font-semibold rounded-md px-2 py-0.5 border cursor-pointer focus:outline-hidden ${
                                topic.difficulty === 'easy'
                                  ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/50'
                                  : topic.difficulty === 'hard'
                                  ? 'bg-rose-950/40 text-rose-300 border-rose-800/50'
                                  : 'bg-amber-950/40 text-amber-300 border-amber-800/50'
                              }`}
                            >
                              <option value="easy">Easy</option>
                              <option value="medium">Medium</option>
                              <option value="hard">Hard</option>
                            </select>

                            {/* Estimated Minutes */}
                            <div className="flex items-center gap-1 bg-[#0b1429] border border-[#1d2f58] rounded-md px-2 py-0.5 text-[11px] text-slate-300">
                              <input
                                type="number"
                                min={10}
                                max={240}
                                step={5}
                                value={topic.estimated_minutes}
                                onChange={(e) =>
                                  handleUpdateTopic(activeModule.id, topic.id, {
                                    estimated_minutes: Number(e.target.value) || 30,
                                  })
                                }
                                className="w-7 text-center bg-transparent focus:outline-hidden text-white font-mono"
                              />
                              <span className="text-slate-500">min</span>
                            </div>

                            {/* Move Up / Down */}
                            <button
                              onClick={() => handleMoveTopic(activeModule.id, tIdx, 'up')}
                              disabled={tIdx === 0}
                              className="p-1 text-slate-500 hover:text-white disabled:opacity-20 cursor-pointer"
                              title="Move topic up"
                            >
                              <ArrowUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleMoveTopic(activeModule.id, tIdx, 'down')}
                              disabled={tIdx === activeModule.topics.length - 1}
                              className="p-1 text-slate-500 hover:text-white disabled:opacity-20 cursor-pointer"
                              title="Move topic down"
                            >
                              <ArrowDown className="w-3.5 h-3.5" />
                            </button>

                            {/* Merge with previous */}
                            <button
                              onClick={() => handleMergeTopicWithPrevious(activeModule.id, tIdx)}
                              disabled={tIdx === 0}
                              className="p-1 text-slate-500 hover:text-amber-400 disabled:opacity-20 cursor-pointer"
                              title={tIdx === 0 ? "Cannot merge first topic" : "Merge with previous topic"}
                            >
                              <GitMerge className="w-3.5 h-3.5" />
                            </button>

                            {/* Split topic */}
                            <button
                              onClick={() => handleOpenSplitModal(activeModule.id, topic)}
                              className="p-1 text-slate-500 hover:text-blue-400 cursor-pointer"
                              title="Split topic into parts"
                            >
                              <Split className="w-3.5 h-3.5" />
                            </button>

                            {/* Edit toggle */}
                            <button
                              onClick={() => setEditingTopicId(isEditing ? null : topic.id)}
                              className={`p-1 rounded-md transition cursor-pointer ${
                                isEditing ? 'text-blue-400 bg-blue-950/40' : 'text-slate-500 hover:text-white'
                              }`}
                              title="Edit topic details"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                            </button>

                            {/* Delete topic */}
                            <button
                              onClick={() =>
                                setDeleteTarget({
                                  type: 'topic',
                                  moduleId: activeModule.id,
                                  topicId: topic.id,
                                  title: topic.title,
                                })
                              }
                              className="p-1 text-slate-500 hover:text-rose-400 transition cursor-pointer"
                              title="Delete topic"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>

                        {/* Nested Subtopics Display & Fast Addition */}
                        <div className="pt-1 space-y-1.5">
                          <div className="flex flex-wrap items-center gap-1.5">
                            {topic.subtopics && topic.subtopics.length > 0 && (
                              <>
                                <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Subtopics:</span>
                                {topic.subtopics.map((sub, sIdx) => (
                                  <span
                                    key={sub.id || sIdx}
                                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#132247] text-slate-300 text-[11px] border border-[#1f366e]"
                                  >
                                    <span>{sub.title}</span>
                                    <button
                                      type="button"
                                      onClick={() => handleDeleteSubtopic(activeModule.id, topic.id, sIdx)}
                                      className="text-slate-500 hover:text-rose-400 cursor-pointer ml-0.5"
                                      title="Remove subtopic"
                                    >
                                      <X className="w-2.5 h-2.5" />
                                    </button>
                                  </span>
                                ))}
                              </>
                            )}
                            {/* Inline Add Subtopic Input */}
                            <div className="inline-flex items-center gap-1">
                              <input
                                type="text"
                                placeholder="+ Add subtopic..."
                                value={newSubtopicInputs[topic.id] || ''}
                                onChange={(e) => setNewSubtopicInputs({ ...newSubtopicInputs, [topic.id]: e.target.value })}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    e.preventDefault();
                                    const val = (newSubtopicInputs[topic.id] || '').trim();
                                    if (val) {
                                      handleAddSubtopic(activeModule.id, topic.id, val);
                                      setNewSubtopicInputs({ ...newSubtopicInputs, [topic.id]: '' });
                                    }
                                  }
                                }}
                                className="text-[10px] bg-[#091122] border border-[#182a52] hover:border-slate-700 focus:border-blue-500 focus:outline-hidden rounded-md px-2 py-0.5 text-slate-300 placeholder:text-slate-600 transition w-28"
                              />
                              {(newSubtopicInputs[topic.id] || '').trim() && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    const val = (newSubtopicInputs[topic.id] || '').trim();
                                    if (val) {
                                      handleAddSubtopic(activeModule.id, topic.id, val);
                                      setNewSubtopicInputs({ ...newSubtopicInputs, [topic.id]: '' });
                                    }
                                  }}
                                  className="text-[10px] text-blue-400 hover:text-blue-300 px-1 py-0.5 font-bold cursor-pointer"
                                >
                                  Add
                                </button>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Validation Warnings for Topic */}
                        {getTopicWarnings(topic.id).map((tw, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-950/30 border border-amber-800/40 text-[11px] text-amber-300"
                          >
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                            <span className="font-medium">{tw.message}</span>
                            {tw.suggested_action && (
                              <span className="text-slate-400">({tw.suggested_action})</span>
                            )}
                          </div>
                        ))}

                        {/* Expanded Edit Form for Explanation & Prerequisites */}
                        {isEditing && (
                          <div className="pt-2 border-t border-[#142347] space-y-2 text-xs">
                            <div>
                              <label className="text-[10px] text-slate-400 font-semibold block mb-1">
                                Topic Objective & Notes:
                              </label>
                              <textarea
                                rows={2}
                                value={topic.explanation}
                                onChange={(e) =>
                                  handleUpdateTopic(activeModule.id, topic.id, {
                                    explanation: e.target.value,
                                  })
                                }
                                className="w-full text-xs text-slate-200 bg-[#0b1429] border border-[#1d2f58] rounded-xl p-2 focus:outline-hidden focus:border-blue-500"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 font-semibold block mb-1">
                                Prerequisites (comma separated):
                              </label>
                              <input
                                type="text"
                                value={topic.prerequisites.join(', ')}
                                onChange={(e) =>
                                  handleUpdateTopic(activeModule.id, topic.id, {
                                    prerequisites: e.target.value
                                      .split(',')
                                      .map((p) => p.trim())
                                      .filter(Boolean),
                                  })
                                }
                                className="w-full text-xs text-slate-200 bg-[#0b1429] border border-[#1d2f58] rounded-xl px-2.5 py-1 focus:outline-hidden focus:border-blue-500"
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>

              {/* Topic Info Legend (Matches Reference Screen 4 Bottom) */}
              <div className="pt-3 border-t border-[#18284e] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="space-y-0.5">
                  <span className="text-[11px] font-bold text-slate-400 block">Topic Info</span>
                  <p className="text-[11px] text-slate-400 m-0">
                    Difficulty levels: <span className="text-emerald-400 font-medium">🟢 Easy</span> • <span className="text-amber-400 font-medium">🟡 Medium</span> • <span className="text-rose-400 font-medium">🔴 Hard</span> • Estimated: 15–90 min per topic
                  </p>
                </div>

                <button
                  onClick={handleConfirmStructure}
                  className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/30 transition cursor-pointer self-start sm:self-auto shrink-0 flex items-center gap-1.5"
                >
                  <span>Confirm Structure</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </>
          ); })() : (
            <div className="p-8 text-center text-slate-400 text-xs">
              Select or add a module to view its topics.
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs">
          <div className="rounded-2xl bg-[#0c162e] border border-[#1d2f58] p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400">
              <div className="w-10 h-10 rounded-xl bg-rose-950/60 flex items-center justify-center">
                <Trash2 className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-white m-0">
                Confirm Deletion
              </h4>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed m-0">
              Are you sure you want to delete{' '}
              <strong className="text-white">"{deleteTarget.title}"</strong>
              {deleteTarget.type === 'module' && ' and all of its topics'}?
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 rounded-xl bg-[#111e3b] hover:bg-[#182a52] text-slate-300 text-xs font-medium cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition cursor-pointer shadow-md shadow-rose-600/30"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Split Topic Modal */}
      {splitModalData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs">
          <div className="rounded-2xl bg-[#0c162e] border border-[#1d2f58] p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-blue-400">
              <div className="w-10 h-10 rounded-xl bg-blue-950/60 flex items-center justify-center">
                <Split className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-base font-bold text-white m-0">
                  Split Topic
                </h4>
                <p className="text-[11px] text-slate-400 m-0">
                  Divide into two focused learning topics with balanced study times.
                </p>
              </div>
            </div>

            <div className="space-y-3 pt-1">
              <div>
                <label className="text-xs text-slate-400 font-semibold block mb-1">
                  Topic Part 1 Title:
                </label>
                <input
                  type="text"
                  value={splitModalData.splitTitle1}
                  onChange={(e) =>
                    setSplitModalData({ ...splitModalData, splitTitle1: e.target.value })
                  }
                  className="w-full text-xs text-white bg-[#070e20] border border-[#1b2b52] rounded-xl px-3 py-2 focus:outline-hidden focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 font-semibold block mb-1">
                  Topic Part 2 Title:
                </label>
                <input
                  type="text"
                  value={splitModalData.splitTitle2}
                  onChange={(e) =>
                    setSplitModalData({ ...splitModalData, splitTitle2: e.target.value })
                  }
                  className="w-full text-xs text-white bg-[#070e20] border border-[#1b2b52] rounded-xl px-3 py-2 focus:outline-hidden focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setSplitModalData(null)}
                className="px-4 py-2 rounded-xl bg-[#111e3b] hover:bg-[#182a52] text-slate-300 text-xs font-medium cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmSplit}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition cursor-pointer shadow-md shadow-blue-600/30"
              >
                Split Topic
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Low Confidence Confirmation Modal */}
      {showLowConfidenceModal && validationReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs">
          <div className="rounded-2xl bg-[#0c162e] border border-amber-600/40 p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-amber-400">
              <div className="w-10 h-10 rounded-xl bg-amber-950/60 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h4 className="text-base font-bold text-white m-0">
                  Syllabus Quality Audit Notice
                </h4>
                <p className="text-[11px] text-amber-300/80 m-0">
                  Quality Score: {validationReport.quality_score}/100 • {validationReport.warnings.length} warning(s)
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed m-0">
              Antigravity detected potential issues in the extracted structure (e.g. topic fragments, metadata lines, or duration warnings). We recommend reviewing and merging flagged topics so that YouTube discovery produces the most accurate video matches.
            </p>

            <div className="max-h-40 overflow-y-auto space-y-1.5 p-2.5 rounded-xl bg-[#070e20] border border-[#18284e]">
              {validationReport.warnings.slice(0, 5).map((w, i) => (
                <div key={i} className="text-[11px] text-slate-300 flex items-start gap-1.5">
                  <span className="text-amber-400 shrink-0">•</span>
                  <span>{w.message}</span>
                </div>
              ))}
              {validationReport.warnings.length > 5 && (
                <p className="text-[10px] text-slate-500 m-0 pl-3">
                  +{validationReport.warnings.length - 5} more issues
                </p>
              )}
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setShowLowConfidenceModal(false)}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold cursor-pointer shadow-sm"
              >
                Review & Edit Topics
              </button>
              <button
                onClick={() => {
                  setShowLowConfidenceModal(false);
                  onConfirmTopics();
                }}
                className="px-4 py-2 rounded-xl bg-[#111e3b] hover:bg-[#182a52] text-slate-300 hover:text-white text-xs font-medium cursor-pointer"
              >
                Proceed Anyway
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
