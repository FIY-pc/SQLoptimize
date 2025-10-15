"use client";

// 前端直连后端服务封装
// 读取公开环境变量（需以 NEXT_PUBLIC_ 开头）或从 localStorage 读取 token

import { buildHeaders, createStore, createSelectedIdStorage } from "./serviceUtils";

const BASE_URL = process.env.NEXT_PUBLIC_MODEL_SERVICE_URL || "http://127.0.0.1:8000";

// =========================
// 错误类型
// =========================
export class HttpError extends Error {
    constructor(message: string, public status: number, public data?: any) {
        super(message);
    }
}
export class NotFoundError extends HttpError {
    constructor(msg = "Not Found", data?: any) { super(msg, 404, data); }
}
export class ValidationError extends HttpError {
    constructor(msg = "Unprocessable Entity", data?: any) { super(msg, 422, data); }
}

// =========================
// API 客户端（纯 HTTP，无本地状态）
// 说明：只负责发起请求与错误处理，完全不触碰 store。
// =========================
export const modelApi = {
    /** 获取当前活跃的模型连接 */
    async getActive(): Promise<BackendModelItem> {
        const url = new URL("/api/models/active", BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "GET",
            headers: buildHeaders(false),
            redirect: "follow"
        });

        if (!resp.ok) {
            if (resp.status === 404) throw new NotFoundError("未找到活跃模型连接");
            throw new Error(`getActive failed: ${resp.status}`);
        }
        const data = await resp.json();
        return data as BackendModelItem;
    },

    /** 获取用户模型连接列表 */
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
        if (!data || !Array.isArray(data.models)) {
            return { models: [], total: 0, skip, limit };
        }
        return data as ListModelsResponse;
    },

    /** 创建模型连接 */
    async create(payload: CreateModelConnection): Promise<BackendModelItem> {
        const url = new URL("/api/models/", BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "POST",
            headers: buildHeaders(true),
            body: JSON.stringify(payload),
            redirect: "follow"
        });
        if (!resp.ok) throw new Error(`create failed: ${resp.status}`);
        const created = await resp.json();
        return created as BackendModelItem;
    },

    /** 设置当前活跃的模型连接 */
    async setActive(connectionId: number | string): Promise<SetActiveModelConnectionResponse> {
        const url = new URL("/api/models/active", BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "POST",
            headers: buildHeaders(true),
            body: JSON.stringify({ connection_id: Number(connectionId) }),
            redirect: "follow"
        });

        if (resp.ok) {
            try { return await resp.json(); } catch { return { message: "OK" }; }
        }

        let payload: any = undefined;
        try {
            const ct = resp.headers.get("content-type") || "";
            if (ct.includes("application/json")) payload = await resp.json();
            else payload = await resp.text();
        } catch (_) { /* ignore */ }

        if (resp.status === 404) throw new NotFoundError("记录不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`setActive failed: ${resp.status}`, resp.status, payload);
    },

    /** 根据 ID 获取模型连接 */
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

    /** 更新模型连接 */
    async update(connectionId: string, payload: UpdateModelConnection, method: "PUT" | "PATCH" = "PUT"): Promise<BackendModelItem> {
        const url = new URL(`/api/models/${encodeURIComponent(connectionId)}`, BASE_URL);
        const resp = await fetch(url.toString(), {
            method,
            headers: buildHeaders(true),
            body: JSON.stringify(payload),
            redirect: "follow"
        });
        if (!resp.ok) throw new Error(`update failed: ${resp.status}`);
        const updated = (await resp.json()) as BackendModelItem;
        return updated;
    },

    /** 删除模型连接 */
    async remove(connectionId: number | string): Promise<void> {
        const url = new URL(`/api/models/${encodeURIComponent(String(connectionId))}`, BASE_URL);
        const resp = await fetch(url.toString(), {
            method: "DELETE",
            headers: buildHeaders(false),
            redirect: "follow"
        });
        if (resp.status === 200 || resp.status === 204) return;

        let payload: any = undefined;
        try {
            const ct = resp.headers.get("content-type") || "";
            if (ct.includes("application/json")) payload = await resp.json();
            else payload = await resp.text();
        } catch (_) { /* ignore */ }

        if (resp.status === 404) throw new NotFoundError("记录不存在", payload);
        if (resp.status === 422) throw new ValidationError("参数错误", payload);
        throw new HttpError(`delete failed: ${resp.status}`, resp.status, payload);
    },
};

