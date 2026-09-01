import React, { useState, useEffect } from "react";
import { Eye, X, Download, ExternalLink, RefreshCw, Layers, ShieldCheck, AlertCircle } from "lucide-react";

interface ResumePreviewModalProps {
  versionId: string;
  company?: string;
  jobTitle?: string;
  initialTemplate?: string;
  triggerButton?: React.ReactNode;
  isOpen?: boolean;
  onClose?: () => void;
}

const TEMPLATES = [
  { id: "modern", label: "Modern Teal" },
  { id: "classic", label: "Classic ATS" },
  { id: "executive", label: "Executive" },
  { id: "harvard", label: "Harvard Academic" },
];

export function ResumePreviewModal({
  versionId,
  company = "Company",
  jobTitle = "Tailored Resume",
  initialTemplate = "modern",
  triggerButton,
  isOpen,
  onClose,
}: ResumePreviewModalProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [template, setTemplate] = useState(initialTemplate);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = isOpen !== undefined ? isOpen : internalOpen;
  const setOpen = (val: boolean) => {
    setInternalOpen(val);
    if (!val && onClose) onClose();
  };

  useEffect(() => {
    if (open && versionId) {
      loadPdf(template);
    }
    return () => {
      if (pdfUrl) {
        window.URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [open, versionId, template]);

  const loadPdf = async (selectedTpl: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("roleradar_token") || sessionStorage.getItem("roleradar_token");
      const res = await fetch(`/api/tailoring/${versionId}/export/pdf?template=${selectedTpl}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        throw new Error(`Failed to generate preview (${res.status} ${res.statusText})`);
      }
      const blob = await res.blob();
      if (pdfUrl) {
        window.URL.revokeObjectURL(pdfUrl);
      }
      const url = window.URL.createObjectURL(blob);
      setPdfUrl(url);
    } catch (err: any) {
      setError(err.message || "Could not load resume PDF preview.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (!pdfUrl) return;
    const a = document.createElement("a");
    a.href = pdfUrl;
    a.download = `resume_${company.replace(/\s+/g, "_")}_${template}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const handleOpenNewTab = () => {
    if (!pdfUrl) return;
    window.open(pdfUrl, "_blank");
  };

  return (
    <>
      {triggerButton && (
        <div onClick={() => setOpen(true)} className="inline-block cursor-pointer">
          {triggerButton}
        </div>
      )}
      {!triggerButton && isOpen === undefined && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-ink-200 bg-white hover:bg-ink-50 text-ink-800 text-xs font-semibold shadow-2xs transition-all hover:border-signal-500"
        >
          <Eye size={14} className="text-signal-600" />
          <span>Preview PDF</span>
        </button>
      )}

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/70 backdrop-blur-xs animate-fade-in"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-5xl h-[92vh] rounded-2xl bg-white border border-ink-100 shadow-2xl flex flex-col overflow-hidden animate-fade-in-up"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between px-5 py-3.5 border-b border-ink-100 bg-ink-50/70 gap-3">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-signal-500/10 flex items-center justify-center text-signal-600 shrink-0">
                  <Eye size={18} />
                </div>
                <div className="min-w-0">
                  <h3 className="font-display text-sm sm:text-base font-bold text-ink-950 truncate flex items-center gap-2">
                    Resume Live Preview
                    <span className="text-[11px] font-medium text-ink-600 bg-white border border-ink-200 px-2 py-0.5 rounded-full truncate">
                      {jobTitle} • {company}
                    </span>
                  </h3>
                  <p className="text-[11px] text-ink-500 flex items-center gap-1">
                    <ShieldCheck size={12} className="text-signal-600" />
                    Truth Guard verified • 1-page ATS canvas compliant
                  </p>
                </div>
              </div>

              {/* Template Switcher & Actions */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex rounded-lg border border-ink-200 bg-white p-0.5 text-xs">
                  {TEMPLATES.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => setTemplate(t.id)}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                        template === t.id
                          ? "bg-ink-950 text-white shadow-2xs"
                          : "text-ink-600 hover:text-ink-900 hover:bg-ink-50"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>

                <div className="h-5 w-px bg-ink-200 hidden sm:block" />

                <button
                  onClick={handleOpenNewTab}
                  disabled={!pdfUrl || isLoading}
                  title="Open PDF in new tab"
                  className="p-1.5 rounded-lg border border-ink-200 bg-white text-ink-700 hover:bg-ink-50 transition-colors disabled:opacity-50"
                >
                  <ExternalLink size={15} />
                </button>

                <button
                  onClick={handleDownload}
                  disabled={!pdfUrl || isLoading}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-signal-600 hover:bg-signal-700 text-white text-xs font-semibold shadow-xs transition-colors disabled:opacity-50"
                >
                  <Download size={13} />
                  <span>Download</span>
                </button>

                <button
                  onClick={() => setOpen(false)}
                  className="p-1.5 rounded-lg text-ink-400 hover:text-ink-900 hover:bg-ink-100 transition-colors"
                  aria-label="Close preview modal"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Viewer Content */}
            <div className="flex-1 bg-ink-100/60 relative overflow-hidden flex items-center justify-center p-2 sm:p-4">
              {isLoading && (
                <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-2xs flex flex-col items-center justify-center gap-3">
                  <RefreshCw className="w-7 h-7 text-signal-600 animate-spin" />
                  <p className="text-xs font-semibold text-ink-700">Rendering {template} template PDF...</p>
                </div>
              )}

              {error ? (
                <div className="p-6 max-w-md bg-white rounded-xl border border-alert-200 text-center shadow-xs">
                  <AlertCircle className="w-8 h-8 text-alert-600 mx-auto mb-2" />
                  <h4 className="text-sm font-bold text-ink-900">Preview Error</h4>
                  <p className="text-xs text-ink-500 mt-1 mb-3">{error}</p>
                  <button
                    onClick={() => loadPdf(template)}
                    className="px-3.5 py-1.5 rounded-lg bg-ink-950 text-white text-xs font-semibold"
                  >
                    Retry Render
                  </button>
                </div>
              ) : pdfUrl ? (
                <iframe
                  src={`${pdfUrl}#toolbar=0&navpanes=0`}
                  title="Resume PDF Preview"
                  className="w-full h-full rounded-xl bg-white shadow-md border border-ink-200"
                />
              ) : null}
            </div>

            {/* Footer Status */}
            <div className="px-5 py-2.5 bg-white border-t border-ink-100 flex items-center justify-between text-xs text-ink-500">
              <span className="flex items-center gap-1.5 text-[11px]">
                <Layers size={13} className="text-ink-400" />
                Template: <strong className="text-ink-800">{TEMPLATES.find((t) => t.id === template)?.label}</strong>
              </span>
              <span className="text-[11px] text-ink-400">
                Pure-data rendering • Guaranteed ATS parseability
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default ResumePreviewModal;
