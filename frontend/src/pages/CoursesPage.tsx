import React, { useState } from 'react';
import { 
  GraduationCap, 
  Plus, 
  Calendar, 
  BookOpen, 
  MoreVertical, 
  Edit3, 
  RefreshCw, 
  Archive, 
  Trash2, 
  CheckCircle2, 
  AlertTriangle, 
  ArrowRight, 
  FileText, 
  X
} from 'lucide-react';
import type { Course, NavigationTab } from '../types';
import { apiService } from '../services/api';

interface CoursesPageProps {
  courses: Course[];
  activeCourseId: string | null;
  onSelectCourse: (course: Course) => void;
  onOpenUploadWizard: () => void;
  onRefreshCourses: (deletedCourseId?: string) => Promise<void>;
  onNavigate: (tab: NavigationTab) => void;
}

export const CoursesPage: React.FC<CoursesPageProps> = ({
  courses,
  activeCourseId,
  onSelectCourse,
  onOpenUploadWizard,
  onRefreshCourses,
  onNavigate,
}) => {
  const [activeTab, setActiveTab] = useState<'active' | 'archived'>('active');
  const [selectedMenuCourseId, setSelectedMenuCourseId] = useState<string | null>(null);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [replacingCourse, setReplacingCourse] = useState<Course | null>(null);
  const [deletingCourse, setDeletingCourse] = useState<Course | null>(null);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [replacementFile, setReplacementFile] = useState<File | null>(null);

  const displayedCourses = courses.filter((c) => 
    activeTab === 'archived' ? c.is_archived : !c.is_archived
  );

  const activeCount = courses.filter((c) => !c.is_archived).length;
  const archivedCount = courses.filter((c) => c.is_archived).length;

  const handleOpenCourse = (c: Course) => {
    onSelectCourse(c);
    onNavigate('syllabus');
  };

  const handleArchiveToggle = async (c: Course) => {
    setIsActionLoading(true);
    setActionError(null);
    try {
      await apiService.archiveCourse(c.id, !c.is_archived);
      await onRefreshCourses();
      setSelectedMenuCourseId(null);
    } catch (err: any) {
      setActionError(err.message || 'Failed to update course archive status.');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleDeleteCourse = async () => {
    if (!deletingCourse) return;
    const targetCourse = deletingCourse;
    setIsActionLoading(true);
    setActionError(null);
    try {
      await apiService.deleteCourse(targetCourse.id);
      setDeletingCourse(null);
      await onRefreshCourses(targetCourse.id);
    } catch (err: any) {
      setActionError(err.message || 'Failed to delete course.');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleUpdateCourseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCourse) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      await apiService.updateCourse(editingCourse.id, {
        course_name: editingCourse.course_name,
        course_code: editingCourse.course_code,
        language: editingCourse.language,
        lesson_style: editingCourse.lesson_style,
        daily_study_availability: editingCourse.daily_study_availability,
      });
      await onRefreshCourses();
      setEditingCourse(null);
    } catch (err: any) {
      setActionError(err.message || 'Failed to update course info.');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleReplaceSyllabusSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replacingCourse || !replacementFile) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      // 1. Upload new document
      const uploadRes = await apiService.uploadSyllabus(replacementFile);
      if (!uploadRes.syllabus_id) {
        throw new Error('Upload succeeded but no syllabus ID was returned.');
      }
      // 2. Replace syllabus in course
      await apiService.replaceCourseSyllabus(replacingCourse.id, uploadRes.syllabus_id, true);
      await onRefreshCourses();
      setReplacingCourse(null);
      setReplacementFile(null);
    } catch (err: any) {
      setActionError(err.message || 'Failed to replace syllabus.');
    } finally {
      setIsActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#152342]">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <GraduationCap className="w-7 h-7 text-blue-400" />
            My Courses & Syllabi
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage your courses, view progress milestones, and keep independent study timetables.
          </p>
        </div>

        <button
          onClick={onOpenUploadWizard}
          className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-lg shadow-blue-600/30 flex items-center justify-center gap-2 transition cursor-pointer self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          Add New Course
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex bg-[#0c162e] p-1 rounded-2xl border border-[#1b2b52] text-xs">
          <button
            onClick={() => setActiveTab('active')}
            className={`px-4 py-1.5 rounded-xl font-medium transition cursor-pointer ${
              activeTab === 'active'
                ? 'bg-blue-600 text-white font-semibold shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Active Courses ({activeCount})
          </button>
          <button
            onClick={() => setActiveTab('archived')}
            className={`px-4 py-1.5 rounded-xl font-medium transition cursor-pointer ${
              activeTab === 'archived'
                ? 'bg-blue-600 text-white font-semibold shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Archived ({archivedCount})
          </button>
        </div>
      </div>

      {actionError && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Courses Grid */}
      {displayedCourses.length === 0 ? (
        <div className="p-12 text-center rounded-3xl bg-[#0c162e] border border-[#1b2b52] space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-blue-600/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mx-auto">
            <BookOpen className="w-8 h-8" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-white">
              {activeTab === 'archived' ? 'No Archived Courses' : 'No Enrolled Courses Yet'}
            </h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              {activeTab === 'archived'
                ? 'Archived courses will appear here when you no longer actively study them.'
                : 'Upload your first syllabus document to set up your subjects and personalized study roadmaps.'}
            </p>
          </div>
          {activeTab === 'active' && (
            <button
              onClick={onOpenUploadWizard}
              className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white inline-flex items-center gap-2 transition cursor-pointer shadow-lg shadow-blue-600/30"
            >
              <Plus className="w-4 h-4" />
              Upload Course Syllabus
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {displayedCourses.map((c) => {
            const isActive = c.id === activeCourseId;
            return (
              <div
                key={c.id}
                className={`relative rounded-3xl bg-[#0c162e] border transition-all duration-200 flex flex-col overflow-hidden ${
                  isActive
                    ? 'border-blue-500/80 shadow-xl shadow-blue-900/20 ring-1 ring-blue-500/50'
                    : 'border-[#1b2b52] hover:border-slate-600 hover:shadow-lg'
                }`}
              >
                {/* Active indicator badge */}
                {isActive && (
                  <div className="absolute top-0 right-0 bg-blue-600 text-white text-[10px] font-bold px-3 py-1 rounded-bl-xl tracking-wider uppercase">
                    Active Selected
                  </div>
                )}

                <div className="p-5 flex-1 space-y-4">
                  {/* Top Bar: Code & Menu */}
                  <div className="flex items-start justify-between gap-2 pr-14">
                    <div className="flex flex-wrap items-center gap-2">
                      {c.course_code ? (
                        <span className="px-2.5 py-1 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 text-xs font-mono font-bold">
                          {c.course_code}
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 text-[10px] font-mono">
                          COURSE
                        </span>
                      )}
                      <span className="text-[11px] text-slate-400">{c.language}</span>
                    </div>

                    <div className="relative">
                      <button
                        onClick={() => setSelectedMenuCourseId(selectedMenuCourseId === c.id ? null : c.id)}
                        className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-[#152342] transition cursor-pointer"
                        title="Course options"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </button>

                      {/* Dropdown Menu */}
                      {selectedMenuCourseId === c.id && (
                        <div className="absolute right-0 top-7 w-48 rounded-2xl bg-[#091122] border border-[#1b2b52] shadow-2xl py-1.5 z-30 text-xs space-y-0.5">
                          <button
                            onClick={() => {
                              setEditingCourse(c);
                              setSelectedMenuCourseId(null);
                            }}
                            className="w-full px-3 py-2 text-left text-slate-300 hover:text-white hover:bg-[#152342] flex items-center gap-2 transition cursor-pointer"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                            Edit Course Details
                          </button>
                          <button
                            onClick={() => {
                              setReplacingCourse(c);
                              setSelectedMenuCourseId(null);
                            }}
                            className="w-full px-3 py-2 text-left text-slate-300 hover:text-white hover:bg-[#152342] flex items-center gap-2 transition cursor-pointer"
                          >
                            <RefreshCw className="w-3.5 h-3.5" />
                            Replace Syllabus PDF
                          </button>
                          <button
                            onClick={() => handleArchiveToggle(c)}
                            className="w-full px-3 py-2 text-left text-slate-300 hover:text-white hover:bg-[#152342] flex items-center gap-2 transition cursor-pointer"
                          >
                            <Archive className="w-3.5 h-3.5" />
                            {c.is_archived ? 'Unarchive Course' : 'Archive Course'}
                          </button>
                          <div className="border-t border-[#1b2b52] my-1" />
                          <button
                            onClick={() => {
                              setDeletingCourse(c);
                              setSelectedMenuCourseId(null);
                            }}
                            className="w-full px-3 py-2 text-left text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 flex items-center gap-2 transition cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Delete Course
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Course Name */}
                  <div className="space-y-1">
                    <h3 className="text-base font-bold text-white line-clamp-2 leading-snug">
                      {c.course_name}
                    </h3>
                    {c.filename && (
                      <p className="text-[11px] text-slate-400 flex items-center gap-1.5 truncate">
                        <FileText className="w-3.5 h-3.5 shrink-0 text-slate-500" />
                        <span className="truncate">{c.filename}</span>
                      </p>
                    )}
                  </div>

                  {/* Progress Bar */}
                  <div className="space-y-1.5 pt-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">Study Progress</span>
                      <span className="font-bold text-blue-400">{c.progress_percentage}%</span>
                    </div>
                    <div className="h-2 w-full bg-[#070b14] rounded-full overflow-hidden border border-[#1b2b52]">
                      <div
                        className="h-full bg-gradient-to-r from-blue-600 to-indigo-500 rounded-full transition-all duration-300"
                        style={{ width: `${Math.min(100, Math.max(0, c.progress_percentage))}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>{c.completed_tasks} tasks completed</span>
                      <span>{c.total_topics} topics</span>
                    </div>
                  </div>

                  {/* Next Assessment Chip */}
                  {c.next_assessment ? (
                    <div className="p-2.5 rounded-xl bg-[#070b14] border border-[#1b2b52] flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                        <span className="text-slate-200 font-medium truncate">{c.next_assessment.name}</span>
                      </div>
                      <span className="text-blue-400 font-mono text-[11px] font-semibold shrink-0">
                        {c.next_assessment.days_remaining >= 0 ? `in ${c.next_assessment.days_remaining}d` : 'Passed'}
                      </span>
                    </div>
                  ) : (
                    <div className="p-2.5 rounded-xl bg-[#070b14] border border-[#1b2b52] text-xs text-slate-400 flex items-center gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Assessments on schedule</span>
                    </div>
                  )}

                  {/* Preferences chips */}
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-slate-400">
                    <span className="px-2 py-0.5 rounded-lg bg-[#070b14] border border-[#1b2b52]">
                      {c.daily_study_availability}
                    </span>
                    <span className="px-2 py-0.5 rounded-lg bg-[#070b14] border border-[#1b2b52]">
                      {c.lesson_style}
                    </span>
                  </div>
                </div>

                {/* Card Action Footer */}
                <div className="p-3.5 bg-[#081023] border-t border-[#152342] flex items-center gap-2">
                  <button
                    onClick={() => handleOpenCourse(c)}
                    className="flex-1 py-2 px-3 rounded-xl bg-blue-600/20 hover:bg-blue-600 text-blue-300 hover:text-white border border-blue-500/30 text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer"
                  >
                    Open Course
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setReplacingCourse(c)}
                    className="py-2 px-3 rounded-xl bg-[#0f1b36] hover:bg-[#16274e] text-slate-300 hover:text-white border border-[#1b2b52] text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer"
                    title="Replace syllabus document for this course"
                  >
                    <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
                    <span>Replace</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Edit Course Details Modal */}
      {editingCourse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#091122] border border-[#1b2b52] rounded-3xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Edit Course Info</h3>
              <button onClick={() => setEditingCourse(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateCourseSubmit} className="space-y-3.5">
              <div className="space-y-1">
                <label className="text-xs text-slate-300">Course Name</label>
                <input
                  type="text"
                  value={editingCourse.course_name}
                  onChange={(e) => setEditingCourse({ ...editingCourse, course_name: e.target.value })}
                  required
                  className="w-full px-3 py-2 rounded-xl bg-[#0c162e] border border-[#1b2b52] text-xs text-white"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs text-slate-300">Course Code</label>
                <input
                  type="text"
                  value={editingCourse.course_code || ''}
                  onChange={(e) => setEditingCourse({ ...editingCourse, course_code: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-[#0c162e] border border-[#1b2b52] text-xs text-white uppercase"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs text-slate-300">Daily Study Availability</label>
                <select
                  value={editingCourse.daily_study_availability}
                  onChange={(e) => setEditingCourse({ ...editingCourse, daily_study_availability: e.target.value as any })}
                  className="w-full px-3 py-2 rounded-xl bg-[#0c162e] border border-[#1b2b52] text-xs text-white"
                >
                  <option value="30-60 minutes">30–60 minutes</option>
                  <option value="1-2 hours">1–2 hours</option>
                  <option value="2-4 hours">2–4 hours</option>
                  <option value="4+ hours">4+ hours</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-xs text-slate-300">Lesson Style</label>
                <select
                  value={editingCourse.lesson_style}
                  onChange={(e) => setEditingCourse({ ...editingCourse, lesson_style: e.target.value as any })}
                  className="w-full px-3 py-2 rounded-xl bg-[#0c162e] border border-[#1b2b52] text-xs text-white"
                >
                  <option value="Beginner-friendly">Beginner-friendly</option>
                  <option value="In-depth">In-depth</option>
                  <option value="Fast-paced">Fast-paced</option>
                  <option value="Practical">Practical</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingCourse(null)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isActionLoading}
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-md cursor-pointer"
                >
                  {isActionLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Replace Syllabus PDF Modal */}
      {replacingCourse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#091122] border border-[#1b2b52] rounded-3xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Replace Syllabus Document</h3>
              <button onClick={() => setReplacingCourse(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3.5 rounded-2xl bg-blue-600/10 border border-blue-500/20 text-blue-300 text-xs space-y-1.5">
              <p className="font-semibold text-white">Topic Completion Preservation Guarantee</p>
              <p className="text-[11px] text-slate-300">
                Uploading a replacement syllabus re-analyzes the document. Completed status and personal notes for topics matching existing topic titles will be safely preserved.
              </p>
            </div>

            <form onSubmit={handleReplaceSyllabusSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs text-slate-300">Select New PDF / DOCX</label>
                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={(e) => setReplacementFile(e.target.files?.[0] || null)}
                  required
                  className="w-full px-3 py-2 rounded-xl bg-[#0c162e] border border-[#1b2b52] text-xs text-slate-300 file:mr-2 file:py-1 file:px-2.5 file:rounded-lg file:border-0 file:bg-blue-600 file:text-white file:text-xs"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setReplacingCourse(null)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!replacementFile || isActionLoading}
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-md disabled:opacity-50 cursor-pointer"
                >
                  {isActionLoading ? 'Replacing...' : 'Confirm & Re-analyze'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Course Confirmation Modal */}
      {deletingCourse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#091122] border border-[#1b2b52] rounded-3xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-400">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <h3 className="text-base font-bold text-white">Delete Course?</h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Are you sure you want to delete <span className="font-semibold text-white">"{deletingCourse.course_name}"</span>? 
              This will permanently remove all associated syllabus modules, daily tasks, study notes, and video associations. This action cannot be undone.
            </p>

            {actionError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
                <span>{actionError}</span>
                <button type="button" onClick={() => setActionError(null)} className="text-slate-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setDeletingCourse(null)}
                className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteCourse}
                disabled={isActionLoading}
                className="px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white shadow-md cursor-pointer"
              >
                {isActionLoading ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
