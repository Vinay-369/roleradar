import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { RequireAuth, RequireGuest } from "./routes/guards";
import { Login } from "./pages/auth/Login";
import { Register } from "./pages/auth/Register";
import { Onboarding } from "./pages/Onboarding";
import { Dashboard } from "./pages/Dashboard";
import { MasterResume } from "./pages/resume/MasterResume";
import { TailoredVersions } from "./pages/resume/TailoredVersions";
import { TailorReview } from "./pages/resume/TailorReview";
import { CustomTailor } from "./pages/resume/CustomTailor";
import { Jobs } from "./pages/opportunities/Jobs";
import { Internships } from "./pages/opportunities/Internships";
import { Saved } from "./pages/opportunities/Saved";
import { JobDetail } from "./pages/opportunities/JobDetail";
import { ApplicationQueue } from "./pages/applications/ApplicationQueue";
import { ApplicationTracker } from "./pages/applications/ApplicationTracker";
import { SkillGaps } from "./pages/growth/SkillGaps";
import { LearningRoadmap } from "./pages/growth/LearningRoadmap";
import { Interview } from "./pages/growth/Interview";
import { Copilot } from "./pages/Copilot";
import { Settings } from "./pages/Settings";

export default function App() {
  return (
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

        <Route path="/applications/queue" element={<ApplicationQueue />} />
        <Route path="/applications/tracker" element={<ApplicationTracker />} />

        <Route path="/growth/skill-gaps" element={<SkillGaps />} />
        <Route path="/growth/roadmap" element={<LearningRoadmap />} />
        <Route path="/growth/roadmap/:jobId" element={<LearningRoadmap />} />
        <Route path="/growth/interview" element={<Interview />} />
        <Route path="/growth/interview/:jobId" element={<Interview />} />

        <Route path="/copilot" element={<Copilot />} />
        <Route path="/settings" element={<Settings />} />
        </Route>
      </Route>
    </Routes>
  );
}
