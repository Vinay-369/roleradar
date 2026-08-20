import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listApplications, updateApplicationStatus } from "../../lib/applications";

export function Saved() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["applications"], queryFn: listApplications });

  const moveToQueue = useMutation({
    mutationFn: (id: string) => updateApplicationStatus(id, "QUEUED"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  const saved = (data ?? []).filter((a) => a.status === "SAVED");

  if (isLoading) return <p className="text-ink-500">Loading…</p>;

  return (
    <div className="max-w-2xl">
      <h1 className="font-display text-2xl text-ink-900 mb-2">Saved</h1>
      <p className="text-ink-500 mb-6">
        Jobs and internships you've bookmarked. Move one to the Application Queue when you're ready to apply.
      </p>

      {saved.length === 0 && (
        <p className="text-sm text-ink-500">
          Nothing saved yet — use the "Save" link on any job in Jobs For You or Internships.
        </p>
      )}

      <div className="space-y-2">
        {saved.map((app) => (
          <div key={app.id} className="rounded-lg border border-ink-100 bg-white p-4 flex items-center justify-between">
            <div>
              <p className="font-medium text-ink-900">{app.job_title}</p>
              <p className="text-sm text-ink-500">{app.company}</p>
            </div>
            <button
              onClick={() => moveToQueue.mutate(app.id)}
              disabled={moveToQueue.isPending}
              className="text-sm text-signal-600 hover:underline font-medium disabled:opacity-60"
            >
              Move to Queue →
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
