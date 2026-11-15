"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart2, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "./ThemeToggle";

const links = [
  { href: "/runs", label: "Runs", icon: BarChart2 },
  { href: "/analytics", label: "Analytics", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex h-screen w-60 flex-shrink-0 flex-col border-r border-border bg-card px-3 py-4">
      <div className="mb-6 px-2">
        <span className="text-sm font-semibold tracking-tight text-foreground">
          MCP Trace Studio
        </span>
      </div>

      <ul className="flex flex-1 flex-col gap-1">
        {links.map(({ href, label, icon: Icon }) => (
          <li key={href}>
            <Link
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                pathname === href || pathname.startsWith(href + "/")
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          </li>
        ))}
      </ul>

      <div className="flex justify-center pt-2 border-t border-border">
        <ThemeToggle />
      </div>
    </nav>
  );
}
