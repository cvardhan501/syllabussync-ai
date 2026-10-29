export type NavigationTab = 
  | 'dashboard' 
  | 'syllabus' 
  | 'videos'
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

export interface VideoResourceItem {
  id: string;
  title: string;
  channelTitle: string;
  thumbnailUrl: string;
  durationFormatted: string;
  durationSeconds: number;
  language: string;
  difficulty: 'easy' | 'medium' | 'hard';
  matchedTopicTitle: string;
  matchedModuleTitle?: string;
  videoUrl: string;
  isBookmarked?: boolean;
}

export interface VideoResource {
  id: string;
  video_id: string;
  title: string;
  channel_title: string;
  channel_id?: string;
  thumbnail_url: string;
  duration_seconds: number;
  duration_formatted: string;
  language?: string;
  published_at?: string;
  view_count: number;
  relevance_score: number;
  relevance_explanation: string;
  is_uncertain: boolean;
  video_url: string;
}

export interface TopicResourceMapping {
  topic_id: string;
  topic_title: string;
  module_id: string;
  module_title: string;
  resource?: VideoResource | null;
  match_status: 'relevant' | 'candidate_only' | 'no_resource' | 'needs_review';
  match_confidence: 'high' | 'medium' | 'low' | 'uncertain';
  relevance_notes?: string;
  rejected_channels: string[];
}

export interface ChannelCoverageSummary {
  channel_title: string;
  topics_covered: number;
  topic_ids: string[];
  is_primary: boolean;
  percentage_of_course: number;
}

export interface CoverageMetrics {
  total_topics: number;
  topics_with_candidates: number;
  topics_with_relevant: number;
  topics_with_no_resource: number;
  topics_needing_review: number;
  coverage_percentage: number;
}

export interface ResourceDiscoveryResponse {
  status: string;
  syllabus_id: string;
  course_name?: string;
  coverage: CoverageMetrics;
  selected_channels: ChannelCoverageSummary[];
  requires_third_channel_approval: boolean;
  third_channel_candidates: string[];
  strategy_explanation: string;
  topic_resources: TopicResourceMapping[];
  is_fallback: boolean;
  discovery_engine: string;
  message: string;
}

export interface AlternativeResourceItem {
  video: VideoResource;
  recommendation_reason: string;
  is_current: boolean;
}

export interface AlternativeResourcesResponse {
  topic_id: string;
  topic_title: string;
  current_channel?: string;
  rejected_channels: string[];
  alternatives: AlternativeResourceItem[];
  message: string;
}

export interface ReplaceChannelRequest {
  rejected_channel: string;
  selected_video_id: string;
  reason?: string;
}

export interface TaskItemSchema {
  id: string;
  plan_id: string;
  syllabus_id: string;
  module_id: string;
  module_title?: string;
  topic_id: string;
  topic_title?: string;
  scheduled_date: string;
  title: string;
  task_type: 'Video' | 'Practice' | 'Study';
  duration_minutes: number;
  video_id?: string;
  video_url?: string;
  status: 'pending' | 'completed';
  completed_at?: string;
  notes?: string;
  order_index: number;
}

export interface DailyScheduleGroup {
  date: string;
  day_name: string;
  formatted_date: string;
  total_minutes: number;
  completed_minutes: number;
  is_today: boolean;
  tasks: TaskItemSchema[];
}

export interface StudyPlanCreateRequest {
  exam_date: string;
  daily_target_minutes?: number;
  preferred_days?: string[];
  start_date?: string;
  preserve_completed?: boolean;
}

export interface StudyPlanResponse {
  id: string;
  syllabus_id: string;
  course_name?: string;
  title: string;
  exam_date: string;
  daily_target_minutes: number;
  preferred_days: string[];
  feasibility_status: 'feasible' | 'tight' | 'impossible';
  shortfall_minutes: number;
  shortfall_hours: number;
  feasibility_warning: string;
  total_planned_minutes: number;
  completed_minutes: number;
  progress_percentage: number;
  total_tasks_count: number;
  completed_tasks_count: number;
  daily_schedules: DailyScheduleGroup[];
  created_at: string;
  updated_at: string;
  message: string;
}

export interface UserSettingsSchema {
  preferred_language: string;
  lesson_style: string;
  daily_study_availability: string;
  daily_target_minutes: number;
  exam_date: string;
  study_days: string[];
  theme: 'dark' | 'light';
  study_reminders: boolean;
  deadline_alerts: boolean;
  auto_save_progress: boolean;
}

export interface UserPreferences {
  preferredLanguage: string;
  lessonStyle: string;
  dailyStudyAvailability: string;
  examDate: string;
  theme: 'dark' | 'light';
  studyReminders: boolean;
  deadlineAlerts: boolean;
  autoSaveProgress: boolean;
}

export interface StudyTaskItem {
  id: string;
  title: string;
  durationMinutes: number;
  type: 'Video' | 'Practice' | 'Study';
  completed: boolean;
  topicId?: string;
}

export interface ApiError {
  detail: string;
}
