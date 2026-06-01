import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider, useTheme } from "@/context/ThemeContext";
import { THEME_STORAGE_KEY } from "@/lib/theme";

function ThemeConsumer() {
  const { theme } = useTheme();
  return <span data-testid="theme-value">{theme}</span>;
}

describe("ThemeContext", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("persists theme when setTheme is called", async () => {
    const user = userEvent.setup();

    function Controls() {
      const { setTheme } = useTheme();
      return (
        <button type="button" onClick={() => setTheme("light")}>
          Use light
        </button>
      );
    }

    render(
      <ThemeProvider>
        <ThemeConsumer />
        <Controls />
      </ThemeProvider>
    );

    await user.click(screen.getByRole("button", { name: "Use light" }));

    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(screen.getByTestId("theme-value")).toHaveTextContent("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("toggleTheme switches and persists", async () => {
    const user = userEvent.setup();

    function Controls() {
      const { toggleTheme } = useTheme();
      return (
        <button type="button" onClick={toggleTheme}>
          Toggle
        </button>
      );
    }

    render(
      <ThemeProvider>
        <ThemeConsumer />
        <Controls />
      </ThemeProvider>
    );

    expect(screen.getByTestId("theme-value")).toHaveTextContent("dark");

    await user.click(screen.getByRole("button", { name: "Toggle" }));

    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(screen.getByTestId("theme-value")).toHaveTextContent("light");
  });

  it("syncs theme across tabs via storage event", () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId("theme-value")).toHaveTextContent("dark");

    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: THEME_STORAGE_KEY,
          newValue: "light",
          storageArea: localStorage,
        })
      );
    });

    expect(screen.getByTestId("theme-value")).toHaveTextContent("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("loads stored theme on mount", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "light");

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId("theme-value")).toHaveTextContent("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
