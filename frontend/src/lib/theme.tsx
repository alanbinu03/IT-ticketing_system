import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export const PALETTES = [
  { id: "ocean", label: "Ocean", swatch: "#0284c7" },
  { id: "forest", label: "Forest", swatch: "#059669" },
  { id: "sunset", label: "Sunset", swatch: "#ea580c" },
  { id: "violet", label: "Violet", swatch: "#7c3aed" },
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
    applyTheme(mode, palette);
    localStorage.setItem(MODE_KEY, mode);
    localStorage.setItem(PALETTE_KEY, palette);
  }, [mode, palette]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      mode,
      palette,
      setMode: setModeState,
      setPalette: setPaletteState,
      toggleNight: () => setModeState((current) => (current === "night" ? "day" : "night")),
    }),
    [mode, palette],
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
