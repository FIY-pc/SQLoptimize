import type { UIMessage } from "ai";

// 1. 前端请求体结构 (保持不变, 前端UI发送的格式)
export interface ForwardBody {
    messages: UIMessage[];
    meta?: Record<string, unknown>;
    model?: string; // model 字段可以保留，但在这个流程中可能不会被使用
}

// 2. 中转到 /api/optimize 的 payload 结构
export interface OptimizeRequestPayload {
    sql: string;
    db_schema?: string;
    stream: boolean;
    stream_llm_chunk?: boolean;
}

// 3. 后端 /api/optimize 的响应体结构
export interface OptimizeResponsePayload {
    input_sql: string;
    optimized_sql: string;
    plan_feedback: string | null;
    db_schema: string;
    z3_result: string[];
    history: string[];
    timestamp: number;
}

// 4. 转换函数：将聊天消息转换为后端请求
export function buildOptimizeRequestPayload(body: ForwardBody): OptimizeRequestPayload {
    // 提取最后一条用户消息作为 SQL 输入
    const lastUserMessage = [...body.messages].reverse().find(m => m.role === 'user');
    const sql = lastUserMessage?.parts.map(p => (p as any).text).join('\n') || '';

    // 从 meta 中获取 db_schema (如果提供的话)
    const db_schema = body.meta?.db_schema as string | undefined;

    console.log("构建的请求体:", {
        sql: sql,
        db_schema: db_schema || "",
        stream: false,
        stream_llm_chunk: true,
    });

    return {
        sql: sql,
        db_schema: db_schema || "", // 如果没有提供，则发送空字符串
        stream: false, // 根据你的后端需求，这里可以设为 true
        stream_llm_chunk: true,
    };
}


// 5. 转换函数：将后端响应转为 UIMessage[]
export function convertOptimizeResponseToUIMessages(data: OptimizeResponsePayload): UIMessage[] {
    if (!data) return [];

    // 将优化结果和历史记录格式化为 Markdown
    const formattedContent = `
### SQL 优化结果

**输入的的 SQL:**
\`\`\`sql
${data.input_sql}
\`\`\`

**优化后的 SQL:**
\`\`\`sql
${data.optimized_sql}
\`\`\`

---

### 优化过程历史

\`\`\`
${data.history.join('\n')}
\`\`\`
    `;

    console.log("构建的响应体:", {formattedContent});
    return [{
        id: `asst_${Date.now()}`, // 创建一个新的消息 ID
        role: 'assistant',
        parts: [{ type: "text", text: formattedContent }],
    }];
}


// 6. 辅助函数：解析后端响应 (保持不变)
export async function parseExternalResponse(resp: Response): Promise<any> {
    const contentType = resp.headers.get("content-type") || "";
    console.log("外部后端响应的 Content-Type:", contentType);
    // 响应头是 application/json 则解析为 JSON
    if (contentType.includes("application/json")) {
        return await resp.json();
    }
    // 否则作为纯文本返回
    return await resp.text();
}
