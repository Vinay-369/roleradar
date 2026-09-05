import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import {
  ClipboardCheck,
  Building2,
  ExternalLink,
  Bot,
  MessageCircleQuestion,
  Trash2,
  Calendar,
  Clock,
  Sparkles,
  Search,
  FileText,
  AlertTriangle,
  Edit3,
  Check,
  X,
} from "lucide-react";
import {
  listApplications,
  deleteApplication,
  updateApplication,
  type Application,
  type ApplicationStatus,
} from "../../lib/applications";
import { useToast } from "../../context/ToastContext";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/SkeletonLoaders";

const ALL_STATUSES: { value: ApplicationStatus; label: string; color: string }[] = [
  { value: "SAVED", label: "Saved", color: "bg-ink-100 text-ink-700 border-ink-200" },
  { value: "TAILORED", label: "Tailored", color: "bg-indigo-50 text-indigo-700 border-indigo-200" },
  { value: "QUEUED", label: "Queued", color: "bg-purple-50 text-purple-700 border-purple-200" },
  { value: "APPLIED", label: "Applied", color: "bg-signal-50 text-signal-700 border-signal-200" },
  { value: "SHORTLISTED", label: "Shortlisted", color: "bg-sky-50 text-sky-700 border-sky-200" },
  { value: "INTERVIEW", label: "Interview", color: "bg-amber-50 text-amber-700 border-amber-200" },
  { value: "OFFER", label: "Offer", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  { value: "REJECTED", label: "Rejected", color: "bg-rose-50 text-rose-700 border-rose-200" },
  { value: "WITHDRAWN", label: "Withdrawn", color: "bg-zinc-100 text-zinc-600 border-zinc-200" },
];

function getStatusBadge(status: ApplicationStatus) {
  const match = ALL_STATUSES.find((s) => s.value === status) || {
    label: status,
    color: "bg-ink-100 text-ink-700 border-ink-200",
  };
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${match.color}`}
    >
      {match.label}
    </span>
  );
}

function formatDate(isoStr?: string) {
  if (!isoStr) return "N/A";
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return isoStr;
  }
}

export function Applications() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { data: applications, isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: listApplications,
  });

  const [searchParams, setSearchParams] = useSearchParams();
  const urlTab = searchParams.get("tab")?.toUpperCase();
  const initialTab: "ALL" | "SAVED" | "TAILORED" | "APPLIED" | "ARCHIVED" =
    urlTab === "SAVED" || urlTab === "TAILORED" || urlTab === "APPLIED" || urlTab === "ARCHIVED"
      ? urlTab
      : "ALL";

  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"ALL" | "SAVED" | "TAILORED" | "APPLIED" | "ARCHIVED">(initialTab);
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");

  const handleTabChange = (tab: "ALL" | "SAVED" | "TAILORED" | "APPLIED" | "ARCHIVED") => {
    setActiveTab(tab);
    if (tab === "ALL") {
      searchParams.delete("tab");
      setSearchParams(searchParams, { replace: true });
    } else {
      setSearchParams({ tab }, { replace: true });
    }
  };

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: { status?: ApplicationStatus; notes?: string } }) =>
      updateApplication(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Application updated.");
      setEditingNoteId(null);
    },
    onError: () => toast.error("Failed to update application."),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => deleteApplication(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.info("Application removed.");
    },
    onError: () => toast.error("Failed to delete application."),
  });

  const allApps = applications ?? [];
  const savedCount = allApps.filter((a) => a.status === "SAVED").length;
  const tailoredCount = allApps.filter((a) => a.status === "TAILORED" || a.status === "QUEUED").length;
  const appliedCount = allApps.filter((a) => a.status === "APPLIED" || a.status === "SHORTLISTED" || a.status === "INTERVIEW" || a.status === "OFFER").length;
  const archivedCount = allApps.filter((a) => a.status === "REJECTED" || a.status === "WITHDRAWN").length;

  const filteredApps = allApps.filter((app) => {
    // 1. Search Query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = app.job_title?.toLowerCase().includes(q);
      const matchCompany = app.company?.toLowerCase().includes(q);
      if (!matchTitle && !matchCompany) return false;
    }

    // 2. Status Tab Filter (Simplified User Flow: SAVED -> TAILORED -> APPLIED -> ARCHIVED)
    if (activeTab === "SAVED") {
      return app.status === "SAVED";
    }
    if (activeTab === "TAILORED") {
      return app.status === "TAILORED" || app.status === "QUEUED";
    }
    if (activeTab === "APPLIED") {
      return app.status === "APPLIED" || app.status === "SHORTLISTED" || app.status === "INTERVIEW" || app.status === "OFFER";
    }
    if (activeTab === "ARCHIVED") {
      return app.status === "REJECTED" || app.status === "WITHDRAWN";
    }

    return true;
  });

  const handleStartEditNote = (app: Application) => {
    setEditingNoteId(app.id);
    setNoteText(app.notes || "");
  };

  const handleSaveNote = (id: string) => {
    updateMutation.mutate({ id, updates: { notes: noteText } });
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 rounded-lg bg-signal-500/10 text-signal-700">
              <ClipboardCheck size={20} />
            </span>
            <h1 className="font-display text-2xl font-bold text-ink-950">
              Application Tracker
            </h1>
          </div>
          <p className="text-sm text-ink-600">
            Track your verified career pipeline across the complete application lifecycle.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <Link
            to="/opportunities/jobs"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-signal-600 hover:bg-signal-700 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Sparkles size={14} />
            <span>Discover Opportunities</span>
          </Link>
        </div>
      </div>

      {/* Tabs and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
        <div className="flex items-center gap-1 bg-ink-100/70 p-1 rounded-xl text-xs font-medium overflow-x-auto">
          <button
            type="button"
            onClick={() => handleTabChange("ALL")}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              activeTab === "ALL" ? "bg-white text-ink-950 shadow-xs font-bold" : "text-ink-600 hover:text-ink-900"
            }`}
          >
            All ({allApps.length})
          </button>
          <button
            type="button"
            onClick={() => handleTabChange("SAVED")}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              activeTab === "SAVED" ? "bg-white text-ink-950 shadow-xs font-bold" : "text-ink-600 hover:text-ink-900"
            }`}
          >
            Saved ({savedCount})
          </button>
          <button
            type="button"
            onClick={() => handleTabChange("TAILORED")}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              activeTab === "TAILORED" ? "bg-white text-ink-950 shadow-xs font-bold" : "text-ink-600 hover:text-ink-900"
            }`}
          >
            Tailored ({tailoredCount})
          </button>
          <button
            type="button"
            onClick={() => handleTabChange("APPLIED")}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              activeTab === "APPLIED" ? "bg-white text-ink-950 shadow-xs font-bold" : "text-ink-600 hover:text-ink-900"
            }`}
          >
            Applied ({appliedCount})
          </button>
          <button
            type="button"
            onClick={() => handleTabChange("ARCHIVED")}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              activeTab === "ARCHIVED" ? "bg-white text-ink-950 shadow-xs font-bold" : "text-ink-600 hover:text-ink-900"
            }`}
          >
            Archived ({archivedCount})
          </button>
        </div>

        <div className="relative max-w-xs w-full">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search roles or companies..."
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-ink-200 bg-white text-xs text-ink-900 placeholder:text-ink-400 focus:outline-hidden"
          />
        </div>
      </div>

      {isLoading ? (
        <SkeletonCard count={3} />
      ) : filteredApps.length === 0 ? (
        <EmptyState
          icon={ClipboardCheck}
          title="No applications found"
          description={
            searchQuery
              ? `No tracked applications match "${searchQuery}".`
              : "Track opportunities as you discover, tailor, and submit applications."
          }
          actionText="Explore Jobs"
          actionHref="/opportunities/jobs"
          secondaryActionText="Explore Internships"
          secondaryActionHref="/opportunities/internships"
        />
      ) : (
        <div className="space-y-3.5">
          {filteredApps.map((app) => {
            const hasDirectApply =
              Boolean(app.apply_url) &&
              !app.apply_url.includes("example.com") &&
              !app.apply_url.includes("google.com");

            return (
              <div
                key={app.id}
                className="rounded-2xl border border-ink-100 bg-white p-5 shadow-xs hover:shadow-sm hover:border-ink-200 transition-all duration-200"
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  {/* Left Column: Role Details */}
                  <div className="space-y-2 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        to={app.job_id ? `/opportunities/job/${app.job_id}` : "#"}
                        className="text-base font-bold text-ink-950 hover:text-signal-600 hover:underline leading-snug truncate"
                      >
                        {app.job_title}
                      </Link>
                      {getStatusBadge(app.status)}
                      {app.tailored_resume_id && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 text-[10px] font-semibold border border-indigo-200">
                          <FileText size={11} />
                          Tailored Resume Attached
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3 text-xs text-ink-600 font-medium flex-wrap">
                      <div className="flex items-center gap-1.5">
                        <Building2 size={13} className="text-ink-400 shrink-0" />
                        <span>{app.company}</span>
                      </div>
                      <div className="flex items-center gap-1 text-ink-400">
                        <Calendar size={12} />
                        <span>Saved: {formatDate(app.created_at)}</span>
                      </div>
                      {app.updated_at && app.updated_at !== app.created_at && (
                        <div className="flex items-center gap-1 text-ink-400">
                          <Clock size={12} />
                          <span>Updated: {formatDate(app.updated_at)}</span>
                        </div>
                      )}
                    </div>

                    {/* Notes Row */}
                    <div className="pt-1">
                      {editingNoteId === app.id ? (
                        <div className="flex items-center gap-2 max-w-lg mt-1">
                          <input
                            type="text"
                            value={noteText}
                            onChange={(e) => setNoteText(e.target.value)}
                            placeholder="Add note (e.g. Recruiter message sent)..."
                            className="flex-1 px-2.5 py-1 text-xs border border-signal-400 rounded-lg outline-none"
                            autoFocus
                          />
                          <button
                            type="button"
                            onClick={() => handleSaveNote(app.id)}
                            className="p-1.5 bg-signal-600 text-white rounded-md hover:bg-signal-700 text-xs"
                            title="Save note"
                          >
                            <Check size={13} />
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingNoteId(null)}
                            className="p-1.5 bg-ink-100 text-ink-700 rounded-md hover:bg-ink-200 text-xs"
                            title="Cancel"
                          >
                            <X size={13} />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-xs text-ink-500 group">
                          <span className="italic">
                            {app.notes ? `Note: "${app.notes}"` : "No notes added"}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleStartEditNote(app)}
                            className="opacity-60 group-hover:opacity-100 p-1 hover:text-signal-600 text-ink-400 transition-opacity"
                            title="Edit notes"
                          >
                            <Edit3 size={12} />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Status Transition & Actions */}
                  <div className="flex flex-col sm:flex-row md:flex-col items-start sm:items-center md:items-end gap-2.5 shrink-0">
                    {/* Status Dropdown */}
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-ink-500 font-medium">Stage:</span>
                      <select
                        value={app.status}
                        onChange={(e) =>
                          updateMutation.mutate({
                            id: app.id,
                            updates: { status: e.target.value as ApplicationStatus },
                          })
                        }
                        disabled={updateMutation.isPending}
                        aria-label={`Update application stage for ${app.job_title}`}
                        className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-ink-200 bg-white text-ink-900 shadow-2xs outline-none focus:border-signal-500 cursor-pointer"
                      >
                        {ALL_STATUSES.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {/* Tailor Resume */}
                      {app.job_id && (
                        <Link
                          to={`/resume/tailor/${app.job_id}`}
                          className="px-2.5 py-1.5 rounded-lg bg-signal-50 hover:bg-signal-100 text-signal-700 text-xs font-semibold transition-colors"
                          title="Tailor resume"
                        >
                          Tailor
                        </Link>
                      )}

                      {/* Interview Prep */}
                      {app.job_id && (
                        <Link
                          to={`/growth/interview/${app.job_id}`}
                          className="p-1.5 rounded-lg bg-ink-50 hover:bg-ink-100 text-indigo-600 hover:text-indigo-700 transition-colors"
                          title="Interview questions"
                        >
                          <MessageCircleQuestion size={15} />
                        </Link>
                      )}

                      {/* Copilot */}
                      <Link
                        to={`/copilot?job_id=${encodeURIComponent(app.job_id)}&company=${encodeURIComponent(app.company)}&role=${encodeURIComponent(app.job_title)}`}
                        className="p-1.5 rounded-lg bg-ink-50 hover:bg-ink-100 text-signal-600 transition-colors"
                        title="Ask Copilot"
                      >
                        <Bot size={15} />
                      </Link>

                      {/* P2-01 Direct Apply External Link or Unavailable Banner */}
                      {hasDirectApply ? (
                        <a
                          href={app.apply_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-signal-600 hover:bg-signal-700 text-white text-xs font-bold shadow-2xs transition-colors"
                          title="Open official direct employer application page"
                        >
                          <span>Apply Directly</span>
                          <ExternalLink size={12} />
                        </a>
                      ) : (
                        <span
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 text-xs font-medium"
                          title="RoleRadar cannot verify a direct application link for this posting"
                        >
                          <AlertTriangle size={12} className="text-amber-600 shrink-0" />
                          <span>Application link unavailable</span>
                        </span>
                      )}

                      {/* Delete */}
                      <button
                        type="button"
                        onClick={() => removeMutation.mutate(app.id)}
                        disabled={removeMutation.isPending}
                        className="p-1.5 rounded-lg text-ink-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                        title="Remove from tracker"
                        aria-label="Remove application"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
