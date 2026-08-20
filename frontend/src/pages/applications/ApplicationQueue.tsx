import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listApplications, getApplicationPackage, updateApplicationStatus, type Application } from "../../lib/applications";

function PackagePanel({ app, onMarkApplied }: { app: Application; onMarkApplied: () => void }) {
  const { data: pkg, isLoading } = useQuery({
    queryKey: ["application-package", app.id],
    queryFn: () => getApplicationPackage(app.id),
  });

  if (isLoading) return <p className="text-sm text-ink-500">Preparing package…</p>;
  if (!pkg) return null;

  return (
    <div className="mt-3 rounded-lg border border-ink-100 bg-ink-50 p-4">
      {pkg.resume_source === "none" && (
        <p className="text-sm text-alert-600 mb-3">No resume available yet — upload your master resume first.</p>
      )}
      {pkg.resume_source === "master" && (
        <p className="text-xs text-amber-600 mb-3">Using your master resume — no tailored version exists for this job yet.</p>
      )}

      <p className="text-xs font-medium uppercase tracking-wider text-ink-500 mb-2">Checklist</p>
      <ul className="space-y-1 mb-4">
        {pkg.checklist.map((step, i) => (
          <li key={i} className="text-sm text-ink-700 flex gap-2">
            <span className="text-ink-300">{i + 1}.</span>{step}
          </li>
        ))}
      </ul>

      {pkg.apply_url ? (
        <a
          href={pkg.apply_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block rounded-md bg-ink-950 hover:bg-ink-900 text-white px-4 py-2 text-sm font-medium mb-3"
        >
          Open official application page →
        </a>
      ) : (
        <a
          href={`https://www.google.com/search?q=${encodeURIComponent(`${app.company} ${app.job_title} careers apply`)}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block rounded-md bg-ink-950 hover:bg-ink-900 text-white px-4 py-2 text-sm font-medium mb-3"
        >
          Search {app.company} application portal →
        </a>
      )}

      <div>
        <button
          onClick={onMarkApplied}
          className="rounded-md bg-signal-500 hover:bg-signal-600 text-white px-4 py-2 text-sm font-medium"
        >
          I've submitted it — mark as Applied
        </button>
      </div>
    </div>
  );
}

export function ApplicationQueue() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["applications"], queryFn: listApplications });
  const [openId, setOpenId] = useState<string | null>(null);

  const markApplied = useMutation({
    mutationFn: (id: string) => updateApplicationStatus(id, "APPLIED"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  const queueItems = (data ?? []).filter((a) => a.status === "TAILORED" || a.status === "QUEUED");

  if (isLoading) return <p className="text-ink-500">Loading…</p>;

  return (
    <div className="max-w-2xl">
      <h1 className="font-display text-2xl text-ink-900 mb-2">Application Queue</h1>
      <p className="text-ink-500 mb-6">
        RoleRadar prepares each application package for you — you always submit it yourself on the real company site. No automated submissions, ever.
      </p>

      {queueItems.length === 0 && <p className="text-sm text-ink-500">Nothing queued — move a saved job here when you're ready to apply, or tailor a resume for one first.</p>}

      <div className="space-y-3">
        {queueItems.map((app) => (
          <div key={app.id} className="rounded-lg border border-ink-100 bg-white p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-ink-900">{app.job_title}</p>
                <p className="text-sm text-ink-500">{app.company}</p>
              </div>
              <button
                onClick={() => setOpenId(openId === app.id ? null : app.id)}
                className="text-sm text-signal-600 hover:underline font-medium"
              >
                {openId === app.id ? "Hide" : "Prepare package"}
              </button>
            </div>
            {openId === app.id && (
              <PackagePanel app={app} onMarkApplied={() => markApplied.mutate(app.id)} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
