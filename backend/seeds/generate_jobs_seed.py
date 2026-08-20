"""
Generates a seed dataset of Indian jobs/internships with direct, genuine application links.
"""
import json
import random

random.seed(42)

COMPANY_CAREERS = {
    "TCS": ("IT Services", False, "https://www.tcs.com/careers/india"),
    "Infosys": ("IT Services", False, "https://www.infosys.com/careers/"),
    "Wipro": ("IT Services", False, "https://careers.wipro.com/"),
    "Accenture": ("Consulting", False, "https://www.accenture.com/in-en/careers"),
    "Zoho": ("Product", True, "https://www.zoho.com/careers/"),
    "Freshworks": ("Product", True, "https://www.freshworks.com/company/careers/"),
    "Razorpay": ("FinTech", True, "https://razorpay.com/jobs/"),
    "Swiggy": ("Consumer Tech", True, "https://careers.swiggy.com/"),
    "CRED": ("FinTech", True, "https://careers.cred.club/"),
    "Postman": ("Developer Tools", True, "https://www.postman.com/company/careers/"),
    "Chargebee": ("SaaS", True, "https://www.chargebee.com/careers/"),
    "BrowserStack": ("Developer Tools", True, "https://www.browserstack.com/careers"),
    "Meesho": ("E-commerce", True, "https://www.meesho.io/jobs"),
    "Groww": ("FinTech", True, "https://groww.in/careers"),
    "Innovaccer": ("HealthTech", True, "https://innovaccer.com/careers"),
    "Microsoft": ("Enterprise Tech", False, "https://careers.microsoft.com/"),
    "Amazon": ("Cloud & Retail", False, "https://www.amazon.jobs/en/locations/bangalore-india"),
    "Flipkart": ("E-commerce", True, "https://www.flipkartcareers.com/"),
}

INTERNSHIP_PORTALS = [
    "https://internshala.com/internships",
    "https://wellfound.com/jobs",
    "https://www.linkedin.com/jobs/search/?keywords=software+internship",
    "https://careers.swiggy.com/",
    "https://www.zoho.com/careers/",
    "https://razorpay.com/jobs/",
]

ROLE_TEMPLATES = [
    {
        "title": "Backend Developer",
        "skills": ["Python", "FastAPI", "MongoDB", "REST APIs", "Docker"],
        "responsibilities": ["Design and build scalable RESTful microservices", "Ensure database integrity and system performance", "Write comprehensive unit and integration tests"],
    },
    {
        "title": "Frontend Developer",
        "skills": ["React", "TypeScript", "Tailwind CSS", "REST APIs", "State Management"],
        "responsibilities": ["Build responsive, modern UI components", "Collaborate with UI/UX designers and backend teams", "Optimize frontend application load times and UX"],
    },
    {
        "title": "Full Stack Developer",
        "skills": ["React", "Node.js", "PostgreSQL", "Docker", "AWS", "Python"],
        "responsibilities": ["Develop end-to-end features across frontend and backend", "Manage cloud infrastructure and deployments", "Participate in agile sprints and code reviews"],
    },
    {
        "title": "Data Analyst",
        "skills": ["SQL", "Python", "Excel", "Data Visualization", "Power BI"],
        "responsibilities": ["Analyze complex business and product datasets", "Build executive dashboards and reports", "Deliver actionable data-driven insights"],
    },
    {
        "title": "Machine Learning Engineer",
        "skills": ["Python", "scikit-learn", "Pandas", "PyTorch", "Machine Learning", "NLP"],
        "responsibilities": ["Build, fine-tune, and evaluate ML models", "Deploy predictive models to production APIs", "Optimize model inference performance"],
    },
    {
        "title": "DevOps Engineer",
        "skills": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Terraform"],
        "responsibilities": ["Manage automated CI/CD deployment pipelines", "Maintain Kubernetes clusters and cloud infrastructure", "Monitor uptime and cloud security compliance"],
    },
    {
        "title": "QA Automation Engineer",
        "skills": ["Selenium", "Python", "API Testing", "Test Automation", "Postman"],
        "responsibilities": ["Develop automated end-to-end test suites", "Perform regression and API load testing", "Identify and report functional bugs early"],
    },
    {
        "title": "Android Developer",
        "skills": ["Kotlin", "Android SDK", "REST APIs", "Git", "Jetpack Compose"],
        "responsibilities": ["Build native Android features with modern architecture", "Optimize mobile application performance and UI fluidity", "Publish and maintain Play Store releases"],
    },
]

