"use client";

import { HttpError, NotFoundError, ValidationError } from "./modelService";
import { buildHeaders, createStore, createSelectedIdStorage } from "./serviceUtils";

const BASE_URL = process.env.NEXT_PUBLIC_MODEL_SERVICE_URL || "http://127.0.0.1:8000";

export type CreateDatabaseConnection = Record<string, any>;
export type UpdateDatabaseConnection = Record<string, any>;

// 定义数据库项
export interface BackendDatabaseItem {
    id: number;
    database_name: string; // 展示名
    //database: string; // 数据库/连接标识
    database_uri: string;
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

// 本地状态（与 modelService 相同模式）
export type DatabaseOption = { value: string; name: string };
type DatabaseState = {
    databases: BackendDatabaseItem[];
    options: DatabaseOption[];
    selectedId: string | null;
    loading: boolean;
    error?: string;
};

const DB_SELECTED_KEY = "SELECTED_DB_ID";
const dbStore = createStore<DatabaseState>({ databases: [], options: [], selectedId: null, loading: false });
const { read: readSavedDb, save: saveDb } = createSelectedIdStorage(DB_SELECTED_KEY);

function toOptions(items: BackendDatabaseItem[]): DatabaseOption[] {
    return items.map(it => ({ value: String(it.id), name: it.database_name || String(it.id) }));
}

export const databaseService = {
    // 订阅/读取
    subscribe(fn: () => void) { return dbStore.subscribe(fn); },
    getState(): Readonly<DatabaseState> { return dbStore.getState(); },
    getOptions(): DatabaseOption[] { return dbStore.getState().options; },
    getSelectedId(): string | null { return dbStore.getState().selectedId; },

    // 初始化：localStorage → 后端活跃 → 列表首项
    async init() {
        dbStore.setState({ loading: true, error: undefined });
        try {
            const data = await this.list();
            const items = Array.isArray(data.databases) ? data.databases : [];
            const options = toOptions(items);
            dbStore.setState({ databases: items, options });
            let selected = readSavedDb();
            if (!selected) {
                try { const active = await this.getActive(); selected = active ? String(active.id) : null; } catch { }
            }
            if (selected && !options.find(o => o.value === selected)) selected = null;
            if (!selected) selected = options[0]?.value ?? null;
            dbStore.setState({ selectedId: selected });
            if (selected) saveDb(selected);
        } catch (e) {
            dbStore.setState({ error: e instanceof Error ? e.message : String(e) });
        } finally {
            dbStore.setState({ loading: false });
        }
    },

    async refresh() {
        dbStore.setState({ loading: true, error: undefined });
        try {
            const data = await this.list();
            const items = Array.isArray(data.databases) ? data.databases : [];
            const options = toOptions(items);
            let selected = dbStore.getState().selectedId;
            if (selected && !options.find(o => o.value === selected)) selected = options[0]?.value ?? null;
            dbStore.setState({ databases: items, options, selectedId: selected });
            if (selected) saveDb(selected); else saveDb(null);
        } catch (e) {
            dbStore.setState({ error: e instanceof Error ? e.message : String(e) });
        } finally {
            dbStore.setState({ loading: false });
        }
    },

    async select(id: string) {
        const numericId = Number(id);
        await this.setActive(numericId);
        if (dbStore.getState().options.find(o => o.value === String(numericId))) {
            dbStore.setState({ selectedId: String(numericId) });
            saveDb(String(numericId));
        } else {
            await this.refresh();
        }
    },

    // 获取当前活跃的数据库连接 GET /api/databases/active
    async getActive(): Promise<BackendDatabaseItem> {
        const url = new URL("/api/databases/active", BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "GET",
            headers: buildHeaders(false),
            redirect: "follow",
        });
        if (resp.ok) {
            return (await resp.json()) as BackendDatabaseItem;
        }
        let payload: any = undefined;
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

    // 设置当前活跃的数据库连接 POST /api/databases/active
    async setActive(connectionId: number | string) {
        const url = new URL("/api/databases/active", BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "POST",
            headers: buildHeaders(true),
            body: JSON.stringify({ connection_id: Number(connectionId) }),
            redirect: "follow",
        });
        if (resp.ok) {
            try { return await resp.json(); } catch { return { message: "OK" }; }
        }
        let payload: any = undefined;
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
        if (resp.status === 200 || resp.status === 204) {
            // 本地同步删除与选择回退
            const idStr = String(connectionId);
            const prev = dbStore.getState();
            const databases = prev.databases.filter(d => String(d.id) !== idStr);
            const options = prev.options.filter(o => o.value !== idStr);
            let selected = prev.selectedId;
            if (selected === idStr) selected = options[0]?.value ?? null;
            dbStore.setState({ databases, options, selectedId: selected });
            if (selected) saveDb(selected); else saveDb(null);
            return;
        }
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
