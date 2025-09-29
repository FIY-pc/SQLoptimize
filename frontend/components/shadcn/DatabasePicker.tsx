"use client";

import { useEffect, useMemo, useState, type FC } from "react";
import { databaseService, type BackendDatabaseItem } from "@/lib/databaseService";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";

// 简单的占位/后备
const FALLBACK_DBS = [
    { name: "默认数据库", value: "default" },
];

export const DatabasePicker: FC = () => {
    const [options, setOptions] = useState<Array<{ name: string; value: string }>>(
        FALLBACK_DBS,
    );
    const defaultValue = useMemo(() => options[0]?.value ?? "", [options]);
    const [inner, setInner] = useState<string>(defaultValue);
    const [loading, setLoading] = useState<boolean>(false);
    const val = inner;

    useEffect(() => {
        let cancelled = false;
        (async () => {
            setLoading(true);
            try {
                const data = await databaseService.list();
                const arr: BackendDatabaseItem[] = Array.isArray(data.databases) ? data.databases : [];
                if (arr.length > 0) {
                    const mapped = arr.map((it) => ({
                        value: String(it.id),
                        name: (it as any).database_name || (it as any).database || (it as any).name || (it as any).db_name || String(it.id),
                    }));
                    if (!cancelled) setOptions(mapped);
                    if (!cancelled) {
                        const saved = typeof window !== "undefined" ? window.localStorage.getItem("SELECTED_DB_ID") : null;
                        const initial = saved && mapped.find((m) => m.value === saved) ? saved : mapped[0]?.value ?? "";
                        setInner(initial);
                    }
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);

    const handleOpenChange = async (isOpen: boolean) => {
        if (!isOpen) return;
        setLoading(true);
        try {
            const data = await databaseService.list();
            const arr: BackendDatabaseItem[] = Array.isArray(data.databases) ? data.databases : [];
            if (arr.length > 0) {
                const mapped = arr.map((it) => ({ value: String(it.id), name: (it as any).database_name || (it as any).database || (it as any).name || (it as any).db_name || String(it.id) }));
                setOptions(mapped);
                setInner((prev) => (mapped.find((m) => m.value === prev) ? prev : mapped[0]?.value ?? prev));
            }
        } finally {
            setLoading(false);
        }
    };

    const handleChange = async (v: string) => {
        const prev = val;
        setInner(v);
        setLoading(true);
        try {
            await databaseService.get(v); // 触发后端切换/校验
            if (typeof window !== "undefined") {
                try {
                    window.localStorage.setItem("SELECTED_DB_ID", v);
                } catch { }
            }
        } catch (e) {
            console.error(e);
            setInner(prev);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Select value={val} onValueChange={handleChange} disabled={loading} onOpenChange={handleOpenChange}>
            <SelectTrigger className="max-w-[240px]" aria-busy={loading}>
                <SelectValue placeholder="选择数据库" />
            </SelectTrigger>
            <SelectContent>
                {options.map((db) => (
                    <SelectItem key={db.value} value={db.value}>
                        <span className="flex items-center gap-2">
                            <span>{db.name}</span>
                        </span>
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
};
