import nodemailer from "nodemailer";

export function smtpConfigured() {
  return Boolean((process.env.SMTP_HOST || "").trim());
}

export function smtpFromAddress() {
  const fromEmail = (process.env.SMTP_FROM_EMAIL || "").trim();
  const fromName = (process.env.SMTP_FROM_NAME || "IT Support").trim();
  const username = (process.env.SMTP_USERNAME || "").trim();
  const email =
    !fromEmail || fromEmail.endsWith("@localhost") ? username || fromEmail : fromEmail;
  if (!email) {
    return fromName;
  }
  return fromName ? `${fromName} <${email}>` : email;
}

export function createTransport() {
  const host = (process.env.SMTP_HOST || "").trim();
  if (!host) {
    return null;
  }
  const port = Number(process.env.SMTP_PORT || 587);
  const useTls = String(process.env.SMTP_USE_TLS || "true").toLowerCase() !== "false";
  const username = (process.env.SMTP_USERNAME || "").trim();
  const password = process.env.SMTP_PASSWORD || "";

  return nodemailer.createTransport({
    host,
    port,
    secure: port === 465,
    requireTLS: useTls && port !== 465,
    auth: username ? { user: username, pass: password } : undefined,
    pool: true,
    maxConnections: 3,
    connectionTimeout: 15000,
    greetingTimeout: 15000,
    socketTimeout: 20000,
    disableFileAccess: true,
    disableUrlAccess: true,
  });
}
