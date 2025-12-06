import { User, TokenResponse } from './types';

const STORAGE_KEYS = {
  USER: 'nexus_user',
  ACCESS_TOKEN: 'nexus_access_token',
} as const;

// User storage
export const storage = {
  // User
  getUser: (): User | null => {
    try {
      const userStr = localStorage.getItem(STORAGE_KEYS.USER);
      if (!userStr) return null;
      return JSON.parse(userStr) as User;
    } catch (error) {
      console.error('Failed to get user from storage:', error);
      return null;
    }
  },

  setUser: (user: User | null): void => {
    try {
      if (user) {
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
      } else {
        localStorage.removeItem(STORAGE_KEYS.USER);
      }
    } catch (error) {
      console.error('Failed to set user in storage:', error);
    }
  },

  // Access Token
  getAccessToken: (): string | null => {
    try {
      return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    } catch (error) {
      console.error('Failed to get access token from storage:', error);
      return null;
    }
  },

  setAccessToken: (token: string | null): void => {
    try {
      if (token) {
        localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, token);
      } else {
        localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
      }
    } catch (error) {
      console.error('Failed to set access token in storage:', error);
    }
  },

  // Token Response (saves both user and token)
  setTokenResponse: (tokenResponse: TokenResponse): void => {
    storage.setUser(tokenResponse.data.user);
    storage.setAccessToken(tokenResponse.data.access_token);
  },

  // Clear all auth data
  clearAuth: (): void => {
    localStorage.removeItem(STORAGE_KEYS.USER);
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
  },
};
