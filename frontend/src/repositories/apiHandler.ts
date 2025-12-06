import { storage } from "@/lib/storage";
import axios, { AxiosResponse } from "axios";
import { API_ROUTES } from "@/lib/constants";
import { AuthRepository } from "./auth";

let isRefreshing = false;
let failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (reason?: any) => void;
    originalRequest: () => Promise<any>;
}> = [];

const processQueue = (error: any) => {
    failedQueue.forEach((item) => {
        if (error) {
            item.reject(error);
        } else {
            // Retry the original request after token refresh
            item.originalRequest()
                .then(item.resolve)
                .catch(item.reject);
        }
    });
    failedQueue = [];
};

export class ApiHandler {
    static async sendAuthRequest(url: string, data: any, signal?: AbortSignal) {
        try {
            const response = await axios.post(url, data, {
                headers: { "Content-Type": "application/json" },
                signal
            });
            return response;
        } catch (error) {
            throw error;
        }
    }

    static async sendUnauthenticatedGetRequest(url: string, signal?: AbortSignal) {
        try {
            const response = await axios.get(url, {
                headers: { "Content-Type": "application/json" },
                signal
            });
            return response;
        } catch (error) {
            throw error;
        }
    }

    static async sendUnauthenticatedPostRequest(url: string, data: any, signal?: AbortSignal) {
        try {
            const response = await axios.post(url, data, {
                headers: { "Content-Type": "application/json" },
                signal
            });
            return response;
        } catch (error) {
            throw error;
        }
    }

    static async sendGetRequest(url: string, signal?: AbortSignal): Promise<AxiosResponse> {
        try {
            const response = await axios.get(url, {
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${storage.getAccessToken()}`
                },
                signal
            });
            return response;
        } catch (error: any) {
            if (error.response?.status === 401 && url !== API_ROUTES.AUTH.REFRESH) {
                return this.handle401Error(() => this.sendGetRequest(url, signal));
            }
            throw error;
        }
    }

    static async sendPostRequest(url: string, data: any, hasFile = false, signal?: AbortSignal): Promise<AxiosResponse> {
        try {
            const response = await axios.post(url, data, {
                headers: {
                    "Content-Type": hasFile ? "multipart/form-data" : "application/json",
                    "Authorization": `Bearer ${storage.getAccessToken()}`
                },
                signal
            });
            return response;
        } catch (error: any) {
            if (error.response?.status === 401 && url !== API_ROUTES.AUTH.REFRESH && url !== API_ROUTES.AUTH.LOGOUT) {
                return this.handle401Error(() => this.sendPostRequest(url, data, hasFile, signal));
            }
            throw error;
        }
    }

    static async sendPatchRequest(url: string, data: any, hasFile = false, signal?: AbortSignal): Promise<AxiosResponse> {
        try {
            const response = await axios.patch(url, data, {
                headers: {
                    "Content-Type": hasFile ? "multipart/form-data" : "application/json",
                    "Authorization": `Bearer ${storage.getAccessToken()}`
                },
                signal
            });
            return response;
        } catch (error: any) {
            if (error.response?.status === 401 && url !== API_ROUTES.AUTH.REFRESH && url !== API_ROUTES.AUTH.LOGOUT) {
                return this.handle401Error(() => this.sendPatchRequest(url, data, hasFile, signal));
            }
            throw error;
        }
    }

    static async sendPutRequest(url: string, data: any, hasFile = false, signal?: AbortSignal): Promise<AxiosResponse> {
        try {
            const response = await axios.put(url, data, {
                headers: {
                    "Content-Type": hasFile ? "multipart/form-data" : "application/json",
                    "Authorization": `Bearer ${storage.getAccessToken()}`
                },
                signal
            });
            return response;
        } catch (error: any) {
            if (error.response?.status === 401 && url !== API_ROUTES.AUTH.REFRESH && url !== API_ROUTES.AUTH.LOGOUT) {
                return this.handle401Error(() => this.sendPutRequest(url, data, hasFile, signal));
            }
            throw error;
        }
    }

    static async sendDeleteRequest(url: string, data?: any, signal?: AbortSignal): Promise<AxiosResponse> {
        try {
            const response = await axios.delete(url, {
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${storage.getAccessToken()}`
                },
                data,
                signal
            });
            return response;
        } catch (error: any) {
            if (error.response?.status === 401 && url !== API_ROUTES.AUTH.REFRESH && url !== API_ROUTES.AUTH.LOGOUT) {
                return this.handle401Error(() => this.sendDeleteRequest(url, data, signal));
            }
            throw error;
        }
    }

    static async sendGetExportRequest(url: string, signal?: AbortSignal): Promise<AxiosResponse> {
        try {
            const response = await axios.get(url, {
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${storage.getAccessToken()}`
                },
                responseType: "blob",
                signal
            });
            return response;
        } catch (error: any) {
            if (error.response?.status === 401 && url !== API_ROUTES.AUTH.REFRESH && url !== API_ROUTES.AUTH.LOGOUT) {
                return this.handle401Error(() => this.sendGetExportRequest(url, signal));
            }
            throw error;
        }
    }

    static async sendPostExportRequest(url: string, data: any, signal?: AbortSignal): Promise<AxiosResponse> {
        try {
            const response = await axios.post(url, data, {
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${storage.getAccessToken()}`
                },
                responseType: "blob",
                signal
            });
            return response;
        } catch (error: any) {
            if (error.response?.status === 401 && url !== API_ROUTES.AUTH.REFRESH && url !== API_ROUTES.AUTH.LOGOUT) {
                return this.handle401Error(() => this.sendPostExportRequest(url, data, signal));
            }
            throw error;
        }
    }

    private static async handle401Error(originalRequest: () => Promise<AxiosResponse>): Promise<AxiosResponse> {
        const refreshToken = storage.getRefreshToken();

        if (!refreshToken) {
            storage.clearAuth();
            window.location.href = '/login';
            return Promise.reject(new Error('No refresh token available'));
        }

        if (isRefreshing) {
            // Queue this request to retry after refresh completes
            return new Promise((resolve, reject) => {
                failedQueue.push({ resolve, reject, originalRequest });
            });
        }

        isRefreshing = true;

        try {
            const response = await AuthRepository.refreshToken(refreshToken);
            if (response && response.status === "SUCCESS") {
                storage.setTokenResponse(response);
                processQueue(null);
                isRefreshing = false;
                // Retry the original request with new token
                return originalRequest();
            } else {
                throw new Error('Failed to refresh token');
            }
        } catch (error) {
            processQueue(error);
            isRefreshing = false;
            storage.clearAuth();
            window.location.href = '/login';
            return Promise.reject(error);
        }
    }
}
