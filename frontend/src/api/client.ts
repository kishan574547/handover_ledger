import { DemoRole, AIHealthData, BackendHealthData, GitHubHealthData, ProjectData } from '../types';
import { sanitizeSecrets } from '../utils/sanitize';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export function getStoredRole(): DemoRole {
  return (localStorage.getItem('handover_demo_role') as DemoRole) || 'lead';
}

export type ApiErrorKind = 'network' | 'timeout' | 'client' | 'server';

export class ApiClientError extends Error {
  kind: ApiErrorKind;
  statusCode?: number;
  details?: string;
  url: string;

  constructor(params: {
    message: string;
    kind: ApiErrorKind;
    statusCode?: number;
    details?: string;
    url: string;
  }) {
    super(params.message);
    this.name = 'ApiClientError';
    this.kind = params.kind;
    this.statusCode = params.statusCode;
    this.details = params.details;
    this.url = params.url;
  }
}

export function setStoredRole(role: DemoRole): void {
  localStorage.setItem('handover_demo_role', role);
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  customRole?: DemoRole
): Promise<T> {
  const role = customRole || getStoredRole();
  const headers = new Headers(options.headers || {});

  headers.set('X-Demo-Role', role);

  // If payload is not FormData, set Content-Type to application/json
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  // Set up 45-second timeout controller
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 45000);

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      signal: options.signal || controller.signal,
    });
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err?.name === 'AbortError') {
      throw new ApiClientError({
        message: 'The server took too long. Try again.',
        kind: 'timeout',
        details: `Request to ${url} exceeded 45s timeout.`,
        url,
      });
    }
    // Browser network error (e.g. server down, connection refused, CORS failure)
    throw new ApiClientError({
      message: `Cannot reach the server. Check that the backend is running at ${API_BASE_URL}.`,
      kind: 'network',
      details: sanitizeSecrets(err?.message || 'Network connection failed or was blocked by the browser.'),
      url,
    });
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    let errJson: any = null;
    let rawText = '';
    try {
      errJson = await response.json();
    } catch {
      try {
        rawText = await response.text();
      } catch {
        // ignore
      }
    }

    const serverMessage = errJson?.message || errJson?.detail || rawText || `HTTP ${response.status}`;
    const technicalDetail = typeof errJson?.detail === 'object'
      ? JSON.stringify(errJson.detail)
      : (errJson?.technical_detail || rawText || `HTTP status ${response.status}`);

    if (response.status >= 400 && response.status < 500) {
      throw new ApiClientError({
        message: sanitizeSecrets(typeof serverMessage === 'string' ? serverMessage : JSON.stringify(serverMessage)),
        kind: 'client',
        statusCode: response.status,
        details: sanitizeSecrets(technicalDetail),
        url,
      });
    } else {
      // 5xx Server Error
      throw new ApiClientError({
        message: 'Something went wrong on our side.',
        kind: 'server',
        statusCode: response.status,
        details: sanitizeSecrets(typeof serverMessage === 'string' ? serverMessage : technicalDetail),
        url,
      });
    }
  }

  // Handle blob/text downloads like export
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('text/markdown')) {
    return (await response.text()) as unknown as T;
  }

  return response.json();
}

