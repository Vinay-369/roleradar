import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertOctagon, RotateCcw, Home } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught application error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  private handleGoHome = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = "/dashboard";
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-[400px] flex items-center justify-center p-6">
          <div className="max-w-md w-full rounded-2xl border border-alert-500/20 bg-white p-6 shadow-lg text-center space-y-4">
            <div className="w-12 h-12 rounded-xl bg-alert-500/10 text-alert-600 flex items-center justify-center mx-auto">
              <AlertOctagon size={24} />
            </div>

            <div>
              <h2 className="text-base font-bold text-ink-950">Something went wrong</h2>
              <p className="text-xs text-ink-600 mt-1 leading-relaxed">
                An unexpected interface error occurred. You can reload this view or return to the main dashboard.
              </p>
            </div>

            {this.state.error && (
              <div className="p-3 rounded-lg bg-ink-50 border border-ink-200/60 text-left overflow-hidden">
                <p className="text-[11px] font-mono text-alert-700 font-semibold truncate">
                  {this.state.error.toString()}
                </p>
              </div>
            )}

            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                onClick={this.handleReset}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-signal-500 hover:bg-signal-600 text-white text-xs font-semibold shadow-xs transition-colors"
              >
                <RotateCcw size={13} />
                <span>Reload Page</span>
              </button>
              <button
                onClick={this.handleGoHome}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-ink-100 hover:bg-ink-200 text-ink-800 text-xs font-semibold transition-colors"
              >
                <Home size={13} />
                <span>Go to Dashboard</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
