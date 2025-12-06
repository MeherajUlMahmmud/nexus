import { ApiHandler } from './apiHandler';
import { API_ROUTES } from '@/lib/constants';
import {
    SessionCreate,
    SessionResponse,
    SessionsResponse,
} from '@/lib/types';

export const SessionRepository = {
    /**
     * Create new session
     */
    createSession: async (data: SessionCreate): Promise<SessionResponse> => {
        const response = await ApiHandler.sendPostRequest(API_ROUTES.SESSIONS.CREATE, data);
        return response.data;
    },
    /**
     * Get sessions
     */
    getSessions: async (): Promise<SessionsResponse> => {
        const response = await ApiHandler.sendGetRequest(API_ROUTES.SESSIONS.LIST);
        return response.data;
    },
    /**
     * Get session details
     */
    getSessionDetails: async (sessionId: number): Promise<SessionResponse> => {
        const response = await ApiHandler.sendGetRequest(API_ROUTES.SESSIONS.DETAILS(sessionId));
        return response.data;
    },
    /**
     * Delete session
     */
    deleteSession: async (sessionId: number): Promise<void> => {
        await ApiHandler.sendDeleteRequest(API_ROUTES.SESSIONS.DELETE(sessionId));
    },
};
