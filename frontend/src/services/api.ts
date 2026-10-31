import type { 
  HealthResponse, 
  SyllabusUploadResponse, 
  SyllabusAnalysisResponse, 
  TopicUpdateRequest,
  ResourceDiscoveryResponse,
  AlternativeResourcesResponse,
  ReplaceChannelRequest,
  TopicResourceMapping,
  ChannelDiscoveryResponse,
  PreviewStrategyResponse,
  StudyPlanResponse,
  StudyPlanCreateRequest,
  TaskItemSchema,
  UserSettingsSchema,
  SystemDiagnosticsResponse,
  DiagnosticTestResult,
  Course,
  SemesterOverview
} from '../types';
import { getSupabaseAccessToken } from './supabase';

// Use relative API path to leverage Vite proxy in dev, or customizable via environment
const API_BASE = '/api';

export class ApiErrorResponse extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiErrorResponse';
    this.status = status;
  }
}

/**
 * Custom authenticated fetch wrapper that injects Supabase JWT access token
 * into outgoing API requests as `Authorization: Bearer <token>`.
 * Dispatches an event on 401 Unauthorized so the UI can prompt for re-authentication.
 */
async function authenticatedFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const token = await getSupabaseAccessToken();
  const headers = new Headers(init?.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await window.fetch(input, {
    ...init,
    headers,
  });

  if (response.status === 401 && typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('syllabussync:unauthorized'));
  }

  return response;
}

