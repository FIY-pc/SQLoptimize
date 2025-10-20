import { buildHeaders } from "@/lib/serviceUtils";
import { fetchWithAuth } from "@/lib/auth";
import { HttpError, NotFoundError, ValidationError } from "@/lib/errors";

const BASE_URL = process.env.NEXT_PUBLIC_SQLOPT_SERVICE_URL || "http://127.0.0.1:8000";

export type CreateDatabaseConnection = Record<string, unknown>;
export type UpdateDatabaseConnection = Record<string, unknown>;

export interface BackendDatabaseItem {
    id: number;
    database_name: string;
    database_uri: string;
    database_type: string;
    database_description: string;
    created_at: string;
    updated_at: string;
    [key: string]: unknown;
}

export interface ListDatabasesResponse {
    databases: BackendDatabaseItem[];
    total: number;
    skip: number;
    limit: number;
    has_more?: boolean;
    active_connection_id?: number;
}

export const databaseApi = {
    async getActive(): Promise<BackendDatabaseItem> {
        const url = new URL("/api/databases/active", BASE_URL);
        const resp = await fetchWithAuth(url.toString(), { method: "GET", headers: buildHeaders(false), redirect: "follow" });
        if (resp.ok) return (await resp.json()) as BackendDatabaseItem;
        let payload: unknown = undefined;
        try { const ct = resp.headers.get("content-type") || ""; payload = ct.includes("application/json") ? await resp.json() : await resp.text(); } catch { }
        if (resp.status === 404) throw new NotFoundError("未找到活跃数据库连接", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`db getActive failed: ${resp.status}`, resp.status, payload);
    },

    async list(params?: { skip?: number; limit?: number; q?: string }): Promise<ListDatabasesResponse> {
        const url = new URL("/api/databases/", BASE_URL);
        const skip = params?.skip ?? 0;
        const limit = params?.limit ?? 100;
        url.searchParams.set("skip", String(skip));
        url.searchParams.set("limit", String(limit));
        if (params?.q) url.searchParams.set("q", params.q);
        const resp = await fetchWithAuth(url.toString(), { method: "GET", headers: buildHeaders(false), redirect: "follow" });
        if (!resp.ok) throw new Error(`db list failed: ${resp.status}`);
        const data = await resp.json().catch(() => undefined);
        if (!data || !Array.isArray(data.databases)) return { databases: [], total: 0, skip, limit };
        return data as ListDatabasesResponse;
    },

    async create(payload: CreateDatabaseConnection): Promise<BackendDatabaseItem> {
        const url = new URL("/api/databases/", BASE_URL);
        const resp = await fetchWithAuth(url.toString(), { method: "POST", headers: buildHeaders(true), body: JSON.stringify(payload), redirect: "follow" });
        if (!resp.ok) throw new Error(`db create failed: ${resp.status}`);
        return (await resp.json()) as BackendDatabaseItem;
    },

    async setActive(connectionId: number | string) {
        const url = new URL("/api/databases/active", BASE_URL);
        const resp = await fetchWithAuth(url.toString(), { method: "POST", headers: buildHeaders(true), body: JSON.stringify({ connection_id: Number(connectionId) }), redirect: "follow" });
        if (resp.ok) { try { return await resp.json(); } catch { return { message: "OK" }; } }
        let payload: unknown = undefined;
        try { const ct = resp.headers.get("content-type") || ""; payload = ct.includes("application/json") ? await resp.json() : await resp.text(); } catch { }
        if (resp.status === 404) throw new NotFoundError("记录不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`db setActive failed: ${resp.status}`, resp.status, payload);
    },

    async get(connectionId: number | string): Promise<BackendDatabaseItem> {
        const url = new URL(`/api/databases/${encodeURIComponent(String(connectionId))}`, BASE_URL);
        const resp = await fetchWithAuth(url.toString(), { method: "GET", headers: buildHeaders(false), redirect: "follow" });
        if (resp.ok) return (await resp.json()) as BackendDatabaseItem;
        let payload: unknown = undefined;
        try { const ct = resp.headers.get("content-type") || ""; payload = ct.includes("application/json") ? await resp.json() : await resp.text(); } catch { }
        if (resp.status === 404) throw new NotFoundError("数据库连接不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`db get failed: ${resp.status}`, resp.status, payload);
    },

    async update(connectionId: number | string, payload: UpdateDatabaseConnection, method: "PUT" | "PATCH" = "PUT"): Promise<BackendDatabaseItem> {
        const url = new URL(`/api/databases/${encodeURIComponent(String(connectionId))}`, BASE_URL);
        const resp = await fetchWithAuth(url.toString(), { method, headers: buildHeaders(true), body: JSON.stringify(payload), redirect: "follow" });
        if (!resp.ok) throw new Error(`db update failed: ${resp.status}`);
        return (await resp.json()) as BackendDatabaseItem;
    },

    async remove(connectionId: number | string): Promise<void> {
        const url = new URL(`/api/databases/${encodeURIComponent(String(connectionId))}`, BASE_URL);
        const resp = await fetchWithAuth(url.toString(), { method: "DELETE", headers: buildHeaders(false), redirect: "follow" });
        if (resp.status === 200 || resp.status === 204) return;
        let payload: unknown = undefined;
        try { const ct = resp.headers.get("content-type") || ""; payload = ct.includes("application/json") ? await resp.json() : await resp.text(); } catch { }
        if (resp.status === 404) throw new NotFoundError("数据库连接不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`db delete failed: ${resp.status}`, resp.status, payload);
    },
};
