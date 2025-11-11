import type { UIMessage } from "ai";

/**
 * Assistant UI 前端请求体结构
 */
export interface ForwardBody {
    messages: UIMessage[];
    meta?: Record<string, unknown>;
    model?: string;
}

/**
 * 发往后端的请求体
 */
export interface OptimizeRequestPayload {
    sql: string;
    stream: boolean;
}

/**
 * SSE 统一响应头，与 Assistant UI 协议保持兼容）
 */
export const SSE_HEADERS: Record<string, string> = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
    "x-accel-buffering": "no",
    "x-vercel-ai-ui-message-stream": "v1",
};

// 此文件编码器与解码器
const encoder = new TextEncoder();
const decoder = new TextDecoder();

/**
 * 从消息数组中提取最新一条 user 消息的文本。
 * 兼容两种结构：`content` 为字符串 或 `parts` 数组（其中元素可能是字符串或含 text 字段的对象）。
 */
export function extractLastUserText(messages: UIMessage[]): string {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return "";

    const chunks: string[] = [];
    // 处理 content
    const content = (lastUser as unknown as { content?: unknown }).content;
    if (typeof content === "string") chunks.push(content);

    // 处理 parts
    const parts = (lastUser as unknown as { parts?: unknown }).parts;
    if (Array.isArray(parts)) {
        for (const p of parts as unknown[]) {
            if (typeof p === "string") {
                chunks.push(p);
            } else if (p && typeof p === "object") {
                const text = (p as Record<string, unknown>).text;
                if (typeof text === "string") chunks.push(text);
            }
        }
    }
    return chunks.map(String).join("\n").trim();
}

/**
 * 构建后端需要的优化请求体：
 * - 优先取最新 user 消息文本作为 SQL
 * - 若为空则兜底使用 meta.sql
 * - stream 默认为 true
 */
export function buildOptimizeRequestPayload(body: ForwardBody): OptimizeRequestPayload {
    const meta = (body.meta || {}) as Record<string, unknown>;
    const fromMessages = extractLastUserText(body.messages);
    const fromMeta = typeof meta.sql === "string" ? meta.sql : "";
    const sql = (fromMessages || fromMeta || "").trim();

    const stream = typeof meta.stream === "boolean" ? meta.stream : true;
    return { sql, stream: Boolean(stream) };
}

/**
 * 生成 Assistant UI 协议的错误响应（流式 SSE），并立即结束。
 */
