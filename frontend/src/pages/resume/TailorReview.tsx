import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, ArrowRight, Kanban, MessageCircleQuestion, Map as MapIcon, Sparkles } from "lucide-react";
import {
  generateTailoring,
  getTailoredVersion,
  finalizeTailoring,
  updateChangeStatus,
  type Change,
} from "../../lib/tailoring";
import { getATSScore } from "../../lib/intelligence";
import { apiClient } from "../../lib/apiClient";
import { ResumeDiffModal } from "../../components/resume/ResumeDiffModal";

const STATUS_STYLE: Record<Change["status"], string> = {
  PENDING: "bg-ink-50 text-ink-500",
  APPROVED: "bg-signal-500/10 text-signal-600",
  REJECTED: "bg-alert-600/10 text-alert-600",
  NEEDS_USER_INPUT: "bg-amber-500/10 text-amber-600",
};

const ATS_PLATFORMS = [
  { id: "workday", label: "Workday" },
  { id: "greenhouse", label: "Greenhouse" },
  { id: "lever", label: "Lever" },
  { id: "taleo", label: "Oracle Taleo" },
  { id: "icims", label: "iCIMS" },
  { id: "generic", label: "Standard ATS" },
];

const TEMPLATES = [
  { id: "modern", label: "Modern Clean", desc: "Sleek sans-serif with subtle emerald accents" },
  { id: "classic", label: "Classic Executive", desc: "Traditional serif with centered formal headers" },
  { id: "technical", label: "Technical Minimal", desc: "High-density layout tailored for engineers" },
];

function ScoreRow({ label, value }: { label: string; value: number }) {
  const color = value >= 85 ? "text-signal-600" : value >= 70 ? "text-amber-600" : "text-alert-600";
  return (
    <div className="flex items-center justify-between py-1.5 text-xs">
      <span className="text-ink-600">{label}</span>
      <span className={`font-semibold ${color}`}>{value}/100</span>
    </div>
  );
}

