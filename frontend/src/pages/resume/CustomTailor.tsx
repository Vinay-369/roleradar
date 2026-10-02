import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  ClipboardPaste,
  FileText,
  LoaderCircle,
  SearchCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { createCustomJob } from "../../lib/jobs";
import { getMasterResume } from "../../lib/resume";

export function CustomTailor() {
  const navigate = useNavigate();
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [jdText, setJdText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const wordCount = jdText.trim() ? jdText.trim().split(/\s+/).length : 0;

  async function pasteFromClipboard() {
    try {
      const clipboardText = await navigator.clipboard.readText();
      if (!clipboardText) {
        setError("Your clipboard is empty.");
        return;
      }
      setJdText((current) => current ? `${current}\n${clipboardText}` : clipboardText);
      setError(null);
    } catch {
      setError("Clipboard access is unavailable. Please paste the job description into the text area.");
    }
  }

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
    <div className="mx-auto w-full min-w-0 max-w-4xl py-5 sm:py-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800 sm:p-8">
        <div className="mb-6 flex items-start gap-3.5">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-300">
            <Sparkles size={21} />
          </span>
          <div className="min-w-0">
            <h1 className="font-display text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 sm:text-2xl">
              Analyze External Job Description
            </h1>
            <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              Paste a job description to inspect requirements, eligibility, technical alignment, and skill gaps.
            </p>
          </div>
        </div>

        {!isCheckingResume && !masterResume && (
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-signal-500/20 bg-signal-500/5 p-4 dark:bg-signal-950/25">
            <AlertCircle size={19} className="mt-0.5 shrink-0 text-signal-600 dark:text-signal-300" />
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">No resume uploaded (optional)</h2>
              <p className="mb-2 mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                You can inspect job requirements without a resume. Upload one for personalized match scoring and Truth Guard tailoring.
              </p>
              <Link
                to="/resume/master"
                className="inline-flex items-center gap-1 text-xs font-semibold text-signal-700 hover:text-signal-800 hover:underline dark:text-signal-300"
              >
                Upload Master Resume <ArrowRight size={13} />
              </Link>
            </div>
          </div>
        )}

        {error && (
          <div role="alert" className="mb-5 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label htmlFor="external-jd-company" className="mb-1.5 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
              <Building2 size={15} className="text-slate-400" />
              Company Name <span className="font-normal text-slate-400">(Optional)</span>
            </label>
            <input
              id="external-jd-company"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="e.g. Google, Acme Corp"
              className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500"
            />
          </div>

          <div>
            <label htmlFor="external-jd-role" className="mb-1.5 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
              <BriefcaseBusiness size={15} className="text-slate-400" />
              Target Role Title <span className="font-normal text-slate-400">(Optional)</span>
            </label>
            <input
              id="external-jd-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="e.g. SDE-1, Backend Developer"
              className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500"
            />
          </div>
        </div>

        <div className="mt-5">
          <div className="mb-1.5 flex flex-wrap items-end justify-between gap-2">
            <label htmlFor="external-jd-text" className="text-sm font-semibold text-slate-700 dark:text-slate-200">
              Job Description or Requirements <span className="text-rose-500">*</span>
            </label>
            <span className="text-[11px] tabular-nums text-slate-500 dark:text-slate-400">
              {wordCount.toLocaleString()} words · {jdText.length.toLocaleString()} characters
            </span>
          </div>
          <textarea
            id="external-jd-text"
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            rows={10}
            placeholder="Paste the full job description or requirements text here…"
            className="min-h-[220px] w-full resize-y rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-3 text-sm leading-relaxed text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500"
          />
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <button type="button" onClick={pasteFromClipboard} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
              <ClipboardPaste size={13} /> Paste from Clipboard
            </button>
            <button type="button" onClick={() => { setJdText(""); setError(null); }} disabled={!jdText} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
              <Trash2 size={13} /> Clear Text
            </button>
            <button
              type="button"
              onClick={() => {
                setCompany("Acme Technologies");
                setRole("Backend Software Engineer");
                setJdText("Backend Software Engineer\n\nAbout the role\nWe are looking for a backend engineer to build reliable, scalable services and APIs.\n\nResponsibilities\n- Design, develop, and maintain REST APIs and distributed services.\n- Collaborate with product and frontend teams to deliver customer-facing features.\n- Improve application performance, reliability, and observability.\n\nRequirements\n- 3+ years of experience with Java or Python backend development.\n- Strong knowledge of data structures, algorithms, and object-oriented design.\n- Experience with SQL databases, caching, and cloud platforms.\n- Familiarity with Docker, Kubernetes, and CI/CD workflows.\n- Clear communication and a collaborative approach.");
                setError(null);
              }}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-2.5 text-xs font-semibold text-indigo-700 transition-colors hover:bg-indigo-100 dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300 dark:hover:bg-indigo-950/70"
            >
              <FileText size={13} /> Try Sample JD
            </button>
          </div>
        </div>

        <div className="mt-6 border-t border-slate-200 pt-5 dark:border-slate-700">
          <button
            type="button"
            onClick={() => {
              setError(null);
              analyzeMutation.mutate();
            }}
            disabled={analyzeMutation.isPending || !jdText.trim()}
            className="flex min-h-12 w-full items-center justify-center gap-2.5 rounded-xl bg-indigo-600 px-6 py-3.5 text-sm font-semibold text-white shadow-md transition-all hover:bg-indigo-700 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {analyzeMutation.isPending ? (
              <>
                <LoaderCircle size={17} className="animate-spin" />
                Analyzing opportunity…
              </>
            ) : (
              <>
                <SearchCheck size={17} />
                Analyze Opportunity &amp; Inspect Requirements
              </>
            )}
          </button>
          {analyzeMutation.isPending && (
            <p role="status" className="mt-2.5 flex items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <Sparkles size={13} className="animate-pulse text-indigo-500" />
              Extracting canonical skills &amp; computing match…
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
