import { useState, useEffect } from "react";
import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ShieldCheck,
  Download,
  AlertTriangle,
  Trash2,
  FileCheck2,
  CheckCircle2,
  XCircle,
  Eye,
  Layers,
  Award,
  Edit3,
  Save,
  Check,
  RefreshCw,
  Info,
  ExternalLink,
} from "lucide-react";
import { apiClient } from "../../lib/apiClient";
import { recordApplicationSubmission } from "../../lib/applications";
import {
  generateTailoring,
  getTailoredVersion,
  getTailoredVersionForJob,
  finalizeTailoring,
  deleteTailoredVersion,
  updateChangeStatus,
  updateParsedResume,
  getEvidenceBadge,
  getRequirementStatusInfo,
} from "../../lib/tailoring";
import { ResumeDiffModal } from "../../components/resume/ResumeDiffModal";
import { ResumePreviewModal } from "../../components/resume/ResumePreviewModal";
import { useToast } from "../../context/ToastContext";

const TEMPLATES = [
  { id: "modern", label: "Modern Teal", desc: "Clean single-column with elegant signal accents." },
  { id: "classic", label: "Classic ATS Monochrome", desc: "Traditional monochrome layout for strict corporate ATS." },
  { id: "executive", label: "Tech Executive", desc: "High-density formatting with deep executive headers." },
  { id: "harvard", label: "Harvard Academic", desc: "Classic ivy-league serif styling with clean dividers." },
];