export const apiService = {
  async getHealth(): Promise<HealthResponse> {
    try {
      const response = await authenticatedFetch(`${API_BASE}/health`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new ApiErrorResponse(`Health check failed with status ${response.status}`, response.status);
      }

      return await response.json();
    } catch (err: any) {
      if (err instanceof ApiErrorResponse) {
        throw err;
      }
      throw new Error(err.message || 'Unable to connect to SyllabusSync AI backend API.');
    }
  },

  async uploadSyllabus(file: File): Promise<SyllabusUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await authenticatedFetch(`${API_BASE}/syllabus/upload`, {
      method: 'POST',
      body: formData,
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'An unexpected error occurred while parsing the syllabus.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as SyllabusUploadResponse;
  },

  async analyzeSyllabus(file?: File, syllabusId?: string): Promise<SyllabusAnalysisResponse> {
    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    }
    if (syllabusId) {
      formData.append('syllabus_id', syllabusId);
    }

    const response = await authenticatedFetch(`${API_BASE}/syllabus/analyze`, {
      method: 'POST',
      body: formData,
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response during syllabus analysis.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'An unexpected error occurred while analyzing syllabus topics with Strands Agents SDK.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as SyllabusAnalysisResponse;
  },

  async getSyllabus(syllabusId: string): Promise<SyllabusAnalysisResponse> {
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || `Failed to retrieve syllabus '${syllabusId}'.`;
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as SyllabusAnalysisResponse;
  },

  async updateSyllabusTopics(syllabusId: string, payload: TopicUpdateRequest): Promise<SyllabusAnalysisResponse> {
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}/topics`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to update syllabus topics.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as SyllabusAnalysisResponse;
  },

  async discoverResources(
    syllabusId: string, 
    options?: { preferred_language?: string; force_refresh?: boolean; allow_third_channel?: boolean }
  ): Promise<ResourceDiscoveryResponse> {
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}/discover-resources`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(options || {}),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response during resource discovery.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to discover YouTube educational resources.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as ResourceDiscoveryResponse;
  },

  async getResources(syllabusId: string): Promise<ResourceDiscoveryResponse> {
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}/resources`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || `Failed to retrieve resources for syllabus '${syllabusId}'.`;
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as ResourceDiscoveryResponse;
  },

  async getTopicAlternatives(syllabusId: string, topicId: string, language: string = 'English'): Promise<AlternativeResourcesResponse> {
    const params = new URLSearchParams({ language });
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}/topics/${topicId}/alternatives?${params.toString()}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to fetch alternative channels for this topic.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as AlternativeResourcesResponse;
  },

  async replaceTopicChannel(
    syllabusId: string, 
    topicId: string, 
    payload: ReplaceChannelRequest
  ): Promise<TopicResourceMapping> {
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}/topics/${topicId}/replace-channel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response during channel replacement.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to replace channel for this topic.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as TopicResourceMapping;
  },

  async approveThirdChannel(syllabusId: string): Promise<ResourceDiscoveryResponse> {
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}/approve-third-channel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ approve: true }),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to approve third channel.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as ResourceDiscoveryResponse;
  },

  async discoverChannels(
    syllabusId: string, 
    languages: string[] = ['English'], 
    forceRefresh: boolean = false
  ): Promise<ChannelDiscoveryResponse> {
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}/channel-discovery`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ languages, force_refresh: forceRefresh }),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response during channel discovery.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to discover channels for course.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as ChannelDiscoveryResponse;
  },

  async previewStrategy(
    syllabusId: string,
    strategy: 'one_channel' | 'two_channels' | 'different_per_topic' | 'custom',
    languages: string[] = ['English'],
    selectedChannelNames?: string[],
    customAssignments?: Record<string, string>
  ): Promise<PreviewStrategyResponse> {
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}/preview-strategy`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        strategy,
        languages,
        selected_channel_names: selectedChannelNames,
        custom_assignments: customAssignments,
      }),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response during strategy preview.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to generate channel strategy preview.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as PreviewStrategyResponse;
  },

  async confirmStrategy(
    syllabusId: string,
    strategy: 'one_channel' | 'two_channels' | 'different_per_topic' | 'custom',
    languages: string[] = ['English'],
    selectedChannelNames?: string[],
    customAssignments?: Record<string, string>
  ): Promise<ResourceDiscoveryResponse> {
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}/confirm-strategy`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        strategy,
        languages,
        selected_channel_names: selectedChannelNames,
        custom_assignments: customAssignments,
      }),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response during strategy confirmation.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to confirm channel strategy and build video library.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as ResourceDiscoveryResponse;
  },

  async createStudyPlan(syllabusId: string, payload: StudyPlanCreateRequest): Promise<StudyPlanResponse> {
    const response = await authenticatedFetch(`${API_BASE}/study-plan/${syllabusId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response during study plan generation.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to generate personalized study plan.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as StudyPlanResponse;
  },

  async getStudyPlan(syllabusId: string): Promise<StudyPlanResponse> {
    const response = await authenticatedFetch(`${API_BASE}/study-plan/${syllabusId}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || `Failed to retrieve study plan for syllabus '${syllabusId}'.`;
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as StudyPlanResponse;
  },

  async updateTaskStatus(planId: string, taskId: string, completed: boolean): Promise<TaskItemSchema> {
    const response = await authenticatedFetch(`${API_BASE}/study-plan/${planId}/tasks/${taskId}/status`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ completed }),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to update task completion state.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as TaskItemSchema;
  },

  async saveTaskNote(planId: string, taskId: string, notes: string): Promise<TaskItemSchema> {
    const response = await authenticatedFetch(`${API_BASE}/study-plan/${planId}/tasks/${taskId}/notes`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ notes }),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to save task notes.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as TaskItemSchema;
  },

  async reschedulePlan(planId: string, options?: { missed_date?: string; from_date?: string }): Promise<StudyPlanResponse> {
    const response = await authenticatedFetch(`${API_BASE}/study-plan/${planId}/reschedule`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(options || {}),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response during rescheduling.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to reschedule study plan.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as StudyPlanResponse;
  },

  async getSettings(): Promise<UserSettingsSchema> {
    const response = await authenticatedFetch(`${API_BASE}/settings`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to retrieve settings.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as UserSettingsSchema;
  },

  async updateSettings(settingsData: UserSettingsSchema): Promise<UserSettingsSchema> {
    const response = await authenticatedFetch(`${API_BASE}/settings`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(settingsData),
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to update settings.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as UserSettingsSchema;
  },

  async getDiagnostics(): Promise<SystemDiagnosticsResponse> {
    const response = await authenticatedFetch(`${API_BASE}/diagnostics`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response during diagnostics check.', response.status);
    }

    if (!response.ok) {
      const errorMsg = responseData?.detail || 'Failed to retrieve system diagnostics.';
      throw new ApiErrorResponse(errorMsg, response.status);
    }

    return responseData as SystemDiagnosticsResponse;
  },

  async testYouTubeApi(): Promise<DiagnosticTestResult> {
    const response = await authenticatedFetch(`${API_BASE}/diagnostics/test-youtube`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response during YouTube test.', response.status);
    }

    return responseData as DiagnosticTestResult;
  },

  async testStrandsModel(): Promise<DiagnosticTestResult> {
    const response = await authenticatedFetch(`${API_BASE}/diagnostics/test-strands`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
    });

    let responseData: any;
    try {
      responseData = await response.json();
    } catch {
      throw new ApiErrorResponse('Server returned an unreadable response during Strands test.', response.status);
    }

    return responseData as DiagnosticTestResult;
  },

  // ============================================================================
  // Multi-Course Academic Management Endpoints
  // ============================================================================

  async getCourses(includeArchived: boolean = false): Promise<{ status: string; total_count: number; courses: Course[] }> {
    const params = new URLSearchParams({ include_archived: includeArchived.toString() });
    const response = await authenticatedFetch(`${API_BASE}/courses?${params.toString()}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });

    let data: any;
    try {
      data = await response.json();
    } catch {
      throw new ApiErrorResponse('Failed to parse courses response.', response.status);
    }

    if (!response.ok) {
      throw new ApiErrorResponse(data?.detail || 'Failed to fetch courses.', response.status);
    }

    return data;
  },

  async getCourse(courseId: string): Promise<Course> {
    const response = await authenticatedFetch(`${API_BASE}/courses/${courseId}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });

    let data: any;
    try {
      data = await response.json();
    } catch {
      throw new ApiErrorResponse('Failed to parse course response.', response.status);
    }

    if (!response.ok) {
      throw new ApiErrorResponse(data?.detail || 'Failed to fetch course.', response.status);
    }

    return data as Course;
  },

  async createCourse(payload: any): Promise<Course> {
    const response = await authenticatedFetch(`${API_BASE}/courses`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    let data: any;
    try {
      data = await response.json();
    } catch {
      throw new ApiErrorResponse('Failed to create course.', response.status);
    }

    if (!response.ok) {
      throw new ApiErrorResponse(data?.detail || 'Failed to create course.', response.status);
    }

    return data as Course;
  },

  async updateCourse(courseId: string, payload: any): Promise<Course> {
    const response = await authenticatedFetch(`${API_BASE}/courses/${courseId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    let data: any;
    try {
      data = await response.json();
    } catch {
      throw new ApiErrorResponse('Failed to update course.', response.status);
    }

    if (!response.ok) {
      throw new ApiErrorResponse(data?.detail || 'Failed to update course.', response.status);
    }

    return data as Course;
  },

  async archiveCourse(courseId: string, isArchived: boolean = true): Promise<any> {
    const params = new URLSearchParams({ is_archived: isArchived.toString() });
    const response = await authenticatedFetch(`${API_BASE}/courses/${courseId}/archive?${params.toString()}`, {
      method: 'POST',
      headers: { 'Accept': 'application/json' },
    });

    let data: any;
    try {
      data = await response.json();
    } catch {
      throw new ApiErrorResponse('Failed to archive course.', response.status);
    }

    if (!response.ok) {
      throw new ApiErrorResponse(data?.detail || 'Failed to archive course.', response.status);
    }

    return data;
  },

  async deleteCourse(courseId: string): Promise<any> {
    const response = await authenticatedFetch(`${API_BASE}/courses/${courseId}`, {
      method: 'DELETE',
      headers: { 'Accept': 'application/json' },
    });

    let data: any;
    try {
      data = await response.json();
    } catch {
      throw new ApiErrorResponse('Failed to delete course.', response.status);
    }

    if (!response.ok) {
      throw new ApiErrorResponse(data?.detail || 'Failed to delete course.', response.status);
    }

    return data;
  },

  async replaceCourseSyllabus(courseId: string, newSyllabusId: string, preserveCompletions: boolean = true): Promise<Course> {
    const response = await authenticatedFetch(`${API_BASE}/courses/${courseId}/replace-syllabus`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        new_syllabus_id: newSyllabusId,
        preserve_matching_completions: preserveCompletions,
      }),
    });

    let data: any;
    try {
      data = await response.json();
    } catch {
      throw new ApiErrorResponse('Failed to replace syllabus.', response.status);
    }

    if (!response.ok) {
      throw new ApiErrorResponse(data?.detail || 'Failed to replace syllabus.', response.status);
    }

    return data as Course;
  },

  async getSemesterOverview(): Promise<SemesterOverview> {
    const response = await authenticatedFetch(`${API_BASE}/courses/semester-overview`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });

    let data: any;
    try {
      data = await response.json();
    } catch {
      throw new ApiErrorResponse('Failed to parse semester overview.', response.status);
    }

    if (!response.ok) {
      throw new ApiErrorResponse(data?.detail || 'Failed to fetch semester overview.', response.status);
    }

    return data as SemesterOverview;
  },

  async setupAndAnalyzeSyllabus(payload: any): Promise<{
    status: string;
    course: Course;
    analysis: SyllabusAnalysisResponse;
    study_plan?: StudyPlanResponse;
  }> {
    const response = await authenticatedFetch(`${API_BASE}/courses/setup-and-analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    let data: any;
    try {
      data = await response.json();
    } catch {
      throw new ApiErrorResponse('Failed to analyze syllabus and create course.', response.status);
    }

    if (!response.ok) {
      throw new ApiErrorResponse(data?.detail || 'Syllabus setup and analysis failed.', response.status);
    }

    return data;
  },
};
