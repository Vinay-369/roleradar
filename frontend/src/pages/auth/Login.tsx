import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Mail, Eye, EyeOff, ArrowRight } from "lucide-react";
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
        className="w-full rounded-md border border-ink-100 px-3 py-2.5 pr-10 text-sm outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-shadow"
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Login failed. Check your credentials.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex bg-ink-50">
      <AuthBrandPanel />
      <div className="flex-1 flex items-center justify-center p-6">
        <form onSubmit={handleSubmit} className="w-full max-w-sm animate-fade-in-up">
          <h1 className="font-display text-2xl text-ink-900 mb-1">Welcome back</h1>
          <p className="text-sm text-ink-500 mb-8">Sign in to your account</p>

          {error && (
            <p className="mb-4 rounded-md bg-alert-600/10 px-3 py-2 text-sm text-alert-600">{error}</p>
          )}

          <label className="block text-sm text-ink-700 mb-1.5">Email</label>
          <div className="relative mb-4">
            <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" />
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-ink-100 pl-9 pr-3 py-2.5 text-sm outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-shadow"
            />
          </div>

          <label className="block text-sm text-ink-700 mb-1.5">Password</label>
          <div className="mb-6">
            <PasswordInput value={password} onChange={setPassword} />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-1.5 rounded-md bg-ink-950 hover:bg-ink-900 text-white py-2.5 text-sm font-medium disabled:opacity-60 transition-all active:scale-[0.98]"
          >
            {submitting ? "Signing in…" : <>Sign in <ArrowRight size={15} /></>}
          </button>

          <p className="mt-6 text-sm text-ink-500 text-center">
            No account? <Link to="/register" className="text-signal-600 hover:underline font-medium">Register</Link>
          </p>

          <div className="mt-6 p-3.5 bg-ink-100/70 border border-ink-200/80 rounded-lg text-xs text-ink-600">
            <div className="flex items-center justify-between font-medium text-ink-900 mb-1">
              <span>Quick Sign-In</span>
              <button
                type="button"
                onClick={() => {
                  setEmail("demo@example.com");
                  setPassword("Password123!");
                }}
                className="text-signal-600 font-semibold hover:underline"
              >
                Auto-fill
              </button>
            </div>
            <p className="text-ink-500 font-mono text-[11px]">demo@example.com / Password123!</p>
          </div>
        </form>
      </div>
    </div>
  );
}
