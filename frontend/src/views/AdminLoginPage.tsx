import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Navigate } from "react-router-dom";
import { Link } from "../lib/nav";
import { useState } from "react";
import { AuthTopBar, BrandLogo } from "../components/BrandLogo";
import { useAuth } from "../lib/auth";
import { getErrorMessage } from "../lib/api";
import { accountEmailSchema } from "../lib/email";

const schema = z.object({
  email: accountEmailSchema,
  password: z.string().min(1, "Password is required"),
});

type FormValues = z.infer<typeof schema>;

export function AdminLoginPage() {
  const { user, loading, adminLogin, hasPermission } = useAuth();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const form = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (!loading && user && hasPermission("admin.portal.access")) {
    return <Navigate to="/admin/dashboard" replace />;
  }

  return (
    <div className="app-shell flex min-h-screen items-center justify-center px-4 py-4 sm:py-10">
      <AuthTopBar />
      <div className="auth-frame">
        <div className="hero-banner hidden min-h-full flex-col justify-between rounded-none p-8 md:flex md:p-10">
          <div className="flex flex-col items-start">
            <BrandLogo size="auth" />
            <h1 className="mt-8 max-w-sm text-3xl font-semibold leading-tight tracking-tight lg:text-4xl">
              Keep the queue moving.
            </h1>
          </div>
          <div className="max-w-sm space-y-3 text-sm leading-6 text-white/80">
            <p>Assign work, manage people, and close the loop from one console.</p>
            <p>Accounts are created by IT. There is no self-registration.</p>
          </div>
        </div>
        <div className="flex min-h-0 flex-col justify-center overflow-y-auto bg-surface p-8 md:p-10">
          <div className="mb-6 flex justify-center md:hidden">
            <BrandLogo size="auth" />
          </div>
          <p className="text-xs uppercase tracking-wide text-muted">IT Administration</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight">Admin sign in</h2>
          <p className="mt-2 text-sm text-muted">Use the administrator email and password provided by IT.</p>
          <form
            className="mt-6 space-y-4"
            noValidate
            onSubmit={form.handleSubmit(async (values) => {
              setSubmitError(null);
              try {
                await adminLogin(values.email, values.password);
              } catch (err) {
                setSubmitError(
                  getErrorMessage(err, "This account does not have access to the administration portal."),
                );
              }
            })}
          >
            <label className="field-label">
              Administrator email
              <input
                className="input"
                type="text"
                inputMode="email"
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                placeholder="you@company.com"
                {...form.register("email", { onChange: () => setSubmitError(null) })}
              />
              {form.formState.errors.email && (
                <p className="text-xs text-red-500">{form.formState.errors.email.message}</p>
              )}
            </label>
            <label className="field-label">
              Password
              <input className="input" type="password" autoComplete="current-password" {...form.register("password", { onChange: () => setSubmitError(null) })} />
              {form.formState.errors.password && (
                <p className="text-xs text-red-500">{form.formState.errors.password.message}</p>
              )}
            </label>
            {submitError && <p className="text-sm text-red-500">{submitError}</p>}
            <button type="submit" disabled={form.formState.isSubmitting} className="btn-primary w-full">
              {form.formState.isSubmitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="mt-8 text-center text-xs text-muted">
            <Link className="hover:underline" to="/login">
              Employee sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
