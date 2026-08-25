export function SkeletonBox({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-xl bg-ink-200/60 ${className}`}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard({ count = 1 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, idx) => (
        <div
          key={idx}
          className="rounded-2xl border border-ink-100 bg-white p-5 space-y-3.5 shadow-xs"
        >
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <SkeletonBox className="h-4 w-44" />
              <SkeletonBox className="h-3 w-28" />
            </div>
            <SkeletonBox className="h-9 w-16 rounded-full" />
          </div>
          <div className="flex gap-2 pt-2">
            <SkeletonBox className="h-6 w-20 rounded-md" />
            <SkeletonBox className="h-6 w-24 rounded-md" />
            <SkeletonBox className="h-6 w-16 rounded-md" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, idx) => (
        <div
          key={idx}
          className="rounded-2xl border border-ink-100 bg-white p-5 space-y-4 shadow-xs"
        >
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <SkeletonBox className="h-4 w-36" />
              <SkeletonBox className="h-3 w-24" />
            </div>
            <SkeletonBox className="h-8 w-12 rounded-lg" />
          </div>
          <SkeletonBox className="h-10 w-full rounded-lg" />
          <div className="flex items-center justify-between pt-2 border-t border-ink-50">
            <SkeletonBox className="h-3 w-20" />
            <SkeletonBox className="h-7 w-24 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonStats() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
      {Array.from({ length: 4 }).map((_, idx) => (
        <div
          key={idx}
          className="rounded-xl border border-ink-100 bg-white p-4 space-y-2.5 shadow-xs"
        >
          <div className="flex items-center justify-between">
            <SkeletonBox className="h-3 w-20" />
            <SkeletonBox className="h-6 w-6 rounded-md" />
          </div>
          <SkeletonBox className="h-6 w-14" />
          <SkeletonBox className="h-2.5 w-24" />
        </div>
      ))}
    </div>
  );
}
