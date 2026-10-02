import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Lock, Mail, Moon, Sun, Target, User } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";

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
        minLength={8}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete="new-password"
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

export function Register() {
  const { register } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(email, password, fullName);
      navigate("/onboarding");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Registration failed. Please check your details and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="rr-auth-page relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-slate-50 via-slate-100 to-indigo-50/30 p-4 text-slate-900 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 dark:text-slate-100">
      <button
        type="button"
        onClick={toggleTheme}
        className="absolute right-4 top-4 inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white/80 text-slate-600 shadow-sm backdrop-blur transition hover:border-indigo-200 hover:bg-white hover:text-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-300 dark:hover:border-indigo-700 dark:hover:bg-slate-800 dark:hover:text-indigo-300"
        aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
        title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
      >
        {theme === "light" ? <Moon size={18} /> : <Sun size={18} className="text-amber-300" />}
      </button>

      <div className="relative z-10 flex w-full max-w-md flex-col items-center py-8">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-sky-500 text-white shadow-lg shadow-indigo-500/20">
            <Target size={23} strokeWidth={2.5} />
          </div>
          <div>
            <p className="font-display text-lg font-semibold tracking-tight text-slate-900 dark:text-white">Role<span className="text-indigo-600 dark:text-indigo-400">Radar</span></p>
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">AI Resume Intelligence</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="w-full rounded-2xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-900/5 dark:border-slate-800 dark:bg-slate-900 dark:shadow-black/20">
          <div className="mb-7">
            <h1 className="font-display text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Create your account</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">Build your personal workspace for smarter applications.</p>
          </div>

          {error && <p className="mb-5 rounded-xl border border-red-200 bg-red-50 p-3 text-xs font-medium leading-5 text-red-700 dark:border-red-900/70 dark:bg-red-950/30 dark:text-red-300" role="alert">{error}</p>}

          <div className="space-y-5">
            <div>
              <label htmlFor="full-name" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">Full name</label>
              <div className="relative">
                <User aria-hidden="true" size={18} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input id="full-name" name="full_name" required value={fullName} onChange={(event) => setFullName(event.target.value)} autoComplete="name" className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-3 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
              </div>
            </div>

            <div>
              <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">Email address</label>
              <div className="relative">
                <Mail aria-hidden="true" size={18} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input id="email" name="email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" autoComplete="email" className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-3 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">Password</label>
              <PasswordInput value={password} onChange={setPassword} />
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Use at least 8 characters.</p>
            </div>
          </div>

          <button type="submit" disabled={submitting} className="mt-7 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-3 text-sm font-medium text-white shadow-md shadow-indigo-600/20 transition-all hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:focus:ring-offset-slate-900">
            {submitting ? "Creating account..." : <>Create account <ArrowRight size={17} /></>}
          </button>

          <p className="mt-7 text-center text-sm text-slate-500 dark:text-slate-400">Already have an account? <Link to="/login" className="font-semibold text-indigo-600 hover:underline dark:text-indigo-400">Sign in</Link></p>
        </form>
      </div>
    </main>
  );
}
