import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import dotenv from "dotenv";

import { createTransport, smtpConfigured, smtpFromAddress } from "./smtp.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
dotenv.config({ path: path.join(root, ".env") });

const port = Number(process.env.MAILER_PORT || 3010);
const token = (process.env.MAILER_TOKEN || "").trim();
const emailEnabled = String(process.env.EMAIL_ENABLED || "false").toLowerCase() === "true";
const transporter = emailEnabled ? createTransport() : null;

function json(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function unauthorized(req) {
  if (!token) {
    return false;
  }
  return (req.headers.authorization || "") !== `Bearer ${token}`;
}

async function readJson(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
    if (Buffer.concat(chunks).length > 1024 * 1024) {
      throw new Error("payload too large");
    }
  }
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  if (!raw) {
    return {};
  }
  return JSON.parse(raw);
}

async function handleSend(req, res) {
  if (unauthorized(req)) {
    json(res, 401, { error: "unauthorized" });
    return;
  }
  if (!emailEnabled) {
    json(res, 200, { ok: true, skipped: true, reason: "email_disabled" });
    return;
  }
  if (!transporter) {
    json(res, 503, { error: "smtp_not_configured" });
    return;
  }
  let payload;
  try {
    payload = await readJson(req);
  } catch {
    json(res, 400, { error: "invalid_json" });
    return;
  }
  const to = String(payload.to || "").trim();
  const subject = String(payload.subject || "").trim();
  const text = String(payload.text || payload.body || "");
  const html = payload.html ? String(payload.html) : undefined;
  if (!to || !subject) {
    json(res, 400, { error: "to_and_subject_required" });
    return;
  }
  try {
    const info = await transporter.sendMail({
      from: smtpFromAddress(),
      to,
      subject,
      text,
      html,
    });
    json(res, 200, { ok: true, messageId: info.messageId || null });
  } catch (err) {
    console.error("smtp_send_failed", err?.message || err);
    json(res, 502, { error: "smtp_send_failed", detail: String(err?.message || err) });
  }
}

async function handleVerify(req, res) {
  if (unauthorized(req)) {
    json(res, 401, { error: "unauthorized" });
    return;
  }
  if (!emailEnabled) {
    json(res, 200, { ok: true, skipped: true, reason: "email_disabled" });
    return;
  }
  if (!transporter) {
    json(res, 503, { ok: false, error: "smtp_not_configured" });
    return;
  }
  try {
    await transporter.verify();
    json(res, 200, { ok: true, host: process.env.SMTP_HOST, port: Number(process.env.SMTP_PORT || 587) });
  } catch (err) {
    json(res, 502, { ok: false, error: "smtp_verify_failed", detail: String(err?.message || err) });
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  if (req.method === "GET" && (url.pathname === "/health" || url.pathname === "/ready")) {
    json(res, 200, { ok: true, smtpConfigured: smtpConfigured(), emailEnabled });
    return;
  }
  if (req.method === "POST" && url.pathname === "/send") {
    handleSend(req, res);
    return;
  }
  if ((req.method === "GET" || req.method === "POST") && url.pathname === "/verify") {
    handleVerify(req, res);
    return;
  }
  json(res, 404, { error: "not_found" });
});

server.listen(port, "0.0.0.0", () => {
  console.log(
    JSON.stringify({
      event: "mailer_started",
      port,
      smtpConfigured: smtpConfigured(),
      emailEnabled,
      host: process.env.SMTP_HOST || "",
    }),
  );
});
