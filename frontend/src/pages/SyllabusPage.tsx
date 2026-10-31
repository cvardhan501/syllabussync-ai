import React, { useState, useRef, useEffect } from 'react';
import { 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  X, 
  FileCode, 
  Check, 
  RefreshCw,
  Layers,
  Sparkles
} from 'lucide-react';
import type { SyllabusUploadResponse, SyllabusAnalysisResponse, Course } from '../types';
import { apiService, ApiErrorResponse } from '../services/api';
import { TopicReviewEditor } from '../components/TopicReviewEditor';
import { RobotMascotIllustration } from '../components/Illustrations';
import { SyllabusSetupWizard } from '../components/SyllabusSetupWizard';

interface SyllabusPageProps {
  uploadedSyllabus: SyllabusUploadResponse | null;
  onSyllabusUploaded: (data: SyllabusUploadResponse | null) => void;
  analyzedSyllabus: SyllabusAnalysisResponse | null;
  onAnalysisComplete: (data: SyllabusAnalysisResponse | null) => void;
  onNavigateToStudyPlan: () => void;
  onCourseCreated?: (course: Course) => void;
}

const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];

export const SyllabusPage: React.FC<SyllabusPageProps> = ({
  uploadedSyllabus,
  onSyllabusUploaded,
  analyzedSyllabus,
  onAnalysisComplete,
  onNavigateToStudyPlan,
  onCourseCreated,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState(1);
  const [activeTab, setActiveTab] = useState<'editor' | 'raw'>('editor');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Stepper simulation during analysis
  useEffect(() => {
    let timer: any;
    if (isAnalyzing) {
      setAnalysisStep(1);
      timer = setInterval(() => {
        setAnalysisStep((prev) => (prev < 4 ? prev + 1 : prev));
      }, 900);
    }
    return () => clearInterval(timer);
  }, [isAnalyzing]);

  const validateFile = (file: File): string | null => {
    const name = file.name.toLowerCase();
    const hasValidExt = ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
    if (!hasValidExt) {
      return `Unsupported file format. Please upload a PDF (.pdf) or Word document (.docx).`;
    }

    if (file.size === 0) {
      return `The selected file is empty (0 bytes). Please select a valid document.`;
    }

    if (file.size > MAX_SIZE_BYTES) {
      return `File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds the ${MAX_SIZE_MB} MB limit.`;
    }

    return null;
  };

  const handleFileSelect = (file: File) => {
    setErrorMessage(null);
    const validationError = validateFile(file);
    if (validationError) {
      setErrorMessage(validationError);
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleFileSelect(file);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleUploadAndOpenWizard = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setErrorMessage(null);

    try {
      const uploadRes = await apiService.uploadSyllabus(selectedFile);
      onSyllabusUploaded(uploadRes);
      setIsWizardOpen(true);
    } catch (err: any) {
      if (err instanceof ApiErrorResponse) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(err.message || 'Failed to parse syllabus. Ensure backend server is running.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleWizardSubmit = async (wizardData: any) => {
    setIsAnalyzing(true);
    setErrorMessage(null);

    try {
      const result = await apiService.setupAndAnalyzeSyllabus(wizardData);
      onAnalysisComplete(result.analysis);
      if (onCourseCreated && result.course) {
        onCourseCreated(result.course);
      }
      setIsWizardOpen(false);
      setSelectedFile(null);
      setActiveTab('editor');
    } catch (err: any) {
      if (err instanceof ApiErrorResponse) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(err.message || 'Failed to analyze syllabus with Strands Agent.');
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleResetAll = () => {
    onSyllabusUploaded(null);
    onAnalysisComplete(null);
    setSelectedFile(null);
    setIsWizardOpen(false);
    setActiveTab('editor');
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleCopyPreview = () => {
    if (!uploadedSyllabus?.preview_text) return;
    navigator.clipboard.writeText(uploadedSyllabus.preview_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Screen 3: Analyzing State (Matches Reference Top-Right)
  if (isAnalyzing) {
    return (
      <div className="max-w-4xl mx-auto py-10 px-4 space-y-10 text-center">
        <div className="space-y-2">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight m-0">
            Analyzing Your Syllabus...
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 m-0">
            Our AI is reading and understanding your syllabus. This may take a few moments.
          </p>
        </div>

        {/* Stepper (Matches Reference Screen 3) */}
        <div className="grid grid-cols-4 gap-2 max-w-2xl mx-auto">
          {[
            { step: 1, label: 'Extracting text' },
            { step: 2, label: 'Identifying modules' },
            { step: 3, label: 'Organizing topics' },
            { step: 4, label: 'Preparing review' },
          ].map((s) => {
            const isDone = analysisStep > s.step;
            const isCurrent = analysisStep === s.step;

            return (
              <div key={s.step} className="flex flex-col items-center space-y-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    isDone
                      ? 'bg-emerald-500 text-white'
                      : isCurrent
                      ? 'bg-blue-600 text-white ring-4 ring-blue-500/25 animate-pulse'
                      : 'bg-slate-800 text-slate-500'
                  }`}
                >
                  {isDone ? <Check className="w-4 h-4" /> : s.step}
                </div>
                <span className={`text-[11px] font-medium leading-tight ${isCurrent ? 'text-blue-300' : isDone ? 'text-slate-300' : 'text-slate-500'}`}>
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Robot Mascot & Thought Bubble (Matches Reference Screen 3) */}
        <div className="relative flex flex-col items-center justify-center pt-4">
          <div className="mb-4 px-4 py-2.5 rounded-2xl bg-[#0f1d3b] border border-[#203666] shadow-xl text-xs text-blue-200 font-medium inline-flex items-center gap-2 animate-bounce">
            <span>Looking for key topics, modules and structure... Almost there! 🚀</span>
          </div>
          <RobotMascotIllustration className="w-56 h-48" />
        </div>
      </div>
    );
  }

  // Screen 4: Topic Review Editor
  if (analyzedSyllabus) {
    return (
      <div className="space-y-6 max-w-6xl mx-auto">
        {/* Navigation Tab Switcher */}
        <div className="flex items-center justify-between border-b border-[#18284e] pb-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('editor')}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'editor'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-white hover:bg-[#111d38]'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Syllabus Topic Review</span>
            </button>

            {uploadedSyllabus?.preview_text && (
              <button
                onClick={() => setActiveTab('raw')}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer ${
                  activeTab === 'raw'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white hover:bg-[#111d38]'
                }`}
              >
                <FileCode className="w-4 h-4" />
                <span>Raw Extracted Text</span>
              </button>
            )}
          </div>

          <button
            onClick={handleResetAll}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#111d38] hover:bg-[#192b52] text-slate-300 text-xs font-medium border border-[#1e325f] transition cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Upload New Document</span>
          </button>
        </div>

        {activeTab === 'editor' ? (
          <TopicReviewEditor
            analysisData={analyzedSyllabus}
            onUpdateSuccess={onAnalysisComplete}
            onConfirmTopics={onNavigateToStudyPlan}
            onViewSource={() => setActiveTab('raw')}
          />
        ) : (
          /* Raw Extracted Text View */
          <div className="space-y-4">
            <div className="rounded-2xl bg-[#0b1429] border border-[#18284e] p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Raw Text Preview
                </span>
                <button
                  onClick={handleCopyPreview}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#111d38] hover:bg-[#1a2d54] text-slate-300 text-xs font-medium cursor-pointer"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <span>Copy Text</span>
                  )}
                </button>
              </div>
              <pre className="font-mono text-xs leading-relaxed text-slate-300 bg-[#070e20] p-4 rounded-xl border border-[#162548] overflow-x-auto whitespace-pre-wrap max-h-96 overflow-y-auto">
                {uploadedSyllabus?.preview_text}
              </pre>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Screen 2: Upload Your Syllabus (Matches Reference Top-Middle)
  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight m-0">
          Upload Your Syllabus
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1 m-0">
          Add your college syllabus (PDF or DOCX) and let AI do the magic ✨
        </p>
      </div>

      {/* Main Grid: Upload Drop Zone (Left) & File Guidelines (Right) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
        {/* Left: Drag & Drop Zone (8 cols) */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={`md:col-span-8 rounded-3xl border-2 border-dashed p-8 sm:p-12 text-center transition-all cursor-pointer flex flex-col items-center justify-center ${
            isDragging
              ? 'border-blue-500 bg-blue-950/20 shadow-xl shadow-blue-500/10'
              : 'border-[#1e305e] hover:border-blue-500/60 bg-[#0b1429] hover:bg-[#0e1935]'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileSelect(e.target.files[0]);
              }
            }}
          />

          <div className="w-16 h-16 rounded-2xl bg-blue-600/15 border border-blue-500/25 flex items-center justify-center text-blue-400 mb-4 group-hover:scale-105 transition-transform">
            <UploadCloud className="w-8 h-8" />
          </div>

          <h3 className="text-base sm:text-lg font-bold text-white mb-1">
            Drag & drop your file here
          </h3>
          <p className="text-xs text-slate-400 mb-4">or</p>

          <button
            type="button"
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition shadow-md shadow-blue-600/30"
          >
            Choose File
          </button>

          <p className="text-[11px] text-slate-400 mt-5 m-0">
            Supported formats: PDF, DOCX • Max size: 10 MB
          </p>
        </div>

        {/* Right: File Guidelines Card (4 cols) */}
        <div className="md:col-span-4 rounded-3xl bg-[#0b1429] border border-[#1e305e] p-6 space-y-4">
          <h4 className="text-sm font-bold text-white tracking-tight m-0">
            File Guidelines
          </h4>
          <ul className="space-y-3 text-xs text-slate-300 p-0 m-0 list-none">
            <li className="flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>PDF or DOCX only</span>
            </li>
            <li className="flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Max size 10 MB</span>
            </li>
            <li className="flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Clear and readable text</span>
            </li>
            <li className="flex items-center gap-2.5 text-slate-400">
              <CheckCircle2 className="w-4 h-4 text-slate-500 shrink-0" />
              <span>Scanned PDFs not supported (for now)</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Selected File Card & Upload & Analyze CTA (Matches Reference) */}
      {selectedFile && (
        <div className="space-y-4">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
            Selected File
          </span>

          <div className="rounded-2xl bg-[#0b1429] border border-[#1e305e] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-400 flex items-center justify-center shrink-0">
                <FileText className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-bold text-white truncate m-0">
                  {selectedFile.name}
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5 m-0 font-mono">
                  {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB • {selectedFile.name.endsWith('.pdf') ? 'PDF' : 'DOCX'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 self-end sm:self-auto">
              <button
                onClick={() => setSelectedFile(null)}
                className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-[#111d38] cursor-pointer"
                title="Remove file"
              >
                <X className="w-4 h-4" />
              </button>

              <button
                onClick={handleUploadAndOpenWizard}
                disabled={isUploading}
                className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white font-semibold text-xs sm:text-sm transition shadow-lg shadow-blue-600/30 cursor-pointer flex items-center gap-2"
              >
                {isUploading ? (
                  <>
                    <div className="w-4 h-4 rounded-full border-2 border-t-white border-r-transparent animate-spin" />
                    <span>Parsing Document...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Configure & Analyze</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div className="rounded-2xl bg-rose-950/40 border border-rose-800/80 p-4 flex items-start gap-3 text-rose-200">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <h4 className="text-xs font-bold text-rose-300 m-0">Upload Failed</h4>
            <p className="text-xs text-rose-200/90 leading-relaxed m-0">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Pre-Analysis Syllabus Setup Wizard Modal */}
      <SyllabusSetupWizard
        isOpen={isWizardOpen}
        uploadedSyllabus={uploadedSyllabus}
        onClose={() => setIsWizardOpen(false)}
        onSubmit={handleWizardSubmit}
        isAnalyzing={isAnalyzing}
        analysisStep={analysisStep}
      />
    </div>
  );
};
