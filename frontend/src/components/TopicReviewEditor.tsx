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
  ChevronRight
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
  onViewSource?: () => void;
}

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

  // Active Module
  const activeModule = modules.find((m) => m.id === activeModuleId) || modules[0];

  // Module Actions
  const handleAddModule = () => {
    const nextIdx = modules.length + 1;
    const newModId = `mod_custom_${Date.now()}`;
    const newModule: ModuleItem = {
      id: newModId,
      title: `Module ${nextIdx}: New Unit`,
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
      setModules(remaining);
      if (activeModuleId === deleteTarget.moduleId && remaining[0]) {
        setActiveModuleId(remaining[0].id);
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

  // Save changes to SQLite backend
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
          {analysisData.is_fallback ? (
            <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3 text-amber-400" />
              <span>Dev Fallback Mode</span>
            </span>
          ) : (
            <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5">
              <Sparkles className="w-3 h-3 text-emerald-400" />
              <span>Strands Agents Verified</span>
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

      {/* Ambiguous Sections Alert */}
      {ambiguousSections.length > 0 && (
        <div className="rounded-2xl bg-amber-950/20 border border-amber-800/40 p-4 space-y-1.5">
          <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Syllabus Notes / Ambiguities:</span>
          </div>
          <ul className="text-xs text-amber-200/90 space-y-1 pl-5 list-disc m-0">
            {ambiguousSections.map((sec, idx) => (
              <li key={idx} className="leading-relaxed">{sec}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Two-Pane Layout (Matches Screen 4 Exactly) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Pane: Module List (4 cols) */}
        <div className="lg:col-span-5 space-y-2.5">
          <div className="space-y-2">
            {modules.map((mod, mIdx) => {
              const isSelected = mod.id === activeModule?.id;
              const modMinutes = mod.topics.reduce((acc, t) => acc + t.estimated_minutes, 0);

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
                    <p className={`text-xs font-bold truncate m-0 ${isSelected ? 'text-white' : 'text-slate-200'}`}>
                      {mod.title}
                    </p>
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
          {activeModule ? (
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
                  <p className="text-[11px] text-slate-400 mt-0.5 m-0 px-1">
                    {activeModule.topics.length} topics • {activeModule.topics.reduce((acc, t) => acc + t.estimated_minutes, 0)} min
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
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
                            <span className="w-5 h-5 rounded-md bg-[#111e3b] text-slate-400 text-[11px] font-mono flex items-center justify-center shrink-0">
                              {tIdx + 1}
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
                  onClick={onConfirmTopics}
                  className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/30 transition cursor-pointer self-start sm:self-auto shrink-0 flex items-center gap-1.5"
                >
                  <span>Confirm Structure</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </>
          ) : (
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
    </div>
  );
};
