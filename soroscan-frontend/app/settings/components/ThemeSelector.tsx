"use client";

import { useTheme } from "@/context/ThemeContext";

export default function ThemeSelector() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="border border-green-500/30 rounded p-4 mb-4">
      <h2 className="text-green-400 font-mono text-sm mb-3">[ THEME ]</h2>
      <div className="flex gap-3">
        {(["dark", "light"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTheme(t)}
            className={`px-4 py-2 font-mono text-sm border rounded transition-colors ${
              theme === t
                ? "border-green-400 bg-green-400/10 text-green-400"
                : "border-green-500/30 text-green-600 hover:border-green-400"
            }`}
          >
            {t === "dark" ? "◆ DARK" : "◇ LIGHT"}
          </button>
        ))}
      </div>
    </div>
  );
}
