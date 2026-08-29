import { useRef, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  UploadCloud, FileText, Check, AlertCircle, AlertTriangle, Layers,
  Code2, Database, Cloud, Terminal, Cpu, CheckCircle2, XCircle, Award, Globe, Phone, Mail,
} from "lucide-react";
import { getMasterResume, uploadResume } from "../../lib/resume";
import { ScoreRing } from "../../components/ui/ScoreRing";
import { useToast } from "../../context/ToastContext";

const JUNK_SKILL_TOKENS = new Set([
  "team player", "leadership", "time management", "detail oriented",
  "self motivated", "quick learner", "hard worker", "passionate", "good listener",
  "communication", "skills", "knowledge", "proficient", "familiar", "working", "building",
  "responsible", "assisted", "learning", "enthusiastic", "hardworking", "problem solving",
]);

interface SkillCategory {
  name: string;
  icon: any;
  color: string;
  items: string[];
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
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

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
      toast.success("Master resume parsed and audited across 4 ATS pillars!");
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
  const rawSkills = resume?.parsed.skills ?? [];

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
    <div className="max-w-3xl space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl text-ink-900">Master Resume</h1>
          <p className="text-sm text-ink-500">
            Enterprise 4-Pillar ATS benchmark, strict pass/fail filtering evaluation, and categorized competencies.
          </p>
        </div>
        {resume && (
          <Link
            to="/resume/tailor-custom"
            className="shrink-0 rounded-lg bg-signal-500 px-3.5 py-2 text-xs font-bold text-white shadow-xs transition-colors hover:bg-signal-600"
          >
            Paste JD &amp; Tailor
          </Link>
        )}
      </div>

      {/* Upload button bar / dropzone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`flex items-center justify-between gap-4 flex-wrap bg-white p-4 rounded-xl border transition-colors shadow-xs ${
          isDragging ? "border-signal-500 bg-signal-500/5 ring-2 ring-signal-500/20" : "border-ink-100"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx"
          onChange={handleFileChange}
          className="hidden"
        />
        <div className="flex items-center gap-3">
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={upload.isPending}
            className="group flex items-center gap-2 rounded-lg bg-ink-950 hover:bg-ink-900 text-white px-4 py-2.5 text-xs font-semibold disabled:opacity-60 transition-all active:scale-[0.98] shadow-xs"
          >
            <UploadCloud size={16} className={upload.isPending ? "animate-pulse-soft" : "group-hover:-translate-y-0.5 transition-transform text-signal-400"} />
            {upload.isPending ? "Uploading & Analyzing…" : resume ? "Upload Updated Resume (PDF/DOCX)" : "Upload Master Resume (PDF/DOCX)"}
          </button>
          {resume && (
            <span className="text-xs text-ink-500 font-mono">
              Version {resume.version} • {resume.file_type.toUpperCase()}
            </span>
          )}
        </div>

        {upload.isPending && (
          <span className="text-xs text-signal-600 font-medium animate-pulse">
            Extracting text AST & running 4-Pillar recruiter audit…
          </span>
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
          <div className="rounded-2xl border border-ink-100 bg-white p-6 shadow-sm overflow-hidden relative card-hover">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div className="flex items-center gap-5">
                <ScoreRing value={strictATSScore} size={92} strokeWidth={8} label="Strict ATS Score" />
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-full border ${atsStatus.color}`}>
                      <StatusIcon size={13} /> {atsStatus.label}
                    </span>
                  </div>
                  <h2 className="font-display text-lg font-bold text-ink-950">
                    Enterprise ATS Screening Benchmark
                  </h2>
                  <p className="text-xs text-ink-500 max-w-md leading-relaxed mt-0.5">
                    Evaluated strictly against Workday, Taleo, and Greenhouse screening filters: single-column layout, contact detection, bullet metrics, and core skill breadth.
                  </p>
                </div>
              </div>

              <div className="bg-ink-50/80 p-3 rounded-xl border border-ink-100/80 text-xs space-y-1.5 w-full md:w-auto shrink-0 font-medium text-ink-700">
                <div className="flex items-center justify-between gap-4">
                  <span>Layout Format:</span>
                  <span className={isMultiCol ? "text-alert-600 font-bold" : "text-signal-700 font-bold"}>
                    {isMultiCol ? "Multi-Column ⚠️" : "Single Column ✓"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Contact Data:</span>
                  <span className={hasEmail && hasPhone ? "text-signal-700 font-bold" : "text-alert-600 font-bold"}>
                    {hasEmail && hasPhone ? "Complete ✓" : "Incomplete ⚠️"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Quantified Impact:</span>
                  <span className={quantRate >= 0.5 ? "text-signal-700 font-bold" : "text-amber-600 font-bold"}>
                    {Math.round(quantRate * 100)}% Bullets
                  </span>
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
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              {/* Pillar 1: Parseability */}
              <div className="bg-white p-4 rounded-xl border border-ink-100 shadow-2xs card-hover">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">1. ATS Parseability</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${parseabilityScore >= 80 ? "bg-signal-500/10 text-signal-700" : "bg-amber-500/10 text-amber-700"}`}>
                    {parseabilityScore}/100
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  {resume.parseability.issues.length === 0 ? "Flawless single-column text extraction." : `${resume.parseability.issues.length} structural warnings detected.`}
                </p>
              </div>

