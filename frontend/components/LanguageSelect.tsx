"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const LANGUAGES = [
  { id: "EN", label: "English" },
  { id: "VI", label: "Tiếng Việt" },
] as const;

export default function LanguageSelect() {
  const [lang, setLang] = useState<(typeof LANGUAGES)[number]["id"]>("EN");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-gray-400 hover:bg-gray-700 hover:text-gray-200"
        >
          {lang}
          <ChevronDown className="size-4" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {LANGUAGES.map((item) => (
          <DropdownMenuItem key={item.id} onClick={() => setLang(item.id)}>
            {item.id} · {item.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
