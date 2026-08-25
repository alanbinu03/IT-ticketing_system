import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { flushSync } from "react-dom";
import { canViewTransition, prefersReducedMotion } from "./motion";

export const PALETTES = [
  { id: "ocean", label: "Azure", swatch: "linear-gradient(135deg, #38bdf8 0%, #0284c7 55%, #6366f1 100%)" },
  { id: "forest", label: "Jade", swatch: "linear-gradient(135deg, #5eead4 0%, #0f766e 58%, #fbbf24 100%)" },
  { id: "sunset", label: "Rose", swatch: "linear-gradient(135deg, #fb7185 0%, #e11d48 52%, #f59e0b 100%)" },
  { id: "violet", label: "Orchid", swatch: "linear-gradient(135deg, #e9d5ff 0%, #7c3aed 52%, #4f46e5 100%)" },
] as const;

export type PaletteId = (typeof PALETTES)[number]["id"];
export type ColorMode = "day" | "night";

const MODE_KEY = "its.theme.mode";
const PALETTE_KEY = "its.theme.palette";

type ThemeContextValue = {
  mode: ColorMode;
  palette: PaletteId;
  setMode: (mode: ColorMode) => void;
  setPalette: (palette: PaletteId) => void;
  toggleNight: () => void;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function isPalette(value: string | null): value is PaletteId {
  return PALETTES.some((item) => item.id === value);
}

function applyTheme(mode: ColorMode, palette: PaletteId) {
  const root = document.documentElement;
  root.dataset.mode = mode;
  root.dataset.palette = palette;
  root.style.colorScheme = mode === "night" ? "dark" : "light";
}

let themeSwitching = false;

function blendTheme(apply: () => void, durationMs: number) {
  const root = document.documentElement;
  root.style.setProperty("--duration-theme", `${durationMs}ms`);
  root.classList.add("theme-blend");
  apply();
  window.setTimeout(() => {
    root.classList.remove("theme-blend");
    root.style.removeProperty("--duration-theme");
  }, durationMs);
}

function withThemeTransition(apply: () => void, reveal = true) {
  const root = document.documentElement;
  const doc = document as Document & {
    startViewTransition?: (update: () => void) => { finished: Promise<unknown> };
  };

  if (prefersReducedMotion() || (themeSwitching && reveal)) {
    apply();
    return;
  }

  if (!reveal) {
    blendTheme(apply, 160);
    return;
  }

  if (!canViewTransition() || typeof doc.startViewTransition !== "function") {
    blendTheme(apply, 520);
    return;
  }

  themeSwitching = true;
  root.classList.add("is-theme-vt");
  try {
    const transition = doc.startViewTransition(() => {
      flushSync(() => apply());
    });
    void transition.finished.finally(() => {
      root.classList.remove("is-theme-vt");
      themeSwitching = false;
    });
  } catch {
    root.classList.remove("is-theme-vt");
    apply();
    themeSwitching = false;
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ColorMode>(() => {
    const stored = localStorage.getItem(MODE_KEY);
    return stored === "night" ? "night" : "day";
  });
  const [palette, setPaletteState] = useState<PaletteId>(() => {
    const stored = localStorage.getItem(PALETTE_KEY);
    return isPalette(stored) ? stored : "ocean";
  });

  useEffect(() => {
    localStorage.setItem(MODE_KEY, mode);
    localStorage.setItem(PALETTE_KEY, palette);
  }, [mode, palette]);

  const setMode = useCallback(
    (next: ColorMode) => {
      if (next === mode) return;
      withThemeTransition(() => {
        applyTheme(next, palette);
        setModeState(next);
      });
    },
    [mode, palette],
  );

  const setPalette = useCallback(
    (next: PaletteId) => {
      if (next === palette) return;
      withThemeTransition(() => {
        applyTheme(mode, next);
        setPaletteState(next);
      }, false);
    },
    [mode, palette],
  );

  const toggleNight = useCallback(() => {
    setMode(mode === "night" ? "day" : "night");
  }, [mode, setMode]);

  const value = useMemo<ThemeContextValue>(
    () => ({ mode, palette, setMode, setPalette, toggleNight }),
    [mode, palette, setMode, setPalette, toggleNight],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}
