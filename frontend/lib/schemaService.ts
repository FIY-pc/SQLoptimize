"use client";

import { HttpError, NotFoundError, ValidationError } from "./modelService";
import { buildHeaders, createStore, createSelectedIdStorage } from "./serviceUtils";

const BASE_URL = process.env.NEXT_PUBLIC_MODEL_SERVICE_URL || "http://127.0.0.1:8000";

export type CreateDbSchema = Record<string, any>;
export type UpdateDbSchema = Record<string, any>;

export interface BackendDbSchemaItem {
    id: number;
    schema_name: string;
    schema_content: string;
    created_at: string;
    updated_at: string;
    user_id: number;
    [key: string]: any;
}

export interface ListDbSchemasResponse {
    schemas: BackendDbSchemaItem[];
    total: number;
    skip: number;
    limit: number;
}

// 本地状态（与 modelService 相同模式）
export type SchemaOption = { value: string; name: string };
type SchemaState = {
    schemas: BackendDbSchemaItem[];
    options: SchemaOption[];
    selectedId: string | null;
    loading: boolean;
    error?: string;
};

const SCHEMA_SELECTED_KEY = "SELECTED_SCHEMA_ID";
const schemaStore = createStore<SchemaState>({ schemas: [], options: [], selectedId: null, loading: false });
const { read: readSavedSchema, save: saveSchema } = createSelectedIdStorage(SCHEMA_SELECTED_KEY);

function toOptions(items: BackendDbSchemaItem[]): SchemaOption[] {
    return items.map(it => ({ value: String(it.id), name: it.schema_name || String(it.id) }));
}

