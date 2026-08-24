import { PALETTES, useTheme } from "../lib/theme";

export function ThemeSwitcher() {
  const { mode, palette, setPalette, toggleNight } = useTheme();

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1" title="Day color palette">
        {PALETTES.map((item) => (
          <button
            key={item.id}
            type="button"
            aria-label={`${item.label} palette`}
            title={item.label}
            onClick={() => setPalette(item.id)}
            className={`h-5 w-5 rounded-full border-2 transition hover:scale-110 ${
              palette === item.id ? "scale-110 border-white shadow" : "border-transparent opacity-80 hover:opacity-100"
            }`}
            style={{ background: item.swatch }}
          />
        ))}
      </div>
      <button
        type="button"
        onClick={toggleNight}
        className="icon-btn"
      >
        {mode === "night" ? "Day mode" : "Night mode"}
      </button>
    </div>
  );
}
