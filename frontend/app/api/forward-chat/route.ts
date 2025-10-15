import { buildOptimizeRequestPayload, ForwardBody, toAssistantUIResponse, createAssistantUIErrorStream } from "./externalPayload";
// no-op

export async function POST(req: Request) {
    let body: ForwardBody;
    try {
        body = await req.json();
    } catch (e) {
        return new Response(JSON.stringify({ error: "请求体必须是合法 JSON" }), {
            status: 400,
            headers: { "content-type": "application/json" },
        });
    }

    if (!body?.messages || !Array.isArray(body.messages) || body.messages.length === 0) {
        return new Response(JSON.stringify({ error: "缺少 messages 或格式不正确" }), {
            status: 400,
            headers: { "content-type": "application/json" },
        });
    }

    const externalURL = process.env.EXTERNAL_BACKEND_URL || "http://127.0.0.1:8000/api/optimize";
    const payload = buildOptimizeRequestPayload(body);

    try {
        // 构造鉴权（优先顺序，与前端 buildHeaders 思路对齐）：
        // 1) 透传来访请求的 Authorization 头（如果前端已用 buildHeaders 注入）
        // 2) 自定义头 x-model-service-token（允许前端从 localStorage 显式传入）
        // 3) 回退到服务端环境变量中的 token
        const incomingAuth = req.headers.get("authorization") || req.headers.get("Authorization");
        const headerToken = req.headers.get("x-model-service-token");
        const fallbackToken = process.env.NEXT_PUBLIC_MODEL_SERVICE_TOKEN || process.env.MODEL_SERVICE_TOKEN;
        const chosenToken = headerToken || fallbackToken;
        const authHeader = incomingAuth || (chosenToken ? `Bearer ${chosenToken}` : undefined);

        const resp = await fetch(externalURL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                ...(authHeader ? { Authorization: authHeader } : {}),
            },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            const text = await resp.text();
            return createAssistantUIErrorStream(`外部后端错误: ${resp.status}`, text);
        }

        // 仅支持流式：将后端流直接适配为 Assistant UI 协议
        if (!resp.body) {
            return createAssistantUIErrorStream("后端返回了空的流");
        }
        return toAssistantUIResponse(resp.body);
    } catch (err: any) {
        return createAssistantUIErrorStream("调用外部后端失败", err?.message);
    }
}