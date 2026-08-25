import { useEffect, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { setThemeOriginFromEvent } from "../lib/motion";
import { PALETTES, useTheme } from "../lib/theme";

function popoverStyle(button: HTMLButtonElement | null): CSSProperties {
  const rect = button?.getBoundingClientRect();
  if (!rect) return { position: "fixed", top: 0, left: 0, visibility: "hidden" };
  return {
    position: "fixed",
    top: rect.bottom + 8,
    left: Math.max(12, rect.right - 168),
  };
}

export function ThemeSwitcher() {
  const { mode, palette, setPalette, toggleNight } = useTheme();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const popRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [popStyle, setPopStyle] = useState<CSSProperties>({});
  const current = PALETTES.find((item) => item.id === palette) ?? PALETTES[0];

  useEffect(() => {
    if (!open) return;
    const place = () => setPopStyle(popoverStyle(buttonRef.current));
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      const path = event.composedPath();
      if (
        (rootRef.current && path.includes(rootRef.current)) ||
        (popRef.current && path.includes(popRef.current))
      ) {
        return;
      }
      setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [open]);

  return (
    <div className="relative flex h-10 items-center gap-1" ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className="icon-btn"
        aria-label={`${current.label} palette`}
        title="Color palette"
        aria-expanded={open}
        onClick={() => {
          setPopStyle(popoverStyle(buttonRef.current));
          setOpen((value) => !value);
        }}
      >
        <span className="swatch" style={{ backgroundImage: current.swatch }} />
      </button>
      {open &&
        createPortal(
          <div
            ref={popRef}
            className="theme-pop z-[80] flex items-center gap-2 rounded-2xl border border-edge bg-surface p-2 shadow-xl"
            style={popStyle}
            onPointerDown={(event) => event.stopPropagation()}
          >
            {PALETTES.map((item) => {
              const selected = palette === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  aria-label={`${item.label} palette`}
                  title={item.label}
                  onPointerDown={(event) => {
                    event.stopPropagation();
                    setPalette(item.id);
                    setOpen(false);
                  }}
                  className={`swatch ${selected ? "is-selected" : "opacity-80 hover:opacity-100"}`}
                  style={{ backgroundImage: item.swatch }}
                />
              );
            })}
          </div>,
          document.body,
        )}
      <button
        type="button"
        onClick={(event) => {
          setThemeOriginFromEvent(event);
          toggleNight();
        }}
        className="icon-btn"
        aria-label={mode === "night" ? "Switch to day" : "Switch to night"}
        title={mode === "night" ? "Day" : "Night"}
      >
        <span className="theme-glyph" key={mode}>
          {mode === "night" ? <SunIcon /> : <MoonIcon />}
        </span>
      </button>
    </div>
  );
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M12 3v2.2M12 18.8V21M4.93 4.93l1.56 1.56M17.51 17.51l1.56 1.56M3 12h2.2M18.8 12H21M4.93 19.07l1.56-1.56M17.51 6.49l1.56-1.56"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M16.5 13.2A6.5 6.5 0 1 0 16.5 13.2Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}
