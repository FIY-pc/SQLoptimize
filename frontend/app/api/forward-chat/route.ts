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

    const externalURL = process.env.EXTERNAL_BACKEND_URL || "http://127.0.0.1:8000/api/optimize";
    const payload = buildOptimizeRequestPayload(body);

    try {
        const resp = await fetch(externalURL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            const text = await resp.text();
            return createAssistantUIErrorStream(`外部后端错误: ${resp.status}`, text);
        }

        const externalData = await parseExternalResponse(resp);
        const uiMessages = convertOptimizeResponseToUIMessages(externalData);
        return createAssistantUITextStreamResponse(uiMessages);
    } catch (err: any) {
        return createAssistantUIErrorStream("调用外部后端失败", err?.message);
    }
}

// 严格 Assistant UI 协议流式输出，开头加 start
function createAssistantUITextStreamResponse(uiMessages: any[]) {
    // 只取最后一个 assistant 消消息
    const lastAssistantMessage = uiMessages
        .slice().reverse().find(msg => msg.role === 'assistant');
    if (!lastAssistantMessage || !lastAssistantMessage.parts || !lastAssistantMessage.parts[0]?.text) {
        return createAssistantUIErrorStream("没有找到助理回复内容");
    }
    const content = lastAssistantMessage.parts[0].text;
    const encoder = new TextEncoder();
    const msgId = crypto.randomUUID();
    const chunks = splitContentIntoChunks(content);
    let idx = 0;
    const stream = new ReadableStream({
        start(controller) {
            // 0. 发送 start
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "start" })}\n\n`));
            // 1. 发送 text-start
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text-start", id: msgId })}\n\n`));
        },
        pull(controller) {
            if (idx < chunks.length) {
                // 2. 发送 text-delta
                const chunk = chunks[idx++];
                const data = {
                    type: "text-delta",
                    id: msgId,
                    delta: chunk
                };
                controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
            } else if (idx === chunks.length) {
                // 3. 发送 text-end
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text-end", id: msgId })}\n\n`));
                // 4. 发送 finish
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "finish" })}\n\n`));
                // 5. 发送 [DONE]
                controller.enqueue(encoder.encode(`data: [DONE]\n\n`));
                controller.close();
                idx++;
            }
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

function splitContentIntoChunks(content: string): string[] {
    // 按句子或每 30 字分块
    const chunks: string[] = [];
    const sentences = content.split(/([。！？\.!?])/);
    let currentChunk = '';
    for (let i = 0; i < sentences.length; i++) {
        currentChunk += sentences[i];
        if ((i % 2 === 1 && sentences[i].match(/[。！？\.!?]/)) || currentChunk.length >= 30) {
            if (currentChunk.trim()) {
                chunks.push(currentChunk);
            }
            currentChunk = '';
        }
    }
    if (currentChunk.trim()) {
        chunks.push(currentChunk);
    }
    if (chunks.length === 0) {
        const fixedChunkSize = 10;
        for (let i = 0; i < content.length; i += fixedChunkSize) {
            chunks.push(content.slice(i, i + fixedChunkSize));
        }
    }
    return chunks;
}

function createAssistantUIErrorStream(error: string, details?: string) {
    const encoder = new TextEncoder();
    const errorData = {
        type: 'error',
        error: details ? `${error}: ${details}` : error
    };
    const stream = new ReadableStream({
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