import type { HealthResponse, SyllabusUploadResponse } from '../types';

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
};
