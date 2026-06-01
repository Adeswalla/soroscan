import {
  applyTheme,
  DEFAULT_THEME,
  getStoredTheme,
  isTheme,
  persistTheme,
  THEME_STORAGE_KEY,
  themeInitScript,
} from "@/lib/theme";

describe("theme utilities", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  describe("isTheme", () => {
    it("accepts dark and light", () => {
      expect(isTheme("dark")).toBe(true);
      expect(isTheme("light")).toBe(true);
    });

    it("rejects invalid values", () => {
      expect(isTheme("system")).toBe(false);
      expect(isTheme(null)).toBe(false);
    });
  });

  describe("getStoredTheme", () => {
    it("returns default when nothing is stored", () => {
      expect(getStoredTheme()).toBe(DEFAULT_THEME);
    });

    it("returns stored preference", () => {
      localStorage.setItem(THEME_STORAGE_KEY, "light");
      expect(getStoredTheme()).toBe("light");
    });
  });

  describe("applyTheme", () => {
    it("adds dark class for dark theme", () => {
      applyTheme("dark");
      expect(document.documentElement.classList.contains("dark")).toBe(true);
    });

    it("removes dark class for light theme", () => {
      document.documentElement.classList.add("dark");
      applyTheme("light");
      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });
  });

  describe("persistTheme", () => {
    it("saves theme to localStorage", () => {
      persistTheme("light");
      expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    });
  });

  describe("themeInitScript", () => {
    it("reads localStorage and toggles dark class", () => {
      localStorage.setItem(THEME_STORAGE_KEY, "light");
      eval(themeInitScript);
      expect(document.documentElement.classList.contains("dark")).toBe(false);

      localStorage.setItem(THEME_STORAGE_KEY, "dark");
      eval(themeInitScript);
      expect(document.documentElement.classList.contains("dark")).toBe(true);
    });
  });
});
