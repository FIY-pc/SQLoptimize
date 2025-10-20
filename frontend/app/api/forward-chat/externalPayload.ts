import type { UIMessage } from "ai";

// 前端请求体（Assistant UI 发来的格式）
export interface ForwardBody {
    messages: UIMessage[];
    meta?: Record<string, unknown>;
    model?: string;
}

// 发往后端 /api/optimize 的请求体
export interface OptimizeRequestPayload {
    sql: string;
    stream: boolean;
}

// 构建发往后端的请求体（仅保留流式所需字段）
export function buildOptimizeRequestPayload(body: ForwardBody): OptimizeRequestPayload {
    // 取最后一条 user 消息作为 SQL 输入
    const lastUser = [...body.messages].reverse().find(m => m.role === 'user');
    const parts = lastUser?.parts ?? [];
    const texts: string[] = [];
    for (const p of parts as unknown[]) {
        if (typeof p === 'string') {
            texts.push(p);
            continue;
        }
        if (typeof p === 'object' && p !== null) {
            const text = (p as Record<string, unknown>).text;
            if (typeof text === 'string') texts.push(text);
        }
    }
    const sql = texts.filter(Boolean).join('\n');

    // 可从 meta 读取控制项（可选）
    const meta = body.meta || {};
    const stream = typeof meta.stream === 'boolean' ? meta.stream : true;

    const payload: OptimizeRequestPayload = {
        sql,
        stream: Boolean(stream)
    };
    return payload;
}

// 统一错误流（Assistant UI 协议）
export function createAssistantUIErrorStream(error: string, details?: string) {
    const encoder = new TextEncoder();
    const errorData = {
        type: 'error',
        error: details ? `${error}: ${details}` : error
    };
    const stream = new ReadableStream<Uint8Array>({
        start(controller) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(errorData)}\n\n`));
            controller.enqueue(encoder.encode(`data: [DONE]\n\n`));
            controller.close();
        }
    });
    return new Response(stream, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        },
    });
}

// 将后端流转换并直接构造 Assistant UI 响应（集成转换和响应头）
export function toAssistantUIResponse(backendStream: ReadableStream<Uint8Array>) {
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();
    const msgId = crypto.randomUUID();
    let buffer = "";
    let started = false;

    // 提取行（兼容 SSE 的 data: 行和 NDJSON）
    function* extractPayloadLines(text: string): Generator<string> {
        const lines = text.split(/\r?\n/);
        for (const raw of lines) {
            const trimmed = raw.trim();
            if (!trimmed) continue;
            if (trimmed.startsWith('data:')) {
                const payload = trimmed.slice(5).trim();
                if (payload) yield payload;
            } else {
                yield trimmed;
            }
        }
    }

    const uiTransform = new TransformStream<Uint8Array, Uint8Array>({
        start(controller) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "start" })}\n\n`));
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text-start", id: msgId })}\n\n`));
            started = true;
        },
        transform(chunk, controller) {
            buffer += decoder.decode(chunk, { stream: true });

            // 只处理完整的行，余下留到下次
            const lastNewlineIdx = Math.max(buffer.lastIndexOf('\n'), buffer.lastIndexOf('\r'));
            if (lastNewlineIdx === -1) return;

            const processPart = buffer.slice(0, lastNewlineIdx + 1);
            buffer = buffer.slice(lastNewlineIdx + 1);

            for (const jsonLine of extractPayloadLines(processPart)) {
                if (jsonLine === "[DONE]") continue;
                try {
                    const obj = JSON.parse(jsonLine);
                    if (obj?.type === 'AIMessageChunk' && typeof obj?.content === 'string' && obj.content) {
                        const deltaEvt = { type: 'text-delta', id: msgId, delta: obj.content };
                        controller.enqueue(encoder.encode(`data: ${JSON.stringify(deltaEvt)}\n\n`));
                    }
                } catch {
                    // 忽略无法解析的行
                }
            }
        },
        flush(controller) {
            if (started) {
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text-end", id: msgId })}\n\n`));
            }
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "finish" })}\n\n`));
            controller.enqueue(encoder.encode(`data: [DONE]\n\n`));
        },
    });

    const piped = backendStream.pipeThrough(uiTransform);
    return new Response(piped, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'x-accel-buffering': 'no',
            'x-vercel-ai-ui-message-stream': 'v1',
        },
    });
}
