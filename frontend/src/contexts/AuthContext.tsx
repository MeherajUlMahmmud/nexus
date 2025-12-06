import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { RegisterRequest, User } from '@/lib/types';
import { storage } from '@/lib/storage';
import { APP_ROUTES } from '@/lib/constants';
import { AuthRepository } from '@/repositories/auth';

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

    const login = async (usernameOrEmail: string, password: string) => {
        try {
            setLoading(true);
            const loginData = usernameOrEmail.includes('@')
                ? { email: usernameOrEmail, password }
                : { username: usernameOrEmail, password };

            const response = await AuthRepository.login(loginData);

            console.log('response', response);

            // Double check response success
            if (response && response.status === "SUCCESS") {
                setUser(response.data.user);
                storage.setUser(response.data.user);
                storage.setAccessToken(response.data.access_token);
                setLoading(false);
                navigate(APP_ROUTES.HOME, { replace: true });
            } else if (response && response.status === "FAIL") {
                throw new Error(response.message);
            } else {
                throw new Error('Login failed');
            }
        } catch (error) {
            setLoading(false);
            throw new Error('Failed to login');
        }
    };

    const register = async (registerRequest: RegisterRequest) => {
        // try {
        //   setLoading(true);
        //   const response = await AuthRepository.register(registerRequest);

        //   setUser(response.user);

        //   storage.setUser(response.user);

        //   setLoading(false);

        //   navigate(APP_ROUTES.HOME, { replace: true });
        // } catch (error) {
        //   setLoading(false);
        //   throw new Error('Failed to register');
        // }
    };

    const logout = async () => {
        // try {
        //   await AuthRepository.logout(storage.getRefreshToken() || '');
        // } catch (error) {
        //   console.error('Failed to logout:', error);
        // }
        storage.clearAuth();
        setUser(null);
        navigate(APP_ROUTES.LOGIN);
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