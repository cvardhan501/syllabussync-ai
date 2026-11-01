export type NavigationTab = 
  | 'dashboard' 
  | 'courses'
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
  database_connected?: boolean | null;
}

export interface SyllabusUploadResponse {
  status: string;
  syllabus_id?: string;
  owner_user_id?: string | null;
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
  course_name_suggestion?: string;
  course_code_suggestion?: string;
  message: string;
}

export interface AssessmentItem {
  id: string;
  course_id: string;
  name: string;
  exam_date: string;
  assessment_type: 'internal' | 'mid_sem' | 'end_sem' | 'custom';
  scope: 'internal' | 'end_sem' | 'both';
  weightage: number;
  order_index: number;
  days_remaining: number;
  is_past: boolean;
}

export interface AssessmentCreate {
  id?: string;
  name: string;
  exam_date: string;
  assessment_type: 'internal' | 'mid_sem' | 'end_sem' | 'custom';
  scope: 'internal' | 'end_sem' | 'both';
  weightage?: number;
  order_index?: number;
}

export interface Course {
  id: string;
  owner_user_id?: string | null;
  syllabus_id?: string;
  course_name: string;
  course_code?: string;
  language: string;
  lesson_style: 'Beginner-friendly' | 'In-depth' | 'Fast-paced' | 'Practical';
  daily_study_availability: '30-60 minutes' | '1-2 hours' | '2-4 hours' | '4+ hours';
  daily_target_minutes: number;
  assessment_system_type: 'autonomous' | 'university' | 'custom';
  assessment_scope: 'internal' | 'end_sem' | 'both';
  color_theme: string;
  is_archived: boolean;
  filename?: string;
  file_type?: string;
  file_size_bytes?: number;
  total_topics: number;
  total_tasks: number;
  completed_tasks: number;
  total_minutes: number;
  completed_minutes: number;
  progress_percentage: number;
  overdue_tasks_count: number;
  assessments: AssessmentItem[];
  next_assessment?: AssessmentItem | null;
  created_at?: string;
  updated_at?: string;
}

export interface UpcomingAssessmentOverview {
  id: string;
  course_id: string;
  course_name: string;
  course_code?: string;
  name: string;
  exam_date: string;
  days_remaining: number;
  assessment_type: string;
  scope: string;
}

export interface SemesterOverview {
  status: string;
  total_courses: number;
  total_topics: number;
  total_tasks: number;
  completed_tasks: number;
  overall_percentage: number;
  overdue_tasks_count: number;
  upcoming_assessments: UpcomingAssessmentOverview[];
  courses: Course[];
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
  official_hours?: number;
  official_minutes?: number;
  topics: TopicItem[];
}

export interface ValidationWarning {
  code: string;
  severity: 'warning' | 'error' | 'info';
  message: string;
  module_id?: string;
  topic_id?: string;
  suggested_action?: string;
}

export interface ValidationReport {
  quality_score: number;
  needs_confirmation: boolean;
  warnings: ValidationWarning[];
  summary: string;
  total_modules: number;
  total_topics: number;
  total_hours: number;
}

export interface SyllabusAnalysisResponse {
  status: string;
  syllabus_id: string;
  owner_user_id?: string | null;
  filename: string;
  file_type: string;
  char_count: number;
  word_count: number;
  course_name?: string;
  course_code?: string;
  credits?: string;
  course_objectives?: string[];
  course_outcomes?: string[];
  prerequisites?: string[];
  textbooks?: string[];
  reference_books?: string[];
  online_resources?: string[];
  assignments?: string[];
  lab_experiments?: string[];
  has_lab_component?: boolean;
  assessment_info?: string[];
  modules: ModuleItem[];
  ambiguous_sections: string[];
  total_topics_count: number;
  total_estimated_minutes: number;
  is_fallback: boolean;
  analysis_engine: string;
  ai_status?: 'completed' | 'temporarily_unavailable' | 'local_extraction';
  ai_status_message?: string;
  message: string;
  validation_report?: ValidationReport;
}

export interface TopicUpdateRequest {
  course_name?: string;
  course_code?: string;
  credits?: string;
  course_objectives?: string[];
  course_outcomes?: string[];
  prerequisites?: string[];
  textbooks?: string[];
  reference_books?: string[];
  online_resources?: string[];
  assignments?: string[];
  lab_experiments?: string[];
  has_lab_component?: boolean;
  assessment_info?: string[];
  modules: ModuleItem[];
  ambiguous_sections?: string[];
  validation_report?: ValidationReport;
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
  availability_status?: 'available' | 'unavailable' | 'missing';
  description?: string;
  provenance?: 'live' | 'cache' | 'fallback';
}

