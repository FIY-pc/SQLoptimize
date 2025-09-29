import {
    buildOptimizeRequestPayload,
    convertOptimizeResponseToUIMessages,
    parseExternalResponse,
    ForwardBody,
} from "./externalPayload";

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

    // 你的后端 /api/optimize 接口地址
    const externalURL = process.env.EXTERNAL_BACKEND_URL || "http://127.0.0.1:8000/api/optimize";

    // 1. 使用新的函数构建请求体
    const payload = buildOptimizeRequestPayload(body);

    try {
        const resp = await fetch(externalURL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            const text = await resp.text();
            return new Response(
                JSON.stringify({ error: "外部后端错误", status: resp.status, body: text }),
                { status: 502, headers: { "content-type": "application/json" } }
            );
        }

        // 2. 解析后端响应
        const data = await parseExternalResponse(resp);

        // 3. 将后端响应转换为 UI 消息
        const uiMessages = convertOptimizeResponseToUIMessages(data);

        // 4. 将格式化后的消息返回给前端
        // 注意：这里我们直接返回一个包含新消息的 JSON 对象，而不是流。
        // 前端 useAssistant hook 会接收这个对象并更新UI。
        return new Response(JSON.stringify({ messages: uiMessages }), {
            status: 200,
            headers: { "content-type": "application/json" },
        });

    } catch (err: any) {
        return new Response(
            JSON.stringify({ error: "调用外部后端失败", message: err?.message }),
            { status: 500, headers: { "content-type": "application/json" } }
        );
    }
}