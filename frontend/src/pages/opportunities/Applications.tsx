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
  CircleHelp,
  LayoutGrid,
  List,
} from "lucide-react";
import {
  listApplications,
  deleteApplication,
  updateApplication,
  type Application,
  type ApplicationStatus,
} from "../../lib/applications";
import { useToast } from "../../context/ToastContext";
import { SkeletonCard } from "../../components/ui/SkeletonLoaders";

const ALL_STATUSES: { value: ApplicationStatus; label: string; color: string }[] = [
  { value: "SAVED", label: "Saved", color: "bg-ink-100 text-ink-700 border-ink-200 dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700" },
  { value: "TAILORED", label: "Tailored", color: "bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/50 dark:text-indigo-300 dark:border-indigo-900" },
  { value: "QUEUED", label: "Queued", color: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/50 dark:text-purple-300 dark:border-purple-900" },
  { value: "APPLIED", label: "Applied", color: "bg-signal-50 text-signal-700 border-signal-200 dark:bg-signal-950/40 dark:text-signal-300 dark:border-signal-900" },
  { value: "SHORTLISTED", label: "Shortlisted", color: "bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/50 dark:text-sky-300 dark:border-sky-900" },
  { value: "INTERVIEW", label: "Interview", color: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900" },
  { value: "OFFER", label: "Offer", color: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900" },
  { value: "REJECTED", label: "Rejected", color: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-900" },
  { value: "WITHDRAWN", label: "Withdrawn", color: "bg-zinc-100 text-zinc-600 border-zinc-200 dark:bg-zinc-900 dark:text-zinc-300 dark:border-zinc-700" },
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
  const [viewMode, setViewMode] = useState<"list" | "board">("list");
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

  const boardColumns: { title: string; statuses: ApplicationStatus[]; color: string }[] = [
    { title: "Saved", statuses: ["SAVED"], color: "border-slate-300" },
    { title: "Tailored", statuses: ["TAILORED", "QUEUED"], color: "border-indigo-300" },
    { title: "Applied", statuses: ["APPLIED"], color: "border-signal-400" },
    { title: "Interviewing", statuses: ["SHORTLISTED", "INTERVIEW"], color: "border-amber-300" },
    { title: "Offer / Archived", statuses: ["OFFER", "REJECTED", "WITHDRAWN"], color: "border-emerald-300" },
  ];

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 sm:py-8 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-signal-500/15 bg-signal-500/10 text-signal-700">
              <ClipboardCheck size={20} />
            </span>
            <h1 className="font-display text-2xl font-bold text-ink-950 sm:text-3xl">
              Application Tracker
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 pl-11">
            <p className="text-sm text-ink-600">Track your applications manually</p>
            <span className="group relative inline-flex">
              <button
                type="button"
                aria-label="Why are application updates manual?"
                className="inline-flex h-6 w-6 items-center justify-center rounded-full text-ink-400 transition-colors hover:bg-slate-100 hover:text-signal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-500 dark:hover:bg-slate-800"
              >
                <CircleHelp size={15} />
              </button>
              <span role="tooltip" className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 w-64 -translate-x-1/2 rounded-lg border border-slate-200 bg-white p-3 text-xs font-normal leading-relaxed text-ink-700 opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
                Employer portals don’t share application progress with RoleRadar. Update each status here when you hear back or move to the next stage.
              </span>
            </span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2.5 self-start sm:self-auto">
          <Link
            to="/opportunities/jobs"
            className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-signal-600 px-4 text-xs font-semibold text-white shadow-xs transition-colors hover:bg-signal-700"
          >
            <Sparkles size={14} />
            <span>Discover Opportunities</span>
          </Link>
        </div>
      </div>

      {/* Tabs, search, and view controls */}
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-1 overflow-x-auto rounded-lg bg-slate-100 p-1 text-xs font-medium dark:bg-slate-800">
          <button
            type="button"
            onClick={() => handleTabChange("ALL")}
            className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 transition-all ${
              activeTab === "ALL" ? "bg-white text-ink-950 shadow-xs font-bold dark:bg-slate-700 dark:text-white" : "text-ink-600 hover:text-ink-900 dark:text-slate-300 dark:hover:text-white"
            }`}
          >
            All <span className="rounded-full bg-slate-200/80 px-1.5 py-0.5 text-[10px] dark:bg-slate-600">{allApps.length}</span>
          </button>
          <button
            type="button"
            onClick={() => handleTabChange("SAVED")}
            className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 transition-all ${
              activeTab === "SAVED" ? "bg-white text-ink-950 shadow-xs font-bold dark:bg-slate-700 dark:text-white" : "text-ink-600 hover:text-ink-900 dark:text-slate-300 dark:hover:text-white"
            }`}
          >
            Saved <span className="rounded-full bg-slate-200/80 px-1.5 py-0.5 text-[10px] dark:bg-slate-600">{savedCount}</span>
          </button>
          <button
            type="button"
            onClick={() => handleTabChange("TAILORED")}
            className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 transition-all ${
              activeTab === "TAILORED" ? "bg-white text-ink-950 shadow-xs font-bold dark:bg-slate-700 dark:text-white" : "text-ink-600 hover:text-ink-900 dark:text-slate-300 dark:hover:text-white"
            }`}
          >
            Tailored <span className="rounded-full bg-slate-200/80 px-1.5 py-0.5 text-[10px] dark:bg-slate-600">{tailoredCount}</span>
          </button>
          <button
            type="button"
            onClick={() => handleTabChange("APPLIED")}
            className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 transition-all ${
              activeTab === "APPLIED" ? "bg-white text-ink-950 shadow-xs font-bold dark:bg-slate-700 dark:text-white" : "text-ink-600 hover:text-ink-900 dark:text-slate-300 dark:hover:text-white"
            }`}
          >
            Applied <span className="rounded-full bg-slate-200/80 px-1.5 py-0.5 text-[10px] dark:bg-slate-600">{appliedCount}</span>
          </button>
          <button
            type="button"
            onClick={() => handleTabChange("ARCHIVED")}
            className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 transition-all ${
              activeTab === "ARCHIVED" ? "bg-white text-ink-950 shadow-xs font-bold dark:bg-slate-700 dark:text-white" : "text-ink-600 hover:text-ink-900 dark:text-slate-300 dark:hover:text-white"
            }`}
          >
            Archived <span className="rounded-full bg-slate-200/80 px-1.5 py-0.5 text-[10px] dark:bg-slate-600">{archivedCount}</span>
          </button>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative w-full sm:w-64">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search roles or companies..."
            className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-4 text-xs text-ink-900 placeholder:text-ink-400 outline-none transition focus:border-signal-400 focus:ring-2 focus:ring-signal-500/15 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          />
        </div>
        <div className="inline-flex h-10 shrink-0 items-center rounded-lg border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-800" aria-label="Application display mode">
          <button type="button" onClick={() => setViewMode("list")} aria-pressed={viewMode === "list"} title="List view" className={`inline-flex h-8 w-9 items-center justify-center rounded-md transition ${viewMode === "list" ? "bg-white text-signal-700 shadow-xs dark:bg-slate-700 dark:text-white" : "text-ink-500 hover:text-ink-900 dark:text-slate-400 dark:hover:text-white"}`}>
            <List size={16} />
          </button>
          <button type="button" onClick={() => setViewMode("board")} aria-pressed={viewMode === "board"} title="Kanban board view" className={`inline-flex h-8 w-9 items-center justify-center rounded-md transition ${viewMode === "board" ? "bg-white text-signal-700 shadow-xs dark:bg-slate-700 dark:text-white" : "text-ink-500 hover:text-ink-900 dark:text-slate-400 dark:hover:text-white"}`}>
            <LayoutGrid size={16} />
          </button>
        </div>
        </div>
      </div>

      {isLoading ? (
        <SkeletonCard count={3} />
        ) : filteredApps.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-12 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:py-16">
            <div className="relative mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-signal-500/20 bg-signal-500/10 text-signal-700 dark:text-signal-300">
              <ClipboardCheck size={29} strokeWidth={1.7} />
              <span className="absolute -right-1 -top-1 h-4 w-4 rounded-full border-2 border-white bg-emerald-400 dark:border-slate-900" />
            </div>
            <h2 className="font-display text-xl font-bold text-ink-950 dark:text-white">No applications found</h2>
            <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-500 dark:text-slate-400">
              {searchQuery
                ? `No tracked applications match "${searchQuery}". Try another search or explore current opportunities.`
                : "Your next opportunity starts here. Save a role to track its progress from discovery through offer."}
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2.5">
              <Link to="/opportunities/jobs" className="inline-flex h-10 items-center gap-2 rounded-lg bg-signal-600 px-4 text-xs font-semibold text-white shadow-xs transition-colors hover:bg-signal-700">
                <Sparkles size={14} />
                Explore Jobs
              </Link>
              <Link to="/opportunities/internships" className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-xs font-semibold text-ink-700 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800">
                Explore Internships
              </Link>
            </div>
          </div>
        ) : viewMode === "board" ? (
          <div className="flex gap-4 overflow-x-auto pb-3">
            {boardColumns.map((column) => {
              const columnApps = filteredApps.filter((app) => column.statuses.includes(app.status));
              return (
                <section key={column.title} className="w-[260px] shrink-0">
                  <div className={`mb-3 flex items-center justify-between border-t-2 ${column.color} rounded-t-lg bg-slate-50 px-3 py-3 dark:bg-slate-900`}>
                    <h2 className="text-xs font-bold text-ink-800 dark:text-slate-100">{column.title}</h2>
                    <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-bold text-ink-600 shadow-xs dark:bg-slate-800 dark:text-slate-300">{columnApps.length}</span>
                  </div>
                  <div className="space-y-3">
                    {columnApps.map((app) => (
                      <article key={app.id} className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm transition hover:border-slate-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700">
                        <div className="flex items-start gap-2.5">
                          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                            <Building2 size={17} />
                          </span>
                          <div className="min-w-0 flex-1">
                            <Link to={app.job_id ? `/opportunities/job/${app.job_id}` : "#"} className="line-clamp-2 text-sm font-bold leading-snug text-ink-950 hover:text-signal-700 dark:text-white dark:hover:text-signal-300">
                              {app.job_title}
                            </Link>
                            <p className="mt-1 truncate text-xs text-ink-500 dark:text-slate-400">{app.company}</p>
                          </div>
                        </div>
                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          {getStatusBadge(app.status)}
                          <span className="inline-flex items-center gap-1 text-[10px] text-ink-400" title={`Added ${formatDate(app.created_at)}`}>
                            <Calendar size={11} /> Tracked {formatDate(app.created_at)}
                          </span>
                        </div>
                        <label className="mt-3 block text-[10px] font-medium text-ink-500 dark:text-slate-400">
                          Update status
                          <select
                            value={app.status}
                            onChange={(e) => updateMutation.mutate({ id: app.id, updates: { status: e.target.value as ApplicationStatus } })}
                            disabled={updateMutation.isPending}
                            aria-label={`Update status for ${app.job_title}`}
                            className="mt-1 h-9 w-full rounded-lg border border-slate-200 bg-white px-2 text-xs font-semibold text-ink-800 outline-none focus:border-signal-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                          >
                            {ALL_STATUSES.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}
                          </select>
                        </label>
                        <div className="mt-3 flex gap-2">
                          {app.job_id && (
                            <Link to={`/resume/tailor/${app.job_id}`} className="inline-flex h-8 flex-1 items-center justify-center gap-1 rounded-lg bg-signal-50 text-[11px] font-semibold text-signal-700 transition hover:bg-signal-100 dark:bg-signal-950/40 dark:text-signal-300 dark:hover:bg-signal-950/70">
                              <FileText size={12} /> Tailor Resume
                            </Link>
                          )}
                          <Link to={app.job_id ? `/opportunities/job/${app.job_id}` : "#"} className="inline-flex h-8 flex-1 items-center justify-center gap-1 rounded-lg border border-slate-200 text-[11px] font-semibold text-ink-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
                            <ExternalLink size={12} /> View JD
                          </Link>
                        </div>
                      </article>
                    ))}
                    {columnApps.length === 0 && (
                      <div className="rounded-xl border border-dashed border-slate-200 px-3 py-6 text-center text-[11px] text-ink-400 dark:border-slate-800 dark:text-slate-500">
                        No roles in this stage
                      </div>
                    )}
                  </div>
                </section>
              );
            })}
          </div>
        ) : (
        <div className="space-y-3.5">
          {filteredApps.map((app) => {
            const hasDirectApply =
              Boolean(app.apply_url) &&
              (app.apply_url.startsWith("https://") || app.apply_url.startsWith("http://")) &&
              !app.apply_url.includes("example.com") &&
              !app.apply_url.includes("google.com");

            return (
              <div
                key={app.id}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all duration-200 hover:border-slate-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  {/* Left Column: Role Details */}
                  <div className="flex min-w-0 flex-1 items-start gap-3">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                      <Building2 size={20} />
                    </span>
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          to={app.job_id ? `/opportunities/job/${app.job_id}` : "#"}
                          className="truncate text-base font-bold leading-snug text-ink-950 hover:text-signal-600 hover:underline dark:text-white"
                        >
                          {app.job_title}
                        </Link>
                        {getStatusBadge(app.status)}
                        {app.tailored_resume_id && (
                          <span className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 dark:border-indigo-900 dark:bg-indigo-950/50 dark:text-indigo-300">
                            <FileText size={11} />
                            Tailored Resume Attached
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-medium text-ink-600 dark:text-slate-300">{app.company}</p>

                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-medium text-ink-600 dark:text-slate-400">
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
                            className="h-9 flex-1 rounded-lg border border-signal-400 bg-white px-2.5 text-xs text-ink-900 outline-none focus:ring-2 focus:ring-signal-500/15 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
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
                  </div>

                  {/* Right Column: Status Transition & Actions */}
                  <div className="flex flex-col sm:flex-row md:flex-col items-start sm:items-center md:items-end gap-2.5 shrink-0">
                    {/* Status Dropdown */}
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-medium text-ink-500">Update status:</span>
                      <select
                        value={app.status}
                        onChange={(e) =>
                          updateMutation.mutate({
                            id: app.id,
                            updates: { status: e.target.value as ApplicationStatus },
                          })
                        }
                        disabled={updateMutation.isPending}
                        aria-label={`Manually update application stage for ${app.job_title}`}
                        title="Update this stage yourself; employer website activity is not synced."
                        className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-ink-900 shadow-2xs outline-none focus:border-signal-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                      >
                        {ALL_STATUSES.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <p className="text-[10px] text-ink-400 sm:text-right md:text-right">
                      Updated {formatDate(app.updated_at)}
                    </p>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {/* Tailor Resume */}
                      {app.job_id && (
                        <Link
                          to={`/resume/tailor/${app.job_id}`}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-signal-50 px-2.5 py-1.5 text-xs font-semibold text-signal-700 transition-colors hover:bg-signal-100 dark:bg-signal-950/40 dark:text-signal-300 dark:hover:bg-signal-950/70"
                          title="Tailor resume"
                        >
                          <FileText size={13} />
                          Tailor Resume
                        </Link>
                      )}
                      {app.job_id && (
                        <Link
                          to={`/opportunities/job/${app.job_id}`}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-ink-700 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                        >
                          <ExternalLink size={13} />
                          View JD
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
