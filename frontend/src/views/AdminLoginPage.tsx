import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, Navigate } from "react-router-dom";
import { useState } from "react";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useAuth } from "../lib/auth";
import { getErrorMessage } from "../lib/api";

const schema = z.object({
  email: z.string().email(),
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
    <div className="app-shell flex min-h-screen items-center justify-center px-4 py-10">
      <div className="absolute right-6 top-6">
        <ThemeSwitcher />
      </div>
      <div className="card w-full max-w-md p-8 sm:p-10">
        <p className="text-xs uppercase tracking-wide text-muted">IT Administration</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Admin sign in</h1>
        <p className="mt-2 text-sm text-muted">Administrator access only. There is no public admin registration.</p>
        <form
          className="mt-8 space-y-4"
          onSubmit={form.handleSubmit(async (values) => {
            setSubmitError(null);
            try {
              await adminLogin(values.email, values.password);
            } catch (err) {
              setSubmitError(getErrorMessage(err, "This account does not have access to the administration portal."));
            }
          })}
        >
          <label className="block text-sm font-medium">
            Administrator email
            <input className="input mt-1" type="email" autoComplete="username" {...form.register("email")} />
          </label>
          <label className="block text-sm font-medium">
            Password
            <input className="input mt-1" type="password" autoComplete="current-password" {...form.register("password")} />
          </label>
          {submitError && <p className="text-sm text-red-500">{submitError}</p>}
          <button type="submit" disabled={form.formState.isSubmitting} className="btn-primary w-full py-2.5">
            {form.formState.isSubmitting ? "Signing in…" : "Sign in to Admin Console"}
          </button>
        </form>
        <p className="mt-8 text-center text-sm text-muted">
          <Link className="text-accent hover:underline" to="/login">
            Employee sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
