// Backend API Base URL
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';

// Backend API Routes
export const API_ROUTES = {
  // Auth routes
  AUTH: {
    LOGIN: `${API_BASE_URL}/auth/login`,
    REGISTER: `${API_BASE_URL}/auth/register`,
    REFRESH: `${API_BASE_URL}/auth/refresh`,
    ME: `${API_BASE_URL}/auth/me`,
    LOGOUT: `${API_BASE_URL}/auth/logout`,
  },
  // Session routes
  SESSIONS: {
    LIST: `${API_BASE_URL}/sessions/list`,
    CREATE: `${API_BASE_URL}/sessions/create`,
    DETAILS: (id: string) => `${API_BASE_URL}/sessions/${id}/details`,
    UPDATE: (id: string) => `${API_BASE_URL}/sessions/${id}/update`,
    DELETE: (id: string) => `${API_BASE_URL}/sessions/${id}/delete`,
  },
  // Message routes
  MESSAGES: {
    LIST: (sessionId: string) => `${API_BASE_URL}/sessions/${sessionId}/messages/list`,
    NEW: `${API_BASE_URL}/messages/new`,
    CHAT: (sessionId: string) => `${API_BASE_URL}/sessions/${sessionId}/messages/chat`,
  },
  // Transcription routes
  TRANSCRIBE: {
    TRANSCRIBE: `${API_BASE_URL}/transcribe`,
  },
  // Model routes
  MODELS: {
    LIST: `${API_BASE_URL}/models`,
  },
  // User routes
  USERS: {
    PROFILE: `${API_BASE_URL}/users/profile`,
    PASSWORD: `${API_BASE_URL}/users/password`,
    DELETE_ACCOUNT: `${API_BASE_URL}/users/account`,
  },
} as const;

export const APP_ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  PROFILE: '/profile',
  SETTINGS: '/settings',
} as const;
