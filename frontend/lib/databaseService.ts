"use client";

import { HttpError, NotFoundError, ValidationError } from "./modelService";
import { buildHeaders, createStore, createSelectedIdStorage } from "./serviceUtils";
import { fetchWithAuth } from "@/lib/auth";

const BASE_URL = process.env.NEXT_PUBLIC_MODEL_SERVICE_URL || "http://127.0.0.1:8000";

// =========================
// 类型定义
// =========================
export type CreateDatabaseConnection = Record<string, unknown>;
export type UpdateDatabaseConnection = Record<string, unknown>;

export interface BackendDatabaseItem {
    id: number;
    database_name: string; // 展示名
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
    active_connection_id?: number; // 0 表示无活跃连接
}

// =========================
// API 客户端（纯 HTTP，无本地状态）
// =========================
export const databaseApi = {
    async getActive(): Promise<BackendDatabaseItem> {
        const url = new URL("/api/databases/active", BASE_URL);
        const resp = await fetchWithAuth(url.toString(), { method: "GET", headers: buildHeaders(false), redirect: "follow" });
        if (resp.ok) return (await resp.json()) as BackendDatabaseItem;
        let payload: unknown = undefined;
        try {
            const ct = resp.headers.get("content-type") || "";
            payload = ct.includes("application/json") ? await resp.json() : await resp.text();
        } catch { }
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
        try {
            const ct = resp.headers.get("content-type") || "";
            payload = ct.includes("application/json") ? await resp.json() : await resp.text();
        } catch { }
        if (resp.status === 404) throw new NotFoundError("记录不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`db setActive failed: ${resp.status}`, resp.status, payload);
    },

    async get(connectionId: number | string): Promise<BackendDatabaseItem> {
        const url = new URL(`/api/databases/${encodeURIComponent(String(connectionId))}`, BASE_URL);
        const resp = await fetchWithAuth(url.toString(), { method: "GET", headers: buildHeaders(false), redirect: "follow" });
        if (resp.ok) return (await resp.json()) as BackendDatabaseItem;
        let payload: unknown = undefined;
        try {
            const ct = resp.headers.get("content-type") || "";
            payload = ct.includes("application/json") ? await resp.json() : await resp.text();
        } catch { }
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
        try {
            const ct = resp.headers.get("content-type") || "";
            payload = ct.includes("application/json") ? await resp.json() : await resp.text();
        } catch { }
        if (resp.status === 404) throw new NotFoundError("数据库连接不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`db delete failed: ${resp.status}`, resp.status, payload);
    },
};

// =========================
// 本地状态（与 modelService 相同模式）
// =========================
export type DatabaseOption = { value: string; name: string };
type DatabaseState = { databases: BackendDatabaseItem[]; options: DatabaseOption[]; selectedId: string | null; loading: boolean; error?: string; };

const DB_SELECTED_KEY = "SELECTED_DB_ID";
const dbStore = createStore<DatabaseState>({ databases: [], options: [], selectedId: null, loading: false });
const { read: readSavedDb, save: saveDb } = createSelectedIdStorage(DB_SELECTED_KEY);

function toOptions(items: BackendDatabaseItem[]): DatabaseOption[] {
    return items.map(it => ({ value: String(it.id), name: it.database_name || String(it.id) }));
}

function applyDatabasesToStore(items: BackendDatabaseItem[], selectedOverride?: string | null) {
    const options = toOptions(items);
    let selected = selectedOverride ?? dbStore.getState().selectedId ?? null;
    if (!options.some(o => o.value === selected)) selected = options[0]?.value ?? null;
    dbStore.setState({ databases: items, options, selectedId: selected });
    saveDb(selected ?? null);
}

// =========================
// Service 层（带本地状态）
// 暴露 7 个方法：getActive/list/get/create/update/remove/setActive
// 以及 init/refresh/select 等便捷方法，与 modelService 对齐
// =========================
export const databaseService = {
    subscribe(fn: () => void) { return dbStore.subscribe(fn); },
    getState(): Readonly<DatabaseState> { return dbStore.getState(); },
    getOptions(): DatabaseOption[] { return dbStore.getState().options; },
    getSelectedId(): string | null { return dbStore.getState().selectedId; },

    async init() {
        dbStore.setState({ loading: true, error: undefined });
        try {
            const data = await databaseApi.list();
            const items = Array.isArray(data.databases) ? data.databases : [];
            applyDatabasesToStore(items, null);
            let selected = readSavedDb();
            if (!selected) {
                const activeId = typeof data.active_connection_id === "number" && data.active_connection_id > 0
                    ? String(data.active_connection_id)
                    : null;
                if (activeId) {
                    selected = activeId;
                } else {
                    try { const active = await databaseApi.getActive(); selected = active ? String(active.id) : null; } catch { /* ignore */ }
                }
            }
            applyDatabasesToStore(items, selected);
        } catch (e) {
            dbStore.setState({ error: e instanceof Error ? e.message : String(e) });
        } finally {
            dbStore.setState({ loading: false });
        }
    },

    async refresh() {
        dbStore.setState({ loading: true, error: undefined });
        try {
            const data = await databaseApi.list();
            const items = Array.isArray(data.databases) ? data.databases : [];
            // 优先使用后端返回的活跃项
            const activeId = typeof (data as { active_connection_id?: number }).active_connection_id === "number" && (data as { active_connection_id?: number }).active_connection_id! > 0
                ? String((data as { active_connection_id?: number }).active_connection_id)
                : null;
            if (activeId) {
                applyDatabasesToStore(items, activeId);
            } else {
                const current = dbStore.getState().selectedId;
                const options = toOptions(items);
                const selected = current && options.some(o => o.value === current) ? current : (options[0]?.value ?? null);
                applyDatabasesToStore(items, selected);
            }
        } catch (e) {
            dbStore.setState({ error: e instanceof Error ? e.message : String(e) });
        } finally {
            dbStore.setState({ loading: false });
        }
    },

    async select(id: string) {
        await databaseApi.setActive(id);
        const found = dbStore.getState().options.some(o => o.value === String(id));
        dbStore.setState({ selectedId: found ? String(id) : dbStore.getState().selectedId });
        saveDb(found ? String(id) : null);
        if (!found) await this.refresh();
    },

    // 7 个接口（HTTP 代理）
    async getActive(): Promise<BackendDatabaseItem> { return databaseApi.getActive(); },
    async list(params?: { skip?: number; limit?: number; q?: string }): Promise<ListDatabasesResponse> { return databaseApi.list(params); },
    async get(connectionId: number | string): Promise<BackendDatabaseItem> { return databaseApi.get(connectionId); },
    async create(payload: CreateDatabaseConnection): Promise<BackendDatabaseItem> {
        const created = await databaseApi.create(payload);
        this.refresh().catch(() => void 0);
        return created;
    },
    async update(connectionId: number | string, payload: UpdateDatabaseConnection, method: "PUT" | "PATCH" = "PUT"): Promise<BackendDatabaseItem> {
        const updated = await databaseApi.update(connectionId, payload, method);
        const prev = dbStore.getState();
        const next = [...prev.databases];
        const idx = next.findIndex(d => String(d.id) === String(connectionId));
        if (idx >= 0) next[idx] = updated; else next.push(updated);
        applyDatabasesToStore(next);
        return updated;
    },
    async remove(connectionId: number | string): Promise<void> {
        await databaseApi.remove(connectionId);
        const idStr = String(connectionId);
        const prev = dbStore.getState();
        const next = prev.databases.filter(d => String(d.id) !== idStr);
        applyDatabasesToStore(next);
    },
};
