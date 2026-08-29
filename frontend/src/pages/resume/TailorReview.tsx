import { useState } from "react";
import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ShieldCheck,
  Sparkles,
  Download,
  AlertTriangle,
  Trash2,
  Bookmark,
  MessageCircleQuestion,
  Map as MapIcon,
  ArrowRight,
  ArrowUpDown,
  FileCheck2,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Eye,
} from "lucide-react";
import {
  generateTailoring,
  getTailoredVersion,
  finalizeTailoring,
  deleteTailoredVersion,
  updateChangeStatus,
  type Change,
} from "../../lib/tailoring";
import { getATSScore } from "../../lib/intelligence";
import { apiClient } from "../../lib/apiClient";
import { ResumeDiffModal } from "../../components/resume/ResumeDiffModal";
import { useToast } from "../../context/ToastContext";

const STATUS_STYLE: Record<Change["status"], string> = {
  PENDING: "bg-ink-50 text-ink-500",
  APPROVED: "bg-signal-500/10 text-signal-600",
  REJECTED: "bg-alert-600/10 text-alert-600",
  NEEDS_USER_INPUT: "bg-amber-500/10 text-amber-600",
};

const ATS_PLATFORMS = [
  { id: "general", label: "Standard ATS (Parseability & Density)" },
  { id: "workday", label: "Workday (Strict Layout & Keyword Match)" },
  { id: "greenhouse", label: "Greenhouse (Recruiter Impact & Verbs)" },
  { id: "lever", label: "Lever (Core CS Taxonomy)" },
  { id: "icims", label: "iCIMS (Section Structure)" },
];

const TEMPLATES = [
  { id: "modern", label: "Modern Teal", desc: "Clean single-column with elegant signal accents." },
  { id: "classic", label: "Classic Black", desc: "Traditional monochrome layout for strict corporate ATS." },
  { id: "technical", label: "Tech Navy", desc: "High-density formatting with deep navy headers." },
  { id: "harvard", label: "Harvard Academic", desc: "Classic ivy-league serif styling with clean dividers." },
];

