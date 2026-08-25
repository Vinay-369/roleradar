import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from "lucide-react";
import { useToast, type ToastType } from "../../context/ToastContext";

const ICONS: Record<ToastType, typeof CheckCircle2> = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const STYLES: Record<ToastType, { border: string; bg: string; iconColor: string; titleColor: string }> = {
  success: {
    border: "border-signal-500/30",
    bg: "bg-white/95 backdrop-blur-md shadow-lg shadow-signal-500/5",
    iconColor: "text-signal-600 bg-signal-500/10",
    titleColor: "text-signal-900",
  },
  error: {
    border: "border-alert-500/30",
    bg: "bg-white/95 backdrop-blur-md shadow-lg shadow-alert-500/5",
    iconColor: "text-alert-600 bg-alert-500/10",
    titleColor: "text-alert-900",
  },
  warning: {
    border: "border-amber-500/30",
    bg: "bg-white/95 backdrop-blur-md shadow-lg shadow-amber-500/5",
    iconColor: "text-amber-600 bg-amber-500/10",
    titleColor: "text-amber-900",
  },
  info: {
    border: "border-blue-500/30",
    bg: "bg-white/95 backdrop-blur-md shadow-lg shadow-blue-500/5",
    iconColor: "text-blue-600 bg-blue-500/10",
    titleColor: "text-blue-900",
  },
};

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      className="fixed top-5 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center gap-2.5 max-w-md w-full px-4 pointer-events-none"
    >
      {toasts.map((toast) => {
        const Icon = ICONS[toast.type];
        const style = STYLES[toast.type];

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto w-full rounded-2xl border ${style.border} ${style.bg} p-3.5 shadow-xl shadow-ink-950/10 flex items-start gap-3 animate-fade-in-down transition-all hover:scale-[1.01]`}
            role="alert"
          >
            <div className={`p-1.5 rounded-xl shrink-0 ${style.iconColor}`}>
              <Icon size={16} />
            </div>

            <div className="flex-1 min-w-0 pt-0.5">
              {toast.title && (
                <p className={`text-xs font-bold ${style.titleColor} leading-snug`}>
                  {toast.title}
                </p>
              )}
              <p className="text-xs text-ink-700 mt-0.5 leading-relaxed break-words font-medium">
                {toast.message}
              </p>
            </div>

            <button
              onClick={() => removeToast(toast.id)}
              className="p-1 rounded-lg text-ink-400 hover:text-ink-700 hover:bg-ink-100/80 transition-colors shrink-0 -mr-1 -mt-1"
              aria-label="Dismiss notification"
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
