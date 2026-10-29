import type { 
  HealthResponse, 
  SyllabusUploadResponse, 
  SyllabusAnalysisResponse, 
  TopicUpdateRequest 
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
};
