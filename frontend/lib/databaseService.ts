"use client";

import { HttpError, NotFoundError, ValidationError } from "./modelService";

const BASE_URL = process.env.NEXT_PUBLIC_MODEL_SERVICE_URL || "http://127.0.0.1:8000";

function getToken(): string | undefined {
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

export type CreateDatabaseConnection = Record<string, any>;
export type UpdateDatabaseConnection = Record<string, any>;

// 定义数据库项
export interface BackendDatabaseItem {
    id: number;
    database_name: string; // 展示名
    //database: string; // 数据库/连接标识
    base_uri: string;
    database_type: string;
    database_description: string;
    created_at: string;
    updated_at: string;
    
    // 允许存在服务端额外字段
    [key: string]: any;
}

export interface ListDatabasesResponse {
    databases: BackendDatabaseItem[];
    total: number;
    skip: number;
    limit: number;
}

export const databaseService = {
    async list(params?: { skip?: number; limit?: number; q?: string }): Promise<ListDatabasesResponse> {
        const url = new URL("/api/databases/", BASE_URL);
        const skip = params?.skip ?? 0;
        const limit = params?.limit ?? 100;
        url.searchParams.set("skip", String(skip));
        url.searchParams.set("limit", String(limit));
        if (params?.q) url.searchParams.set("q", params.q);

        const resp = await fetch(url.toString(), {
            method: "GET",
            headers: buildHeaders(false),
            redirect: "follow",
        });
        if (!resp.ok) throw new Error(`db list failed: ${resp.status}`);
        const data = await resp.json().catch(() => undefined);
        if (!data || !Array.isArray(data.databases)) {
            return { databases: [], total: 0, skip, limit };
        }
        return data as ListDatabasesResponse;
    },

    // 创建数据库连接 POST /api/databases/
    async create(payload: CreateDatabaseConnection): Promise<BackendDatabaseItem> {
        const url = new URL("/api/databases/", BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "POST",
            headers: buildHeaders(true),
            body: JSON.stringify(payload),
            redirect: "follow",
        });
        if (!resp.ok) throw new Error(`db create failed: ${resp.status}`);
        return (await resp.json()) as BackendDatabaseItem;
    },

    async get(connectionId: number | string): Promise<BackendDatabaseItem> {
        const url = new URL(`/api/databases/${encodeURIComponent(String(connectionId))}`, BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "GET",
            headers: buildHeaders(false),
            redirect: "follow",
        });
        if (resp.ok) {
            return (await resp.json()) as BackendDatabaseItem;
        }
        // 读取错误体（可选）
        let payload: any = undefined;
        try {
            const ct = resp.headers.get("content-type") || "";
            payload = ct.includes("application/json") ? await resp.json() : await resp.text();
        } catch { }
        if (resp.status === 404) throw new NotFoundError("数据库连接不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`db get failed: ${resp.status}`, resp.status, payload);
    },

    // 更新数据库连接 PUT/PATCH /api/databases/{id}
    async update(connectionId: number | string, payload: UpdateDatabaseConnection, method: "PUT" | "PATCH" = "PUT"): Promise<BackendDatabaseItem> {
        const url = new URL(`/api/databases/${encodeURIComponent(String(connectionId))}`, BASE_URL);
        const resp = await fetch(url.toString(), {
            method,
            headers: buildHeaders(true),
            body: JSON.stringify(payload),
            redirect: "follow",
        });
        if (!resp.ok) throw new Error(`db update failed: ${resp.status}`);
        return (await resp.json()) as BackendDatabaseItem;
    },

    // 删除数据库连接 DELETE /api/databases/{id}
    async remove(connectionId: number | string): Promise<void> {
        const url = new URL(`/api/databases/${encodeURIComponent(String(connectionId))}`, BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "DELETE",
            headers: buildHeaders(false),
            redirect: "follow",
        });
        if (resp.status === 200 || resp.status === 204) return;
        let payload: any = undefined;
        try {
            const ct = resp.headers.get("content-type") || "";
            payload = ct.includes("application/json") ? await resp.json() : await resp.text();
        } catch { }
        if (resp.status === 404) throw new NotFoundError("数据库连接不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`db delete failed: ${resp.status}`, resp.status, payload);
    },
};
