import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listApplications, updateApplicationStatus, type Application, type ApplicationStatus } from "../../lib/applications";

const COLUMNS: ApplicationStatus[] = ["SAVED", "TAILORED", "QUEUED", "APPLIED", "VIEWED", "INTERVIEW", "OFFER", "REJECTED"];

const NEXT_STATUS: Partial<Record<ApplicationStatus, ApplicationStatus>> = {
  SAVED: "QUEUED",
  TAILORED: "QUEUED",
  QUEUED: "APPLIED",
  APPLIED: "VIEWED",
  VIEWED: "INTERVIEW",
  INTERVIEW: "OFFER",
};

function ApplicationCard({ app, onAdvance, onWithdraw }: { app: Application; onAdvance: () => void; onWithdraw: () => void }) {
  const next = NEXT_STATUS[app.status];
  return (
    <div className="rounded-lg border border-ink-100 bg-white p-3 transition-all duration-200 hover:shadow-md hover:border-signal-500/40">
      <p className="text-sm font-medium text-ink-900">{app.job_title}</p>
      <p className="text-xs text-ink-500 mb-2">{app.company}</p>
      <div className="flex gap-2">
        {next && (
          <button onClick={onAdvance} className="text-xs text-signal-600 hover:underline font-medium">
            Move to {next.toLowerCase()} →
          </button>
        )}
        {app.status !== "WITHDRAWN" && app.status !== "REJECTED" && (
          <button onClick={onWithdraw} className="text-xs text-ink-500 hover:underline">
            Withdraw
          </button>
        )}
      </div>
    </div>
  );
}

export function ApplicationTracker() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["applications"], queryFn: listApplications });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: ApplicationStatus }) => updateApplicationStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  if (isLoading) return <p className="text-ink-500">Loading…</p>;

  const byStatus = (status: ApplicationStatus) => (data ?? []).filter((a) => a.status === status);

  return (
    <div>
      <h1 className="font-display text-2xl text-ink-900 mb-2">Application Tracker</h1>
      <p className="text-ink-500 mb-6">Every application, with the exact resume version sent to each company.</p>

      {(data ?? []).length === 0 ? (
        <p className="text-sm text-ink-500">No applications yet — save one from Jobs For You.</p>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map((col) => (
            <div key={col} className="w-56 shrink-0">
              <p className="text-xs font-medium uppercase tracking-wider text-ink-500 mb-2">
                {col} ({byStatus(col).length})
              </p>
              <div className="space-y-2">
                {byStatus(col).map((app) => (
                  <ApplicationCard
                    key={app.id}
                    app={app}
                    onAdvance={() => {
                      const next = NEXT_STATUS[app.status];
                      if (next) updateStatus.mutate({ id: app.id, status: next });
                    }}
                    onWithdraw={() => updateStatus.mutate({ id: app.id, status: "WITHDRAWN" })}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
