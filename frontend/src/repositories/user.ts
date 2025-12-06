import { ApiHandler } from './apiHandler';
import { API_ROUTES } from '@/lib/constants';
import { APIResponse, User } from '@/lib/types';

export interface UserUpdate {
    username?: string;
    email?: string;
}

export interface PasswordChange {
    current_password: string;
    new_password: string;
}

export const UserRepository = {
    /**
     * Update user profile
     */
    updateProfile: async (userUpdate: UserUpdate): Promise<APIResponse<User>> => {
        const response = await ApiHandler.sendPutRequest(API_ROUTES.USERS.PROFILE, userUpdate);
        return response.data;
    },

    /**
     * Change user password
     */
    changePassword: async (passwordChange: PasswordChange): Promise<APIResponse<null>> => {
        const response = await ApiHandler.sendPutRequest(API_ROUTES.USERS.PASSWORD, passwordChange);
        return response.data;
    },

    /**
     * Delete user account
     */
    deleteAccount: async (password: string): Promise<APIResponse<null>> => {
        const response = await ApiHandler.sendDeleteRequest(API_ROUTES.USERS.DELETE_ACCOUNT, { password });
        return response.data;
    },
};
