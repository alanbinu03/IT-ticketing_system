import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Navigate, Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { getErrorMessage } from "../lib/api";
import { useState } from "react";
import { ThemeSwitcher } from "../components/ThemeSwitcher";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1, "Password is required"),
});

type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (!loading && user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="app-shell flex min-h-screen items-center justify-center px-4 py-10">
      <div className="absolute right-6 top-6">
        <ThemeSwitcher />
      </div>
      <div className="grid w-full max-w-5xl overflow-hidden rounded-[2rem] border border-white/40 shadow-2xl lg:grid-cols-[1.15fr_0.85fr]">
        <div className="hero-banner hidden min-h-[520px] flex-col justify-between rounded-none p-10 lg:flex">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-white/75">IT Support</p>
            <h1 className="mt-5 max-w-sm text-4xl font-semibold leading-tight tracking-tight">
              A calmer way to get unblocked.
            </h1>
          </div>
          <div className="max-w-sm space-y-3 text-sm text-white/80">
            <p>Open a request, follow the thread, and see who owns the work.</p>
            <p>Admins get queues. Employees just see their own tickets.</p>
          </div>
        </div>
        <div className="card rounded-none border-0 bg-surface p-8 sm:p-10">
          <p className="text-xs uppercase tracking-wide text-muted">Welcome</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight">Sign in</h2>
          <p className="mt-2 text-sm text-muted">Use your organization account to continue.</p>
          <form
            className="mt-8 space-y-4"
            onSubmit={handleSubmit(async (values) => {
              setSubmitError(null);
              try {
                await login(values.email, values.password);
              } catch (err) {
                setSubmitError(getErrorMessage(err, "Invalid email or password."));
              }
            })}
          >
            <label className="block text-sm font-medium">
              Email
              <input
                className="input mt-1"
                type="email"
                autoComplete="username"
                placeholder="you@example.com"
                {...register("email")}
              />
              {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>}
            </label>
            <label className="block text-sm font-medium">
              Password
              <input
                className="input mt-1"
                type="password"
                autoComplete="current-password"
                {...register("password")}
              />
              {errors.password && <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>}
            </label>
            {submitError && <p className="text-sm text-red-500">{submitError}</p>}
            <button type="submit" disabled={isSubmitting} className="btn-primary w-full py-2.5">
              {isSubmitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="mt-8 text-center text-sm text-muted">
            New employee?{" "}
            <Link className="text-accent hover:underline" to="/register">
              Create account
            </Link>
          </p>
          <p className="mt-3 text-center text-xs text-muted">
            <Link className="hover:underline" to="/admin/login">
              Administrator login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
