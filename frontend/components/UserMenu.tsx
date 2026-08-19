"use client";

import { LogOut } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import NavItems from "@/components/NavItems";
import { MOCK_USER } from "@/lib/mock-data";

export default function UserMenu({ onSearch }: { onSearch?: () => void }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="flex items-center gap-3 bg-transparent text-gray-400 hover:bg-gray-700">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-teal-500 text-sm font-bold text-teal-950">
              {MOCK_USER.name.slice(0, 1).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <span className="hidden text-base font-medium md:inline">{MOCK_USER.name}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex items-center gap-3 py-1">
            <Avatar className="h-10 w-10">
              <AvatarFallback className="bg-teal-500 font-bold text-teal-950">
                {MOCK_USER.name.slice(0, 1).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-gray-200">{MOCK_USER.name}</span>
              <span className="text-xs text-gray-500">{MOCK_USER.email}</span>
            </div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem>
          <LogOut className="size-4" />
          Logout
        </DropdownMenuItem>
        <div className="sm:hidden">
          <DropdownMenuSeparator />
          <NavItems onSearch={onSearch} />
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