// API methods
export const api = {
  // Project & Demo
  getProject: () => request<ProjectData>('/project'),
  healthCheck: () => request<BackendHealthData>('/health'),
  getAIHealth: () => request<AIHealthData>('/health/ai'),
  getGitHubHealth: () => request<GitHubHealthData>('/health/github'),
  loadDemo: () => request<any>('/demo/load', { method: 'POST' }),
  resetDemo: () => request<any>('/demo/reset', { method: 'POST' }),
  updateProjectMembers: (data: { project_name?: string; departing_member?: string; successor_name?: string }) =>
    request<any>('/project/members', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  // Dashboard
  getDashboard: () => request<any>('/dashboard'),

  // Sources
  getSources: () => request<any>('/sources'),
  addGithubSource: (url: string) =>
    request<any>('/sources/github', {
      method: 'POST',
      body: JSON.stringify({ url }),
    }),
  uploadSource: (formData: FormData) =>
    request<any>('/sources/upload', {
      method: 'POST',
      body: formData,
    }),
  updateSourceClearance: (id: string, clearance: number) =>
    request<any>(`/sources/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ clearance }),
    }),
  deleteSource: (id: string) =>
    request<any>(`/sources/${id}`, { method: 'DELETE' }),

  // Analysis
  triggerAnalysis: (force?: boolean) => request<any>(`/analysis/run${force ? '?force=true' : ''}`, { method: 'POST' }),
  resetAnalysis: () => request<any>('/analysis/reset', { method: 'POST' }),
  getAnalysisStatus: () => request<any>('/analysis/status'),

  // Claims
  getClaims: (params: Record<string, string | number | boolean | undefined> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '') query.append(k, String(v));
    });
    const qs = query.toString();
    return request<any>(`/claims${qs ? `?${qs}` : ''}`);
  },
  getClaimDetail: (id: string) => request<any>(`/claims/${id}`),
  updateClaim: (id: string, data: { text?: string; review_state?: string; note?: string }) =>
    request<any>(`/claims/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  approveAllVerified: () =>
    request<any>('/claims/approve-verified', { method: 'POST' }),
  resolveConflict: (id: string, data: { choice: string; text?: string }) =>
    request<any>(`/claims/${id}/resolve-conflict`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  addClaimComment: (id: string, text: string) =>
    request<any>(`/claims/${id}/comments`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  // Timeline
  getTimeline: () => request<any>('/timeline'),

  // Questions (Exit Interview)
  getQuestions: (params: { state?: string; priority?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.state) query.append('state', params.state);
    if (params.priority) query.append('priority', params.priority);
    const qs = query.toString();
    return request<any>(`/questions${qs ? `?${qs}` : ''}`);
  },
  generateQuestions: () => request<any>('/questions/generate', { method: 'POST' }),
  answerQuestion: (id: string, answer: string) =>
    request<any>(`/questions/${id}/answer`, {
      method: 'PUT',
      body: JSON.stringify({ answer }),
    }),
  skipQuestion: (id: string) =>
    request<any>(`/questions/${id}/skip`, { method: 'POST' }),
  unknownQuestion: (id: string) =>
    request<any>(`/questions/${id}/unknown`, { method: 'POST' }),

  // Review & Approve
  getReviewSummary: () => request<any>('/review/summary'),
  createVersion: (note?: string) =>
    request<any>('/handover/versions', {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),
  getVersions: () => request<any>('/handover/versions'),
  compareVersions: (a: number, b: number) =>
    request<any>(`/handover/versions/${a}/diff/${b}`),
  approveHandover: (note?: string, accept_open_items: boolean = true) =>
    request<any>('/handover/approve', {
      method: 'POST',
      body: JSON.stringify({ note, accept_open_items }),
    }),
  sendBackHandover: (note: string) =>
    request<any>('/handover/send-back', {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),

  // Handover View & Actions
  getHandoverView: (previewRole?: string) => {
    const qs = previewRole ? `?role=${previewRole}` : '';
    return request<any>(`/handover/view${qs}`);
  },
  runLeakCheck: (previewRole?: string) => {
    const qs = previewRole ? `?role=${previewRole}` : '';
    return request<any>(`/handover/leak-check${qs}`, { method: 'POST' });
  },
  acknowledgeHandover: (name: string) =>
    request<any>('/handover/acknowledge', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  assignSuccessor: (claimId: string) =>
    request<any>('/handover/assign-successor', {
      method: 'POST',
      body: JSON.stringify({ claim_id: claimId }),
    }),
  exportHandoverMarkdown: (previewRole?: string) => {
    const tz = encodeURIComponent(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
    const qs = previewRole ? `?role=${previewRole}&format=md&tz=${tz}` : `?format=md&tz=${tz}`;
    return request<string>(`/handover/export${qs}`);
  },

  // Activity
  getActivityLogs: (role?: string) => {
    const qs = role ? `?role=${role}` : '';
    return request<any>(`/activity${qs}`);
  },

  // Ask the Handover
  askHandover: (question: string) =>
    request<any>('/ask', {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),
  askHelp: (question: string) =>
    request<{ answer: string; suggested_steps: string[] }>('/ask/help', {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),
  sendQuestionToLeaver: (question: string, why_we_ask?: string) =>
    request<any>('/ask/send-to-leaver', {
      method: 'POST',
      body: JSON.stringify({ question, why_we_ask }),
    }),
};

