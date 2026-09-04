"""
Test Suite: Phase 11 P0/P1 Remediation Verification
Covers:
- DEF-TRUTH-001 (P0): Whole-token / normalized leadership evidence detection without substring collisions
- DEF-RES-001 (P1): Generalized semantic section detection across alternative/executive headings
"""
import pytest
from app.modules.tailoring.validation import (
    detect_unsupported_action_verbs_and_scope,
    detect_unsupported_metrics,
    detect_fabricated_claims,
)
from app.modules.resume.parsing.structurer import (
    extract_candidate_profile,
    structure_resume_text,
)


# =========================================================================
# DEF-TRUTH-001 (P0) REGRESSION SUITE: LEADERSHIP & SCOPE DETECTION
# =========================================================================

class TestDefTruth001Remediation:
    @pytest.mark.parametrize("technical_word", ["scaled", "handled", "compiled", "bundled", "installed"])
    def test_technical_words_ending_in_led_do_not_satisfy_leadership(self, technical_word: str):
        """
        Original contains technical verbs ending in -led ('scaled', 'handled', 'compiled', 'bundled', 'installed').
        Proposed introduces ungrounded leadership verb 'managed'.
        Must detect leadership claim violation. Substring 'led' inside 'scaled' must not satisfy check.
        """
        original = f"Designed and {technical_word} enterprise order dispatch microservices using Go and Python."
        proposed = "Managed a cross-functional engineering team and boosted throughput by 35%."
        violations = detect_unsupported_action_verbs_and_scope(original, proposed)
        
        assert any("Leadership claim (managed)" in v for v in violations), (
            f"Failed to flag ungrounded leadership escalation when original has '{technical_word}': {violations}"
        )

    def test_legitimate_leadership_evidence_preserved(self):
        """
        Original contains genuine leadership evidence: 'Led a team of 8 engineers...'
        Proposed uses alternative leadership verb: 'Managed a team of 8 engineers...'
        Must NOT falsely flag leadership violation.
        """
        original = "Led a team of 8 backend engineers on cloud platform migration."
        proposed = "Managed a team of 8 backend engineers delivering distributed cloud infrastructure."
        violations = detect_unsupported_action_verbs_and_scope(original, proposed)
        
        leadership_violations = [v for v in violations if "Leadership claim" in v]
        assert len(leadership_violations) == 0, f"Falsely rejected legitimate leadership evidence: {leadership_violations}"

    def test_legitimate_mentoring_evidence_preserved(self):
        """
        Original contains genuine mentoring evidence: 'Mentored 5 engineers...'
        Proposed adapts phrasing: 'Led mentoring initiatives...'
        Must recognize mentoring/leadership evidence family.
        """
        original = "Mentored 5 junior and mid-level engineers on microservice architecture and test automation."
        proposed = "Led mentoring initiatives for 5 engineers on microservice design patterns."
        violations = detect_unsupported_action_verbs_and_scope(original, proposed)
        
        leadership_violations = [v for v in violations if "Leadership claim" in v]
        assert len(leadership_violations) == 0, f"Falsely rejected legitimate mentoring evidence: {leadership_violations}"

    def test_existing_metric_detection_intact(self):
        """
        Verifies unsupported metric detection remains intact alongside verb remediation.
        """
        original = "Reduced latency by 28% and improved uptime."
        proposed = "Reduced latency by 95% and achieved 99.999% availability."
        violations = detect_unsupported_metrics(original, proposed)
        
        assert "95%" in violations or any("95%" in v for v in violations)

    def test_existing_unsupported_technology_detection_intact(self):
        """
        Verifies ungrounded tool/library fabrication detection remains intact.
        """
        original = "Built backend services using Python and FastAPI."
        proposed = "Built backend services in Rust and deployed to Kubernetes."
        violations = detect_fabricated_claims(original, proposed, "", ["Python", "FastAPI"])
        
        assert "rust" in [v.lower() for v in violations] or any("rust" in v.lower() for v in violations)

    def test_legitimate_truthful_rewrite_passes(self):
        """
        Verifies truthful semantic rewrite passes all checks without false positives.
        """
        original = "Designed and scaled order dispatch microservice in Go and Python, reducing checkout latency by 28%."
        proposed = "Engineered and scaled distributed order dispatch microservice in Go and Python, reducing checkout latency by 28%."
        
        verb_violations = detect_unsupported_action_verbs_and_scope(original, proposed)
        metric_violations = detect_unsupported_metrics(original, proposed)
        tool_violations = detect_fabricated_claims(original, proposed, "", ["Python", "Go", "Microservices"])
        
        assert len(verb_violations) == 0
        assert len(metric_violations) == 0
        assert len(tool_violations) == 0


