import { storage } from "@/lib/storage";
import axios from "axios";

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

    static async sendGetRequest(url: string, signal?: AbortSignal) {
        try {
            const response = await axios.get(url, {
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${storage.getAccessToken()}`
                },
                signal
            });
            return response;
        } catch (error) {
            throw error;
        }
    }

    static async sendPostRequest(url: string, data: any, hasFile = false, signal?: AbortSignal) {
        try {
            const response = await axios.post(url, data, {
                headers: {
                    "Content-Type": hasFile ? "multipart/form-data" : "application/json",
                    "Authorization": `Bearer ${storage.getAccessToken()}`
                },
                signal
            });
            return response;
        } catch (error) {
            throw error;
        }
    }

    static async sendPatchRequest(url: string, data: any, hasFile = false, signal?: AbortSignal) {
        try {
            const response = await axios.patch(url, data, {
                headers: {
                    "Content-Type": hasFile ? "multipart/form-data" : "application/json",
                    "Authorization": `Bearer ${storage.getAccessToken()}`
                },
                signal
            });
            return response;
        } catch (error) {
            throw error;
        }
    }

    static async sendPutRequest(url: string, data: any, hasFile = false, signal?: AbortSignal) {
        try {
            const response = await axios.put(url, data, {
                headers: {
                    "Content-Type": hasFile ? "multipart/form-data" : "application/json",
                    "Authorization": `Bearer ${storage.getAccessToken()}`
                },
                signal
            });
            return response;
        } catch (error) {
            throw error;
        }
    }

    static async sendDeleteRequest(url: string, data?: any, signal?: AbortSignal) {
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
        } catch (error) {
            throw error;
        }
    }

    static async sendGetExportRequest(url: string, signal?: AbortSignal) {
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
        } catch (error) {
            throw error;
        }
    }

    static async sendPostExportRequest(url: string, data: any, signal?: AbortSignal) {
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
        } catch (error) {
            throw error;
        }
    }
}
