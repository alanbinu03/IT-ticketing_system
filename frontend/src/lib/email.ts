import { z } from "zod";

export function normalizeEmailInput(raw: string): string {
  let value = (raw || "").trim();
  if (value.toLowerCase().startsWith("mailto:")) {
    value = value.slice(7).trim();
  }
  const open = value.indexOf("<");
  const close = value.lastIndexOf(">");
  if (open >= 0 && close > open) {
    value = value.slice(open + 1, close).trim();
  }
  return value.replace(/\u00a0/g, " ").replace(/\s+/g, "").replace(/^['"]+|['"]+$/g, "");
}

export const accountEmailSchema = z
  .string()
  .transform(normalizeEmailInput)
  .refine((value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value), {
    message: "Enter a valid email like name@company.com",
  });
