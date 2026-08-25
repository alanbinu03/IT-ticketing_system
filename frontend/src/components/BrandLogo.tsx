import { Link } from "../lib/nav";
import { ThemeSwitcher } from "./ThemeSwitcher";

const LOGO_SRC = "/brand/hirect-logo.png";
const LOGO_ALT = "Hirect";

type BrandLogoProps = {
  size?: "header" | "sidebar" | "auth";
  to?: string;
};

export function BrandLogo({ size = "header", to }: BrandLogoProps) {
  const image = (
    <span
      className={`brand-logo inline-flex items-center justify-center rounded-xl bg-white ${
        size === "auth" ? "h-16 px-4" : size === "sidebar" ? "h-10 px-3" : "h-8 px-2"
      }`}
    >
      <img
        src={LOGO_SRC}
        alt={LOGO_ALT}
        className={
          size === "auth"
            ? "h-10 w-auto object-contain"
            : size === "sidebar"
              ? "h-6 w-auto object-contain"
              : "h-5 w-auto object-contain"
        }
      />
    </span>
  );
  if (!to) return image;
  return (
    <Link to={to} className="shrink-0" aria-label={LOGO_ALT}>
      {image}
    </Link>
  );
}

export function AuthTopBar() {
  return (
    <div className="absolute right-4 top-4 z-10 sm:right-6 sm:top-6">
      <ThemeSwitcher />
    </div>
  );
}
