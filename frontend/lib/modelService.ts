"use client";

// 前端直连后端服务封装
// 读取公开环境变量（需以 NEXT_PUBLIC_ 开头）或从 localStorage 读取 token

const BASE_URL = process.env.NEXT_PUBLIC_MODEL_SERVICE_URL || "http://127.0.0.1:8000";

function getToken(): string | undefined {
    // 优先使用公开环境变量，其次使用 localStorage（你也可以改成仅 localStorage）
    const fromEnv = process.env.NEXT_PUBLIC_MODEL_SERVICE_TOKEN;
    if (fromEnv) return fromEnv;
    if (typeof window !== "undefined") {
        return window.localStorage.getItem("MODEL_SERVICE_TOKEN") || undefined;
    }
    return undefined;
}

function buildHeaders(json = true): HeadersInit {
    const headers: HeadersInit = {};
    if (json) headers["content-type"] = "application/json";
    headers["accept"] = "application/json";
    const token = getToken();
    if (token) headers["authorization"] = `Bearer ${token}`;
    return headers;
}

// 统一的错误类型，便于前端根据状态码区分处理
export class HttpError extends Error {
    status: number;
    data?: any;
    constructor(message: string, status: number, data?: any) {
        super(message);
        this.status = status;
        this.data = data;
    }
}

export class NotFoundError extends HttpError {
    constructor(message = "Not Found", data?: any) {
        super(message, 404, data);
    }
}

export class ValidationError extends HttpError {
    constructor(message = "Unprocessable Entity", data?: any) {
        super(message, 422, data);
    }
}

export type CreateModelConnection = Record<string, any>; // 根据后端实际定义细化
export type UpdateModelConnection = Record<string, any>;

// 定义模型项
export interface BackendModelItem {
    id: number;
    model_name: string; // 展示名
    model: string; // 模型标识
    base_url: string;
    model_description: string;
    model_avatar_url: string;
    created_at: string;
    updated_at: string;
}

export interface ListModelsResponse {
    models: BackendModelItem[];
    total: number;
    skip: number;
    limit: number;
}

export const modelService = {
    // 获取用户模型连接列表http://127.0.0.1:8000/api/models/
    async list(params?: { skip?: number; limit?: number; model?: string }): Promise<ListModelsResponse> {
        const url = new URL("/api/models/", BASE_URL);
        const skip = params?.skip ?? 0;
        const limit = params?.limit ?? 100;
        url.searchParams.set("skip", String(skip));
        url.searchParams.set("limit", String(limit));
        if (params?.model !== undefined) url.searchParams.set("model", String(params.model));

        const resp = await fetch(url.toString(), {
            method: "GET",
            headers: buildHeaders(false),
            redirect: "follow"
        });

        if (!resp.ok) throw new Error(`list failed: ${resp.status}`);
        const data = await resp.json();
        // 基本形状校验/回退
        if (!data || !Array.isArray(data.models)) {
            return { models: [], total: 0, skip, limit };
        }
        return data as ListModelsResponse;
    },

    // 创建模型连接http://127.0.0.1:8000/api/models/
    async create(payload: CreateModelConnection) {
        const url = new URL("/api/models/", BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "POST",
            headers: buildHeaders(true),
            body: JSON.stringify(payload),
            redirect: "follow"
        });
        if (!resp.ok) throw new Error(`create failed: ${resp.status}`);
        return resp.json();
    },

    // 根据ID获取模型连接http://127.0.0.1:8000/api/models/{connection_id}
    async get(connectionId: number | string): Promise<BackendModelItem> {
        const url = new URL(`/api/models/${encodeURIComponent(String(connectionId))}`, BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "GET",
            headers: buildHeaders(false),
            redirect: "follow"
        });
        if (!resp.ok) throw new Error(`get failed: ${resp.status}`);
        const data = await resp.json();
        return data as BackendModelItem;
    },

    // 更新模型连接http://127.0.0.1:8000/api/models/{connection_id}
    async update(connectionId: string, payload: UpdateModelConnection, method: "PUT" | "PATCH" = "PUT") {
        const url = new URL(`/api/models/${encodeURIComponent(connectionId)}`, BASE_URL);
        const resp = await fetch(url.toString(), {
            method,
            headers: buildHeaders(true),
            body: JSON.stringify(payload),
            redirect: "follow"
        });
        if (!resp.ok) throw new Error(`update failed: ${resp.status}`);
        return resp.json();
    },

    // 删除模型连接http://127.0.0.1:8000/api/models/{connection_id}
    async remove(connectionId: number | string): Promise<void> {
        const url = new URL(`/api/models/${encodeURIComponent(String(connectionId))}`, BASE_URL);
        const resp = await fetch(url.toString(), { 
            method: "DELETE",
            headers: buildHeaders(false),
            redirect: "follow"
        });
        if (resp.status === 200 || resp.status === 204) {
            return;
        }
        // 尝试读取错误体
        let payload: any = undefined;
        try {
            const ct = resp.headers.get("content-type") || "";
            if (ct.includes("application/json")) payload = await resp.json();
            else payload = await resp.text();
        } catch (_) { /* ignore */ }

        if (resp.status === 404) {
            throw new NotFoundError("记录不存在", payload);
        }
        if (resp.status === 422) {
            throw new ValidationError("参数错误", payload);
        }
        throw new HttpError(`delete failed: ${resp.status}`, resp.status, payload);
    },
};
