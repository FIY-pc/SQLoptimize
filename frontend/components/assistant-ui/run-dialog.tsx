"use client";

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { type RunResult, stringifySafe } from "./sqlrunner";

export type RunDialogProps = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    language?: string;
    running: boolean;
    result: RunResult | null;
};

export function RunDialog({ open, onOpenChange, language, running, result }: RunDialogProps) {
    const rows = result?.rows ?? [];
    const columns = rows.length > 0 ? Object.keys(rows[0]!) : [];
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-4xl">
                <DialogHeader>
                    <DialogTitle>运行结果</DialogTitle>
                    <DialogDescription>
                        {language ? `语言：${language}` : "SQL"}
                    </DialogDescription>
                </DialogHeader>
                <div className="max-h-[70vh] overflow-auto space-y-4">
                    {running && <div className="text-sm text-muted-foreground">运行中...</div>}
                    {!running && result && (
                        <div className="space-y-3">
                            {result.errorText && (
                                <div>
                                    <div className="mb-1 text-xs font-semibold text-red-500">error</div>
                                    <pre className="rounded-md bg-red-50 p-3 text-sm text-red-600 whitespace-pre-wrap break-words">
                                        {result.errorText}
                                    </pre>
                                </div>
                            )}

                            {rows.length > 0 && (
                                <div className="rounded-md border">
                                    <div className="px-3 py-2 text-xs text-muted-foreground">共 {rows.length} 行</div>
                                    <div className="overflow-auto">
                                        <table className="w-full text-sm">
                                            <thead className="sticky top-0 bg-muted">
                                                <tr>
                                                    {columns.map((col) => (
                                                        <th key={col} className="px-3 py-2 text-left font-semibold border-b">
                                                            {col}
                                                        </th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {rows.map((r, i) => (
                                                    <tr key={i} className="border-b last:border-0">
                                                        {columns.map((col) => (
                                                            <td key={col} className="px-3 py-2 align-top">
                                                                {formatCell(r[col])}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {!result.errorText && rows.length === 0 && (
                                <div className="text-sm text-muted-foreground">无结果</div>
                            )}

                            {process.env.NODE_ENV !== "production" && !!result?.raw && (
                                <details className="rounded-md border p-3">
                                    <summary className="cursor-pointer text-xs text-muted-foreground">原始响应(raw)</summary>
                                    <pre className="mt-2 text-xs whitespace-pre-wrap break-words">{stringifySafe(result.raw)}</pre>
                                </details>
                            )}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}

function formatCell(v: unknown): string {
    if (v == null) return "";
    if (typeof v === "object") return stringifySafe(v);
    return String(v);
}
