import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Navigate } from "react-router-dom";
import { Link } from "../lib/nav";
import { useAuth } from "../lib/auth";
import { getErrorMessage } from "../lib/api";
import { accountEmailSchema } from "../lib/email";
import { useState } from "react";
import { AuthTopBar, BrandLogo } from "../components/BrandLogo";

const schema = z.object({
  email: accountEmailSchema,
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
    <div className="app-shell flex min-h-screen items-center justify-center px-4 py-4 sm:py-10">
      <AuthTopBar />
      <div className="auth-frame">
        <div className="hero-banner hidden min-h-full flex-col justify-between rounded-none p-8 md:flex md:p-10">
          <div className="flex flex-col items-start">
            <BrandLogo size="auth" />
            <h1 className="mt-8 max-w-sm text-3xl font-semibold leading-tight tracking-tight lg:text-4xl">
              A calmer way to get unblocked.
            </h1>
          </div>
          <div className="max-w-sm space-y-3 text-sm leading-6 text-white/80">
            <p>Open a request, follow the thread, and see who owns the work.</p>
            <p>Admins get queues. Employees just see their own tickets.</p>
          </div>
        </div>
        <div className="flex min-h-0 flex-col justify-center overflow-y-auto bg-surface p-8 md:p-10">
          <div className="mb-6 flex justify-center md:hidden">
            <BrandLogo size="auth" />
          </div>
          <p className="text-xs uppercase tracking-wide text-muted">Welcome</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight">Sign in</h2>
          <p className="mt-2 text-sm text-muted">Use the email and password provided by IT.</p>
          <form
            className="mt-6 space-y-4"
            noValidate
            onSubmit={handleSubmit(async (values) => {
              setSubmitError(null);
              try {
                await login(values.email, values.password);
              } catch (err) {
                setSubmitError(getErrorMessage(err, "Invalid email or password."));
              }
            })}
          >
            <label className="field-label">
              Email
              <input
                className="input"
                type="text"
                inputMode="email"
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                placeholder="you@company.com"
                {...register("email", { onChange: () => setSubmitError(null) })}
              />
              {errors.email && <p className="text-xs text-red-500">{errors.email.message}</p>}
            </label>
            <label className="field-label">
              Password
              <input
                className="input"
                type="password"
                autoComplete="current-password"
                {...register("password", { onChange: () => setSubmitError(null) })}
              />
              {errors.password && <p className="text-xs text-red-500">{errors.password.message}</p>}
            </label>
            {submitError && <p className="text-sm text-red-500">{submitError}</p>}
            <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
              {isSubmitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="mt-8 text-center text-xs text-muted">
            <Link className="hover:underline" to="/admin/login">
              Administrator login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
