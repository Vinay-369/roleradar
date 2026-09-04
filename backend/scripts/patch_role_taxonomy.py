"""
Generates the fully expanded, hardened role_taxonomy.py.
Adds:
- RoleSpecialization dataclass
- 38 new canonical profiles across Healthcare, Pharma, Engineering, Construction,
  Legal, Education, Research, Media, Hospitality, Operations, HR, Finance, and Sales
- Registered ROLE_SPECIALIZATIONS
- Aliases for Category A roles
- Controlled Composition step in resolve_role
"""
import sys

NEW_CANONICAL_PROFILES_CODE = '''
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
'''


SPECIALIZATIONS_CODE = '''

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
'''

def patch_file():
    path = r"c:\VINAY\roleradar\backend\app\modules\learning\role_taxonomy.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update aliases on existing roles
    # ai_researcher:
    old_ai_res = 'aliases=["Research Scientist (AI)", "Machine Learning Scientist"],'
    new_ai_res = 'aliases=["Research Scientist (AI)", "Machine Learning Scientist", "ML Researcher", "Machine Learning Researcher"],'
    assert old_ai_res in content, "ai_researcher aliases not found"
    content = content.replace(old_ai_res, new_ai_res)

    # video_editor:
    old_ve = 'aliases=["Motion Picture Editor", "Video Producer"],'
    new_ve = 'aliases=["Motion Picture Editor", "Video Producer", "Film Editor"],'
    assert old_ve in content, "video_editor aliases not found"
    content = content.replace(old_ve, new_ve)

    # teacher:
    old_t = 'aliases=["Educator", "High School Teacher", "Elementary Teacher", "Instructor"],'
    new_t = 'aliases=["Educator", "High School Teacher", "Elementary Teacher", "Instructor", "School Teacher"],'
    assert old_t in content, "teacher aliases not found"
    content = content.replace(old_t, new_t)

    # civil_engineer:
    old_ce = 'aliases=["Structural Engineer", "Site Civil Engineer"],'
    new_ce = 'aliases=["Structural Engineer", "Site Civil Engineer", "Site Engineer"],'
    assert old_ce in content, "civil_engineer aliases not found"
    content = content.replace(old_ce, new_ce)

    # accountant:
    old_acc = 'aliases=["Staff Accountant", "Senior Accountant", "Corporate Accountant"],'
    new_acc = 'aliases=["Staff Accountant", "Senior Accountant", "Corporate Accountant", "Tax Analyst"],'
    assert old_acc in content, "accountant aliases not found"
    content = content.replace(old_acc, new_acc)

    # 2. Insert new canonical profiles before the closing brace of ROLE_TAXONOMY
    closing_bracket = '\n}\n\n\n# Precompute lookup maps'
    assert closing_bracket in content, "ROLE_TAXONOMY closing bracket not found"
    content = content.replace(closing_bracket, '\n' + NEW_CANONICAL_PROFILES_CODE + '\n}\n\n\n# Precompute lookup maps')

    # 3. Add RoleSpecialization dataclass, registry, and composition helper
    # We can place SPECIALIZATIONS_CODE right before `def _normalize_role_input`
    norm_def = 'def _normalize_role_input(raw: str) -> str:'
    assert norm_def in content, "_normalize_role_input not found"
    content = content.replace(norm_def, SPECIALIZATIONS_CODE + '\n\n' + norm_def)

    # 4. Enhance resolve_role with Controlled Specialization step
    old_resolve_body = '''    # 5. Specialized Niche / Unknown Roles
    # Examples: "Marine Robotics Engineer", "Spacecraft Propulsion Specialist", "Quantum Cryogenics Technician"
    # Never guess or hallucinate generic tech roles. Return LOW confidence.
    return None, "LOW", "UNCONFIRMED_ROLE_IDENTITY"'''

    new_resolve_body = '''    # 5. Controlled Specialization Matching
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
    return None, "LOW", "UNCONFIRMED_ROLE_IDENTITY"'''

    assert old_resolve_body in content, "old resolve_role end not found"
    content = content.replace(old_resolve_body, new_resolve_body)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Successfully patched role_taxonomy.py!")

if __name__ == "__main__":
    patch_file()

