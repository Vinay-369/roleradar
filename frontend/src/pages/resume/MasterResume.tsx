import { useRef, useState, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  UploadCloud, FileText, Check, AlertCircle, AlertTriangle, Layers,
  Code2, Database, Cloud, Terminal, Cpu, CheckCircle2, XCircle, Award, Globe, Phone, Mail,
  ChevronDown, Info,
} from "lucide-react";
import { getMasterResume, uploadResume } from "../../lib/resume";
import { useToast } from "../../context/ToastContext";

const JUNK_SKILL_TOKENS = new Set([
  "team player", "leadership", "time management", "detail oriented",
  "self motivated", "quick learner", "hard worker", "passionate", "good listener",
  "communication", "skills", "knowledge", "proficient", "familiar", "working", "building",
  "responsible", "assisted", "learning", "enthusiastic", "hardworking", "problem solving",
]);
const EMPTY_SKILLS: string[] = [];

interface SkillCategory {
  name: string;
  icon: any;
  color: string;
  items: string[];
}

function getScoreTone(score: number): { badge: string; bar: string } {
  if (score >= 80) return { badge: "border-emerald-200 bg-emerald-50 text-emerald-700", bar: "bg-emerald-500" };
  if (score >= 60) return { badge: "border-amber-200 bg-amber-50 text-amber-700", bar: "bg-amber-500" };
  return { badge: "border-rose-200 bg-rose-50 text-rose-700", bar: "bg-rose-500" };
}

function ScoreGauge({ value }: { value: number }) {
  const gaugePathLength = 251.33;
  const clampedValue = Math.max(0, Math.min(value, 100));
  const tone = getScoreTone(clampedValue);

  return (
    <div className="relative w-36 shrink-0" role="img" aria-label={`Strict ATS Score: ${clampedValue} out of 100`}>
      <svg viewBox="0 0 180 105" className="w-full overflow-visible">
        <path
          d="M 15 92 A 75 75 0 0 1 165 92"
          fill="none"
          stroke="currentColor"
          strokeWidth="12"
          strokeLinecap="round"
          className="text-slate-100"
        />
        <path
          d="M 15 92 A 75 75 0 0 1 165 92"
          fill="none"
          stroke="currentColor"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={gaugePathLength}
          strokeDashoffset={gaugePathLength * (1 - clampedValue / 100)}
          className={clampedValue >= 80 ? "text-emerald-500" : clampedValue >= 60 ? "text-amber-500" : "text-rose-500"}
          style={{ transition: "stroke-dashoffset 500ms ease" }}
        />
      </svg>
      <div className="absolute inset-x-0 bottom-0 flex flex-col items-center">
        <span className="font-display text-3xl font-bold leading-none tabular-nums text-ink-950">{clampedValue}</span>
        <span className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-ink-500">Strict ATS / 100</span>
      </div>
      <span className={`absolute right-0 top-2 rounded-full border px-2 py-0.5 text-[9px] font-bold ${tone.badge}`}>
        {clampedValue >= 80 ? "STRONG" : clampedValue >= 60 ? "REVIEW" : "AT RISK"}
      </span>
    </div>
  );
}