export function TailorReview() {
  const { jobId, versionId: routeVersionId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { success: toastSuccess, error: toastError, info: toastInfo } = useToast();

  const [activeTab, setActiveTab] = useState<"alignment" | "changes" | "editor" | "ats">("alignment");
  const [reqFilter, setReqFilter] = useState<"ALL" | "DIRECT_STRONG" | "SUPPORTED" | "PARTIAL_RELATED" | "MISSING">("ALL");
  const versionQuery = searchParams.get("version") || searchParams.get("versionId");
  const effectiveVersionId = routeVersionId || versionQuery || null;
  const effectiveJobId = jobId || searchParams.get("jobId") || null;

  const [selectedTemplate, setSelectedTemplate] = useState<string>("modern");
  const [isDiffOpen, setIsDiffOpen] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [activeVersionId, setActiveVersionId] = useState<string | null>(effectiveVersionId);

  // Editable Resume Local State
  const [isEditing, setIsEditing] = useState(false);
  const [editableSummary, setEditableSummary] = useState("");
  const [editableSkillsRaw, setEditableSkillsRaw] = useState("");

  // Check if an existing version already exists for this job before triggering a new generation
  const { data: existingJobVersion, isLoading: isCheckingJob } = useQuery({
    queryKey: ["tailored-version-for-job", effectiveJobId],
    queryFn: () => getTailoredVersionForJob(effectiveJobId!),
    enabled: !!effectiveJobId && !effectiveVersionId && !activeVersionId,
    retry: false,
  });

  // 1. Generation Mutation (if coming directly from Job Page with jobId and no versionId)
  const generateMutation = useMutation({
    mutationFn: (jId: string) => generateTailoring(jId),
    onSuccess: (data) => {
      setActiveVersionId(data.id);
      queryClient.setQueryData(["tailored-version", data.id], data);
      toastSuccess("Grounded resume tailoring ready for review.", "Tailoring Complete");
    },
    onError: (err: any) => {
      toastError(
        err.response?.data?.detail || "Could not generate tailored resume.",
        "Tailoring Failed"
      );
    },
  });

  useEffect(() => {
    if (effectiveVersionId) {
      setActiveVersionId(effectiveVersionId);
    } else if (existingJobVersion?.id) {
      setActiveVersionId(existingJobVersion.id);
    } else if (
      effectiveJobId &&
      !activeVersionId &&
      !isCheckingJob &&
      existingJobVersion === null &&
      !generateMutation.isPending &&
      !generateMutation.isSuccess
    ) {
      generateMutation.mutate(effectiveJobId);
    }
  }, [effectiveVersionId, effectiveJobId, existingJobVersion, isCheckingJob]);

  // 2. Fetch Version Data
  const { data: version, isLoading } = useQuery({
    queryKey: ["tailored-version", activeVersionId],
    queryFn: () => getTailoredVersion(activeVersionId!),
    enabled: !!activeVersionId,
  });

  // Synchronize local editable resume state
  useEffect(() => {
    if (version?.parsed) {
      setEditableSummary(version.parsed.summary || "");
      const skills = version.parsed.skills || [];
      setEditableSkillsRaw(skills.join(", "));
    }
  }, [version?.parsed]);

  const [showApplyModal, setShowApplyModal] = useState(false);

  const effectiveTargetJobId = version?.job_id || effectiveJobId || existingJobVersion?.job_id;
  const { data: jobData } = useQuery({
    queryKey: ["job-detail", effectiveTargetJobId],
    queryFn: () => apiClient.get(`/jobs/${effectiveTargetJobId}`).then((r) => r.data),
    enabled: !!effectiveTargetJobId && !effectiveTargetJobId.startsWith("custom-"),
  });

  const directApplyUrl = (jobData?.is_direct_apply && jobData?.apply_url && !jobData.apply_url.includes("example.com"))
    ? jobData.apply_url
    : null;

  const recordAppliedMutation = useMutation({
    mutationFn: () => recordApplicationSubmission(effectiveTargetJobId!, activeVersionId || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setShowApplyModal(false);
      toastSuccess("Application persisted as APPLIED in your Application Tracker.", "Application Submitted");
    },
    onError: () => {
      toastError("Could not record application status.", "Update Error");
    },
  });

  const handleApplyDirectly = () => {
    if (!directApplyUrl) return;
    window.open(directApplyUrl, "_blank", "noopener,noreferrer");
    setShowApplyModal(true);
  };

  // 3. Status Mutation
  const changeStatusMutation = useMutation({
    mutationFn: ({ changeId, status }: { changeId: string; status: "APPROVED" | "REJECTED" }) =>
      updateChangeStatus(activeVersionId!, changeId, status),
    onSuccess: (updated) => {
      queryClient.setQueryData(["tailored-version", activeVersionId], updated);
      toastSuccess("Change preference saved.", "Status Updated");
    },
    onError: (err: any) => {
      toastError(
        err.response?.data?.detail || "Could not update change status.",
        "Update Failed"
      );
    },
  });

  // 4. Save Editable Resume Mutation
  const saveResumeMutation = useMutation({
    mutationFn: (newParsed: Record<string, any>) => updateParsedResume(activeVersionId!, newParsed),
    onSuccess: (updated) => {
      queryClient.setQueryData(["tailored-version", activeVersionId], updated);
      setIsEditing(false);
      toastSuccess("Your manual edits have been updated.", "Resume Saved");
    },
    onError: (err: any) => {
      toastError(
        err.response?.data?.detail || "Could not save resume edits.",
        "Save Failed"
      );
    },
  });

  // 5. Finalize Mutation
  const finalizeMutation = useMutation({
    mutationFn: () => finalizeTailoring(activeVersionId!),
    onSuccess: (updated) => {
      queryClient.setQueryData(["tailored-version", activeVersionId], updated);
      toastSuccess("Resume is finalized and verified for export.", "Resume Finalized");
    },
    onError: (err: any) => {
      toastError(
        err.response?.data?.detail || "Could not finalize resume.",
        "Finalization Failed"
      );
    },
  });

  // 6. Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: () => deleteTailoredVersion(activeVersionId!),
    onSuccess: () => {
      toastInfo("Tailored draft deleted.", "Version Deleted");
      navigate("/resume/versions");
    },
  });

  const handleSaveEditor = () => {
    if (!version?.parsed) return;
    const skillsList = editableSkillsRaw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const updatedParsed = {
      ...version.parsed,
      summary: editableSummary,
      skills: skillsList,
    };
    saveResumeMutation.mutate(updatedParsed);
  };

  const handleApproveAll = async () => {
    if (!version) return;
    for (const change of version.changes) {
      if (change.status === "PENDING") {
        await changeStatusMutation.mutateAsync({ changeId: change.change_id, status: "APPROVED" });
      }
    }
    toastSuccess("All verified changes approved.", "All Approved");
  };

  const handleDownload = async (format: "pdf" | "docx") => {
    if (!activeVersionId) return;
    try {
      const token = localStorage.getItem("roleradar_token") || sessionStorage.getItem("roleradar_token");
      const res = await fetch(`/api/tailoring/${activeVersionId}/export/${format}?template=${selectedTemplate}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`Export failed: ${res.statusText}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume_${version?.company || "custom"}_${selectedTemplate}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toastSuccess(`Downloaded ${format.toUpperCase()} successfully.`, "Export Complete");
    } catch (err: any) {
      toastError(err.message || "Failed to download resume file.", "Export Error");
    }
  };

  if (isLoading || generateMutation.isPending) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <RefreshCw className="w-8 h-8 text-signal-500 animate-spin" />
        <div className="text-center">
          <h2 className="text-lg font-bold text-ink-900">Tailoring Your Resume for This Role</h2>
          <p className="text-xs text-ink-500 max-w-sm mt-1">
            Analyzing job requirements, aligning your verified experience, and checking that proposed content stays grounded in your experience…
          </p>
        </div>
      </div>
    );
  }

  if (!version) {
    return (
      <div className="rounded-xl border border-ink-100 bg-white p-8 text-center max-w-lg mx-auto mt-12">
        <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-3" />
        <h2 className="text-base font-bold text-ink-900">No Tailored Resume Found</h2>
        <p className="text-xs text-ink-500 mt-1 mb-4">Please select a job to begin evidence-grounded tailoring.</p>
        <Link to="/opportunities/jobs" className="inline-flex items-center gap-2 px-4 py-2 bg-ink-900 text-white rounded-lg text-xs font-semibold">
          Browse Opportunities
        </Link>
      </div>
    );
  }

  const classification = version.candidate_classification;
  const strategy = version.resume_strategy;
  const mappings = version.evidence_mapping || [];
  const changes = version.changes || [];
  const needsConfirmationChanges = changes.filter((c) => c.status === "NEEDS_USER_INPUT");
  const pendingChanges = changes.filter((c) => c.status === "PENDING");
  const atsFindings = version.ats_readability_findings;

  const filteredMappings = mappings.filter((m) => {
    if (reqFilter === "ALL") return true;
    if (reqFilter === "DIRECT_STRONG") return m.status === "EXACT_MATCH" || m.status === "STRONG_MATCH";
    if (reqFilter === "SUPPORTED") return m.status === "SUPPORTED";
    if (reqFilter === "PARTIAL_RELATED") return m.status === "PARTIAL" || m.status === "RELATED" || m.status === "WEAK";
    if (reqFilter === "MISSING") return m.status === "MISSING" || m.status === "CONFLICTING";
    return true;
  });

  const evidenceBadge = getEvidenceBadge(version);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* 1. Header Banner & Disclaimers */}
      <div className="rounded-2xl border border-ink-100 bg-white p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border flex items-center gap-1.5 ${evidenceBadge.style}`}>
                {evidenceBadge.iconType === "alert" && <AlertTriangle size={12} className="shrink-0" />}
                {evidenceBadge.iconType === "edit" && <Edit3 size={12} className="shrink-0" />}
                {evidenceBadge.iconType === "check" && <CheckCircle2 size={12} className="shrink-0" />}
                {evidenceBadge.iconType === "info" && <Info size={12} className="shrink-0" />}
                <span>{evidenceBadge.label}</span>
              </span>
              {version.is_finalized && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-ink-900 text-white flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-signal-400" /> Finalized
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold text-ink-900 mt-2 font-display">
              {version.job_title} <span className="text-ink-400 font-normal">at</span> {version.company}
            </h1>
            <p className="text-xs text-ink-500 mt-1 max-w-2xl">
              Targeted resume transformation with strict anti-fabrication truth guard, ATS format validation, and explicit candidate evidence mapping.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setIsPreviewOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-ink-200 bg-white hover:bg-ink-50 text-xs font-semibold text-ink-800 shadow-2xs hover:border-signal-500 transition-colors"
            >
              <Eye className="w-3.5 h-3.5 text-signal-600" /> Live Preview
            </button>
            <button
              onClick={() => setIsDiffOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-ink-200 text-xs font-semibold text-ink-700 hover:bg-ink-50"
            >
              <Layers className="w-3.5 h-3.5" /> Full Diff
            </button>
            {pendingChanges.length > 0 && (
              <button
                onClick={handleApproveAll}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-signal-600 text-white text-xs font-semibold hover:bg-signal-700 shadow-xs"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Approve All ({pendingChanges.length})
              </button>
            )}
            <button
              onClick={() => finalizeMutation.mutate()}
              disabled={finalizeMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-ink-900 text-white text-xs font-semibold hover:bg-ink-800 shadow-xs disabled:opacity-50"
            >
              <FileCheck2 className="w-3.5 h-3.5 text-signal-400" />
              {finalizeMutation.isPending
                ? "Finalizing Resume…"
                : version.is_finalized
                ? "Re-Finalize"
                : "Finalize Resume"}
            </button>
            <button
              onClick={() => {
                if (window.confirm("Are you sure you want to delete this tailored draft?")) {
                  deleteMutation.mutate();
                }
              }}
              disabled={deleteMutation.isPending}
              title="Delete this tailored draft"
              className="p-2 rounded-lg border border-ink-200 text-ink-400 hover:text-alert-600 hover:bg-alert-50 hover:border-alert-200 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Ethical System Notice */}
        <div className="mt-4 pt-3 border-t border-ink-100 flex items-start gap-2 text-[11px] text-ink-500">
          <Info className="w-4 h-4 text-ink-400 shrink-0 mt-0.5" />
          <span>
            <strong>RoleRadar Guarantee Notice:</strong> We guarantee factual accuracy against your uploaded master resume and ATS layout compliance.
            We do not claim guaranteed shortlisting or automatic hiring outcomes, as hiring decisions remain with human recruiters.
          </span>
        </div>
      </div>

      {/* 2. Top Intelligence Grid (Analysis, Classification, Strategy) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Resume Analysis */}
        <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="w-4 h-4 text-signal-600" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-ink-600">1. Resume Analysis</h3>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-ink-50">
              <span className="text-ink-500">Candidate Name</span>
              <span className="font-semibold text-ink-900">{version.parsed?.personal?.name || "Verified Candidate"}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-ink-50">
              <span className="text-ink-500">Verified Skills Count</span>
              <span className="font-semibold text-ink-900">{version.parsed?.skills?.length || 0} skills</span>
            </div>
            <div className="flex justify-between py-1 border-b border-ink-50">
              <span className="text-ink-500">Work Experience Entries</span>
              <span className="font-semibold text-ink-900">{version.parsed?.experience_raw?.length || 0} items</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-ink-500">Projects Count</span>
              <span className="font-semibold text-ink-900">{version.parsed?.projects_raw?.length || 0} items</span>
            </div>
          </div>
        </div>

        {/* Card 2: Candidate Classification */}
        <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <Award className="w-4 h-4 text-signal-600" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-ink-600">2. Candidate Classification</h3>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between py-1 border-b border-ink-50">
              <span className="text-ink-500">Experience Tier</span>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-signal-500/10 text-signal-700">
                {classification?.classification || "PROFESSIONAL"}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-ink-50">
              <span className="text-ink-500">Experience Level</span>
              <span className="font-semibold text-ink-900">{classification?.experience_level || "MID"}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-ink-50">
              <span className="text-ink-500">Project Depth</span>
              <span className="font-semibold text-ink-900">{classification?.project_depth || "STANDARD"}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-ink-500">Career Continuity</span>
              <span className="font-semibold text-ink-900">{classification?.career_continuity || "CONTINUOUS"}</span>
            </div>
          </div>
        </div>

        {/* Card 3: Recommended Strategy */}
        <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <Layers className="w-4 h-4 text-signal-600" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-ink-600">3. Recommended Strategy</h3>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between py-1 border-b border-ink-50">
              <span className="text-ink-500">Layout Strategy</span>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-ink-100 text-ink-800">
                {strategy?.candidate_type || "BALANCED_CHRONOLOGY"}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-ink-50">
              <span className="text-ink-500">Education Placement</span>
              <span className="font-semibold text-ink-900">
                {strategy?.highlight_education_top ? "Top (Fresher/Student)" : "Standard (Bottom)"}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-ink-50">
              <span className="text-ink-500">Recommended Template</span>
              <span className="font-semibold text-ink-900 capitalize">{strategy?.template_variant || "Modern"}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-ink-500">Recommended Length</span>
              <span className="font-semibold text-ink-900">{strategy?.recommended_length_pages || 1} Page</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-ink-200">
        <button
          onClick={() => setActiveTab("alignment")}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 transition-colors ${
            activeTab === "alignment"
              ? "border-signal-600 text-signal-700 bg-signal-500/5"
              : "border-transparent text-ink-500 hover:text-ink-800"
          }`}
        >
          4. JD Alignment & Requirement Mapping ({mappings.length})
        </button>
        <button
          onClick={() => setActiveTab("changes")}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "changes"
              ? "border-signal-600 text-signal-700 bg-signal-500/5"
              : "border-transparent text-ink-500 hover:text-ink-800"
          }`}
        >
          8. Changes Made ({changes.length})
          {needsConfirmationChanges.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] font-extrabold bg-amber-500 text-white">
              {needsConfirmationChanges.length} Alert
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("editor")}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "editor"
              ? "border-signal-600 text-signal-700 bg-signal-500/5"
              : "border-transparent text-ink-500 hover:text-ink-800"
          }`}
        >
          <Edit3 className="w-3.5 h-3.5" /> 10. Final Editable Resume
        </button>
        <button
          onClick={() => setActiveTab("ats")}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 transition-colors ${
            activeTab === "ats"
              ? "border-signal-600 text-signal-700 bg-signal-500/5"
              : "border-transparent text-ink-500 hover:text-ink-800"
          }`}
        >
          11. ATS & Readability Findings
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: JD ALIGNMENT & REQUIREMENT MAPPING                                 */}
      {/* ========================================================================= */}
      {activeTab === "alignment" && (
        <div className="space-y-4">
          {/* Explanatory Header & Legend */}
          <div className="rounded-xl border border-ink-100 bg-white p-4 shadow-xs space-y-3">
            <div>
              <h3 className="text-sm font-bold text-ink-900 font-display">Job Requirement Alignment</h3>
              <p className="text-xs text-ink-500 mt-0.5">
                See how your experience and skills align with each job requirement.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 pt-2 border-t border-ink-100 text-[11px]">
              <div className="flex items-start gap-1.5">
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-signal-500/10 text-signal-700 border border-signal-500/20 shrink-0">Direct Match</span>
                <span className="text-ink-500">Backed by direct work experience or project evidence.</span>
              </div>
              <div className="flex items-start gap-1.5">
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-700 border border-emerald-500/20 shrink-0">Strong Match</span>
                <span className="text-ink-500">Matches a closely related or equivalent technology.</span>
              </div>
              <div className="flex items-start gap-1.5">
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-teal-500/10 text-teal-700 border border-teal-500/20 shrink-0">Supported</span>
                <span className="text-ink-500">Backed by listed skills or academic coursework.</span>
              </div>
              <div className="flex items-start gap-1.5">
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-500/10 text-amber-700 border border-amber-500/20 shrink-0">Partial</span>
                <span className="text-ink-500">Only part of the requirement is supported.</span>
              </div>
              <div className="flex items-start gap-1.5">
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-500/10 text-amber-700 border border-amber-500/20 shrink-0">Related</span>
                <span className="text-ink-500">Your background includes adjacent or related skills.</span>
              </div>
              <div className="flex items-start gap-1.5">
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-alert-500/10 text-alert-700 border border-alert-500/20 shrink-0">Missing</span>
                <span className="text-ink-500">No supporting evidence found in your source resume.</span>
              </div>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span className="font-semibold text-ink-500 mr-1">Filter Support Level:</span>
            {[
              { id: "ALL", label: `All (${mappings.length})` },
              {
                id: "DIRECT_STRONG",
                label: `Direct & Strong (${mappings.filter((m) => m.status === "EXACT_MATCH" || m.status === "STRONG_MATCH").length})`,
                color: "bg-signal-500/10 text-signal-700",
              },
              {
                id: "SUPPORTED",
                label: `Supported (${mappings.filter((m) => m.status === "SUPPORTED").length})`,
                color: "bg-teal-500/10 text-teal-700",
              },
              {
                id: "PARTIAL_RELATED",
                label: `Partial / Related (${mappings.filter((m) => m.status === "PARTIAL" || m.status === "RELATED" || m.status === "WEAK").length})`,
                color: "bg-amber-500/10 text-amber-700",
              },
              {
                id: "MISSING",
                label: `Missing (${mappings.filter((m) => m.status === "MISSING" || m.status === "CONFLICTING").length})`,
                color: "bg-alert-500/10 text-alert-700",
              },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setReqFilter(f.id as any)}
                className={`px-3 py-1 rounded-full text-xs font-bold transition-colors ${
                  reqFilter === f.id ? "bg-ink-900 text-white" : f.color || "bg-ink-100 text-ink-700 hover:bg-ink-200"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Mappings List */}
          <div className="rounded-xl border border-ink-100 bg-white overflow-hidden shadow-xs divide-y divide-ink-100">
            {filteredMappings.length === 0 ? (
              <div className="p-8 text-center text-xs text-ink-400">No requirements match the selected filter.</div>
            ) : (
              filteredMappings.map((m, idx) => {
                const statusInfo = getRequirementStatusInfo(m.status);
                return (
                  <div key={idx} className="p-4 hover:bg-ink-50/50 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="space-y-1 max-w-3xl">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-ink-100 text-ink-600 font-bold">
                          {m.category || "REQUIREMENT"}
                        </span>
                        <p className="text-xs font-semibold text-ink-900">{m.requirement_text}</p>
                      </div>
                      {m.notes && <p className="text-[11px] text-ink-500 italic pl-2 border-l-2 border-ink-200">{m.notes}</p>}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${statusInfo.style}`}
                      >
                        {statusInfo.label}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: CHANGES MADE & CONFIRMATION AUDIT                                  */}
      {/* ========================================================================= */}
      {activeTab === "changes" && (
        <div className="space-y-6">
          {/* Section A: Needs Confirmation Alerts (9. Evidence Requiring Confirmation) */}
          {needsConfirmationChanges.length > 0 && (
            <div className="rounded-xl border border-amber-300 bg-amber-50/50 p-5 space-y-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                <div>
                  <h3 className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                    9. Evidence Requiring Candidate Confirmation ({needsConfirmationChanges.length})
                  </h3>
                  <p className="text-xs text-amber-700">
                    Truth Guard detected terms or claims not verified in your source resume. These changes cannot be auto-approved.
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                {needsConfirmationChanges.map((c) => (
                  <div key={c.change_id} className="rounded-lg border border-amber-200 bg-white p-4 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-amber-800 uppercase text-[10px] bg-amber-100 px-2 py-0.5 rounded">
                        NEEDS CONFIRMATION • {c.section}
                      </span>
                      <span className="text-ink-400 font-mono text-[10px]">ID: {c.change_id}</span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="p-2.5 rounded bg-ink-50 border border-ink-100">
                        <p className="text-[10px] font-bold text-ink-500 uppercase mb-1">Source Original:</p>
                        <p className="text-ink-700">{c.original || "(None / Skill Addition)"}</p>
                      </div>
                      <div className="p-2.5 rounded bg-amber-500/5 border border-amber-200">
                        <p className="text-[10px] font-bold text-amber-800 uppercase mb-1">Proposed Rewrite:</p>
                        <p className="text-amber-950 font-medium">{c.proposed}</p>
                      </div>
                    </div>

                    {c.fabrication_warning && (
                      <p className="text-xs text-alert-700 font-medium flex items-start gap-1.5">
                        <span>⚠️</span> <span>{c.fabrication_warning}</span>
                      </p>
                    )}

                    <div className="flex justify-end gap-2 pt-2 border-t border-ink-100">
                      <button
                        onClick={() => changeStatusMutation.mutate({ changeId: c.change_id, status: "REJECTED" })}
                        className="px-3 py-1.5 rounded text-xs font-semibold bg-ink-100 text-ink-700 hover:bg-ink-200"
                      >
                        Keep Original (Reject)
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section B: All Tailoring Changes (8. Changes Made) */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-ink-600">8. Proposed Transformations & Improvements</h3>
            {changes.map((c) => (
              <div key={c.change_id} className="rounded-xl border border-ink-100 bg-white p-4 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-ink-100 text-ink-700">
                      {c.section}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        c.status === "APPROVED"
                          ? "bg-signal-500/10 text-signal-700"
                          : c.status === "REJECTED"
                          ? "bg-alert-500/10 text-alert-700"
                          : c.status === "NEEDS_USER_INPUT"
                          ? "bg-amber-500/10 text-amber-700"
                          : "bg-ink-100 text-ink-600"
                      }`}
                    >
                      {c.status === "NEEDS_USER_INPUT" ? "NEEDS CONFIRMATION" : c.status}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {c.status !== "NEEDS_USER_INPUT" && (
                      <>
                        <button
                          onClick={() => changeStatusMutation.mutate({ changeId: c.change_id, status: "APPROVED" })}
                          className={`px-2.5 py-1 rounded text-xs font-bold flex items-center gap-1 ${
                            c.status === "APPROVED" ? "bg-signal-600 text-white" : "bg-ink-50 text-ink-600 hover:bg-signal-50 hover:text-signal-700"
                          }`}
                        >
                          <Check className="w-3 h-3" /> Approve
                        </button>
                        <button
                          onClick={() => changeStatusMutation.mutate({ changeId: c.change_id, status: "REJECTED" })}
                          className={`px-2.5 py-1 rounded text-xs font-bold flex items-center gap-1 ${
                            c.status === "REJECTED" ? "bg-alert-600 text-white" : "bg-ink-50 text-ink-600 hover:bg-alert-50 hover:text-alert-700"
                          }`}
                        >
                          <XCircle className="w-3 h-3" /> Reject
                        </button>
                      </>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-lg bg-ink-50/70 border border-ink-100">
                    <p className="text-[10px] font-bold text-ink-400 uppercase mb-1">Original Content:</p>
                    <p className="text-ink-700">{c.original || "(New Addition)"}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-signal-500/5 border border-signal-500/20">
                    <p className="text-[10px] font-bold text-signal-700 uppercase mb-1">Tailored Proposal:</p>
                    <p className="text-ink-900 font-medium">{c.proposed}</p>
                  </div>
                </div>

                {c.reason && (
                  <div className="p-2.5 rounded bg-ink-50/50 border border-ink-100 text-[11px] text-ink-600">
                    <strong>Why this change was made:</strong> {c.reason}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: FINAL EDITABLE RESUME (10. Final Editable Resume)                 */}
      {/* ========================================================================= */}
      {activeTab === "editor" && (
        <div className="rounded-xl border border-ink-100 bg-white p-6 shadow-xs space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-ink-100">
            <div>
              <h3 className="text-base font-bold text-ink-900 font-display">10. Final Editable Resume Preview</h3>
              <p className="text-xs text-ink-500">Edit any section directly before final PDF/DOCX rendering.</p>
            </div>

            <div className="flex items-center gap-2">
              {!isEditing ? (
                <button
                  onClick={() => setIsEditing(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-ink-900 text-white text-xs font-semibold hover:bg-ink-800"
                >
                  <Edit3 className="w-3.5 h-3.5" /> Edit Resume
                </button>
              ) : (
                <button
                  onClick={handleSaveEditor}
                  disabled={saveResumeMutation.isPending}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-signal-600 text-white text-xs font-semibold hover:bg-signal-700 shadow-xs disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" />
                  {saveResumeMutation.isPending ? "Saving Edits…" : "Save Changes"}
                </button>
              )}
            </div>
          </div>

          {/* Section: Personal Info */}
          <div className="space-y-1">
            <h4 className="text-xs font-bold uppercase text-ink-400">Header & Contact (Protected)</h4>
            <div className="p-3 rounded-lg bg-ink-50 border border-ink-100 text-xs text-ink-700">
              <p className="font-bold text-ink-900 text-sm">{version.parsed?.personal?.name || "Candidate Name"}</p>
              <p className="text-ink-500">
                {version.parsed?.personal?.email} • {version.parsed?.personal?.location || "Location Verified"}
              </p>
            </div>
          </div>

          {/* Section: Summary */}
          <div className="space-y-1.5">
            <h4 className="text-xs font-bold uppercase text-ink-400">Professional Summary</h4>
            {isEditing ? (
              <textarea
                value={editableSummary}
                onChange={(e) => setEditableSummary(e.target.value)}
                rows={3}
                className="w-full p-3 text-xs rounded-lg border border-ink-200 focus:border-signal-500 focus:outline-none"
              />
            ) : (
              <div className="p-3 rounded-lg bg-ink-50/50 border border-ink-100 text-xs leading-relaxed text-ink-800">
                {version.parsed?.summary || "No summary provided."}
              </div>
            )}
          </div>

          {/* Section: Technical Skills */}
          <div className="space-y-1.5">
            <h4 className="text-xs font-bold uppercase text-ink-400">Technical Skills</h4>
            {isEditing ? (
              <input
                type="text"
                value={editableSkillsRaw}
                onChange={(e) => setEditableSkillsRaw(e.target.value)}
                placeholder="Comma separated skills..."
                className="w-full p-3 text-xs rounded-lg border border-ink-200 focus:border-signal-500 focus:outline-none"
              />
            ) : (
              <div className="flex flex-wrap gap-1.5 p-3 rounded-lg bg-ink-50/50 border border-ink-100">
                {(version.parsed?.skills || []).map((sk: string, idx: number) => (
                  <span key={idx} className="px-2 py-0.5 rounded text-xs font-medium bg-white border border-ink-200 text-ink-800">
                    {sk}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Section: Experience */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase text-ink-400">Work Experience</h4>
            <div className="space-y-2">
              {(version.parsed?.experience_raw || []).map((exp: string, idx: number) => (
                <div key={idx} className="p-3 rounded-lg bg-ink-50/40 border border-ink-100 text-xs text-ink-800 leading-relaxed">
                  {exp}
                </div>
              ))}
            </div>
          </div>

          {/* Section: Projects */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase text-ink-400">Technical Projects</h4>
            <div className="space-y-2">
              {(version.parsed?.projects_raw || []).map((proj: any, idx: number) => (
                <div key={idx} className="p-3 rounded-lg bg-ink-50/40 border border-ink-100 text-xs text-ink-800 leading-relaxed">
                  {typeof proj === "string" ? proj : `${proj.title}: ${proj.bullets?.join(" ") || ""}`}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: ATS & READABILITY FINDINGS (11. ATS/Readability Findings)          */}
      {/* ========================================================================= */}
      {activeTab === "ats" && (
        <div className="rounded-xl border border-ink-100 bg-white p-6 shadow-xs space-y-6">
          <div className="flex items-start justify-between pb-4 border-b border-ink-100">
            <div>
              <h3 className="text-base font-bold text-ink-900 font-display">11. ATS & Readability Validation Report</h3>
              <p className="text-xs text-ink-500">
                Automated compliance checks across standard section headings, bullet formatting, date consistency, and ATS readability.
              </p>
            </div>
            <div className="text-right">
              <span className="text-3xl font-bold font-display text-signal-700">
                {atsFindings?.ats_format_validation?.overall_ats_score || 85}%
              </span>
              <p className="text-[10px] text-ink-400 uppercase font-bold">ATS Format Score</p>
            </div>
          </div>

          {/* Sub-Score Bars */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-ink-50 border border-ink-100 text-center">
              <p className="text-ink-500 text-[10px] uppercase font-bold">Standard Headings</p>
              <p className="text-lg font-bold text-ink-900">{atsFindings?.ats_format_validation?.standard_headings_score || 100}%</p>
            </div>
            <div className="p-3 rounded-lg bg-ink-50 border border-ink-100 text-center">
              <p className="text-ink-500 text-[10px] uppercase font-bold">Section Order</p>
              <p className="text-lg font-bold text-ink-900">{atsFindings?.ats_format_validation?.section_order_score || 100}%</p>
            </div>
            <div className="p-3 rounded-lg bg-ink-50 border border-ink-100 text-center">
              <p className="text-ink-500 text-[10px] uppercase font-bold">Bullet Quality</p>
              <p className="text-lg font-bold text-ink-900">{atsFindings?.ats_format_validation?.bullet_consistency_score || 95}%</p>
            </div>
            <div className="p-3 rounded-lg bg-ink-50 border border-ink-100 text-center">
              <p className="text-ink-500 text-[10px] uppercase font-bold">Date Consistency</p>
              <p className="text-lg font-bold text-ink-900">{atsFindings?.ats_format_validation?.date_consistency_score || 100}%</p>
            </div>
          </div>

          {/* Actionable Recommendations */}
          {atsFindings?.ats_format_validation?.actionable_recommendations && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-ink-600">Actionable ATS Recommendations:</h4>
              <ul className="space-y-1.5 text-xs text-ink-700">
                {atsFindings.ats_format_validation.actionable_recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-2 p-2.5 rounded bg-ink-50/50 border border-ink-100">
                    <CheckCircle2 className="w-4 h-4 text-signal-600 shrink-0 mt-0.5" />
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 12. EXPORT OPTIONS & TEMPLATE SELECTION                                  */}
      {/* ========================================================================= */}
      <div className="rounded-xl border border-ink-100 bg-white p-6 shadow-xs space-y-5">
        <div>
          <h3 className="text-base font-bold text-ink-900 font-display">12. Export Resume Options</h3>
          <p className="text-xs text-ink-500">Choose an ATS-safe template variant and download your tailored resume.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {TEMPLATES.map((t) => (
            <button
              key={t.id}
              onClick={() => setSelectedTemplate(t.id)}
              className={`p-3.5 rounded-xl border text-left transition-all ${
                selectedTemplate === t.id
                  ? "border-signal-600 bg-signal-500/5 shadow-xs ring-1 ring-signal-500"
                  : "border-ink-200 bg-white hover:border-ink-300"
              }`}
            >
              <p className="text-xs font-bold text-ink-900">{t.label}</p>
              <p className="text-[11px] text-ink-500 mt-1">{t.desc}</p>
            </button>
          ))}
        </div>

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-ink-100">
          <button
            onClick={() => setIsPreviewOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-signal-500/30 bg-signal-500/10 text-signal-800 text-xs font-bold hover:bg-signal-500/20 transition-colors shadow-2xs"
          >
            <Eye className="w-4 h-4 text-signal-600" /> Preview PDF
          </button>
          <button
            onClick={() => handleDownload("docx")}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-ink-200 bg-white text-ink-800 text-xs font-semibold hover:bg-ink-50"
          >
            <Download className="w-4 h-4 text-ink-500" /> Export DOCX
          </button>
          <button
            onClick={() => handleDownload("pdf")}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-signal-600 text-white text-xs font-bold hover:bg-signal-700 shadow-xs"
          >
            <Download className="w-4 h-4" /> Export PDF
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 13. DIRECT APPLY & APPLICATION CONTINUITY (P1-03)                        */}
      {/* ========================================================================= */}
      <div className="rounded-xl border border-signal-500/30 bg-gradient-to-br from-signal-500/5 via-white to-white p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1 rounded-md bg-signal-500/20 text-signal-800">
                <CheckCircle2 size={16} />
              </span>
              <h3 className="text-base font-bold text-ink-950 font-display">13. Next Step: Direct Application</h3>
            </div>
            <p className="text-xs text-ink-600">
              Your resume is finalized for <strong className="text-ink-900">{version.job_title} at {version.company}</strong>.
              Apply directly without needing to search for the job again.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {directApplyUrl ? (
              <button
                type="button"
                onClick={handleApplyDirectly}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-signal-600 hover:bg-signal-700 text-white text-xs font-bold shadow-xs transition-all active:scale-95"
              >
                <span>Apply Directly on {version.company} Portal</span>
                <ExternalLink size={14} />
              </button>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 text-xs font-medium">
                <AlertTriangle size={14} className="text-amber-600 shrink-0" />
                <span>Application link unavailable: RoleRadar cannot verify a direct application link.</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Direct Apply Confirmation Modal (P1-03) */}
      {showApplyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">
          <div className="w-full max-w-md rounded-2xl bg-white border border-ink-100 shadow-2xl p-6 space-y-4 animate-fade-in-up">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-signal-500/10 flex items-center justify-center text-signal-600 shrink-0">
                <CheckCircle2 size={22} />
              </div>
              <div>
                <h3 className="text-base font-bold font-display text-ink-950">
                  Mark as Submitted?
                </h3>
                <p className="text-xs text-ink-500">
                  {version.job_title} at {version.company}
                </p>
              </div>
            </div>

            <p className="text-xs text-ink-600 leading-relaxed">
              We opened the official application portal in a new tab. Once you complete and submit your application with this tailored resume, confirm below to mark it as <strong>APPLIED</strong> in your Application Tracker.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-ink-100">
              <button
                type="button"
                onClick={() => setShowApplyModal(false)}
                className="px-3.5 py-2 rounded-lg border border-ink-200 text-ink-700 text-xs font-medium hover:bg-ink-50"
              >
                I&apos;ll Mark Later
              </button>
              <button
                type="button"
                onClick={() => recordAppliedMutation.mutate()}
                disabled={recordAppliedMutation.isPending}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-signal-600 hover:bg-signal-700 text-white text-xs font-bold shadow-xs transition-colors disabled:opacity-50"
              >
                <Check size={14} />
                <span>{recordAppliedMutation.isPending ? "Persisting…" : "Yes, Mark as APPLIED"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {isPreviewOpen && activeVersionId && (
        <ResumePreviewModal
          isOpen={isPreviewOpen}
          onClose={() => setIsPreviewOpen(false)}
          versionId={activeVersionId}
          company={version.company}
          jobTitle={version.job_title}
          initialTemplate={selectedTemplate}
        />
      )}

      {/* Diff Modal */}
      {isDiffOpen && (
        <ResumeDiffModal
          isOpen={isDiffOpen}
          onClose={() => setIsDiffOpen(false)}
          version={version}
        />
      )}
    </div>
  );
}

export default TailorReview;

