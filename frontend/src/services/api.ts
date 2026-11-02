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

// Resolves API Base URL for local development and production deployments
export const getApiBaseUrl = (): string => {
  const envUrl = (import.meta.env.VITE_API_URL as string)?.trim();
  if (envUrl) {
    const clean = envUrl.replace(/\/$/, '');
    return clean.endsWith('/api') ? clean : `${clean}/api`;
  }
  // Local development default: directly target local FastAPI backend
  if (import.meta.env.DEV) {
    return 'http://127.0.0.1:8000/api';
  }
  // Production fallback: relative /api routed by Vercel serverless functions
  return '/api';
};

export const API_BASE = getApiBaseUrl();

export class ApiErrorResponse extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiErrorResponse';
    this.status = status;
  }
}

// Map of in-flight GET requests for transparent client-side deduplication
const inFlightGetRequests = new Map<string, Promise<Response>>();

/**
 * Custom authenticated fetch wrapper that injects Supabase JWT access token
 * into outgoing API requests as `Authorization: Bearer <token>`.
 * Dispatches an event on 401 Unauthorized so the UI can prompt for re-authentication.
 * Automatically deduplicates concurrent in-flight GET requests to eliminate redundant network traffic.
 */
async function authenticatedFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const method = (init?.method || 'GET').toUpperCase();
  const isGet = method === 'GET';
  const urlKey = typeof input === 'string' ? input : (input instanceof URL ? input.toString() : input.url);

  // Invalidate any cached in-flight GET promises when a mutation is issued
  if (!isGet) {
    inFlightGetRequests.clear();
  }

  // Return cloned response for concurrent duplicate in-flight GET requests
  if (isGet && inFlightGetRequests.has(urlKey)) {
    try {
      const inFlight = await inFlightGetRequests.get(urlKey)!;
      return inFlight.clone();
    } catch {
      // If previous in-flight failed, proceed to fresh fetch
    }
  }

  const token = await getSupabaseAccessToken();
  const headers = new Headers(init?.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Enforce a client-side timeout (adaptive: 180s for AI/uploads/study-plan, 60s for standard requests)
  const urlStr = typeof input === 'string' ? input : ((input as Request)?.url || '');
  const isHeavyOperation = (
    urlStr.includes('/syllabus/upload') ||
    urlStr.includes('/setup-and-analyze') ||
    urlStr.includes('/analyze') ||
    urlStr.includes('/study-plan') ||
    urlStr.includes('/strategy') ||
    urlStr.includes('/channel-discovery') ||
    urlStr.includes('/approve-third-channel')
  );
  const customTimeout = (init as any)?.timeoutMs;
  const timeoutMs = customTimeout || (isHeavyOperation ? 180000 : 60000);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  if (init?.signal) {
    init.signal.addEventListener('abort', () => controller.abort());
  }

  const executeFetch = async (): Promise<Response> => {
    try {
      const response = await window.fetch(input, {
        ...init,
        signal: controller.signal,
        headers,
      });

      if (response.status === 401 && typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('syllabussync:unauthorized'));
      }

      return response;
    } catch (err: any) {
      if (err.name === 'AbortError') {
        throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)} seconds. Please check your network connection and retry.`);
      }
      throw err;
    } finally {
      clearTimeout(timeoutId);
      if (isGet) {
        inFlightGetRequests.delete(urlKey);
      }
    }
  };

  if (isGet) {
    const fetchPromise = executeFetch();
    inFlightGetRequests.set(urlKey, fetchPromise);
    const resp = await fetchPromise;
    return resp.clone();
  }

  return executeFetch();
}

/**
 * Safely parses response JSON or plain text/HTML errors from the backend.
 * Provides clear human-friendly messages for HTTP 400, 401, 403, 404, 413, 422, 429, 500, 502, 504,
 * and Vercel serverless platform errors (FUNCTION_INVOCATION_FAILED, payload limits).
 */
async function handleApiResponse<T = any>(response: Response, defaultErrorPrefix: string = 'Operation failed'): Promise<T> {
  let responseData: any = null;
  let rawText = '';

  try {
    rawText = await response.text();
    if (rawText.trim()) {
      responseData = JSON.parse(rawText);
    }
  } catch {
    // Non-JSON responses preserved in rawText
  }

  if (!response.ok) {
    let errorMsg = '';

    // 1. Structured FastAPI detail response
    if (responseData && typeof responseData === 'object' && responseData.detail) {
      if (typeof responseData.detail === 'string') {
        errorMsg = responseData.detail.replace(/^Value error,\s*/i, '');
      } else if (Array.isArray(responseData.detail)) {
        errorMsg = responseData.detail.map((d: any) => (d.msg || JSON.stringify(d)).replace(/^Value error,\s*/i, '')).join(', ');
      }
    }
    // 2. Vercel serverless error strings
    else if (rawText) {
      const cleanText = rawText.trim();
      if (cleanText.includes('FUNCTION_INVOCATION_FAILED')) {
        errorMsg = 'Backend service is starting or encountered a serverless invocation error (HTTP 500). Please retry in a few moments.';
      } else if (cleanText.includes('FUNCTION_PAYLOAD_TOO_LARGE') || response.status === 413) {
        errorMsg = 'Uploaded file exceeds the maximum allowed request size (4.5 MB).';
      } else if (response.status === 502 || response.status === 504) {
        errorMsg = `Backend gateway error or timeout (HTTP ${response.status}).`;
      } else if (cleanText.length < 200 && !cleanText.startsWith('<')) {
        errorMsg = cleanText;
      }
    }

    // 3. Fallback standard HTTP status descriptions
    if (!errorMsg) {
      switch (response.status) {
        case 400: errorMsg = `${defaultErrorPrefix}: Invalid request parameters.`; break;
        case 401: errorMsg = 'Authentication required or session expired. Please sign in again.'; break;
        case 403: errorMsg = 'Access denied: You do not have permission to access or modify this resource.'; break;
        case 404: errorMsg = `${defaultErrorPrefix}: Requested resource not found.`; break;
        case 413: errorMsg = 'File or payload too large. Maximum allowed size is 4.5 MB.'; break;
        case 422: errorMsg = `${defaultErrorPrefix}: Validation error in request data.`; break;
        case 429: errorMsg = 'Rate limit exceeded. Please wait a moment before trying again.'; break;
        case 500: errorMsg = `${defaultErrorPrefix}: Internal server error (HTTP 500).`; break;
        case 502: errorMsg = 'Backend service unavailable (HTTP 502 Bad Gateway).'; break;
        case 504: errorMsg = 'Backend request timed out (HTTP 504 Gateway Timeout).'; break;
        default: errorMsg = `${defaultErrorPrefix} (HTTP ${response.status}).`;
      }
    }

    throw new ApiErrorResponse(errorMsg, response.status);
  }

  if (responseData !== null) {
    return responseData as T;
  }

  if (!rawText.trim()) {
    return {} as T;
  }

  throw new ApiErrorResponse(`Server returned an unreadable response (HTTP ${response.status}).`, response.status);
}

// In-flight deduplication and sequence guards for health polling
let inFlightHealthPromise: Promise<HealthResponse> | null = null;
let lastHealthFetchTime = 0;
let lastHealthResponse: HealthResponse | null = null;
let healthSequenceNumber = 0;
const HEALTH_DEBOUNCE_MS = 1500;

export const apiService = {
  async getHealth(forceRefresh: boolean = false): Promise<HealthResponse> {
    const now = Date.now();
    // Return recent cached response if available and not forced
    if (!forceRefresh && lastHealthResponse && (now - lastHealthFetchTime < HEALTH_DEBOUNCE_MS)) {
      return lastHealthResponse;
    }
    // Share existing in-flight promise to prevent concurrent overlapping calls
    if (inFlightHealthPromise) {
      return inFlightHealthPromise;
    }

    const currentSeq = ++healthSequenceNumber;

    const executeProbe = async (attempt: number = 0): Promise<HealthResponse> => {
      const controller = new AbortController();
      const timeoutMs = 5000;
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      try {
        const response = await window.fetch(`${API_BASE}/health`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
          },
          signal: controller.signal,
        });

        const data = await handleApiResponse<HealthResponse>(response, 'Health check failed');
        // Prevent stale responses from overwriting newer sequences
        if (currentSeq >= healthSequenceNumber) {
          lastHealthResponse = data;
          lastHealthFetchTime = Date.now();
        }
        return data;
      } catch (err: any) {
        // Automatic retry with backoff on momentary network glitch (attempt 0 only)
        if (attempt === 0 && (err.name === 'AbortError' || err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError'))) {
          await new Promise((res) => setTimeout(res, 500));
          return executeProbe(1);
        }

        // Do not cache failed health results
        if (currentSeq >= healthSequenceNumber) {
          lastHealthResponse = null;
          lastHealthFetchTime = 0;
        }

        if (err.name === 'AbortError') {
          throw new Error('Health check request timed out after 5 seconds.');
        }
        if (err instanceof ApiErrorResponse) {
          throw err;
        }
        throw new Error(err?.message || 'Unable to connect to SyllabusSync AI backend API.');
      } finally {
        clearTimeout(timeoutId);
      }
    };

    inFlightHealthPromise = executeProbe().finally(() => {
      inFlightHealthPromise = null;
    });

    return inFlightHealthPromise;
  },

  async uploadSyllabus(file: File): Promise<SyllabusUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await authenticatedFetch(`${API_BASE}/syllabus/upload`, {
      method: 'POST',
      body: formData,
    });

    return await handleApiResponse<SyllabusUploadResponse>(response, 'An unexpected error occurred while parsing the syllabus.');
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

    return await handleApiResponse<SyllabusAnalysisResponse>(response, 'An unexpected error occurred while analyzing syllabus topics with Strands Agents SDK.');
  },

  async getSyllabus(syllabusId: string): Promise<SyllabusAnalysisResponse> {
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    return await handleApiResponse<SyllabusAnalysisResponse>(response, '${syllabusId}');
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

    return await handleApiResponse<SyllabusAnalysisResponse>(response, 'Failed to update syllabus topics.');
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

    return await handleApiResponse<ResourceDiscoveryResponse>(response, 'Failed to discover YouTube educational resources.');
  },

  async getResources(syllabusId: string): Promise<ResourceDiscoveryResponse> {
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}/resources`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    return await handleApiResponse<ResourceDiscoveryResponse>(response, '${syllabusId}');
  },

  async getTopicAlternatives(syllabusId: string, topicId: string, language: string = 'English'): Promise<AlternativeResourcesResponse> {
    const params = new URLSearchParams({ language });
    const response = await authenticatedFetch(`${API_BASE}/syllabus/${syllabusId}/topics/${topicId}/alternatives?${params.toString()}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    return await handleApiResponse<AlternativeResourcesResponse>(response, 'Failed to fetch alternative channels for this topic.');
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

    return await handleApiResponse<TopicResourceMapping>(response, 'Failed to replace channel for this topic.');
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

    return await handleApiResponse<ResourceDiscoveryResponse>(response, 'Failed to approve third channel.');
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

    return await handleApiResponse<ChannelDiscoveryResponse>(response, 'Failed to discover channels for course.');
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

    return await handleApiResponse<PreviewStrategyResponse>(response, 'Failed to generate channel strategy preview.');
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

    return await handleApiResponse<ResourceDiscoveryResponse>(response, 'Failed to confirm channel strategy and build video library.');
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

    return await handleApiResponse<StudyPlanResponse>(response, 'Failed to generate personalized study plan.');
  },

  async getStudyPlan(syllabusId: string): Promise<StudyPlanResponse> {
    const response = await authenticatedFetch(`${API_BASE}/study-plan/${syllabusId}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    return await handleApiResponse<StudyPlanResponse>(response, '${syllabusId}');
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

    return await handleApiResponse<TaskItemSchema>(response, 'Failed to update task completion state.');
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

    return await handleApiResponse<TaskItemSchema>(response, 'Failed to save task notes.');
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

    return await handleApiResponse<StudyPlanResponse>(response, 'Failed to reschedule study plan.');
  },

  async getSettings(): Promise<UserSettingsSchema> {
    const response = await authenticatedFetch(`${API_BASE}/settings`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    return await handleApiResponse<UserSettingsSchema>(response, 'Failed to retrieve settings.');
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

    return await handleApiResponse<UserSettingsSchema>(response, 'Failed to update settings.');
  },

  async getDiagnostics(): Promise<SystemDiagnosticsResponse> {
    const response = await authenticatedFetch(`${API_BASE}/diagnostics`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      ...({ timeoutMs: 8000 } as any),
    });

    return await handleApiResponse<SystemDiagnosticsResponse>(response, 'Failed to retrieve system diagnostics.');
  },

  async testYouTubeApi(): Promise<DiagnosticTestResult> {
    const response = await authenticatedFetch(`${API_BASE}/diagnostics/test-youtube`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
      ...({ timeoutMs: 8000 } as any),
    });

    return await handleApiResponse<DiagnosticTestResult>(response, 'Server returned an unreadable response during YouTube test.');
  },

  async testStrandsModel(): Promise<DiagnosticTestResult> {
    const response = await authenticatedFetch(`${API_BASE}/diagnostics/test-strands`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
      ...({ timeoutMs: 8000 } as any),
    });

    return await handleApiResponse<DiagnosticTestResult>(response, 'Server returned an unreadable response during Strands test.');
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

    return await handleApiResponse(response, 'Failed to fetch courses.');
  },

  async getCourse(courseId: string): Promise<Course> {
    const response = await authenticatedFetch(`${API_BASE}/courses/${courseId}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });

    return await handleApiResponse<Course>(response, 'Failed to fetch course.');
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

    return await handleApiResponse<Course>(response, 'Failed to create course.');
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

    return await handleApiResponse<Course>(response, 'Failed to update course.');
  },

  async archiveCourse(courseId: string, isArchived: boolean = true): Promise<any> {
    const params = new URLSearchParams({ is_archived: isArchived.toString() });
    const response = await authenticatedFetch(`${API_BASE}/courses/${courseId}/archive?${params.toString()}`, {
      method: 'POST',
      headers: { 'Accept': 'application/json' },
    });

    return await handleApiResponse(response, 'Failed to archive course.');
  },

  async deleteCourse(courseId: string): Promise<any> {
    const response = await authenticatedFetch(`${API_BASE}/courses/${courseId}`, {
      method: 'DELETE',
      headers: { 'Accept': 'application/json' },
    });

    return await handleApiResponse(response, 'Failed to delete course.');
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

    return await handleApiResponse<Course>(response, 'Failed to replace syllabus.');
  },

  async getSemesterOverview(): Promise<SemesterOverview> {
    const response = await authenticatedFetch(`${API_BASE}/courses/semester-overview`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });

    return await handleApiResponse<SemesterOverview>(response, 'Failed to fetch semester overview.');
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

    return await handleApiResponse(response, 'Syllabus setup and analysis failed.');
  },
};
