import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Sparkles, ArrowRight, AlertCircle, SearchCheck } from "lucide-react";
import { createCustomJob } from "../../lib/jobs";
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

  const analyzeMutation = useMutation({
    mutationFn: () =>
      createCustomJob({
        company: company.trim() || undefined,
        title: role.trim() || undefined,
        jd_text: jdText.trim(),
      }),
    onSuccess: (job) => {
      navigate(`/opportunities/job/${job.id}`);
    },
    onError: (err: any) =>
      setError(err?.response?.data?.detail ?? "Failed to analyze job description. Please check the text and try again."),
  });

  return (
    <div className="max-w-2xl mx-auto py-6 px-4">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles size={22} className="text-signal-600" />
        <h1 className="font-display text-2xl text-ink-900">Analyze External Job Description</h1>
      </div>
      <p className="text-ink-500 mb-6 text-sm leading-relaxed">
        Paste any job description from LinkedIn, Indeed, or company portals. RoleRadar will extract canonical structured requirements, evaluate your eligibility, compute your technical alignment, and highlight skill gaps. You can optionally tailor your resume afterwards.
      </p>

      {!isCheckingResume && !masterResume && (
        <div className="mb-6 rounded-lg border border-signal-500/20 bg-signal-500/5 p-4 flex items-start gap-3">
          <AlertCircle size={20} className="text-signal-600 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-ink-900">No Resume Uploaded (Optional)</h3>
            <p className="text-xs text-ink-600 mt-1 mb-2">
              You can still inspect the structured requirements and market expectations of this job without a resume. Upload your resume whenever you want personalized match scoring and Truth Guard tailoring.
            </p>
            <Link
              to="/resume/master"
              className="inline-flex items-center gap-1 text-xs font-semibold text-signal-700 hover:text-signal-800 hover:underline"
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

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-ink-700 mb-1">Company Name (Optional)</label>
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. Google, Acme Corp (or extracted from JD)"
            className="w-full rounded-md border border-ink-100 px-3 py-2.5 text-sm outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-shadow"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-ink-700 mb-1">Target Role Title (Optional)</label>
          <input
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder="e.g. SDE-1, Backend Developer"
            className="w-full rounded-md border border-ink-100 px-3 py-2.5 text-sm outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-shadow"
          />
        </div>
      </div>

      <label className="block text-sm font-medium text-ink-700 mb-1">
        Job Description or Requirements <span className="text-alert-600">*</span>
      </label>
      <textarea
        value={jdText}
        onChange={(e) => setJdText(e.target.value)}
        rows={12}
        placeholder="Paste the full job description or requirements text here…"
        className="w-full mb-6 rounded-md border border-ink-100 px-3.5 py-2.5 text-sm outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-shadow font-mono text-xs leading-relaxed"
      />

      <div className="flex flex-col sm:flex-row items-center gap-3">
        <button
          onClick={() => {
            setError(null);
            analyzeMutation.mutate();
          }}
          disabled={analyzeMutation.isPending || !jdText.trim()}
          className="w-full sm:flex-1 flex items-center justify-center gap-2 rounded-md bg-ink-950 hover:bg-ink-900 text-white px-4 py-2.5 text-sm font-medium disabled:opacity-50 transition-all active:scale-[0.99]"
        >
          {analyzeMutation.isPending ? (
            <>
              <span className="inline-block w-2 h-2 rounded-full bg-signal-400 animate-pulse" />
              Extracting Structured Requirements & Evaluating Fit…
            </>
          ) : (
            <>
              <SearchCheck size={16} /> Analyze Opportunity & Inspect Requirements
            </>
          )}
        </button>
      </div>
    </div>
  );
}
