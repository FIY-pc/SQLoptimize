"use client";

import { useEffect, useState, type FC } from "react";
import { schemaService, type SchemaOption } from "@/lib/schemaService";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Separator } from "../ui/separator";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { PlusIcon, Trash2Icon } from "lucide-react";
import { NotFoundError, ValidationError } from "@/lib/modelService";

export const SchemaPicker: FC = () => {
    const [options, setOptions] = useState<Array<{ name: string; value: string }>>([]);
    const [val, setVal] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);
    const ADD_VALUE = "__add__";
    const [menuOpen, setMenuOpen] = useState(false);

    const [open, setOpen] = useState(false);
    const [creating, setCreating] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [form, setForm] = useState({
        schema_name: "",
        schema_content: "",
    });

    useEffect(() => {
        const syncFromService = () => {
            const opts: SchemaOption[] = schemaService.getOptions();
            setOptions(opts.map((o) => ({ name: o.name, value: o.value })));
            setVal(schemaService.getSelectedId() ?? "");
        };
        const unsub = schemaService.subscribe(syncFromService);
        (async () => {
            setLoading(true);
            try {
                await schemaService.init();
                syncFromService();
            } finally {
                setLoading(false);
            }
        })();
        return () => {
            unsub();
        };
    }, []);

    const handleSelectOpenChange = async (isOpen: boolean) => {
        setMenuOpen(isOpen);
        if (!isOpen) return;
        setLoading(true);
        try {
            await schemaService.refresh();
        } finally {
            setLoading(false);
        }
    };

    const handleChange = async (v: string) => {
        if (v === ADD_VALUE) {
            setOpen(true);
            return;
        }
        const prev = val;
        setVal(v);
        setLoading(true);
        try {
            await schemaService.select(v);
        } catch (e) {
            console.error(e);
            setVal(prev);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (e: React.MouseEvent, id: string) => {
        e.preventDefault();
        e.stopPropagation();
        if (deletingId) return;
        const ok = typeof window !== "undefined" ? window.confirm("确认删除该 Schema？") : true;
        if (!ok) return;
        try {
            setDeletingId(id);
            await schemaService.remove(id);
        } catch (err) {
            console.error(err);
            if (err instanceof NotFoundError) {
                if (typeof window !== "undefined") window.alert("删除失败：记录不存在（可能已被删除）。");
            } else if (err instanceof ValidationError) {
                if (typeof window !== "undefined") window.alert("删除失败：参数错误，请检查 schema_id。");
            } else if (err instanceof Error) {
                if (typeof window !== "undefined") window.alert(`删除失败：${err.message}`);
            }
        } finally {
            setDeletingId(null);
        }
    };

    const submitCreate = async () => {
        if (!form.schema_content?.trim()) {
            return; // schema_content 为必填
        }
        setCreating(true);
        try {
            const created = await schemaService.create({
                schema_name: form.schema_name || undefined,
                schema_content: form.schema_content,
            } as any);
            console.log("Schema created:", created);
            setOpen(false);
            setForm({ schema_name: "", schema_content: "" });
        } catch (err) {
            console.error(err);
        } finally {
            setCreating(false);
        }
    };

    return (
        <>
            <Select value={val} onValueChange={handleChange} disabled={loading} onOpenChange={handleSelectOpenChange}>
                <SelectTrigger className="max-w-[300px]" aria-busy={loading}>
                    <SelectValue placeholder="选择 Schema" />
                </SelectTrigger>
                <SelectContent>
                    {options.map((s) => (
                        <SelectItem key={s.value} value={s.value}>
                            {menuOpen ? (
                                <span className="flex w-full items-center justify-between">
                                    <span className="flex items-center gap-2">
                                        <span>{s.name}</span>
                                    </span>
                                    <span className="flex items-center gap-2 pl-2">
                                        <button
                                            title="删除"
                                            className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                                            onMouseDown={(e) => e.preventDefault()}
                                            onClick={(e) => handleDelete(e, s.value)}
                                            disabled={deletingId === s.value || loading}
                                        >
                                            <Trash2Icon className="size-4" />
                                        </button>
                                    </span>
                                </span>
                            ) : (
                                <span className="flex items-center gap-2">
                                    <span>{s.name}</span>
                                </span>
                            )}
                        </SelectItem>
                    ))}
                    <Separator className="my-1" />
                    <SelectItem value={ADD_VALUE} disabled={loading}>
                        <span className="flex items-center gap-2 text-muted-foreground">
                            <PlusIcon className="size-4" />
                            <span>添加 Schema…</span>
                        </span>
                    </SelectItem>
                </SelectContent>
            </Select>

            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>添加 Schema</DialogTitle>
                    </DialogHeader>
                    <div className="grid gap-3 py-2">
                        <div className="grid gap-1">
                            <label className="text-sm text-muted-foreground">名称（可选）</label>
                            <Input value={form.schema_name} onChange={(e) => setForm((f) => ({ ...f, schema_name: e.target.value }))} placeholder="例如：线上库 Schema" />
                        </div>
                        <div className="grid gap-1">
                            <label className="text-sm text-muted-foreground">内容（JSON 或 DDL，必填）</label>
                            <Input value={form.schema_content} onChange={(e) => setForm((f) => ({ ...f, schema_content: e.target.value }))} placeholder="粘贴 Schema 内容" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)} disabled={creating}>取消</Button>
                        <Button onClick={submitCreate} disabled={creating || !form.schema_content.trim()}>{creating ? "创建中..." : "创建"}</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
};
