"use client";
import Image from "next/image";
import { useEffect, useMemo, useState, type FC } from "react";
import { modelService, type BackendModelItem, NotFoundError, ValidationError } from "@/lib/modelService";
import anthropic from "../../assets/providers/anthropic.svg";
import fireworks from "../../assets/providers/fireworks.svg";
import google from "../../assets/providers/google.svg";
import deepseek from "../../assets/providers/deepseek.svg";
import meta from "../../assets/providers/meta.svg";
import mistral from "../../assets/providers/mistral.svg";
import openai from "../../assets/providers/openai.svg";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Separator } from "../ui/separator";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { PlusIcon, Trash2Icon } from "lucide-react";

// 作为后备选项（当后端不可用或返回空时使用）
const FALLBACK_MODELS = [
  // {
  //   name: "GPT 4o-mini",
  //   value: "gpt-4o-mini",
  //   icon: openai,
  // },
  {
    name: "Deepseek R1",
    value: "deepseek-r1",
    icon: deepseek,
  },
  {
    name: "Claude 3.5 Sonnet",
    value: "claude-3.5-sonnet",
    icon: anthropic,
  },
  {
    name: "Gemini 2.0 Flash",
    value: "gemini-2.0-flash",
    icon: google,
  },
  {
    name: "Llama 3 8b",
    value: "llama-3-8b",
    icon: meta,
  },
  {
    name: "Firefunction V2",
    value: "firefunction-v2",
    icon: fireworks,
  },
  {
    name: "Mistral 7b",
    value: "mistral-7b",
    icon: mistral,
  },
];
export const ModelPicker: FC = () => {
  const [options, setOptions] = useState<Array<{ name: string; value: string; icon: any }>>(FALLBACK_MODELS);
  const defaultValue = useMemo(() => options[0]?.value ?? "", [options]);
  const [inner, setInner] = useState<string>(defaultValue);
  const [loading, setLoading] = useState<boolean>(false);
  const val = inner;
  const ADD_VALUE = "__add__";

  // Add-model dialog state
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    model_name: "",
    model: "",
    base_url: "",
    api_key: "",
    model_description: "",
    model_avatar_url: "",
  });

  // 简单的 provider/icon 映射与回退逻辑
  const pickIcon = (provider?: string, modelName?: string) => {
    const key = (provider || modelName || "").toLowerCase();
    if (key.includes("openai") || key.includes("gpt")) return openai;
    if (key.includes("deepseek")) return deepseek;
    if (key.includes("claude") || key.includes("anthropic")) return anthropic;
    if (key.includes("gemini") || key.includes("google")) return google;
    if (key.includes("llama") || key.includes("meta")) return meta;
    if (key.includes("mistral")) return mistral;
    if (key.includes("firefunction") || key.includes("fireworks")) return fireworks;
    return openai;
  };

  // 初始化模型列表：尝试从后端加载模型列表，并基于 localStorage 选择默认项
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await modelService.list();
        const arr: BackendModelItem[] = Array.isArray(data.models) ? data.models : [];
        if (arr.length > 0) {
          const mapped = arr.map((it) => {
            // 现在选择值使用 id，切换时用 GET /api/models/{id}
            const value = String(it.id);
            const name = it.model_name || it.model || value;
            // 若后端未来提供 provider 字段可替换；当前用模型名推断
            return { name, value, icon: pickIcon(undefined, it.model) };
          });
          if (!cancelled) setOptions(mapped);
          // 决定初始选中：优先 localStorage，其次列表首项
          if (!cancelled) {
            const saved = typeof window !== "undefined" ? window.localStorage.getItem("SELECTED_MODEL_ID") : null;
            const initial = saved && mapped.find(m => m.value === saved) ? saved : (mapped[0]?.value ?? "");
            setInner(initial);
          }
        } else {
          // 后端返回空，保留后备选项，并基于 localStorage 初始化
          const saved = typeof window !== "undefined" ? window.localStorage.getItem("SELECTED_MODEL_ID") : null;
          const initial = saved && FALLBACK_MODELS.find(m => m.value === saved) ? saved : (FALLBACK_MODELS[0]?.value ?? "");
          setInner(initial);
        }
      } catch (_) {
        // 失败则使用后备选项，并尝试使用本地已保存值
        const saved = typeof window !== "undefined" ? window.localStorage.getItem("SELECTED_MODEL_ID") : null;
        const initial = saved && FALLBACK_MODELS.find(m => m.value === saved) ? saved : (FALLBACK_MODELS[0]?.value ?? "");
        setInner(initial);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
    // 首次加载
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 
  // 下拉框展开时，实时从后端刷新列表（以便展示刚创建的模型等最新数据）
  const handleSelectOpenChange = async (isOpen: boolean) => {
    if (!isOpen) return;
    setLoading(true);
    try {
      const data = await modelService.list();
      const arr: BackendModelItem[] = Array.isArray(data.models) ? data.models : [];
      if (arr.length > 0) {
        const mapped = arr.map((it) => {
          const value = String(it.id);
          const name = it.model_name || it.model || value;
          return { name, value, icon: pickIcon(undefined, it.model) };
        });
        setOptions(mapped);
        // 保持原有选择；若当前选择已不在新列表中，则回退为第一项
        setInner((prev) => (mapped.find((m) => m.value === prev) ? prev : (mapped[0]?.value ?? prev)));
      }
    } catch (_) {
      // 忽略错误，保留现有选项
    } finally {
      setLoading(false);
    }
  };

  // 选择模型：调用 GET /api/models/{id} 验证可用性，成功则持久化选择
  const handleChange = async (v: string) => {
    // 先本地展示选择，但在失败时回滚
    const prev = val;
    if (v === ADD_VALUE) {
      // 打开创建弹窗，不改变当前选中
      setOpen(true);
      return;
    }
    setInner(v);
    setLoading(true);
    try {
      // 按 ID 调用 GET /api/models/{connection_id}，即为切换模型
      await modelService.get(v);
      // 持久化选择（供下次初始化时读取），保存 ID
      if (typeof window !== "undefined") {
        try { window.localStorage.setItem("SELECTED_MODEL_ID", v); } catch { }
      }
    } catch (e) {
      console.error(e);
      // 回滚显示
      setInner(prev);
    } finally {
      setLoading(false);
    }
  };

  // 删除模型
  const handleDelete = async (e: React.MouseEvent, id: string) => {
    // 阻止触发 SelectItem 的选择行为
    e.preventDefault();
    e.stopPropagation();
    if (deletingId) return;
    // 简单确认，可替换为自定义对话框
    const ok = typeof window !== "undefined" ? window.confirm("确认删除该模型连接？") : true;
    if (!ok) return;
    try {
      setDeletingId(id);
      await modelService.remove(id);
      // 删除后刷新列表
      setLoading(true);
      try {
        const data = await modelService.list();
        const arr: BackendModelItem[] = Array.isArray(data.models) ? data.models : [];
        if (arr.length > 0) {
          const mapped = arr.map((it) => ({ name: it.model_name || it.model || String(it.id), value: String(it.id), icon: pickIcon(undefined, it.model) }));
          setOptions(mapped);
          setInner((prev) => (mapped.find((m) => m.value === prev) ? prev : (mapped[0]?.value ?? "")));
        } else {
          setOptions(FALLBACK_MODELS);
          setInner(FALLBACK_MODELS[0]?.value ?? "");
        }
      } finally {
        setLoading(false);
      }
    } catch (err) {
      console.error(err);
      if (err instanceof NotFoundError) {
        if (typeof window !== "undefined") window.alert("删除失败：记录不存在（可能已被删除）。");
      } else if (err instanceof ValidationError) {
        if (typeof window !== "undefined") window.alert("删除失败：参数错误，请检查 connection_id。");
      } else if (err instanceof Error) {
        if (typeof window !== "undefined") window.alert(`删除失败：${err.message}`);
      }
    } finally {
      setDeletingId(null);
    }
  };

  // 创建模型
  const submitCreate = async () => {
    if (!form.model?.trim()) {
      // 至少需要模型标识
      return;
    }
    setCreating(true);
    try {
      const created = await modelService.create({
        model_name: form.model_name || form.model,
        model: form.model,
        base_url: form.base_url,
        api_key: form.api_key,
        model_description: form.model_description,
        model_avatar_url: form.model_avatar_url,
      });
      // 仅打印日志，不在前端静态追加或选择，列表将于下次展开下拉时自动刷新
      console.log("Model created:", created);
      setOpen(false);
      setForm({ model_name: "", model: "", base_url: "", api_key: "", model_description: "", model_avatar_url: "" });
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
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((model) => (
            <SelectItem key={model.value} value={model.value}>
              <div className="flex w-full items-center justify-between">
                <span className="flex items-center gap-2">
                  <Image src={model.icon} alt={model.name} className="inline size-4" />
                  <span>{model.name}</span>
                </span>
                <span className="flex items-center gap-2 pl-2">
                  <button
                    title="删除"
                    className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={(e) => handleDelete(e, model.value)}
                    disabled={deletingId === model.value || loading}
                  >
                    <Trash2Icon className="size-4" />
                  </button>
                </span>
              </div>
            </SelectItem>
          ))}
          <Separator className="my-1" />
          <SelectItem value={ADD_VALUE} disabled={loading}>
            <span className="flex items-center gap-2 text-muted-foreground">
              <PlusIcon className="size-4" />
              <span>添加自定义模型…</span>
            </span>
          </SelectItem>
        </SelectContent>
      </Select>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加自定义模型</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 py-2">
            <div className="grid gap-1">
              <label className="text-sm text-muted-foreground">显示名称（可选）</label>
              <Input value={form.model_name} onChange={(e) => setForm((f) => ({ ...f, model_name: e.target.value }))} placeholder="例如：GPT-4o mini (内部)" />
            </div>
            <div className="grid gap-1">
              <label className="text-sm text-muted-foreground">模型标识（必填）</label>
              <Input value={form.model} onChange={(e) => setForm((f) => ({ ...f, model: e.target.value }))} placeholder="例如：gpt-4o-mini" />
            </div>
            <div className="grid gap-1">
              <label className="text-sm text-muted-foreground">Base URL（可选）</label>
              <Input value={form.base_url} onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))} placeholder="例如：https://api.openai.com/v1" />
            </div>
            <div className="grid gap-1">
              <label className="text-sm text-muted-foreground">API密匙（可选）</label>
              <Input value={form.api_key} onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))} placeholder="例如：sk-..." />
            </div>
            <div className="grid gap-1">
              <label className="text-sm text-muted-foreground">描述（可选）</label>
              <Input value={form.model_description} onChange={(e) => setForm((f) => ({ ...f, model_description: e.target.value }))} placeholder="简短说明" />
            </div>
            <div className="grid gap-1">
              <label className="text-sm text-muted-foreground">头像 URL（可选）</label>
              <Input value={form.model_avatar_url} onChange={(e) => setForm((f) => ({ ...f, model_avatar_url: e.target.value }))} placeholder="https://.../avatar.png" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={creating}>取消</Button>
            <Button onClick={submitCreate} disabled={creating || !form.model.trim()}>{creating ? "创建中..." : "创建"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};