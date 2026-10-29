import type { 
  HealthResponse, 
  SyllabusUploadResponse, 
  SyllabusAnalysisResponse, 
  TopicUpdateRequest,
  ResourceDiscoveryResponse,
  AlternativeResourcesResponse,
  ReplaceChannelRequest,
  TopicResourceMapping,
  StudyPlanResponse,
  StudyPlanCreateRequest,
  TaskItemSchema,
  UserSettingsSchema
} from '../types';

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

export const apiService = {
  async getHealth(): Promise<HealthResponse> {
    try {
      const response = await fetch(`${API_BASE}/health`, {
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

    const response = await fetch(`${API_BASE}/syllabus/upload`, {
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

    const response = await fetch(`${API_BASE}/syllabus/analyze`, {
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
    const response = await fetch(`${API_BASE}/syllabus/${syllabusId}`, {
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
    const response = await fetch(`${API_BASE}/syllabus/${syllabusId}/topics`, {
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
    const response = await fetch(`${API_BASE}/syllabus/${syllabusId}/discover-resources`, {
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
    const response = await fetch(`${API_BASE}/syllabus/${syllabusId}/resources`, {
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
    const response = await fetch(`${API_BASE}/syllabus/${syllabusId}/topics/${topicId}/alternatives?${params.toString()}`, {
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
    const response = await fetch(`${API_BASE}/syllabus/${syllabusId}/topics/${topicId}/replace-channel`, {
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
    const response = await fetch(`${API_BASE}/syllabus/${syllabusId}/approve-third-channel`, {
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

  async createStudyPlan(syllabusId: string, payload: StudyPlanCreateRequest): Promise<StudyPlanResponse> {
    const response = await fetch(`${API_BASE}/study-plan/${syllabusId}`, {
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
    const response = await fetch(`${API_BASE}/study-plan/${syllabusId}`, {
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
    const response = await fetch(`${API_BASE}/study-plan/${planId}/tasks/${taskId}/status`, {
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
    const response = await fetch(`${API_BASE}/study-plan/${planId}/tasks/${taskId}/notes`, {
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
    const response = await fetch(`${API_BASE}/study-plan/${planId}/reschedule`, {
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
    const response = await fetch(`${API_BASE}/settings`, {
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
    const response = await fetch(`${API_BASE}/settings`, {
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
};