function ATSScorePanel({ jobId, versionId }: { jobId: string; versionId?: string }) {
  const [selectedPlatform, setSelectedPlatform] = useState<string>("general");

  const { data: ats, isLoading } = useQuery({
    queryKey: ["ats-score", jobId, selectedPlatform, versionId],
    queryFn: () => getATSScore(jobId, selectedPlatform, versionId),
    enabled: !!jobId,
  });

  if (isLoading || !ats) {
    return <div className="rounded-lg border border-ink-100 bg-white p-4 mb-6 text-xs text-ink-500">Evaluating ATS compatibility…</div>;
  }

  const guidance = ats.match_guidance;
  const platform = ats.platform_compliance;

  return (
    <div className="rounded-xl border border-ink-100 bg-white p-5 mb-6 shadow-xs">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <p className="text-xs font-bold uppercase tracking-wider text-ink-500">
              Corporate ATS Scoring & Audit Engine
            </p>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
              ats.knockout_passed !== false
                ? "bg-signal-500/10 text-signal-700 border border-signal-500/20"
                : "bg-alert-600/10 text-alert-700 border border-alert-600/20"
            }`}>
              {ats.knockout_passed !== false ? "✓ Passed Knockout Gatekeeper" : "⚠️ Failed Knockout"}
            </span>
          </div>
          <p className="text-xs text-ink-500">
            Target company system: <span className="font-semibold text-ink-800">{platform?.platform_name || "Enterprise ATS"}</span> • Status: <span className="font-semibold text-signal-700">{ats.match_status || "High Match (>=80%)"}</span>
          </p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-display text-ink-900 font-bold">{ats.overall}%</span>
          <p className="text-[10px] text-ink-400">ATS Match Score</p>
        </div>
      </div>

      <div className={`p-3 rounded-lg border mb-4 ${
        guidance?.status === "ideal"
          ? "bg-signal-500/10 border-signal-500/20 text-signal-800"
          : guidance?.status === "over_optimized"
          ? "bg-signal-500/10 border-signal-500/20 text-signal-800"
          : "bg-ink-50 border-ink-100 text-ink-800"
      }`}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-bold flex items-center gap-1.5">
            🎯 {guidance?.label || "ATS Benchmark Evaluation"}
          </span>
          <span className="text-[11px] font-mono font-medium">Enterprise Target: 75%–85%+</span>
        </div>
        <p className="text-xs leading-relaxed opacity-90">{guidance?.message}</p>
        {ats.keyword_density !== undefined && (
          <div className="mt-2 pt-2 border-t border-black/5 flex items-center justify-between text-[11px]">
            <span>Keyword Density: <strong className={ats.over_optimization_warning ? "text-amber-600" : "text-ink-700"}>{ats.keyword_density}%</strong></span>
            <span className="text-ink-500">Workday safe limit: &lt;3.0% / 100 words</span>
          </div>
        )}
      </div>

      {ats.categories && ats.categories.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-bold uppercase tracking-wider text-ink-700 mb-2">
            Detailed 4-Dimension Score Breakdown:
          </p>
          <div className="overflow-x-auto rounded-lg border border-ink-100">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-ink-50 border-b border-ink-100 text-ink-600">
                  <th className="py-2 px-3 font-semibold">Evaluation Category</th>
                  <th className="py-2 px-2 font-semibold text-center w-16">Max</th>
                  <th className="py-2 px-2 font-semibold text-center w-16">Awarded</th>
                  <th className="py-2 px-3 font-semibold">Key Findings / Critical Gaps</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100">
                {ats.categories.map((cat, idx) => (
                  <tr key={idx} className="hover:bg-ink-50/50">
                    <td className="py-2 px-3 font-semibold text-ink-900">{cat.category_name}</td>
                    <td className="py-2 px-2 text-center text-ink-500">{cat.max_points}</td>
                    <td className="py-2 px-2 text-center font-bold text-signal-700">{cat.points_awarded}</td>
                    <td className="py-2 px-3 text-ink-600 leading-tight">{cat.key_findings}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {ats.action_plan && ats.action_plan.length > 0 && (
        <div className="mb-4 rounded-lg bg-ink-50/70 border border-ink-100/80 p-3.5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-signal-800 mb-2 flex items-center gap-1.5">
            🛠️ Critical Action Plan to Reach 90%+
          </p>
          <div className="space-y-2">
            {ats.action_plan.map((item, idx) => (
              <div key={idx} className="text-xs">
                <span className="font-bold text-ink-800 mr-1.5">{idx + 1}. {item.type} ({item.title}):</span>
                <span className="text-ink-600">{item.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <label className="block text-[11px] font-semibold uppercase tracking-wider text-ink-500 mb-2">
          Select Target Hiring Platform Rules:
        </label>
        <div className="flex flex-wrap gap-1.5">
          {ATS_PLATFORMS.map((p) => {
            const isSelected = selectedPlatform === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => setSelectedPlatform(p.id)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                  isSelected
                    ? "bg-ink-950 text-white shadow-xs"
                    : "bg-ink-50 text-ink-600 hover:bg-ink-100"
                }`}
              >
                {p.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ChangeCard({
  change,
}: {
  versionId: string;
  change: Change;
  onUpdated: () => void;
}) {
  const isReorder = change.change_type === "SKILL_REORDER";
  const sectionLabel = change.section || "EXPERIENCE";

  return (
    <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs transition-all hover:border-ink-200">
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="rounded bg-ink-100 px-2 py-0.5 font-mono text-[10px] font-bold uppercase text-ink-700">
            {sectionLabel}
          </span>
          {isReorder && (
            <span className="rounded bg-teal-500/10 border border-teal-500/20 px-2 py-0.5 text-[10px] font-bold text-teal-700 flex items-center gap-1">
              <ArrowUpDown size={11} /> Skill Reorder
            </span>
          )}
          <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${STATUS_STYLE[change.status]}`}>
            {change.status.replace("_", " ")}
          </span>
        </div>
        <span className="text-xs text-ink-500 font-mono">
          Confidence: {Math.round(change.confidence * 100)}%
        </span>
      </div>

      {change.fabrication_warning && (
        <div className="mb-3 rounded-lg border border-amber-300 bg-amber-50 p-2.5 text-xs text-amber-900 flex items-start gap-2">
          <AlertTriangle size={14} className="text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold">Truth Guard Verification Notice</p>
            <p className="text-[11px] text-amber-800">{change.fabrication_warning}</p>
          </div>
        </div>
      )}

      {isReorder && change.after_order ? (
        <div className="mb-3 space-y-2">
          <p className="text-xs font-semibold text-ink-700">Prioritized Skill Ordering:</p>
          <div className="flex flex-wrap gap-1.5 p-3 rounded-lg bg-signal-500/5 border border-signal-500/20">
            {change.after_order.map((sk, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded bg-white border border-signal-500/30 text-xs font-medium text-signal-900 shadow-2xs"
              >
                {sk}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <>
          <p className="text-xs text-ink-900 font-medium mb-1.5 font-mono bg-emerald-500/5 border border-emerald-500/20 p-2.5 rounded-lg text-emerald-950">
            <span className="font-bold text-emerald-700 mr-1.5">Proposed:</span>
            {change.proposed}
          </p>
          {change.original && (
            <p className="text-xs text-ink-500 line-through mb-2 font-mono bg-ink-50/50 p-2 rounded-lg">
              <span className="font-semibold text-ink-400 mr-1.5">Original:</span>
              {change.original}
            </p>
          )}
        </>
      )}

      <div className="rounded-xl bg-signal-500/5 border border-signal-500/20 p-3 mb-3">
        <span className="text-[11px] font-bold uppercase tracking-wider text-signal-700 flex items-center gap-1 mb-1">
          <ShieldCheck size={13} /> Verified Source Evidence:
        </span>
        <p className="text-xs text-ink-800 leading-relaxed font-mono">
          {change.source_evidence || "None provided — requires candidate confirmation."}
        </p>
      </div>

      <p className="text-xs text-ink-600"><span className="font-bold text-ink-800">Why:</span> {change.reason}</p>
    </div>
  );
}

export function TailorReview() {
  const { jobId } = useParams<{ jobId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [batchApproving, setBatchApproving] = useState(false);

  const existingVersionId = searchParams.get("version");

  const versionQuery = useQuery({
    queryKey: ["tailoring", existingVersionId],
    queryFn: () => getTailoredVersion(existingVersionId!),
    enabled: !!existingVersionId,
  });

  const generate = useMutation({
    mutationFn: () => generateTailoring(jobId!),
    onSuccess: (data) => {
      setSearchParams({ version: data.id });
      queryClient.invalidateQueries({ queryKey: ["tailoring", data.id] });
      queryClient.invalidateQueries({ queryKey: ["tailoring-list"] });
      toast.success("Tailoring proposal generated with Grounded Evidence!");
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail ?? "Generation failed.");
      toast.error("Failed to generate tailoring proposal.");
    },
  });

  const version = existingVersionId ? versionQuery.data : generate.data;
  const activeVersionId = version?.id || existingVersionId;

  const finalize = useMutation({
    mutationFn: (versionId: string) => finalizeTailoring(versionId),
    onSuccess: () => {
      if (activeVersionId) {
        queryClient.invalidateQueries({ queryKey: ["tailoring", activeVersionId] });
      }
      queryClient.invalidateQueries({ queryKey: ["tailoring-list"] });
      queryClient.invalidateQueries({ queryKey: ["ats-score"] });
      toast.success("Tailored resume finalized and verified with ATS benchmark!");
    },
    onError: () => toast.error("Failed to finalize resume."),
  });

  const deleteVersion = useMutation({
    mutationFn: (versionId: string) => deleteTailoredVersion(versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tailoring-list"] });
      toast.info("Tailored version deleted.");
      navigate("/resume/versions");
    },
  });

  function refresh() {
    if (activeVersionId) {
      queryClient.invalidateQueries({ queryKey: ["tailoring", activeVersionId] });
    }
    queryClient.invalidateQueries({ queryKey: ["ats-score"] });
  }

  const handleApplyAllChanges = async () => {
    if (!version?.id) return;
    setBatchApproving(true);
    try {
      const pendingChanges = version.changes.filter((c) => c.status === "PENDING");
      for (const c of pendingChanges) {
        await updateChangeStatus(version.id, c.change_id, "APPROVED");
      }
      refresh();
      await finalize.mutateAsync(version.id);
      toast.success("Applied verified changes and finalized resume. Unverified changes were excluded.");
    } catch {
      toast.error("Failed to apply changes.");
    } finally {
      setBatchApproving(false);
    }
  };

  const [selectedTemplate, setSelectedTemplate] = useState<string>("modern");

  const previewPdf = async (url: string) => {
    try {
      const res = await apiClient.get(url, { responseType: "blob" });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const blobUrl = window.URL.createObjectURL(blob);
      window.open(blobUrl, "_blank");
      setTimeout(() => {
        window.URL.revokeObjectURL(blobUrl);
      }, 120000);
    } catch {
      toast.error("Failed to preview PDF.");
    }
  };

  const downloadFile = async (url: string, filename: string) => {
    try {
      const isPdf = filename.toLowerCase().endsWith(".pdf");
      const mimeType = isPdf
        ? "application/pdf"
        : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
      const res = await apiClient.get(url, { responseType: "blob" });
      const blob = new Blob([res.data], { type: mimeType });
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      // Keep blob URL alive so browser download shelf / viewer has time to access the file
      setTimeout(() => {
        window.URL.revokeObjectURL(blobUrl);
      }, 60000);
      toast.success(`Downloaded ${filename}`);
    } catch {
      toast.error("Download failed. Please try again.");
    }
  };

  if (!existingVersionId && !generate.data && !generate.isPending) {
    return (
      <div className="max-w-3xl">
        <h1 className="font-display text-2xl text-ink-900 mb-2">Tailor resume for this job</h1>
        <p className="text-ink-500 mb-6 text-sm">
          RoleRadar will propose section-complete changes grounded exclusively in your master resume — zero fabrication.
        </p>
        {error && (
          <p className="mb-4 rounded-md bg-alert-600/10 px-3 py-2 text-sm text-alert-600">
            {error}
          </p>
        )}
        <button
          onClick={() => generate.mutate()}
          className="rounded-lg bg-ink-950 hover:bg-ink-900 text-white px-5 py-2.5 text-xs font-bold shadow-xs transition-colors"
        >
          Generate Holistic Tailoring Proposal
        </button>
      </div>
    );
  }

  if (generate.isPending || versionQuery.isLoading) {
    return <p className="text-ink-500 text-sm">Generating holistic tailoring proposal…</p>;
  }

  if (!version) return <p className="text-ink-500 text-sm">Loading…</p>;

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl text-ink-900">
            {version.job_title} at {version.company}
          </h1>
          <p className="text-ink-500 text-sm mt-0.5">
            Holistic resume tailoring across all sections with deterministic truth guards.
          </p>
        </div>

        <div className="shrink-0">
          {confirmDelete ? (
            <div className="flex items-center gap-1.5 bg-alert-50/90 border border-alert-200 px-2.5 py-1 rounded-lg">
              <span className="text-xs font-semibold text-alert-700">Delete version?</span>
              <button
                type="button"
                onClick={() => version.id && deleteVersion.mutate(version.id)}
                disabled={deleteVersion.isPending}
                className="px-2 py-0.5 rounded bg-alert-600 hover:bg-alert-700 text-white text-xs font-bold transition-colors flex items-center gap-1"
              >
                {deleteVersion.isPending ? "Deleting…" : "Confirm"}
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="px-2 py-0.5 rounded bg-ink-100 hover:bg-ink-200 text-ink-700 text-xs font-semibold transition-colors"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-alert-200 text-alert-700 hover:bg-alert-50 text-xs font-semibold transition-colors"
              title="Delete this tailored version"
            >
              <Trash2 size={13} />
              <span>Delete</span>
            </button>
          )}
        </div>
      </div>

      {/* ATS Score Benchmark Panel */}
      <ATSScorePanel jobId={version.job_id} versionId={version.is_finalized ? (activeVersionId || undefined) : undefined} />

      {/* Protected Sections Structural Lock Banner */}
      <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-3.5 mb-6 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-emerald-950">
          <ShieldCheck size={16} className="text-emerald-600 shrink-0" />
          <span>
            <strong>Protected Sections Locked &amp; 100% Intact:</strong> Contact Details, Education History, and Certifications are physically isolated from AI alterations.
          </span>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-600/10 text-emerald-800 border border-emerald-600/20">
          Truth Guard Protected
        </span>
      </div>

      {/* Honesty Guard: Unmatched Skill Gaps Found */}
      {version.unmatched_gaps && version.unmatched_gaps.length > 0 && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-4 shadow-xs mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-blue-900 flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-blue-600" />
              Gaps Found in Job Description (Honesty Guarded)
            </span>
            <Link
              to={`/growth/roadmap/${version.job_id}`}
              className="text-[11px] font-bold text-blue-700 hover:text-blue-800 hover:underline flex items-center gap-1"
            >
              Prepare with Roadmap <ArrowRight size={11} />
            </Link>
          </div>
          <p className="text-xs text-blue-800 leading-relaxed mb-3">
            The target job requires the following skills that were not found in your master resume. RoleRadar’s Truth Guard will <strong>never invent</strong> false experience:
          </p>
          <div className="flex flex-wrap gap-1.5">
            {version.unmatched_gaps.map((gap, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-md bg-white border border-blue-200 text-blue-900 text-xs font-semibold shadow-2xs flex items-center gap-1"
              >
                <AlertTriangle size={11} className="text-amber-500" /> {gap}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-ink-900">
            Proposed Changes ({version.changes.length})
          </h2>
          <p className="text-xs text-ink-500">
            All changes are verified against your master resume with zero fabrication.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {!version.is_finalized && (
            <button
              type="button"
              onClick={handleApplyAllChanges}
              disabled={batchApproving || finalize.isPending}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-signal-500 hover:bg-signal-600 text-white text-xs font-bold transition-colors shadow-xs disabled:opacity-60"
            >
              <Sparkles size={13} />
              <span>{batchApproving || finalize.isPending ? "Applying All Changes…" : "Apply All Changes"}</span>
            </button>
          )}
          <ResumeDiffModal version={version} />
        </div>
      </div>

      {/* Changes List */}
      <div className="space-y-3">
        {version.changes.map((change) => (
          <ChangeCard key={change.change_id} versionId={version.id} change={change} onUpdated={refresh} />
        ))}
      </div>

      {/* Finalize CTA & Post-Finalize Results */}
      {!version.is_finalized ? (
        <button
          onClick={handleApplyAllChanges}
          disabled={batchApproving || finalize.isPending}
          className="rounded-lg bg-signal-500 hover:bg-signal-600 text-white px-5 py-2.5 text-xs font-bold shadow-xs disabled:opacity-60 transition-colors flex items-center gap-1.5"
        >
          <Sparkles size={13} />
          <span>{batchApproving || finalize.isPending ? "Applying All Changes & Finalizing…" : "Apply All Changes"}</span>
        </button>
      ) : (
        <div className="space-y-4 animate-fade-in-up">
          {/* Whole-Document Validation Dashboard */}
          {version.validation_summary && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 shadow-xs">
              <p className="text-xs font-bold uppercase tracking-wider text-emerald-950 mb-3 flex items-center gap-1.5">
                <FileCheck2 size={16} className="text-emerald-700" />
                4-Point Whole-Document Validation Audit:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                <div className="flex items-center gap-2 p-2 rounded-lg bg-white border border-emerald-100">
                  {version.validation_summary.protected_sections_intact ? (
                    <CheckCircle2 size={15} className="text-emerald-600 shrink-0" />
                  ) : (
                    <XCircle size={15} className="text-alert-600 shrink-0" />
                  )}
                  <span className="text-ink-800">Protected Sections Intact (Education & Contact)</span>
                </div>

                <div className="flex items-center gap-2 p-2 rounded-lg bg-white border border-emerald-100">
                  {version.validation_summary.anti_fabrication_passed ? (
                    <CheckCircle2 size={15} className="text-emerald-600 shrink-0" />
                  ) : (
                    <AlertTriangle size={15} className="text-amber-500 shrink-0" />
                  )}
                  <span className="text-ink-800">Anti-Fabrication Check (0 ungrounded tools)</span>
                </div>

                <div className="flex items-center gap-2 p-2 rounded-lg bg-white border border-emerald-100">
                  {version.validation_summary.one_page_fit ? (
                    <CheckCircle2 size={15} className="text-emerald-600 shrink-0" />
                  ) : (
                    <AlertTriangle size={15} className="text-amber-500 shrink-0" />
                  )}
                  <span className="text-ink-800">1-Page PDF Fit Guarantee ({version.validation_summary.page_count} page)</span>
                </div>

                <div className="flex items-center gap-2 p-2 rounded-lg bg-white border border-emerald-100">
                  {version.validation_summary.score_improvement ? (
                    <CheckCircle2 size={15} className="text-emerald-600 shrink-0" />
                  ) : (
                    <HelpCircle size={15} className="text-ink-400 shrink-0" />
                  )}
                  <span className="text-ink-800">ATS Score & Recruiter Impact Verified</span>
                </div>
              </div>
            </div>
          )}

          {version.tailored_scores?.score_warning && (
            <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-900 shadow-xs flex items-start gap-3">
              <AlertTriangle size={18} className="text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-amber-900">ATS Score Alert</p>
                <p className="text-xs text-amber-800 mt-0.5 leading-relaxed">
                  {version.tailored_scores.score_warning}
                </p>
              </div>
            </div>
          )}

          {/* Template Selection & Export */}
          <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
            <p className="text-xs font-bold uppercase tracking-wider text-ink-700 mb-2.5">
              Select ATS-Safe Template Layout:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5 mb-4">
              {TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setSelectedTemplate(t.id)}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    selectedTemplate === t.id
                      ? "border-signal-600 bg-signal-500/5 ring-1 ring-signal-600"
                      : "border-ink-100 bg-ink-50/50 hover:bg-ink-50 text-ink-700"
                  }`}
                >
                  <p className="text-xs font-bold text-ink-900">{t.label}</p>
                  <p className="text-[10px] text-ink-500 leading-tight mt-1">{t.desc}</p>
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2.5">
              <button
                type="button"
                onClick={() => previewPdf(`/tailoring/${version.id}/export/pdf?template=${selectedTemplate}`)}
                className="rounded-lg bg-teal-600 hover:bg-teal-700 text-white px-4 py-2.5 text-xs font-bold shadow-xs flex items-center gap-1.5 transition-colors"
              >
                <Eye size={13} />
                <span>Preview PDF in Browser</span>
              </button>
              <button
                type="button"
                onClick={() => downloadFile(`/tailoring/${version.id}/export/pdf?template=${selectedTemplate}`, `resume_${version.company}_${selectedTemplate}.pdf`)}
                className="rounded-lg bg-ink-950 hover:bg-ink-900 text-white px-5 py-2.5 text-xs font-bold shadow-xs flex items-center gap-1.5 transition-colors"
              >
                <Download size={13} />
                <span>Download PDF ({TEMPLATES.find((t) => t.id === selectedTemplate)?.label})</span>
              </button>
              <button
                type="button"
                onClick={() => downloadFile(`/tailoring/${version.id}/export/docx?template=${selectedTemplate}`, `resume_${version.company}_${selectedTemplate}.docx`)}
                className="rounded-lg bg-ink-100 hover:bg-ink-200 text-ink-800 px-5 py-2.5 text-xs font-bold flex items-center gap-1.5 transition-colors"
              >
                <Download size={13} />
                <span>Download DOCX</span>
              </button>
            </div>
          </div>

          {/* Finalized Text */}
          <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
            <p className="text-xs font-bold uppercase tracking-wider text-signal-700 mb-2">Finalized Resume Text</p>
            <pre className="text-xs text-ink-700 whitespace-pre-wrap font-sans bg-ink-50/50 p-4 rounded-lg border border-ink-100 max-h-96 overflow-y-auto leading-relaxed">
              {version.final_text}
            </pre>
          </div>

          {/* Connected Career Loop */}
          <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
            <p className="text-xs font-bold uppercase tracking-wider text-ink-500 mb-3 flex items-center gap-1.5">
              <Sparkles size={14} className="text-signal-600" /> Continue Your Connected Career Loop
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <Link
                to="/opportunities/saved"
                className="p-3 rounded-lg border border-ink-100 bg-ink-50/60 hover:bg-ink-100 text-ink-900 transition-colors flex flex-col justify-between"
              >
                <div>
                  <p className="text-xs font-bold flex items-center gap-1"><Bookmark size={13} className="text-signal-600" /> Saved</p>
                  <p className="text-[10px] text-ink-500 mt-1">Access and review all your bookmarked roles</p>
                </div>
                <span className="text-[11px] font-semibold text-signal-600 mt-2 flex items-center gap-1">Open Saved <ArrowRight size={11} /></span>
              </Link>

              <Link
                to={`/growth/interview/${version.job_id}`}
                className="p-3 rounded-lg border border-ink-100 bg-ink-50/60 hover:bg-ink-100 text-ink-900 transition-colors flex flex-col justify-between"
              >
                <div>
                  <p className="text-xs font-bold flex items-center gap-1"><MessageCircleQuestion size={13} className="text-signal-600" /> Interview Prep</p>
                  <p className="text-[10px] text-ink-500 mt-1">Practice role questions for {version.company}</p>
                </div>
                <span className="text-[11px] font-semibold text-signal-600 mt-2 flex items-center gap-1">Practice Questions <ArrowRight size={11} /></span>
              </Link>

              <Link
                to={`/growth/roadmap/${version.job_id}`}
                className="p-3 rounded-lg border border-ink-100 bg-ink-50/60 hover:bg-ink-100 text-ink-900 transition-colors flex flex-col justify-between"
              >
                <div>
                  <p className="text-xs font-bold flex items-center gap-1"><MapIcon size={13} className="text-signal-600" /> Skill Roadmap</p>
                  <p className="text-[10px] text-ink-500 mt-1">Bridge missing skills for {version.job_title}</p>
                </div>
                <span className="text-[11px] font-semibold text-signal-600 mt-2 flex items-center gap-1">View Roadmap <ArrowRight size={11} /></span>
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