export const schemaService = {
    // 订阅/读取
    subscribe(fn: () => void) { return schemaStore.subscribe(fn); },
    getState(): Readonly<SchemaState> { return schemaStore.getState(); },
    getOptions(): SchemaOption[] { return schemaStore.getState().options; },
    getSelectedId(): string | null { return schemaStore.getState().selectedId; },

    // 初始化：localStorage → 后端活跃 → 列表首项
    async init() {
        schemaStore.setState({ loading: true, error: undefined });
        try {
            const data = await this.list();
            const items = Array.isArray(data.schemas) ? data.schemas : [];
            const options = toOptions(items);
            schemaStore.setState({ schemas: items, options });
            let selected = readSavedSchema();
            if (!selected) {
                try { const active = await this.getActive(); selected = active ? String(active.id) : null; } catch { }
            }
            if (selected && !options.find(o => o.value === selected)) selected = null;
            if (!selected) selected = options[0]?.value ?? null;
            schemaStore.setState({ selectedId: selected });
            if (selected) saveSchema(selected);
        } catch (e) {
            schemaStore.setState({ error: e instanceof Error ? e.message : String(e) });
        } finally {
            schemaStore.setState({ loading: false });
        }
    },

    async refresh() {
        schemaStore.setState({ loading: true, error: undefined });
        try {
            const data = await this.list();
            const items = Array.isArray(data.schemas) ? data.schemas : [];
            const options = toOptions(items);
            let selected = schemaStore.getState().selectedId;
            if (selected && !options.find(o => o.value === selected)) selected = options[0]?.value ?? null;
            schemaStore.setState({ schemas: items, options, selectedId: selected });
            if (selected) saveSchema(selected); else saveSchema(null);
        } catch (e) {
            schemaStore.setState({ error: e instanceof Error ? e.message : String(e) });
        } finally {
            schemaStore.setState({ loading: false });
        }
    },

    async select(id: string) {
        const numericId = Number(id);
        await this.setActive(numericId);
        if (schemaStore.getState().options.find(o => o.value === String(numericId))) {
            schemaStore.setState({ selectedId: String(numericId) });
            saveSchema(String(numericId));
        } else {
            await this.refresh();
        }
    },

    // 获取当前活跃的数据库模式 GET /api/schemas/active
    async getActive(): Promise<BackendDbSchemaItem> {
        const url = new URL("/api/schemas/active", BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "GET",
            headers: buildHeaders(false),
            redirect: "follow",
        });
        if (resp.ok) {
            return (await resp.json()) as BackendDbSchemaItem;
        }
        let payload: any = undefined;
        try {
            const ct = resp.headers.get("content-type") || "";
            payload = ct.includes("application/json") ? await resp.json() : await resp.text();
        } catch { }
        if (resp.status === 404) throw new NotFoundError("未找到活跃数据库模式", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`schema getActive failed: ${resp.status}`, resp.status, payload);
    },

    // 列表 GET /api/schemas/
    async list(params?: { skip?: number; limit?: number }): Promise<ListDbSchemasResponse> {
        const url = new URL("/api/schemas/", BASE_URL);
        const skip = params?.skip ?? 0;
        const limit = params?.limit ?? 100;
        url.searchParams.set("skip", String(skip));
        url.searchParams.set("limit", String(limit));

        const resp = await fetch(url.toString(), {
            method: "GET",
            headers: buildHeaders(false),
            redirect: "follow",
        });
        if (!resp.ok) throw new Error(`schema list failed: ${resp.status}`);
        const data = await resp.json().catch(() => undefined);
        if (!data || !Array.isArray(data.schemas)) {
            return { schemas: [], total: 0, skip, limit };
        }
        return data as ListDbSchemasResponse;
    },

    // 创建 POST /api/schemas/
    async create(payload: CreateDbSchema): Promise<BackendDbSchemaItem> {
        const url = new URL("/api/schemas/", BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "POST",
            headers: buildHeaders(true),
            body: JSON.stringify(payload),
            redirect: "follow",
        });
        if (!resp.ok) throw new Error(`schema create failed: ${resp.status}`);
        return (await resp.json()) as BackendDbSchemaItem;
    },

    // 设置当前活跃的数据库模式 POST /api/schemas/active
    async setActive(schemaId: number | string) {
        const url = new URL("/api/schemas/active", BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "POST",
            headers: buildHeaders(true),
            body: JSON.stringify({ schema_id: Number(schemaId) }),
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
        throw new HttpError(`schema setActive failed: ${resp.status}`, resp.status, payload);
    },

    // 获取指定模式 GET /api/schemas/{id}
    async get(schemaId: number | string): Promise<BackendDbSchemaItem> {
        const url = new URL(`/api/schemas/${encodeURIComponent(String(schemaId))}`, BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "GET",
            headers: buildHeaders(false),
            redirect: "follow",
        });
        if (resp.ok) return (await resp.json()) as BackendDbSchemaItem;
        let payload: any = undefined;
        try {
            const ct = resp.headers.get("content-type") || "";
            payload = ct.includes("application/json") ? await resp.json() : await resp.text();
        } catch { }
        if (resp.status === 404) throw new NotFoundError("数据库模式不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`schema get failed: ${resp.status}`, resp.status, payload);
    },

    // 更新 PUT/PATCH /api/schemas/{id}
    async update(schemaId: number | string, payload: UpdateDbSchema, method: "PUT" | "PATCH" = "PUT"): Promise<BackendDbSchemaItem> {
        const url = new URL(`/api/schemas/${encodeURIComponent(String(schemaId))}`, BASE_URL);
        const resp = await fetch(url.toString(), {
            method,
            headers: buildHeaders(true),
            body: JSON.stringify(payload),
            redirect: "follow",
        });
        if (!resp.ok) throw new Error(`schema update failed: ${resp.status}`);
        return (await resp.json()) as BackendDbSchemaItem;
    },

    // 删除 DELETE /api/schemas/{id}
    async remove(schemaId: number | string): Promise<void> {
        const url = new URL(`/api/schemas/${encodeURIComponent(String(schemaId))}`, BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "DELETE",
            headers: buildHeaders(false),
            redirect: "follow",
        });
        if (resp.status === 200 || resp.status === 204) {
            const idStr = String(schemaId);
            const prev = schemaStore.getState();
            const schemas = prev.schemas.filter(s => String(s.id) !== idStr);
            const options = prev.options.filter(o => o.value !== idStr);
            let selected = prev.selectedId;
            if (selected === idStr) selected = options[0]?.value ?? null;
            schemaStore.setState({ schemas, options, selectedId: selected });
            if (selected) saveSchema(selected); else saveSchema(null);
            return;
        }
        let payload: any = undefined;
        try {
            const ct = resp.headers.get("content-type") || "";
            payload = ct.includes("application/json") ? await resp.json() : await resp.text();
        } catch { }
        if (resp.status === 404) throw new NotFoundError("数据库模式不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`schema delete failed: ${resp.status}`, resp.status, payload);
    },
};
