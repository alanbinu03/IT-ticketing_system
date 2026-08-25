import path from "node:path";
import { fileURLToPath } from "node:url";

import dotenv from "dotenv";

import { createTransport, smtpConfigured } from "./smtp.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
dotenv.config({ path: path.join(root, ".env") });

if (!smtpConfigured()) {
  console.error("SMTP_HOST is empty. Set it in .env before verifying.");
  process.exit(1);
}

const transporter = createTransport();
try {
  await transporter.verify();
  console.log("SMTP connection OK", {
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT || 587),
    user: process.env.SMTP_USERNAME,
  });
} catch (err) {
  console.error("SMTP connection failed:", err?.message || err);
  process.exit(1);
}
