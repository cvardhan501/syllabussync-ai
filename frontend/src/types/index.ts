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
  syllabus_id?: string;
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

export interface SubtopicItem {
  id: string;
  title: string;
}

export interface TopicItem {
  id: string;
  title: string;
  explanation: string;
  estimated_minutes: number;
  difficulty: 'easy' | 'medium' | 'hard';
  prerequisites: string[];
  subtopics: SubtopicItem[];
  source_evidence?: string;
  confidence_notes?: string;
  order_index: number;
}

export interface ModuleItem {
  id: string;
  title: string;
  order_index: number;
  topics: TopicItem[];
}

export interface SyllabusAnalysisResponse {
  status: string;
  syllabus_id: string;
  filename: string;
  file_type: string;
  char_count: number;
  word_count: number;
  course_name?: string;
  course_code?: string;
  modules: ModuleItem[];
  ambiguous_sections: string[];
  total_topics_count: number;
  total_estimated_minutes: number;
  is_fallback: boolean;
  analysis_engine: string;
  message: string;
}

export interface TopicUpdateRequest {
  course_name?: string;
  modules: ModuleItem[];
  ambiguous_sections?: string[];
}

export interface ApiError {
  detail: string;
}
