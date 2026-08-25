import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Mail, Eye, EyeOff, ArrowRight, Zap, AlertCircle } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { AuthBrandPanel } from "../../components/layout/AuthBrandPanel";

function PasswordInput({ value, onChange, minLength }: { value: string; onChange: (v: string) => void; minLength?: number }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <input
        type={visible ? "text" : "password"}
        required
        minLength={minLength}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-ink-100 bg-white px-3 py-2.5 pr-10 text-sm outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-shadow"
      />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-500 hover:text-ink-900"
        tabIndex={-1}
      >
        {visible ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function performLogin(targetEmail: string, targetPass: string) {
    setError(null);
    setSubmitting(true);
    try {
      await login(targetEmail, targetPass);
      navigate("/dashboard");
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? "Invalid email or password. Please check your credentials or register.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await performLogin(email, password);
  }

  async function handleDemoSignIn() {
    setEmail("demo@example.com");
    setPassword("Password123!");
    await performLogin("demo@example.com", "Password123!");
  }

  return (
    <div className="min-h-screen flex bg-ink-50">
      <AuthBrandPanel />
      <div className="flex-1 flex items-center justify-center p-6">
        <form onSubmit={handleSubmit} className="w-full max-w-sm animate-fade-in-up">
          <h1 className="font-display text-2xl text-ink-900 mb-1">Welcome back</h1>
          <p className="text-sm text-ink-500 mb-6">Sign in to your RoleRadar account</p>

          {error && (
            <div className="mb-4 rounded-lg bg-alert-600/10 border border-alert-600/20 p-3 text-xs text-alert-600 flex items-start gap-2">
              <AlertCircle size={15} className="shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">{error}</p>
                <p className="mt-1 text-ink-600">
                  Don't have an account? <Link to="/register" className="text-signal-600 font-semibold underline">Register here</Link> or use demo sign-in below.
                </p>
              </div>
            </div>
          )}

          <label className="block text-sm text-ink-700 mb-1.5 font-medium">Email Address</label>
          <div className="relative mb-4">
            <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" />
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-md border border-ink-100 bg-white pl-9 pr-3 py-2.5 text-sm outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-shadow"
            />
          </div>

          <label className="block text-sm text-ink-700 mb-1.5 font-medium">Password</label>
          <div className="mb-6">
            <PasswordInput value={password} onChange={setPassword} />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-1.5 rounded-lg bg-ink-950 hover:bg-ink-900 text-white py-2.5 text-sm font-semibold disabled:opacity-60 transition-all active:scale-[0.98] shadow-xs"
          >
            {submitting ? "Signing in…" : <>Sign in <ArrowRight size={15} /></>}
          </button>

          {/* Quick 1-Click Demo Login */}
          <div className="mt-4">
            <button
              type="button"
              onClick={handleDemoSignIn}
              disabled={submitting}
              className="w-full flex items-center justify-center gap-1.5 rounded-lg bg-signal-500/10 hover:bg-signal-500/15 border border-signal-500/20 text-signal-700 py-2.5 text-xs font-semibold transition-all active:scale-[0.98]"
            >
              <Zap size={14} className="text-signal-600" />
              <span>⚡ 1-Click Sign In as Demo Candidate</span>
            </button>
          </div>

          <p className="mt-6 text-sm text-ink-500 text-center">
            No account? <Link to="/register" className="text-signal-600 hover:underline font-semibold">Create account</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