export function createAssistantUIErrorStream(error: string, details?: string) {
    const errorData = {
        type: "error",
        error: details ? `${error}: ${details}` : error,
    };
    const stream = new ReadableStream<Uint8Array>({
        start(controller) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(errorData)}\n\n`));
            controller.enqueue(encoder.encode(`data: [DONE]\n\n`));
            controller.close();
        },
    });
    return new Response(stream, { headers: SSE_HEADERS });
}

/**
 * 将后端输出的原始流（包含推理与文本增量）转换为 Assistant UI 约定的事件序列。
 * 保持原语义：按 step 分组，分别输出 reasoning 与 text 的开始 / 增量 / 结束事件。
 */
export function toAssistantUIResponse(backendStream: ReadableStream<Uint8Array>) {
    let buffer = ""; // 累积原始字节解码后的文本缓冲

    // step 元信息与状态
    let currentBackendStep: number | null = null; // 来自后端 metadata.langgraph_step
    let currentStepIndex = -1; // 对外暴露的顺序索引（自增）
    let stepActive = false; // 当前是否处于一个已开始的 step

    // 单个 step 内的局部状态
    let reasoningStarted = false;
    let lastReasoning = ""; // 用于计算 reasoning 增量 delta
    let textStarted = false;

    function reasoningId() {
        return `reasoning-${currentStepIndex}`;
    }
    function textId() {
        return `txt-${currentStepIndex}`;
    }

    /** 关闭当前 step（若打开），输出对应的 end 事件与 finish-step */
    function closeStep(controller: TransformStreamDefaultController<Uint8Array>) {
        if (!stepActive) return;
        if (reasoningStarted) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "reasoning-end", id: reasoningId() })}\n\n`));
        }
        if (textStarted) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text-end", id: textId() })}\n\n`));
        }
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "finish-step" })}\n\n`));
        // 重置局部状态
        stepActive = false;
        reasoningStarted = false;
        textStarted = false;
        lastReasoning = "";
    }

    /** 提取有效负载行（兼容 SSE 的 data: 前缀与裸行） */
    function* extractPayloadLines(text: string): Generator<string> {
        const lines = text.split(/\r?\n/);
        for (const raw of lines) {
            const trimmed = raw.trim();
            if (!trimmed) continue;
            if (trimmed.startsWith("data:")) {
                const payload = trimmed.slice(5).trim();
                if (payload) yield payload;
            } else {
                yield trimmed;
            }
        }
    }

    /** 处理单条 JSON 对象并发出对应事件 */
    function processObj(obj: any, controller: TransformStreamDefaultController<Uint8Array>) {
        const backendStep: number | null = obj?.metadata && typeof obj.metadata.langgraph_step === "number" ? obj.metadata.langgraph_step : null;

        // 是否需要开始新 step
        if (!stepActive || (backendStep !== null && backendStep !== currentBackendStep)) {
            closeStep(controller);
            currentStepIndex += 1;
            currentBackendStep = backendStep;
            stepActive = true;
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "start-step" })}\n\n`));
        }

        // reasoning 增量（两种字段兼容）
        if (typeof obj?.reasoning_content === "string") {
            const newText = obj.reasoning_content;
            const delta = newText.startsWith(lastReasoning) ? newText.slice(lastReasoning.length) : newText;
            if (delta) {
                if (!reasoningStarted) {
                    controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "reasoning-start", id: reasoningId() })}\n\n`));
                    reasoningStarted = true;
                }
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "reasoning-delta", id: reasoningId(), delta })}\n\n`));
                lastReasoning = newText;
            }
        } else if (obj?.type === "ReasoningChunk" && typeof obj?.content === "string" && obj.content) {
            if (!reasoningStarted) {
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "reasoning-start", id: reasoningId() })}\n\n`));
                reasoningStarted = true;
            }
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "reasoning-delta", id: reasoningId(), delta: obj.content })}\n\n`));
        }

        // 正文文本增量
        if (obj?.type === "AIMessageChunk" && typeof obj?.content === "string" && obj.content) {
            if (!textStarted) {
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text-start", id: textId() })}\n\n`));
                textStarted = true;
            }
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text-delta", id: textId(), delta: obj.content })}\n\n`));
        }
    }

    const uiTransform = new TransformStream<Uint8Array, Uint8Array>({
        start(controller) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "start" })}\n\n`));
        },
        transform(chunk, controller) {
            buffer += decoder.decode(chunk, { stream: true });
            const lastNewlineIdx = Math.max(buffer.lastIndexOf("\n"), buffer.lastIndexOf("\r"));
            if (lastNewlineIdx === -1) return; // 尚未形成完整行

            const completePart = buffer.slice(0, lastNewlineIdx + 1);
            buffer = buffer.slice(lastNewlineIdx + 1);

            for (const line of extractPayloadLines(completePart)) {
                if (line === "[DONE]") continue;
                try {
                    processObj(JSON.parse(line), controller);
                } catch {
                    // 忽略无法解析的行
                }
            }
        },
        flush(controller) {
            if (buffer.trim()) {
                for (const line of extractPayloadLines(buffer)) {
                    if (line === "[DONE]") continue;
                    try {
                        processObj(JSON.parse(line), controller);
                    } catch {
                        // 忽略无法解析的行
                    }
                }
            }
            // 结束最后一个 step
            closeStep(controller);
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "finish" })}\n\n`));
            controller.enqueue(encoder.encode(`data: [DONE]\n\n`));
        },
    });

    const piped = backendStream.pipeThrough(uiTransform);
    return new Response(piped, { headers: SSE_HEADERS });
}
