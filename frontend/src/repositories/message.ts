import { ApiHandler } from './apiHandler';
import { API_ROUTES } from '@/lib/constants';
import {
    MessageResponse,
    MessagesResponse,
} from '@/lib/types';

export const MessageRepository = {
    /**
     * Send message (chat endpoint that gets AI response)
     */
    sendChatMessage: async (sessionId: string, formData: FormData): Promise<MessageResponse> => {
        const response = await ApiHandler.sendPostRequest(
            API_ROUTES.MESSAGES.CHAT(sessionId), 
            formData,
            true,
        );
        return response.data;
    },

    /**
     * Get messages
     */
    getMessages: async (sessionId: string): Promise<MessagesResponse> => {
        const response = await ApiHandler.sendGetRequest(API_ROUTES.MESSAGES.LIST(sessionId));
        return response.data;
    },
};
