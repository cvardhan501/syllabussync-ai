import React from 'react';
import { X, BookOpen, Sparkles, Video, Calendar } from 'lucide-react';
import { StudentAvatarIllustration } from './Illustrations';

interface GuideModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (tab: any) => void;
}

export const GuideModal: React.FC<GuideModalProps> = ({ isOpen, onClose, onNavigate }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs">
      <div className="rounded-2xl bg-[#0c162e] border border-[#1e305e] max-w-lg w-full p-6 space-y-5 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#162548] cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3">
          <StudentAvatarIllustration className="w-12 h-12" />
          <div>
            <h3 className="text-base font-bold text-white m-0">SyllabusSync AI Study Guide</h3>
            <p className="text-xs text-slate-400 m-0">How to get the most out of your AI-guided course roadmap</p>
          </div>
        </div>

        <div className="space-y-3 text-xs">
          <div className="p-3 rounded-xl bg-[#081022] border border-[#162548] flex items-start gap-3">
            <BookOpen className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white m-0">1. Upload Clean Digital Documents</p>
              <p className="text-slate-400 mt-0.5 m-0 leading-relaxed">
                Use selectable text PDFs or DOCX files. Avoid photocopies or scanned images without text layers.
              </p>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-[#081022] border border-[#162548] flex items-start gap-3">
            <Sparkles className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white m-0">2. Review & Customize Topics</p>
              <p className="text-slate-400 mt-0.5 m-0 leading-relaxed">
                Use the Topic Review Editor to reorder units, adjust study minutes, or add topics specific to your professor's syllabus.
              </p>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-[#081022] border border-[#162548] flex items-start gap-3">
            <Video className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white m-0">3. Match Educational Videos</p>
              <p className="text-slate-400 mt-0.5 m-0 leading-relaxed">
                Videos are matched with channel consistency (1 primary channel first, max 2 complementary channels).
              </p>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-[#081022] border border-[#162548] flex items-start gap-3">
            <Calendar className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white m-0">4. Stick to Daily Blocks</p>
              <p className="text-slate-400 mt-0.5 m-0 leading-relaxed">
                Complete 60–90 minute daily study sessions to keep streaks and ensure high exam readiness.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-2">
          <button
            onClick={() => {
              onClose();
              onNavigate('syllabus');
            }}
            className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/30 cursor-pointer"
          >
            Start with My Syllabus
          </button>
        </div>
      </div>
    </div>
  );
};
