import { useRef, useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  UploadCloud, FileText, CheckCircle2, AlertCircle,
  ShieldCheck, Cpu, Layers, Award, Terminal, Database,
  Cloud, Code2, Check, AlertTriangle, XCircle, Mail, Phone, Globe,
} from "lucide-react";
import { getMasterResume, uploadResume } from "../../lib/resume";
import { ScoreRing } from "../../components/ui/ScoreRing";

// Filter out generic filler words and noise
const JUNK_SKILL_TOKENS = new Set([
  "experience", "development", "management", "developer", "engineering", "code", "coding",
  "software", "web", "application", "applications", "project", "projects", "team", "teamwork",
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
      // Default to Core CS & Tools if technical, otherwise categorize into closest
      categories[4].items.push(trimmed);
    }
  }

  return categories.filter((c) => c.items.length > 0);
}

export function MasterResume() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

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
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail ?? "Upload failed.");
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) upload.mutate(file);
  }

  // Compute Strict Enterprise ATS Score
  const parseabilityScore = resume?.parseability.score ?? 0;
  const recruiterScore = resume?.recruiter_impact.score ?? 0;
  const quantRate = resume?.recruiter_impact.quantification_rate ?? 0;
  const weakVerbCount = resume?.recruiter_impact.weak_verb_bullets ?? 0;
  const totalBullets = resume?.recruiter_impact.bullets_analyzed ?? 0;
  const hasEmail = Boolean(resume?.parseability.contact_info_found?.email);
  const hasPhone = Boolean(resume?.parseability.contact_info_found?.phone);
  const isMultiCol = Boolean(resume?.parseability.likely_multi_column);
  const rawSkills = resume?.parsed.skills ?? [];

  const categorizedSkills = useMemo(() => {
    return categorizeAndFilterSkills(rawSkills);
  }, [rawSkills]);

  const validTechnicalSkillCount = categorizedSkills.reduce((acc, cat) => acc + cat.items.length, 0);

  // Strict Enterprise Formula
  let strictATSScore = 100;
  if (!hasEmail) strictATSScore -= 20;
  if (!hasPhone) strictATSScore -= 10;
  if (isMultiCol) strictATSScore -= 25;
  if (quantRate < 0.3) strictATSScore -= 25;
  else if (quantRate < 0.6) strictATSScore -= 12;
  if (weakVerbCount > 0) strictATSScore -= Math.min(20, Math.round((weakVerbCount / Math.max(1, totalBullets)) * 30));
  if (validTechnicalSkillCount < 5) strictATSScore -= 25;
  else if (validTechnicalSkillCount < 10) strictATSScore -= 10;
  if (parseabilityScore < 70) strictATSScore -= 15;

  strictATSScore = Math.max(15, Math.min(100, strictATSScore));

  const atsStatus = strictATSScore >= 80
    ? { label: "PASSED ATS FILTER — Shortlist Ready", color: "text-signal-700 bg-signal-500/10 border-signal-500/30", icon: CheckCircle2 }
    : strictATSScore >= 65
    ? { label: "REVIEW QUEUE — Optimization Recommended", color: "text-amber-700 bg-amber-500/10 border-amber-500/30", icon: AlertTriangle }
    : { label: "AT RISK OF AUTO-REJECTION — Critical Issues Found", color: "text-alert-700 bg-alert-600/10 border-alert-600/30", icon: XCircle };

  const StatusIcon = atsStatus.icon;

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
            Enterprise ATS benchmark, strict pass/fail filtering evaluation, and categorized competencies.
          </p>
        </div>
      </div>

      {/* Upload button bar */}
      <div className="flex items-center justify-between gap-4 flex-wrap bg-white p-4 rounded-xl border border-ink-100 shadow-xs">
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
            Extracting text AST & running recruiter audit…
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
          <div className="rounded-2xl border border-ink-100 bg-white p-6 shadow-sm overflow-hidden relative">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div className="flex items-center gap-5">
                <ScoreRing value={strictATSScore} size={92} strokeWidth={8} label="Strict ATS Score" />
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-full border ${atsStatus.color}`}>
                      <StatusIcon size={13} /> {atsStatus.label}
                    </span>
                  </div>
                  <h2 className="font-display text-lg text-ink-950">
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
          {/* 2. PARAMETERS THAT ACTUALLY MATTER (4 Core Quality Cards)                 */}
          {/* ========================================================================= */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-ink-500 mb-3 flex items-center gap-1.5">
              <Award size={14} className="text-signal-600" /> Core Parameters That Determine Shortlisting
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              {/* Card 1: Parseability */}
              <div className="bg-white p-4 rounded-xl border border-ink-100 shadow-2xs">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">ATS Parseability</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${parseabilityScore >= 80 ? "bg-signal-500/10 text-signal-700" : "bg-amber-500/10 text-amber-700"}`}>
                    {parseabilityScore}/100
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  {resume.parseability.issues.length === 0 ? "Flawless single-column text extraction." : `${resume.parseability.issues.length} structural warnings detected.`}
                </p>
              </div>

              {/* Card 2: Recruiter Bullet Impact */}
              <div className="bg-white p-4 rounded-xl border border-ink-100 shadow-2xs">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">Recruiter Impact</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${recruiterScore >= 75 ? "bg-signal-500/10 text-signal-700" : "bg-amber-500/10 text-amber-700"}`}>
                    {recruiterScore}/100
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  {Math.round(quantRate * 100)}% bullets contain quantified measurable metrics.
                </p>
              </div>

              {/* Card 3: Action Verb Strength */}
              <div className="bg-white p-4 rounded-xl border border-ink-100 shadow-2xs">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">Action Verbs</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${weakVerbCount === 0 ? "bg-signal-500/10 text-signal-700" : "bg-amber-500/10 text-amber-700"}`}>
                    {weakVerbCount === 0 ? "Strong" : `${weakVerbCount} Weak`}
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  {weakVerbCount === 0 ? "All bullets lead with strong active engineering verbs." : "Replace passive verbs with direct action terms."}
                </p>
              </div>

              {/* Card 4: Technical Breadth */}
              <div className="bg-white p-4 rounded-xl border border-ink-100 shadow-2xs">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-ink-600 uppercase tracking-wider">Technical Stack</span>
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-signal-500/10 text-signal-700">
                    {validTechnicalSkillCount} Skills
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">
                  Covering {categorizedSkills.length} core technical engineering domains.
                </p>
              </div>
            </div>
          </div>

          {/* ========================================================================= */}
          {/* 3. IDENTIFIED TECHNICAL SKILLS (Separated Strictly by Lines / Groups)     */}
          {/* ========================================================================= */}
          <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-ink-100">
              <div className="flex items-center gap-2">
                <Layers size={18} className="text-signal-600" />
                <h3 className="font-display text-base text-ink-900">
                  Identified Technical Skills
                </h3>
              </div>
              <span className="text-xs font-semibold text-ink-500 bg-ink-50 px-2.5 py-1 rounded-full">
                {validTechnicalSkillCount} Verified Competencies
              </span>
            </div>

            <p className="text-xs text-ink-500 mb-4">
              Categorized into distinct domain lines for clear ATS indexing and technical recruiter screening:
            </p>

            <div className="space-y-3.5">
              {categorizedSkills.map((cat) => {
                const Icon = cat.icon;
                return (
                  <div key={cat.name} className="p-3 rounded-lg bg-ink-50/50 border border-ink-100/70">
                    <div className="flex items-center gap-2 mb-2">
                      <Icon size={14} className="text-ink-600" />
                      <span className="text-xs font-bold text-ink-900 uppercase tracking-wider">{cat.name}</span>
                      <span className="text-[10px] text-ink-400 font-mono">({cat.items.length})</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {cat.items.map((skill) => (
                        <span
                          key={skill}
                          className="px-2.5 py-1 rounded-md text-xs font-medium bg-white text-ink-800 border border-ink-200 shadow-2xs"
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
          {/* 4. RESUME DETAILS & STRUCTURAL AUDIT BREAKDOWN                             */}
          {/* ========================================================================= */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Extracted Contact Info & Header Details */}
            <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
              <h3 className="font-display text-sm text-ink-900 mb-3 flex items-center gap-2">
                <ShieldCheck size={16} className="text-signal-600" /> Contact & Header Integrity
              </h3>

              <div className="space-y-2.5 text-xs">
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-ink-50 border border-ink-100/60">
                  <span className="flex items-center gap-2 text-ink-600">
                    <Mail size={13} className="text-ink-400" /> Email Address:
                  </span>
                  <span className={`font-semibold ${hasEmail ? "text-signal-700" : "text-alert-600 font-bold"}`}>
                    {hasEmail ? "Detected ✓" : "Missing ❌"}
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-ink-50 border border-ink-100/60">
                  <span className="flex items-center gap-2 text-ink-600">
                    <Phone size={13} className="text-ink-400" /> Phone Number:
                  </span>
                  <span className={`font-semibold ${hasPhone ? "text-signal-700" : "text-alert-600 font-bold"}`}>
                    {hasPhone ? "Detected ✓" : "Missing ❌"}
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

            {/* Actionable ATS Audit Issues */}
            <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
              <h3 className="font-display text-sm text-ink-900 mb-3 flex items-center gap-2">
                <AlertTriangle size={16} className="text-amber-600" /> ATS Scan Findings & Fixes
              </h3>

              {resume.parseability.issues.length === 0 && resume.recruiter_impact.issues.length === 0 ? (
                <div className="p-4 bg-signal-500/5 rounded-lg border border-signal-500/20 text-center">
                  <Check size={20} className="text-signal-600 mx-auto mb-1" />
                  <p className="text-xs font-bold text-signal-800">Zero Critical ATS Flaws Found</p>
                  <p className="text-[11px] text-ink-500 mt-0.5">Your resume complies with single-column AST parsing standards.</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto pr-1 text-xs">
                  {resume.parseability.issues.map((iss, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 flex items-start gap-2">
                      <AlertTriangle size={13} className="text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-amber-900 block text-[11px]">{iss.code}</span>
                        <p className="text-[11px] text-ink-600 leading-snug">{iss.message}</p>
                      </div>
                    </div>
                  ))}
                  {resume.recruiter_impact.issues.map((iss, idx) => (
                    <div key={`rec-${idx}`} className="p-2.5 rounded-lg bg-ink-50 border border-ink-200/60 flex items-start gap-2">
                      <Cpu size={13} className="text-ink-500 shrink-0 mt-0.5" />
                      <p className="text-[11px] text-ink-700 leading-snug">{iss}</p>
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
