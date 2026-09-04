import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { RequireAuth, RequireGuest } from "./routes/guards";

// Lazy load pages for fast initial page load and code splitting
const Login = lazy(() => import("./pages/auth/Login").then((m) => ({ default: m.Login })));
const Register = lazy(() => import("./pages/auth/Register").then((m) => ({ default: m.Register })));
const Onboarding = lazy(() => import("./pages/Onboarding").then((m) => ({ default: m.Onboarding })));
const Dashboard = lazy(() => import("./pages/Dashboard").then((m) => ({ default: m.Dashboard })));
const MasterResume = lazy(() => import("./pages/resume/MasterResume").then((m) => ({ default: m.MasterResume })));
const TailoredVersions = lazy(() => import("./pages/resume/TailoredVersions").then((m) => ({ default: m.TailoredVersions })));
const TailorReview = lazy(() => import("./pages/resume/TailorReview").then((m) => ({ default: m.TailorReview || m.default })));
const CustomTailor = lazy(() => import("./pages/resume/CustomTailor").then((m) => ({ default: m.CustomTailor })));
const Jobs = lazy(() => import("./pages/opportunities/Jobs").then((m) => ({ default: m.Jobs })));
const Internships = lazy(() => import("./pages/opportunities/Internships").then((m) => ({ default: m.Internships })));
const Saved = lazy(() => import("./pages/opportunities/Saved").then((m) => ({ default: m.Saved })));
const Applications = lazy(() => import("./pages/opportunities/Applications").then((m) => ({ default: m.Applications })));
const JobDetail = lazy(() => import("./pages/opportunities/JobDetail").then((m) => ({ default: m.JobDetail })));
const SkillGaps = lazy(() => import("./pages/growth/SkillGaps").then((m) => ({ default: m.SkillGaps })));
const LearningRoadmap = lazy(() => import("./pages/growth/LearningRoadmap").then((m) => ({ default: m.LearningRoadmap })));
const Interview = lazy(() => import("./pages/growth/Interview").then((m) => ({ default: m.Interview })));
const Copilot = lazy(() => import("./pages/Copilot").then((m) => ({ default: m.Copilot })));
const Settings = lazy(() => import("./pages/Settings").then((m) => ({ default: m.Settings })));

function PageLoader() {
  return (
    <div className="flex items-center justify-center p-12">
      <div className="flex flex-col items-center gap-3">
        <span className="w-6 h-6 rounded-full border-2 border-signal-500 border-t-transparent animate-spin" />
        <span className="text-xs text-ink-500 font-medium">Loading workspace…</span>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route element={<RequireGuest />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>

        <Route path="/onboarding" element={<Onboarding />} />

        <Route element={<RequireAuth />}>
          <Route element={<AppShell />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />

            <Route path="/resume/master" element={<MasterResume />} />
            <Route path="/resume/versions" element={<TailoredVersions />} />
            <Route path="/resume/tailor/:jobId" element={<TailorReview />} />
            <Route path="/resume/tailor-custom" element={<CustomTailor />} />

            <Route path="/opportunities/jobs" element={<Jobs />} />
            <Route path="/opportunities/internships" element={<Internships />} />
            <Route path="/opportunities/saved" element={<Saved />} />
            <Route path="/opportunities/job/:jobId" element={<JobDetail />} />

            <Route path="/applications" element={<Applications />} />
            <Route path="/applications/*" element={<Applications />} />

            <Route path="/growth/skill-gaps" element={<SkillGaps />} />
            <Route path="/growth/roadmap" element={<LearningRoadmap />} />
            <Route path="/growth/roadmap/:jobId" element={<LearningRoadmap />} />
            <Route path="/growth/interview" element={<Interview />} />
            <Route path="/growth/interview/:jobId" element={<Interview />} />

            <Route path="/copilot" element={<Copilot />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/profile" element={<Settings />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  );
}
