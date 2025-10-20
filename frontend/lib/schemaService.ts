"use client";

import { HttpError, NotFoundError, ValidationError } from "./modelService";
import { buildHeaders, createStore, createSelectedIdStorage } from "./serviceUtils";

const BASE_URL = process.env.NEXT_PUBLIC_MODEL_SERVICE_URL || "http://127.0.0.1:8000";

export type CreateDbSchema = Record<string, unknown>;
export type UpdateDbSchema = Record<string, unknown>;

export interface BackendDbSchemaItem {
    id: number;
    schema_name: string;
    schema_content: string;
    created_at: string;
    updated_at: string;
    user_id: number;
    [key: string]: unknown;
}

export interface ListDbSchemasResponse {
    schemas: BackendDbSchemaItem[];
    total: number;
    skip: number;
    limit: number;
    has_more?: boolean;
    active_schema_id?: number; // 0 表示无活跃
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

// 纯 HTTP API 客户端（7 个方法）
export const schemaApi = {
    async getActive(): Promise<BackendDbSchemaItem> {
        const url = new URL("/api/schemas/active", BASE_URL);
        const resp = await fetch(url.toString(), { method: "GET", headers: buildHeaders(false), redirect: "follow" });
        if (resp.ok) return (await resp.json()) as BackendDbSchemaItem;
        let payload: unknown = undefined;
        try { const ct = resp.headers.get("content-type") || ""; payload = ct.includes("application/json") ? await resp.json() : await resp.text(); } catch { }
        if (resp.status === 404) throw new NotFoundError("未找到活跃数据库模式", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`schema getActive failed: ${resp.status}`, resp.status, payload);
    },
    async list(params?: { skip?: number; limit?: number }): Promise<ListDbSchemasResponse> {
        const url = new URL("/api/schemas/", BASE_URL);
        const skip = params?.skip ?? 0;
        const limit = params?.limit ?? 100;
        url.searchParams.set("skip", String(skip));
        url.searchParams.set("limit", String(limit));
        const resp = await fetch(url.toString(), { method: "GET", headers: buildHeaders(false), redirect: "follow" });
        if (!resp.ok) throw new Error(`schema list failed: ${resp.status}`);
        const data = await resp.json().catch(() => undefined);
        if (!data || !Array.isArray(data.schemas)) return { schemas: [], total: 0, skip, limit };
        return data as ListDbSchemasResponse;
    },
    async create(payload: CreateDbSchema): Promise<BackendDbSchemaItem> {
        const url = new URL("/api/schemas/", BASE_URL);
        const resp = await fetch(url.toString(), { method: "POST", headers: buildHeaders(true), body: JSON.stringify(payload), redirect: "follow" });
        if (!resp.ok) throw new Error(`schema create failed: ${resp.status}`);
        return (await resp.json()) as BackendDbSchemaItem;
    },
    async setActive(schemaId: number | string) {
        const url = new URL("/api/schemas/active", BASE_URL);
        const resp = await fetch(url.toString(), { method: "POST", headers: buildHeaders(true), body: JSON.stringify({ schema_id: Number(schemaId) }), redirect: "follow" });
        if (resp.ok) { try { return await resp.json(); } catch { return { message: "OK" }; } }
        let payload: unknown = undefined;
        try { const ct = resp.headers.get("content-type") || ""; payload = ct.includes("application/json") ? await resp.json() : await resp.text(); } catch { }
        if (resp.status === 404) throw new NotFoundError("记录不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`schema setActive failed: ${resp.status}`, resp.status, payload);
    },
    async get(schemaId: number | string): Promise<BackendDbSchemaItem> {
        const url = new URL(`/api/schemas/${encodeURIComponent(String(schemaId))}`, BASE_URL);
        const resp = await fetch(url.toString(), { method: "GET", headers: buildHeaders(false), redirect: "follow" });
        if (resp.ok) return (await resp.json()) as BackendDbSchemaItem;
        let payload: unknown = undefined;
        try { const ct = resp.headers.get("content-type") || ""; payload = ct.includes("application/json") ? await resp.json() : await resp.text(); } catch { }
        if (resp.status === 404) throw new NotFoundError("数据库模式不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`schema get failed: ${resp.status}`, resp.status, payload);
    },
    async update(schemaId: number | string, payload: UpdateDbSchema, method: "PUT" | "PATCH" = "PUT"): Promise<BackendDbSchemaItem> {
        const url = new URL(`/api/schemas/${encodeURIComponent(String(schemaId))}`, BASE_URL);
        const resp = await fetch(url.toString(), { method, headers: buildHeaders(true), body: JSON.stringify(payload), redirect: "follow" });
        if (!resp.ok) throw new Error(`schema update failed: ${resp.status}`);
        return (await resp.json()) as BackendDbSchemaItem;
    },
    async remove(schemaId: number | string): Promise<void> {
        const url = new URL(`/api/schemas/${encodeURIComponent(String(schemaId))}`, BASE_URL);
        const resp = await fetch(url.toString(), { method: "DELETE", headers: buildHeaders(false), redirect: "follow" });
        if (resp.status === 200 || resp.status === 204) return;
        let payload: unknown = undefined;
        try { const ct = resp.headers.get("content-type") || ""; payload = ct.includes("application/json") ? await resp.json() : await resp.text(); } catch { }
        if (resp.status === 404) throw new NotFoundError("数据库模式不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`schema delete failed: ${resp.status}`, resp.status, payload);
    },
};

// Service 层（带本地状态）
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
            const data = await schemaApi.list();
            const items = Array.isArray(data.schemas) ? data.schemas : [];
            const options = toOptions(items);
            schemaStore.setState({ schemas: items, options });
            let selected = readSavedSchema();
            if (!selected) {
                const activeId = typeof data.active_schema_id === "number" && data.active_schema_id > 0
                    ? String(data.active_schema_id)
                    : null;
                if (activeId) {
                    selected = activeId;
                } else {
                    try { const active = await schemaApi.getActive(); selected = active ? String(active.id) : null; } catch { }
                }
            }
            if (selected && !options.find(o => o.value === selected)) selected = null;
            if (!selected) selected = options[0]?.value ?? null;
            schemaStore.setState({ selectedId: selected });
            if (selected) saveSchema(selected);
        } catch (e) {
            schemaStore.setState({ error: e instanceof Error ? e.message : String(e) });
        } finally { schemaStore.setState({ loading: false }); }
    },

    async refresh() {
        schemaStore.setState({ loading: true, error: undefined });
        try {
            const data = await schemaApi.list();
            const items = Array.isArray(data.schemas) ? data.schemas : [];
            const options = toOptions(items);
            // 优先使用后端返回的活跃项
            const activeId = typeof data.active_schema_id === "number" && data.active_schema_id > 0
                ? String(data.active_schema_id) : null;
            let selected = activeId;
            if (!selected) {
                // 否则保留当前有效选中，否则选列表首项
                const current = schemaStore.getState().selectedId;
                selected = current && options.find(o => o.value === current) ? current : (options[0]?.value ?? null);
            }
            schemaStore.setState({ schemas: items, options, selectedId: selected });
            if (selected) saveSchema(selected); else saveSchema(null);
        } catch (e) {
            schemaStore.setState({ error: e instanceof Error ? e.message : String(e) });
        } finally { schemaStore.setState({ loading: false }); }
    },

    async select(id: string) {
        const numericId = Number(id);
        await schemaApi.setActive(numericId);
        if (schemaStore.getState().options.find(o => o.value === String(numericId))) {
            schemaStore.setState({ selectedId: String(numericId) });
            saveSchema(String(numericId));
        } else {
            await this.refresh();
        }
    },

    // 代理 API 方法（必要时附带本地状态同步）
    async getActive() { return schemaApi.getActive(); },
    async list(params?: { skip?: number; limit?: number }) { return schemaApi.list(params); },
    async get(schemaId: number | string) { return schemaApi.get(schemaId); },

    async create(payload: CreateDbSchema) {
        const created = await schemaApi.create(payload);
        // 创建后刷新列表，便于立刻出现在下拉项中
        await this.refresh();
        return created;
    },

    async update(schemaId: number | string, payload: UpdateDbSchema, method: "PUT" | "PATCH" = "PUT") {
        const updated = await schemaApi.update(schemaId, payload, method);
        // 就地同步本地 store
        const prev = schemaStore.getState();
        const idStr = String(schemaId);
        const schemas = prev.schemas.map(s => String(s.id) === idStr ? { ...s, ...updated } : s);
        const options = prev.options.map(o => o.value === idStr ? { ...o, name: updated.schema_name || o.name } : o);
        schemaStore.setState({ schemas, options });
        return updated;
    },

    async remove(schemaId: number | string) {
        await schemaApi.remove(schemaId);
        // 删除后就地更新本地 store
        const idStr = String(schemaId);
        const prev = schemaStore.getState();
        const schemas = prev.schemas.filter(s => String(s.id) !== idStr);
        const options = prev.options.filter(o => o.value !== idStr);
        let selected = prev.selectedId;
        if (selected === idStr) selected = options[0]?.value ?? null;
        schemaStore.setState({ schemas, options, selectedId: selected });
        if (selected) saveSchema(selected); else saveSchema(null);
    },
};