// =========================
// 类型定义
// =========================
export type CreateModelConnection = Record<string, any>; // 可按后端实际细化
export type UpdateModelConnection = Record<string, any>;

// 定义模型项（后端会返回已混淆的 api_key，可按需使用）
export interface BackendModelItem {
    id: number;
    model_name: string; // 展示名
    model: string; // 模型标识
    base_url: string;
    api_key: string;
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
    // 后端还会返回以下字段，这里标记为可选，避免破坏性变更
    has_more?: boolean;
    active_connection_id?: number; // 0 表示无活跃连接
}

// 设置活跃连接响应
export interface SetActiveModelConnectionResponse { message: string }

// 本地状态与订阅机制（轻量 store）
export type ModelOption = { value: string; name: string; iconKey: string };
type ModelState = {
    models: BackendModelItem[];
    options: ModelOption[];
    selectedId: string | null;
    loading: boolean;
    error?: string;
};

// =========================
// 本地状态与持久化
// =========================
const LS_SELECTED_KEY = "SELECTED_MODEL_ID";
const store = createStore<ModelState>({ models: [], options: [], selectedId: null, loading: false });
const selectedStorage = createSelectedIdStorage(LS_SELECTED_KEY);

function pickIconKey(modelOrName?: string): string {
    const key = (modelOrName || "").toLowerCase();
    if (/openai|gpt/.test(key)) return "openai";
    if (/deepseek/.test(key)) return "deepseek";
    if (/claude|anthropic/.test(key)) return "anthropic";
    if (/gemini|google/.test(key)) return "google";
    if (/llama|meta/.test(key)) return "meta";
    if (/mistral/.test(key)) return "mistral";
    if (/firefunction|fireworks/.test(key)) return "fireworks";
    if (/qwen/.test(key)) return "qwen";
    return "openai";
}

const toOptions = (models: BackendModelItem[]) => models.map(it => ({
    value: String(it.id),
    name: it.model_name || it.model || String(it.id),
    iconKey: pickIconKey(it.model),
}));

let initPromise: Promise<void> | null = null;

// 统一写入 models/options/selectedId 到 store，并持久化 selectedId
function applyModelsToStore(models: BackendModelItem[], selectedOverride?: string | null) {
    const options = toOptions(models);
    // 优先使用外部传入的选中值，其次取当前 store 的选中值
    let selected = selectedOverride ?? store.getState().selectedId ?? null;
    if (!options.some(o => o.value === selected)) selected = options[0]?.value ?? null;
    store.setState({ models, options, selectedId: selected });
    selectedStorage.save(selected ?? null);
}

