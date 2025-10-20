import {
    buildOptimizeRequestPayload,
    ForwardBody,
    toAssistantUIResponse,
    createAssistantUIErrorStream,
} from "./externalPayload";

// 小工具：标准 JSON 响应
function jsonError(message: string, status = 400, detail?: unknown) {
    return new Response(
        JSON.stringify(detail !== undefined ? { error: message, detail } : { error: message }),
        {
            status,
            headers: { "content-type": "application/json", "cache-control": "no-store" },
        }
    );
}

// 解析请求体（必须是合法 JSON）
async function readBody(req: Request): Promise<ForwardBody | Response> {
    try {
        return (await req.json()) as ForwardBody;
    } catch {
        return jsonError("请求体必须是合法 JSON", 400);
    }
}

// 只使用一个 BASE（NEXT_PUBLIC_SQLOPT_SERVICE_URL），服务器端在容器环境下把 localhost/127.0.0.1 映射为 backend
function resolveBackendBase(): string {
    const publicBase = process.env.NEXT_PUBLIC_SQLOPT_SERVICE_URL || "http://127.0.0.1:8000";
    try {
        const u = new URL(publicBase);
        if (u.hostname === "localhost" || u.hostname === "127.0.0.1") {
            u.hostname = "backend"; // 容器内通过服务名访问后端
        }
        return u.toString();
    } catch {
        return publicBase; // 不可解析则直接返回默认
    }
}

// 构造鉴权头（优先：Authorization → x-model-service-token）
function buildAuthHeader(req: Request): string | undefined {
    const incomingAuth = req.headers.get("authorization") || req.headers.get("Authorization");
    if (incomingAuth) return incomingAuth;
    const headerToken = req.headers.get("x-model-service-token");
    return headerToken ? `Bearer ${headerToken}` : undefined;
}

export async function POST(req: Request) {
    // 1) 读取并校验请求体
    const maybeBody = await readBody(req);
    if (maybeBody instanceof Response) return maybeBody;
    const body = maybeBody;
    if (!body?.messages || !Array.isArray(body.messages) || body.messages.length === 0) {
        return jsonError("缺少 messages 或格式不正确", 400);
    }

    // 2) 解析后端地址与拼接目标 URL
    const serverBase = resolveBackendBase();
    const externalURL = new URL("/api/optimize", serverBase).toString();
    const payload = buildOptimizeRequestPayload(body);
    if (!payload.sql) {
        // 直接返回 UI 错误流，避免对后端发起无效调用
        return createAssistantUIErrorStream("缺少 SQL 输入");
    }

    // 3) 代理转发（SSE）
    try {
        const authHeader = buildAuthHeader(req);
        const resp = await fetch(externalURL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "text/event-stream",
                ...(authHeader ? { Authorization: authHeader } : {}),
            },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            // 鉴权失败：向前端透传 401/403，触发统一注销处理
            if (resp.status === 401 || resp.status === 403) {
                const text = await resp.text().catch(() => "");
                return jsonError("未授权或登录已过期", resp.status, text || undefined);
            }
            const text = await resp.text();
            return createAssistantUIErrorStream(`外部后端错误: ${resp.status}`, text);
        }

        // 流式响应适配
        if (!resp.body) return createAssistantUIErrorStream("后端返回了空的流");
        return toAssistantUIResponse(resp.body);
    } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return createAssistantUIErrorStream("调用外部后端失败", message);
    }
}