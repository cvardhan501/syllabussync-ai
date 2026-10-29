export type NavigationTab = 
  | 'dashboard' 
  | 'syllabus' 
  | 'study-plan' 
  | 'progress' 
  | 'settings';

export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
  timestamp: string;
  environment: string;
}

export interface SyllabusUploadResponse {
  status: string;
  filename: string;
  file_type: 'pdf' | 'docx';
  file_size_bytes: number;
  char_count: number;
  word_count: number;
  unit_count: number;
  unit_label: string;
  preview_text: string;
  full_text_length: number;
  extraction_notes?: string;
  message: string;
}

export interface ApiError {
  detail: string;
}
