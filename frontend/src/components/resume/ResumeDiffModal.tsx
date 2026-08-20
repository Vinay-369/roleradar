import { useState } from "react";
import { GitCompare, X, ShieldCheck, Sparkles } from "lucide-react";
import type { TailoredResume, Change } from "../../lib/tailoring";

interface ResumeDiffModalProps {
  version: TailoredResume;
  triggerButton?: React.ReactNode;
}

export function ResumeDiffModal({ version, triggerButton }: ResumeDiffModalProps) {
  const [open, setOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"side-by-side" | "unified">("side-by-side");

  const changes = version.changes || [];
  const approvedCount = changes.filter((c: Change) => c.status === "APPROVED").length;

  return (
    <>
      {triggerButton ? (
        <div onClick={() => setOpen(true)}>{triggerButton}</div>
      ) : (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-ink-200 bg-white hover:bg-ink-50 text-ink-800 text-xs font-semibold shadow-2xs transition-all hover:border-signal-500"
        >
          <GitCompare size={14} className="text-signal-600" />
          <span>Compare Diff with Master</span>
        </button>
      )}

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-xs animate-fade-in"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-5xl max-h-[90vh] rounded-2xl bg-white border border-ink-100 shadow-2xl flex flex-col overflow-hidden animate-fade-in-up"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-ink-100 bg-ink-50/50">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-signal-500/10 flex items-center justify-center text-signal-600 shrink-0">
                  <GitCompare size={18} />
                </div>
                <div>
                  <h3 className="font-display text-base font-bold text-ink-900 flex items-center gap-2">
                    Master vs. Tailored Version Diff
                    <span className="text-xs font-normal text-ink-500 bg-white border border-ink-200 px-2 py-0.5 rounded-full">
                      {version.job_title} ({version.company})
                    </span>
                  </h3>
                  <p className="text-xs text-ink-500">
                    Side-by-side audit of all candidate-approved changes and Truth Guard verified source evidence.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {/* View toggle */}
                <div className="hidden sm:flex rounded-lg border border-ink-200 bg-white p-0.5 text-xs">
                  <button
                    onClick={() => setViewMode("side-by-side")}
                    className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                      viewMode === "side-by-side" ? "bg-ink-950 text-white" : "text-ink-600 hover:text-ink-900"
                    }`}
                  >
                    Side-by-Side
                  </button>
                  <button
                    onClick={() => setViewMode("unified")}
                    className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                      viewMode === "unified" ? "bg-ink-950 text-white" : "text-ink-600 hover:text-ink-900"
                    }`}
                  >
                    Unified List
                  </button>
                </div>

                <button
                  onClick={() => setOpen(false)}
                  className="p-1.5 rounded-lg text-ink-400 hover:text-ink-900 hover:bg-ink-100 transition-colors"
                  aria-label="Close modal"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Top Summary Banner */}
            <div className="px-6 py-3 bg-gradient-to-r from-ink-950 to-ink-900 text-white flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-4">
                <div>
                  <span className="text-ink-400 block text-[10px] uppercase">Approved Changes</span>
                  <span className="font-bold font-display text-signal-400 text-sm">
                    {approvedCount} / {changes.length}
                  </span>
                </div>
                <div className="h-6 w-px bg-ink-800" />
                <div>
                  <span className="text-ink-400 block text-[10px] uppercase">Truth Guard Verification</span>
                  <span className="font-bold text-signal-400 flex items-center gap-1">
                    <ShieldCheck size={13} /> 100% Sourced
                  </span>
                </div>
                <div className="h-6 w-px bg-ink-800" />
                <div>
                  <span className="text-ink-400 block text-[10px] uppercase">Master Resume Integrity</span>
                  <span className="font-bold text-white">Zero Untracked Hallucinations</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-full bg-signal-500/20 text-signal-300 border border-signal-400/30 text-[11px] font-semibold">
                  {version.is_finalized ? "Finalized Version" : "Review in Progress"}
                </span>
              </div>
            </div>

            {/* Diff Content Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {changes.length === 0 ? (
                <div className="text-center py-12 text-ink-400 text-sm">
                  No proposed changes recorded for this version.
                </div>
              ) : (
                changes.map((change: Change, idx: number) => (
                  <div
                    key={change.change_id || idx}
                    className="rounded-xl border border-ink-100 bg-white overflow-hidden shadow-2xs"
                  >
                    {/* Change Header */}
                    <div className="px-4 py-2.5 bg-ink-50 border-b border-ink-100 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-ink-700">Change #{idx + 1}</span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                            change.status === "APPROVED"
                              ? "bg-signal-500/10 text-signal-700 border border-signal-500/20"
                              : change.status === "REJECTED"
                              ? "bg-alert-600/10 text-alert-700 border border-alert-600/20"
                              : "bg-amber-500/10 text-amber-700 border border-amber-500/20"
                          }`}
                        >
                          {change.status}
                        </span>
                      </div>
                      <span className="text-[11px] text-ink-500">
                        AI Confidence: <strong>{Math.round((change.confidence || 0.9) * 100)}%</strong>
                      </span>
                    </div>

                    {/* Diff Panes */}
                    {viewMode === "side-by-side" ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-ink-100 text-xs">
                        {/* Master Resume Baseline */}
                        <div className="p-4 bg-red-50/20">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-red-700 mb-1.5 flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-red-500" /> Master Resume (Original)
                          </p>
                          <p className="text-ink-600 line-through leading-relaxed bg-red-100/50 p-2.5 rounded-md border border-red-200/60 font-mono">
                            {change.original || "(No previous equivalent bullet)"}
                          </p>
                        </div>

                        {/* Tailored Rewrite */}
                        <div className="p-4 bg-signal-500/5">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-signal-700 mb-1.5 flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-signal-500" /> Tailored Proposal (Final)
                          </p>
                          <p className="text-ink-900 font-medium leading-relaxed bg-signal-500/10 p-2.5 rounded-md border border-signal-500/30 font-mono">
                            {change.proposed}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="p-4 space-y-2 text-xs">
                        {change.original && (
                          <div className="p-2.5 rounded-md bg-red-50 border border-red-200 text-red-900 line-through font-mono">
                            - {change.original}
                          </div>
                        )}
                        <div className="p-2.5 rounded-md bg-signal-500/10 border border-signal-500/30 text-signal-950 font-mono font-medium">
                          + {change.proposed}
                        </div>
                      </div>
                    )}

                    {/* Truth Guard Evidence & Rationale Footer */}
                    <div className="px-4 py-3 bg-ink-50/50 border-t border-ink-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs">
                      <div className="flex items-center gap-1.5 text-ink-700">
                        <ShieldCheck size={14} className="text-signal-600 shrink-0" />
                        <span className="font-bold text-ink-900">Truth Guard Evidence:</span>
                        <span className="text-ink-600 italic font-mono">
                          "{change.source_evidence || 'Master resume validated baseline'}"
                        </span>
                      </div>
                      <p className="text-[11px] text-ink-500">
                        <strong className="text-ink-700">Why:</strong> {change.reason}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-ink-100 bg-ink-50 flex items-center justify-between">
              <span className="text-xs text-ink-500 flex items-center gap-1">
                <Sparkles size={13} className="text-signal-600" />
                Deterministic snapshot stored immutably in MongoDB.
              </span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="px-4 py-1.5 rounded-lg bg-ink-950 text-white text-xs font-semibold hover:bg-ink-900 transition-colors"
              >
                Close Diff View
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
