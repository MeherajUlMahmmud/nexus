import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { Session, SessionCreate } from '@/lib/types';
import { SessionRepository } from '@/repositories/session';

interface SessionContextType {
    sessions: Session[];
    currentSession: Session | null;
    loading: boolean;
    error: string | null;
    setCurrentSession: (session: Session | null) => void;
    createSession: (modelName?: string, message?: string) => Promise<Session | null>;
    deleteSession: (sessionId: number) => Promise<void>;
    refreshSessions: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: React.ReactNode }) {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [currentSession, setCurrentSessionState] = useState<Session | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const refreshSessions = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await SessionRepository.getSessions();
            // Response is APIResponse<Session[]>
            if (response && response.status === 'SUCCESS') {
                setSessions(Array.isArray(response.data) ? response.data : []);
            } else if (response && response.status === 'FAIL') {
                setError(response.message);
            }
        } catch (err) {
            console.error('Failed to fetch sessions:', err);
            setError('Failed to load sessions');
        } finally {
            setLoading(false);
        }
    }, []);

    const createSession = useCallback(async (modelName?: string, message?: string): Promise<Session | null> => {
        setError(null);
        try {
            const data: SessionCreate = {
                model_name: modelName || undefined,
                message: message || undefined,
            };
            const response = await SessionRepository.createSession(data);
            
            if (response && response.status === 'SUCCESS') {
                const newSession = response.data;
                setSessions((prev) => [newSession, ...prev]);
                setCurrentSessionState(newSession);
                return newSession;
            } else if (response && response.status === 'FAIL') {
                setError(response.message);
                return null;
            }
            return null;
        } catch (err) {
            console.error('Failed to create session:', err);
            setError('Failed to create session');
            return null;
        }
    }, []);

    const setCurrentSession = useCallback((session: Session | null) => {
        setCurrentSessionState(session);
    }, []);

    const deleteSession = useCallback(async (sessionId: number): Promise<void> => {
        setError(null);
        try {
            await SessionRepository.deleteSession(sessionId);
            setSessions((prev) => prev.filter((s) => s.id !== sessionId));
            // If the deleted session was the current session, clear it
            setCurrentSessionState((prev) => (prev?.id === sessionId ? null : prev));
        } catch (err) {
            console.error('Failed to delete session:', err);
            setError('Failed to delete session');
            throw err;
        }
    }, []);

    useEffect(() => {
        refreshSessions();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <SessionContext.Provider
            value={{
                sessions,
                currentSession,
                loading,
                error,
                setCurrentSession,
                createSession,
                deleteSession,
                refreshSessions,
            }}
        >
            {children}
        </SessionContext.Provider>
    );
}

export function useSession() {
    const context = useContext(SessionContext);
    if (context === undefined) {
        throw new Error('useSession must be used within a SessionProvider');
    }
    return context;
}
