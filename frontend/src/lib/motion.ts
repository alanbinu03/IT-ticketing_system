export function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function canViewTransition() {
  return typeof document !== "undefined" && "startViewTransition" in document && !prefersReducedMotion();
}

export function setThemeOrigin(x: number, y: number) {
  const root = document.documentElement;
  root.style.setProperty("--theme-x", `${Math.round(x)}px`);
  root.style.setProperty("--theme-y", `${Math.round(y)}px`);
}

export function setThemeOriginFromEvent(event: { currentTarget: EventTarget }) {
  const node = event.currentTarget as HTMLElement | null;
  if (!node?.getBoundingClientRect) return;
  const rect = node.getBoundingClientRect();
  setThemeOrigin(rect.left + rect.width / 2, rect.top + rect.height / 2);
}