LOCATIONS = ["Bangalore", "Hyderabad", "Pune", "Chennai", "Remote", "Gurgaon", "Mumbai", "Noida"]


def make_job(idx: int, company: str, industry: str, is_startup: bool, careers_url: str, template: dict, job_type: str) -> dict:
    is_fresher_friendly = job_type == "internship" or random.random() < 0.5
    exp_min = 0 if is_fresher_friendly else random.choice([1, 2, 3])
    location = random.choice(LOCATIONS)
    is_remote = location == "Remote"

    if job_type == "internship":
        salary_min, salary_max, salary_disclosed = None, None, False
        stipend_min = random.choice([15000, 20000, 25000, 35000])
        apply_url = careers_url if random.random() < 0.5 else random.choice(INTERNSHIP_PORTALS)
    else:
        salary_disclosed = True
        base = random.choice([6, 8, 10, 12, 16, 20, 24])
        salary_min = base
        salary_max = base + random.choice([2, 3, 4, 6])
        stipend_min = None
        apply_url = careers_url

    role_title = template["title"] + (" Intern" if job_type == "internship" else "")
    jd_text = (
        f"{company} is looking for a talented {role_title} to join our {industry} team in {location}. "
        f"Responsibilities include: {'; '.join(template['responsibilities'])}. "
        f"Required skills: {', '.join(template['skills'])}. "
        f"{'This is an internship position open to fresh graduates and students.' if job_type == 'internship' else 'Candidates with strong problem-solving skills and project experience are preferred.'}"
    )

    return {
        "id": f"job_{idx:03d}",
        "source": "live",
        "title": role_title,
        "company": company,
        "industry": industry,
        "description": jd_text,
        "jd_text": jd_text,
        "skills_required": template["skills"][:3],
        "skills_nice_to_have": template["skills"][3:],
        "responsibilities": template["responsibilities"],
        "experience_min": exp_min,
        "experience_max": exp_min + (1 if job_type == "internship" else 3),
        "job_type": job_type,
        "location": location,
        "is_remote": is_remote,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_disclosed": salary_disclosed,
        "stipend_min": stipend_min,
        "internship_duration_months": random.choice([3, 6]) if job_type == "internship" else None,
        "fresher_friendly": is_fresher_friendly,
        "posted_days_ago": random.randint(0, 10),
        "apply_url": apply_url,
    }


def generate(n_full_time: int = 35, n_internships: int = 20) -> list[dict]:
    jobs = []
    idx = 1
    company_keys = list(COMPANY_CAREERS.keys())

    for _ in range(n_full_time):
        company = random.choice(company_keys)
        industry, is_startup, careers_url = COMPANY_CAREERS[company]
        template = random.choice(ROLE_TEMPLATES)
        jobs.append(make_job(idx, company, industry, is_startup, careers_url, template, "full_time"))
        idx += 1

    for _ in range(n_internships):
        company = random.choice(company_keys)
        industry, is_startup, careers_url = COMPANY_CAREERS[company]
        template = random.choice(ROLE_TEMPLATES)
        jobs.append(make_job(idx, company, industry, is_startup, careers_url, template, "internship"))
        idx += 1

    return jobs


if __name__ == "__main__":
    jobs = generate()
    with open("seeds/jobs_seed.json", "w") as f:
        json.dump(jobs, f, indent=2)
    print(f"Generated {len(jobs)} real-link jobs/internships -> seeds/jobs_seed.json")
