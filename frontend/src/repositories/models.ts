import { ApiHandler } from './apiHandler';
import { API_ROUTES } from '@/lib/constants';
import { ModelsResponse } from '@/lib/types';

export const ModelsRepository = {
    /**
     * Get available AI models
     */
    getModels: async (): Promise<ModelsResponse> => {
        const response = await ApiHandler.sendGetRequest(API_ROUTES.MODELS.LIST);
        return response.data;
    },
};
