"""
Canonical Role Taxonomy & Role Intelligence Layer.
Provides domain-agnostic, structured competency benchmarks across all major career families.
Eliminates loose token matching, generic fallback pollution, and cross-domain contamination.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

RoleConfidence = Literal["HIGH", "MEDIUM", "LOW"]
BenchmarkProvenance = Literal[
    "ROLE_TAXONOMY",
    "MARKET_POSTINGS",
    "ROLE_TAXONOMY_AND_MARKET",
    "LIMITED_MARKET_EVIDENCE",
    "LOW_CONFIDENCE",
    "JOB_REQUIREMENTS",
]


@dataclass
class RoleCompetencyProfile:
    canonical_role: str
    domain: str
    subdomain: str
    aliases: list[str] = field(default_factory=list)
    core_competencies: list[str] = field(default_factory=list)
    common_competencies: list[str] = field(default_factory=list)
    optional_competencies: list[str] = field(default_factory=list)
    tools_technologies: list[str] = field(default_factory=list)
    knowledge_areas: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)
    typical_responsibilities: list[str] = field(default_factory=list)


# Generic tokens that must NEVER independently determine role identity
GENERIC_ROLE_TOKENS = {
    "engineer",
    "developer",
    "analyst",
    "manager",
    "specialist",
    "consultant",
    "coordinator",
    "associate",
    "officer",
    "director",
    "lead",
    "administrator",
    "technician",
    "intern",
    "expert",
    "assistant",
    "planner",
    "executive",
    "designer",
    "scientist",
    "practitioner",
    "advisor",
    "worker",
    "staff",
    "generalist",
}


# ==============================================================================
# AUTHORITATIVE ROLE TAXONOMY (23+ Major Career Families)
# ==============================================================================

ROLE_TAXONOMY: dict[str, RoleCompetencyProfile] = {
    # --------------------------------------------------------------------------
    # 1. Software Engineering
    # --------------------------------------------------------------------------
    "software_engineer": RoleCompetencyProfile(
        canonical_role="Software Engineer",
        domain="Software Engineering",
        subdomain="General & Systems",
        aliases=["Software Developer", "Software Development Engineer", "SDE", "SWE"],
        core_competencies=["Data Structures & Algorithms", "System Design", "Object-Oriented Programming", "REST APIs", "Git & Version Control"],
        common_competencies=["Unit Testing", "Microservices Architecture", "CI/CD Pipelines", "Code Review", "Agile Methodologies"],
        optional_competencies=["Distributed Systems", "Cloud Deployment", "Performance Optimization"],
        tools_technologies=["Git", "Docker", "Linux", "CI/CD", "SQL"],
        knowledge_areas=["Software Lifecycle", "Concurrency", "Database Design", "Design Patterns"],
        soft_skills=["Problem Solving", "Collaboration", "Technical Communication", "Code Ownership"],
    ),
    "backend_developer": RoleCompetencyProfile(
        canonical_role="Backend Developer",
        domain="Software Engineering",
        subdomain="Backend Systems",
        aliases=["Backend Engineer", "Server-Side Developer", "API Engineer"],
        core_competencies=["RESTful API Design", "Database Modeling & Querying", "Server Architecture", "Authentication & Authorization", "Data Structures"],
        common_competencies=["Microservices Architecture", "Caching Strategies", "Message Queues", "Unit & Integration Testing"],
        optional_competencies=["GraphQL", "gRPC", "High-Throughput Systems", "Event-Driven Systems"],
        tools_technologies=["Python", "FastAPI", "SQL", "PostgreSQL", "MongoDB", "Redis", "Docker", "Git"],
        knowledge_areas=["Relational Databases", "Distributed Caching", "API Security", "Data Serialization"],
        soft_skills=["Systems Thinking", "Debugging Persistence", "Cross-Functional Collaboration"],
    ),
    "frontend_developer": RoleCompetencyProfile(
        canonical_role="Frontend Developer",
        domain="Software Engineering",
        subdomain="Web & Client Interfaces",
        aliases=["Frontend Engineer", "Web Developer", "Client-Side Developer", "UI Engineer"],
        core_competencies=["Component-Based UI Architecture", "Responsive Web Design", "DOM Manipulation & Events", "State Management", "Web Accessibility (a11y)"],
        common_competencies=["CSS Frameworks & Flexbox/Grid", "Client-Side Routing", "RESTful API Consumption", "Cross-Browser Compatibility", "Web Performance"],
        optional_competencies=["Server-Side Rendering (SSR)", "Static Site Generation", "Animation Libraries", "Progressive Web Apps"],
        tools_technologies=["JavaScript", "TypeScript", "React", "HTML5", "CSS3", "Tailwind CSS", "Vite", "Git"],
        knowledge_areas=["Web Standards", "HTTP Protocols", "Design Systems", "Client Security"],
        soft_skills=["Visual Attention to Detail", "Empathy for User Experience", "Communication with Designers"],
    ),
    "full_stack_developer": RoleCompetencyProfile(
        canonical_role="Full Stack Developer",
        domain="Software Engineering",
        subdomain="End-to-End Applications",
        aliases=["Full Stack Engineer", "Fullstack Developer", "Fullstack Engineer"],
        core_competencies=["Frontend UI Development", "Backend API Construction", "Database Schema Design", "State Management", "Version Control"],
        common_competencies=["Authentication & Sessions", "Responsive Design", "Containerization Basics", "Integration Testing"],
        optional_competencies=["DevOps & CI/CD", "Serverless Architecture", "Performance Tuning"],
        tools_technologies=["JavaScript", "TypeScript", "React", "Node.js", "Python", "SQL", "PostgreSQL", "Git", "Docker"],
        knowledge_areas=["End-to-End Lifecycle", "Client-Server Architecture", "Data Flow Patterns"],
        soft_skills=["Versatility", "Rapid Prototyping", "Full Lifecycle Ownership"],
    ),
    "mobile_developer": RoleCompetencyProfile(
        canonical_role="Mobile Developer",
        domain="Software Engineering",
        subdomain="Mobile Platforms",
        aliases=["Mobile Engineer", "iOS Developer", "Android Developer", "Mobile App Developer"],
        core_competencies=["Mobile UI Design Patterns", "Mobile State & Lifecycle Management", "Offline Storage & Sync", "REST API Integration", "Mobile Security"],
        common_competencies=["App Store / Play Store Deployment", "Native Performance Profiling", "Push Notifications", "Crash Reporting"],
        optional_competencies=["Cross-Platform Frameworks", "Native SDK Integration", "Deep Linking"],
        tools_technologies=["Flutter", "React Native", "Kotlin", "Swift", "Android Studio", "Xcode", "Git"],
        knowledge_areas=["Mobile Operating System Lifecycles", "Touch & Gesture Handling", "Battery & Memory Optimization"],
        soft_skills=["User Experience Sensitivity", "Device Compatibility Empathy"],
    ),
    "qa_test_engineer": RoleCompetencyProfile(
        canonical_role="QA / Test Engineer",
        domain="Software Engineering",
        subdomain="Quality & Automation",
        aliases=["QA Engineer", "Software Development Engineer in Test", "SDET", "Test Automation Engineer", "Quality Assurance Engineer"],
        core_competencies=["Test Case Design & Planning", "Automated Functional Testing", "API Testing & Validation", "Regression Testing", "Defect Tracking"],
        common_competencies=["End-to-End Automation", "Performance & Load Testing", "CI/CD Test Integration", "Bug Reporting & Triaging"],
        optional_competencies=["Security Testing", "Cross-Browser Cloud Testing", "Contract Testing"],
        tools_technologies=["Selenium", "Cypress", "Playwright", "Postman", "Pytest", "Jest", "Jira", "Git"],
        knowledge_areas=["Software Testing Lifecycle (STLC)", "Test Pyramid", "Boundary Value Analysis"],
        soft_skills=["Meticulous Attention to Detail", "Root Cause Investigation", "Quality Advocacy"],
    ),
    "embedded_software_engineer": RoleCompetencyProfile(
        canonical_role="Embedded Software Engineer",
        domain="Software Engineering",
        subdomain="Hardware & Firmware",
        aliases=["Firmware Engineer", "Embedded Systems Developer", "Embedded Engineer"],
        core_competencies=["C/C++ Programming", "Microcontroller Architecture", "Hardware Protocols (I2C, SPI, UART)", "Memory-Constrained Programming", "Real-Time Operating Systems (RTOS)"],
        common_competencies=["Device Drivers Development", "Oscilloscopes & Logic Analyzers", "Interrupt Handling", "Power Optimization"],
        optional_competencies=["Wireless Protocols (BLE, Zigbee, Wi-Fi)", "Bootloader Development", "Hardware In The Loop (HIL)"],
        tools_technologies=["C", "C++", "FreeRTOS", "Linux", "Git", "GDB", "JTAG"],
        knowledge_areas=["Digital Circuitry Basics", "Memory Mapping", "Hardware Interfaces"],
        soft_skills=["Rigorous Debugging", "Hardware Empathy", "Safety Mindset"],
    ),
    "systems_engineer": RoleCompetencyProfile(
        canonical_role="Systems Engineer",
        domain="Software Engineering",
        subdomain="Systems & OS",
        aliases=["Systems Software Engineer", "OS Developer", "Kernel Developer"],
        core_competencies=["Low-Level Programming (C/C++/Rust)", "Operating Systems Internals", "Kernel & Device Interfaces", "Concurrency & Multithreading", "Memory Management"],
        common_competencies=["Socket Programming", "File Systems", "Performance Profiling", "Compilation Toolchains"],
        optional_competencies=["Virtualization", "Hypervisors", "Assembly Language"],
        tools_technologies=["C", "C++", "Rust", "Linux", "GDB", "Valgrind", "Git"],
        knowledge_areas=["POSIX Standards", "CPU Architecture", "Virtual Memory", "Cache Hierarchies"],
        soft_skills=["Analytical Depth", "Patience with Complex Bugs"],
    ),

    # --------------------------------------------------------------------------
    # 2. Data & Analytics
    # --------------------------------------------------------------------------
    "data_analyst": RoleCompetencyProfile(
        canonical_role="Data Analyst",
        domain="Data & Analytics",
        subdomain="Business & Exploratory Analytics",
        aliases=["Business Data Analyst", "Reporting Analyst", "Analytics Specialist"],
        core_competencies=["SQL Querying & Data Extraction", "Exploratory Data Analysis", "Data Cleaning & Transformation", "Dashboard Creation", "Statistical Analysis"],
        common_competencies=["KPI Definition & Tracking", "Data Storytelling & Reporting", "Business Intelligence Reporting", "Ad-Hoc Analysis"],
        optional_competencies=["A/B Testing Analysis", "Predictive Trend Analysis", "Automated Pipeline Scripts"],
        tools_technologies=["SQL", "Excel", "Tableau", "Power BI", "Python", "Pandas"],
        knowledge_areas=["Descriptive Statistics", "Relational Data Modeling", "Business Metrics"],
        soft_skills=["Data Storytelling", "Stakeholder Communication", "Curiosity", "Critical Thinking"],
    ),
    "data_scientist": RoleCompetencyProfile(
        canonical_role="Data Scientist",
        domain="Data & Analytics",
        subdomain="Predictive Analytics & Statistics",
        aliases=["Applied Data Scientist", "Data Science Specialist"],
        core_competencies=["Statistical Modeling & Hypothesis Testing", "Predictive Machine Learning", "Feature Engineering", "Data Wrangling", "Experimentation & A/B Testing"],
        common_competencies=["Model Evaluation Metrics", "Data Visualization", "Production Scripting", "Model Validation"],
        optional_competencies=["Deep Learning Basics", "Model Deployment", "Unsupervised Clustering"],
        tools_technologies=["Python", "SQL", "Scikit-Learn", "Pandas", "NumPy", "Jupyter", "Matplotlib"],
        knowledge_areas=["Probability & Statistics", "Linear Algebra", "Experimental Design", "Data Ethics"],
        soft_skills=["Scientific Inquiry", "Translating Math to Business Impact", "Executive Communication"],
    ),
    "data_engineer": RoleCompetencyProfile(
        canonical_role="Data Engineer",
        domain="Data & Analytics",
        subdomain="Data Pipelines & Infrastructure",
        aliases=["Big Data Engineer", "Data Pipeline Engineer"],
        core_competencies=["ETL/ELT Pipeline Development", "Data Warehouse Modeling", "Distributed Data Processing", "SQL & Query Optimization", "Data Lake Architecture"],
        common_competencies=["Batch & Stream Processing", "Data Quality & Validation", "Database Indexing & Partitioning", "Workflow Orchestration"],
        optional_competencies=["Real-Time Streaming", "Infrastructure as Code", "Data Governance"],
        tools_technologies=["SQL", "Python", "Apache Spark", "Airflow", "PostgreSQL", "Snowflake", "dbt", "Docker", "Git"],
        knowledge_areas=["Dimensional Modeling (Star/Snowflake)", "Data Partitioning", "Distributed Computing"],
        soft_skills=["Reliability Focus", "Data Integrity Mindset", "Cross-Team Collaboration"],
    ),
    "bi_analyst": RoleCompetencyProfile(
        canonical_role="BI Analyst",
        domain="Data & Analytics",
        subdomain="Business Intelligence",
        aliases=["Business Intelligence Analyst", "BI Developer"],
        core_competencies=["Data Modeling for BI", "Dashboard & Visual Scorecard Design", "Complex SQL Aggregations", "Business Requirement Translation", "Metric Definition"],
        common_competencies=["ETL Data Preparation", "Report Automation", "Data Governance & Accuracy", "Executive Presentations"],
        optional_competencies=["DAX Modeling", "Semantic Layers", "Self-Service BI Enablement"],
        tools_technologies=["Power BI", "Tableau", "SQL", "Excel", "DAX", "Looker"],
        knowledge_areas=["Star Schema Modeling", "Business Performance Management", "Visual Hierarchy"],
        soft_skills=["Business Acumen", "Active Listening", "Presentation Skills"],
    ),
    "analytics_engineer": RoleCompetencyProfile(
        canonical_role="Analytics Engineer",
        domain="Data & Analytics",
        subdomain="Analytics Modeling",
        aliases=["Modern Data Stack Engineer", "dbt Developer"],
        core_competencies=["Data Transformation Modeling (dbt)", "Data Warehouse Architecture", "SQL Mastery", "Data Testing & Version Control", "Semantic Layer Management"],
        common_competencies=["CI/CD for Data Pipelines", "Data Cataloging & Documentation", "Metric Layer Definition", "Query Optimization"],
        optional_competencies=["Reverse ETL", "Data Observability", "Python Data Scripts"],
        tools_technologies=["dbt", "Snowflake", "BigQuery", "SQL", "Git", "Python"],
        knowledge_areas=["Software Engineering for Data", "Dimensional Data Modeling", "Data Lineage"],
        soft_skills=["Bridging Business & Tech", "Attention to Documentation", "Collaboration"],
    ),
    "quantitative_analyst": RoleCompetencyProfile(
        canonical_role="Quantitative Analyst",
        domain="Data & Analytics",
        subdomain="Quantitative Finance & Math",
        aliases=["Quant Analyst", "Financial Quantitative Analyst", "Quant"],
        core_competencies=["Mathematical Modeling", "Time-Series Econometrics", "Stochastic Calculus", "Statistical Arbitrage & Risk Modeling", "High-Performance Numerical Code"],
        common_competencies=["Backtesting Strategies", "Algorithmic Pricing", "Monte Carlo Simulations", "Financial Instrument Valuation"],
        optional_competencies=["Low-Latency Systems", "Machine Learning for Alpha Generation"],
        tools_technologies=["Python", "C++", "R", "SQL", "NumPy", "SciPy"],
        knowledge_areas=["Financial Derivatives", "Stochastic Processes", "Portfolio Theory"],
        soft_skills=["Mathematical Rigor", "Stress Resilience", "Speed of Execution"],
    ),

    # --------------------------------------------------------------------------
    # 3. AI / Machine Learning
    # --------------------------------------------------------------------------
    "machine_learning_engineer": RoleCompetencyProfile(
        canonical_role="Machine Learning Engineer",
        domain="AI / Machine Learning",
        subdomain="Applied Machine Learning",
        aliases=["ML Engineer", "Machine Learning Developer", "Applied ML Engineer", "AI / Machine Learning Engineer", "AI/ML Engineer"],
        core_competencies=["ML Pipeline Engineering", "Supervised & Unsupervised Modeling", "Feature Store Integration", "Model Serving & Inference APIs", "Model Evaluation & Drift Monitoring"],
        common_competencies=["Hyperparameter Optimization", "Data Preprocessing Pipelines", "Model Serialization & Export", "Dockerized Deployment"],
        optional_competencies=["Distributed Training", "ONNX Optimization", "GPU Acceleration"],
        tools_technologies=["Python", "PyTorch", "TensorFlow", "Scikit-Learn", "FastAPI", "Docker", "Git", "SQL"],
        knowledge_areas=["Applied Machine Learning", "Linear Algebra & Calculus", "Inference Latency Optimization"],
        soft_skills=["Experiment Discipline", "Scientific Method", "Production Pragmatism"],
    ),
    "ai_engineer": RoleCompetencyProfile(
        canonical_role="AI Engineer",
        domain="AI / Machine Learning",
        subdomain="GenAI & LLMs",
        aliases=["Generative AI Engineer", "LLM Engineer", "Applied AI Developer"],
        core_competencies=["LLM Orchestration & Prompt Architecture", "Retrieval-Augmented Generation (RAG)", "Vector Database Indexing & Search", "API Integration with Foundation Models", "Evaluation & Guardrails for AI"],
        common_competencies=["Embedding Generation", "Agentic Workflows", "Context Window Management", "Structured Output Parsing"],
        optional_competencies=["Fine-Tuning (LoRA/QLoRA)", "Multi-Modal AI Integration", "Latency & Token Cost Optimization"],
        tools_technologies=["Python", "LangChain", "LlamaIndex", "ChromaDB", "Pinecone", "OpenAI API", "Hugging Face", "Git"],
        knowledge_areas=["Prompt Engineering", "Semantic Search", "Hallucination Mitigation", "AI Safety"],
        soft_skills=["Agile Experimentation", "Creativity", "Critical Evaluation of AI Outputs"],
    ),
    "nlp_engineer": RoleCompetencyProfile(
        canonical_role="NLP Engineer",
        domain="AI / Machine Learning",
        subdomain="Natural Language Processing",
        aliases=["Natural Language Processing Engineer", "NLP Specialist"],
        core_competencies=["Text Tokenization & Preprocessing", "Transformer Architecture", "Named Entity Recognition (NER)", "Sentiment Analysis & Classification", "Sequence-to-Sequence Modeling"],
        common_competencies=["Word Embeddings & Vectors", "Language Model Evaluation (BLEU/ROUGE)", "Text Cleaning & Normalization", "Corpus Annotation"],
        optional_competencies=["Speech Recognition (ASR)", "Machine Translation", "Topic Modeling"],
        tools_technologies=["Python", "PyTorch", "Hugging Face Transformers", "spaCy", "NLTK", "Git"],
        knowledge_areas=["Computational Linguistics", "Attention Mechanisms", "Text Syntax & Semantics"],
        soft_skills=["Linguistic Sensitivity", "Systematic Benchmarking"],
    ),
    "computer_vision_engineer": RoleCompetencyProfile(
        canonical_role="Computer Vision Engineer",
        domain="AI / Machine Learning",
        subdomain="Visual Computing",
        aliases=["Vision Engineer", "CV Engineer", "Image Processing Engineer"],
        core_competencies=["Convolutional Neural Networks (CNN)", "Image Segmentation & Object Detection", "Image Preprocessing & Augmentation", "Feature Extraction", "Real-Time Video Stream Processing"],
        common_competencies=["Model Pruning & Quantization", "Bounding Box Algorithms (YOLO)", "Camera Calibration", "Optical Flow"],
        optional_competencies=["3D Reconstruction", "Generative Vision Models (Diffusion/GAN)", "Edge AI Deployment"],
        tools_technologies=["Python", "C++", "OpenCV", "PyTorch", "TensorFlow", "YOLO", "Git"],
        knowledge_areas=["Linear Transformations", "Digital Image Processing", "Spatial Geometry"],
        soft_skills=["Visual Intuition", "Performance Optimization Mindset"],
    ),
    "ai_researcher": RoleCompetencyProfile(
        canonical_role="AI Researcher",
        domain="AI / Machine Learning",
        subdomain="Research & Innovation",
        aliases=["Research Scientist (AI)", "Machine Learning Scientist", "ML Researcher", "Machine Learning Researcher"],
        core_competencies=["Novel Algorithmic Design", "Mathematical Formulation", "Peer-Reviewed Literature Review", "Rigorous Hypothesis Testing", "Large-Scale Experimentation"],
        common_competencies=["Academic Paper Writing", "Ablation Studies", "Reproducibility Benchmarking", "Code Open-Sourcing"],
        optional_competencies=["Theory of Deep Learning", "Reinforcement Learning", "Multi-Agent Systems"],
        tools_technologies=["Python", "PyTorch", "JAX", "LaTeX", "CUDA", "Git"],
        knowledge_areas=["Information Theory", "Optimization Theory", "Probabilistic Graphical Models"],
        soft_skills=["Intellectual Rigor", "Original Thinking", "Scholarly Persistence"],
    ),

    # --------------------------------------------------------------------------
    # 4. Cloud / DevOps / Infrastructure
    # --------------------------------------------------------------------------
    "devops_engineer": RoleCompetencyProfile(
        canonical_role="DevOps Engineer",
        domain="Cloud / DevOps / Infrastructure",
        subdomain="Continuous Delivery & Automation",
        aliases=["CI/CD Engineer", "DevSecOps Engineer", "Build & Release Engineer"],
        core_competencies=["CI/CD Pipeline Automation", "Containerization & Orchestration", "Infrastructure as Code (IaC)", "Linux System Administration", "Cloud Infrastructure Configuration"],
        common_competencies=["Monitoring & Observability", "Secrets Management", "Automated Testing Integration", "Bash Shell Scripting"],
        optional_competencies=["Service Mesh", "GitOps Implementation", "Cost Optimization"],
        tools_technologies=["Docker", "Kubernetes", "Linux", "Git", "Terraform", "AWS", "GitHub Actions", "Prometheus", "Bash"],
        knowledge_areas=["Software Release Engineering", "Cloud Architecture", "Zero Downtime Deployments"],
        soft_skills=["Operational Ownership", "Cross-Team Automation Advocacy", "Calm Under Pressure"],
    ),
    "cloud_engineer": RoleCompetencyProfile(
        canonical_role="Cloud Engineer",
        domain="Cloud / DevOps / Infrastructure",
        subdomain="Cloud Architecture & Hosting",
        aliases=["Cloud Solutions Engineer", "Cloud Infrastructure Engineer"],
        core_competencies=["Cloud Architecture Design", "Virtual Networking (VPC/Subnets)", "Cloud Identity & Access Management (IAM)", "Compute & Storage Provisioning", "Infrastructure as Code"],
        common_competencies=["Cloud Security Best Practices", "High Availability & Disaster Recovery", "Cost Governance", "Serverless Infrastructure"],
        optional_competencies=["Multi-Cloud Architecture", "Migration Strategies", "Compliance Automation"],
        tools_technologies=["AWS", "Azure", "GCP", "Terraform", "Linux", "Docker", "Git"],
        knowledge_areas=["Cloud Design Principles", "Network Protocols", "Shared Responsibility Security Model"],
        soft_skills=["Architecture Communication", "Prudent Resource Management"],
    ),
    "site_reliability_engineer": RoleCompetencyProfile(
        canonical_role="Site Reliability Engineer",
        domain="Cloud / DevOps / Infrastructure",
        subdomain="Reliability & Scalability",
        aliases=["SRE", "Reliability Engineer"],
        core_competencies=["SLO/SLI Definition & Monitoring", "Incident Response & Post-Mortem Analysis", "Automated Remediation", "High-Availability System Architecture", "Capacity Planning"],
        common_competencies=["Chaos Engineering", "Observability (Tracing, Metrics, Logs)", "Load Testing & Performance Benchmarking", "Production On-Call Best Practices"],
        optional_competencies=["Distributed Tracing", "Kernel Tuning", "Disaster Drills"],
        tools_technologies=["Kubernetes", "Linux", "Prometheus", "Grafana", "Python", "Go", "Terraform", "Docker"],
        knowledge_areas=["Error Budgets", "Incident Command", "Distributed Systems Reliability"],
        soft_skills=["Blameless Problem Solving", "Grace Under Fire", "Root-Cause Rigor"],
    ),
    "platform_engineer": RoleCompetencyProfile(
        canonical_role="Platform Engineer",
        domain="Cloud / DevOps / Infrastructure",
        subdomain="Internal Developer Platforms",
        aliases=["Internal Platform Engineer", "Core Infrastructure Engineer"],
        core_competencies=["Internal Developer Platform (IDP) Design", "Developer Tooling & SDKs", "Kubernetes Platform Management", "Infrastructure Self-Service Enablement", "Security & Governance by Default"],
        common_competencies=["Golden Path Templates", "Developer Experience (DevEx) Metrics", "API Gateways", "Automated Provisioning"],
        optional_competencies=["Backstage Portal", "Policy as Code", "Custom Kubernetes Operators"],
        tools_technologies=["Kubernetes", "Terraform", "Helm", "Go", "Docker", "GitLab CI", "AWS"],
        knowledge_areas=["Developer Productivity", "Platform as a Product", "API Standardization"],
        soft_skills=["Customer-Centric Mindset for Developers", "Empathy for Teammates"],
    ),
    "infrastructure_engineer": RoleCompetencyProfile(
        canonical_role="Infrastructure Engineer",
        domain="Cloud / DevOps / Infrastructure",
        subdomain="Core Infrastructure",
        aliases=["Infra Engineer", "Systems Infrastructure Engineer"],
        core_competencies=["Server Hardware & OS Provisioning", "Network Configuration & Routing", "Storage Systems Management", "Data Center / Cloud Core Infrastructure", "High-Throughput Networking"],
        common_competencies=["Backup & Recovery", "DNS/DHCP Management", "Configuration Management", "Virtualization (KVM/VMware)"],
        optional_competencies=["Hardware Telemetry", "Bare-Metal Automation", "Optical Networking"],
        tools_technologies=["Linux", "Ansible", "Terraform", "Bash", "Python", "Git", "Networking Tools"],
        knowledge_areas=["TCP/IP", "BGP/OSPF", "RAID & SAN Storage", "Datacenter Operations"],
        soft_skills=["Methodical Troubleshooting", "Safety & Reliability Focus"],
    ),

    # --------------------------------------------------------------------------
    # 5. Cybersecurity
    # --------------------------------------------------------------------------
    "cybersecurity_analyst": RoleCompetencyProfile(
        canonical_role="Cybersecurity Analyst",
        domain="Cybersecurity",
        subdomain="Security Operations & Defense",
        aliases=["Security Analyst", "Information Security Analyst", "InfoSec Analyst", "Cyber Security Analyst"],
        core_competencies=["Threat Monitoring & Detection", "Security Incident Investigation", "Log Analysis (SIEM)", "Vulnerability Assessment", "Network Traffic & Packet Analysis"],
        common_competencies=["Incident Triage & Containment", "Security Awareness Procedures", "Endpoint Detection & Response (EDR)", "Basic Malware Triage"],
        optional_competencies=["Threat Hunting", "Forensics Basics", "Scripting for Security Automation"],
        tools_technologies=["SIEM (Splunk/QRadar)", "Wireshark", "Nessus", "EDR Tools", "Linux", "Bash", "Python Basics"],
        knowledge_areas=["MITRE ATT&CK Framework", "Common Cyber Threats (Phishing, Ransomware)", "OSI Model", "Cybersecurity Principles"],
        soft_skills=["Attention to Anomalies", "Vigilance", "Crisis Communication", "Discretion"],
    ),
    "security_engineer": RoleCompetencyProfile(
        canonical_role="Security Engineer",
        domain="Cybersecurity",
        subdomain="Security Architecture & Engineering",
        aliases=["InfoSec Engineer", "Information Security Engineer"],
        core_competencies=["Security Architecture Design", "Identity & Access Governance", "Vulnerability Remediation", "Cryptographic Implementations", "Secure Network Configuration"],
        common_competencies=["Automated Security Scanners", "Firewall & WAF Management", "Security Tool Deployment", "Hardening Operating Systems"],
        optional_competencies=["Zero Trust Architecture", "DevSecOps Integration", "Threat Modeling"],
        tools_technologies=["Linux", "Python", "Terraform", "WAF", "Burp Suite", "Git", "AWS Security Hub"],
        knowledge_areas=["Cryptography Basics", "Network Architecture", "Security Standard Frameworks (NIST/ISO 27001)"],
        soft_skills=["Balanced Security Pragmatism", "Cross-Engineering Collaboration"],
    ),
    "soc_analyst": RoleCompetencyProfile(
        canonical_role="SOC Analyst",
        domain="Cybersecurity",
        subdomain="Security Operations Center",
        aliases=["Security Operations Center Analyst", "SOC Tier 1 Analyst", "SOC Tier 2 Analyst"],
        core_competencies=["Real-Time Alert Triage", "SIEM Dashboards & Monitoring", "Phishing Investigation", "Containment Playbooks Execution", "Ticket Documentation & Escalation"],
        common_competencies=["Log Correlation", "Threat Intelligence Consumption", "Host Isolation", "False Positive Filtering"],
        optional_competencies=["Playbook Automation (SOAR)", "Memory Artifact Inspection"],
        tools_technologies=["Splunk", "Sentinel", "Wireshark", "EDR (CrowdStrike/Defender)", "Jira"],
        knowledge_areas=["Cyber Kill Chain", "Incident Response Stages", "Network Protocols"],
        soft_skills=["Urgency", "Methodical Documentation", "Focus During Shift Work"],
    ),
    "penetration_tester": RoleCompetencyProfile(
        canonical_role="Penetration Tester",
        domain="Cybersecurity",
        subdomain="Offensive Security",
        aliases=["Ethical Hacker", "Pen Tester", "Red Team Specialist"],
        core_competencies=["Web Application Penetration Testing", "Network Vulnerability Exploitation", "Reconnaissance & Footprinting", "Privilege Escalation", "Comprehensive Pentest Reporting"],
        common_competencies=["Social Engineering Assessment", "Wireless Security Testing", "Exploit Modification", "Remediation Consultation"],
        optional_competencies=["Active Directory Exploitation", "Binary Reverse Engineering", "Red Team Operations"],
        tools_technologies=["Kali Linux", "Burp Suite", "Metasploit", "Nmap", "Wireshark", "Python", "Bash"],
        knowledge_areas=["OWASP Top 10", "Common Exploitation Techniques", "Responsible Disclosure Ethics"],
        soft_skills=["Ethical Integrity", "Creative Problem Cracking", "Clear Technical Report Writing"],
    ),
    "security_consultant": RoleCompetencyProfile(
        canonical_role="Security Consultant",
        domain="Cybersecurity",
        subdomain="Advisory & Strategy",
        aliases=["Cybersecurity Consultant", "Cyber Risk Consultant"],
        core_competencies=["Security Risk Assessment", "Compliance & Gap Analysis", "Security Policy Formulation", "Client Stakeholder Advising", "Security Maturity Auditing"],
        common_competencies=["Vendor Risk Assessment", "Business Continuity Planning", "Security Roadmap Definition"],
        optional_competencies=["Virtual CISO Services", "Merger & Acquisition Security Review"],
        tools_technologies=["GRC Software", "Excel", "PowerPoint", "Assessment Toolkits"],
        knowledge_areas=["ISO 27001", "NIST CSF", "SOC 2", "GDPR & Privacy Laws"],
        soft_skills=["Client Advising", "Business Risk Communication", "Persuasion"],
    ),
    "grc_analyst": RoleCompetencyProfile(
        canonical_role="GRC Analyst",
        domain="Cybersecurity",
        subdomain="Governance, Risk & Compliance",
        aliases=["Governance Risk Compliance Analyst", "Information Security Compliance Analyst"],
        core_competencies=["Regulatory Compliance Auditing", "Risk Register Maintenance", "Security Policy Review", "Third-Party Vendor Assessments", "Audit Evidence Gathering"],
        common_competencies=["Internal Control Testing", "Security Awareness Program Tracking", "Incident Log Audits"],
        optional_competencies=["Continuous Compliance Tooling", "Privacy Impact Assessments"],
        tools_technologies=["OneTrust", "Jira", "Excel", "Confluence", "GRC Platforms"],
        knowledge_areas=["SOC 2", "ISO 27001", "HIPAA", "PCI-DSS", "NIST 800-53"],
        soft_skills=["Meticulous Record Keeping", "Auditor Interfacing", "Policy Diplomacy"],
    ),
    "cloud_security_engineer": RoleCompetencyProfile(
        canonical_role="Cloud Security Engineer",
        domain="Cybersecurity",
        subdomain="Cloud Defense",
        aliases=["Cloud SecOps Engineer", "Cloud Security Specialist"],
        core_competencies=["Cloud IAM Policy Least Privilege", "Cloud Security Posture Management (CSPM)", "Container & Kubernetes Security", "Cloud Network Security Groups", "Automated Compliance Checks"],
        common_competencies=["Cloud Trail Log Auditing", "Secrets Encryption & KMS", "Threat Detection in Cloud Environments"],
        optional_competencies=["Cloud Workload Protection (CWPP)", "GuardDuty Tuning"],
        tools_technologies=["AWS Security Hub", "Prisma Cloud", "Terraform", "Kubernetes", "Docker", "Git"],
        knowledge_areas=["Cloud Security Alliance (CSA) Matrix", "IAM Policy Logic", "Multi-Tenant Isolation"],
        soft_skills=["Security Evangelism", "DevOps Alignment"],
    ),

    # --------------------------------------------------------------------------
    # 6. Product Management
    # --------------------------------------------------------------------------
    "product_manager": RoleCompetencyProfile(
        canonical_role="Product Manager",
        domain="Product",
        subdomain="Product Strategy & Lifecycle",
        aliases=["PM", "Associate Product Manager", "Senior Product Manager"],
        core_competencies=["Product Strategy & Vision", "User Problem Discovery", "Roadmap Prioritization (RICE/MoSCoW)", "PRD & User Story Writing", "Product Metrics & KPI Tracking"],
        common_competencies=["Competitive Market Analysis", "Cross-Functional Team Leadership", "User Interviewing", "A/B Testing Hypothesis Definition"],
        optional_competencies=["Go-To-Market Coordination", "Pricing Strategy", "Technical Feasibility Analysis"],
        tools_technologies=["Jira", "Figma", "Linear", "Mixpanel", "Amplitude", "Notion", "Google Analytics"],
        knowledge_areas=["Product Discovery", "Design Thinking", "Agile/Scrum Frameworks", "Unit Economics"],
        soft_skills=["Empathy", "Strategic Prioritization", "Stakeholder Influence Without Authority", "Decisiveness"],
    ),
    "product_owner": RoleCompetencyProfile(
        canonical_role="Product Owner",
        domain="Product",
        subdomain="Agile Execution",
        aliases=["Agile Product Owner", "Scrum Product Owner"],
        core_competencies=["Backlog Refinement & Management", "Sprint Planning & Acceptance Criteria", "User Story Authoring", "Release Planning", "Stakeholder Communication"],
        common_competencies=["Velocity Tracking", "Feature Demonstration", "Trade-Off Negotiation"],
        optional_competencies=["Scrum Master Collaboration", "User Journey Mapping"],
        tools_technologies=["Jira", "Confluence", "Azure DevOps", "Miro"],
        knowledge_areas=["Scrum Principles", "Definition of Done", "Story Point Estimation"],
        soft_skills=["Clarity", "Decisive Prioritization", "Team Enablement"],
    ),
    "technical_product_manager": RoleCompetencyProfile(
        canonical_role="Technical Product Manager",
        domain="Product",
        subdomain="Technical & Platform Products",
        aliases=["Technical PM", "Platform Product Manager"],
        core_competencies=["API & Platform Strategy", "Technical Requirement Specifications", "Developer Persona Understanding", "System Architecture Trade-Offs", "Developer Experience (DevEx) Metrics"],
        common_competencies=["Data Flow Diagramming", "Technical Debt Prioritization", "Engineering Partnership"],
        optional_competencies=["SDK Strategy", "Open Source Community Engagement"],
        tools_technologies=["Postman", "Swagger", "Jira", "Git", "SQL"],
        knowledge_areas=["Software Architecture Fundamentals", "API Lifecycle", "Microservice Systems"],
        soft_skills=["Technical Fluency", "Translating Business to Tech", "Consensus Building"],
    ),
    "program_manager": RoleCompetencyProfile(
        canonical_role="Program Manager",
        domain="Product",
        subdomain="Multi-Project Orchestration",
        aliases=["Technical Program Manager", "TPM"],
        core_competencies=["Cross-Functional Program Execution", "Dependency & Risk Management", "Milestone Tracking", "Executive Status Reporting", "Resource Alignment"],
        common_competencies=["Process Optimization", "Change Management", "Retrospectives & Post-Mortems"],
        optional_competencies=["Agile Transformation", "Budget Tracking"],
        tools_technologies=["Jira", "Asana", "Monday.com", "Smartsheet", "Excel"],
        knowledge_areas=["Program Management Frameworks", "Critical Path Method", "Governance Models"],
        soft_skills=["Organization", "Diplomacy", "Conflict Resolution", "Clarity"],
    ),
    "project_manager": RoleCompetencyProfile(
        canonical_role="Project Manager",
        domain="Project Management",
        subdomain="Delivery & Project Governance",
        aliases=["Technical Project Manager", "IT Project Manager", "Delivery Lead"],
        core_competencies=["Project Scope & Milestone Management", "Work Breakdown Structure (WBS) Creation", "Risk & Issue Register (RAID) Management", "Budget & Resource Allocation Planning", "Stakeholder Status Reporting & Steering Committee Alignment"],
        common_competencies=["Critical Path Scheduling (Gantt)", "Agile / Scrum Sprint Coordination", "Vendor & Contractor Deliverable Oversight"],
        optional_competencies=["PMP Certification Principles", "Change Management (Prosci)"],
        tools_technologies=["Microsoft Project", "Jira", "Asana", "Smartsheet", "Excel Advanced"],
        knowledge_areas=["Project Management Methodologies (Waterfall/Agile)", "Earned Value Management (EVM)", "Resource Leveling"],
        soft_skills=["Empathetic Project Leadership", "Cross-Functional Alignment", "Crisis De-escalation"],
    ),

    # --------------------------------------------------------------------------
    # 7. Design
    # --------------------------------------------------------------------------
    "graphic_designer": RoleCompetencyProfile(
        canonical_role="Graphic Designer",
        domain="Design",
        subdomain="Visual Design & Branding",
        aliases=["Visual Designer", "Brand Designer", "Graphic Artist"],
        core_competencies=["Visual Composition & Layout", "Typography & Font Pairing", "Color Theory & Palettes", "Branding & Identity Guidelines", "Vector Illustration & Asset Export"],
        common_competencies=["Print & Digital Production", "Image Retouching & Manipulation", "Marketing Collateral Design", "Packaging Design"],
        optional_competencies=["Motion Graphics Basics", "Editorial Design", "3D Asset Basics"],
        tools_technologies=["Adobe Photoshop", "Adobe Illustrator", "InDesign", "Figma", "Canva"],
        knowledge_areas=["Visual Hierarchy", "Color Spaces (RGB/CMYK)", "Resolution & DPI Standards", "Licensing & Copyright"],
        soft_skills=["Creative Vision", "Receptive to Feedback", "Brand Storytelling", "Attention to Detail"],
    ),
    "ui_designer": RoleCompetencyProfile(
        canonical_role="UI Designer",
        domain="Design",
        subdomain="User Interface Design",
        aliases=["User Interface Designer", "UI/UX Visual Designer"],
        core_competencies=["Design System Maintenance", "High-Fidelity Wireframing", "Component States & Micro-Interactions", "Typography & Spacing Scales", "Responsive Grid Layouts"],
        common_competencies=["Interactive Prototyping", "Design-to-Code Handoff", "Iconography & Visual Assets"],
        optional_competencies=["CSS Basics", "Motion Design for UI", "Illustration"],
        tools_technologies=["Figma", "Sketch", "Adobe XD", "Zeplin"],
        knowledge_areas=["Human Interface Guidelines (Apple/Material)", "Visual Accessibility (WCAG)", "Design Systems"],
        soft_skills=["Visual Polish", "Collaboration with Engineers", "Detail Discipline"],
    ),
    "ux_designer": RoleCompetencyProfile(
        canonical_role="UX Designer",
        domain="Design",
        subdomain="User Experience & Interaction",
        aliases=["Interaction Designer", "Experience Designer", "UX/UI Designer", "User Experience Designer"],
        core_competencies=["User Journey Mapping", "Information Architecture", "Low & Mid-Fidelity Wireframing", "Usability Testing & Feedback Synthesis", "Interaction Flow Design"],
        common_competencies=["User Persona Development", "Rapid Prototyping", "Heuristic Evaluation"],
        optional_competencies=["Design Sprint Facilitation", "Quantitative Analytics Interpretation"],
        tools_technologies=["Figma", "Miro", "FigJam", "Whimsical", "UsabilityHub"],
        knowledge_areas=["Cognitive Psychology in Design", "Design Thinking", "Nielsen Norman Usability Heuristics"],
        soft_skills=["Deep User Empathy", "Analytical Listening", "Constructive Inquiry"],
    ),
    "product_designer": RoleCompetencyProfile(
        canonical_role="Product Designer",
        domain="Design",
        subdomain="End-to-End Product Design",
        aliases=["Digital Product Designer", "End-to-End UX/UI Designer"],
        core_competencies=["End-to-End UX/UI Design", "User Problem Discovery", "Design Systems Governance", "Interactive Prototyping", "Product Strategy Alignment"],
        common_competencies=["Usability Testing", "Data-Informed Design Iteration", "Cross-Functional Feature Collaboration"],
        optional_competencies=["Micro-Copywriting", "Basic Front-End Understanding"],
        tools_technologies=["Figma", "Miro", "Notion", "UserTesting"],
        knowledge_areas=["Business Objectives Alignment", "Design Systems Architecture", "Accessibility Standards"],
        soft_skills=["Holistic Problem Solving", "Strategic Communication", "Partnership with PMs & Tech"],
    ),
    "ux_researcher": RoleCompetencyProfile(
        canonical_role="UX Researcher",
        domain="Design",
        subdomain="User Research & Insights",
        aliases=["User Researcher", "Design Researcher"],
        core_competencies=["Generative & Evaluative User Interviews", "Usability Study Design & Moderation", "Qualitative Coding & Synthesis", "Survey Design & Analysis", "Insight Presentations & Actionable Recommendations"],
        common_competencies=["Card Sorting & Tree Testing", "Diary Studies", "Research Repository Management"],
        optional_competencies=["Quantitative Research (SPSS/R)", "Benchmarking Studies"],
        tools_technologies=["UserTesting", "Dovetail", "Qualtrics", "Miro", "Excel"],
        knowledge_areas=["Research Ethics", "Cognitive Biases in Research", "Mixed-Methods Research"],
        soft_skills=["Empathic Inquiry", "Objectivity", "Compelling Synthesis"],
    ),

    # --------------------------------------------------------------------------
    # 8. Marketing
    # --------------------------------------------------------------------------
    "digital_marketing_specialist": RoleCompetencyProfile(
        canonical_role="Digital Marketing Specialist",
        domain="Marketing",
        subdomain="Digital & Growth",
        aliases=["Digital Marketer", "Performance Marketer", "Marketing Specialist"],
        core_competencies=["Multi-Channel Campaign Management", "Paid Search & Social Advertising (PPC)", "Conversion Rate Optimization (CRO)", "Email Marketing Automation", "Marketing Analytics & Attribution"],
        common_competencies=["A/B Ad Creative Testing", "Audience Segmentation", "Budget Allocation", "Landing Page Optimization"],
        optional_competencies=["Affiliate Marketing", "MarTech Stack Integration"],
        tools_technologies=["Google Ads", "Meta Ads Manager", "Google Analytics (GA4)", "HubSpot", "Mailchimp"],
        knowledge_areas=["Customer Acquisition Funnels", "ROAS & CAC Metrics", "Privacy Regulations (GDPR/CAN-SPAM)"],
        soft_skills=["Analytical Creativity", "Agility", "Commercial Awareness"],
    ),
    "seo_specialist": RoleCompetencyProfile(
        canonical_role="SEO Specialist",
        domain="Marketing",
        subdomain="Search Engine Optimization",
        aliases=["Search Engine Optimization Specialist", "SEO Analyst", "SEO Manager"],
        core_competencies=["Keyword Research & Intent Mapping", "On-Page SEO Optimization", "Technical SEO Auditing", "Link Building Strategy", "Organic Search Performance Tracking"],
        common_competencies=["Content Gap Analysis", "Site Architecture & Crawlability", "Core Web Vitals Understanding", "Local SEO"],
        optional_competencies=["International SEO", "Schema Markup Implementation"],
        tools_technologies=["Ahrefs", "Semrush", "Google Search Console", "Screaming Frog", "Google Analytics"],
        knowledge_areas=["Search Engine Algorithms", "HTML Structure for SEO", "Content Quality Guidelines"],
        soft_skills=["Patient Investigation", "Adaptability to Algorithm Changes", "Data-Driven Persuasion"],
    ),
    "content_marketing_specialist": RoleCompetencyProfile(
        canonical_role="Content Marketing Specialist",
        domain="Marketing",
        subdomain="Content Strategy",
        aliases=["Content Marketer", "Content Strategist"],
        core_competencies=["Long-Form Content Writing & Editing", "Content Calendar Management", "Editorial Planning", "SEO-Informed Writing", "Audience Persona Alignment"],
        common_competencies=["Whitepaper & Case Study Production", "Distribution & Repurposing Strategy", "Copywriting for Conversions"],
        optional_competencies=["Podcast/Video Production Basics", "Newsletter Strategy"],
        tools_technologies=["WordPress", "Notion", "Grammarly", "Google Docs", "Ahrefs Basics"],
        knowledge_areas=["Content Marketing Funnel", "Storytelling Frameworks", "Tone of Voice Guidelines"],
        soft_skills=["Articulate Writing", "Storytelling", "Research Curiosity"],
    ),
    "social_media_manager": RoleCompetencyProfile(
        canonical_role="Social Media Manager",
        domain="Marketing",
        subdomain="Social Media & Community",
        aliases=["Social Media Specialist", "Community Manager"],
        core_competencies=["Social Media Strategy", "Community Engagement & Moderation", "Social Copywriting & Visual Curation", "Social Listening & Trend Monitoring", "Platform Analytics Reporting"],
        common_competencies=["Influencer Collaboration", "Social Ad Campaign Management", "Crisis Social Response"],
        optional_competencies=["Short-Form Video Production (TikTok/Reels)", "Employee Advocacy Programs"],
        tools_technologies=["Buffer", "Hootsuite", "Sprout Social", "Canva", "CapCut"],
        knowledge_areas=["Platform Algorithms", "Viral Mechanics", "Brand Voice Consistency"],
        soft_skills=["Cultural Awareness", "Speed & Witty Communication", "Grace Under Public Scrutiny"],
    ),

    # --------------------------------------------------------------------------
    # 9. Sales / Business Development
    # --------------------------------------------------------------------------
    "sales_executive": RoleCompetencyProfile(
        canonical_role="Sales Executive",
        domain="Sales / Business Development",
        subdomain="Direct Sales",
        aliases=["Account Executive", "Sales Representative", "Commercial Sales Executive"],
        core_competencies=["Prospect Qualification & Discovery", "Value Proposition Pitching", "Objection Handling & Negotiation", "Contract Closing & Deal Structuring", "Pipeline & Forecast Management"],
        common_competencies=["CRM Hygiene & Activity Tracking", "Product Demonstrations", "Territory Management"],
        optional_competencies=["Enterprise RFP Responses", "Partner Co-Selling"],
        tools_technologies=["Salesforce", "HubSpot CRM", "LinkedIn Sales Navigator", "Gong", "ZoomInfo"],
        knowledge_areas=["MEDDIC / BANT Frameworks", "Sales Funnel Dynamics", "Pricing Models"],
        soft_skills=["Resilience & Grit", "Persuasive Communication", "Active Listening", "High EQ"],
    ),
    "business_development_executive": RoleCompetencyProfile(
        canonical_role="Business Development Executive",
        domain="Sales / Business Development",
        subdomain="Outbound & Partnerships",
        aliases=["BDE", "BDR", "SDR", "Sales Development Representative"],
        core_competencies=["Cold Outreach & Prospecting", "Lead Qualification", "Email & Phone Cadences", "Setting Qualified Discovery Meetings", "Ideal Customer Profile (ICP) Research"],
        common_competencies=["Multi-Touch Sequences", "Objection Overcoming", "CRM Lead Logging"],
        optional_competencies=["Event Lead Follow-Up", "Social Selling"],
        tools_technologies=["Outreach.io", "SalesLoft", "Apollo.io", "LinkedIn Sales Navigator", "Salesforce"],
        knowledge_areas=["Inbound vs Outbound Sales", "Prospecting Best Practices"],
        soft_skills=["Persistence", "Rejection Immunity", "High Energy Communication"],
    ),
    "account_manager": RoleCompetencyProfile(
        canonical_role="Account Manager",
        domain="Sales / Business Development",
        subdomain="Client Retention & Upsell",
        aliases=["Client Success Manager", "Key Account Manager"],
        core_competencies=["Client Relationship Nurturing", "Account Renewal & Retention", "Upselling & Cross-Selling", "Quarterly Business Reviews (QBR)", "Client Risk Identification & Mitigation"],
        common_competencies=["Internal Advocate for Client", "Escalation Management", "Contract Renegotiation"],
        optional_competencies=["Customer Health Score Modeling", "Executive Sponsorship Programs"],
        tools_technologies=["Salesforce", "Gainsight", "Zendesk", "Excel"],
        knowledge_areas=["Customer Lifetime Value (LTV)", "Churn Mitigation", "Account Planning"],
        soft_skills=["Relationship Building", "Patience", "Commercial Diplomacy"],
    ),

    # --------------------------------------------------------------------------
    # 10. Finance / Accounting
    # --------------------------------------------------------------------------
    "accountant": RoleCompetencyProfile(
        canonical_role="Accountant",
        domain="Finance / Accounting",
        subdomain="General Accounting",
        aliases=["Staff Accountant", "Senior Accountant", "Corporate Accountant", "Tax Analyst"],
        core_competencies=["General Ledger Maintenance", "Month-End & Year-End Closing", "Bank & Account Reconciliation", "Financial Statement Preparation", "Accounts Payable & Receivable (AP/AR)"],
        common_competencies=["Tax Filing Preparation", "Audit Schedule Preparation", "Payroll Accounting", "Variance Review"],
        optional_competencies=["Fixed Asset Management", "Foreign Currency Accounting"],
        tools_technologies=["Excel", "QuickBooks", "NetSuite", "SAP ERP", "Xero"],
        knowledge_areas=["GAAP / IFRS Principles", "Double-Entry Bookkeeping", "Internal Financial Controls"],
        soft_skills=["Numerical Precision", "Confidentiality", "Integrity", "Methodical Organization"],
    ),
    "financial_analyst": RoleCompetencyProfile(
        canonical_role="Financial Analyst",
        domain="Finance / Accounting",
        subdomain="FP&A & Corporate Finance",
        aliases=["FP&A Analyst", "Corporate Financial Analyst"],
        core_competencies=["Financial Modeling (DCF/LBO/3-Statement)", "Budgeting & Forecasting (FP&A)", "Variance & Trend Analysis", "Capital Expenditure Evaluation", "Management Presentation Deck Creation"],
        common_competencies=["KPI Dashboards for Leadership", "Scenario Planning & Sensitivity Analysis", "Cost-Benefit Studies"],
        optional_competencies=["M&A Modeling", "Treasury & Cash Flow Optimization"],
        tools_technologies=["Excel (Advanced Formulas/VBA)", "PowerPoint", "NetSuite", "Power BI", "Tableau"],
        knowledge_areas=["Corporate Finance Principles", "Valuation Methodologies", "Cash Flow Dynamics"],
        soft_skills=["Commercial Acumen", "Synthesizing Numbers into Strategic Decisions", "Executive Presence"],
    ),
    "investment_analyst": RoleCompetencyProfile(
        canonical_role="Investment Analyst",
        domain="Finance / Accounting",
        subdomain="Investment & Asset Management",
        aliases=["Equity Research Analyst", "Private Equity Analyst"],
        core_competencies=["Company & Industry Due Diligence", "Financial Valuation Models", "Investment Thesis Authoring", "Market Research & Competitive Intelligence", "Portfolio Performance Tracking"],
        common_competencies=["Management Interviews", "Earnings Call Analysis", "Term Sheet Evaluation"],
        optional_competencies=["LBO Modeling", "Alternative Asset Valuation"],
        tools_technologies=["Bloomberg Terminal", "FactSet", "Excel", "Capital IQ"],
        knowledge_areas=["Capital Markets", "Securities Analysis", "Macroeconomics"],
        soft_skills=["Critical Skepticism", "Speed of Synthesis", "Conviction in Analysis"],
    ),

    # --------------------------------------------------------------------------
    # 11. HR / People
    # --------------------------------------------------------------------------
    "hr_generalist": RoleCompetencyProfile(
        canonical_role="HR Generalist",
        domain="HR / People",
        subdomain="People Operations",
        aliases=["Human Resources Generalist", "People Operations Specialist", "HR Specialist"],
        core_competencies=["Employee Relations & Conflict Resolution", "Onboarding & Offboarding Orchestration", "HR Policy Implementation & Compliance", "Benefits & Compensation Administration", "Performance Management Cycles"],
        common_competencies=["HRIS Database Management", "Exit Interviews & Retention Insights", "Workplace Investigations"],
        optional_competencies=["Employee Engagement Programs", "DEI Initiatives"],
        tools_technologies=["Workday", "BambooHR", "Gusto", "Lattice", "Excel"],
        knowledge_areas=["Labor Laws & Employment Regulations", "HR Best Practices", "Confidential Record Handling"],
        soft_skills=["Empathy", "Fairness", "High Emotional Intelligence", "Discretion"],
    ),
    "recruiter": RoleCompetencyProfile(
        canonical_role="Recruiter",
        domain="HR / People",
        subdomain="Talent Acquisition",
        aliases=["Talent Acquisition Specialist", "Technical Recruiter", "Corporate Recruiter"],
        core_competencies=["Candidate Sourcing & Outbound Outreach", "Resume Screening & Structured Phone Screens", "Hiring Manager Stakeholder Alignment", "Interview Pipeline Coordination", "Offer Negotiation & Closing"],
        common_competencies=["Applicant Tracking System (ATS) Management", "Employer Branding Initiatives", "Salary Benchmarking"],
        optional_competencies=["Campus Hiring", "Executive Search"],
        tools_technologies=["LinkedIn Recruiter", "Greenhouse", "Lever", "Gem", "Calendly"],
        knowledge_areas=["Hiring Market Dynamics", "Job Description Crafting", "Interview Compliance (EEO)"],
        soft_skills=["Persuasion", "Candidate Care", "Speed of Follow-Through", "Networking"],
    ),

    # --------------------------------------------------------------------------
    # 12. Operations / Supply Chain
    # --------------------------------------------------------------------------
    "operations_analyst": RoleCompetencyProfile(
        canonical_role="Operations Analyst",
        domain="Operations / Supply Chain",
        subdomain="Business & Process Operations",
        aliases=["Business Operations Analyst", "BizOps Analyst"],
        core_competencies=["Process Mapping & Bottleneck Identification", "Operational KPI Tracking & Reporting", "Workflow Automation & Optimization", "Cross-Departmental Coordination", "Resource Utilization Analysis"],
        common_competencies=["Standard Operating Procedure (SOP) Authoring", "Root-Cause Problem Analysis", "Cost Reduction Recommendations"],
        optional_competencies=["Six Sigma / Lean Techniques", "Change Management Execution"],
        tools_technologies=["Excel", "SQL", "Tableau", "Jira", "Lucidchart", "Asana"],
        knowledge_areas=["Operational Efficiency", "Capacity Planning", "Process Re-engineering"],
        soft_skills=["Structured Thinking", "Pragmatism", "Diplomatic Communication"],
    ),
    "supply_chain_analyst": RoleCompetencyProfile(
        canonical_role="Supply Chain Analyst",
        domain="Operations / Supply Chain",
        subdomain="Logistics & Supply Planning",
        aliases=["Logistics Analyst", "Demand Planning Analyst"],
        core_competencies=["Demand Forecasting & Inventory Optimization", "Supplier Performance Tracking", "Logistics & Freight Route Analysis", "Supply Chain Cost Analysis", "Lead Time Modeling"],
        common_competencies=["ERP Supply Chain Transactions", "Purchase Order Tracking", "Safety Stock Calculations"],
        optional_competencies=["Warehouse Management Systems (WMS)", "Customs & Trade Compliance"],
        tools_technologies=["SAP SCM", "Oracle NetSuite", "Excel (Advanced)", "Tableau", "SQL"],
        knowledge_areas=["Supply Chain Operations Reference (SCOR)", "Inventory Theory (EOQ)", "Global Freight Modes"],
        soft_skills=["Analytical Precision", "Anticipation of Disruptions", "Vendor Negotiation"],
    ),

    # --------------------------------------------------------------------------
    # 13. Consulting
    # --------------------------------------------------------------------------
    "management_consultant": RoleCompetencyProfile(
        canonical_role="Management Consultant",
        domain="Consulting",
        subdomain="Strategy & Management",
        aliases=["Strategy Consultant", "Business Consultant", "Management Associate"],
        core_competencies=["Structured Problem Solving (MECE Frameworks)", "Market Sizing & Commercial Due Diligence", "Client Executive Interviewing", "Slide Deck Storyboarding & Presentation", "Financial Impact Estimation"],
        common_competencies=["Stakeholder Workshop Facilitation", "Operating Model Design", "Benchmarking Studies"],
        optional_competencies=["Merger Integration Support", "Turnaround Restructuring"],
        tools_technologies=["PowerPoint", "Excel", "Think-Cell", "Miro"],
        knowledge_areas=["Competitive Strategy (Porter's Five Forces)", "Value Chain Analysis", "Organizational Design"],
        soft_skills=["Executive Presence", "Rapid Domain Ramp-Up", "Poise Under Scrutiny"],
    ),

    # --------------------------------------------------------------------------
    # 14. Healthcare
    # --------------------------------------------------------------------------
    "healthcare_analyst": RoleCompetencyProfile(
        canonical_role="Healthcare Analyst",
        domain="Healthcare",
        subdomain="Clinical & Health Data",
        aliases=["Clinical Data Analyst", "Health Informatics Analyst"],
        core_competencies=["Electronic Health Record (EHR) Data Querying", "Clinical Quality Metric Tracking (HEDIS/CMS)", "Healthcare Utilization & Cost Modeling", "HIPAA-Compliant Data Handling", "Patient Outcome Trend Analysis"],
        common_competencies=["Medical Coding Cross-Walks (ICD-10, CPT)", "Provider Scorecard Generation", "Health Insurance Claims Analysis"],
        optional_competencies=["Population Health Modeling", "Epidemiological Studies"],
        tools_technologies=["SQL", "Excel", "SAS", "R", "Tableau", "Epic / Cerner Systems"],
        knowledge_areas=["Healthcare Regulations (HIPAA)", "Clinical Terminology", "Medical Billing Systems"],
        soft_skills=["Meticulous Compliance", "Patient-Centric Empathy", "Analytical Discretion"],
    ),
    "clinical_research_associate": RoleCompetencyProfile(
        canonical_role="Clinical Research Associate",
        domain="Healthcare",
        subdomain="Clinical Trials",
        aliases=["CRA", "Clinical Trial Monitor"],
        core_competencies=["Clinical Trial Protocol Adherence", "Trial Site Monitoring & Auditing", "Adverse Event Documentation & Reporting", "Good Clinical Practice (GCP) Enforcement", "Informed Consent Verification"],
        common_competencies=["Electronic Data Capture (EDC) Verification", "Investigator Site File Maintenance", "Regulatory Document Submission"],
        optional_competencies=["Site Initiation Visits", "Close-Out Visits"],
        tools_technologies=["Medidata Rave", "Veeva Vault", "CTMS", "Excel"],
        knowledge_areas=["FDA Regulations (21 CFR Part 11)", "ICH-GCP Guidelines", "Clinical Trial Phases"],
        soft_skills=["Ethical Vigilance", "Uncompromising Accuracy", "Professional Firmness"],
    ),

    # --------------------------------------------------------------------------
    # 15. Engineering (Physical & Applied)
    # --------------------------------------------------------------------------
    "mechanical_engineer": RoleCompetencyProfile(
        canonical_role="Mechanical Engineer",
        domain="Engineering",
        subdomain="Mechanical Systems",
        aliases=["Mechanical Design Engineer", "Product Design Engineer (Hardware)"],
        core_competencies=["3D CAD Modeling (SolidWorks/Creo)", "Finite Element Analysis (FEA)", "Geometric Dimensioning & Tolerancing (GD&T)", "Thermal & Stress Analysis", "Manufacturing Drawing Creation (ANSI/ISO)"],
        common_competencies=["Design for Manufacturing (DFM/DFA)", "Prototyping & CNC/3D Printing", "Material Selection (Metals, Polymers)", "Root Cause Failure Analysis"],
        optional_competencies=["Computational Fluid Dynamics (CFD)", "Tolerance Stack-Up Analysis"],
        tools_technologies=["SolidWorks", "ANSYS", "Autodesk Inventor", "AutoCAD", "MATLAB", "Excel"],
        knowledge_areas=["Thermodynamics", "Fluid Mechanics", "Mechanics of Materials", "Kinematics"],
        soft_skills=["Spatial Reasoning", "Safety Obsession", "Hands-On Pragmatism"],
    ),
    "civil_engineer": RoleCompetencyProfile(
        canonical_role="Civil Engineer",
        domain="Engineering",
        subdomain="Infrastructure & Structural",
        aliases=["Structural Engineer", "Site Civil Engineer", "Site Engineer"],
        core_competencies=["Structural Analysis & Calculations", "Civil Infrastructure Drafting & Plan Sets", "Site Grading & Drainage Design", "Local Building Code & Zoning Compliance", "Bill of Quantities & Cost Estimating"],
        common_competencies=["Soil Mechanics & Geotechnical Review", "Construction Site Inspections", "Permit Applications"],
        optional_competencies=["Hydraulic Modeling", "Seismic Design"],
        tools_technologies=["AutoCAD", "Civil 3D", "Revit", "STAAD.Pro", "ETABS", "Excel"],
        knowledge_areas=["Reinforced Concrete Design", "Steel Structure Design", "Environmental Impact"],
        soft_skills=["Public Safety Mindset", "Long-Term Reliability Planning", "Contractor Communication"],
    ),
    "electrical_engineer": RoleCompetencyProfile(
        canonical_role="Electrical Engineer",
        domain="Engineering",
        subdomain="Electrical Systems",
        aliases=["Power Systems Engineer", "Electrical Design Engineer"],
        core_competencies=["Circuit Design & Schematic Capture", "Power Distribution & Load Calculations", "PCB Layout & Routing", "Signal Integrity & Noise Filtering", "Electrical Safety Code Adherence (NEC/IEC)"],
        common_competencies=["Oscilloscope & Test Bench Verification", "Component Sourcing & Selection", "EMI/EMC Compliance Testing"],
        optional_competencies=["High-Voltage Power Engineering", "PLC Automation"],
        tools_technologies=["Altium Designer", "Eagle", "MATLAB / Simulink", "SPICE (LTspice)", "AutoCAD Electrical"],
        knowledge_areas=["Electromagnetism", "Analog & Digital Electronics", "Power Electronics"],
        soft_skills=["Rigorous Methodology", "Safety Consciousness", "Attention to Detail"],
    ),
    "chemical_engineer": RoleCompetencyProfile(
        canonical_role="Chemical Engineer",
        domain="Engineering",
        subdomain="Process & Chemical Systems",
        aliases=["Process Chemical Engineer"],
        core_competencies=["Mass & Energy Balance Calculations", "Process Flow Diagram (PFD) & P&ID Development", "Chemical Reaction Engineering", "Separation Process Design", "Process Safety Management (HAZOP)"],
        common_competencies=["Equipment Sizing (Pumps, Heat Exchangers)", "Pilot Plant Scale-Up", "Quality Assurance in Chemical Processing"],
        optional_competencies=["Computational Fluid Dynamics", "Environmental Emissions Modeling"],
        tools_technologies=["Aspen Plus", "Aspen HYSYS", "MATLAB", "Excel"],
        knowledge_areas=["Thermodynamics", "Transport Phenomena", "Industrial Safety Standards"],
        soft_skills=["Process Discipline", "Safety Stewardship", "Analytical Problem Solving"],
    ),
    "robotics_engineer": RoleCompetencyProfile(
        canonical_role="Robotics Engineer",
        domain="Engineering",
        subdomain="Robotics & Mechatronics",
        aliases=["Mechatronics Engineer", "Robotics Systems Engineer", "Autonomous Systems Engineer"],
        core_competencies=["Kinematics & Dynamics Modeling", "Robot Operating System (ROS/ROS2)", "Sensor Integration (LiDAR, IMU, Encoders)", "Motion Planning & Trajectory Generation", "Control Systems (PID, State-Space)"],
        common_competencies=["Actuator & Motor Control", "Embedded Controller Programming (C++/Python)", "Hardware-in-the-Loop Testing", "Computer Vision for Robotics"],
        optional_competencies=["SLAM (Simultaneous Localization & Mapping)", "Reinforcement Learning for Control"],
        tools_technologies=["ROS", "ROS2", "C++", "Python", "Gazebo", "Linux", "Git", "MATLAB"],
        knowledge_areas=["Mechatronic Systems", "Feedback Control Theory", "Coordinate Transformations"],
        soft_skills=["Interdisciplinary Curiosity", "Patience with Hardware", "System Integration Focus"],
    ),

    # --------------------------------------------------------------------------
    # 16. Architecture / Construction
    # --------------------------------------------------------------------------
    "architect": RoleCompetencyProfile(
        canonical_role="Architect",
        domain="Architecture / Construction",
        subdomain="Architectural Design",
        aliases=["Architectural Designer", "Registered Architect", "Project Architect"],
        core_competencies=["Architectural Concept Design & Space Planning", "Building Information Modeling (BIM)", "Construction Document Preparation", "Building Codes & Accessibility Standards", "Material Specification & Detailing"],
        common_competencies=["3D Architectural Rendering & Visualization", "Client Design Presentations", "Contractor RFIs & Site Visits"],
        optional_competencies=["Sustainable Architecture (LEED/BREEAM)", "Historical Restoration"],
        tools_technologies=["Autodesk Revit", "AutoCAD", "Rhino", "SketchUp", "Lumion", "Photoshop"],
        knowledge_areas=["Life Safety Codes", "Structural Principles", "Building Envelopes", "Architectural History"],
        soft_skills=["Spatial Imagination", "Client Vision Synthesis", "Aesthetic Excellence"],
    ),

    # --------------------------------------------------------------------------
    # 17. Legal / Compliance
    # --------------------------------------------------------------------------
    "legal_associate": RoleCompetencyProfile(
        canonical_role="Legal Associate",
        domain="Legal / Compliance",
        subdomain="Corporate & Legal Practice",
        aliases=["Corporate Lawyer", "Staff Attorney", "Legal Counsel"],
        core_competencies=["Contract Drafting, Review & Redlining", "Legal Research & Precedent Analysis", "Due Diligence Auditing", "Statutory & Regulatory Compliance", "Legal Brief & Memorandum Writing"],
        common_competencies=["Risk Identification & Mitigation Clauses", "Dispute Resolution Support", "Corporate Governance Filings"],
        optional_competencies=["Intellectual Property Prosecution", "Employment Law Advising"],
        tools_technologies=["Westlaw", "LexisNexis", "Microsoft Word", "Ironclad", "DocuSign"],
        knowledge_areas=["Contract Law", "Corporate Legal Structures", "Jurisdictional Regulations"],
        soft_skills=["Precision in Language", "Uncompromising Ethics", "Logical Argumentation"],
    ),

    # --------------------------------------------------------------------------
    # 18. Education
    # --------------------------------------------------------------------------
    "teacher": RoleCompetencyProfile(
        canonical_role="Teacher",
        domain="Education",
        subdomain="Classroom & Pedagogy",
        aliases=["Educator", "High School Teacher", "Elementary Teacher", "Instructor", "School Teacher"],
        core_competencies=["Curriculum & Lesson Planning", "Classroom Facilitation & Engagement", "Differentiated Instruction", "Student Assessment & Rubric Design", "Parent & Guardian Communication"],
        common_competencies=["Educational Technology Integration", "Classroom Behavior Management", "Individualized Education Plans (IEP)"],
        optional_competencies=["Extracurricular Advising", "Standardized Test Prep"],
        tools_technologies=["Google Classroom", "Canvas LMS", "Kahoot", "Microsoft Office"],
        knowledge_areas=["Pedagogical Theories", "Child/Adolescent Development", "Subject Matter Mastery"],
        soft_skills=["Patience", "Empathy", "Inspirational Communication", "Adaptability"],
    ),

    # --------------------------------------------------------------------------
    # 19. Research / Academia
    # --------------------------------------------------------------------------
    "research_scientist": RoleCompetencyProfile(
        canonical_role="Research Scientist",
        domain="Research / Academia",
        subdomain="Scientific Research",
        aliases=["Staff Scientist", "Principal Investigator", "Senior Scientist"],
        core_competencies=["Experimental Design & Methodology", "Peer-Reviewed Scientific Writing", "Statistical Data Analysis", "Literature Review & Gap Identification", "Grant Proposal Authoring"],
        common_competencies=["Lab Equipment Operation", "Scientific Presentation at Conferences", "Mentoring Graduate Students"],
        optional_competencies=["Patent Application Writing", "Interdisciplinary Consortia"],
        tools_technologies=["R", "Python", "MATLAB", "LaTeX", "GraphPad Prism"],
        knowledge_areas=["Scientific Method", "Statistical Significance", "Research Ethics"],
        soft_skills=["Intellectual Rigor", "Curiosity", "Resilience to Failed Experiments"],
    ),

    # --------------------------------------------------------------------------
    # 20. Media / Creative
    # --------------------------------------------------------------------------
    "video_editor": RoleCompetencyProfile(
        canonical_role="Video Editor",
        domain="Media / Creative",
        subdomain="Post-Production",
        aliases=["Motion Picture Editor", "Video Producer", "Film Editor"],
        core_competencies=["Non-Linear Video Editing (NLE)", "Pacing & Story Rhythm", "Audio Mixing & Sound Design", "Color Grading & Correction", "Export Optimization & Codecs"],
        common_competencies=["Motion Graphics & Titles", "Multi-Camera Editing", "Asset Organization & Archiving"],
        optional_competencies=["VFX Compositing", "3D Motion Design"],
        tools_technologies=["Adobe Premiere Pro", "DaVinci Resolve", "After Effects", "Final Cut Pro"],
        knowledge_areas=["Visual Storytelling", "Audio Levels & Mastering Standards", "Aspect Ratios & Formats"],
        soft_skills=["Story Sense", "Rhythmic Intuition", "Receptiveness to Director Notes"],
    ),

    # --------------------------------------------------------------------------
    # 21. Hospitality / Travel
    # --------------------------------------------------------------------------
    "hotel_manager": RoleCompetencyProfile(
        canonical_role="Hotel Manager",
        domain="Hospitality / Travel",
        subdomain="Hotel Operations",
        aliases=["General Manager - Hospitality", "Hospitality Operations Manager"],
        core_competencies=["Guest Experience & Service Excellence", "Front Desk & Housekeeping Operations", "Revenue Management & Room Pricing", "Hospitality Staff Leadership & Scheduling", "Facility Maintenance Oversight"],
        common_competencies=["Vendor & Supplier Contract Management", "Guest Complaint Escalation Resolution", "Health & Safety Inspections"],
        optional_competencies=["Food & Beverage Operations", "Event Sales"],
        tools_technologies=["Opera PMS", "Amadeus", "Excel", "TripAdvisor Management"],
        knowledge_areas=["Hospitality Accounting (RevPAR/ADR)", "Guest Service Standards", "Local Tourism Trends"],
        soft_skills=["Hospitality Charm", "Crisis Composure", "Customer Obsession"],
    ),

    # --------------------------------------------------------------------------
    # 22. Pharmaceutical / Life Sciences
    # --------------------------------------------------------------------------
    "pharmaceutical_analyst": RoleCompetencyProfile(
        canonical_role="Pharmaceutical Analyst",
        domain="Pharmaceutical / Life Sciences",
        subdomain="Quality Control & Analysis",
        aliases=["QC Chemist", "Pharmaceutical Quality Analyst"],
        core_competencies=["Analytical Chemistry Instrumentation (HPLC, GC)", "Pharmacopoeia Compliance (USP/EP)", "Dissolution & Assay Testing", "Method Validation & Verification", "Good Laboratory Practice (GLP/GMP)"],
        common_competencies=["Out-of-Specification (OOS) Investigations", "Stability Chamber Testing", "Batch Record Documentation"],
        optional_competencies=["Mass Spectrometry (LC-MS)", "Bioanalytical Assays"],
        tools_technologies=["Empower HPLC Software", "ChemStation", "LIMS", "Excel"],
        knowledge_areas=["FDA Pharmaceutical Regulations", "Chemical Purity Standards", "Cleanroom Protocols"],
        soft_skills=["Zero-Defect Precision", "Integrity in Documentation"],
    ),

    # --------------------------------------------------------------------------
    # 23. Manufacturing
    # --------------------------------------------------------------------------
    "manufacturing_engineer": RoleCompetencyProfile(
        canonical_role="Manufacturing Engineer",
        domain="Manufacturing",
        subdomain="Production & Assembly",
        aliases=["Production Engineer", "Process Engineer (Manufacturing)"],
        core_competencies=["Assembly Line Layout & Cycle Time Optimization", "Standard Work Instructions (SWI) Creation", "Tooling & Fixture Design", "Statistical Process Control (SPC)", "Root Cause Corrective Action (RCCA)"],
        common_competencies=["Lean Manufacturing & 5S Implementation", "Equipment Commissioning & Qualification", "Scrap Reduction Initiatives"],
        optional_competencies=["Robotic Workcell Integration", "Six Sigma Black Belt Projects"],
        tools_technologies=["SolidWorks", "AutoCAD", "Minitab", "ERP (SAP)", "Excel"],
        knowledge_areas=["Manufacturing Operations", "Quality Management Systems (ISO 9001)", "Occupational Safety (OSHA)"],
        soft_skills=["Hands-On Presence on the Floor", "Empathetic Operator Collaboration", "Practical Innovation"],
    ),

    # --------------------------------------------------------------------------
    # 1. Software Engineering & Cloud (Expanded)
    # --------------------------------------------------------------------------
    "solutions_architect": RoleCompetencyProfile(
        canonical_role="Solutions Architect",
        domain="Software Engineering",
        subdomain="Architecture & Integration",
        aliases=["Solution Architect", "Enterprise Solutions Architect"],
        core_competencies=["Enterprise Architecture Design", "System Integration Architecture", "Cloud Migration Planning", "Technical Pre-Sales & Solution Scoping", "Non-Functional Requirements Definition"],
        common_competencies=["API Gateway Architecture", "Security Architecture Alignment", "Cost Optimization & Sizing"],
        optional_competencies=["TOGAF Framework", "High-Availability Disaster Recovery"],
        tools_technologies=["AWS", "Azure", "UML/Archimate", "Draw.io", "Kubernetes"],
        knowledge_areas=["Enterprise Systems", "Distributed Architecture", "Client Solutioning"],
        soft_skills=["Executive Stakeholder Communication", "Active Listening", "Persuasion"],
    ),
    "cloud_architect": RoleCompetencyProfile(
        canonical_role="Cloud Architect",
        domain="Cloud / DevOps / Infrastructure",
        subdomain="Cloud Architecture & Governance",
        aliases=["Enterprise Cloud Architect", "AWS Architect", "Azure Architect", "Cloud Solutions Architect"],
        core_competencies=["Multi-Region Cloud Architecture", "Cloud Governance & Landing Zones", "Cloud Security & Compliance", "Cloud Cost Optimization (FinOps)", "Infrastructure as Code Strategy"],
        common_competencies=["Hybrid Cloud Networking", "Disaster Recovery Planning", "Cloud Native Migration"],
        optional_competencies=["Serverless Architecture", "Zero Trust Cloud Networking"],
        tools_technologies=["AWS", "Azure", "GCP", "Terraform", "Kubernetes", "FinOps Tools"],
        knowledge_areas=["Well-Architected Framework", "Cloud Cost Governance", "Cloud Resilience"],
        soft_skills=["Strategic Vision", "Executive Storytelling", "Architecture Governance"],
    ),

    # --------------------------------------------------------------------------
    # 7. Design (Expanded)
    # --------------------------------------------------------------------------
    "motion_designer": RoleCompetencyProfile(
        canonical_role="Motion Designer",
        domain="Design",
        subdomain="Motion Design & Animation",
        aliases=["Motion Graphics Designer", "Motion Graphic Artist", "Animator"],
        core_competencies=["2D/3D Motion Graphics Animation", "Keyframe Animation & Graph Editor Curve Smoothing", "Kinetic Typography & Title Design", "Storyboarding & Animatic Conception", "Audio-Visual Synchronization & Sound Design"],
        common_competencies=["Video Compositing & Alpha Channel Masking", "Logo Animation & Brand Identity Motion", "Lottie / Web Animation Exporting"],
        optional_competencies=["Cinema 4D / Octane 3D Motion", "Character Rigging & Walk Cycles"],
        tools_technologies=["Adobe After Effects", "Cinema 4D", "Adobe Illustrator", "Premiere Pro", "Lottie/Bodymovin"],
        knowledge_areas=["12 Principles of Animation", "Visual Timing & Rhythm", "Digital Video Formats & Codecs"],
        soft_skills=["Instinct for Dynamic Rhythm", "Creative Playfulness", "Patience with Render Timelines"],
    ),

    # --------------------------------------------------------------------------
    # 9. Sales / Business Development (Expanded)
    # --------------------------------------------------------------------------
    "customer_success_manager": RoleCompetencyProfile(
        canonical_role="Customer Success Manager",
        domain="Sales / Business",
        subdomain="Customer Success & Retention",
        aliases=["CSM", "Client Success Manager", "Customer Success Lead"],
        core_competencies=["Customer Onboarding & Time-to-Value Acceleration", "Net Revenue Retention (NRR) & Churn Mitigation", "Quarterly Business Review (QBR) Presentation", "Customer Health Score Monitoring & Early Warning", "Cross-Sell & Expansion Opportunity Identification"],
        common_competencies=["Product Feature Adoption Coaching", "Customer Advocacy & Case Study Generation", "Support Escalation Management"],
        optional_competencies=["Enterprise Executive Sponsor Alignment", "Voice of Customer (VoC) Strategy"],
        tools_technologies=["Gainsight", "Totango", "Salesforce", "Zendesk", "Pendo", "HubSpot"],
        knowledge_areas=["SaaS Business Metrics (CAC, LTV, NRR)", "Customer Journey Mapping", "Change Management for Software Adoption"],
        soft_skills=["Genuine Customer Empathy", "Diplomatic Conflict Resolution", "Consultative Problem-Solving"],
    ),

    # --------------------------------------------------------------------------
    # 10. Finance / Accounting (Expanded)
    # --------------------------------------------------------------------------
    "financial_controller": RoleCompetencyProfile(
        canonical_role="Financial Controller",
        domain="Finance / Accounting",
        subdomain="Financial Controllership & Reporting",
        aliases=["Controller", "Corporate Controller", "Director of Accounting"],
        core_competencies=["Statutory Financial Statement Preparation (GAAP/IFRS)", "Internal Financial Controls Architecture (SOX)", "Month-End & Year-End Close Acceleration", "Treasury, Working Capital & Cash Management", "External Financial Audit Management & Liaison"],
        common_competencies=["Corporate Tax Planning & Regulatory Compliance", "Accounting Policy Drafting & Technical Research", "ERP Financial Ledger Configuration"],
        optional_competencies=["M&A Purchase Price Accounting", "ERP Implementation Leadership (NetSuite/SAP)"],
        tools_technologies=["NetSuite", "SAP S/4HANA", "FloQast", "BlackLine", "Excel Advanced"],
        knowledge_areas=["US GAAP / IFRS Standards", "COSO Internal Control Framework", "Corporate Governance & Compliance"],
        soft_skills=["Fierce Financial Integrity", "Command of Operational Details", "Executive Gravitas"],
    ),
    "audit_associate": RoleCompetencyProfile(
        canonical_role="Audit Associate",
        domain="Finance / Accounting",
        subdomain="External & Internal Audit",
        aliases=["Auditor", "Staff Auditor", "Internal Auditor"],
        core_competencies=["Financial Statement Substantive Testing", "Internal Controls Testing (Design & Operating Effectiveness)", "Audit Workpaper Preparation & Cross-Referencing", "Analytical Procedures & Variance Inquiries", "Bank, Inventory & Account Confirmations"],
        common_competencies=["Audit Sampling Methodology", "Walkthrough Documentation Creation", "PBC (Provided by Client) List Management"],
        optional_competencies=["IT General Controls (ITGC) Testing", "Forensic Accounting Investigation Basics"],
        tools_technologies=["IDEA / Alteryx", "AuditBoard", "TeamMate", "Excel Advanced"],
        knowledge_areas=["Generally Accepted Auditing Standards (GAAS)", "PCAOB Guidelines", "Risk Assessment Procedures"],
        soft_skills=["Professional Skepticism", "Persistent Inquisitiveness", "Polite Interviewing Poise"],
    ),
    "risk_analyst": RoleCompetencyProfile(
        canonical_role="Risk Analyst",
        domain="Finance / Accounting",
        subdomain="Financial & Enterprise Risk",
        aliases=["Financial Risk Analyst", "Market Risk Analyst", "Credit Risk Analyst"],
        core_competencies=["Value at Risk (VaR) & Scenario Stress Testing", "Credit & Counterparty Risk Assessment", "Market Risk & Volatility Modeling", "Risk Reporting & Dashboard Visualization", "Basel III / Dodd-Frank Capital Requirements"],
        common_competencies=["Monte Carlo Simulation", "Liquidity Risk Monitoring", "Key Risk Indicator (KRI) Tracking"],
        optional_competencies=["Model Validation & Backtesting", "Operational Risk Frameworks"],
        tools_technologies=["Python / R", "Excel Advanced (VBA)", "SQL", "Bloomberg Terminal", "Moody's Analytics"],
        knowledge_areas=["Financial Derivatives", "Stochastic Modeling", "Capital Adequacy Regulations"],
        soft_skills=["Intellectual Rigor", "Healthy Skepticism", "Clear Risk Communication"],
    ),

    # --------------------------------------------------------------------------
    # 11. HR / People (Expanded)
    # --------------------------------------------------------------------------
    "hr_business_partner": RoleCompetencyProfile(
        canonical_role="HR Business Partner",
        domain="HR / People",
        subdomain="Strategic HR & Business Partnership",
        aliases=["HRBP", "Senior HR Business Partner", "People Business Partner"],
        core_competencies=["Strategic Workforce Planning & Talent Strategy", "Organizational Design & Team Restructuring", "Executive Leadership Coaching & Advising", "High-Risk Employee Relations & Investigations", "Talent Management & Succession Planning"],
        common_competencies=["Employee Retention & Engagement Action Plans", "Performance Management Calibration", "Culture & Change Management Leadership"],
        optional_competencies=["Compensation Band & Equity Strategy", "M&A People Due Diligence & Integration"],
        tools_technologies=["Workday", "Culture Amp", "Lattice", "Excel", "Visio (Org Charts)"],
        knowledge_areas=["Labor Law & Legal Risk", "Organizational Psychology", "Business Financial Literacy"],
        soft_skills=["Strategic Business Acumen", "Trusted Confidant Diplomacy", "Courageous Truth-Telling"],
    ),
    "learning_and_development_specialist": RoleCompetencyProfile(
        canonical_role="Learning and Development Specialist",
        domain="HR / People",
        subdomain="Talent Development & Organizational Learning",
        aliases=["L&D Specialist", "Training Specialist", "Corporate Trainer"],
        core_competencies=["Training Needs Analysis (TNA)", "Employee Workshop & Training Facilitation", "Leadership & Career Development Program Design", "Learning Management System (LMS) Administration", "Training Impact Measurement (Kirkpatrick Levels 1-4)"],
        common_competencies=["Onboarding Learning Path Curation", "Mentorship Program Orchestration", "Vendor & External Speaker Management"],
        optional_competencies=["Executive Coaching Certification", "Competency Model Framework Architecture"],
        tools_technologies=["LinkedIn Learning", "Cornerstone OnDemand", "Docebo", "Zoom/Teams", "Miro"],
        knowledge_areas=["Adult Learning Principles", "Behavioral Competency Frameworks", "Organizational Development"],
        soft_skills=["Engaging Platform Presence", "Empathetic Facilitation", "Infectious Enthusiasm for Growth"],
    ),

    # --------------------------------------------------------------------------
    # 12. Operations / Supply Chain (Expanded)
    # --------------------------------------------------------------------------
    "procurement_specialist": RoleCompetencyProfile(
        canonical_role="Procurement Specialist",
        domain="Operations / Supply Chain",
        subdomain="Procurement & Sourcing",
        aliases=["Procurement Officer", "Purchasing Specialist", "Buyer", "Sourcing Specialist"],
        core_competencies=["Strategic Sourcing & Vendor Evaluation", "RFP / RFQ / RFI Process Management", "Commercial Contract Negotiation & Price Term Execution", "Supplier Relationship Management (SRM)", "Procurement Spend Analytics & Cost Reduction"],
        common_competencies=["Purchase Order (PO) Lifecycle Management", "Procure-to-Pay (P2P) Compliance", "Supplier Quality Auditing Collaboration"],
        optional_competencies=["Global Trade & Incoterms 2020", "Sustainable & Ethical Procurement"],
        tools_technologies=["SAP Ariba", "Coupa", "Oracle Procurement", "Excel Advanced"],
        knowledge_areas=["Supply Market Dynamics", "Total Cost of Ownership (TCO)", "Commercial Contract Law"],
        soft_skills=["Tough but Fair Negotiation", "Analytical Skepticism", "Cross-Functional Collaboration"],
    ),
    "inventory_analyst": RoleCompetencyProfile(
        canonical_role="Inventory Analyst",
        domain="Operations / Supply Chain",
        subdomain="Inventory Optimization & Control",
        aliases=["Inventory Control Analyst", "Stock Analyst"],
        core_competencies=["Safety Stock & Reorder Point Optimization", "Economic Order Quantity (EOQ) Modeling", "Inventory Shrinkage & Obsolete Stock Control", "Cycle Count Planning & Reconciliation", "Inventory Turnover & Days of Supply (DOS) Tracking"],
        common_competencies=["ABC Inventory Stratification", "Warehouse Slotting Analysis", "Slow-Moving Inventory Depletion Strategies"],
        optional_competencies=["VMI (Vendor-Managed Inventory)", "Radio-Frequency ID (RFID) Tracking"],
        tools_technologies=["SAP MM", "Oracle NetSuite", "Excel Advanced", "Tableau"],
        knowledge_areas=["Inventory Carrying Costs", "Supply Chain Logistics", "Warehouse Operations"],
        soft_skills=["Meticulous Counting Rigor", "Root-Cause Discrepancy Analysis", "Operational Tenacity"],
    ),
    "demand_planner": RoleCompetencyProfile(
        canonical_role="Demand Planner",
        domain="Operations / Supply Chain",
        subdomain="Demand Planning & S&OP",
        aliases=["Demand Analyst", "Demand Planning Specialist"],
        core_competencies=["Statistical Demand Forecasting & Seasonality Modeling", "Sales & Operations Planning (S&OP) Facilitation", "Forecast Accuracy & Bias Tracking (MAPE/WAPE)", "Promotional Lift & New Product Launch Modeling", "Consensus Demand Plan Consensus Building"],
        common_competencies=["Supply and Production Constraint Balancing", "Downstream Retail POS Data Analysis", "Exception-Based Forecasting"],
        optional_competencies=["Machine Learning for Demand Forecasting", "Multi-Echelon Inventory Optimization (MEIO)"],
        tools_technologies=["SAP IBP", "JDA / Blue Yonder", "Kinaxis RapidResponse", "Excel Advanced", "R / Python"],
        knowledge_areas=["Time Series Econometrics", "Supply Chain Trade-Offs", "S&OP Best Practices"],
        soft_skills=["Cross-Functional Diplomacy", "Synthesizing Qualitative Commercial Inputs", "Analytical Conviction"],
    ),

    # --------------------------------------------------------------------------
    # 13. Consulting (Expanded)
    # --------------------------------------------------------------------------
    "technology_consultant": RoleCompetencyProfile(
        canonical_role="Technology Consultant",
        domain="Consulting",
        subdomain="Technology Strategy & Advisory",
        aliases=["IT Consultant", "Digital Transformation Consultant"],
        core_competencies=["IT Strategy & Technology Roadmap Definition", "Digital Transformation Gap Assessment", "Technology Vendor Evaluation & Selection", "Business Architecture Alignment", "Technology Cost & ROI Business Case Formulation"],
        common_competencies=["Cloud Transformation Advisory", "System Implementation Quality Assurance", "Operating Model Design for IT"],
        optional_competencies=["Enterprise Agility Coaching", "Emerging Tech Feasibility (GenAI/Blockchain)"],
        tools_technologies=["Visio", "PowerPoint", "Excel Advanced", "Jira", "Miro"],
        knowledge_areas=["Enterprise IT Operating Models", "Cloud Ecosystems", "Software Development Methodologies"],
        soft_skills=["Client Trusted Advisory", "Clear Business-Tech Translation", "Executive Stakeholder Poise"],
    ),
    "risk_consultant": RoleCompetencyProfile(
        canonical_role="Risk Consultant",
        domain="Consulting",
        subdomain="Governance & Risk Advisory",
        aliases=["Advisory Risk Consultant", "GRC Consultant"],
        core_competencies=["Enterprise Risk Management (ERM) Framework Assessment", "Operational Resilience & Business Continuity Planning", "Regulatory Compliance Gap Analysis", "Internal Controls Diagnostic & Review", "Third-Party & Vendor Risk Assessment"],
        common_competencies=["Crisis Management Simulation Exercises", "Fraud Risk Assessment", "Policy & Governance Documenting"],
        optional_competencies=["Cyber Risk Quantification (FAIR)", "ESG Regulatory Risk Strategy"],
        tools_technologies=["MetricStream", "ServiceNow GRC", "Excel Advanced", "PowerPoint"],
        knowledge_areas=["COSO Framework", "ISO 31000 Risk Management", "Regulatory Guidance (SEC, OCC, PRA)"],
        soft_skills=["Unflappable Integrity", "Diplomatic Inquisitiveness", "Structured Logical Synthesis"],
    ),

    # --------------------------------------------------------------------------
    # 14. Healthcare (Expanded)
    # --------------------------------------------------------------------------
    "registered_nurse": RoleCompetencyProfile(
        canonical_role="Registered Nurse",
        domain="Healthcare",
        subdomain="Clinical Nursing & Patient Care",
        aliases=["Staff Nurse", "Clinical Nurse", "Nurse"],
        core_competencies=["Patient Assessment & Triage", "Medication Administration & Safety Protocols", "Care Plan Formulation & Clinical Execution", "Vital Signs Monitoring & Decompensation Detection", "Clinical Documentation in Electronic Health Records (EHR)"],
        common_competencies=["Infection Prevention & Sterile Techniques", "Patient & Family Discharge Education", "Emergency Response Protocols (BLS/ACLS)", "Interprofessional Clinical Communication (SBAR)"],
        optional_competencies=["Peripheral IV Cannulation", "Advanced Wound Care", "Chemotherapy / Specialized Infusions"],
        tools_technologies=["Epic EHR", "Cerner", "Vital Sign Monitors", "Infusion Pumps", "Pyxis MedStation"],
        knowledge_areas=["Pharmacology", "Human Pathophysiology", "Nursing Ethics & HIPAA Regulations", "Patient Safety Standards"],
        soft_skills=["Profound Empathy & Compassion", "Composure in High-Acuity Crises", "Sharp Observational Vigilance"],
    ),
    "medical_coder": RoleCompetencyProfile(
        canonical_role="Medical Coder",
        domain="Healthcare",
        subdomain="Health Information & Medical Coding",
        aliases=["Health Information Specialist", "Clinical Coder", "Medical Billing and Coding Specialist"],
        core_competencies=["ICD-10-CM / ICD-10-PCS Diagnosis & Procedure Coding", "CPT & HCPCS Level II Medical Coding", "Medical Record Clinical Documentation Review", "Billing Compliance & Claim Adjudication Guidelines", "DRG Grouping & Healthcare Reimbursement Methodologies"],
        common_competencies=["Claim Denial Management & Coding Appeals", "EHR Clinical Documentation Improvement (CDI)", "HIPAA Privacy & Security Standards"],
        optional_competencies=["Inpatient Hospital Facility Coding", "Hierarchical Condition Category (HCC) Risk Adjustment"],
        tools_technologies=["3M Coding System", "Epic Resolute", "EncoderPro", "Optum360", "Excel"],
        knowledge_areas=["Medical Terminology", "Human Anatomy & Disease Pathology", "CMS Inpatient/Outpatient Reimbursement Rules"],
        soft_skills=["Extreme Attention to Granular Detail", "Methodical Integrity", "Analytical Persistence"],
    ),

    # --------------------------------------------------------------------------
    # 15. Pharmaceutical / Life Sciences (Expanded)
    # --------------------------------------------------------------------------
    "pharmacovigilance_specialist": RoleCompetencyProfile(
        canonical_role="Pharmacovigilance Specialist",
        domain="Pharmaceutical / Life Sciences",
        subdomain="Drug Safety & Surveillance",
        aliases=["Drug Safety Specialist", "Pharmacovigilance Officer", "Drug Safety Associate"],
        core_competencies=["Individual Case Safety Report (ICSR) Processing", "Adverse Event (AE) Triage & MedDRA Coding", "Aggregate Safety Reporting (PSUR/PBRER)", "Safety Signal Detection & Risk Management Plans (RMP)", "Regulatory Drug Safety Reporting (FDA/EMA)"],
        common_competencies=["Safety Database Entry (Argus/ARISg)", "Scientific Literature Surveillance for Safety Signals", "Quality Review of Case Narratives"],
        optional_competencies=["Post-Marketing Safety Surveillance", "Clinical Trial Safety Reconciliations"],
        tools_technologies=["Argus Safety", "ARISg", "MedDRA", "WHO Drug Dictionary", "Excel"],
        knowledge_areas=["Good Pharmacovigilance Practices (GVP)", "ICH-GCP Guidelines", "FDA 21 CFR Part 312/314"],
        soft_skills=["Scientific Rigor", "Regulatory Vigilance", "Uncompromising Ethics"],
    ),
    "regulatory_affairs_associate": RoleCompetencyProfile(
        canonical_role="Regulatory Affairs Associate",
        domain="Pharmaceutical / Life Sciences",
        subdomain="Regulatory Compliance & Submissions",
        aliases=["Regulatory Affairs Specialist", "Regulatory Specialist"],
        core_competencies=["Regulatory Submission Preparation (IND/NDA/BLA)", "eCTD Dossier Compilation & Publishing", "Health Authority Interaction & Query Response", "Regulatory Intelligence & Guideline Tracking", "Labeling & Packaging Regulatory Compliance"],
        common_competencies=["Change Control Regulatory Assessments", "Chemistry, Manufacturing & Controls (CMC) Documentation Review", "Annual Report Submissions"],
        optional_competencies=["Medical Device 510(k) Submissions", "Global Submissions (EMA/PMDA)"],
        tools_technologies=["eCTD Software (Lorenz/Veeva)", "Documentum", "Adobe Acrobat Pro", "Excel"],
        knowledge_areas=["FDA Regulations (21 CFR)", "ICH Guidelines", "GXP Compliance", "Regulatory Strategy"],
        soft_skills=["Meticulous Document Care", "Diplomatic Communication", "Strategic Foresight"],
    ),
    "biostatistician": RoleCompetencyProfile(
        canonical_role="Biostatistician",
        domain="Pharmaceutical / Life Sciences",
        subdomain="Clinical Biostatistics",
        aliases=["Clinical Biostatistician", "Statistical Programmer (Clinical)"],
        core_competencies=["Clinical Trial Study Design & Sample Size Calculation", "Statistical Analysis Plan (SAP) Authoring", "Survival Analysis & Longitudinal Modeling", "CDISC Standards Implementation (SDTM/ADaM)", "Clinical Study Report (CSR) Statistical Tables & Figures"],
        common_competencies=["Interim Analysis & Data Safety Monitoring", "Randomization Schedule Generation", "Clinical Protocol Review"],
        optional_competencies=["Adaptive Trial Design", "Bayesian Biostatistics", "FDA Advisory Committee Prep"],
        tools_technologies=["SAS", "R", "PASS", "nQuery", "Git", "Linux"],
        knowledge_areas=["Biostatistical Methodology", "ICH E9 Statistical Principles", "FDA Clinical Trial Guidance"],
        soft_skills=["Methodological Precision", "Clarity in Communicating Complex Statistics", "Scientific Tenacity"],
    ),

    # --------------------------------------------------------------------------
    # 16. Engineering — Physical (Expanded)
    # --------------------------------------------------------------------------
    "electronics_engineer": RoleCompetencyProfile(
        canonical_role="Electronics Engineer",
        domain="Engineering",
        subdomain="Electronics & Hardware",
        aliases=["Hardware Engineer", "Circuit Design Engineer", "Electronic Design Engineer"],
        core_competencies=["Analog & Digital Circuit Design", "PCB Schematic & Layout Design", "Microcontroller & Embedded Hardware Interfacing", "Signal Integrity & Power Distribution", "Hardware Testing & Oscilloscope Debugging"],
        common_competencies=["Component Selection & Sourcing", "EMC/EMI Compliance Testing", "Design for Manufacturing (DFM) for PCBs"],
        optional_competencies=["High-Speed PCB Routing", "FPGA Interfacing", "Power Electronics Design"],
        tools_technologies=["Altium Designer", "KiCad", "Eagle", "Oscilloscopes", "Logic Analyzers", "SPICE Simulation"],
        knowledge_areas=["Circuit Analysis", "Semiconductor Physics", "IPC Standards", "Electromagnetic Compatibility"],
        soft_skills=["Systematic Root-Cause Debugging", "Precision Craft", "Collaborative Problem Solving"],
    ),
    "industrial_engineer": RoleCompetencyProfile(
        canonical_role="Industrial Engineer",
        domain="Engineering",
        subdomain="Operations & Industrial Systems",
        aliases=["Industrial Operations Engineer", "Continuous Improvement Engineer"],
        core_competencies=["Time & Motion Studies (MOST/MTM)", "Plant & Facility Layout Optimization", "Ergonomics & Workstation Design", "Line Balancing & Bottleneck Analysis", "Value Stream Mapping & Waste Reduction"],
        common_competencies=["Capacity Planning & Throughput Modeling", "Standard Operating Procedure (SOP) Development", "Cost-Benefit & ROI Analysis"],
        optional_competencies=["Discrete Event Simulation (Arena/FlexSim)", "Operations Research Optimization"],
        tools_technologies=["AutoCAD", "Arena Simulation", "Minitab", "Visio", "Excel Advanced", "SAP"],
        knowledge_areas=["Lean Manufacturing", "Six Sigma Methodology", "Human Factors Engineering", "Supply Chain Operations"],
        soft_skills=["Worker Empathy", "Analytical Mindset", "Pragmatic Change Leadership"],
    ),
    "biomedical_engineer": RoleCompetencyProfile(
        canonical_role="Biomedical Engineer",
        domain="Engineering",
        subdomain="Biomedical Devices & Instrumentation",
        aliases=["Medical Device Engineer", "Bioengineer"],
        core_competencies=["Medical Device Product Development", "Biocompatibility & Materials Selection", "Design Controls (FDA 21 CFR 820.30)", "Risk Management for Medical Devices (ISO 14971)", "Biomedical Sensor Interfacing & Signal Acquisition"],
        common_competencies=["Benchtop & In-Vitro Verification Testing", "Medical Device Usability Engineering (IEC 62366)", "Clinical Evaluation Support"],
        optional_competencies=["Implantable Device Design", "Tissue Engineering Basics", "Bio-Microfluidics"],
        tools_technologies=["SolidWorks", "MATLAB", "LabVIEW", "Minitab", "FDA Guidance Portals"],
        knowledge_areas=["ISO 13485 Quality Standards", "Physiology & Anatomy Basics", "Biomaterials", "FDA 510(k)/PMA Pathways"],
        soft_skills=["Patient-First Safety Ethics", "Interdisciplinary Translation", "Rigorous Verification Discipline"],
    ),
    "automotive_engineer": RoleCompetencyProfile(
        canonical_role="Automotive Engineer",
        domain="Engineering",
        subdomain="Automotive Systems & Powertrain",
        aliases=["Vehicle Engineer", "Chassis Systems Engineer"],
        core_competencies=["Vehicle Powertrain & Drivetrain Engineering", "Chassis & Suspension Geometry Design", "Automotive Functional Safety (ISO 26262)", "Vehicle Dynamics & NVH Analysis", "Automotive Communication Protocols (CAN/LIN)"],
        common_competencies=["Thermal Management for Vehicles", "Crashworthiness & Safety Simulation", "DFMEA & DVP&R Execution"],
        optional_competencies=["Electric Vehicle (EV) Battery Packaging", "Autonomous Driving Systems Integration"],
        tools_technologies=["CATIA", "Simulink", "CANalyzer", "ANSYS", "Adams Car"],
        knowledge_areas=["Automotive Standards (SAE/ISO)", "Combustion & Electric Propulsion", "Materials & Metallurgy"],
        soft_skills=["Safety Mindset", "Hands-On Prototyping Passion", "Cross-Subsystem Collaboration"],
    ),
    "aerospace_engineer": RoleCompetencyProfile(
        canonical_role="Aerospace Engineer",
        domain="Engineering",
        subdomain="Aeronautics & Astronautics",
        aliases=["Aeronautical Engineer", "Flight Systems Engineer"],
        core_competencies=["Aerodynamics & Airfoil Flow Modeling", "Aerospace Structural Analysis & Stress (FEA)", "Flight Dynamics, Stability & Control", "Propulsion System Sizing & Performance", "Avionics & Flight Management System Integration"],
        common_competencies=["Weight & Balance Management", "Aviation Airworthiness Standards (FAA/EASA)", "Vibration & Aeroelasticity Testing"],
        optional_competencies=["Orbital Mechanics & Trajectory Analysis", "Composite Material Autoclave Curing"],
        tools_technologies=["ANSYS Fluent", "Nastran/Patran", "MATLAB/Simulink", "CATIA", "XFLR5"],
        knowledge_areas=["Compressible Aerodynamics", "Propulsion Thermodynamics", "FAR Part 23/25 Certification"],
        soft_skills=["Zero-Tolerance for Calculation Errors", "Disciplined Peer Review", "Systems Thinking"],
    ),

    # --------------------------------------------------------------------------
    # 17. Architecture & Construction (Expanded)
    # --------------------------------------------------------------------------
    "interior_designer": RoleCompetencyProfile(
        canonical_role="Interior Designer",
        domain="Architecture / Construction",
        subdomain="Interior Architecture & Spatial Design",
        aliases=["Commercial Interior Designer", "Interior Architect"],
        core_competencies=["Spatial Planning & Layout Optimization", "FF&E (Furniture, Fixtures & Equipment) Specification", "Material, Finishes & Color Schemes Selection", "Construction & Millwork Detailing", "Interior Lighting & Acoustic Design"],
        common_competencies=["Building Code Egress Compliance", "3D Interior Photorealistic Rendering", "Contractor Coordination & Punch Lists"],
        optional_competencies=["LEED/WELL Green Building Certification", "Historic Interior Conservation"],
        tools_technologies=["AutoCAD", "Revit", "SketchUp", "V-Ray", "Photoshop", "Enscape"],
        knowledge_areas=["ADA Accessibility Standards", "Building Codes (IBC)", "Materials Science & Durability"],
        soft_skills=["Aesthetic Sophistication", "Client Empathy", "Spatial Imagination"],
    ),
    "construction_manager": RoleCompetencyProfile(
        canonical_role="Construction Manager",
        domain="Architecture / Construction",
        subdomain="Construction Execution & Management",
        aliases=["Construction Project Manager", "Site Construction Manager"],
        core_competencies=["Construction Project Scheduling (Critical Path Method)", "Subcontractor & Trade Coordination", "Construction Site Safety & OSHA Compliance", "Cost Estimation & Budget Control", "Quality Control & Field Inspections"],
        common_competencies=["RFI & Submittal Processing", "Change Order Negotiation", "Building Permit Coordination"],
        optional_competencies=["Lean Construction (Last Planner System)", "Heavy Equipment Logistics"],
        tools_technologies=["Procore", "Primavera P6", "Microsoft Project", "Bluebeam Revu", "Excel"],
        knowledge_areas=["Building Codes & Standards", "OSHA Construction Regulations", "Contract Law for Construction"],
        soft_skills=["Firm Site Leadership", "Decisive Crisis Negotiation", "Uncompromising Safety Integrity"],
    ),
    "bim_engineer": RoleCompetencyProfile(
        canonical_role="BIM Engineer",
        domain="Architecture / Construction",
        subdomain="Building Information Modeling",
        aliases=["BIM Coordinator", "VDC Engineer", "BIM Specialist"],
        core_competencies=["3D/4D/5D Building Information Modeling (BIM)", "Clash Detection & Multi-Trade Resolution", "BIM Execution Plan (BEP) Authoring", "Level of Development (LOD 100-500) Compliance", "BIM Model Quantity Take-Off (QTO)"],
        common_competencies=["Revit Family Creation & Parametric Design", "Laser Scan to BIM Point Cloud Modeling", "Virtual Design & Construction (VDC) Coordination"],
        optional_competencies=["Dynamo Visual Scripting for Revit", "IFC OpenBIM Interoperability"],
        tools_technologies=["Autodesk Revit", "Navisworks Manage", "BIM 360", "Solibri", "Dynamo"],
        knowledge_areas=["AEC Industry Standards", "Multi-Discipline Coordination (MEP/Structural/Arch)", "Model Integrity Standards"],
        soft_skills=["Spatial Precision", "Proactive Conflict Resolution", "Patience with Complex Assemblies"],
    ),
    "quantity_surveyor": RoleCompetencyProfile(
        canonical_role="Quantity Surveyor",
        domain="Architecture / Construction",
        subdomain="Cost Engineering & Quantity Surveying",
        aliases=["Cost Engineer", "Construction Estimator"],
        core_competencies=["Bill of Quantities (BOQ) Preparation", "Construction Cost Estimation & Tendering", "Valuation of Variations & Interim Payments", "Subcontractor Procurement & Evaluation", "Final Account Settlement"],
        common_competencies=["Cost Feasibility Studies", "Contract Administration (FIDIC/JCT)", "Cash Flow Forecasting"],
        optional_competencies=["Life-Cycle Costing", "Construction Dispute Resolution Support"],
        tools_technologies=["CostX", "Bluebeam", "Buildsoft", "Excel Advanced", "PlanSwift"],
        knowledge_areas=["Standard Methods of Measurement (NRM/POMI)", "Construction Law & Contracts", "Cost Benchmarks"],
        soft_skills=["Commercial Acumen", "Contractual Rigor", "Fierce Negotiation"],
    ),

    # --------------------------------------------------------------------------
    # 18. Legal / Compliance (Expanded)
    # --------------------------------------------------------------------------
    "compliance_analyst": RoleCompetencyProfile(
        canonical_role="Compliance Analyst",
        domain="Legal / Compliance",
        subdomain="Regulatory Compliance & Risk",
        aliases=["Compliance Officer", "Regulatory Compliance Analyst"],
        core_competencies=["Regulatory Risk Assessment & Monitoring", "Compliance Policy Authoring & Review", "Internal Compliance Audits & Testing", "AML / KYC Screening & Transaction Monitoring", "Regulatory Reporting & Inquiry Responses"],
        common_competencies=["Ethics & Whistleblower Investigation Support", "Employee Compliance Training Delivery", "Vendor Due Diligence"],
        optional_competencies=["Sanctions Screening", "Data Privacy Compliance (GDPR/CCPA)"],
        tools_technologies=["GRC Platforms (MetricStream/LogicGate)", "LexisNexis", "World-Check", "Excel"],
        knowledge_areas=["Financial Regulations (SEC/FINRA/FCA)", "Anti-Bribery Laws (FCPA/UKBA)", "Corporate Governance"],
        soft_skills=["Unwavering Integrity", "Inquisitive Skepticism", "Diplomatic Firmness"],
    ),
    "contract_specialist": RoleCompetencyProfile(
        canonical_role="Contract Specialist",
        domain="Legal / Compliance",
        subdomain="Contract Management",
        aliases=["Contract Manager", "Contract Administrator"],
        core_competencies=["Commercial Contract Drafting & Redlining", "Contract Negotiation (Terms & Conditions)", "Contract Lifecycle Management (CLM)", "Risk Allocation & Indemnity Analysis", "Post-Award Contract Administration & Milestone Tracking"],
        common_competencies=["Non-Disclosure Agreement (NDA) Execution", "Service Level Agreement (SLA) Monitoring", "Contract Renewal & Termination Procedures"],
        optional_competencies=["Government Contracting (FAR/DFARS)", "Cross-Border International Contracts"],
        tools_technologies=["Ironclad", "DocuSign CLM", "Icertis", "Salesforce", "Word Advanced"],
        knowledge_areas=["Commercial Contract Law", "UCC Guidelines", "Risk Mitigation Frameworks"],
        soft_skills=["Sharp Attention to Legal Nuances", "Pragmatic Business Alignment", "Negotiation Poise"],
    ),

    # --------------------------------------------------------------------------
    # 19. Education (Expanded)
    # --------------------------------------------------------------------------
    "instructional_designer": RoleCompetencyProfile(
        canonical_role="Instructional Designer",
        domain="Education",
        subdomain="Instructional Design & Learning Tech",
        aliases=["E-Learning Developer", "Learning Designer"],
        core_competencies=["Instructional Systems Design (ADDIE/SAM)", "Adult Learning Pedagogy (Andragogy)", "E-Learning Authoring (Storyline/Rise)", "Learning Management System (LMS) Administration", "Formative & Summative Learning Assessment Design"],
        common_competencies=["Microlearning & Video Module Scripting", "User Experience (UX) for Learners", "Kirkpatrick Training Evaluation"],
        optional_competencies=["SCORM/xAPI Standards", "Gamification in Learning"],
        tools_technologies=["Articulate 360 (Storyline, Rise)", "Canvas LMS", "Moodle", "Camtasia", "Figma"],
        knowledge_areas=["Cognitive Load Theory", "Bloom's Taxonomy", "Universal Design for Learning (UDL)"],
        soft_skills=["Empathy for Novice Learners", "Creative Synthesis", "Structured Thinking"],
    ),
    "curriculum_developer": RoleCompetencyProfile(
        canonical_role="Curriculum Developer",
        domain="Education",
        subdomain="Curriculum & Academic Standards",
        aliases=["Curriculum Specialist", "Academic Content Developer"],
        core_competencies=["Scope & Sequence Curriculum Mapping", "Educational Standards Alignment", "Pedagogical Material & Textbook Authoring", "Rubric & Standardized Assessment Development", "Teacher Facilitator Guide Creation"],
        common_competencies=["Curriculum Review & Continuous Improvement", "Differentiated Learning Frameworks", "Subject Matter Expert (SME) Interviewing"],
        optional_competencies=["STEM Education Integration", "Bilingual Curriculum Development"],
        tools_technologies=["Google Workspace", "Microsoft 365", "Curriculum Mapping Tools", "LMS"],
        knowledge_areas=["Educational Standards (Common Core/NGSS)", "Instructional Scaffolding", "Developmental Psychology"],
        soft_skills=["Methodical Organization", "Educational Passion", "Clear Written Expression"],
    ),
    "academic_coordinator": RoleCompetencyProfile(
        canonical_role="Academic Coordinator",
        domain="Education",
        subdomain="Academic Operations",
        aliases=["Program Coordinator (Academic)", "Education Coordinator"],
        core_competencies=["Academic Program Scheduling & Timetabling", "Student Academic Advising & Progression Tracking", "Faculty Workload Coordination", "Accreditation & Compliance Record Keeping", "Academic Examination Administration"],
        common_competencies=["Student Orientation Planning", "Academic Policy Communication", "Course Feedback Collection & Reporting"],
        optional_competencies=["Curriculum Committee Secretariat", "International Student Support"],
        tools_technologies=["Student Information Systems (SIS)", "Banner", "Canvas", "Excel", "Acuity/Calendly"],
        knowledge_areas=["University/School Academic Regulations", "Accreditation Criteria (ABET/HLC)", "FERPA Compliance"],
        soft_skills=["Warm Empathy with Students", "Masterful Organization", "Calm Problem-Solving"],
    ),
    "professor": RoleCompetencyProfile(
        canonical_role="Professor",
        domain="Education",
        subdomain="Higher Education & Faculty",
        aliases=["Lecturer", "Assistant Professor", "Associate Professor", "University Professor", "Faculty Member"],
        core_competencies=["Undergraduate & Graduate Course Instruction", "Academic Research & Peer-Reviewed Publishing", "Grant Writing & Research Funding Acquisition", "Graduate Student Thesis Supervision", "University & Departmental Committee Service"],
        common_competencies=["Syllabus Design & Academic Rigor", "Scholarly Conference Presentations", "Peer Review of Academic Manuscripts"],
        optional_competencies=["Department Chair Duties", "Sabbatical Research Leadership"],
        tools_technologies=["Canvas/Blackboard", "LaTeX", "Mendeley/Zotero", "Statistical Tools (R/Python)", "Google Scholar"],
        knowledge_areas=["Domain-Specific Scholarship", "Pedagogy in Higher Education", "Academic Freedom & Ethics"],
        soft_skills=["Intellectual Curiosity", "Mentorship", "Oratorical Clarity"],
    ),

    # --------------------------------------------------------------------------
    # 20. Research / Academia (Expanded)
    # --------------------------------------------------------------------------
    "laboratory_scientist": RoleCompetencyProfile(
        canonical_role="Laboratory Scientist",
        domain="Research / Academia",
        subdomain="Laboratory Research & Experimentation",
        aliases=["Lab Scientist", "Bench Scientist", "Laboratory Chemist", "Laboratory Biologist"],
        core_competencies=["Wet-Lab Experimental Protocol Execution", "Sample Preparation & Analytical Assay Setup", "Laboratory Instrumentation (Spectrophotometry, Centrifugation)", "Standard Operating Procedure (SOP) Strict Adherence", "Experimental Data Recording (ELN)"],
        common_competencies=["Chemical & Biological Inventory Management", "Lab Safety & Hazardous Waste Disposal", "Equipment Calibration & Maintenance"],
        optional_competencies=["Cleanroom Operations", "Biohazard Level 2/3 Procedures"],
        tools_technologies=["Electronic Lab Notebooks (Benchling/LabArchives)", "Pipettes", "Centrifuges", "Spectrophotometers", "Excel"],
        knowledge_areas=["Good Laboratory Practice (GLP)", "OSHA Laboratory Safety", "Scientific Method"],
        soft_skills=["Flawless Pipetting/Bench Dexterity", "Observation of Subtle Anomalies", "Meticulous Record Keeping"],
    ),

    # --------------------------------------------------------------------------
    # 21. Media / Creative (Expanded)
    # --------------------------------------------------------------------------
    "content_creator": RoleCompetencyProfile(
        canonical_role="Content Creator",
        domain="Media / Creative",
        subdomain="Digital Content & Social Media",
        aliases=["Digital Creator", "Digital Content Specialist", "Social Media Creator"],
        core_competencies=["Short-Form Video Production (Reels/TikTok/Shorts)", "Scriptwriting & Visual Storyboarding", "Audience Engagement & Community Building", "Digital Photography & Mobile Videography", "Social Platform Trend Identification"],
        common_competencies=["Content Performance Analytics Interpretation", "Thumbnail & Cover Art Design", "Basic Video Editing & Captioning"],
        optional_competencies=["Live Stream Broadcasting", "Brand Partnership & Sponsorship Integration"],
        tools_technologies=["CapCut", "Premiere Rush", "Canva", "Photoshop", "TikTok Analytics", "YouTube Studio"],
        knowledge_areas=["Social Media Algorithms", "Viral Storytelling Hooks", "Copyright & Music Licensing"],
        soft_skills=["Charismatic Authenticity", "Relentless Creative Output", "Adaptability to Trends"],
    ),
    "copywriter": RoleCompetencyProfile(
        canonical_role="Copywriter",
        domain="Media / Creative",
        subdomain="Copywriting & Creative Writing",
        aliases=["Advertising Copywriter", "Creative Copywriter", "Marketing Copywriter"],
        core_competencies=["Persuasive Advertising Headline & Body Copy", "Brand Voice & Tone Guidelines Conception", "Direct-Response & Landing Page Copywriting", "Creative Campaign Conceptualization", "Email Marketing Campaign Sequences"],
        common_competencies=["A/B Copy Testing & Message Refinement", "Collaboration with Art Directors & Designers", "Proofreading & Editorial Polish"],
        optional_competencies=["SEO Copy Optimization", "Scriptwriting for TV & Radio Commercials"],
        tools_technologies=["Google Docs", "Figma (Copy Collaboration)", "Grammarly", "Notion", "Word"],
        knowledge_areas=["Consumer Psychology", "Storytelling Frameworks", "Marketing Funnels"],
        soft_skills=["Witty Linguistic Versatility", "Empathy for the Reader", "Openness to Creative Critique"],
    ),
    "creative_director": RoleCompetencyProfile(
        canonical_role="Creative Director",
        domain="Media / Creative",
        subdomain="Creative Leadership & Art Direction",
        aliases=["Executive Creative Director", "Head of Creative"],
        core_competencies=["Creative Campaign Vision & Strategic Direction", "Creative Team Leadership & Mentorship", "Client Creative Pitching & Stakeholder Alignment", "Brand Identity & Visual Cohesion Governance", "Cross-Channel Concept Development (Digital, Print, Video)"],
        common_competencies=["Production Budget Oversight", "Creative Agency Roster Management", "Critique & Constructive Art Direction"],
        optional_competencies=["Global Brand Architecture", "Experiential Creative Strategy"],
        tools_technologies=["Adobe Creative Cloud", "Figma", "Keynote/PowerPoint", "Slack", "Miro"],
        knowledge_areas=["Cultural & Design Trends", "Brand Strategy", "Advertising Production Workflows"],
        soft_skills=["Charismatic Creative Inspiration", "Decisive Taste", "Business-Creative Translation"],
    ),
    "photographer": RoleCompetencyProfile(
        canonical_role="Photographer",
        domain="Media / Creative",
        subdomain="Commercial & Editorial Photography",
        aliases=["Commercial Photographer", "Portrait Photographer", "Event Photographer"],
        core_competencies=["Camera Operation & Exposure Mastery (Manual Mode)", "Studio & Natural Lighting Direction", "Subject Posing & Art Direction", "RAW Photo Development & Retouching", "Color Profiling & Calibration"],
        common_competencies=["Location Scouting & Shoot Logistics", "Equipment Maintenance & Lens Selection", "Client Digital Asset Delivery & Archiving"],
        optional_competencies=["High-End Fashion Retouching", "Drone Aerial Photography"],
        tools_technologies=["Adobe Lightroom", "Adobe Photoshop", "Capture One", "Studio Strobes", "Sony/Canon/Nikon Systems"],
        knowledge_areas=["Optics & Focal Lengths", "Composition & Framing Rules", "Digital Asset Licensing"],
        soft_skills=["Interpersonal Warmth on Set", "Keen Eye for Ephemeral Light", "Calm Under Unpredictable Weather"],
    ),
    "3d_artist": RoleCompetencyProfile(
        canonical_role="3D Artist",
        domain="Media / Creative",
        subdomain="3D Modeling & Visualization",
        aliases=["3D Generalist", "3D Modeler", "CGI Artist"],
        core_competencies=["Hard-Surface & Organic 3D Modeling", "UV Unwrapping & Texture Mapping", "PBR Material Creation (Substance/Blender)", "3D Scene Lighting & Camera Setup", "High-Fidelity Rendering & Post-Compositing"],
        common_competencies=["Topology Optimization for Games & Real-Time", "Basic 3D Rigging & Keyframe Animation", "Asset Exporting (FBX/OBJ/USD)"],
        optional_competencies=["ZBrush Digital Sculpting", "Volumetric & Particle FX"],
        tools_technologies=["Blender", "Autodesk Maya", "Substance 3D Painter", "ZBrush", "Unreal Engine"],
        knowledge_areas=["PBR Rendering Pipelines", "Light Transport Physics", "Anatomy & Mechanical Structures"],
        soft_skills=["Obsessive Spatial Patience", "Geometric Precision", "Visual Passion"],
    ),

    # --------------------------------------------------------------------------
    # 22. Hospitality / Travel (Expanded)
    # --------------------------------------------------------------------------
    "front_office_manager": RoleCompetencyProfile(
        canonical_role="Front Office Manager",
        domain="Hospitality / Travel",
        subdomain="Front Desk & Guest Services",
        aliases=["Front Desk Manager", "Guest Services Manager"],
        core_competencies=["Front Desk Daily Operations Oversight", "Room Inventory Allocation & Upgrades", "Guest Service Recovery & VIP Treatment", "Property Management System (PMS) Operation", "Night Audit & Financial Balancing Reconciliation"],
        common_competencies=["Front Desk Staff Scheduling & Training", "Check-in / Check-out Queue Optimization", "Concierge & Luggage Coordination"],
        optional_competencies=["Revenue Management Basics (RevPAR)", "Group Block Management"],
        tools_technologies=["Opera PMS", "Amadeus Hospitality", "Maestro", "Excel", "Keycard Systems"],
        knowledge_areas=["Hospitality Standards of Excellence", "Hotel Safety & Emergency Procedures", "Cash Handling Controls"],
        soft_skills=["Infinite Grace & Tact", "Crisis De-escalation", "Warm Welcoming Demeanor"],
    ),
    "travel_consultant": RoleCompetencyProfile(
        canonical_role="Travel Consultant",
        domain="Hospitality / Travel",
        subdomain="Travel Advisory & Booking",
        aliases=["Travel Agent", "Travel Advisor", "Corporate Travel Consultant"],
        core_competencies=["Tailored Itinerary Planning & Route Designing", "Global Distribution System (GDS) Flight & Hotel Booking", "Travel Documentation & Visa Advisory", "Travel Budgeting & Price Negotiation", "Traveler Emergency Support & Disruption Rebooking"],
        common_competencies=["Travel Insurance Recommendations", "Supplier Relationship Management (Hotels/Airlines)", "Group Travel Logistics"],
        optional_competencies=["Luxury Destination Concierge", "Corporate Travel Policy Compliance"],
        tools_technologies=["Amadeus GDS", "Sabre", "Travelport", "CRM", "FlightAware"],
        knowledge_areas=["World Geography & Climatology", "IATA Rules & Ticketing Tariffs", "Visa & Health Entry Requirements"],
        soft_skills=["Passionate Cultural Curiosity", "Unflappable Patience", "Attention to Detail"],
    ),
    "event_manager": RoleCompetencyProfile(
        canonical_role="Event Manager",
        domain="Hospitality / Travel",
        subdomain="Event Planning & Operations",
        aliases=["Event Coordinator", "Event Planner", "Conference Manager"],
        core_competencies=["End-to-End Event Planning & Timeline Execution", "Venue Sourcing & Space Layout Design", "Vendor & Supplier Contract Negotiation (Catering/AV)", "Event Budget Tracking & Cost Control", "On-Site Run-of-Show Stage Management"],
        common_competencies=["Event Registration & Attendee Badge Logistics", "Risk Assessment & Crowd Safety Protocols", "Post-Event Debrief & ROI Analysis"],
        optional_competencies=["Virtual/Hybrid Event Platform Management", "Sponsorship Activation Coordination"],
        tools_technologies=["Cvent", "Eventbrite", "Asana", "Excel", "AllSeated"],
        knowledge_areas=["Hospitality Catering Service Styles", "AV Production Terminology", "Fire Codes & Venue Capacities"],
        soft_skills=["Ironclad Multi-Tasking Nerve", "Contingency Intuition", "Charming Host Presence"],
    ),
    "restaurant_manager": RoleCompetencyProfile(
        canonical_role="Restaurant Manager",
        domain="Hospitality / Travel",
        subdomain="Food & Beverage Operations",
        aliases=["Food and Beverage Manager", "General Manager (Restaurant)"],
        core_competencies=["Front-of-House Dining Room Floor Leadership", "Food & Beverage Cost Control & Waste Minimization", "Food Safety (HACCP/ServSafe) & Hygiene Compliance", "Labor Scheduling & Productivity Optimization", "Guest Dining Experience & Table Visits"],
        common_competencies=["POS System Management & Daily Cash Out", "Staff Hospitality & Wine Service Training", "Supplier Ordering & Inventory Auditing"],
        optional_competencies=["Menu Engineering & Pricing Strategy", "Alcohol Licensing Compliance"],
        tools_technologies=["Toast POS", "Square", "OpenTable / Resy", "Excel", "7shifts"],
        knowledge_areas=["Food Safety Regulations", "Cost of Goods Sold (COGS) Metrics", "Hospitality Service Sequences"],
        soft_skills=["High Energy on the Floor", "Fair Staff Leadership", "Generous Hospitality Spirit"],
    ),

    # --------------------------------------------------------------------------
    # 23. Manufacturing (Expanded)
    # --------------------------------------------------------------------------
    "process_engineer": RoleCompetencyProfile(
        canonical_role="Process Engineer",
        domain="Manufacturing",
        subdomain="Process Optimization & Scaling",
        aliases=["Process Improvement Engineer", "Manufacturing Process Engineer"],
        core_competencies=["Statistical Process Control (SPC) Charting", "Process Capability (Cp/Cpk) Analysis", "Process Yield & Cycle Time Optimization", "Standard Operating Procedure (SOP) Formulation", "Root Cause Analysis (Fishbone/5-Why)"],
        common_competencies=["Design of Experiments (DOE)", "Process Flow Mapping", "Equipment Commissioning Support"],
        optional_competencies=["Continuous Flow Automation", "Cleanroom Process Control"],
        tools_technologies=["Minitab", "AutoCAD", "Excel Advanced", "JMP", "SCADA"],
        knowledge_areas=["Six Sigma DMAIC", "Quality Management Systems", "Thermodynamics & Heat Transfer"],
        soft_skills=["Methodical Persistence", "Data-Driven Objectivity", "Shop Floor Rapport"],
    ),
    "quality_engineer": RoleCompetencyProfile(
        canonical_role="Quality Engineer",
        domain="Manufacturing",
        subdomain="Quality Assurance & Reliability",
        aliases=["QA Engineer (Manufacturing)", "Quality Assurance Engineer (Hardware)"],
        core_competencies=["Failure Mode & Effects Analysis (DFMEA/PFMEA)", "Advanced Product Quality Planning (APQP/PPAP)", "Quality Management System Audits (ISO 9001/IATF 16949)", "Non-Conformance & CAPA Investigation", "Metrology & Coordinate Measuring Machine (CMM) Inspection"],
        common_competencies=["Gauge R&R (Repeatability & Reproducibility) Studies", "Supplier Quality Auditing", "First Article Inspection (FAI)"],
        optional_competencies=["Six Sigma Black Belt Leadership", "Reliability Life Testing (Weibull)"],
        tools_technologies=["Minitab", "CMM Software (PC-DMIS)", "Gage R&R Software", "Excel"],
        knowledge_areas=["ISO 9001 / IATF 16949 Standards", "GD&T Interpretation", "Quality Engineering Principles"],
        soft_skills=["Uncompromising Standards", "Constructive Assertiveness", "Fact-Based Influence"],
    ),
    "maintenance_engineer": RoleCompetencyProfile(
        canonical_role="Maintenance Engineer",
        domain="Manufacturing",
        subdomain="Plant Reliability & Maintenance",
        aliases=["Plant Maintenance Engineer", "Reliability Engineer (Manufacturing)"],
        core_competencies=["Total Productive Maintenance (TPM) Program Execution", "Preventive & Predictive Maintenance Scheduling (CMMS)", "Mean Time Between Failures (MTBF) & MTTR Analysis", "Hydraulic, Pneumatic & Mechanical Troubleshooting", "Programmable Logic Controller (PLC) Diagnostic Support"],
        common_competencies=["Spare Parts Criticality & Inventory Planning", "Vibration Analysis & Thermal Imaging", "Lockout/Tagout (LOTO) Safety Compliance"],
        optional_competencies=["SCADA System Integration", "Robotic Arm Servo Maintenance"],
        tools_technologies=["CMMS (eMaint/Maximo)", "PLC Diagnostic Software (Siemens/Allen-Bradley)", "Multimeters", "Vibration Analyzers"],
        knowledge_areas=["Mechanical & Electrical Systems", "OSHA Machine Guarding", "Plant Safety Protocols"],
        soft_skills=["Calm Breakdown Troubleshooting", "Safety Discipline", "Hands-On Mechanical Mastery"],
    ),

}


# Precompute lookup maps for fast, canonical matching
_ROLE_CANONICAL_LOOKUP: dict[str, RoleCompetencyProfile] = {}
_ROLE_ALIAS_LOOKUP: dict[str, RoleCompetencyProfile] = {}

for _key, _profile in ROLE_TAXONOMY.items():
    _ROLE_CANONICAL_LOOKUP[_profile.canonical_role.lower().strip()] = _profile
    for _alias in _profile.aliases:
        _ROLE_ALIAS_LOOKUP[_alias.lower().strip()] = _profile




@dataclass
class RoleSpecialization:
    specialization_id: str
    target_role_family: str  # must match an existing key in ROLE_TAXONOMY
    domain_override: str | None = None
    subdomain_override: str | None = None
    required_modifier_tokens: set[str] = field(default_factory=set)
    additional_core_competencies: list[str] = field(default_factory=list)
    additional_common_competencies: list[str] = field(default_factory=list)
    additional_tools: list[str] = field(default_factory=list)
    additional_knowledge: list[str] = field(default_factory=list)


ROLE_SPECIALIZATIONS: dict[str, RoleSpecialization] = {
    "healthcare_data": RoleSpecialization(
        specialization_id="healthcare_data",
        target_role_family="data_analyst",
        domain_override="Healthcare",
        subdomain_override="Healthcare & Clinical Analytics",
        required_modifier_tokens={"healthcare"},
        additional_core_competencies=["Electronic Health Record (EHR) Data Querying", "Clinical Quality Metric Tracking (HEDIS/CMS)", "HIPAA Patient Data Compliance"],
        additional_common_competencies=["Healthcare Utilization & Cost Modeling", "Clinical Workflow Data Analysis"],
        additional_tools=["Epic Caboodle/Cogito", "Cerner", "SQL", "Tableau"],
        additional_knowledge=["Healthcare Data Standards (HL7/FHIR)", "CMS Quality Measures", "Clinical Terminologies (ICD/CPT)"],
    ),
    "clinical_data": RoleSpecialization(
        specialization_id="clinical_data",
        target_role_family="data_analyst",
        domain_override="Pharmaceutical / Life Sciences",
        subdomain_override="Clinical Trial Data Analysis",
        required_modifier_tokens={"clinical"},
        additional_core_competencies=["Clinical Trial Data Validation & Querying", "CDISC Standards Compliance (SDTM)", "Patient Safety & Adverse Event Data Tracking"],
        additional_common_competencies=["Electronic Data Capture (EDC) Discrepancy Management", "Clinical Protocol Adherence Audits"],
        additional_tools=["Medidata Rave", "SAS", "SQL", "Excel"],
        additional_knowledge=["Good Clinical Practice (GCP)", "ICH E6 Guidelines", "Clinical Data Management (CDM)"],
    ),
    "application_security": RoleSpecialization(
        specialization_id="application_security",
        target_role_family="security_engineer",
        domain_override="Cybersecurity",
        subdomain_override="Application Security & Secure SDLC",
        required_modifier_tokens={"application"},
        additional_core_competencies=["OWASP Top 10 Vulnerability Remediation", "Static & Dynamic Code Analysis (SAST/DAST)", "Secure Code Review & Developer Security Advocacy"],
        additional_common_competencies=["Software Composition Analysis (SCA)", "Threat Modeling for Web & API Services", "Security Gate Integration in CI/CD"],
        additional_tools=["Snyk", "Checkmarx", "Burp Suite", "SonarQube", "GitLab CI"],
        additional_knowledge=["Secure Coding Principles", "Common Weakness Enumeration (CWE)", "API Security Architecture"],
    ),
    "cloud_security": RoleSpecialization(
        specialization_id="cloud_security",
        target_role_family="security_engineer",
        domain_override="Cybersecurity",
        subdomain_override="Cloud Security & Posture Management",
        required_modifier_tokens={"cloud"},
        additional_core_competencies=["Cloud Security Posture Management (CSPM)", "Container & Kubernetes Security Hardening", "Cloud IAM Principle of Least Privilege"],
        additional_common_competencies=["Cloud Infrastructure Security Scanning", "Cloud Incident Investigation & Forensics"],
        additional_tools=["Prisma Cloud", "Wiz", "AWS GuardDuty", "Terraform", "Kubernetes"],
        additional_knowledge=["CIS Cloud Benchmarks", "Cloud Shared Responsibility Model", "Zero Trust Architecture"],
    ),
    "product_operations": RoleSpecialization(
        specialization_id="product_operations",
        target_role_family="product_manager",
        domain_override="Product",
        subdomain_override="Product Operations & Analytics",
        required_modifier_tokens={"operations"},
        additional_core_competencies=["Product Experimentation Infrastructure & Analysis", "User Feedback Loop Systematization", "Product Release Operations & Launch Readiness"],
        additional_common_competencies=["Product Stack Tooling Administration", "Cross-Functional Voice-of-Customer Synthesis"],
        additional_tools=["Pendo", "Amplitude", "Jira", "LaunchDarkly", "Notion"],
        additional_knowledge=["Product-Led Growth (PLG)", "Experimentation Governance", "Product Operating Models"],
    ),
    "growth_marketing": RoleSpecialization(
        specialization_id="growth_marketing",
        target_role_family="digital_marketing_specialist",
        domain_override="Marketing",
        subdomain_override="Growth & User Acquisition",
        required_modifier_tokens={"growth"},
        additional_core_competencies=["Funnel A/B Testing & Optimization", "Viral Loops & Referral Architecture", "Customer Acquisition Cost (CAC) vs LTV Optimization"],
        additional_common_competencies=["Lifecycle Marketing Automation", "Growth Hypothesis Prioritization (ICE/PIE)"],
        additional_tools=["Google Optimize / VWO", "Segment CDP", "Mixpanel", "HubSpot", "Google Analytics 4"],
        additional_knowledge=["Growth Accounting", "Conversion Rate Optimization (CRO)", "Product-Led Acquisition"],
    ),
    "sales_operations": RoleSpecialization(
        specialization_id="sales_operations",
        target_role_family="operations_analyst",
        domain_override="Sales / Business",
        subdomain_override="Sales Operations & Enablement",
        required_modifier_tokens={"sales"},
        additional_core_competencies=["CRM Pipeline & Quota Modeling (Salesforce)", "Sales Commission & Incentive Structuring", "Sales Velocity & Conversion Funnel Analytics"],
        additional_common_competencies=["Territory Planning & Account Allocation", "Sales Tech Stack Administration"],
        additional_tools=["Salesforce CRM", "Clari", "Gong.io", "Excel Advanced", "Tableau"],
        additional_knowledge=["Sales Methodologies (MEDDIC/Challenger)", "Revenue Operations (RevOps)", "Sales Forecasting Accuracy"],
    ),
    "hospital_operations": RoleSpecialization(
        specialization_id="hospital_operations",
        target_role_family="operations_analyst",
        domain_override="Healthcare",
        subdomain_override="Hospital Operations & Patient Flow",
        required_modifier_tokens={"hospital"},
        additional_core_competencies=["Emergency Department Patient Flow Optimization", "Inpatient Bed Utilization & Capacity Modeling", "Clinical Staffing & Nurse-to-Patient Ratio Analytics"],
        additional_common_competencies=["Operating Room Schedule Balancing", "Healthcare Operational Accreditation (Joint Commission)"],
        additional_tools=["Epic Cadence", "Tableau", "Excel Advanced", "Cerner Capacity Management"],
        additional_knowledge=["Hospital Operational Workflows", "CMS Hospital Inpatient Quality Reporting", "Patient Safety Goals"],
    ),
    "manufacturing_operations": RoleSpecialization(
        specialization_id="manufacturing_operations",
        target_role_family="manufacturing_engineer",
        domain_override="Manufacturing",
        subdomain_override="Plant & Production Operations",
        required_modifier_tokens={"operations"},
        additional_core_competencies=["Plant Production Scheduling & Shift Balancing", "Overall Equipment Effectiveness (OEE) Optimization", "Shop Floor Labor & Material Utilization Tracking"],
        additional_common_competencies=["Daily Stand-Up Tier Management", "Continuous Flow Kaizen Coordination"],
        additional_tools=["MES (Manufacturing Execution Systems)", "ERP (SAP)", "Excel Advanced", "Power BI"],
        additional_knowledge=["Lean Manufacturing Systems", "Shop Floor Management", "Manufacturing Health & Safety"],
    ),
    "legal_operations": RoleSpecialization(
        specialization_id="legal_operations",
        target_role_family="legal_associate",
        domain_override="Legal / Compliance",
        subdomain_override="Legal Operations & Technology",
        required_modifier_tokens={"operations"},
        additional_core_competencies=["Legal Tech & CLM System Administration", "Outside Counsel Spend Analytics & Billing Guidelines", "Legal Workflow & Knowledge Management Systematization"],
        additional_common_competencies=["Legal Vendor Due Diligence", "Contract SLA & Turnaround Tracking"],
        additional_tools=["Ironclad", "SimpleLegal / Brightflag", "DocuSign", "Excel", "Tableau"],
        additional_knowledge=["Legal Department Operations (CLOC Core 12)", "E-Billing Standards (LEDES)", "Corporate Legal Governance"],
    ),
}


def _compose_specialized_profile(
    base_profile: RoleCompetencyProfile,
    spec: RoleSpecialization,
    input_role_name: str,
) -> RoleCompetencyProfile:
    """Safely and deterministically composes a specialized competency profile from a base profile and bounded specialization."""
    title_words = [w.capitalize() for w in input_role_name.strip().split()]
    canonical_title = " ".join(title_words)

    combined_core = list(spec.additional_core_competencies)
    for c in base_profile.core_competencies:
        if c not in combined_core:
            combined_core.append(c)

    combined_common = list(spec.additional_common_competencies)
    for c in base_profile.common_competencies:
        if c not in combined_common:
            combined_common.append(c)

    combined_tools = list(spec.additional_tools)
    for t in base_profile.tools_technologies:
        if t not in combined_tools:
            combined_tools.append(t)

    combined_knowledge = list(spec.additional_knowledge)
    for k in base_profile.knowledge_areas:
        if k not in combined_knowledge:
            combined_knowledge.append(k)

    return RoleCompetencyProfile(
        canonical_role=canonical_title,
        domain=spec.domain_override or base_profile.domain,
        subdomain=spec.subdomain_override or base_profile.subdomain,
        aliases=[input_role_name],
        core_competencies=combined_core[:5],
        common_competencies=combined_common[:4],
        optional_competencies=base_profile.optional_competencies[:3],
        tools_technologies=combined_tools,
        knowledge_areas=combined_knowledge,
        soft_skills=base_profile.soft_skills,
        typical_responsibilities=base_profile.typical_responsibilities,
    )


def _normalize_role_input(raw: str) -> str:
    """Cleans role strings: lowers, removes punctuation noise, collapses spaces."""
    s = raw.lower().strip()
    s = re.sub(r"[/\\_-]+", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def resolve_role(role_name: str | None) -> tuple[RoleCompetencyProfile | None, RoleConfidence, str]:
    """
    Authoritative Semantic Role Resolver.
    
    Guarantees:
    1. NEVER matches single generic tokens alone (e.g. 'analyst', 'engineer', 'manager').
    2. 'Cybersecurity Analyst' will NEVER resolve to 'Data Analyst'.
    3. 'Graphic Designer' will NEVER resolve to 'DevOps Engineer'.
    4. 'Product Manager' will NEVER resolve to 'Software Engineer'.
    5. 'Financial Analyst' will NEVER resolve to 'Data Analyst'.
    6. 'Mechanical Engineer' will NEVER resolve to 'Software Engineer'.
    7. 'Healthcare Analyst' will NEVER resolve to 'Data Analyst'.
    8. Unknown or ambiguous roles (e.g. 'Marine Robotics Engineer' when unmatched)
       return (None, "LOW", reason) with ZERO fabricated tech skills.
    
    Returns:
      (profile, confidence, match_reason)
    """
    if not role_name or not role_name.strip():
        return None, "LOW", "EMPTY_INPUT"

    norm = _normalize_role_input(role_name)
    tokens = set(norm.split())

    # 1. Exact canonical name match
    if norm in _ROLE_CANONICAL_LOOKUP:
        return _ROLE_CANONICAL_LOOKUP[norm], "HIGH", "EXACT_CANONICAL_MATCH"

    # Also check with simple normalization on keys
    for canon_name, prof in _ROLE_CANONICAL_LOOKUP.items():
        if _normalize_role_input(canon_name) == norm:
            return prof, "HIGH", "EXACT_CANONICAL_MATCH"

    # 2. Exact alias match
    if norm in _ROLE_ALIAS_LOOKUP:
        return _ROLE_ALIAS_LOOKUP[norm], "HIGH", "EXACT_ALIAS_MATCH"

    for alias_name, prof in _ROLE_ALIAS_LOOKUP.items():
        if _normalize_role_input(alias_name) == norm:
            return prof, "HIGH", "EXACT_ALIAS_MATCH"

    # 3. Guard against single generic token inputs (e.g. just "Engineer" or "Analyst")
    # If the user typed solely a generic token, reject with LOW confidence
    if norm in GENERIC_ROLE_TOKENS or tokens.issubset(GENERIC_ROLE_TOKENS):
        return None, "LOW", "AMBIGUOUS_GENERIC_TOKEN_ONLY"

    # 4. Multi-word and discriminative modifier matching
    # Extract discriminative tokens (words not in GENERIC_ROLE_TOKENS)
    discriminative_tokens = tokens - GENERIC_ROLE_TOKENS

    # Check against known profiles where ALL discriminative tokens match the profile's canonical identity
    candidates: list[tuple[RoleCompetencyProfile, int, float]] = []

    for prof in ROLE_TAXONOMY.values():
        canon_norm = _normalize_role_input(prof.canonical_role)
        canon_tokens = set(canon_norm.split())
        prof_discriminative = canon_tokens - GENERIC_ROLE_TOKENS

        # Exact match of discriminative modifiers (e.g. {"cybersecurity"}, {"graphic"}, {"mechanical"})
        # If the input has extra unrepresented modifiers (e.g. {"marine", "robotics"} vs {"robotics"}),
        # it is a specialized/niche domain that must NOT be collapsed into an unrelated or overly generic role.
        if prof_discriminative and prof_discriminative == discriminative_tokens:
            overlap = len(tokens.intersection(canon_tokens))
            candidates.append((prof, overlap, 1.0))
            continue

        # Check aliases
        for alias in prof.aliases:
            alias_norm = _normalize_role_input(alias)
            alias_tokens = set(alias_norm.split())
            alias_discriminative = alias_tokens - GENERIC_ROLE_TOKENS
            if alias_discriminative and alias_discriminative == discriminative_tokens:
                overlap = len(tokens.intersection(alias_tokens))
                candidates.append((prof, overlap, 0.95))
                break

    if candidates:
        # Sort by highest ratio and overlap
        candidates.sort(key=lambda x: (x[2], x[1]), reverse=True)
        best_prof, best_overlap, best_ratio = candidates[0]
        conf: RoleConfidence = "HIGH" if best_ratio >= 0.9 else "MEDIUM"
        return best_prof, conf, f"DISCRIMINATIVE_MATCH (ratio={best_ratio:.2f})"

    # 5. Controlled Specialization Matching
    # Decompose input into (base_role_family, specialization_modifier)
    # Allows safe, bounded resolution for compound roles (e.g. Healthcare Data Analyst, Cloud Security Engineer)
    for spec in ROLE_SPECIALIZATIONS.values():
        target_prof = ROLE_TAXONOMY.get(spec.target_role_family)
        if not target_prof:
            continue
        
        # Check canonical tokens and alias tokens of the base profile
        base_token_sets = [set(_normalize_role_input(target_prof.canonical_role).split()) - GENERIC_ROLE_TOKENS]
        for a in target_prof.aliases:
            base_token_sets.append(set(_normalize_role_input(a).split()) - GENERIC_ROLE_TOKENS)

        for base_tokens in base_token_sets:
            if base_tokens and base_tokens.issubset(discriminative_tokens):
                remaining_tokens = discriminative_tokens - base_tokens
                if remaining_tokens and remaining_tokens == spec.required_modifier_tokens:
                    composed = _compose_specialized_profile(target_prof, spec, role_name)
                    return composed, "HIGH", f"CONTROLLED_SPECIALIZATION ({spec.specialization_id})"

    # 6. Specialized Niche / Unknown Roles
    # Examples: "Marine Robotics Engineer", "Spacecraft Propulsion Specialist", "Quantum Cryogenics Technician"
    # Never guess or hallucinate generic tech roles. Return LOW confidence.
    return None, "LOW", "UNCONFIRMED_ROLE_IDENTITY"


match_canonical_role = resolve_role
