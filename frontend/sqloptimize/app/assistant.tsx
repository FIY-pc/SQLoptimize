"use client";

import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { useChatRuntime, AssistantChatTransport } from "@assistant-ui/react-ai-sdk";
import { Thread } from "@/components/assistant-ui/thread";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { ThreadListSidebar } from "@/components/assistant-ui/threadlist-sidebar";
import { Separator } from "@/components/ui/separator";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Shadcn } from "@/components/shadcn/Shadcn";
import { useState } from "react";

// 将 runtime 放入子组件中，父组件用 key 绑定 model，切换模型时强制重挂载 runtime
const RuntimeRoot: React.FC<{ model: string; onModelChange: (v: string) => void }> = ({ model, onModelChange }) => {
  const runtime = useChatRuntime({
    transport: new AssistantChatTransport({
      api: `/api/chat?model=${encodeURIComponent(model)}`,
    }),
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <SidebarProvider>
        <div className="flex h-dvh w-full pr-0.5">
          <ThreadListSidebar />
          <SidebarInset>
            <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
              <SidebarTrigger />
              <Separator orientation="vertical" className="mr-2 h-4" />
              <Shadcn model={model} onModelChange={onModelChange} />
            </header>
            <div className="flex-1 overflow-hidden">
              <Thread />
            </div>
          </SidebarInset>
        </div>
      </SidebarProvider>
    </AssistantRuntimeProvider>
  );
};

export const Assistant = () => {
  const [model, setModel] = useState("gpt-4o-mini");
  // 关键点：使用 key 绑定当前 model，变化时强制 RuntimeRoot（含 runtime）重挂载
  return <RuntimeRoot key={model} model={model} onModelChange={setModel} />;
};
