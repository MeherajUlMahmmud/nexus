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
    sendChatMessage: async (sessionId: number, content: string): Promise<MessageResponse> => {
        const response = await ApiHandler.sendPostRequest(API_ROUTES.MESSAGES.CHAT(sessionId), { content });
        return response.data;
    },

    /**
     * Send new message
     */
    sendNewMessage: async (message: string): Promise<MessageResponse> => {
        const response = await ApiHandler.sendPostRequest(API_ROUTES.MESSAGES.NEW, { message });
        return response.data;
    },

    /**
     * Get messages
     */
    getMessages: async (sessionId: number): Promise<MessagesResponse> => {
        const response = await ApiHandler.sendGetRequest(API_ROUTES.MESSAGES.LIST(sessionId));
        return response.data;
    },
};
