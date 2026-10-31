import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Clock, 
  GraduationCap, 
  CheckCircle2, 
  AlertCircle, 
  Plus, 
  Trash2, 
  X,
  Languages,
  HelpCircle
} from 'lucide-react';
import type { SyllabusUploadResponse, AssessmentCreate } from '../types';

interface SyllabusSetupWizardProps {
  isOpen: boolean;
  uploadedSyllabus: SyllabusUploadResponse | null;
  onClose: () => void;
  onSubmit: (wizardData: {
    syllabus_id: string;
    course_name: string;
    course_code: string;
    language: string;
    lesson_style: 'Beginner-friendly' | 'In-depth' | 'Fast-paced' | 'Practical';
    daily_study_availability: '30-60 minutes' | '1-2 hours' | '2-4 hours' | '4+ hours';
    assessment_system_type: 'autonomous' | 'university' | 'custom';
    assessment_scope: 'internal' | 'end_sem' | 'both';
    assessments: AssessmentCreate[];
  }) => Promise<void>;
  isAnalyzing: boolean;
  analysisStep: number;
}

const getFutureDate = (daysFromNow: number): string => {
  const d = new Date();
  d.setDate(d.getDate() + daysFromNow);
  return d.toISOString().split('T')[0];
};

const getTodayString = (): string => {
  return new Date().toISOString().split('T')[0];
};

