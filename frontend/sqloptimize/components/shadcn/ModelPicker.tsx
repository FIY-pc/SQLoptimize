"use client";
import Image from "next/image";
import { useMemo, useState, type FC } from "react";
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

const models = [
  {
    name: "GPT 4o-mini",
    value: "gpt-4o-mini",
    icon: openai,
  },
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
export type ModelPickerProps = {
  value?: string;
  onChange?: (value: string) => void;
};

export const ModelPicker: FC<ModelPickerProps> = ({ value, onChange }) => {
  const defaultValue = useMemo(() => models[0]?.value ?? "", []);
  const [inner, setInner] = useState<string>(value ?? defaultValue);
  const val = value ?? inner;

  const handleChange = (v: string) => {
    if (onChange) onChange(v);
    else setInner(v);
  };

  return (
    <Select value={val} onValueChange={handleChange}>
      <SelectTrigger className="max-w-[300px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {models.map((model) => (
          <SelectItem key={model.value} value={model.value}>
            <span className="flex items-center gap-2">
              <Image
                src={model.icon}
                alt={model.name}
                className="inline size-4"
              />
              <span>{model.name}</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
};
