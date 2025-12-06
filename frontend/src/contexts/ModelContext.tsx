import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { Model } from '@/lib/types';
import { ModelsRepository } from '@/repositories/models';

const STORAGE_KEY = 'nexus_selected_model';
const DEFAULT_MODEL = 'llama-3.1-8b-instant';

interface ModelContextType {
    models: Model[];
    selectedModel: string;
    loading: boolean;
    error: string | null;
    setSelectedModel: (modelId: string) => void;
    refreshModels: () => Promise<void>;
}

const ModelContext = createContext<ModelContextType | undefined>(undefined);

export function ModelProvider({ children }: { children: React.ReactNode }) {
    const [models, setModels] = useState<Model[]>([]);
    const [selectedModel, setSelectedModelState] = useState<string>(() => {
        // Initialize from localStorage or use default
        try {
            return localStorage.getItem(STORAGE_KEY) || DEFAULT_MODEL;
        } catch {
            return DEFAULT_MODEL;
        }
    });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const refreshModels = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await ModelsRepository.getModels();
            if (response && response.status === 'SUCCESS') {
                setModels(response.data);
                // If current selected model is not in the list, select the first one
                if (response.data.length > 0) {
                    const modelIds = response.data.map((m) => m.id);
                    if (!modelIds.includes(selectedModel)) {
                        setSelectedModelState(response.data[0].id);
                        localStorage.setItem(STORAGE_KEY, response.data[0].id);
                    }
                }
            } else if (response && response.status === 'FAIL') {
                setError(response.message);
            }
        } catch (err) {
            console.error('Failed to fetch models:', err);
            setError('Failed to load models');
        } finally {
            setLoading(false);
        }
    }, [selectedModel]);

    const setSelectedModel = useCallback((modelId: string) => {
        setSelectedModelState(modelId);
        try {
            localStorage.setItem(STORAGE_KEY, modelId);
        } catch (err) {
            console.error('Failed to save selected model:', err);
        }
    }, []);

    useEffect(() => {
        refreshModels();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <ModelContext.Provider
            value={{
                models,
                selectedModel,
                loading,
                error,
                setSelectedModel,
                refreshModels,
            }}
        >
            {children}
        </ModelContext.Provider>
    );
}

export function useModel() {
    const context = useContext(ModelContext);
    if (context === undefined) {
        throw new Error('useModel must be used within a ModelProvider');
    }
    return context;
}
