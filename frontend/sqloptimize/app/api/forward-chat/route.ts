import type { UIMessage } from "ai";

// 说明：这个接口作为一个“中转层”示例，它接收前端 Assistant UI 发送的标准 UIMessage 数组
// 然后按你自定义后端（已有独立服务）的需求打包转发。
// 你可以根据目标后端协议修改 payload 的结构、header、鉴权等。

// 环境变量建议：
// EXTERNAL_BACKEND_URL=https://your-backend.example.com/chat
// EXTERNAL_BACKEND_API_KEY=xxxxx （如果需要鉴权）

interface ForwardBody {
  messages: UIMessage[];
  // 允许前端额外附带的元信息（可选）
  meta?: Record<string, unknown>;
  // 可选：显式模型，若不传可由后端自行决定
  model?: string;
}

interface ExternalRequestPayload {
  // 这里是给你的自定义后端的“规范化”格式，你可以自由调整
  conversation: Array<{
    id: string;
    role: string;
    content: Array<{ type: string; text?: string }>;
  }>;
  model?: string;
  meta?: Record<string, unknown>;
  // 预留参数：可携带温度、采样等
  params?: Record<string, unknown>;
}

export async function POST(req: Request) {
  let body: ForwardBody;
  try {
    body = await req.json();
  } catch (e) {
    return new Response(
      JSON.stringify({ error: "请求体必须是合法 JSON" }),
      { status: 400, headers: { "content-type": "application/json" } },
    );
  }

  if (!body?.messages || !Array.isArray(body.messages)) {
    return new Response(
      JSON.stringify({ error: "缺少 messages 或格式不正确" }),
      { status: 400, headers: { "content-type": "application/json" } },
    );
  }

  const externalURL = process.env.EXTERNAL_BACKEND_URL;
  if (!externalURL) {
    return new Response(
      JSON.stringify({ error: "未配置 EXTERNAL_BACKEND_URL" }),
      { status: 500, headers: { "content-type": "application/json" } },
    );
  }

  // 映射 UIMessage -> 你的后端想要的格式
  const payload: ExternalRequestPayload = {
    conversation: body.messages.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.parts.map((p) => ({ type: p.type, text: (p as any).text })),
    })),
    model: body.model,
    meta: body.meta,
    params: {},
  };

  const headers: Record<string, string> = {
    "content-type": "application/json",
  };
  if (process.env.EXTERNAL_BACKEND_API_KEY) {
    headers["authorization"] = `Bearer ${process.env.EXTERNAL_BACKEND_API_KEY}`;
  }

  try {
    const resp = await fetch(externalURL, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    // 如果你的后端支持流式（SSE / chunk），这里可以改造成直接透传。
    // 目前简化为：读取完整 JSON。
    const contentType = resp.headers.get("content-type") || "";
    if (!resp.ok) {
      const text = await resp.text();
      return new Response(
        JSON.stringify({ error: "外部后端错误", status: resp.status, body: text }),
        { status: 502, headers: { "content-type": "application/json" } },
      );
    }

    if (contentType.includes("application/json")) {
      const data = await resp.json();
      return new Response(JSON.stringify({ data }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    // 回退：非 JSON 直接原样文本返回
    const text = await resp.text();
    return new Response(text, { status: 200 });
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: "调用外部后端失败", message: err?.message }),
      { status: 500, headers: { "content-type": "application/json" } },
    );
  }
}

// TODO: 如需流式透传：
// 1. 将 fetch 的响应 body 直接 return new Response(resp.body, { headers: { 'content-type': 'text/event-stream' } })
// 2. 或者对 chunk 做适配转换再推送给前端。