export const SyllabusSetupWizard: React.FC<SyllabusSetupWizardProps> = ({
  isOpen,
  uploadedSyllabus,
  onClose,
  onSubmit,
  isAnalyzing,
  analysisStep,
}) => {
  const todayStr = getTodayString();

  const [courseName, setCourseName] = useState(
    uploadedSyllabus?.course_name_suggestion || 
    uploadedSyllabus?.filename.replace(/\.[^/.]+$/, '').replace(/_/g, ' ') || 
    'Course Syllabus'
  );
  const [courseCode, setCourseCode] = useState(uploadedSyllabus?.course_code_suggestion || '');
  const [language, setLanguage] = useState('English');
  const [lessonStyle, setLessonStyle] = useState<'Beginner-friendly' | 'In-depth' | 'Fast-paced' | 'Practical'>('In-depth');
  const [availability, setAvailability] = useState<'30-60 minutes' | '1-2 hours' | '2-4 hours' | '4+ hours'>('2-4 hours');
  const [patternType, setPatternType] = useState<'autonomous' | 'university' | 'custom'>('autonomous');
  const [assessmentScope, setAssessmentScope] = useState<'internal' | 'end_sem' | 'both'>('both');
  const [dateError, setDateError] = useState<string | null>(null);

  // Sync suggestion whenever uploadedSyllabus changes
  useEffect(() => {
    if (uploadedSyllabus) {
      if (uploadedSyllabus.course_name_suggestion) {
        setCourseName(uploadedSyllabus.course_name_suggestion);
      } else if (uploadedSyllabus.filename) {
        setCourseName(uploadedSyllabus.filename.replace(/\.[^/.]+$/, '').replace(/_/g, ' '));
      }
      if (uploadedSyllabus.course_code_suggestion) {
        setCourseCode(uploadedSyllabus.course_code_suggestion);
      }
    }
  }, [uploadedSyllabus]);

  // Initialize assessment templates
  const [assessments, setAssessments] = useState<AssessmentCreate[]>([
    { name: 'Continuous Assessment 1 (CA1)', exam_date: getFutureDate(21), assessment_type: 'internal', scope: 'internal', weightage: 20, order_index: 0 },
    { name: 'Continuous Assessment 2 (CA2)', exam_date: getFutureDate(45), assessment_type: 'internal', scope: 'internal', weightage: 20, order_index: 1 },
    { name: 'End-Semester Final Examination', exam_date: getFutureDate(75), assessment_type: 'end_sem', scope: 'end_sem', weightage: 60, order_index: 2 },
  ]);

  if (!isOpen || !uploadedSyllabus) return null;

  const handlePatternChange = (type: 'autonomous' | 'university' | 'custom') => {
    setPatternType(type);
    setDateError(null);
    if (type === 'autonomous') {
      setAssessments([
        { name: 'Continuous Assessment 1 (CA1)', exam_date: getFutureDate(21), assessment_type: 'internal', scope: 'internal', weightage: 20, order_index: 0 },
        { name: 'Continuous Assessment 2 (CA2)', exam_date: getFutureDate(45), assessment_type: 'internal', scope: 'internal', weightage: 20, order_index: 1 },
        { name: 'End-Semester Final Examination', exam_date: getFutureDate(75), assessment_type: 'end_sem', scope: 'end_sem', weightage: 60, order_index: 2 },
      ]);
    } else if (type === 'university') {
      setAssessments([
        { name: 'Internal Assessment 1 (IA1)', exam_date: getFutureDate(25), assessment_type: 'internal', scope: 'internal', weightage: 20, order_index: 0 },
        { name: 'Mid-Semester Exam', exam_date: getFutureDate(50), assessment_type: 'mid_sem', scope: 'internal', weightage: 30, order_index: 1 },
        { name: 'University End-Sem Exam', exam_date: getFutureDate(80), assessment_type: 'end_sem', scope: 'end_sem', weightage: 50, order_index: 2 },
      ]);
    } else {
      setAssessments([
        { name: 'Midterm Milestone', exam_date: getFutureDate(35), assessment_type: 'mid_sem', scope: 'internal', weightage: 40, order_index: 0 },
        { name: 'Final Exam', exam_date: getFutureDate(70), assessment_type: 'end_sem', scope: 'end_sem', weightage: 60, order_index: 1 },
      ]);
    }
  };

  const handleAddAssessment = () => {
    const nextOrder = assessments.length;
    setAssessments([
      ...assessments,
      {
        name: `Assessment Milestone ${nextOrder + 1}`,
        exam_date: getFutureDate(30 + nextOrder * 20),
        assessment_type: 'custom',
        scope: 'both',
        weightage: 10,
        order_index: nextOrder,
      },
    ]);
  };

  const handleRemoveAssessment = (index: number) => {
    if (assessments.length <= 1) return;
    setAssessments(assessments.filter((_, idx) => idx !== index));
  };

  const handleUpdateAssessment = (index: number, field: keyof AssessmentCreate, val: any) => {
    setDateError(null);
    const updated = [...assessments];
    updated[index] = { ...updated[index], [field]: val };
    setAssessments(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setDateError(null);

    // Validate future dates
    for (const a of assessments) {
      if (!a.exam_date) {
        setDateError(`Please enter a valid exam date for "${a.name}".`);
        return;
      }
      if (a.exam_date < todayStr) {
        setDateError(`Exam date for "${a.name}" cannot be in the past. Please select a future date.`);
        return;
      }
    }

    if (!courseName.trim()) {
      setDateError('Please provide a course name.');
      return;
    }

    await onSubmit({
      syllabus_id: uploadedSyllabus.syllabus_id || '',
      course_name: courseName.trim(),
      course_code: courseCode.trim(),
      language,
      lesson_style: lessonStyle,
      daily_study_availability: availability,
      assessment_system_type: patternType,
      assessment_scope: assessmentScope,
      assessments,
    });
  };

  const analysisSteps = [
    'Parsing syllabus structure & modules',
    'Extracting discrete topics & estimated hours',
    'Evaluating educational coherence',
    'Configuring assessment milestones roadmap',
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-[#091122] border border-[#1b2b52] rounded-3xl shadow-2xl overflow-hidden my-6">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4.5 border-b border-[#152342] bg-[#0c162e]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Pre-Analysis Course Setup</h2>
              <p className="text-xs text-slate-400">Personalize study roadmap before starting AI analysis</p>
            </div>
          </div>
          {!isAnalyzing && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#152342] transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {isAnalyzing ? (
          <div className="p-10 flex flex-col items-center justify-center text-center space-y-6">
            <div className="relative w-20 h-20">
              <div className="absolute inset-0 rounded-full border-4 border-blue-500/20 animate-ping" />
              <div className="w-20 h-20 rounded-full border-4 border-t-blue-500 border-r-blue-400 border-b-transparent border-l-transparent animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-blue-400 animate-pulse" />
              </div>
            </div>

            <div className="space-y-2 max-w-md">
              <h3 className="text-lg font-bold text-white">Analyzing Syllabus & Building Roadmap...</h3>
              <p className="text-xs text-slate-400">
                Strands Agent is extracting modules, topics, and structuring your milestone schedule.
              </p>
            </div>

            {/* Stepper */}
            <div className="w-full max-w-md space-y-2 text-left bg-[#0c162e] p-4 rounded-2xl border border-[#1b2b52]">
              {analysisSteps.map((step, idx) => {
                const isDone = analysisStep > idx + 1;
                const isCurr = analysisStep === idx + 1;
                return (
                  <div key={idx} className="flex items-center gap-3 text-xs">
                    {isDone ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : isCurr ? (
                      <div className="w-4 h-4 rounded-full border-2 border-t-blue-400 border-r-transparent animate-spin shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-slate-700 shrink-0" />
                    )}
                    <span className={isDone ? 'text-slate-300' : isCurr ? 'text-blue-400 font-semibold' : 'text-slate-500'}>
                      {step}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
            {/* Step 1: Course Identification */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-blue-600/30 text-blue-400 text-xs font-bold flex items-center justify-center">1</span>
                <h3 className="text-sm font-semibold text-white">Course Identity</h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2 space-y-1">
                  <label className="text-[11px] font-medium text-slate-300">Course / Subject Name</label>
                  <input
                    type="text"
                    value={courseName}
                    onChange={(e) => setCourseName(e.target.value)}
                    required
                    placeholder="e.g. Object Oriented Modelling and Design"
                    className="w-full px-3.5 py-2 rounded-xl bg-[#0d172e] border border-[#1b2b52] text-xs text-white placeholder-slate-500 focus:outline-hidden focus:border-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-slate-300">Course Code</label>
                  <input
                    type="text"
                    value={courseCode}
                    onChange={(e) => setCourseCode(e.target.value)}
                    placeholder="e.g. CSE3016"
                    className="w-full px-3.5 py-2 rounded-xl bg-[#0d172e] border border-[#1b2b52] text-xs text-white placeholder-slate-500 focus:outline-hidden focus:border-blue-500 uppercase"
                  />
                </div>
              </div>
            </div>

            {/* Step 2: Learning Preferences */}
            <div className="space-y-3 pt-2 border-t border-[#152342]">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-blue-600/30 text-blue-400 text-xs font-bold flex items-center justify-center">2</span>
                <h3 className="text-sm font-semibold text-white">Learning Preferences</h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Language */}
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-slate-300 flex items-center gap-1.5">
                    <Languages className="w-3.5 h-3.5 text-blue-400" />
                    Preferred Content Language
                  </label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl bg-[#0d172e] border border-[#1b2b52] text-xs text-white focus:outline-hidden focus:border-blue-500"
                  >
                    <option value="English">English</option>
                    <option value="Hindi">Hindi (हिंदी)</option>
                    <option value="Spanish">Spanish (Español)</option>
                    <option value="French">French (Français)</option>
                    <option value="German">German (Deutsch)</option>
                  </select>
                </div>

                {/* Lesson Style */}
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-slate-300">Preferred Lesson Style</label>
                  <div className="grid grid-cols-2 gap-1.5">
                    {(['Beginner-friendly', 'In-depth', 'Fast-paced', 'Practical'] as const).map((style) => (
                      <button
                        key={style}
                        type="button"
                        onClick={() => setLessonStyle(style)}
                        className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border text-center transition cursor-pointer ${
                          lessonStyle === style
                            ? 'bg-blue-600/30 border-blue-500 text-blue-300 font-semibold'
                            : 'bg-[#0d172e] border-[#1b2b52] text-slate-400 hover:text-white'
                        }`}
                      >
                        {style}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Daily Availability */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-slate-300 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-blue-400" />
                  Daily Study Availability
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { val: '30-60 minutes', label: '30–60 min', sub: 'Light pace' },
                    { val: '1-2 hours', label: '1–2 hours', sub: 'Steady pace' },
                    { val: '2-4 hours', label: '2–4 hours', sub: 'Standard load' },
                    { val: '4+ hours', label: '4+ hours', sub: 'Intensive prep' },
                  ].map((item) => (
                    <button
                      key={item.val}
                      type="button"
                      onClick={() => setAvailability(item.val as any)}
                      className={`p-2.5 rounded-xl border text-left transition cursor-pointer ${
                        availability === item.val
                          ? 'bg-blue-600/20 border-blue-500/80 shadow-md ring-1 ring-blue-500/50'
                          : 'bg-[#0d172e] border-[#1b2b52] hover:border-slate-600'
                      }`}
                    >
                      <p className={`text-xs font-bold ${availability === item.val ? 'text-blue-300' : 'text-white'}`}>
                        {item.label}
                      </p>
                      <span className="text-[10px] text-slate-400">{item.sub}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Step 3: Assessment Pattern & Milestones */}
            <div className="space-y-3 pt-2 border-t border-[#152342]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-blue-600/30 text-blue-400 text-xs font-bold flex items-center justify-center">3</span>
                  <h3 className="text-sm font-semibold text-white">Assessment Milestones & Dates</h3>
                </div>

                {/* Pattern switcher */}
                <div className="flex bg-[#0c162e] p-0.5 rounded-xl border border-[#1b2b52] text-[11px]">
                  {(['autonomous', 'university', 'custom'] as const).map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => handlePatternChange(t)}
                      className={`px-2.5 py-1 rounded-lg capitalize transition cursor-pointer ${
                        patternType === t
                          ? 'bg-blue-600 text-white font-semibold'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Assessment Scope Selector */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-[11px] text-slate-400">Preparation Scope:</span>
                <div className="flex bg-[#0c162e] p-0.5 rounded-lg border border-[#1b2b52] text-[10px]">
                  {[
                    { id: 'both', label: 'Both Internal & End-Sem' },
                    { id: 'internal', label: 'Internal Only' },
                    { id: 'end_sem', label: 'End-Sem Only' },
                  ].map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => setAssessmentScope(s.id as any)}
                      className={`px-2 py-0.5 rounded font-medium transition cursor-pointer ${
                        assessmentScope === s.id
                          ? 'bg-blue-600 text-white font-bold'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Assessment list */}
              <div className="space-y-2">
                {assessments.map((a, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 p-3 rounded-xl bg-[#0c162e] border border-[#1b2b52]"
                  >
                    <div className="flex-1">
                      <input
                        type="text"
                        value={a.name}
                        onChange={(e) => handleUpdateAssessment(idx, 'name', e.target.value)}
                        placeholder="Assessment name"
                        className="w-full px-2.5 py-1.5 rounded-lg bg-[#070b14] border border-[#1b2b52] text-xs text-white focus:outline-hidden focus:border-blue-500"
                      />
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="relative">
                        <input
                          type="date"
                          min={todayStr}
                          value={a.exam_date}
                          onChange={(e) => handleUpdateAssessment(idx, 'exam_date', e.target.value)}
                          required
                          className="px-2.5 py-1.5 rounded-lg bg-[#070b14] border border-[#1b2b52] text-xs text-blue-300 focus:outline-hidden focus:border-blue-500"
                        />
                      </div>

                      <select
                        value={a.assessment_type}
                        onChange={(e) => handleUpdateAssessment(idx, 'assessment_type', e.target.value)}
                        className="px-2 py-1.5 rounded-lg bg-[#070b14] border border-[#1b2b52] text-xs text-slate-300"
                      >
                        <option value="internal">Internal (CA/IA)</option>
                        <option value="mid_sem">Mid-Sem</option>
                        <option value="end_sem">End-Sem / Final</option>
                        <option value="custom">Custom Milestone</option>
                      </select>

                      {assessments.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveAssessment(idx)}
                          className="p-1.5 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-rose-500/10 transition cursor-pointer"
                          title="Remove milestone"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Add milestone button */}
              <button
                type="button"
                onClick={handleAddAssessment}
                className="w-full py-2 rounded-xl border border-dashed border-[#1b2b52] text-xs text-blue-400 hover:text-blue-300 hover:border-blue-500/50 flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Assessment Milestone
              </button>
            </div>

            {/* Date Validation Alert */}
            {dateError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{dateError}</span>
              </div>
            )}

            {/* Footer Actions */}
            <div className="pt-3 border-t border-[#152342] flex items-center justify-between">
              <span className="text-[11px] text-slate-500 flex items-center gap-1">
                <HelpCircle className="w-3 h-3" />
                AI will organize topics and schedule milestones accordingly.
              </span>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-[#111d38] transition cursor-pointer"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-lg shadow-blue-600/30 flex items-center gap-2 transition cursor-pointer"
                >
                  <Sparkles className="w-4 h-4" />
                  Start AI Analysis & Roadmap
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
