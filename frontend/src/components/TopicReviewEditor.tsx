import React, { useState } from 'react';
import { 
  Sparkles, 
  Save, 
  Plus, 
  Trash2, 
  ChevronDown, 
  ChevronUp, 
  ArrowUp, 
  ArrowDown, 
  AlertTriangle, 
  Clock, 
  Edit3, 
  X, 
  Check, 
  Loader2,
  ArrowRight
} from 'lucide-react';
import type { 
  SyllabusAnalysisResponse, 
  ModuleItem, 
  TopicItem, 
  TopicUpdateRequest 
} from '../types';
import { apiService, ApiErrorResponse } from '../services/api';

interface TopicReviewEditorProps {
  analysisData: SyllabusAnalysisResponse;
  onUpdateSuccess: (updated: SyllabusAnalysisResponse) => void;
  onConfirmTopics: () => void;
}

export const TopicReviewEditor: React.FC<TopicReviewEditorProps> = ({
  analysisData,
  onUpdateSuccess,
  onConfirmTopics,
}) => {
  const [courseName, setCourseName] = useState(analysisData.course_name || 'My Course');
  const [modules, setModules] = useState<ModuleItem[]>(analysisData.modules);
  const [ambiguousSections] = useState<string[]>(analysisData.ambiguous_sections);
  const [expandedTopicIds, setExpandedTopicIds] = useState<Set<string>>(new Set());
  
  // UI states
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  // Deletion Confirmation modal state
  const [deleteTarget, setDeleteTarget] = useState<{
    type: 'module' | 'topic';
    moduleId: string;
    topicId?: string;
    title: string;
  } | null>(null);

  // Toggle expansion of topic details
  const toggleTopicExpand = (topicId: string) => {
    setExpandedTopicIds((prev) => {
      const next = new Set(prev);
      if (next.has(topicId)) {
        next.delete(topicId);
      } else {
        next.add(topicId);
      }
      return next;
    });
  };

  // Module Actions
  const handleAddModule = () => {
    const nextIdx = modules.length + 1;
    const newModId = `mod_custom_${Date.now()}`;
    const newModule: ModuleItem = {
      id: newModId,
      title: `Module ${nextIdx}: New Learning Unit`,
      order_index: modules.length,
      topics: [
        {
          id: `top_custom_${Date.now()}`,
          title: 'Initial Topic',
          explanation: 'Core concept for this module.',
          estimated_minutes: 60,
          difficulty: 'medium',
          prerequisites: [],
          subtopics: [],
          order_index: 0,
        },
      ],
    };
    setModules([...modules, newModule]);
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

    // re-index
    updated.forEach((m, idx) => {
      m.order_index = idx;
    });

    setModules(updated);
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
          title: `New Topic ${nextTopicIdx}`,
          explanation: 'Study objective for this topic.',
          estimated_minutes: 60,
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

  // Execute Deletion
  const confirmDelete = () => {
    if (!deleteTarget) return;

    if (deleteTarget.type === 'module') {
      if (modules.length <= 1) {
        setErrorMessage('A syllabus must contain at least one module.');
        setDeleteTarget(null);
        return;
      }
      setModules((prev) => prev.filter((m) => m.id !== deleteTarget.moduleId));
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

  // Save to Backend
  const handleSave = async () => {
    setIsSaving(true);
    setErrorMessage(null);
    setSaveSuccess(false);

    const payload: TopicUpdateRequest = {
      course_name: courseName,
      modules,
      ambiguous_sections: ambiguousSections,
    };

    try {
      const updated = await apiService.updateSyllabusTopics(analysisData.syllabus_id, payload);
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

  // Metrics
  const totalTopics = modules.reduce((acc, m) => acc + m.topics.length, 0);
  const totalMinutes = modules.reduce(
    (acc, m) => acc + m.topics.reduce((sub, t) => sub + t.estimated_minutes, 0),
    0
  );
  const totalHours = (totalMinutes / 60).toFixed(1);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Banner & Control Bar */}
      <div className="rounded-2xl bg-gradient-to-r from-indigo-950/70 via-slate-900 to-slate-950 border border-indigo-900/40 p-5 sm:p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Phase 2 Topic Hierarchy
              </span>
              {analysisData.is_fallback ? (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  <span>Dev Fallback Mode</span>
                </span>
              ) : (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  <span>Strands Agents SDK</span>
                </span>
              )}
            </div>

            {/* Editable Course Name */}
            <div className="flex items-center gap-2 pt-1">
              <input
                type="text"
                value={courseName}
                onChange={(e) => {
                  setCourseName(e.target.value);
                  setIsDirty(true);
                }}
                className="text-xl sm:text-2xl font-extrabold text-white bg-transparent border-b border-transparent hover:border-slate-700 focus:border-indigo-500 focus:outline-hidden transition px-1 py-0.5 rounded-sm max-w-lg"
                title="Click to edit course name"
              />
              <Edit3 className="w-4 h-4 text-slate-500 shrink-0" />
            </div>
            <p className="text-xs text-slate-400">
              Source: <span className="font-mono text-slate-300">{analysisData.filename}</span> • {analysisData.word_count.toLocaleString()} words
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2.5 self-start sm:self-auto">
            <button
              onClick={handleAddModule}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Add Module</span>
            </button>

            <button
              onClick={handleSave}
              disabled={isSaving}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition cursor-pointer shadow-md ${
                isDirty
                  ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30 animate-pulse'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
              }`}
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : saveSuccess ? (
                <>
                  <Check className="w-4 h-4 text-emerald-400" />
                  <span className="text-emerald-400">Saved</span>
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  <span>{isDirty ? 'Save Changes *' : 'Save Changes'}</span>
                </>
              )}
            </button>

            <button
              onClick={onConfirmTopics}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs sm:text-sm font-medium transition shadow-md shadow-emerald-600/20 cursor-pointer"
            >
              <span>Confirm & Plan</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Metrics Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 uppercase font-semibold">Modules / Units</span>
            <p className="text-lg font-bold text-white mt-0.5 m-0">{modules.length}</p>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 uppercase font-semibold">Total Topics</span>
            <p className="text-lg font-bold text-white mt-0.5 m-0">{totalTopics}</p>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 uppercase font-semibold">Est. Study Load</span>
            <p className="text-lg font-bold text-indigo-300 mt-0.5 m-0">{totalHours} hrs <span className="text-xs text-slate-400">({totalMinutes}m)</span></p>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 uppercase font-semibold">Analysis Engine</span>
            <p className="text-xs font-mono text-slate-300 mt-1 m-0 truncate" title={analysisData.analysis_engine}>
              {analysisData.is_fallback ? 'Dev Fallback' : 'Strands Agent'}
            </p>
          </div>
        </div>
      </div>

      {/* Error or Success Notifications */}
      {errorMessage && (
        <div className="rounded-xl bg-rose-950/40 border border-rose-800 p-4 text-xs text-rose-200 flex items-center justify-between">
          <span>{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-white cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Ambiguous Sections Banner (Human-in-the-loop requirement) */}
      {ambiguousSections.length > 0 && (
        <div className="rounded-2xl bg-amber-950/30 border border-amber-800/60 p-4 sm:p-5 space-y-2">
          <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Syllabus Sections Needing Review:</span>
          </div>
          <ul className="text-xs text-amber-200/90 space-y-1 pl-5 list-disc m-0">
            {ambiguousSections.map((sec, idx) => (
              <li key={idx} className="leading-relaxed">
                {sec}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Modules & Topics List */}
      <div className="space-y-5">
        {modules.map((module, mIdx) => (
          <div
            key={module.id}
            className="rounded-2xl bg-slate-900/70 border border-slate-800 overflow-hidden shadow-sm"
          >
            {/* Module Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 py-3.5 bg-slate-950/80 border-b border-slate-800/80">
              <div className="flex items-center gap-2.5 flex-1 min-w-0">
                <span className="w-6 h-6 rounded-lg bg-indigo-600/20 text-indigo-400 font-bold text-xs flex items-center justify-center shrink-0">
                  {mIdx + 1}
                </span>
                <input
                  type="text"
                  value={module.title}
                  onChange={(e) => handleUpdateModuleTitle(module.id, e.target.value)}
                  className="font-bold text-sm sm:text-base text-white bg-transparent border-b border-transparent hover:border-slate-700 focus:border-indigo-500 focus:outline-hidden px-1.5 py-0.5 rounded-sm transition flex-1 min-w-0"
                  title="Click to edit unit title"
                />
              </div>

              {/* Module Reorder & Delete Controls */}
              <div className="flex items-center gap-1.5 self-end sm:self-auto shrink-0">
                <span className="text-xs text-slate-400 font-medium mr-2">
                  {module.topics.length} topic{module.topics.length !== 1 ? 's' : ''}
                </span>

                <button
                  onClick={() => handleMoveModule(mIdx, 'up')}
                  disabled={mIdx === 0}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 cursor-pointer"
                  title="Move module up"
                >
                  <ArrowUp className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleMoveModule(mIdx, 'down')}
                  disabled={mIdx === modules.length - 1}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 cursor-pointer"
                  title="Move module down"
                >
                  <ArrowDown className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleAddTopic(module.id)}
                  className="p-1.5 rounded-lg text-indigo-400 hover:text-indigo-300 hover:bg-indigo-950/50 cursor-pointer"
                  title="Add topic to this module"
                >
                  <Plus className="w-4 h-4" />
                </button>
                <button
                  onClick={() =>
                    setDeleteTarget({
                      type: 'module',
                      moduleId: module.id,
                      title: module.title,
                    })
                  }
                  className="p-1.5 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-950/50 cursor-pointer"
                  title="Delete module"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Topics inside Module */}
            <div className="p-4 space-y-3">
              {module.topics.length === 0 ? (
                <div className="p-4 rounded-xl border border-dashed border-slate-800 text-center text-xs text-slate-500">
                  No topics in this unit yet.{' '}
                  <button
                    onClick={() => handleAddTopic(module.id)}
                    className="text-indigo-400 underline hover:text-indigo-300 cursor-pointer"
                  >
                    Add a topic
                  </button>
                </div>
              ) : (
                module.topics.map((topic, tIdx) => {
                  const isExpanded = expandedTopicIds.has(topic.id);

                  return (
                    <div
                      key={topic.id}
                      className="rounded-xl bg-slate-950/50 border border-slate-800/80 transition-all hover:border-slate-700/80"
                    >
                      {/* Topic Summary Row */}
                      <div className="flex items-center justify-between p-3 gap-3">
                        {/* Topic Order & Title */}
                        <div className="flex items-center gap-2.5 flex-1 min-w-0">
                          <div className="flex flex-col text-slate-500 shrink-0">
                            <button
                              onClick={() => handleMoveTopic(module.id, tIdx, 'up')}
                              disabled={tIdx === 0}
                              className="hover:text-white disabled:opacity-20 cursor-pointer p-0.5"
                            >
                              <ChevronUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleMoveTopic(module.id, tIdx, 'down')}
                              disabled={tIdx === module.topics.length - 1}
                              className="hover:text-white disabled:opacity-20 cursor-pointer p-0.5"
                            >
                              <ChevronDown className="w-3.5 h-3.5" />
                            </button>
                          </div>

                          <span className="text-xs text-slate-500 font-mono shrink-0">
                            {mIdx + 1}.{tIdx + 1}
                          </span>

                          <input
                            type="text"
                            value={topic.title}
                            onChange={(e) =>
                              handleUpdateTopic(module.id, topic.id, {
                                title: e.target.value,
                              })
                            }
                            className="text-xs sm:text-sm font-semibold text-slate-200 bg-transparent border-b border-transparent hover:border-slate-700 focus:border-indigo-500 focus:outline-hidden px-1.5 py-0.5 rounded-sm transition flex-1 min-w-0"
                            title="Click to edit topic title"
                          />
                        </div>

                        {/* Metadata badges: Difficulty & Estimated Minutes */}
                        <div className="flex items-center gap-2 shrink-0">
                          {/* Difficulty Selector */}
                          <select
                            value={topic.difficulty}
                            onChange={(e) =>
                              handleUpdateTopic(module.id, topic.id, {
                                difficulty: e.target.value as any,
                              })
                            }
                            className={`text-[11px] font-medium rounded-lg px-2 py-0.5 border cursor-pointer focus:outline-hidden ${
                              topic.difficulty === 'easy'
                                ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60'
                                : topic.difficulty === 'hard'
                                ? 'bg-rose-950/40 text-rose-300 border-rose-800/60'
                                : 'bg-indigo-950/40 text-indigo-300 border-indigo-800/60'
                            }`}
                          >
                            <option value="easy">Easy</option>
                            <option value="medium">Medium</option>
                            <option value="hard">Hard</option>
                          </select>

                          {/* Est Minutes input */}
                          <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg px-2 py-0.5 text-[11px] text-slate-300">
                            <Clock className="w-3 h-3 text-slate-500" />
                            <input
                              type="number"
                              min={15}
                              max={240}
                              step={15}
                              value={topic.estimated_minutes}
                              onChange={(e) =>
                                handleUpdateTopic(module.id, topic.id, {
                                  estimated_minutes: Number(e.target.value) || 60,
                                })
                              }
                              className="w-8 text-center bg-transparent focus:outline-hidden text-white font-mono"
                            />
                            <span className="text-slate-500">m</span>
                          </div>

                          {/* Expand details toggle */}
                          <button
                            onClick={() => toggleTopicExpand(topic.id)}
                            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 cursor-pointer"
                            title={isExpanded ? 'Collapse details' : 'Expand details'}
                          >
                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4" />
                            ) : (
                              <ChevronDown className="w-4 h-4" />
                            )}
                          </button>

                          {/* Delete Topic button */}
                          <button
                            onClick={() =>
                              setDeleteTarget({
                                type: 'topic',
                                moduleId: module.id,
                                topicId: topic.id,
                                title: topic.title,
                              })
                            }
                            className="p-1 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-slate-800 cursor-pointer"
                            title="Delete topic"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Topic Expanded Details */}
                      {isExpanded && (
                        <div className="px-4 pb-4 pt-1 border-t border-slate-900/80 space-y-3 text-xs bg-slate-950/20">
                          {/* Explanation */}
                          <div className="space-y-1">
                            <label className="text-[11px] text-slate-400 font-semibold">
                              Topic Explanation & Learning Objective:
                            </label>
                            <textarea
                              rows={2}
                              value={topic.explanation}
                              onChange={(e) =>
                                handleUpdateTopic(module.id, topic.id, {
                                  explanation: e.target.value,
                                })
                              }
                              className="w-full text-xs text-slate-300 bg-slate-900/80 border border-slate-800 rounded-xl p-2.5 focus:outline-hidden focus:border-indigo-500 leading-relaxed"
                            />
                          </div>

                          {/* Prerequisites & Source Evidence */}
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div className="space-y-1">
                              <label className="text-[11px] text-slate-400 font-semibold">
                                Prerequisites (comma separated):
                              </label>
                              <input
                                type="text"
                                value={topic.prerequisites.join(', ')}
                                onChange={(e) =>
                                  handleUpdateTopic(module.id, topic.id, {
                                    prerequisites: e.target.value
                                      .split(',')
                                      .map((p) => p.trim())
                                      .filter(Boolean),
                                  })
                                }
                                placeholder="e.g. Basic Calculus, Arrays"
                                className="w-full text-xs text-slate-300 bg-slate-900/80 border border-slate-800 rounded-xl px-3 py-1.5 focus:outline-hidden focus:border-indigo-500"
                              />
                            </div>

                            {topic.source_evidence && (
                              <div className="space-y-1">
                                <label className="text-[11px] text-slate-400 font-semibold">
                                  Source Evidence from Syllabus:
                                </label>
                                <p className="text-xs italic text-slate-400 bg-slate-900/50 border border-slate-800/80 rounded-xl p-2 m-0 truncate">
                                  "{topic.source_evidence}"
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Confirmation Modal for Deletion */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 max-w-md w-full space-y-4 shadow-2xl">
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
              {deleteTarget.type === 'module' && ' and all of its topics'}? This action can be canceled or re-saved.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium cursor-pointer"
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
    </div>
  );
};
