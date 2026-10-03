import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  Eye,
  EyeOff,
  Lock,
  Mail,
  Moon,
  Sun,
  Target,
  Zap,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { requestPasswordReset, resetPassword } from "../../lib/auth";

function PasswordInput({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="relative">
      <Lock aria-hidden="true" size={18} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
      <input
        id="password"
        name="password"
        type={visible ? "text" : "password"}
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete="current-password"
        className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-11 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
      />
      <button
        type="button"
        onClick={() => setVisible((current) => !current)}
        className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        aria-label={visible ? "Hide password" : "Show password"}
      >
        {visible ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </div>
  );
}

export function Login() {
  const { login } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [recoveryOpen, setRecoveryOpen] = useState(false);
  const [recoveryEmail, setRecoveryEmail] = useState("");
  const [recoveryToken, setRecoveryToken] = useState<string | null>(null);
  const [recoveryPassword, setRecoveryPassword] = useState("");
  const [recoveryMessage, setRecoveryMessage] = useState<string | null>(null);
  const [recoverySubmitting, setRecoverySubmitting] = useState(false);

  async function performLogin(targetEmail: string, targetPassword: string) {
    setError(null);
    setNotice(null);
    setSubmitting(true);
    try {
      await login(targetEmail, targetPassword);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Invalid email or password. Please check your credentials or register.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await performLogin(email, password);
  }

  async function handleDemoSignIn() {
    setEmail("demo@example.com");
    setPassword("Password123!");
    await performLogin("demo@example.com", "Password123!");
  }

  function handleForgotPassword(event: React.MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setRecoveryEmail(email);
    setRecoveryToken(null);
    setRecoveryPassword("");
    setRecoveryMessage(null);
    setRecoveryOpen(true);
  }

  async function handleRecoveryRequest() {
    setError(null);
    setRecoveryMessage(null);
    setRecoverySubmitting(true);
    try {
      const result = await requestPasswordReset(recoveryEmail);
      setRecoveryMessage(result.message);
      setRecoveryToken(result.reset_token ?? null);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "We could not start password recovery. Please try again.");
    } finally {
      setRecoverySubmitting(false);
    }
  }

  async function handlePasswordReset() {
    if (!recoveryToken) return;
    setError(null);
    setRecoverySubmitting(true);
    try {
      const message = await resetPassword(recoveryToken, recoveryPassword);
      setNotice(message);
      setRecoveryOpen(false);
      setRecoveryToken(null);
      setRecoveryPassword("");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "We could not update your password. Please request a new reset link.");
    } finally {
      setRecoverySubmitting(false);
    }
  }

  return (
    <main className="rr-auth-page rr-login-page relative min-h-screen overflow-x-hidden overflow-y-auto text-slate-900 dark:text-slate-100">
      <button
        type="button"
        onClick={toggleTheme}
        className="absolute right-4 top-4 inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white/80 text-slate-600 shadow-sm backdrop-blur transition hover:border-indigo-200 hover:bg-white hover:text-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-300 dark:hover:border-indigo-700 dark:hover:bg-slate-800 dark:hover:text-indigo-300"
        aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
        title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
      >
        {theme === "light" ? <Moon size={18} /> : <Sun size={18} className="text-amber-300" />}
      </button>

      <header className="rr-portal-header">
        <div className="rr-portal-header-inner">
          <div className="rr-portal-brand">
          <div className="rr-portal-brand-mark">
            <Target size={23} strokeWidth={2.5} />
          </div>
          <div>
            <p className="font-display text-lg font-semibold tracking-tight text-white">Role<span className="text-cyan-300">Radar</span></p>
            <p className="text-xs font-medium text-slate-300">AI Resume Intelligence</p>
          </div>
        </div>
          <span className="rr-portal-year">AI CAREER WORKSPACE</span>
        </div>
      </header>

      <div className="relative z-10 mx-auto flex w-full max-w-[632px] flex-col items-center px-4 py-12">

        <form onSubmit={handleSubmit} className="rr-portal-card w-full rounded-2xl border bg-white p-8 shadow-xl sm:p-10 dark:bg-slate-900">
          <div className="mb-7">
            <p className="rr-portal-eyebrow">ROLE RADAR SIGN IN</p>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Welcome back</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">Sign in to continue to your RoleRadar workspace.</p>
          </div>

          {error && (
            <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900/70 dark:bg-red-950/30 dark:text-red-300" role="alert">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              <p className="font-medium leading-5">{error}</p>
            </div>
          )}

          {notice && (
            <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-indigo-200 bg-indigo-50 p-3 text-xs text-indigo-700 dark:border-indigo-900/70 dark:bg-indigo-950/30 dark:text-indigo-300" role="status">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              <p className="font-medium leading-5">{notice}</p>
            </div>
          )}

          <div className="space-y-5">
            <div>
              <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">Email address</label>
              <div className="relative">
                <Mail aria-hidden="true" size={18} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  autoComplete="email"
                  className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-3 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                />
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-slate-300">Password</label>
              </div>
              <PasswordInput value={password} onChange={setPassword} />
              <div className="mt-2 text-right">
                <a href="#forgot-password" onClick={handleForgotPassword} className="text-xs font-medium text-indigo-600 transition hover:text-indigo-700 hover:underline dark:text-indigo-400 dark:hover:text-indigo-300">Forgot password?</a>
              </div>
            </div>

            {recoveryOpen && (
              <div className="rounded-xl border border-indigo-200 bg-indigo-50/70 p-4 dark:border-indigo-900/70 dark:bg-indigo-950/30">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-semibold text-indigo-950 dark:text-indigo-100">Reset your password</h2>
                    <p className="mt-1 text-xs leading-5 text-indigo-800 dark:text-indigo-300">Enter your account email and we’ll prepare a secure reset.</p>
                  </div>
                  <button type="button" onClick={() => setRecoveryOpen(false)} className="text-xs font-medium text-indigo-700 hover:underline dark:text-indigo-300">Close</button>
                </div>

                {!recoveryToken ? (
                  <div className="space-y-3">
                    <label htmlFor="recovery-email" className="sr-only">Account email</label>
                    <input id="recovery-email" type="email" required value={recoveryEmail} onChange={(event) => setRecoveryEmail(event.target.value)} placeholder="you@example.com" autoComplete="email" className="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-indigo-800 dark:bg-slate-950 dark:text-slate-100" />
                    <button type="button" onClick={() => void handleRecoveryRequest()} disabled={recoverySubmitting || !recoveryEmail} className="w-full rounded-lg bg-indigo-600 px-3 py-2.5 text-xs font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60">{recoverySubmitting ? "Preparing reset..." : "Send reset instructions"}</button>
                    {recoveryMessage && <p className="text-xs leading-5 text-indigo-800 dark:text-indigo-300" role="status">{recoveryMessage}</p>}
                  </div>
                ) : (
                  <div className="space-y-3">
                    <label htmlFor="recovery-password" className="block text-xs font-medium text-indigo-900 dark:text-indigo-200">New password</label>
                    <input id="recovery-password" type="password" required minLength={8} value={recoveryPassword} onChange={(event) => setRecoveryPassword(event.target.value)} autoComplete="new-password" className="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-indigo-800 dark:bg-slate-950 dark:text-slate-100" />
                    <button type="button" onClick={() => void handlePasswordReset()} disabled={recoverySubmitting || recoveryPassword.length < 8} className="w-full rounded-lg bg-indigo-600 px-3 py-2.5 text-xs font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60">{recoverySubmitting ? "Updating password..." : "Update password"}</button>
                    {recoveryMessage && <p className="text-xs leading-5 text-indigo-800 dark:text-indigo-300" role="status">{recoveryMessage}</p>}
                  </div>
                )}
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="mt-7 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-3 text-sm font-medium text-white shadow-md shadow-indigo-600/20 transition-all hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:focus:ring-offset-slate-900"
          >
            {submitting ? "Signing in..." : <>Sign in <ArrowRight size={17} /></>}
          </button>

          <div className="my-6 flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
            <span>or</span>
            <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
          </div>

          <button
            type="button"
            onClick={handleDemoSignIn}
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 py-3 text-sm font-medium text-indigo-700 transition-all hover:bg-indigo-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 disabled:cursor-not-allowed disabled:opacity-60 dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300 dark:hover:bg-indigo-950/70"
          >
            <Zap size={16} className="text-indigo-500 dark:text-indigo-400" />
            <span>1-Click Sign In as Demo Candidate</span>
          </button>

          <p className="mt-7 text-center text-sm text-slate-500 dark:text-slate-400">No account? <Link to="/register" className="font-semibold text-cyan-700 hover:underline dark:text-cyan-300">Create account</Link></p>
        </form>
        <p className="rr-portal-assurance">Secure access · Your resume data stays private</p>
      </div>

    </main>
  );
}
