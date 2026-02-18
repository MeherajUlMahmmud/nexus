import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { RegisterRequest, User } from '@/lib/types';
import { storage } from '@/lib/storage';
import { APP_ROUTES } from '@/lib/constants';
import { AuthRepository } from '@/repositories/auth';
import { toast } from 'sonner';

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (usernameOrEmail: string, password: string) => Promise<void>;
    register: (data: RegisterRequest) => Promise<void>;
    logout: () => void;
    refreshUser: (setLoadingState?: boolean) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    // Initialize user from localStorage
    const [user, setUser] = useState<User | null>(() => storage.getUser());
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    const refreshUser = useCallback(async (setLoadingState: boolean = true) => {
        if (setLoadingState) {
            setLoading(true);
        }
        try {
            const response = await AuthRepository.getCurrentUser();
            if (response && response.status === "SUCCESS") {
                setUser(response.data);
                storage.setUser(response.data);
            } else if (response && response.status === "FAIL") {
                throw new Error(response.message);
            } else {
                throw new Error('Failed to fetch user');
            }
        } catch (error) {
            console.error('Failed to fetch user:', error);
            storage.clearAuth();
            setUser(null);
        } finally {
            if (setLoadingState) {
                setLoading(false);
            }
        }
    }, []);

    useEffect(() => {
        const storedUser = storage.getUser();
        const accessToken = storage.getAccessToken();

        if (storedUser || accessToken) {
            // If we have a user or token in storage, try to refresh/validate the user
            refreshUser();
        } else {
            // Only clear auth if we have neither user nor token
            storage.clearAuth();
            setUser(null);
            storage.setAccessToken(null);
            setLoading(false);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Set up axios interceptor to handle 401 responses (fallback if refresh fails)
    useEffect(() => {
        const interceptor = axios.interceptors.response.use(
            (response) => response,
            async (error) => {
                if (error.response?.status === 401) {
                    // Only clear auth if refresh token is also invalid/expired
                    // The apiHandler will try to refresh first
                    const refreshToken = storage.getRefreshToken();
                    if (!refreshToken) {
                        storage.clearAuth();
                        setUser(null);
                        navigate(APP_ROUTES.LOGIN, { replace: true });
                    }
                }
                return Promise.reject(error);
            }
        );

        return () => {
            axios.interceptors.response.eject(interceptor);
        };
    }, [navigate]);

    const login = async (usernameOrEmail: string, password: string) => {
        try {
            const loginData = usernameOrEmail.includes('@')
                ? { email: usernameOrEmail, password }
                : { username: usernameOrEmail, password };

            const response = await AuthRepository.login(loginData);

            // Double check response success
            if (response && response.status === "SUCCESS") {
                storage.setTokenResponse(response);
                setUser(response.data.user);
                navigate(APP_ROUTES.HOME, { replace: true });
            } else if (response && response.status === "FAIL") {
                throw new Error(response.message);
            } else {
                throw new Error('Login failed');
            }
        } catch (error: any) {
            const message =
                error?.response?.data?.message ||
                error?.message ||
                'Failed to login. Please check your credentials.';
            throw new Error(message);
        }
    };

    const register = async (registerRequest: RegisterRequest) => {
        try {
            const response = await AuthRepository.register(registerRequest);
            if (response && response.status === "SUCCESS") {
                toast.success('Registration successful');
                navigate(APP_ROUTES.LOGIN, { replace: true });
            } else if (response && response.status === "FAIL") {
                toast.error(response.message);
                throw new Error(response.message);
            } else {
                toast.error('Failed to register');
                throw new Error('Failed to register');
            }
        } catch (error: any) {
            const message =
                error?.response?.data?.message ||
                error?.message ||
                'Failed to register. Please try again.';
            // Only show toast if not already shown (from response.status === "FAIL" case)
            if (!error?.message || error.message === 'Failed to register') {
                toast.error(message);
            }
            throw new Error(message);
        }
    };

    const logout = async () => {
        try {
            const refreshToken = storage.getRefreshToken();
            if (refreshToken) {
                await AuthRepository.logout(refreshToken);
            }
        } catch (error) {
            console.error('Failed to logout:', error);
        } finally {
            storage.clearAuth();
            setUser(null);
            navigate(APP_ROUTES.LOGIN);
        }
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}