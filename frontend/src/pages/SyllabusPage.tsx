import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  X, 
  FileCode, 
  Loader2, 
  Copy, 
  Check, 
  Sparkles, 
  RefreshCw,
  Info,
  Layers
} from 'lucide-react';
import type { SyllabusUploadResponse, SyllabusAnalysisResponse } from '../types';
import { apiService, ApiErrorResponse } from '../services/api';
import { TopicReviewEditor } from '../components/TopicReviewEditor';

interface SyllabusPageProps {
  uploadedSyllabus: SyllabusUploadResponse | null;
  onSyllabusUploaded: (data: SyllabusUploadResponse | null) => void;
  analyzedSyllabus: SyllabusAnalysisResponse | null;
  onAnalysisComplete: (data: SyllabusAnalysisResponse | null) => void;
  onNavigateToStudyPlan: () => void;
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
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState<'editor' | 'raw'>('editor');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleUploadAndAnalyzeDirectly = async (autoAnalyze: boolean = true) => {
    if (!selectedFile) return;

    setIsUploading(true);
    setErrorMessage(null);

    try {
      if (autoAnalyze) {
        setIsAnalyzing(true);
        // Analyze directly with Strands Agent
        const analysisResult = await apiService.analyzeSyllabus(selectedFile);
        onAnalysisComplete(analysisResult);
        // Synthesize an upload response so metadata stays accessible
        onSyllabusUploaded({
          status: 'success',
          syllabus_id: analysisResult.syllabus_id,
          filename: analysisResult.filename,
          file_type: analysisResult.file_type as any,
          file_size_bytes: selectedFile.size,
          char_count: analysisResult.char_count,
          word_count: analysisResult.word_count,
          unit_count: analysisResult.modules.length,
          unit_label: 'modules',
          preview_text: `Course: ${analysisResult.course_name || 'N/A'}\nTotal Topics: ${analysisResult.total_topics_count}`,
          full_text_length: analysisResult.char_count,
          message: analysisResult.message,
        });
      } else {
        const result = await apiService.uploadSyllabus(selectedFile);
        onSyllabusUploaded(result);
      }
    } catch (err: any) {
      if (err instanceof ApiErrorResponse) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(err.message || 'Failed to process syllabus. Ensure the backend server is running.');
      }
    } finally {
      setIsUploading(false);
      setIsAnalyzing(false);
    }
  };

  const handleAnalyzeExistingSyllabus = async () => {
    if (!uploadedSyllabus?.syllabus_id) return;

    setIsAnalyzing(true);
    setErrorMessage(null);

    try {
      const result = await apiService.analyzeSyllabus(undefined, uploadedSyllabus.syllabus_id);
      onAnalysisComplete(result);
      setActiveTab('editor');
    } catch (err: any) {
      if (err instanceof ApiErrorResponse) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(err.message || 'Failed to analyze syllabus topics.');
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
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

  const handleResetAll = () => {
    onSyllabusUploaded(null);
    onAnalysisComplete(null);
    setSelectedFile(null);
    setErrorMessage(null);
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight m-0">
            Syllabus Parsing & Topic Extraction
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 m-0">
            Extract text from PDF or DOCX documents, structure learning units with the Strands Agents SDK, and customize your study topics.
          </p>
        </div>

        {(uploadedSyllabus || analyzedSyllabus) && (
          <button
            onClick={handleResetAll}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition cursor-pointer self-start sm:self-auto"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Upload Another Document</span>
          </button>
        )}
      </div>

      {/* View 1: Initial Upload State */}
      {!uploadedSyllabus && !analyzedSyllabus ? (
        <div className="space-y-6">
          {/* Drag & Drop Area */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`relative rounded-2xl border-2 border-dashed p-8 sm:p-12 text-center transition-all cursor-pointer flex flex-col items-center justify-center ${
              isDragging
                ? 'border-indigo-500 bg-indigo-950/20 shadow-xl shadow-indigo-500/10'
                : 'border-slate-800 hover:border-slate-700 bg-slate-900/40 hover:bg-slate-900/60'
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

            <div className="w-16 h-16 rounded-2xl bg-indigo-600/15 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4 group-hover:scale-105 transition-transform">
              <UploadCloud className="w-8 h-8" />
            </div>

            <h3 className="text-base sm:text-lg font-semibold text-white mb-1">
              Drag and drop your syllabus file here
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 max-w-md mb-4">
              Supported formats: <strong className="text-slate-300">PDF (.pdf)</strong> or{' '}
              <strong className="text-slate-300">Microsoft Word (.docx)</strong> up to 10 MB.
            </p>

            <button
              type="button"
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs sm:text-sm font-medium transition shadow-md shadow-indigo-600/20"
            >
              Browse Local Files
            </button>
          </div>

          {/* Selected File Card */}
          {selectedFile && (
            <div className="rounded-2xl bg-slate-900/90 border border-slate-800 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white truncate m-0">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5 m-0 font-mono">
                    {(selectedFile.size / 1024).toFixed(1)} KB •{' '}
                    {selectedFile.name.endsWith('.pdf') ? 'PDF Document' : 'Word Document'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end sm:self-auto">
                <button
                  onClick={handleClear}
                  disabled={isUploading}
                  className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition disabled:opacity-50 cursor-pointer"
                  title="Remove selected file"
                >
                  <X className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleUploadAndAnalyzeDirectly(true)}
                  disabled={isUploading}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white font-medium text-xs sm:text-sm transition shadow-lg shadow-indigo-600/25 cursor-pointer"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>{isAnalyzing ? 'Strands Agent Analyzing...' : 'Parsing Document...'}</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>Upload & Extract Topics</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Validation or API Error Banner */}
          {errorMessage && (
            <div className="rounded-2xl bg-rose-950/40 border border-rose-800/80 p-4 sm:p-5 flex items-start gap-3 text-rose-200">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-rose-300 m-0">Processing Failed</h4>
                <p className="text-xs sm:text-sm text-rose-200/90 leading-relaxed m-0">
                  {errorMessage}
                </p>
              </div>
            </div>
          )}

          {/* Guidance Note on Digital vs Scanned Documents */}
          <div className="rounded-2xl bg-slate-900/40 border border-slate-800/60 p-4 flex items-start gap-3 text-slate-400">
            <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <span className="font-semibold text-slate-300">Notice on Digital Text:</span>
              <p className="m-0 leading-relaxed">
                SyllabusSync AI parses digital selectable text from PDF and DOCX documents.
                Scanned photocopy PDFs without an embedded text layer are not supported (no OCR is performed).
              </p>
            </div>
          </div>
        </div>
      ) : analyzedSyllabus ? (
        /* View 2: Topic Review & Editor (When Analysis Completed) */
        <div className="space-y-6">
          {/* Navigation Tab Switcher between Editor and Raw Preview */}
          <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
            <button
              onClick={() => setActiveTab('editor')}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'editor'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Topic Hierarchy Editor</span>
              <span className="px-1.5 py-0.2 rounded-md bg-white/20 text-[10px]">
                {analyzedSyllabus.total_topics_count}
              </span>
            </button>

            {uploadedSyllabus?.preview_text && (
              <button
                onClick={() => setActiveTab('raw')}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer ${
                  activeTab === 'raw'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900'
                }`}
              >
                <FileCode className="w-4 h-4" />
                <span>Raw Extracted Text</span>
              </button>
            )}
          </div>

          {activeTab === 'editor' ? (
            <TopicReviewEditor
              analysisData={analyzedSyllabus}
              onUpdateSuccess={onAnalysisComplete}
              onConfirmTopics={onNavigateToStudyPlan}
            />
          ) : (
            /* Raw Text View */
            <div className="space-y-4">
              <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                    Extracted Text Content
                  </span>
                  <button
                    onClick={handleCopyPreview}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium cursor-pointer"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy Text</span>
                      </>
                    )}
                  </button>
                </div>
                <pre className="font-mono text-xs leading-relaxed text-slate-300 bg-slate-950/80 p-4 rounded-xl border border-slate-800 overflow-x-auto whitespace-pre-wrap max-h-96 overflow-y-auto">
                  {uploadedSyllabus?.preview_text}
                </pre>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* View 3: Uploaded but not yet analyzed */
        <div className="space-y-6">
          {/* Success Banner from Upload */}
          <div className="rounded-2xl bg-emerald-950/40 border border-emerald-800/60 p-5 flex items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-emerald-200 m-0">
                  Syllabus Document Parsed
                </h3>
                <p className="text-xs text-emerald-300/80 mt-0.5 m-0">
                  {uploadedSyllabus?.message}
                </p>
              </div>
            </div>

            <button
              onClick={handleAnalyzeExistingSyllabus}
              disabled={isAnalyzing}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white font-semibold text-xs sm:text-sm transition shadow-lg shadow-indigo-600/30 cursor-pointer shrink-0"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Strands Agent Analyzing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Extract Topics with Strands Agent</span>
                </>
              )}
            </button>
          </div>

          {/* Metrics Summary */}
          {uploadedSyllabus && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
                <span className="text-xs text-slate-400 font-medium">Document Units</span>
                <p className="text-xl font-bold text-white mt-1 m-0">
                  {uploadedSyllabus.unit_count}
                </p>
                <span className="text-[11px] text-slate-500 capitalize">{uploadedSyllabus.unit_label}</span>
              </div>

              <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
                <span className="text-xs text-slate-400 font-medium">Word Count</span>
                <p className="text-xl font-bold text-white mt-1 m-0">
                  {uploadedSyllabus.word_count.toLocaleString()}
                </p>
                <span className="text-[11px] text-slate-500">Extracted words</span>
              </div>

              <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
                <span className="text-xs text-slate-400 font-medium">Characters</span>
                <p className="text-xl font-bold text-white mt-1 m-0">
                  {uploadedSyllabus.char_count.toLocaleString()}
                </p>
                <span className="text-[11px] text-slate-500">Total characters</span>
              </div>

              <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
                <span className="text-xs text-slate-400 font-medium">File Size</span>
                <p className="text-xl font-bold text-white mt-1 m-0">
                  {(uploadedSyllabus.file_size_bytes / 1024).toFixed(1)} KB
                </p>
                <span className="text-[11px] text-slate-500">In-memory parse</span>
              </div>
            </div>
          )}

          {/* Raw Text Preview */}
          {uploadedSyllabus && (
            <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Raw Text Preview
                </span>
                <button
                  onClick={handleCopyPreview}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium cursor-pointer"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Text</span>
                    </>
                  )}
                </button>
              </div>

              <pre className="font-mono text-xs leading-relaxed text-slate-300 bg-slate-950/80 p-4 rounded-xl border border-slate-800/80 overflow-x-auto whitespace-pre-wrap max-h-60 overflow-y-auto">
                {uploadedSyllabus.preview_text}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
