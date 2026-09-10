/**
 * Standard comprehensive job and internship roles across the software industry.
 * Used for role dropdown selectors across Jobs, Internships, Interview Prep,
 * Learning Roadmap, and Skill Gap Analysis.
 */

export const ALL_JOB_ROLES: string[] = [
  "Full Stack Developer",
  "Software Engineer",
  "Backend Developer",
  "Frontend Developer",
  "Mobile App Developer",
  "Data Scientist",
  "Data Engineer",
  "Machine Learning Engineer",
  "AI / NLP Engineer",
  "Data Analyst",
  "DevOps Engineer",
  "Cloud Architect",
  "Cloud Engineer",
  "Site Reliability Engineer (SRE)",
  "Cybersecurity Analyst",
  "Cybersecurity Engineer",
  "Information Security Analyst",
  "QA / Test Automation Engineer",
  "Product Manager",
  "Technical Product Manager",
  "UI/UX Designer",
  "Graphic Designer",
  "Product Designer",
  "Digital Marketing Specialist",
  "SEO Specialist",
  "Financial Analyst",
  "Accountant",
  "HR Generalist",
  "Recruiter",
  "Operations Analyst",
  "Supply Chain Analyst",
  "Management Consultant",
  "Healthcare Analyst",
  "Mechanical Engineer",
  "Civil Engineer",
  "Electrical Engineer",
  "Robotics Engineer",
  "Architect",
  "Teacher",
  "Research Scientist",
  "Video Editor",
  "Systems Administrator",
  "Database Administrator (DBA)",
  "Embedded Systems Engineer",
  "Firmware Engineer",
  "Blockchain Developer",
  "Game Developer",
];

export const ALL_INTERNSHIP_ROLES: string[] = [
  "Software Engineering Intern",
  "Full Stack Intern",
  "Frontend Intern",
  "Backend Intern",
  "Mobile Developer Intern",
  "Data Science Intern",
  "Machine Learning / AI Intern",
  "Data Analyst Intern",
  "DevOps / Cloud Intern",
  "QA / Testing Intern",
  "Cybersecurity Intern",
  "UI/UX Design Intern",
  "Product Management Intern",
  "Systems Engineering Intern",
];

/**
 * Maps frontend dropdown role labels to canonical role keys.
 */
export const ROLE_TO_CANONICAL_KEYS: Record<string, string[]> = {
  // Job Roles
  "Full Stack Developer": ["full_stack_developer"],
  "Software Engineer": ["software_engineer"],
  "Backend Developer": ["backend_developer"],
  "Frontend Developer": ["frontend_developer"],
  "Mobile App Developer": ["mobile_developer"],
  "Data Scientist": ["data_scientist"],
  "Data Engineer": ["data_engineer"],
  "Machine Learning Engineer": ["machine_learning_engineer"],
  "AI / NLP Engineer": ["ai_engineer"],
  "Data Analyst": ["data_analyst"],
  "DevOps Engineer": ["devops_engineer"],
  "Cloud Architect": ["cloud_architect"],
  "Cloud Engineer": ["cloud_engineer"],
  "Site Reliability Engineer (SRE)": ["site_reliability_engineer"],
  "Cybersecurity Analyst": ["cybersecurity_analyst"],
  "Cybersecurity Engineer": ["security_engineer", "cybersecurity_engineer"],
  "Information Security Analyst": ["information_security_analyst"],
  "QA / Test Automation Engineer": ["qa_test_engineer"],
  "Product Manager": ["product_manager"],
  "Technical Product Manager": ["technical_product_manager"],
  "UI/UX Designer": ["ui_ux_designer"],
  "Graphic Designer": ["graphic_designer"],
  "Product Designer": ["product_designer"],
  "Digital Marketing Specialist": ["digital_marketing_specialist"],
  "SEO Specialist": ["seo_specialist"],
  "Financial Analyst": ["financial_analyst"],
  "Accountant": ["accountant"],
  "HR Generalist": ["hr_generalist"],
  "Recruiter": ["recruiter"],
  "Operations Analyst": ["operations_analyst"],
  "Supply Chain Analyst": ["supply_chain_analyst"],
  "Management Consultant": ["management_consultant"],
  "Healthcare Analyst": ["healthcare_analyst"],
  "Mechanical Engineer": ["mechanical_engineer"],
  "Civil Engineer": ["civil_engineer"],
  "Electrical Engineer": ["electrical_engineer"],
  "Robotics Engineer": ["robotics_engineer"],
  "Architect": ["architect"],
  "Teacher": ["teacher"],
  "Research Scientist": ["research_scientist"],
  "Video Editor": ["video_editor"],
  "Systems Administrator": ["systems_administrator"],
  "Database Administrator (DBA)": ["database_administrator"],
  "Embedded Systems Engineer": ["embedded_systems_engineer"],
  "Firmware Engineer": ["firmware_engineer"],
  "Blockchain Developer": ["blockchain_developer"],
  "Game Developer": ["game_developer"],

  // Internship Roles
  "Software Engineering Intern": ["software_engineer"],
  "Full Stack Intern": ["full_stack_developer"],
  "Frontend Intern": ["frontend_developer"],
  "Backend Intern": ["backend_developer"],
  "Mobile Developer Intern": ["mobile_developer"],
  "Data Science Intern": ["data_scientist"],
  "Machine Learning / AI Intern": ["machine_learning_engineer", "ai_engineer"],
  "Data Analyst Intern": ["data_analyst"],
  "DevOps / Cloud Intern": ["devops_engineer", "cloud_engineer"],
  "QA / Testing Intern": ["qa_test_engineer"],
  "Cybersecurity Intern": ["cybersecurity_analyst", "security_engineer"],
  "UI/UX Design Intern": ["ui_ux_designer", "product_designer"],
  "Product Management Intern": ["product_manager", "technical_product_manager"],
  "Systems Engineering Intern": ["systems_engineer", "systems_administrator"],
};

/**
 * Filters opportunities using canonical structured role classification produced by backend.
 * Falls back to fuzzy matching only if unclassified.
 */
export function matchesCanonicalRole(
  job: {
    canonical_role?: string | null;
    canonical_role_key?: string | null;
    role_domain?: string | null;
    job_title?: string;
  },
  selectedRole: string
): boolean {
  if (!selectedRole || selectedRole === "ALL") return true;

  const targetKeys = ROLE_TO_CANONICAL_KEYS[selectedRole];

  // 1. If backend resolved a canonical_role_key, match against canonical target keys
  if (job.canonical_role_key) {
    if (targetKeys && targetKeys.includes(job.canonical_role_key)) {
      return true;
    }
    if (job.canonical_role && job.canonical_role.toLowerCase() === selectedRole.toLowerCase()) {
      return true;
    }
    return false;
  }

  // 2. If canonical_role is present without key
  if (job.canonical_role) {
    if (job.canonical_role.toLowerCase() === selectedRole.toLowerCase()) {
      return true;
    }
    return false;
  }

  // 3. Fallback for unclassified custom jobs
  if (job.job_title) {
    const titleLower = job.job_title.toLowerCase();
    const selectedLower = selectedRole.toLowerCase().replace(/\bintern\b/i, "").trim();
    return titleLower.includes(selectedLower) || selectedLower.includes(titleLower);
  }

  return false;
}