              {/* Pillar 2: Recruiter Bullet Impact */}
              <div className="bg-white p-4 rounded-xl border border-ink-100 shadow-2xs card-hover">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">2. Recruiter Impact</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${recruiterScore >= 75 ? "bg-signal-500/10 text-signal-700" : "bg-amber-500/10 text-amber-700"}`}>
                    {recruiterScore}/100
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  {Math.round(quantRate * 100)}% bullets contain quantified measurable metrics.
                </p>
              </div>

              {/* Pillar 3: Action Verb Strength */}
              <div className="bg-white p-4 rounded-xl border border-ink-100 shadow-2xs card-hover">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">3. Action Verbs</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${actionVerbScore >= 80 ? "bg-signal-500/10 text-signal-700" : "bg-amber-500/10 text-amber-700"}`}>
                    {actionVerbScore}/100
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  {weakVerbCount === 0 ? `${Math.round(powerVerbRate * 100)}% strong active verbs.` : `${weakVerbCount} passive phrasing issues.`}
                </p>
              </div>

              {/* Pillar 4: Technical Stack Depth */}
              <div className="bg-white p-4 rounded-xl border border-ink-100 shadow-2xs card-hover">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">4. Technical Stack</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${skillsDepthScore >= 75 ? "bg-signal-500/10 text-signal-700" : "bg-amber-500/10 text-amber-700"}`}>
                    {skillsDepthScore}/100
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  {validTechnicalSkillCount} skills across {domainCoverageCount}/5 engineering domains.
                </p>
              </div>
            </div>
          </div>

          {/* ========================================================================= */}
          {/* 3. IDENTIFIED TECHNICAL SKILLS (Separated Strictly by Lines / Groups)     */}
          {/* ========================================================================= */}
          <div className="rounded-2xl border border-ink-100 bg-white p-5 shadow-xs card-hover">
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
                return (
                  <div key={cat.name} className="p-3 rounded-xl bg-ink-50/50 border border-ink-100/70 hover:border-signal-500/40 transition-colors">
                    <div className="flex items-center gap-2 mb-2">
                      <Icon size={14} className="text-ink-600" />
                      <span className="text-xs font-bold text-ink-900 uppercase tracking-wider">{cat.name}</span>
                      <span className="text-[10px] text-ink-400 font-mono">({cat.items.length})</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {cat.items.map((skill) => (
                        <span
                          key={skill}
                          className="interactive-chip px-2.5 py-1 rounded-lg text-xs font-medium bg-white text-ink-800 border border-ink-200/80 shadow-2xs"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ========================================================================= */}
          {/* 4. STRUCTURAL VERIFICATION & ATS SCAN FINDINGS                            */}
          {/* ========================================================================= */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Contact & Structure Checklist */}
            <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
              <h3 className="font-display text-sm text-ink-900 mb-3 flex items-center gap-2">
                <FileText size={16} className="text-signal-600" /> Structure & Contact Verification
              </h3>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-ink-50 border border-ink-100/60">
                  <span className="flex items-center gap-2 text-ink-600">
                    <Mail size={13} className="text-ink-400" /> Email Address:
                  </span>
                  <span className={hasEmail ? "font-semibold text-signal-700" : "font-semibold text-alert-600"}>
                    {hasEmail ? "Detected ✓" : "Missing ⚠️"}
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-ink-50 border border-ink-100/60">
                  <span className="flex items-center gap-2 text-ink-600">
                    <Phone size={13} className="text-ink-400" /> Phone Number:
                  </span>
                  <span className={hasPhone ? "font-semibold text-signal-700" : "font-semibold text-alert-600"}>
                    {hasPhone ? "Detected ✓" : "Missing ⚠️"}
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-ink-50 border border-ink-100/60">
                  <span className="flex items-center gap-2 text-ink-600">
                    <Globe size={13} className="text-ink-400" /> Online Profiles / Links:
                  </span>
                  <span className="font-semibold text-signal-700">
                    {resume.parseability.contact_info_found?.links ? "Detected ✓" : "Optional"}
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-ink-50 border border-ink-100/60">
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