function categorizeAndFilterSkills(rawSkills: string[]): SkillCategory[] {
  const langSet = ["python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "rust", "kotlin", "swift", "ruby", "php", "scala", "r", "dart", "html5", "html", "css3", "css", "sass", "scss", "sql", "bash", "shell", "powershell"];
  const fwSet = ["react", "angular", "vue", "next.js", "nextjs", "nuxt", "svelte", "tailwind", "bootstrap", "redux", "zustand", "express", "fastapi", "django", "flask", "spring boot", "spring", "asp.net", "dotnet", "nestjs", "graphql", "rest api", "restful", "rest"];
  const dbSet = ["postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb", "kafka", "rabbitmq", "spark", "dbt", "snowflake", "bigquery", "nosql", "sql server", "firebase", "supabase", "prisma"];
  const cloudSet = ["aws", "azure", "google cloud", "gcp", "docker", "kubernetes", "k8s", "terraform", "ci/cd", "ci-cd", "github actions", "gitlab", "jenkins", "linux", "ubuntu", "nginx", "prometheus", "grafana", "devops", "ansible", "cloud"];
  const coreSet = ["data structures", "dsa", "algorithms", "system design", "microservices", "oop", "object oriented", "unit testing", "pytest", "jest", "postman", "git", "github", "clean architecture", "design patterns", "multithreading", "concurrency", "asynchronous"];

  const categories: SkillCategory[] = [
    { name: "Programming Languages", icon: Code2, color: "text-blue-600 bg-blue-500/10 border-blue-500/20", items: [] },
    { name: "Frameworks & Web Technologies", icon: Terminal, color: "text-purple-600 bg-purple-500/10 border-purple-500/20", items: [] },
    { name: "Databases & Storage Systems", icon: Database, color: "text-emerald-600 bg-emerald-500/10 border-emerald-500/20", items: [] },
    { name: "Cloud, Containers & DevOps", icon: Cloud, color: "text-sky-600 bg-sky-500/10 border-sky-500/20", items: [] },
    { name: "Core CS, Architecture & Tools", icon: Cpu, color: "text-amber-600 bg-amber-500/10 border-amber-500/20", items: [] },
  ];

  const seen = new Set<string>();

  for (const s of rawSkills) {
    const trimmed = s.trim();
    const lower = trimmed.toLowerCase();
    if (JUNK_SKILL_TOKENS.has(lower) || lower.length < 2 || seen.has(lower)) {
      continue;
    }
    seen.add(lower);

    if (langSet.some((k) => lower === k || lower.startsWith(k + " ") || lower.endsWith(" " + k))) {
      categories[0].items.push(trimmed);
    } else if (fwSet.some((k) => lower.includes(k))) {
      categories[1].items.push(trimmed);
    } else if (dbSet.some((k) => lower.includes(k))) {
      categories[2].items.push(trimmed);
    } else if (cloudSet.some((k) => lower.includes(k))) {
      categories[3].items.push(trimmed);
    } else if (coreSet.some((k) => lower.includes(k))) {
      categories[4].items.push(trimmed);
    } else {
      categories[4].items.push(trimmed);
    }
  }

  return categories.filter((c) => c.items.length > 0);
}

export function MasterResume() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const targetJobId = searchParams.get("targetJobId") || searchParams.get("jobId");
  const targetRole = searchParams.get("targetRole") || searchParams.get("role");
  const redirectUrl = searchParams.get("redirect");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [expandedSkillGroups, setExpandedSkillGroups] = useState<Record<string, boolean>>({});
  const [showLayoutFix, setShowLayoutFix] = useState(false);

  const { data: resume, isLoading } = useQuery({
    queryKey: ["master-resume"],
    queryFn: getMasterResume,
  });

  const upload = useMutation({
    mutationFn: uploadResume,
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["master-resume"] });
      queryClient.invalidateQueries({ queryKey: ["matches"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["skill-gaps"] });
      queryClient.invalidateQueries({ queryKey: ["career-alignment"] });
      toast.success("Master resume parsed and audited across 4 ATS pillars!");
      if (targetJobId) {
        toast.info("Resuming tailoring for your target opportunity…");
        navigate(`/resume/tailor/${targetJobId}`);
      } else if (targetRole) {
        toast.info(`Evaluating your resume against ${targetRole}…`);
        navigate(`/growth/skill-gaps?role=${encodeURIComponent(targetRole)}`);
      } else if (redirectUrl) {
        navigate(redirectUrl);
      }
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail ?? "Upload failed.";
      setError(msg);
      toast.error(msg);
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) upload.mutate(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      if (file.name.endsWith(".pdf") || file.name.endsWith(".docx")) {
        upload.mutate(file);
      } else {
        toast.error("Please upload a .pdf or .docx document.");
      }
    }
  }

  // 4 Pillar Scores from Backend
  const parseabilityScore = resume?.parseability.score ?? 0;
  const recruiterScore = resume?.recruiter_impact.score ?? 0;
  const actionVerbScore = resume?.action_verbs?.score ?? (resume?.recruiter_impact.weak_verb_bullets === 0 ? 95 : 70);
  const skillsDepthScore = resume?.skills_depth?.score ?? 80;

  const quantRate = resume?.recruiter_impact.quantification_rate ?? 0;
  const weakVerbCount = resume?.action_verbs?.weak_verb_bullets ?? resume?.recruiter_impact.weak_verb_bullets ?? 0;
  const powerVerbRate = resume?.action_verbs?.power_verb_rate ?? (weakVerbCount === 0 ? 1.0 : 0.6);
  const hasEmail = Boolean(resume?.parseability.contact_info_found?.email);
  const hasPhone = Boolean(resume?.parseability.contact_info_found?.phone);
  const isMultiCol = Boolean(resume?.parseability.likely_multi_column);
  const rawSkills = resume?.parsed.skills ?? EMPTY_SKILLS;

  const categorizedSkills = useMemo(() => {
    return categorizeAndFilterSkills(rawSkills);
  }, [rawSkills]);

  const validTechnicalSkillCount = resume?.skills_depth?.verified_skills_count ?? categorizedSkills.reduce((acc, cat) => acc + cat.items.length, 0);
  const domainCoverageCount = resume?.skills_depth?.domain_coverage_count ?? categorizedSkills.length;

  // Strict Enterprise Formula from Backend
  const strictATSScore = resume?.strict_ats_score ?? Math.round(
    parseabilityScore * 0.30 + recruiterScore * 0.30 + actionVerbScore * 0.20 + skillsDepthScore * 0.20
  );

  const atsStatus = resume?.ats_status ?? (
    strictATSScore >= 80
      ? { status: "passed", label: "PASSED ATS FILTER — Shortlist Ready", color: "text-signal-700 bg-signal-500/10 border-signal-500/30" }
      : strictATSScore >= 65
      ? { status: "review", label: "REVIEW QUEUE — Optimization Recommended", color: "text-amber-700 bg-amber-500/10 border-amber-500/30" }
      : { status: "at_risk", label: "AT RISK OF AUTO-REJECTION — Critical Issues Found", color: "text-alert-700 bg-alert-600/10 border-alert-600/30" }
  );

  const StatusIcon = atsStatus.status === "passed" ? CheckCircle2 : atsStatus.status === "review" ? AlertTriangle : XCircle;

  if (isLoading) {
    return (
      <div className="p-12 text-center">
        <span className="inline-block w-4 h-4 rounded-full bg-signal-500 animate-pulse mb-3" />
        <p className="text-sm text-ink-600 font-medium">Analyzing Master Resume against enterprise ATS benchmarks…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full min-w-0 max-w-5xl space-y-5">
      {/* Header and top-level actions */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`rounded-xl border bg-white px-4 py-4 shadow-[0_2px_8px_rgba(0,0,0,0.04)] transition-all sm:px-5 ${
          isDragging ? "border-signal-500 bg-signal-500/5 ring-2 ring-signal-500/20" : "border-slate-200"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx"
          onChange={handleFileChange}
          className="hidden"
        />
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <h1 className="font-display text-2xl font-bold text-ink-900">Master Resume</h1>
            <p className="mt-0.5 text-sm text-ink-500">
            Enterprise 4-Pillar ATS benchmark, strict pass/fail filtering evaluation, and categorized competencies.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {resume && (
              <Link
                to="/resume/tailor-custom"
                className="inline-flex h-10 items-center justify-center gap-1.5 rounded-lg border border-signal-500/25 bg-signal-500 px-3.5 text-xs font-bold text-white shadow-xs transition-colors hover:border-signal-600 hover:bg-signal-600"
              >
                <FileText size={14} />
                Paste JD &amp; Tailor
              </Link>
            )}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={upload.isPending}
            className="group inline-flex h-10 items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-ink-800 shadow-2xs transition-all hover:border-signal-500/50 hover:bg-slate-50 hover:text-signal-800 disabled:cursor-wait disabled:opacity-60"
          >
            <UploadCloud size={15} className={upload.isPending ? "animate-pulse-soft text-signal-600" : "text-signal-600 transition-transform group-hover:-translate-y-0.5"} />
            <span>{upload.isPending ? "Uploading & Analyzing…" : resume ? "Upload Updated Resume" : "Upload Master Resume"}</span>
            <span className="ml-0.5 flex items-center gap-1 border-l border-slate-200 pl-2">
              <span className="rounded border border-slate-200 bg-slate-50 px-1 py-0.5 text-[9px] font-bold text-ink-600">PDF</span>
              <span className="rounded border border-slate-200 bg-slate-50 px-1 py-0.5 text-[9px] font-bold text-ink-600">DOCX</span>
            </span>
          </button>
          </div>
        </div>
        {(resume || upload.isPending || isDragging) && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-2.5">
            {resume && (
              <span className="text-[11px] font-medium text-ink-500">
                Version {resume.version} · {resume.file_type.toUpperCase()}
              </span>
            )}
            {upload.isPending ? (
              <span className="text-xs font-medium text-signal-700 animate-pulse">
                Extracting text and running the 4-pillar recruiter audit…
              </span>
            ) : isDragging ? (
              <span className="text-xs font-semibold text-signal-700">Drop your PDF or DOCX to upload and analyze</span>
            ) : (
              <span className="text-[11px] text-ink-400">Drop a PDF or DOCX here to upload</span>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-xl bg-alert-600/10 border border-alert-600/20 p-4 text-xs text-alert-700 flex items-start gap-2.5 shadow-2xs">
          <AlertCircle size={16} className="shrink-0 mt-0.5" />
          <div>
            <strong className="font-bold">Upload Error:</strong> {error}
          </div>
        </div>
      )}

      {resume && (
        <div className="space-y-6">
          {/* ========================================================================= */}
          {/* 1. STRICT ENTERPRISE ATS SCORE HERO CARD                                 */}
          {/* ========================================================================= */}
          <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_2px_8px_rgba(0,0,0,0.04)] sm:p-6">
            <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
              <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-6">
                <ScoreGauge value={strictATSScore} />
                <div className="min-w-0">
                  <div className={`mb-2 flex items-start gap-2 rounded-xl border p-3 text-xs font-bold ${atsStatus.color} ${
                    atsStatus.status === "review"
                      ? "shadow-[0_0_0_3px_rgba(245,158,11,0.06)]"
                      : ""
                  }`}>
                    <StatusIcon size={15} className="mt-0.5 shrink-0" />
                    <span>{atsStatus.label}</span>
                  </div>
                  <h2 className="font-display text-lg font-bold text-ink-950">
                    Enterprise ATS Screening Benchmark
                  </h2>
                  <p className="text-xs text-ink-500 max-w-md leading-relaxed mt-0.5">
                    Evaluated strictly against Workday, Taleo, and Greenhouse screening filters: single-column layout, contact detection, bullet metrics, and core skill breadth.
                  </p>
                </div>
              </div>

              <div className="w-full shrink-0 rounded-xl border border-slate-200 bg-slate-50/70 p-3 text-xs sm:p-4 lg:w-[270px]">
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-ink-600">Layout Format</span>
                    <span className={`rounded-full border px-2 py-1 text-[10px] font-bold ${isMultiCol ? "border-amber-200 bg-amber-50 text-amber-800" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
                      {isMultiCol ? "Multi-Column" : "Single Column ✓"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3 border-t border-slate-200 pt-2">
                    <span className="text-ink-600">Contact Data</span>
                    <span className={`rounded-full border px-2 py-1 text-[10px] font-bold ${hasEmail && hasPhone ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-rose-200 bg-rose-50 text-rose-700"}`}>
                      {hasEmail && hasPhone ? "Complete ✓" : "Incomplete"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3 border-t border-slate-200 pt-2">
                    <span className="text-ink-600">Quantified Impact</span>
                    <span className={`rounded-full border px-2 py-1 text-[10px] font-bold ${quantRate >= 0.5 ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-800"}`}>
                      {Math.round(quantRate * 100)}% bullets
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ========================================================================= */}
          {/* 2. 4-PILLAR QUALITY BREAKDOWN (All 4 Distinct 0-100 Scores)                */}
          {/* ========================================================================= */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-ink-500 mb-3 flex items-center gap-1.5">
              <Award size={14} className="text-signal-600" /> 4-Pillar Enterprise ATS Audit
            </h3>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {/* Pillar 1: Parseability */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-[0_2px_8px_rgba(0,0,0,0.04)] transition-shadow hover:shadow-md">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">1. ATS Parseability</span>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-bold tabular-nums ${getScoreTone(parseabilityScore).badge}`}>
                    {parseabilityScore}/100
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  {resume.parseability.issues.length === 0 ? "Flawless single-column text extraction." : `${resume.parseability.issues.length} structural warnings detected.`}
                </p>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label="ATS Parseability" aria-valuemin={0} aria-valuemax={100} aria-valuenow={parseabilityScore}>
                  <div className={`h-full rounded-full transition-all ${getScoreTone(parseabilityScore).bar}`} style={{ width: `${Math.max(0, Math.min(parseabilityScore, 100))}%` }} />
                </div>
              </div>

              {/* Pillar 2: Recruiter Bullet Impact */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-[0_2px_8px_rgba(0,0,0,0.04)] transition-shadow hover:shadow-md">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">2. Recruiter Impact</span>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-bold tabular-nums ${getScoreTone(recruiterScore).badge}`}>
                    {recruiterScore}/100
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  {Math.round(quantRate * 100)}% bullets contain quantified measurable metrics.
                </p>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label="Recruiter Impact" aria-valuemin={0} aria-valuemax={100} aria-valuenow={recruiterScore}>
                  <div className={`h-full rounded-full transition-all ${getScoreTone(recruiterScore).bar}`} style={{ width: `${Math.max(0, Math.min(recruiterScore, 100))}%` }} />
                </div>
              </div>

              {/* Pillar 3: Action Verb Strength */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-[0_2px_8px_rgba(0,0,0,0.04)] transition-shadow hover:shadow-md">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">3. Action Verbs</span>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-bold tabular-nums ${getScoreTone(actionVerbScore).badge}`}>
                    {actionVerbScore}/100
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  {weakVerbCount === 0 ? `${Math.round(powerVerbRate * 100)}% strong active verbs.` : `${weakVerbCount} passive phrasing issues.`}
                </p>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label="Action Verbs" aria-valuemin={0} aria-valuemax={100} aria-valuenow={actionVerbScore}>
                  <div className={`h-full rounded-full transition-all ${getScoreTone(actionVerbScore).bar}`} style={{ width: `${Math.max(0, Math.min(actionVerbScore, 100))}%` }} />
                </div>
              </div>

              {/* Pillar 4: Technical Stack Depth */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-[0_2px_8px_rgba(0,0,0,0.04)] transition-shadow hover:shadow-md">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">4. Technical Stack</span>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-bold tabular-nums ${getScoreTone(skillsDepthScore).badge}`}>
                    {skillsDepthScore}/100
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  {validTechnicalSkillCount} skills across {domainCoverageCount}/5 engineering domains.
                </p>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label="Technical Stack" aria-valuemin={0} aria-valuemax={100} aria-valuenow={skillsDepthScore}>
                  <div className={`h-full rounded-full transition-all ${getScoreTone(skillsDepthScore).bar}`} style={{ width: `${Math.max(0, Math.min(skillsDepthScore, 100))}%` }} />
                </div>
              </div>
            </div>
          </div>

          {/* ========================================================================= */}
          {/* 3. IDENTIFIED TECHNICAL SKILLS (Separated Strictly by Lines / Groups)     */}
          {/* ========================================================================= */}
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_2px_8px_rgba(0,0,0,0.04)] sm:p-5">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-ink-100">
              <div className="flex items-center gap-2">
                <Layers size={18} className="text-signal-600" />
                <h3 className="font-display text-base font-bold text-ink-900">
                  Identified Technical Skills
                </h3>
              </div>
              <span className="text-xs font-semibold text-ink-600 bg-ink-50 px-2.5 py-1 rounded-full border border-ink-100">
                {validTechnicalSkillCount} Verified Competencies
              </span>
            </div>

            <p className="text-xs text-ink-500 mb-4">
              Categorized into distinct domain lines for clear ATS indexing and technical recruiter screening:
            </p>

            <div className="space-y-3">
              {categorizedSkills.map((cat) => {
                const Icon = cat.icon;
                const isExpanded = expandedSkillGroups[cat.name] ?? true;
                return (
                  <section key={cat.name} className="rounded-xl border border-slate-200 bg-slate-50/70 transition-colors hover:border-signal-500/30">
                    <button
                      type="button"
                      aria-expanded={isExpanded}
                      onClick={() => setExpandedSkillGroups((groups) => ({ ...groups, [cat.name]: !isExpanded }))}
                      className="flex w-full items-center justify-between gap-3 rounded-xl px-3 py-3 text-left transition-colors hover:bg-white/70"
                    >
                      <span className="flex min-w-0 items-center gap-2">
                        <Icon size={15} className="shrink-0 text-signal-700" />
                        <span className="truncate text-xs font-bold uppercase tracking-wider text-ink-900">{cat.name}</span>
                        <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold tabular-nums text-ink-600">{cat.items.length}</span>
                      </span>
                      <ChevronDown size={15} className={`shrink-0 text-ink-500 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                    </button>
                    {isExpanded && (
                      <div className="flex flex-wrap gap-2 border-t border-slate-200 px-3 py-3">
                        {cat.items.map((skill) => (
                          <span
                            key={skill}
                            className="interactive-chip inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-ink-800 shadow-2xs transition-all hover:border-signal-500/40 hover:bg-signal-50 hover:text-signal-800"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    )}
                  </section>
                );
              })}
            </div>
          </div>

          {/* ========================================================================= */}
          {/* 4. STRUCTURAL VERIFICATION & ATS SCAN FINDINGS                            */}
          {/* ========================================================================= */}
          {isMultiCol && (
            <div className="flex flex-col gap-3 rounded-xl border border-amber-300 bg-amber-50/80 p-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-start gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-amber-200 bg-white text-amber-700">
                  <AlertTriangle size={18} />
                </span>
                <div>
                  <h3 className="text-sm font-bold text-amber-950">Multi-Column Layout May Reduce ATS Accuracy</h3>
                  <p className="mt-1 text-xs leading-relaxed text-amber-900/80">
                    Some applicant tracking systems read columns out of order. A single-column layout improves the reliability of parsing your experience and contact details.
                  </p>
                  {showLayoutFix && (
                    <p className="mt-2 rounded-lg border border-amber-200 bg-white/80 p-2.5 text-[11px] leading-relaxed text-amber-950">
                      How to fix: move content into one left-aligned column, avoid tables and text boxes, and keep section headings in the normal document flow.
                    </p>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowLayoutFix((visible) => !visible)}
                aria-expanded={showLayoutFix}
                className="inline-flex min-h-9 shrink-0 items-center justify-center gap-1.5 self-start rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs font-semibold text-amber-900 transition-colors hover:bg-amber-100"
              >
                <Info size={13} />
                {showLayoutFix ? "Hide fix tip" : "How to Fix"}
              </button>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {/* Contact & Structure Checklist */}
            <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
              <h3 className="font-display text-sm text-ink-900 mb-3 flex items-center gap-2">
                <FileText size={16} className="text-signal-600" /> Structure & Contact Verification
              </h3>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                  <span className="flex items-center gap-2 text-ink-600">
                    <Mail size={13} className="text-ink-400" /> Email Address:
                  </span>
                  <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] font-bold ${hasEmail ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-rose-200 bg-rose-50 text-rose-700"}`}>
                    {hasEmail ? <CheckCircle2 size={11} /> : <AlertCircle size={11} />}
                    {hasEmail ? "Detected" : "Missing"}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                  <span className="flex items-center gap-2 text-ink-600">
                    <Phone size={13} className="text-ink-400" /> Phone Number:
                  </span>
                  <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] font-bold ${hasPhone ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-rose-200 bg-rose-50 text-rose-700"}`}>
                    {hasPhone ? <CheckCircle2 size={11} /> : <AlertCircle size={11} />}
                    {hasPhone ? "Detected" : "Missing"}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                  <span className="flex items-center gap-2 text-ink-600">
                    <Globe size={13} className="text-ink-400" /> Online Profiles / Links:
                  </span>
                  <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] font-bold ${resume.parseability.contact_info_found?.links ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-white text-slate-600"}`}>
                    {resume.parseability.contact_info_found?.links ? <CheckCircle2 size={11} /> : <Info size={11} />}
                    {resume.parseability.contact_info_found?.links ? "Detected" : "Optional"}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                  <span className="flex items-center gap-2 text-ink-600">
                    <FileText size={13} className="text-ink-400" /> Total Word Count:
                  </span>
                  <span className="font-semibold text-ink-800">
                    {resume.parseability.word_count} words (~{Math.max(1, Math.ceil(resume.parseability.word_count / 450))} page budget)
                  </span>
                </div>
              </div>
            </div>

            {/* Actionable 4-Pillar ATS Scan Findings */}
            <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
              <h3 className="font-display text-sm text-ink-900 mb-3 flex items-center gap-2">
                <AlertTriangle size={16} className="text-amber-600" /> 4-Pillar Scan Findings & Fixes
              </h3>

              {resume.parseability.issues.length === 0 &&
              resume.recruiter_impact.issues.length === 0 &&
              (!resume.action_verbs?.issues?.length) &&
              (!resume.skills_depth?.issues?.length) ? (
                <div className="p-4 bg-signal-500/5 rounded-lg border border-signal-500/20 text-center">
                  <Check size={20} className="text-signal-600 mx-auto mb-1" />
                  <p className="text-xs font-bold text-signal-800">Zero Critical ATS Flaws Found</p>
                  <p className="text-[11px] text-ink-500 mt-0.5">Your resume complies with 4-Pillar AST parsing standards.</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto pr-1 text-xs">
                  {resume.parseability.issues.map((iss, idx) => (
                    <div key={`pars-${idx}`} className="p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 flex items-start gap-2">
                      <AlertTriangle size={13} className="text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-amber-900 block text-[11px]">Layout: {iss.code}</span>
                        <p className="text-[11px] text-ink-600 leading-snug">{iss.message}</p>
                      </div>
                    </div>
                  ))}
                  {resume.recruiter_impact.issues.map((iss, idx) => (
                    <div key={`rec-${idx}`} className="p-2.5 rounded-lg bg-ink-50 border border-ink-200/60 flex items-start gap-2">
                      <Cpu size={13} className="text-ink-500 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-ink-900 block text-[11px]">Metrics Impact</span>
                        <p className="text-[11px] text-ink-700 leading-snug">{iss}</p>
                      </div>
                    </div>
                  ))}
                  {resume.action_verbs?.issues.map((iss, idx) => (
                    <div key={`act-${idx}`} className="p-2.5 rounded-lg bg-blue-500/5 border border-blue-500/20 flex items-start gap-2">
                      <Award size={13} className="text-blue-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-blue-900 block text-[11px]">Action Verbs</span>
                        <p className="text-[11px] text-ink-700 leading-snug">{iss}</p>
                      </div>
                    </div>
                  ))}
                  {resume.skills_depth?.issues.map((iss, idx) => (
                    <div key={`sk-${idx}`} className="p-2.5 rounded-lg bg-purple-500/5 border border-purple-500/20 flex items-start gap-2">
                      <Layers size={13} className="text-purple-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-purple-900 block text-[11px]">Technical Breadth</span>
                        <p className="text-[11px] text-ink-700 leading-snug">{iss}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
