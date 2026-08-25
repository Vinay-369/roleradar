import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Bookmark,
  Trash2,
  ShieldCheck,
  Sparkles,
  Building2,
  ExternalLink,
  Bot,
  MessageCircleQuestion,
  Search,
} from "lucide-react";
import { listApplications, deleteApplication } from "../../lib/applications";
import { useToast } from "../../context/ToastContext";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/SkeletonLoaders";

export function Saved() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { data, isLoading } = useQuery({ queryKey: ["applications"], queryFn: listApplications });
  const [searchQuery, setSearchQuery] = useState("");

  const removeBookmark = useMutation({
    mutationFn: (id: string) => deleteApplication(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.info("Removed from saved.");
    },
    onError: () => toast.error("Failed to remove bookmark."),
  });

  const savedList = (data ?? []).filter((a) => a.status === "SAVED" || a.status === "TAILORED" || a.status === "QUEUED" || a.status === "APPLIED");

  const filteredSaved = savedList.filter((app) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return app.job_title.toLowerCase().includes(q) || app.company.toLowerCase().includes(q);
  });

  return (
    <div className="max-w-4xl space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded-md bg-signal-500/10 text-signal-700">
              <Bookmark size={16} />
            </span>
            <h1 className="font-display text-xl sm:text-2xl font-bold text-ink-950">
              Saved
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-ink-500">
            Jobs and internships you&apos;ve bookmarked. Tailor your resume, prepare interview questions, or apply directly on the employer&apos;s portal.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0 self-start sm:self-auto">
          <Link
            to="/opportunities/jobs"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-signal-500 hover:bg-signal-600 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Sparkles size={13} />
            <span>Discover More Jobs</span>
          </Link>
        </div>
      </div>

      {/* Search & Counter bar */}
      {savedList.length > 0 && (
        <div className="flex items-center justify-between gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search saved roles or companies..."
              className="w-full pl-9 pr-4 py-2 rounded-xl border border-ink-200 bg-white text-xs text-ink-900 placeholder:text-ink-400 focus:outline-hidden"
            />
          </div>
          <div className="text-xs text-ink-500 font-medium">
            <span className="font-bold text-ink-800">{savedList.length}</span> saved {savedList.length === 1 ? "role" : "roles"}
          </div>
        </div>
      )}

      {isLoading ? (
        <SkeletonCard count={3} />
      ) : savedList.length === 0 ? (
        <EmptyState
          icon={Bookmark}
          title="No saved opportunities yet"
          description="Browse live verified jobs and internships, then click Save on any role to bookmark it and access it quickly here."
          actionText="Browse Live Matches"
          actionHref="/opportunities/jobs"
          secondaryActionText="View Internships"
          secondaryActionHref="/opportunities/internships"
        />
      ) : filteredSaved.length === 0 ? (
        <div className="rounded-2xl border border-ink-100 bg-white p-8 text-center text-xs text-ink-500">
          No saved opportunities match &ldquo;{searchQuery}&rdquo;.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredSaved.map((app) => {
            const directApplyUrl = (app.apply_url && !app.apply_url.includes("example.com"))
              ? app.apply_url
              : `https://www.google.com/search?q=${encodeURIComponent(`${app.company} ${app.job_title} careers apply`)}`;

            return (
              <div
                key={app.id}
                className="rounded-2xl border border-ink-100 bg-white p-5 shadow-xs transition-all duration-200 hover:border-ink-200 hover:shadow-sm"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  {/* Role and Company Info */}
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        to={app.job_id ? `/opportunities/job/${app.job_id}` : "#"}
                        className="text-sm font-bold text-ink-950 hover:text-signal-600 hover:underline leading-snug truncate"
                      >
                        {app.job_title}
                      </Link>
                      <span className="rounded-full bg-signal-500/10 text-signal-700 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                        Saved
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-ink-500 font-medium">
                      <Building2 size={13} className="text-ink-400 shrink-0" />
                      <span className="truncate">{app.company}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    {/* Tailor Resume Quick Link */}
                    {app.job_id && (
                      <Link
                        to={`/resume/tailor/${app.job_id}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-signal-500/10 hover:bg-signal-500/20 text-signal-700 text-xs font-semibold transition-colors"
                        title="Tailor resume for this role"
                      >
                        <ShieldCheck size={13} />
                        <span>Tailor Resume</span>
                      </Link>
                    )}

                    {/* Interview Prep */}
                    {app.job_id && (
                      <Link
                        to={`/growth/interview/${app.job_id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-ink-50 hover:bg-ink-100 text-ink-700 text-xs font-medium transition-colors"
                        title="Prepare role-specific interview questions"
                      >
                        <MessageCircleQuestion size={13} className="text-indigo-600" />
                        <span>Interview Prep</span>
                      </Link>
                    )}

                    {/* Ask Copilot */}
                    <Link
                      to={`/copilot?job_id=${encodeURIComponent(app.job_id)}&company=${encodeURIComponent(app.company)}&role=${encodeURIComponent(app.job_title)}&prompt=${encodeURIComponent(`I am preparing to apply for ${app.job_title} at ${app.company}. What are the key skills and interview strategies I should highlight?`)}`}
                      className="p-2 rounded-lg bg-ink-50 hover:bg-ink-100 text-ink-600 hover:text-ink-900 transition-colors"
                      title={`Ask AI Copilot about ${app.job_title} at ${app.company}`}
                    >
                      <Bot size={14} className="text-signal-500" />
                    </Link>

                    {/* Direct Apply External Link */}
                    <a
                      href={directApplyUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-signal-500 hover:bg-signal-600 text-white text-xs font-bold shadow-2xs transition-colors"
                      title="Open official employer application page"
                    >
                      <span>Apply Directly</span>
                      <ExternalLink size={12} />
                    </a>

                    {/* Remove Bookmark */}
                    <button
                      onClick={() => removeBookmark.mutate(app.id)}
                      disabled={removeBookmark.isPending}
                      className="p-1.5 rounded-lg text-ink-400 hover:text-alert-600 hover:bg-alert-50 transition-colors"
                      title="Remove from saved"
                      aria-label="Remove bookmark"
                    >
                      <Trash2 size={15} />
                    </button>
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
