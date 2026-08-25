import { Link } from "react-router-dom";
import { Inbox, type LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionText?: string;
  actionHref?: string;
  onAction?: () => void;
  secondaryActionText?: string;
  secondaryActionHref?: string;
  onSecondaryAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  actionText,
  actionHref,
  onAction,
  secondaryActionText,
  secondaryActionHref,
  onSecondaryAction,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`rounded-2xl border border-dashed border-ink-200 bg-white/70 p-8 sm:p-12 text-center flex flex-col items-center justify-center animate-fade-in-up ${className}`}
    >
      <div className="w-14 h-14 rounded-2xl bg-signal-500/10 text-signal-700 flex items-center justify-center mb-4 shadow-xs">
        <Icon size={26} strokeWidth={1.8} />
      </div>

      <h3 className="text-sm sm:text-base font-bold text-ink-950 max-w-md">
        {title}
      </h3>

      <p className="text-xs sm:text-sm text-ink-500 mt-1.5 max-w-sm leading-relaxed">
        {description}
      </p>

      {(actionText || secondaryActionText) && (
        <div className="flex flex-wrap items-center justify-center gap-3 mt-6">
          {actionText && (
            actionHref ? (
              <Link
                to={actionHref}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-signal-500 hover:bg-signal-600 text-white text-xs font-semibold shadow-xs transition-all active:scale-95"
              >
                {actionText}
              </Link>
            ) : (
              <button
                type="button"
                onClick={onAction}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-signal-500 hover:bg-signal-600 text-white text-xs font-semibold shadow-xs transition-all active:scale-95"
              >
                {actionText}
              </button>
            )
          )}

          {secondaryActionText && (
            secondaryActionHref ? (
              <Link
                to={secondaryActionHref}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-ink-100 hover:bg-ink-200 text-ink-800 text-xs font-semibold transition-colors"
              >
                {secondaryActionText}
              </Link>
            ) : (
              <button
                type="button"
                onClick={onSecondaryAction}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-ink-100 hover:bg-ink-200 text-ink-800 text-xs font-semibold transition-colors"
              >
                {secondaryActionText}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
}