export const modelService = {
    // 订阅/取消订阅本地状态
    subscribe(fn: () => void) {
        return store.subscribe(fn);
    },
    getState(): Readonly<ModelState> { return store.getState(); },
    getOptions(): ModelOption[] { return store.getState().options; },
    getSelectedId(): string | null { return store.getState().selectedId; },

    // 初始化：拉取列表并设置选中（优先本地保存 → 后端活跃 → 列表首项）
    async init() {
        if (!initPromise) {
            initPromise = (async () => {
                store.setState({ loading: true, error: undefined });
                const data = await modelApi.list();
                const models = Array.isArray(data.models) ? data.models : [];
                // 先写入 models/options，再决策选中值
                applyModelsToStore(models, null);
                // 选中优先级：localStorage → 后端活跃 → 列表首项
                let selected = selectedStorage.read();
                if (!selected) {
                    const activeId = typeof data.active_connection_id === "number" && data.active_connection_id > 0
                        ? String(data.active_connection_id)
                        : null;
                    if (activeId) {
                        selected = activeId;
                    } else {
                        try {
                            const active = await modelApi.getActive();
                            selected = active ? String(active.id) : null;
                        } catch {
                            selected = null;
                        }
                    }
                }
                applyModelsToStore(models, selected);
                store.setState({ loading: false });
            })();
        }
        return initPromise;
    },

    // 手动刷新列表，尽量保留当前选择
    async refresh() {
        store.setState({ loading: true, error: undefined });
        try {
            const data = await modelApi.list();
            const models = Array.isArray(data.models) ? data.models : [];
            // 优先使用后端返回的活跃项
            const activeId = typeof data.active_connection_id === "number" && data.active_connection_id > 0
                ? String(data.active_connection_id) : null;
            if (activeId) {
                applyModelsToStore(models, activeId);
            } else {
                // 否则保留当前有效选中，否则选列表首项
                const current = store.getState().selectedId;
                const options = toOptions(models);
                const selected = current && options.some(o => o.value === current) ? current : (options[0]?.value ?? null);
                applyModelsToStore(models, selected);
            }
        } catch (e) {
            store.setState({ error: e instanceof Error ? e.message : String(e) });
        } finally {
            store.setState({ loading: false });
        }
    },

    // 选择并同步后端活跃项
    async select(id: string) {
        await modelApi.setActive(id);
        const found = store.getState().options.some(o => o.value === String(id));
        store.setState({ selectedId: found ? String(id) : store.getState().selectedId });
        selectedStorage.save(found ? String(id) : null);
        if (!found) await this.refresh();
    },
    /**
     * 获取当前活跃的模型连接
     * GET /api/models/active
     */
    async getActive(): Promise<BackendModelItem> {
        return modelApi.getActive();
    },
    /**
     * 获取用户模型连接列表
     * GET /api/models/
     */
    async list(params?: { skip?: number; limit?: number; model?: string }): Promise<ListModelsResponse> {
        return modelApi.list(params);
    },

    /**
     * 创建模型连接
     * POST /api/models/
     */
    async create(payload: CreateModelConnection): Promise<BackendModelItem> {
        const created = await modelApi.create(payload);
        // 刷新本地状态但不强制选中该新项
        this.refresh().catch(() => void 0);
        return created as BackendModelItem;
    },

    /**
     * 设置当前活跃的模型连接
     * POST /api/models/active
     */
    async setActive(connectionId: number | string): Promise<SetActiveModelConnectionResponse> {
        return modelApi.setActive(connectionId);
    },

    /**
     * 根据ID获取模型连接
     * GET /api/models/{connection_id}
     */
    async get(connectionId: number | string): Promise<BackendModelItem> {
        return modelApi.get(connectionId);
    },

    /**
     * 更新模型连接
     * PUT/PATCH /api/models/{connection_id}
     */
    async update(connectionId: string, payload: UpdateModelConnection, method: "PUT" | "PATCH" = "PUT"): Promise<BackendModelItem> {
        const updated = await modelApi.update(connectionId, payload, method);
        // 同步到本地 store，避免 UI 侧重复刷新
        const prev = store.getState();
        const nextModels = [...prev.models];
        const idx = nextModels.findIndex(m => String(m.id) === String(connectionId));
        if (idx >= 0) nextModels[idx] = updated; else nextModels.push(updated);
        applyModelsToStore(nextModels);
        return updated;
    },

    /**
     * 删除模型连接
     * DELETE /api/models/{connection_id}
     */
    async remove(connectionId: number | string): Promise<void> {
        await modelApi.remove(connectionId);
        // 本地状态同步删除
        const idStr = String(connectionId);
        const prev = store.getState();
        const nextModels = prev.models.filter(m => String(m.id) !== idStr);
        applyModelsToStore(nextModels);
    },
};