function ATSScorePanel({ jobId }: { jobId: string }) {
  const [selectedPlatform, setSelectedPlatform] = useState<string>("workday");

  const { data: ats, isLoading } = useQuery({
    queryKey: ["ats-score", jobId, selectedPlatform],
    queryFn: () => getATSScore(jobId, selectedPlatform),
  });

  if (isLoading || !ats) {
    return <div className="rounded-lg border border-ink-100 bg-white p-4 mb-6 text-xs text-ink-500">Evaluating ATS compatibility…</div>;
  }

  const guidance = ats.match_guidance;
  const platform = ats.platform_compliance;

  return (
    <div className="rounded-xl border border-ink-100 bg-white p-5 mb-6 shadow-xs">
      {/* Header & Overall Score */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-ink-500 mb-0.5">
            ATS Compatibility Evaluation
          </p>
          <p className="text-xs text-ink-500">
            Target company system: <span className="font-semibold text-ink-800">{platform?.platform_name || "Enterprise ATS"}</span>
          </p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-display text-ink-900 font-bold">{ats.overall}%</span>
          <p className="text-[10px] text-ink-400">Match Score</p>
        </div>
      </div>

      {/* Ideal Match Range Framing */}
      <div className={`p-3 rounded-lg border mb-4 ${
        guidance?.status === "ideal"
          ? "bg-signal-500/10 border-signal-500/20 text-signal-800"
          : guidance?.status === "over_optimized"
          ? "bg-amber-500/10 border-amber-500/20 text-amber-800"
          : "bg-ink-50 border-ink-100 text-ink-800"
      }`}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-bold flex items-center gap-1.5">
            {guidance?.status === "ideal" ? "🎯 Ideal Match Zone (75%–85%)" : guidance?.label || "ATS Target Range"}
          </span>
          <span className="text-[11px] font-mono font-medium">Ideal: 75%–85%</span>
        </div>
        <p className="text-xs leading-relaxed opacity-90">{guidance?.message}</p>
        {ats.keyword_density !== undefined && (
          <div className="mt-2 pt-2 border-t border-black/5 flex items-center justify-between text-[11px]">
            <span>Keyword Density: <strong className={ats.over_optimization_warning ? "text-alert-600" : "text-ink-700"}>{ats.keyword_density}%</strong></span>
            <span className="text-ink-500">Workday safe limit: &lt;3.0% / 100 words</span>
          </div>
        )}
      </div>

      {/* Interactive Platform Selector */}
      <div className="mb-4">
        <label className="block text-[11px] font-semibold uppercase tracking-wider text-ink-500 mb-2">
          Select Hiring Platform:
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

      {/* Platform-Specific Warnings / Tips */}
      {platform && (
        <div className="mb-4 space-y-2">
          {platform.warnings.map((w, i) => (
            <div
              key={i}
              className={`p-2.5 rounded-md text-xs border ${
                w.severity === "high"
                  ? "bg-alert-600/10 border-alert-600/20 text-alert-700 font-medium"
                  : "bg-amber-500/10 border-amber-500/20 text-amber-800"
              }`}
            >
              <span className="font-bold block mb-0.5">⚠️ {w.title}</span>
              <p className="leading-tight opacity-90">{w.message}</p>
            </div>
          ))}
          {platform.tips.length > 0 && (
            <div className="bg-ink-50/70 p-2.5 rounded-md border border-ink-100/60">
              <p className="text-[11px] font-bold text-ink-700 uppercase mb-1">💡 {platform.platform_name} Best Practices:</p>
              <ul className="space-y-0.5 text-xs text-ink-600 list-disc list-inside">
                {platform.tips.map((t, idx) => (
                  <li key={idx}>{t}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Deterministic Sub-score Breakdown */}
      <div className="divide-y divide-ink-50 border-t border-ink-100 pt-2">
        <ScoreRow label="Keyword Coverage" value={ats.keyword_coverage} />
        <ScoreRow label="Required Skills Match" value={ats.required_skills} />
        <ScoreRow label="Role Alignment" value={ats.role_alignment} />
        <ScoreRow label="Document Structure" value={ats.structure} />
        <ScoreRow label="ATS Formatting" value={ats.formatting} />
        <ScoreRow label="Recruiter Readability" value={ats.readability} />
      </div>
    </div>
  );
}

async function downloadFile(url: string, filename: string) {
  const res = await apiClient.get(url, { responseType: "blob" });
  const blobUrl = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

function ChangeCard({ versionId, change, onUpdated }: { versionId: string; change: Change; onUpdated: () => void }) {
  const mutation = useMutation({
    mutationFn: (status: "APPROVED" | "REJECTED") => updateChangeStatus(versionId, change.change_id, status),
    onSuccess: onUpdated,
  });

  return (
    <div className="rounded-lg border border-ink-100 bg-white p-4">
      <div className="flex items-center justify-between mb-2">
        <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[change.status]}`}>
          {change.status.replace("_", " ")}
        </span>
        <span className="text-xs text-ink-500">confidence {Math.round(change.confidence * 100)}%</span>
      </div>

      {change.original && (
        <p className="text-sm text-ink-500 line-through mb-1">{change.original}</p>
      )}
      <div className="rounded-md bg-signal-500/5 border border-signal-500/20 p-2.5 mb-3">
        <span className="text-[11px] font-bold uppercase tracking-wider text-signal-700 flex items-center gap-1 mb-0.5">
          <ShieldCheck size={13} /> Verified Source Evidence:
        </span>
        <p className="text-xs text-ink-700 leading-relaxed font-mono">
          {change.source_evidence || "None provided — requires candidate confirmation."}
        </p>
      </div>

      <p className="text-xs text-ink-500 mb-3"><span className="font-medium text-ink-700">Why:</span> {change.reason}</p>

      {change.status !== "APPROVED" && change.status !== "REJECTED" && (
        <div className="flex gap-2">
          <button
            onClick={() => mutation.mutate("APPROVED")}
            disabled={mutation.isPending}
            className="rounded-md bg-signal-500 hover:bg-signal-600 text-white px-3 py-1.5 text-xs font-semibold disabled:opacity-60 shadow-xs"
          >
            Approve Change
          </button>
          <button
            onClick={() => mutation.mutate("REJECTED")}
            disabled={mutation.isPending}
            className="rounded-md bg-ink-100 hover:bg-ink-200 text-ink-700 px-3 py-1.5 text-xs font-semibold disabled:opacity-60"
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}

export function TailorReview() {
  const { jobId } = useParams<{ jobId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const existingVersionId = searchParams.get("version");
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

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
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "Generation failed."),
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
    },
  });

  function refresh() {
    if (activeVersionId) {
      queryClient.invalidateQueries({ queryKey: ["tailoring", activeVersionId] });
    }
  }

  const [selectedTemplate, setSelectedTemplate] = useState<string>("modern");

  if (!existingVersionId && !generate.data && !generate.isPending) {
    return (
      <div className="max-w-2xl">
        <h1 className="font-display text-2xl text-ink-900 mb-2">Tailor resume for this job</h1>
        <p className="text-ink-500 mb-6">
          RoleRadar will propose changes based only on your master resume — nothing invented. You review and approve each one.
        </p>
        {error && (
          <p className="mb-4 rounded-md bg-alert-600/10 px-3 py-2 text-sm text-alert-600">
            {error}
          </p>
        )}
        <button
          onClick={() => generate.mutate()}
          className="rounded-md bg-ink-950 hover:bg-ink-900 text-white px-4 py-2 text-sm font-medium"
        >
          Generate tailoring proposal
        </button>
      </div>
    );
  }

  if (generate.isPending || versionQuery.isLoading) {
    return <p className="text-ink-500">Generating tailoring proposal…</p>;
  }

  if (!version) return <p className="text-ink-500">Loading…</p>;

  const pendingCount = version.changes.filter((c) => c.status === "PENDING" || c.status === "NEEDS_USER_INPUT").length;

  return (
    <div className="max-w-2xl">
      <h1 className="font-display text-2xl text-ink-900 mb-1">
        {version.job_title} at {version.company}
      </h1>
      <p className="text-ink-500 mb-6">
        Review each proposed change. Only approved changes will appear in your final tailored resume.
      </p>

      <ATSScorePanel jobId={version.job_id} />

      <div className="flex items-center justify-between mb-3 mt-6">
        <h2 className="text-sm font-bold uppercase tracking-wider text-ink-700">
          Proposed Changes ({version.changes.length})
        </h2>
        <ResumeDiffModal version={version} />
      </div>

      <div className="space-y-3 mb-6">
        {version.changes.map((change) => (
          <ChangeCard key={change.change_id} versionId={version.id} change={change} onUpdated={refresh} />
        ))}
      </div>

      {!version.is_finalized ? (
        <button
          onClick={() => version.id && finalize.mutate(version.id)}
          disabled={finalize.isPending}
          className="rounded-md bg-signal-500 hover:bg-signal-600 text-white px-4 py-2 text-sm font-medium disabled:opacity-60"
        >
          {finalize.isPending ? "Finalizing…" : pendingCount > 0 ? `Finalize (${pendingCount} still pending — they'll be excluded)` : "Finalize tailored resume"}
        </button>
      ) : (
        <div className="space-y-4">
          <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
            <p className="text-xs font-bold uppercase tracking-wider text-ink-700 mb-2.5">
              Select ATS-Safe Template Layout:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 mb-4">
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
            <div className="flex gap-2">
              <button
                onClick={() => downloadFile(`/tailoring/${version.id}/export/pdf?template=${selectedTemplate}`, `resume_${version.company}_${selectedTemplate}.pdf`)}
                className="rounded-md bg-ink-950 hover:bg-ink-900 text-white px-4 py-2 text-xs font-semibold shadow-xs"
              >
                Download PDF ({TEMPLATES.find((t) => t.id === selectedTemplate)?.label})
              </button>
              <button
                onClick={() => downloadFile(`/tailoring/${version.id}/export/docx?template=${selectedTemplate}`, `resume_${version.company}_${selectedTemplate}.docx`)}
                className="rounded-md bg-ink-100 hover:bg-ink-200 text-ink-700 px-4 py-2 text-xs font-semibold"
              >
                Download DOCX
              </button>
            </div>
          </div>

          {/* Connected End-to-End Career Loop Actions */}
          <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
            <p className="text-xs font-bold uppercase tracking-wider text-ink-500 mb-3 flex items-center gap-1.5">
              <Sparkles size={14} className="text-signal-600" /> Continue Your Connected Career Loop
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <Link
                to="/applications/tracker"
                className="p-3 rounded-lg border border-ink-100 bg-ink-50/60 hover:bg-ink-100 text-ink-900 transition-colors flex flex-col justify-between"
              >
                <div>
                  <p className="text-xs font-bold flex items-center gap-1"><Kanban size={13} className="text-signal-600" /> Track Application</p>
                  <p className="text-[10px] text-ink-500 mt-1">Manage status in your CRM tracker pipeline</p>
                </div>
                <span className="text-[11px] font-semibold text-signal-600 mt-2 flex items-center gap-1">Open Tracker <ArrowRight size={11} /></span>
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

          <div className="rounded-lg border border-ink-100 bg-white p-5">
            <p className="text-xs font-medium uppercase tracking-wider text-signal-600 mb-2">Finalized Resume Text</p>
            <pre className="text-xs text-ink-700 whitespace-pre-wrap font-sans">{version.final_text}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
