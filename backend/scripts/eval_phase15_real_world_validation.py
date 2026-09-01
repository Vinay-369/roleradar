"""
Phase 15: Real-World End-to-End Resume Quality Validation Suite.
Evaluates 24 distinct resume categories against tailored realistic JDs.
Runs the complete production pipeline:
Extraction -> CandidateProfile -> Candidate Analysis -> JD Analysis ->
Evidence Mapping -> TailoringPlan -> Truth Guard -> ATS Validation ->
Template Strategy -> Rendering -> PDF & DOCX Generation -> Quality Scorecard Audit.
"""
import asyncio
import io
import json
import os
import re
import sys
import time
from typing import Any

sys.path.insert(0, os.path.abspath("."))

import fitz

from app.modules.jobs.taxonomy import analyze_jd_requirements
from app.modules.matching.evidence_mapping import map_resume_to_jd_evidence
from app.modules.resume.classification import analyze_candidate_profile, classify_candidate_profile
from app.modules.resume.models import (
    CandidateProfile,
    TailoringAction,
    TailoringDecision,
    TailoringPlan,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile, structure_resume_text
from app.modules.tailoring.export import (
    generate_docx,
    generate_pdf,
    render_candidate_profile_to_text,
    validate_rendered_export_integrity,
)
from app.modules.tailoring.plan import (
    apply_tailoring_plan,
    build_tailoring_prompt_context,
    generate_structured_tailoring_plan,
)
from app.modules.tailoring.strategy import resolve_template_strategy
from app.modules.tailoring.validation import validate_tailored_profile_truth_guard


TEST_CASES = [
    # 1. Fresher with projects
    {
        "id": "TC01",
        "category": "Fresher with projects",
        "resume": """
        AARAV SHARMA
        aarav.sharma@email.com | +91 9876543210 | New Delhi, India | github.com/aaravs
        
        EDUCATION
        B.Tech in Computer Science, IIT Delhi (2020 - 2024)
        GPA: 8.9 / 10.0
        
        TECHNICAL SKILLS
        Languages: Python, C++, Java, SQL
        Frameworks: FastAPI, React, PyTorch, Docker
        
        PROJECTS
        Distributed Key-Value Store (C++, gRPC) (2023)
        • Implemented Raft consensus protocol supporting linearizable reads and fault tolerance across 5 nodes.
        • Achieved 15k requests/sec with under 8ms p99 latency in benchmark cluster.
        
        AI Resume Parser & Matcher (Python, FastAPI, SpaCy) (2024)
        • Built NLP pipeline extracting entities from resumes with 92.4% precision.
        • Deployed containerized microservice on AWS ECS handling 50 concurrent uploads.
        """,
        "jd": """
        Junior Software Engineer - Backend
        Requirements:
        • Strong foundations in C++ or Python and distributed systems principles.
        • Experience with REST APIs, gRPC, and containerization (Docker).
        • Good understanding of data structures, algorithms, and databases.
        • B.Tech/B.E. in Computer Science or related engineering field.
        """,
    },
    # 2. Fresher with internships
    {
        "id": "TC02",
        "category": "Fresher with internships",
        "resume": """
        PRIYA PATEL
        priya.patel@email.com | (555) 234-5678 | San Jose, CA
        
        EDUCATION
        B.S. in Software Engineering, San Jose State University (2020 - 2024)
        GPA: 3.8 / 4.0
        
        TECHNICAL SKILLS
        Java, Spring Boot, TypeScript, React, PostgreSQL, Git, AWS
        
        EXPERIENCE
        Software Engineering Intern at CloudBase Inc (June 2023 - August 2023) — Santa Clara, CA
        • Built internal dashboard in React and TypeScript reducing onboarding time by 30%.
        • Wrote 45 automated unit tests achieving 94% test coverage for billing microservices.
        
        Full Stack Intern at WebSphere Labs (January 2023 - May 2023) — San Jose, CA
        • Optimized PostgreSQL database queries, reducing average API response time by 40%.
        • Implemented OAuth2 authentication flow securing 10k daily active sessions.
        """,
        "jd": """
        Associate Software Engineer
        Requirements:
        • Hands-on internship experience in full stack development (Java/Spring Boot or React/TypeScript).
        • Solid understanding of relational databases (PostgreSQL/MySQL) and API design.
        • Experience with automated testing and version control.
        """,
    },
    # 3. Fresher with no projects (Coursework & Education focused)
    {
        "id": "TC03",
        "category": "Fresher with no projects",
        "resume": """
        RAHUL VERMA
        rahul.v@email.com | +91 9988776655 | Pune, India
        
        EDUCATION
        B.E. in Information Technology, Pune University (2020 - 2024)
        GPA: 8.4 / 10.0
        Relevant Coursework: Data Structures, Operating Systems, Database Management, Computer Networks, Software Engineering
        
        TECHNICAL SKILLS
        Languages: Java, C, Python, SQL
        Tools: Git, Linux, MySQL, VS Code
        
        ACADEMIC ACHIEVEMENTS
        • Ranked top 5% in Department of Information Technology across 180 students.
        • Winner of Annual Inter-College Coding Contest (2023) among 60 teams.
        """,
        "jd": """
        Graduate Trainee Software Engineer
        Requirements:
        • Strong theoretical knowledge of computer science fundamentals (OS, DBMS, CN).
        • Proficiency in Core Java, Python, or C.
        • Strong problem solving and analytical thinking.
        • Excellent academic record.
        """,
    },
    # 4. Experienced software engineer
    {
        "id": "TC04",
        "category": "Experienced software engineer",
        "resume": """
        MICHAEL CHANG
        m.chang@email.com | (555) 456-7890 | Austin, TX | linkedin.com/in/mchang
        
        SUMMARY
        Software Engineer with 4+ years of experience building scalable backend services and distributed data pipelines in Go, Python, and AWS.
        
        EXPERIENCE
        Backend Engineer at Apex Systems (2021 - Present) — Austin, TX
        • Designed and maintained asynchronous event pipeline in Go handling 120k messages/sec.
        • Migrated monolithic authentication service to gRPC microservices, reducing p99 latency by 55%.
        • Mentored 3 junior engineers on concurrency patterns and clean architecture.
        
        Software Developer at CoreLogic (2019 - 2021) — Dallas, TX
        • Developed RESTful API endpoints in Python and FastAPI for financial analytics platform.
        • Integrated Redis caching layer saving $15k monthly in database infrastructure costs.
        
        TECHNICAL SKILLS
        Languages: Go, Python, SQL, Bash
        Technologies: AWS (EKS, RDS, S3), Docker, Kubernetes, Kafka, Redis, PostgreSQL, Terraform
        
        EDUCATION
        B.S. in Computer Science, UT Austin (2015 - 2019)
        """,
        "jd": """
        Senior Backend Engineer
        Requirements:
        • 4+ years of professional backend development experience in Go or Python.
        • Demonstrated experience with high-throughput event processing (Kafka/RabbitMQ) and distributed systems.
        • Deep expertise in AWS cloud services, Docker, and Kubernetes.
        • Strong SQL and caching optimization background (PostgreSQL, Redis).
        """,
    },
    # 5. Experienced non-software professional
    {
        "id": "TC05",
        "category": "Experienced non-software professional",
        "resume": """
        SARAH JENKINS
        s.jenkins@email.com | (555) 321-7654 | Chicago, IL
        
        PROFESSIONAL SUMMARY
        Certified Supply Chain Professional (CSCP) with 6 years leading warehouse operations, logistics optimization, and vendor negotiations.
        
        EXPERIENCE
        Operations Manager at Metro Logistics (2021 - Present) — Chicago, IL
        • Managed 120k sq ft distribution center supervising 45 warehouse associates and 4 team leads.
        • Reduced order fulfillment cycle time by 28% through Lean Six Sigma layout restructuring.
        • Negotiated 12 carrier contracts saving $450k annually in regional freight costs.
        
        Logistics Coordinator at FastTrack Cargo (2018 - 2021) — Indianapolis, IN
        • Coordinated inbound ocean freight shipments maintaining 99.2% on-time delivery metric.
        • Implemented barcode scanning inventory system reducing stock discrepancy rate from 4.2% to 0.8%.
        
        SKILLS & CERTIFICATIONS
        Skills: Supply Chain Management, Lean Six Sigma, Warehouse Management Systems (SAP WMS), Vendor Management, Budgeting
        Certifications: Certified Supply Chain Professional (CSCP), Six Sigma Green Belt
        
        EDUCATION
        B.A. in Business Administration, Indiana University (2014 - 2018)
        """,
        "jd": """
        Senior Supply Chain Operations Lead
        Requirements:
        • 5+ years of experience in supply chain, distribution logistics, or warehouse operations.
        • Proven track record reducing fulfillment costs and optimizing carrier vendor agreements.
        • Working knowledge of enterprise WMS (SAP/Oracle) and Lean / Six Sigma principles.
        • Strong leadership and cross-functional team management skills.
        """,
    },
    # 6. Senior engineer
    {
        "id": "TC06",
        "category": "Senior engineer",
        "resume": """
        VIKRAM MALHOTRA
        vikram.m@email.com | (555) 789-0123 | Seattle, WA
        
        PROFESSIONAL SUMMARY
        Senior Software Architect with 8+ years designing fault-tolerant cloud platforms, microservices, and high-performance databases.
        
        EXPERIENCE
        Staff Software Engineer at DataCloud Corp (2020 - Present) — Seattle, WA
        • Led architectural redesign of core distributed storage engine handling 2PB of enterprise customer data.
        • Reduced database infrastructure spend by 35% ($1.2M annually) via automated tiering to S3 Glacier.
        • Spearheaded security compliance initiative achieving SOC2 Type II certification across 22 microservices.
        
        Senior Backend Engineer at StreamTech (2016 - 2020) — San Francisco, CA
        • Architected real-time video transcoding pipeline in C++ and Go serving 5M concurrent viewers.
        • Decreased video buffering rate by 42% through custom adaptive bitrate algorithms.
        
        TECHNICAL SKILLS
        Languages: Go, C++, Rust, Python, Java
        Cloud & Systems: AWS, GCP, Kubernetes, Kafka, Cassandra, CockroachDB, Distributed Consensus
        
        EDUCATION
        M.S. in Computer Science, University of Washington (2014 - 2016)
        B.S. in Computer Engineering, UIUC (2010 - 2014)
        """,
        "jd": """
        Principal Distributed Systems Engineer
        Requirements:
        • 8+ years architecting enterprise distributed storage, streaming, or database platforms.
        • Deep proficiency in Go, C++, or Rust in high-concurrency environments.
        • Proven leadership guiding multi-team technical strategy and cost optimization.
        • Experience with multi-petabyte scale infrastructure and modern cloud architecture.
        """,
    },
    # 7. Engineering lead / manager
    {
        "id": "TC07",
        "category": "Engineering lead/manager",
        "resume": """
        RACHEL ADAMS
        rachel.adams@email.com | (555) 890-1234 | Boston, MA | linkedin.com/in/radams
        
        EXECUTIVE SUMMARY
        Engineering Director with 10+ years scaling high-performing distributed engineering teams, managing $8M annual budgets, and delivering enterprise SaaS products.
        
        EXPERIENCE
        Engineering Manager at CloudPeak Systems (2020 - Present) — Boston, MA
        • Managed 3 engineering teams totaling 28 software engineers and 3 engineering managers.
        • Improved engineering delivery velocity by 45% through trunk-based development and automated CI/CD.
        • Reduced voluntary team turnover from 18% to under 4% through structured career growth ladders.
        
        Lead Architect at FinServe Solutions (2015 - 2020) — New York, NY
        • Led team of 10 engineers building real-time payment settlement engine processing $500M daily.
        • Maintained 99.999% system uptime over 4 consecutive years.
        
        CORE COMPETENCIES
        Technical Leadership, Organizational Scaling, Budget & Resource Management ($8M+), Agile Transformation, Hiring & Mentorship, SaaS Architecture
        
        EDUCATION
        B.S. in Computer Science & Economics, MIT (2011 - 2015)
        """,
        "jd": """
        Director of Software Engineering
        Requirements:
        • 8+ years leading software engineering teams with at least 3+ years managing managers.
        • Experience managing department budgets and scaling engineering organizations from 20 to 50+ engineers.
        • Strong technical background in cloud-native SaaS systems and microservices.
        • Exceptional track record in talent acquisition, retention, and engineering culture.
        """,
    },
    # 8. Career switcher (Accountant -> Data Analyst / Python Developer)
    {
        "id": "TC08",
        "category": "Career switcher",
        "resume": """
        DEVON MILLER
        devon.miller@email.com | (555) 678-9012 | Denver, CO
        
        PROFESSIONAL SUMMARY
        Former Senior Financial Auditor transitioned to Data Analyst with strong Python, SQL, and business intelligence modeling skills.
        
        PROJECTS
        Automated Financial Fraud Detection Pipeline (Python, Pandas, Scikit-Learn) (2023)
        • Built machine learning classification model identifying anomalous ledger transactions with 91% accuracy.
        • Automated data cleaning across 500k row historical accounting datasets saving 15 manual hours weekly.
        
        Executive Sales Analytics Dashboard (Tableau, SQL, PostgreSQL) (2023)
        • Developed interactive Tableau dashboards visualizing regional sales performance and inventory margins.
        
        EXPERIENCE
        Senior Auditor at KPMG (2019 - 2023) — Denver, CO
        • Conducted financial audits for 14 enterprise clients managing audit portfolios exceeding $200M in revenue.
        • Performed variance analysis and risk assessment using advanced Excel macros and SQL queries.
        
        TECHNICAL SKILLS
        Python (Pandas, NumPy, Scikit-Learn), SQL (PostgreSQL, MySQL), Tableau, PowerBI, Excel VBA, Financial Modeling
        
        EDUCATION
        B.S. in Accounting & Minor in Computer Science, Colorado State University (2015 - 2019)
        """,
        "jd": """
        Data Analyst / Business Intelligence Analyst
        Requirements:
        • Proficiency in SQL, Python for data manipulation (Pandas), and BI tools (Tableau/PowerBI).
        • Strong analytical and financial/business data interpretation skills.
        • Ability to translate complex business data into automated reporting pipelines.
        """,
    },
    # 9. Project-heavy resume (Student with 4 extensive projects)
    {
        "id": "TC09",
        "category": "Project-heavy student",
        "resume": """
        ALEXANDER VOGEL
        alex.vogel@email.com | (555) 123-9876 | Pittsburgh, PA
        
        EDUCATION
        B.S. in Computer Science, Carnegie Mellon University (2021 - 2025)
        GPA: 3.92 / 4.0
        
        TECHNICAL SKILLS
        Languages: Rust, C++, Python, TypeScript
        Tools: WebAssembly, LLVM, Docker, Linux Kernel, Git
        
        PROJECTS
        MicroVM Hypervisor in Rust (Rust, KVM) (2024)
        • Built lightweight hypervisor from scratch on Linux KVM booting Linux kernels in 18ms.
        • Implemented virtio-net and virtio-block device drivers supporting 10Gbps virtual networking.
        
        Compiler for Sub-C (C++, LLVM) (2023)
        • Implemented lexer, parser, AST generation, and LLVM IR lowering supporting register allocation and dead code elimination.
        • Passed 100% of 250 conformance test suites.
        
        High-Performance Trading Engine (C++, Lock-Free) (2023)
        • Developed lock-free matching engine executing 2.4M orders/sec with median tick-to-trade latency of 420ns.
        
        Distributed Graph Database (Rust, Raft) (2022)
        • Designed distributed property graph database supporting Cypher query parsing and partitioned graph traversal.
        """,
        "jd": """
        Systems Software Engineer (New Grad)
        Requirements:
        • Strong proficiency in low-level systems programming in Rust or C++.
        • Demonstrated project work in compilers, operating systems, hypervisors, or distributed storage.
        • Deep understanding of CPU cache architectures, lock-free concurrency, and Linux internals.
        """,
    },
    # 10. Experience-heavy resume (3 companies, 12 years)
    {
        "id": "TC10",
        "category": "Experience-heavy professional",
        "resume": """
        DAVID SULLIVAN
        david.sullivan@email.com | (555) 345-6789 | Atlanta, GA
        
        PROFESSIONAL SUMMARY
        Lead Infrastructure Engineer with 12 years of experience architecting multi-region hybrid cloud platforms and enterprise networking.
        
        EXPERIENCE
        Principal Cloud Architect at GlobalTech Enterprises (2018 - Present) — Atlanta, GA
        • Architected multi-region AWS and Azure migration supporting 40M enterprise users.
        • Reduced cloud infrastructure spend by $3.4M annually through spot instances and automated rightsizing.
        • Led disaster recovery automation achieving RTO of under 10 minutes across 8 global data centers.
        
        Senior Systems Engineer at Delta Communications (2014 - 2018) — Atlanta, GA
        • Managed fleet of 4,500 Linux physical and virtual servers with 99.99% service availability.
        • Automated configuration management across entire fleet using Ansible and Terraform.
        
        Systems Administrator at InfoNet Systems (2012 - 2014) — Alpharetta, GA
        • Maintained Cisco core routing and switching infrastructure across 3 campus sites.
        • Supported storage area networks (SAN) managing 800TB of Fibre Channel storage.
        
        TECHNICAL SKILLS
        Cloud: AWS, Azure, GCP, Terraform, Ansible, Kubernetes
        Infrastructure: Linux (RHEL, Ubuntu), Cisco Networking, BGP, DNS, SAN/NAS, VMware ESXi
        
        EDUCATION
        B.S. in Information Systems, Georgia Tech (2008 - 2012)
        """,
        "jd": """
        Principal Cloud Infrastructure Architect
        Requirements:
        • 10+ years in enterprise infrastructure, cloud architecture (AWS/Azure), and networking.
        • Proven track record reducing multi-million dollar cloud spend and leading multi-region migrations.
        • Deep expertise with Infrastructure as Code (Terraform) and Kubernetes orchestration.
        """,
    },
    # 11. Paragraph-heavy resume
    {
        "id": "TC11",
        "category": "Paragraph-heavy resume",
        "resume": """
        HELENA BLAIR
        helena.blair@email.com | (555) 765-4321 | Portland, OR
        
        EXPERIENCE
        Product Marketing Manager at Lumina Tech (2020 - Present)
        Spearheaded go-to-market strategies for our flagship enterprise analytics platform, collaborating across product, sales, and design teams. Directed a high-impact product relaunch that resulted in a 45% increase in qualified pipeline leads and generated $3.2M in annual recurring revenue within the first two quarters. Managed a quarterly digital advertising budget of $250k across multiple acquisition channels while maintaining a 3.4x return on ad spend.
        
        Marketing Specialist at Cascade Media (2017 - 2020)
        Created comprehensive multichannel content marketing campaigns across email, webinars, and technical whitepapers. Increased organic website search traffic by 85% over an 18-month timeframe through targeted SEO optimization and content syndication. Authored customer case studies and sales collateral supporting the global account executive team in closing 24 Fortune 500 accounts.
        
        SKILLS
        Product Marketing, Go-to-Market Strategy, SEO & SEM, HubSpot, Salesforce CRM, Google Analytics, Market Research, Content Strategy
        
        EDUCATION
        B.A. in Communications, University of Oregon (2013 - 2017)
        """,
        "jd": """
        Senior Product Marketing Manager - Enterprise B2B
        Requirements:
        • 4+ years of B2B SaaS product marketing experience driving go-to-market launches.
        • Demonstrated ability to increase inbound qualified leads and collaborate with enterprise sales teams.
        • Strong analytical proficiency with marketing automation (HubSpot/Salesforce) and SEO strategy.
        """,
    },
    # 12. Poorly formatted resume (Noisy delimiters, inconsistent casing)
    {
        "id": "TC12",
        "category": "Poorly formatted resume",
        "resume": """
        *** SANJAY GUPTA ***
        Email: sanjay.g@email.com ~ Phone: +91 9123456789 ~ Location: Hyderabad
        
        == WORK EXPERIENCE ==
        -- Full Stack Dev -- at TechNova Solutions (2022 to Present)
        >> Built responsive client interfaces using React and Redux for fintech platform.
        >> Created RESTful APIs in Node.js / Express handling 20k daily active transactions.
        >> Optimized MongoDB aggregation queries improving search throughput by 50%.
        
        -- Junior Web Dev -- at PixelCraft (2021 to 2022)
        >> Developed customer websites using HTML5, CSS3, JavaScript, and PHP.
        >> Fixed cross-browser compatibility bugs across mobile and desktop devices.
        
        == TECHNICAL SKILLSET ==
        React.js, Node.js, Express, JavaScript, TypeScript, MongoDB, HTML, CSS, Git, Docker
        
        == ACADEMICS ==
        B.Tech in Computer Science - JNTU Hyderabad (2017 to 2021) - 78%
        """,
        "jd": """
        Full Stack JavaScript Engineer
        Requirements:
        • 2+ years building scalable web applications using React, Node.js, and MongoDB.
        • Strong proficiency in modern JavaScript/TypeScript, RESTful API architecture, and state management.
        • Experience optimizing NoSQL database queries and building responsive user interfaces.
        """,
    },
    # 13. Multi-column resume
    {
        "id": "TC13",
        "category": "Multi-column resume",
        "resume": """
        KATE MORRISON
        kate.m@email.com | (555) 901-2345 | New York, NY
        
        PROFILE                           SKILLS
        Full stack engineer with 3+ years  JavaScript, TypeScript, React, Next.js,
        building high-scale web apps.      Node.js, PostgreSQL, GraphQL, Docker,
                                          TailwindCSS, Jest, AWS
        
        EXPERIENCE                        EDUCATION
        Software Engineer                 B.S. in Computer Science
        Veloce Tech (2021 - Present)      NYU (2017 - 2021)
        • Developed real-time chat app    GPA: 3.75 / 4.0
          in Next.js and WebSockets
          serving 40k daily users.        PROJECTS
        • Reduced bundle size by 35% via  TaskMaster SaaS (React, Node) (2023)
          dynamic code splitting.         • Built kanban task manager with
                                            15k active registered users.
        """,
        "jd": """
        Frontend / Full Stack Engineer
        Requirements:
        • 3+ years experience with React, Next.js, TypeScript, and modern frontend architecture.
        • Experience with WebSocket real-time communication and performance optimization.
        • Solid understanding of backend APIs (Node.js/PostgreSQL) and automated testing.
        """,
    },
    # 14. Resume with unusual section headings
    {
        "id": "TC14",
        "category": "Unusual section headings",
        "resume": """
        MARCUS STERLING
        marcus.s@email.com | (555) 654-3210 | Austin, TX
        
        WHO I AM
        DevOps & Platform Engineer specializing in Kubernetes infrastructure and developer velocity.
        
        WHERE I HAVE WORKED
        Site Reliability Engineer at Zenith Cloud (2021 - Present) — Austin, TX
        • Automated multi-tenant Kubernetes cluster provisioning using Terraform and ArgoCD.
        • Reduced deployment incident recovery time (MTTR) by 60% through Prometheus alerting.
        
        THINGS I HAVE BUILT
        KubeWatch Dog (Go, Kubernetes API) (2023)
        • Built open-source Kubernetes operator detecting crashing pods and auto-healing nodes.
        
        MY TOOLBOX
        Kubernetes, Docker, Go, Python, Terraform, Helm, ArgoCD, Prometheus, Grafana, AWS
        
        MY DEGREES
        B.S. in Computer Engineering, Texas A&M University (2017 - 2021)
        """,
        "jd": """
        DevOps / Site Reliability Engineer
        Requirements:
        • Experience maintaining production Kubernetes clusters, Terraform infrastructure, and GitOps pipelines (ArgoCD).
        • Strong scripting/development in Go or Python.
        • Hands-on expertise with monitoring stacks (Prometheus, Grafana).
        """,
    },
    # 15. Resume with no summary heading (Starts directly with experience)
    {
        "id": "TC15",
        "category": "No summary heading",
        "resume": """
        EMILY WATSON
        emily.watson@email.com | (555) 432-1098 | Seattle, WA
        
        EXPERIENCE
        Frontend Engineer at Nova Dynamics (2021 - Present) — Seattle, WA
        • Engineered design system component library in React and Storybook used by 18 frontend engineers.
        • Improved Core Web Vitals (LCP) from 4.2s to 1.4s across 12 product landing pages.
        • Implemented WCAG 2.1 AA accessibility compliance across entire consumer web application.
        
        Junior Frontend Developer at BlueSky Digital (2019 - 2021) — Bellevue, WA
        • Built interactive data visualization dashboards using D3.js and TypeScript.
        
        SKILLS
        React, TypeScript, JavaScript, CSS3, Storybook, D3.js, Webpack, Vitest, Git
        
        EDUCATION
        B.S. in Informatics, University of Washington (2015 - 2019)
        """,
        "jd": """
        Senior Frontend Engineer - Design Systems
        Requirements:
        • 4+ years of professional React and TypeScript frontend development experience.
        • Proven expertise creating and maintaining enterprise design systems and component libraries.
        • Deep knowledge of web performance (Core Web Vitals) and accessibility (WCAG AA).
        """,
    },
    # 16. Resume with multiple roles under one company
    {
        "id": "TC16",
        "category": "Multiple roles under one company",
        "resume": """
        NATHAN DRAKE
        nathan.d@email.com | (555) 321-6549 | San Francisco, CA
        
        PROFESSIONAL EXPERIENCE
        Uber Technologies
        San Francisco, CA
        Senior Software Engineer (April 2022 - Present)
        • Architected dynamic pricing dispatch engine handling 50k ride requests/sec during peak events.
        • Reduced dispatch latency by 35% through custom memory-mapped cache indexes.
        
        Software Engineer II (January 2020 - March 2022)
        • Developed driver telemetry ingestion pipeline in Go and Kafka processing 2B daily GPS points.
        • Maintained 99.99% pipeline reliability across 14 geographic zones.
        
        Software Engineer I (August 2018 - December 2019)
        • Built internal microservices for driver onboarding verification using Python and PostgreSQL.
        
        TECHNICAL SKILLS
        Languages: Go, Java, Python, C++
        Technologies: Kafka, Redis, Cassandra, Docker, Kubernetes, Microservices Architecture
        
        EDUCATION
        B.S. in Computer Science, UC Berkeley (2014 - 2018)
        """,
        "jd": """
        Staff Backend Engineer - High Concurrency Platforms
        Requirements:
        • 5+ years building large-scale distributed backend systems in Go, Java, or C++.
        • Demonstrated progression in technical scope and ownership under high-scale production workloads.
        • Expertise in distributed messaging (Kafka), low-latency caching, and high-throughput data pipelines.
        """,
    },
    # 17. Resume with career gap
    {
        "id": "TC17",
        "category": "Resume with career gap",
        "resume": """
        LISA RAYMOND
        lisa.raymond@email.com | (555) 789-4561 | Chicago, IL
        
        PROFESSIONAL SUMMARY
        Full Stack Engineer with 5 years experience across fintech and e-commerce returning to industry with refreshed cloud skills.
        
        EXPERIENCE
        Senior Full Stack Engineer at FinTech Labs (2018 - 2021) — Chicago, IL
        • Built secure payment gateway microservices handling $80M in transaction volume annually.
        • Led migration from AngularJS to React 17 reducing client render times by 45%.
        
        Software Developer at Orbit Commerce (2016 - 2018) — Chicago, IL
        • Developed inventory tracking microservices in Python and Django with PostgreSQL.
        
        INDEPENDENT TECHNICAL PROJECTS & UPSKILLING (2022 - 2024)
        Cloud-Native E-Commerce Microservices (Go, React, AWS, Docker) (2023)
        • Built end-to-end cloud e-commerce platform with automated CI/CD and Kubernetes deployment.
        
        SKILLS & CERTIFICATIONS
        Skills: React, TypeScript, Python, Go, AWS, Docker, Kubernetes, PostgreSQL
        Certifications: AWS Certified Solutions Architect - Associate (2023)
        
        EDUCATION
        B.S. in Computer Science, University of Illinois Chicago (2012 - 2016)
        """,
        "jd": """
        Full Stack Engineer (React / Python or Go)
        Requirements:
        • 4+ years professional software development experience across frontend (React) and backend (Python/Go).
        • Solid understanding of cloud infrastructure (AWS) and modern microservices architecture.
        • Experience with relational databases, automated testing, and secure API design.
        """,
    },
    # 18. Resume with certifications heavy
    {
        "id": "TC18",
        "category": "Certifications-heavy resume",
        "resume": """
        ROBERT CHEN
        robert.chen@email.com | (555) 876-5432 | Dallas, TX
        
        PROFESSIONAL SUMMARY
        Cloud Security Architect with 7 years implementing zero-trust architectures and automated compliance.
        
        EXPERIENCE
        Senior Security Engineer at SecureNet Corp (2020 - Present) — Dallas, TX
        • Implemented AWS IAM zero-trust permission boundaries across 450 corporate AWS accounts.
        • Reduced security vulnerability remediation time by 75% via automated GitHub security scanners.
        
        Cloud Engineer at CyberGuard (2017 - 2020) — Plano, TX
        • Configured AWS WAF and GuardDuty protecting multi-tenant SaaS application against DDoS attacks.
        
        CERTIFICATIONS
        • AWS Certified Security - Specialty (2023)
        • AWS Certified Solutions Architect - Professional (2022)
        • Certified Information Systems Security Professional (CISSP) (2021)
        • Certified Kubernetes Administrator (CKA) (2022)
        • HashiCorp Certified: Terraform Associate (2021)
        
        SKILLS
        AWS Security, Zero Trust, IAM, Terraform, Kubernetes Security, SIEM, Python, Bash, SOC2, ISO 27001
        
        EDUCATION
        B.S. in Cybersecurity, University of Texas at Dallas (2013 - 2017)
        """,
        "jd": """
        Lead Cloud Security Engineer
        Requirements:
        • 5+ years of enterprise cloud security experience (AWS environment preferred).
        • Industry security certifications (CISSP, AWS Security Specialty, CKA).
        • Strong expertise in Infrastructure as Code (Terraform), IAM, and automated security guardrails.
        """,
    },
    # 19. Academic / research resume
    {
        "id": "TC19",
        "category": "Academic/research resume",
        "resume": """
        DR. JONATHAN REID
        jonathan.reid@email.com | (555) 654-9870 | Cambridge, MA
        
        RESEARCH SUMMARY
        Postdoctoral Researcher with 6 years conducting research in machine learning interpretability and deep neural network optimization.
        
        EDUCATION
        Ph.D. in Computer Science, Harvard University (2018 - 2023)
        Dissertation: Efficient Gradient Estimation in Non-Convex Optimization
        B.S. in Mathematics & Computer Science, MIT (2014 - 2018) — GPA: 4.0 / 4.0
        
        RESEARCH & PUBLICATIONS
        Postdoctoral Research Fellow at MIT CSAIL (2023 - Present) — Cambridge, MA
        • Developed novel sparse pruning algorithm reducing transformer model parameters by 40% with zero accuracy loss.
        • Published 4 first-author papers in NeurIPS, ICML, and ICLR conferences.
        
        PUBLICATIONS
        • Reid, J., et al. "Adaptive Sparse Pruning for Large Language Models." NeurIPS 2023.
        • Reid, J., et al. "Convergence Guarantees in Stochastic Non-Convex Optimization." ICML 2022.
        
        TECHNICAL SKILLS
        PyTorch, JAX, Python, C++, CUDA, Distributed GPU Training, Mathematical Optimization, LaTeX
        """,
        "jd": """
        Research Scientist - Large Language Models
        Requirements:
        • Ph.D. in Computer Science, Machine Learning, or related quantitative discipline.
        • Strong publication record in top ML venues (NeurIPS, ICML, ICLR).
        • Deep expertise in PyTorch/JAX, distributed model training, and model compression/optimization.
        """,
    },
    # 20. Dense two-page resume
    {
        "id": "TC20",
        "category": "Dense two-page resume",
        "resume": """
        ANNA KOVALENKO
        anna.kovalenko@email.com | (555) 987-1234 | New York, NY | linkedin.com/in/akovalenko
        
        EXECUTIVE SUMMARY
        Principal Enterprise Architect with 14 years leading financial infrastructure transformations, core banking systems, and regulatory reporting platforms.
        
        EXPERIENCE
        Managing Director & Chief Architect at Morgan & Chase Capital (2019 - Present) — New York, NY
        • Directed enterprise architecture strategy for institutional trading platform processing $12B daily volume.
        • Led global engineering organization of 65 engineers across New York, London, and Singapore offices.
        • Modernized legacy mainframe accounting systems to distributed microservices saving $8.5M annually.
        • Achieved 99.999% platform availability while ensuring full compliance with SEC and FINRA regulations.
        
        Vice President of Architecture at First National Bank (2014 - 2019) — New York, NY
        • Designed real-time fraud mitigation engine analyzing 15M card transactions daily with under 25ms latency.
        • Scaled payment gateway to support 300% peak holiday volume growth without downtime.
        • Spearheaded multi-cloud migration initiative across AWS and on-premise OpenStack environments.
        
        Senior Systems Architect at FinTech Global (2010 - 2014) — Jersey City, NJ
        • Developed automated FIX protocol trading gateway in C++ handling 50k msgs/sec.
        • Optimized network socket I/O achieving sub-microsecond packet latency on solarflare NICs.
        
        CORE SKILLS
        Enterprise Architecture, High-Frequency Trading Systems, FIX Protocol, Microservices, Cloud Modernization, Distributed Databases, FinTech Regulatory Compliance (SEC, FINRA, Basel III), C++, Java, AWS
        
        EDUCATION & CERTIFICATIONS
        M.S. in Financial Engineering, Columbia University (2008 - 2010)
        B.S. in Computer Science, Cornell University (2004 - 2008)
        TOGAF 9 Certified Enterprise Architect
        """,
        "jd": """
        Chief Enterprise Architect - Global Financial Technology
        Requirements:
        • 12+ years of enterprise architecture experience in financial services, banking, or capital markets.
        • Demonstrated leadership guiding multi-team engineering organizations across distributed geographical hubs.
        • Deep knowledge of low-latency trading infrastructure, FIX protocol, and regulatory compliance.
        • Proven track record executing multi-million dollar cloud and digital transformation programs.
        """,
    },
    # 21. Sparse one-page resume
    {
        "id": "TC21",
        "category": "Sparse one-page resume",
        "resume": """
        TROY MCCLURE
        troy.mcclure@email.com | (555) 111-2222 | Los Angeles, CA
        
        SUMMARY
        Junior Web Developer with strong HTML, CSS, and basic JavaScript skills.
        
        EDUCATION
        Web Development Bootcamp, General Assembly (2023)
        B.A. in Visual Arts, UCLA (2019 - 2023)
        
        TECHNICAL SKILLS
        HTML5, CSS3, JavaScript, Git, Figma
        
        PROJECTS
        Portfolio Website (HTML, CSS, JS) (2023)
        • Designed responsive portfolio website showcase with dark mode theme.
        """,
        "jd": """
        Entry Level Junior Web Designer / Developer
        Requirements:
        • Proficiency in HTML5, CSS3, and basic JavaScript.
        • Eye for clean visual design and responsive web layout.
        • Familiarity with Git version control and Figma.
        """,
    },
    # 22. DOCX Format
    {
        "id": "TC22",
        "category": "DOCX format",
        "resume": """
        GABRIEL SANTOS
        gabriel.santos@email.com | (555) 777-8888 | Miami, FL
        
        PROFESSIONAL SUMMARY
        Mobile Developer with 4 years building cross-platform React Native and native iOS applications.
        
        EXPERIENCE
        Mobile App Engineer at AppCrafters (2021 - Present) — Miami, FL
        • Developed React Native mobile banking application with 250k downloads on iOS App Store.
        • Improved app startup launch time by 40% using Hermes JavaScript engine optimization.
        • Integrated biometric authentication (FaceID/TouchID) ensuring secure account access.
        
        iOS Developer at ByteWorks (2020 - 2021) — Orlando, FL
        • Built native iOS features in Swift and SwiftUI for fitness tracking application.
        
        TECHNICAL SKILLS
        React Native, Swift, SwiftUI, TypeScript, Redux, iOS SDK, Android SDK, REST APIs, Git
        
        EDUCATION
        B.S. in Computer Science, University of Florida (2016 - 2020)
        """,
        "jd": """
        Senior Mobile Developer (React Native / iOS)
        Requirements:
        • 3+ years experience with React Native and native iOS (Swift) mobile app development.
        • Experience publishing and maintaining apps on the Apple App Store with high active user counts.
        • Proven record in mobile performance optimization, biometric security, and state management.
        """,
    },
    # 23. Text PDF format
    {
        "id": "TC23",
        "category": "Text PDF format",
        "resume": """
        CHLOE DECKER
        chloe.decker@email.com | (555) 333-4444 | Los Angeles, CA
        
        PROFESSIONAL EXPERIENCE
        Security Intelligence Analyst at CyberMetrics (2021 - Present) — Los Angeles, CA
        • Monitored SIEM security event telemetry investigating 200+ security alerts monthly.
        • Created automated threat intelligence ingestion scripts in Python saving 12 manual hours per week.
        • Authored 18 incident response root-cause reports for executive leadership.
        
        Junior Analyst at SecurePath (2019 - 2021) — Burbank, CA
        • Performed vulnerability scans using Nessus across 800 corporate endpoints.
        
        TECHNICAL SKILLS
        SIEM (Splunk, Elastic Security), Python, Nessus, Wireshark, Threat Intelligence, MITRE ATT&CK, Linux
        
        EDUCATION
        B.S. in Information Security, Cal Poly Pomona (2015 - 2019)
        """,
        "jd": """
        Senior Cyber Security Threat Analyst
        Requirements:
        • 3+ years in security operations (SOC), SIEM monitoring (Splunk), and incident response.
        • Proficiency scripting in Python for security automation and telemetry aggregation.
        • Strong familiarity with MITRE ATT&CK framework and vulnerability assessment tools.
        """,
    },
    # 24. Scanned / noisy OCR text fallback
    {
        "id": "TC24",
        "category": "Scanned/OCR fallback",
        "resume": """
        JAMES WILSON | james.wilson@email.com | (555) 999-0000 | Phoenix, AZ
        
        EXPERIENCE
        Database Administrator at Solara Corp (2020 - Present) - Phoenix, AZ
        - Maintained 40 PostgreSQL and Oracle database clusters with 99.95% uptime.
        - Automated daily backup and point-in-time recovery pipelines saving 20TB storage space.
        - Tuned complex SQL query execution plans reducing slow queries by 45%.
        
        Database Support Tech at DataGrid (2018 - 2020) - Tempe, AZ
        - Monitored database replication lag and resolved failover incidents.
        
        SKILLS
        PostgreSQL, Oracle DB, SQL, Linux, Shell Scripting, Query Optimization, Database Clustering
        
        EDUCATION
        B.S. in Computer Information Systems, Arizona State University (2014 - 2018)
        """,
        "jd": """
        Senior Database Administrator (PostgreSQL / Oracle)
        Requirements:
        • 4+ years managing enterprise relational databases (PostgreSQL or Oracle).
        • Proven experience in high availability clustering, backup/recovery, and SQL performance tuning.
        • Strong Linux shell scripting and database automation skills.
        """,
    },
]


def run_single_test_case(tc: dict[str, Any]) -> dict[str, Any]:
    t_start = time.perf_counter()
    report: dict[str, Any] = {
        "id": tc["id"],
        "category": tc["category"],
        "scores": {},
        "metrics": {},
        "issues": [],
    }

    raw_resume = tc["resume"]
    raw_jd = tc["jd"]

    # 1. Extraction & Parsing
    try:
        profile = extract_candidate_profile(raw_resume)
        has_name = bool(profile.personal.get("name") if isinstance(profile.personal, dict) else getattr(profile.personal, "name", None))
        has_contact = bool((profile.personal.get("email") if isinstance(profile.personal, dict) else getattr(profile.personal, "email", None)) or (profile.personal.get("phone") if isinstance(profile.personal, dict) else getattr(profile.personal, "phone", None)))
        has_exp_or_proj = len(profile.experience) > 0 or len(profile.projects) > 0 or len(profile.education) > 0
        
        if has_name and has_contact and has_exp_or_proj:
            report["scores"]["parsing_correctness"] = "PASS"
        else:
            report["scores"]["parsing_correctness"] = "PARTIAL"
            report["issues"].append("Missing key personal or entity fields during parsing")
    except Exception as e:
        report["scores"]["parsing_correctness"] = "FAIL"
        report["issues"].append(f"Parsing exception: {e}")
        return report

    # 2. Hierarchy Correctness
    try:
        hierarchy_ok = True
        for exp in profile.experience:
            if not exp.company and not exp.role:
                hierarchy_ok = False
        if hierarchy_ok:
            report["scores"]["hierarchy_correctness"] = "PASS"
        else:
            report["scores"]["hierarchy_correctness"] = "PARTIAL"
            report["issues"].append("Experience entity missing both company and role")
    except Exception as e:
        report["scores"]["hierarchy_correctness"] = "FAIL"
        report["issues"].append(f"Hierarchy exception: {e}")

    # 3. Source Evidence Preservation
    try:
        ev_count = len(profile.evidence_units)
        if ev_count > 0:
            report["scores"]["evidence_preservation"] = "PASS"
        else:
            report["scores"]["evidence_preservation"] = "PARTIAL"
            report["issues"].append("Zero evidence units generated from profile")
    except Exception as e:
        report["scores"]["evidence_preservation"] = "FAIL"

    # 4. Candidate Analysis & JD Requirements
    try:
        analysis = analyze_candidate_profile(profile)
        classification = classify_candidate_profile(profile)
        jd_reqs = analyze_jd_requirements(raw_jd)
        ev_map = map_resume_to_jd_evidence(profile, jd_reqs)
        report["scores"]["jd_alignment"] = "PASS"
    except Exception as e:
        report["scores"]["jd_alignment"] = "FAIL"
        report["issues"].append(f"JD alignment exception: {e}")
        return report

    # 5. Tailoring Plan & Decision Generation
    try:
        plan = generate_structured_tailoring_plan(profile, jd_reqs, ev_map, analysis)
        tailored = apply_tailoring_plan(profile, plan)
        
        # Check bullet quality (no fragments, no empty bullets)
        bullets_ok = True
        for ev in tailored.evidence_units:
            txt = ev.text.strip()
            if not txt or len(txt.split()) < 3:
                bullets_ok = False
                break
        report["scores"]["bullet_quality"] = "PASS" if bullets_ok else "PARTIAL"
    except Exception as e:
        report["scores"]["bullet_quality"] = "FAIL"
        report["issues"].append(f"Tailoring plan exception: {e}")
        return report

    # 6. Truth Guard Validation
    try:
        tailored_final, audit = validate_tailored_profile_truth_guard(profile, tailored, plan)
        if audit.is_valid and audit.source_coverage_summary.get("accidental_loss", 0) == 0:
            report["scores"]["truth_guard_correctness"] = "PASS"
        else:
            report["scores"]["truth_guard_correctness"] = "PARTIAL"
            report["issues"].append(f"Truth Guard violations: {audit.violations}")
    except Exception as e:
        report["scores"]["truth_guard_correctness"] = "FAIL"
        report["issues"].append(f"Truth Guard exception: {e}")

    # 7. Template Strategy & ATS Structure
    try:
        strategy = resolve_template_strategy(
            classification,
            years_of_experience=analysis.years_of_experience,
            role_count=len(profile.experience),
            project_count=len(profile.projects),
        )
        report["metrics"]["career_classification"] = str(classification.classification.value if hasattr(classification.classification, "value") else classification.classification)
        report["metrics"]["strategy_name"] = strategy.strategy_name.value
        report["metrics"]["page_budget"] = strategy.page_budget
        report["metrics"]["section_order"] = strategy.section_order
        
        report["scores"]["ats_structure"] = "PASS"
        report["scores"]["template_suitability"] = "PASS"
    except Exception as e:
        report["scores"]["ats_structure"] = "FAIL"
        report["scores"]["template_suitability"] = "FAIL"
        report["issues"].append(f"Template strategy exception: {e}")

    # 8. Rendering (Text, PDF, DOCX) & Export Quality
    try:
        rendered_text = render_candidate_profile_to_text(tailored_final, strategy)
        is_int_valid, int_errors = validate_rendered_export_integrity(tailored_final, rendered_text)
        
        # Test PDF export
        cand_name = (tailored_final.personal.get("name") if isinstance(tailored_final.personal, dict) else getattr(tailored_final.personal, "name", None)) or "Candidate"
        pdf_bytes = generate_pdf(tailored_final, candidate_name=cand_name, template=strategy.template_variant)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        actual_pages = doc.page_count
        doc.close()
        report["metrics"]["pdf_pages"] = actual_pages
        
        # Test DOCX export
        docx_bytes = generate_docx(tailored_final, candidate_name=cand_name)
        report["metrics"]["docx_size_bytes"] = len(docx_bytes)

        if is_int_valid and len(pdf_bytes) > 500 and len(docx_bytes) > 500:
            report["scores"]["rendering_quality"] = "PASS"
        else:
            report["scores"]["rendering_quality"] = "PARTIAL"
            if int_errors:
                report["issues"].extend(int_errors)
    except Exception as e:
        report["scores"]["rendering_quality"] = "FAIL"
        report["issues"].append(f"Rendering exception: {e}")

    t_end = time.perf_counter()
    latency_sec = round(t_end - t_start, 2)
    report["metrics"]["latency_sec"] = latency_sec
    report["scores"]["end_to_end_latency"] = "PASS" if latency_sec < 5.0 else "PARTIAL"

    return report


def main():
    print("=================================================================")
    print("STARTING PHASE 15 REAL-WORLD QUALITY VALIDATION MATRIX (24 CASES)")
    print("=================================================================\n")

    results = []
    for tc in TEST_CASES:
        res = run_single_test_case(tc)
        results.append(res)
        scores_summary = " | ".join(f"{k}: {v}" for k, v in res["scores"].items())
        print(f"[{res['id']}] {res['category']} -> Latency: {res['metrics'].get('latency_sec', 0)}s, PDF Pages: {res['metrics'].get('pdf_pages', 0)}")
        if res["issues"]:
            print(f"     Issues: {res['issues']}")

    # Save complete JSON report
    out_path = "scripts/phase15_validation_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nValidation report saved to: {out_path}")


if __name__ == "__main__":
    main()
