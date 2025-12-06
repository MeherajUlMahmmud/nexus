import { ApiHandler } from './apiHandler';
import { API_ROUTES } from '@/lib/constants';
import {
    APIResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
} from '@/lib/types';

export const AuthRepository = {
    /**
     * Login user
     */
    login: async (credentials: LoginRequest): Promise<TokenResponse> => {
        const response = await ApiHandler.sendUnauthenticatedPostRequest(API_ROUTES.AUTH.LOGIN, credentials);
        return response.data;
    },

    /**
     * Register new user
     */
    register: async (data: RegisterRequest): Promise<APIResponse> => {
        const response = await ApiHandler.sendUnauthenticatedPostRequest(API_ROUTES.AUTH.REGISTER, data);
        return response.data;
    },

    /**
     * Logout user
     */
    logout: async (refreshToken: string): Promise<void> => {
        await ApiHandler.sendPostRequest(API_ROUTES.AUTH.LOGOUT, {
            refresh: refreshToken,
        });
    },

    /**
     * Refresh access token
     */
    refreshToken: async (refreshToken: string): Promise<{ access: string }> => {
        const response = await ApiHandler.sendPostRequest(API_ROUTES.AUTH.REFRESH, { refresh: refreshToken });
        return response.data;
    },

    /**
     * Get current user
     */
    getCurrentUser: async (): Promise<UserResponse> => {
        const response = await ApiHandler.sendGetRequest(API_ROUTES.AUTH.ME);
        return response.data;
    },
};
