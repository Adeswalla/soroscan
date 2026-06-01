"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import { cn } from "@/lib/utils";

export interface ThemeToggleProps {
  className?: string;
  /** Accessible label override */
  label?: string;
}

/**
 * Compact dark/light toggle. Persists via ThemeProvider + localStorage.
 */
export function ThemeToggle({ className, label }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={cn(
        "inline-flex items-center justify-center rounded border border-terminal-green/30 p-2 text-terminal-gray transition-colors hover:border-terminal-green hover:text-terminal-green focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-terminal-green",
        className
      )}
      aria-label={label ?? (isDark ? "Switch to light mode" : "Switch to dark mode")}
      aria-pressed={isDark}
    >
      {isDark ? <Sun className="h-4 w-4" aria-hidden /> : <Moon className="h-4 w-4" aria-hidden />}
    </button>
  );
}
