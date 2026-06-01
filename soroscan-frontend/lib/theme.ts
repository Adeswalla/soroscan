export type Theme = "dark" | "light";

export const THEME_STORAGE_KEY = "theme";
export const DEFAULT_THEME: Theme = "dark";

export function isTheme(value: string | null): value is Theme {
  return value === "dark" || value === "light";
}

/** Read persisted theme from localStorage (client only). */
export function getStoredTheme(): Theme {
  if (typeof window === "undefined") {
    return DEFAULT_THEME;
  }

  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    return isTheme(stored) ? stored : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

/** Apply theme class on `<html>` for Tailwind dark mode. */
export function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") {
    return;
  }
  document.documentElement.classList.toggle("dark", theme === "dark");
}

/** Persist theme to localStorage. */
export function persistTheme(theme: Theme): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Private browsing or quota exceeded — preference still applies for session
  }
}

/**
 * Inline script run before paint so the saved theme applies on first load
 * without a flash of the wrong mode.
 */
export const themeInitScript = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");document.documentElement.classList.toggle("dark",t!=="light");}catch(e){document.documentElement.classList.add("dark");}})();`;