# =========================================================================
# DEF-RES-001 (P1) RESUME REGRESSION MATRIX: GENERALIZED HEADING DETECTION
# =========================================================================

class TestDefRes001ResumeRegressionMatrix:

    def test_a_standard_headings(self):
        """A. Standard headings: EXPERIENCE and EDUCATION."""
        text = """Alex Morgan
alex.morgan@testdomain.io | +1 555 019 2831 | Austin, TX

EXPERIENCE
Apex Systems Inc — Austin, TX
Senior Backend Developer (March 2021 - Present)
- Developed real-time streaming pipelines with Apache Flink handling 40,000 events/sec.

EDUCATION
Metro State University — Austin, TX
B.S. in Computer Science (2016 - 2020) | GPA 3.8 / 4.0
"""
        cand = extract_candidate_profile(text)
        assert cand.name == "Alex Morgan"
        assert len(cand.experience) >= 1
        assert cand.experience[0].company == "Apex Systems Inc"
        assert cand.experience[0].role == "Senior Backend Developer"
        assert len(cand.experience[0].bullets) >= 1
        assert len(cand.education) >= 1
        assert "Metro State" in cand.education[0].institution

    def test_b_alternative_headings(self):
        """B. Alternative headings: CAREER TRAJECTORY and ACADEMIC CREDENTIALS."""
        text = """Elena Vance
elena.v@testconsulting.org | +1 555 382 9102 | Seattle, WA

CAREER TRAJECTORY
Quantum Dynamics Corp — Seattle, WA
Cloud Infrastructure Architect (June 2020 - Present)
- Architected multi-region Kubernetes clusters on AWS with 99.99% service availability.

ACADEMIC CREDENTIALS
Pacific Coast University — Seattle, WA
M.S. in Software Engineering (2018 - 2020) | GPA: 3.9 / 4.0
"""
        cand = extract_candidate_profile(text)
        assert cand.name == "Elena Vance"
        assert len(cand.experience) >= 1
        assert cand.experience[0].company == "Quantum Dynamics Corp"
        assert cand.experience[0].role == "Cloud Infrastructure Architect"
        assert len(cand.education) >= 1
        assert "Pacific Coast" in cand.education[0].institution
        assert cand.education[0].degree == "M.S. in Software Engineering"
        assert "3.9" in str(cand.education[0].gpa)

    def test_c_executive_headings(self):
        """C. Executive headings: CAREER TRAJECTORY & CHRONOLOGY and EDUCATIONAL QUALIFICATIONS."""
        text = """Marcus Sterling
m.sterling@execnetwork.net | +1 555 776 2301 | Chicago, IL

CAREER TRAJECTORY & CHRONOLOGY
Citadel Commerce Ltd — Chicago, IL
Principal Platform Architect (April 2019 - Present)
- Spearheaded global payment gateway modernization reducing transaction failure by 42%.

EDUCATIONAL QUALIFICATIONS
Midwest Institute of Technology — Chicago, IL
B.S. in Electrical and Computer Engineering (2013 - 2017)
"""
        cand = extract_candidate_profile(text)
        assert cand.name == "Marcus Sterling"
        assert len(cand.experience) >= 1
        assert cand.experience[0].company == "Citadel Commerce Ltd"
        assert len(cand.education) >= 1
        assert "Midwest Institute" in cand.education[0].institution

    def test_d_mixed_case_headings(self):
        """D. Mixed-case headings: Career History and Academic Background."""
        text = """Sophia Chen
sophia.chen@techmail.org | +1 555 901 3344 | Boston, MA

Career History
Beacon Analytics — Boston, MA
Data Platform Engineer (January 2022 - Present)
- Engineered scalable ETL pipelines processing 12 TB daily data in Snowflake.

Academic Background
New England University — Boston, MA
B.S. in Data Science & Mathematics (2018 - 2022) | GPA 3.7
"""
        cand = extract_candidate_profile(text)
        assert cand.name == "Sophia Chen"
        assert len(cand.experience) >= 1
        assert cand.experience[0].company == "Beacon Analytics"
        assert len(cand.education) >= 1
        assert "New England" in cand.education[0].institution

    def test_e_headings_with_ampersand(self):
        """E. Headings with '&': WORK EXPERIENCE & HISTORY and EDUCATION & QUALIFICATIONS."""
        text = """David Ross
d.ross@systems.co | +1 555 443 1290 | Denver, CO

WORK EXPERIENCE & HISTORY
Summit Cloud Labs — Denver, CO
Site Reliability Engineer (May 2021 - Present)
- Deployed automated Terraform infrastructure modules managing 400+ virtual cloud instances.

EDUCATION & QUALIFICATIONS
Colorado Polytechnic Institute — Boulder, CO
B.S. in Information Systems (2017 - 2021)
"""
        cand = extract_candidate_profile(text)
        assert cand.name == "David Ross"
        assert len(cand.experience) >= 1
        assert cand.experience[0].company == "Summit Cloud Labs"
        assert len(cand.education) >= 1
        assert "Colorado Polytechnic" in cand.education[0].institution

    def test_f_headings_with_punctuation(self):
        """F. Headings with punctuation: -- PROFESSIONAL JOURNEY -- and ## ACADEMIC CREDENTIALS:."""
        text = """Tara Patel
tara.p@enterprise.io | +1 555 602 8819 | Atlanta, GA

-- PROFESSIONAL JOURNEY --
Omni Retail Systems — Atlanta, GA
Software Development Engineer (August 2020 - Present)
- Built GraphQL microservices for checkout flow supporting 25,000 peak requests/min.

## ACADEMIC CREDENTIALS:
Georgia Institute of Computing — Atlanta, GA
M.S. in Computer Science (2018 - 2020) | GPA: 4.0 / 4.0
"""
        cand = extract_candidate_profile(text)
        assert cand.name == "Tara Patel"
        assert len(cand.experience) >= 1
        assert cand.experience[0].company == "Omni Retail Systems"
        assert len(cand.education) >= 1
        assert "Georgia Institute" in cand.education[0].institution

    def test_g_heading_immediately_after_contact_info(self):
        """G. Headings immediately after contact info / preamble boundary."""
        text = """Liam O'Connor
liam.oc@devmail.com | +1 555 819 0044 | Dublin, Ireland

CAREER TRAJECTORY
Horizon Financial Tech — Dublin, Ireland
Senior Backend Engineer (February 2021 - Present)
- Built distributed payment ledger in Go and PostgreSQL with transactional integrity.

ACADEMIC HISTORY
Trinity College Dublin — Dublin, Ireland
B.A. in Computer Science (2016 - 2020)
"""
        cand = extract_candidate_profile(text)
        assert cand.name == "Liam O'Connor"
        assert len(cand.experience) >= 1
        assert "Horizon Financial Tech" in cand.experience[0].company
        assert len(cand.education) >= 1

    def test_h_multi_role_same_company_progression(self):
        """H. Multi-role at same company: validates career progression roles, dates, and bullets."""
        text = """Rachel Adams
r.adams@techcorp.io | +1 555 771 9922 | New York, NY

PROFESSIONAL EXPERIENCE
Pinnacle Software Inc — New York, NY
Staff Platform Engineer (April 2022 - Present)
- Architected enterprise developer platform reducing CI/CD build duration by 55%.
- Mentored team of 10 engineers and led quarterly architectural reviews.
Senior Software Engineer (January 2020 - March 2022)
- Built high-throughput message ingestion gateway handling 3M messages/hour using Kafka.
Software Engineer (June 2018 - December 2019)
- Designed core REST API services in Python and FastAPI for merchant onboarding.

ACADEMIC CREDENTIALS
Columbia University — New York, NY
B.S. in Computer Engineering (2014 - 2018) | GPA 3.85
"""
        cand = extract_candidate_profile(text)
        assert cand.name == "Rachel Adams"
        assert len(cand.experience) == 1
        ent = cand.experience[0]
        assert ent.company == "Pinnacle Software Inc"
        assert len(ent.progression) == 3
        
        roles = [p.title for p in ent.progression]
        assert "Staff Platform Engineer" in roles
        assert "Senior Software Engineer" in roles
        assert "Software Engineer" in roles
        
        # Verify total bullets across progression
        total_bullets = sum(len(p.bullets) for p in ent.progression)
        assert total_bullets >= 4

    def test_i_multiline_bullets_and_projects(self):
        """I. Multiline bullets and K/L. Project & Skills sections."""
        text = """Kavita Sen
kavita.sen@ai-labs.org | +1 555 312 6677 | San Jose, CA

TECHNICAL SKILLS
Python, PyTorch, Transformers, LangChain, FastAPI, Docker, PostgreSQL, Redis, Kubernetes

CAREER TRAJECTORY
NeuralMatrix AI Labs — San Jose, CA
Machine Learning Engineer (July 2021 - Present)
- Engineered fine-tuning pipeline for 70B parameter open-source LLMs using LoRA
  and DeepSpeed ZeRO-3, decreasing GPU memory footprint by 40% while preserving
  MMLU benchmark evaluation scores.
- Integrated vector embeddings search index with Milvus supporting 5M embeddings.

PROJECTS
MedRAG — Clinical Question Answering System
- Developed end-to-end RAG system utilizing PubMed evidence passages and Mistral-7B
  with hybrid dense-sparse retrieval to synthesize clinical literature queries.

ACADEMIC CREDENTIALS
Stanford University — Stanford, CA
M.S. in Artificial Intelligence (2019 - 2021) | GPA 3.92
"""
        cand = extract_candidate_profile(text)
        assert cand.name == "Kavita Sen"
        assert len(cand.skills) >= 8
        assert "PyTorch" in cand.skills
        assert "Transformers" in cand.skills
        
        assert len(cand.experience) >= 1
        assert "NeuralMatrix" in cand.experience[0].company
        # Verify multiline bullet joined cleanly
        multiline_bullet = cand.experience[0].bullets[0]
        assert "DeepSpeed" in multiline_bullet
        assert "MMLU benchmark" in multiline_bullet
        
        assert len(cand.projects) >= 1
        assert "MedRAG" in cand.projects[0].title
        
        assert len(cand.education) >= 1
        assert "Stanford" in cand.education[0].institution

    def test_ordinary_prose_containing_heading_words_not_classified_as_heading(self):
        """Verify ordinary prose containing terms like 'career trajectory' is not a section heading."""
        text = """Sam Taylor
sam.t@dev.com | +1 555 111 2233 | Austin, TX

SUMMARY
Over my dynamic career trajectory I have managed and delivered distributed systems.
My academic credentials include extensive research in machine learning.

EXPERIENCE
CloudScale — Austin, TX
Backend Engineer (2020 - Present)
- Built scalable web APIs.

EDUCATION
Texas Tech University
B.S. in Computer Science (2016 - 2020)
"""
        sections = structure_resume_text(text)
        # Verify prose was not turned into empty sections
        assert len(sections["experience"]) >= 1
        assert len(sections["education"]) >= 1
        assert "Over my dynamic career trajectory" in sections["summary"]
