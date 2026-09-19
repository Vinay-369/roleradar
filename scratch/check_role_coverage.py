import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import urllib.request
import json

DOMAINS_AND_ROLES = {
    "Software Engineering": ["Full Stack Developer", "Backend Engineer", "Frontend Developer"],
    "Data": ["Data Analyst", "Data Engineer", "Business Intelligence Analyst"],
    "AI/ML": ["Machine Learning Engineer", "AI Engineer", "Data Scientist"],
    "Cloud/DevOps": ["DevOps Engineer", "Cloud Architect", "Site Reliability Engineer"],
    "Cybersecurity": ["Security Analyst", "Cybersecurity Engineer"],
    "QA": ["QA Engineer", "Automation Test Engineer"],
    "Mobile": ["Android Developer", "iOS Developer"],
    "Product": ["Product Manager", "Associate Product Manager"],
    "Design": ["UI/UX Designer", "Product Designer"],
    "HR": ["Technical Recruiter", "HR Specialist"],
    "Sales": ["Business Development Representative", "Account Executive"],
    "Marketing": ["Digital Marketing Specialist", "Growth Marketer"],
    "Finance": ["Financial Analyst"],
    "Operations": ["Operations Manager"]
}

async def main():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["roleradar"]
    
    print(f"{'Domain':<22} | {'Representative Role':<32} | {'Taxonomy Match':<16} | {'Inventory Count'}")
    print("-" * 88)
    
    for domain, roles in DOMAINS_AND_ROLES.items():
        for role in roles:
            # Query learning/roadmap
            url = f"http://127.0.0.1:8000/api/learning/roadmap?role={urllib.parse.quote(role)}"
            try:
                with urllib.request.urlopen(url) as resp:
                    rm = json.loads(resp.read().decode())
                    matched_role = rm.get("role", "Unknown")
                    confidence = rm.get("confidence", "HIGH")
            except Exception as e:
                matched_role = f"ERR: {e}"
                confidence = "FAILED"
                
            # Count opportunities in DB for this role title or keyword
            kw = role.split()[0]
            cnt = await db["jobs"].count_documents({
                "verification_status": "VERIFIED_ACTIVE",
                "title": {"$regex": kw, "$options": "i"}
            })
            
            print(f"{domain:<22} | {role:<32} | {confidence:<16} | {cnt} matching active")

if __name__ == "__main__":
    import urllib.parse
    asyncio.run(main())
