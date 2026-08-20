"""
Deterministic Mock AI provider for offline evaluation, unit testing, and benchmarking.
"""
import json
import re


class MockAIProvider:
    def __init__(self, settings=None):
        self.model_name = "mock-eval-model"

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> str:
        # Check if prompting for resume tailoring
        if "resume tailoring" in system_prompt.lower() or "PROPOSE TAILORING" in user_prompt.upper() or "MASTER RESUME" in user_prompt:
            # Extract sample skills from user prompt
            skills_match = re.search(r'"skills":\s*\[(.*?)\]', user_prompt)
            skills = [s.strip().strip('"') for s in skills_match.group(1).split(",")] if skills_match else ["Python", "FastAPI"]
            primary_skill = skills[0] if skills else "Python"
            secondary_skill = skills[1] if len(skills) > 1 else "REST APIs"

            changes = [
                {
                    "change_id": "chg_01",
                    "original": f"Developed backend services using {primary_skill}.",
                    "proposed": f"Architected high-throughput microservices using {primary_skill} and optimized database queries, reducing response times by 35%.",
                    "reason": f"Emphasizes scalability and technical leadership aligned with job description requirements for {primary_skill}.",
                    "source_evidence": f"Candidate master resume evidences strong hands-on project experience with {primary_skill}.",
                    "confidence": 0.95,
                    "status": "PENDING",
                },
                {
                    "change_id": "chg_02",
                    "original": f"Collaborated on {secondary_skill} integration.",
                    "proposed": f"Engineered reliable {secondary_skill} integration with comprehensive test coverage and automated CI/CD workflows.",
                    "reason": f"Quantifies engineering rigor and matches JD expectations for {secondary_skill}.",
                    "source_evidence": f"Master resume experience section explicitly cites {secondary_skill} development.",
                    "confidence": 0.90,
                    "status": "PENDING",
                },
            ]
            return json.dumps({"changes": changes})

        # Check if prompting for interview questions
        elif "interview" in system_prompt.lower() or "interview questions" in user_prompt.lower():
            role_match = re.search(r'JOB TITLE:\s*(.*?)\n', user_prompt)
            role = role_match.group(1).strip() if role_match else "Software Engineer"

            questions = [
                {
                    "question": f"Can you explain your experience architecting scalable systems for a {role} position?",
                    "category": "technical",
                    "star_hint": "Detail the architecture, concurrency challenges, and measurable performance outcomes.",
                },
                {
                    "question": f"Describe a challenging bug or production outage you investigated in a previous project.",
                    "category": "project_defense",
                    "star_hint": "Walk through your debugging strategy, root cause analysis, and long-term prevention.",
                },
                {
                    "question": "How do you prioritize technical debt against rapid product feature delivery?",
                    "category": "behavioral",
                    "star_hint": "Share a concrete example of trade-offs made with product managers and team leads.",
                },
                {
                    "question": f"What design patterns and testing strategies do you leverage when building for {role}?",
                    "category": "role_specific",
                    "star_hint": "Highlight SOLID principles, unit/integration test coverage, and automated pipelines.",
                },
                {
                    "question": "Tell me about a time you had to learn a new framework or technology quickly under deadline.",
                    "category": "behavioral",
                    "star_hint": "Focus on your learning process, hands-on prototyping, and successful delivery.",
                },
            ]
            return json.dumps({"questions": questions})

        # Default fallback
        return json.dumps({
            "response": "Understood. I am ready to assist with your career growth and application strategy."
        })
