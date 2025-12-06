import { ApiHandler } from './apiHandler';
import { API_ROUTES } from '@/lib/constants';
import {
    TranscribeResponse,
} from '@/lib/types';

export const TranscribeRepository = {
    /**
     * Transcribe audio
     */
    transcribeAudio: async (formData: FormData): Promise<TranscribeResponse> => {
        const response = await ApiHandler.sendPostRequest(
            API_ROUTES.TRANSCRIBE.TRANSCRIBE,
            formData,
            true,
        );
        return response.data;
    },
};
