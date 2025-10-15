"use client";

import { TOKEN_STORAGE_KEY } from "./serviceUtils";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export type AuthResponse = {
    access_token: string;
    refresh_token: string;
    token_type: string; // "bearer"
    user_id: number;
    user_name: string;
};

export type RegisterRequest = {
    name: string;
    email: string;
    password: string;
};

export type LoginRequest = {
    email: string;
    password: string;
};

const AUTH_STORAGE_KEY = "SQLopt.auth";

export type AuthState = {
    accessToken: string;
    refreshToken: string;
    tokenType: string;
    userId: number;
    userName: string;
};

export const AUTH_CHANGED_EVENT = "sqlopt:auth-changed";
type AuthChangedDetail = { kind: "login" | "logout" };
function emitAuthChanged(kind: AuthChangedDetail["kind"]) {
    if (typeof window === "undefined") return;
    try {
        window.dispatchEvent(new CustomEvent<AuthChangedDetail>(AUTH_CHANGED_EVENT as any, { detail: { kind } }));
    } catch { }
}

export function saveAuth(auth: AuthState) {
    if (typeof window === "undefined") return;
    try {
        window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
        // 兼容现有 ModelPicker 等读取的 token key
        window.localStorage.setItem(TOKEN_STORAGE_KEY, auth.accessToken);
        emitAuthChanged("login");
    } catch { }
}

export function getAuth(): AuthState | null {
    if (typeof window === "undefined") return null;
    try {
        const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
        if (!raw) return null;
        return JSON.parse(raw) as AuthState;
    } catch {
        return null;
    }
}

export function isLoggedIn(): boolean {
    const a = getAuth();
    return !!(a && a.accessToken);
}

export function clearAuth() {
    if (typeof window === "undefined") return;
    try {
        window.localStorage.removeItem(AUTH_STORAGE_KEY);
        window.localStorage.removeItem(TOKEN_STORAGE_KEY);
        emitAuthChanged("logout");
    } catch { }
}

async function request<T>(path: string, body: any): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: {
            "content-type": "application/json",
            accept: "application/json",
        },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `HTTP ${res.status}`);
    }
    return (await res.json()) as T;
}

export async function registerUser(payload: RegisterRequest): Promise<AuthState> {
    const data = await request<AuthResponse>("/api/auth/register", payload);
    const auth: AuthState = {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        tokenType: data.token_type,
        userId: data.user_id,
        userName: data.user_name,
    };
    saveAuth(auth);
    return auth;
}

export async function loginUser(payload: LoginRequest): Promise<AuthState> {
    const data = await request<AuthResponse>("/api/auth/login", payload);
    const auth: AuthState = {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        tokenType: data.token_type,
        userId: data.user_id,
        userName: data.user_name,
    };
    saveAuth(auth);
    return auth;
}