export interface TopicResourceMapping {
  topic_id: string;
  topic_title: string;
  module_id: string;
  module_title: string;
  resource?: VideoResource | null;
  match_status: 'verified' | 'probable' | 'unverified' | 'no_resource' | 'relevant' | 'candidate_only' | 'needs_review';
  match_confidence: 'high' | 'medium' | 'low' | 'uncertain';
  relevance_notes?: string;
  rejected_channels: string[];
  assigned_channel?: string;
  is_shared_video?: boolean;
  shared_with_topics?: string[];
  availability_status?: 'available' | 'unavailable' | 'missing';
  provenance?: 'live' | 'cache' | 'fallback';
}

export interface ChannelCoverageSummary {
  channel_title: string;
  channel_id?: string | null;
  channel_url?: string | null;
  topics_covered: number;
  topic_ids: string[];
  is_primary: boolean;
  percentage_of_course: number;
}

export interface CoverageMetrics {
  total_topics: number;
  topics_with_candidates: number;
  topics_with_relevant: number;
  topics_with_verified: number;
  topics_with_probable: number;
  topics_with_no_resource: number;
  topics_needing_review: number;
  coverage_percentage: number;
  verified_coverage_percentage: number;
  probable_coverage_percentage: number;
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
  is_confirmed?: boolean;
  channel_strategy?: string;
  languages?: string[];
}

export interface ExampleVideo {
  video_id: string;
  title: string;
  duration_formatted: string;
  topic_matched: string;
}

export interface DiscoveredChannelItem {
  channel_title: string;
  channel_id?: string;
  channel_url?: string;
  subscriber_count_approx?: string;
  language: string;
  relevant_video_count: number;
  topics_covered: string[];
  topic_ids_covered: string[];
  topics_not_covered: string[];
  example_videos: ExampleVideo[];
  fit_score: number;
  availability_status: string;
  match_notes?: string;
}

export interface ChannelDiscoveryResponse {
  status: string;
  syllabus_id: string;
  course_name?: string;
  course_code?: string;
  total_topics: number;
  languages: string[];
  discovered_channels: DiscoveredChannelItem[];
  message: string;
}

export interface ChannelDistributionPreviewItem {
  topic_id: string;
  topic_title: string;
  module_title: string;
  selected_channel: string;
  candidate_video_title?: string;
  candidate_video_id?: string;
  thumbnail_url?: string;
  duration_formatted?: string;
  match_status: 'verified' | 'probable' | 'unverified' | 'no_resource';
  relevance_explanation: string;
  available_channels: string[];
}

export interface PreviewStrategyResponse {
  status: string;
  syllabus_id: string;
  strategy: 'one_channel' | 'two_channels' | 'different_per_topic' | 'custom';
  strategy_title: string;
  strategy_explanation: string;
  selected_channels: ChannelCoverageSummary[];
  preview_items: ChannelDistributionPreviewItem[];
  coverage: CoverageMetrics;
  missing_topics: string[];
  requires_third_channel_approval: boolean;
  third_channel_candidates: string[];
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
  owner_user_id?: string | null;
  course_id?: string | null;
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

export interface BackendDiagnostic {
  status: string;
  version: string;
  environment: string;
}

export interface DatabaseDiagnostic {
  status: string;
  engine: string;
  tables_count: number;
  tables: string[];
}

export interface StrandsDiagnostic {
  provider: string;
  model: string;
  credentials_configured: boolean;
  credentials_summary: string;
  fallback_enabled: boolean;
  active_mode: string;
  fallback_reason?: string | null;
}

export interface YouTubeDiagnostic {
  key_configured: boolean;
  key_summary: string;
  fallback_enabled: boolean;
  active_mode: string;
  fallback_reason?: string | null;
  cached_queries_count: number;
}

export interface SystemDiagnosticsResponse {
  status: string;
  timestamp: string;
  backend: BackendDiagnostic;
  database: DatabaseDiagnostic;
  strands: StrandsDiagnostic;
  youtube: YouTubeDiagnostic;
}

export interface DiagnosticTestResult {
  service: string;
  tested: boolean;
  status: string;
  latency_ms: number;
  message: string;
}
