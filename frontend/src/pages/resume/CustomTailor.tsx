import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText, Sparkles, ArrowRight, AlertCircle } from "lucide-react";
import { generateCustomTailoring } from "../../lib/tailoring";
import { getMasterResume } from "../../lib/resume";

export function CustomTailor() {
  const navigate = useNavigate();
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [jdText, setJdText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: masterResume, isLoading: isCheckingResume } = useQuery({
    queryKey: ["master-resume"],
    queryFn: getMasterResume,
  });

  const generate = useMutation({
    mutationFn: () => generateCustomTailoring(company || "Custom Application", role || "Target Role", jdText),
    onSuccess: (version) => navigate(`/resume/tailor/${version.job_id}?version=${version.id}`),
    onError: (err: any) => setError(err?.response?.data?.detail ?? "Generation failed. Please try again."),
  });

  return (
    <div className="max-w-xl">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles size={22} className="text-signal-600" />
        <h1 className="font-display text-2xl text-ink-900">Tailor for an external job</h1>
      </div>
      <p className="text-ink-500 mb-6 text-sm">
        Paste any job description from LinkedIn, Indeed, or company portals. RoleRadar will evaluate ATS fit and propose tailored bullet points grounded in your master resume.
      </p>

      {!isCheckingResume && !masterResume && (
        <div className="mb-6 rounded-lg border border-amber-500/20 bg-amber-500/10 p-4 flex items-start gap-3">
          <AlertCircle size={20} className="text-amber-600 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-amber-900">Master Resume Required</h3>
            <p className="text-xs text-amber-700 mt-1 mb-3">
              You must upload an active master resume before tailoring. Our Truth Guard uses your verified background to propose honest, accurate resume bullets.
            </p>
            <Link
              to="/resume/master"
              className="inline-flex items-center gap-1 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-700 px-3 py-1.5 rounded-md transition-colors"
            >
              Upload Master Resume <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-md bg-alert-600/10 p-3 text-sm text-alert-600 flex items-center gap-2">
          <AlertCircle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <label className="block text-sm font-medium text-ink-700 mb-1">Company Name</label>
      <input
        value={company}
        onChange={(e) => setCompany(e.target.value)}
        placeholder="e.g. Acme Corp"
        className="w-full mb-4 rounded-md border border-ink-100 px-3 py-2.5 text-sm outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-shadow"
      />

      <label className="block text-sm font-medium text-ink-700 mb-1">Target Role Title</label>
      <input
        value={role}
        onChange={(e) => setRole(e.target.value)}
        placeholder="e.g. Backend Engineer, Full Stack Developer"
        className="w-full mb-4 rounded-md border border-ink-100 px-3 py-2.5 text-sm outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-shadow"
      />

      <label className="block text-sm font-medium text-ink-700 mb-1">
        Job Description <span className="text-alert-600">*</span>
      </label>
      <textarea
        value={jdText}
        onChange={(e) => setJdText(e.target.value)}
        rows={10}
        placeholder="Paste the full job description or requirements here…"
        className="w-full mb-6 rounded-md border border-ink-100 px-3.5 py-2.5 text-sm outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-shadow"
      />

      <button
        onClick={() => {
          setError(null);
          generate.mutate();
        }}
        disabled={generate.isPending || !jdText.trim() || (!isCheckingResume && !masterResume)}
        className="w-full flex items-center justify-center gap-2 rounded-md bg-ink-950 hover:bg-ink-900 text-white px-4 py-2.5 text-sm font-medium disabled:opacity-50 transition-all active:scale-[0.99]"
      >
        {generate.isPending ? (
          <>
            <span className="inline-block w-2 h-2 rounded-full bg-signal-400 animate-pulse" />
            Analyzing JD & Generating Tailoring Proposal…
          </>
        ) : (
          <>
            <FileText size={16} /> Generate Tailoring Proposal
          </>
        )}
      </button>
    </div>
  );
}
