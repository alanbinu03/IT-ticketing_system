import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { OtpInput } from "../components/OtpInput";
import { api, getErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";

const emailSchema = z.object({
  email: z.string().email("Enter a valid company email"),
});
const profileSchema = z
  .object({
    full_name: z.string().min(1, "Name is required"),
    password: z
      .string()
      .min(8, "At least 8 characters")
      .regex(/[A-Z]/, "Include an uppercase letter")
      .regex(/[a-z]/, "Include a lowercase letter")
      .regex(/\d/, "Include a number"),
    confirm: z.string().min(8),
  })
  .refine((values) => values.password === values.confirm, {
    message: "Passwords do not match",
    path: ["confirm"],
  });

type EmailValues = z.infer<typeof emailSchema>;
type ProfileValues = z.infer<typeof profileSchema>;

export function RegisterPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState<"email" | "otp" | "profile" | "done">("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [registrationToken, setRegistrationToken] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [allowedDomains, setAllowedDomains] = useState<string[]>([]);
  const emailForm = useForm<EmailValues>({ resolver: zodResolver(emailSchema) });
  const profileForm = useForm<ProfileValues>({ resolver: zodResolver(profileSchema) });

  useEffect(() => {
    api
      .get<{ domains: string[] }>("/api/v1/auth/register/allowed-domains")
      .then((res) => setAllowedDomains(res.data.domains))
      .catch(() => setAllowedDomains([]));
  }, []);

  useEffect(() => {
    if (!cooldown) return;
    const timer = window.setInterval(() => setCooldown((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [cooldown]);

  const domainHint = allowedDomains.length
    ? `Use a company email ending in ${allowedDomains.map((domain) => `@${domain}`).join(" or ")}.`
    : "Use your company email address.";
  const emailPlaceholder = `you@${allowedDomains[0] ?? "company.com"}`;

  if (!loading && user) {
    return <Navigate to="/dashboard" replace />;
  }

  const requestOtp = async (address: string) => {
    setSubmitError(null);
    await api.post("/api/v1/auth/register/request-otp", { email: address });
    setEmail(address);
    setOtp("");
    setCooldown(60);
    setStep("otp");
  };

  return (
    <div className="app-shell flex min-h-screen items-center justify-center px-4 py-10">
      <div className="absolute right-6 top-6">
        <ThemeSwitcher />
      </div>
      <div className="card w-full max-w-md p-8 sm:p-10">
        <p className="text-xs uppercase tracking-wide text-muted">IT Support</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">
          {step === "email" && "Create your account"}
          {step === "otp" && "Verify your email"}
          {step === "profile" && "Complete your profile"}
          {step === "done" && "Account created successfully"}
        </h1>
        <ol className="mt-5 grid grid-cols-3 gap-2 text-xs">
          {["Email", "Verify", "Profile"].map((label, index) => {
            const active =
              (step === "email" && index === 0) ||
              (step === "otp" && index === 1) ||
              ((step === "profile" || step === "done") && index === 2);
            return (
              <li
                key={label}
                className={`rounded-xl px-3 py-2 ${active ? "bg-accent-soft font-semibold" : "bg-accent-soft/40 text-muted"}`}
              >
                {index + 1}. {label}
              </li>
            );
          })}
        </ol>

        {step === "email" && (
          <form
            className="mt-6 space-y-4"
            onSubmit={emailForm.handleSubmit(async (values) => {
              try {
                await requestOtp(values.email);
              } catch (err) {
                setSubmitError(getErrorMessage(err, "Could not send a verification code."));
              }
            })}
          >
            <label className="block text-sm font-medium">
              Company email
              <input className="input mt-1" type="email" autoComplete="email" placeholder={emailPlaceholder} {...emailForm.register("email")} />
              <p className="mt-1 text-xs text-muted">{domainHint}</p>
              {emailForm.formState.errors.email && (
                <p className="mt-1 text-xs text-red-500">{emailForm.formState.errors.email.message}</p>
              )}
            </label>
            {submitError && <p className="text-sm text-red-500">{submitError}</p>}
            <button type="submit" disabled={emailForm.formState.isSubmitting} className="btn-primary w-full py-2.5">
              {emailForm.formState.isSubmitting ? "Sending…" : "Send verification code"}
            </button>
          </form>
        )}

        {step === "otp" && (
          <form
            className="mt-6 space-y-4"
            onSubmit={async (event) => {
              event.preventDefault();
              setSubmitError(null);
              try {
                const { data } = await api.post<{ registration_token: string }>(
                  "/api/v1/auth/register/verify-otp",
                  { email, otp },
                );
                setRegistrationToken(data.registration_token);
                setStep("profile");
              } catch (err) {
                setSubmitError(getErrorMessage(err, "Invalid or expired code."));
              }
            }}
          >
            <p className="text-sm text-muted">
              We sent a 6-digit verification code to <span className="font-medium text-ink">{email}</span>
            </p>
            <OtpInput value={otp} onChange={setOtp} />
            {submitError && <p className="text-sm text-red-500">{submitError}</p>}
            <button type="submit" disabled={otp.length !== 6} className="btn-primary w-full py-2.5">
              Verify
            </button>
            <p className="text-center text-sm text-muted">
              Didn’t receive the code?{" "}
              {cooldown > 0 ? (
                <span>Resend in {cooldown} seconds</span>
              ) : (
                <button
                  type="button"
                  className="text-accent hover:underline"
                  onClick={() => void requestOtp(email).catch((err) => setSubmitError(getErrorMessage(err)))}
                >
                  Resend
                </button>
              )}
            </p>
          </form>
        )}

        {step === "profile" && (
          <form
            className="mt-6 space-y-4"
            onSubmit={profileForm.handleSubmit(async (values) => {
              setSubmitError(null);
              try {
                await api.post("/api/v1/auth/register/complete", {
                  registration_token: registrationToken,
                  full_name: values.full_name,
                  password: values.password,
                });
                setStep("done");
                window.setTimeout(() => navigate("/login"), 1200);
              } catch (err) {
                setSubmitError(getErrorMessage(err, "Could not create the account."));
              }
            })}
          >
            <label className="block text-sm font-medium">
              Full name
              <input className="input mt-1" autoComplete="name" {...profileForm.register("full_name")} />
              {profileForm.formState.errors.full_name && (
                <p className="mt-1 text-xs text-red-500">{profileForm.formState.errors.full_name.message}</p>
              )}
            </label>
            <label className="block text-sm font-medium">
              Password
              <input className="input mt-1" type="password" autoComplete="new-password" {...profileForm.register("password")} />
              {profileForm.formState.errors.password && (
                <p className="mt-1 text-xs text-red-500">{profileForm.formState.errors.password.message}</p>
              )}
            </label>
            <label className="block text-sm font-medium">
              Confirm password
              <input className="input mt-1" type="password" autoComplete="new-password" {...profileForm.register("confirm")} />
              {profileForm.formState.errors.confirm && (
                <p className="mt-1 text-xs text-red-500">{profileForm.formState.errors.confirm.message}</p>
              )}
            </label>
            {submitError && <p className="text-sm text-red-500">{submitError}</p>}
            <button type="submit" disabled={profileForm.formState.isSubmitting} className="btn-primary w-full py-2.5">
              {profileForm.formState.isSubmitting ? "Creating…" : "Create account"}
            </button>
          </form>
        )}

        {step === "done" && (
          <p className="mt-6 text-sm text-muted">Redirecting you to sign in…</p>
        )}

        <p className="mt-8 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link className="text-accent hover:underline" to="/login">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
