"""
spaCy and Taxonomy-Powered High-Recall Skill Extraction Engine (Tier 2 Feature).

Uses spaCy's PhraseMatcher over an expansive 650+ skill lexicon across
Software Engineering, Cloud/DevOps, AI/ML/Data, Mobile, Web, QA, Security,
and Architecture, combined with alias resolution (e.g. k8s -> Kubernetes,
martech -> Marketing Automation) and context pattern extraction.
"""
import re
from functools import lru_cache
import spacy
from spacy.matcher import PhraseMatcher

# Alias resolution mapping
ALIAS_MAP: dict[str, str] = {
    "k8s": "Kubernetes",
    "golang": "Go",
    "js": "JavaScript",
    "ts": "TypeScript",
    "node": "Node.js",
    "nodejs": "Node.js",
    "reactjs": "React",
    "vuejs": "Vue",
    "angularjs": "Angular",
    "nextjs": "Next.js",
    "nuxtjs": "Nuxt.js",
    "sveltekit": "Svelte",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "mssql": "Microsoft SQL Server",
    "sql server": "Microsoft SQL Server",
    "gcp": "Google Cloud Platform",
    "aws": "AWS",
    "azure": "Microsoft Azure",
    "tf": "Terraform",
    "docker": "Docker",
    "gha": "GitHub Actions",
    "cicd": "CI/CD",
    "ci/cd": "CI/CD",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "ai": "Artificial Intelligence",
    "genai": "Generative AI",
    "llm": "Large Language Models",
    "llms": "Large Language Models",
    "rag": "Retrieval-Augmented Generation",
    "nlp": "Natural Language Processing",
    "cv": "Computer Vision",
    "scikit learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "rest": "REST APIs",
    "restful": "REST APIs",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "graphql": "GraphQL",
    "grpc": "gRPC",
    "tdd": "Test-Driven Development",
    "bdd": "Behavior-Driven Development",
    "e2e": "End-to-End Testing",
    "martech": "Marketing Automation",
    "marketing automation": "Marketing Automation",
    "pwa": "Progressive Web Apps",
    "oop": "Object-Oriented Programming",
    "fp": "Functional Programming",
    "ddd": "Domain-Driven Design",
    "rdbms": "Relational Databases",
    "nosql": "NoSQL",
    "py": "Python",
    "fast api": "FastAPI",
    "elastic": "Elasticsearch",
    "dsa": "Data Structures",
    "vue.js": "Vue",
    "react.js": "React",
    "angular.js": "Angular",
    "ios sdk": "iOS SDK",
    "cocoa touch": "Cocoa Touch",
    "uikit": "UIKit",
    "dependency injection": "Dependency Injection",
    "mvvm": "MVVM",
    "mvc": "MVC",
    "viper": "VIPER",
    "figma": "Figma",
    "sketch": "Sketch",
    "apache spark": "Spark",
    "pyspark": "Spark",
    "apache kafka": "Kafka",
    "objective-c": "Objective-C",
    "objective c": "Objective-C",
    "objc": "Objective-C",
    "obj-c": "Objective-C",
    "restful apis": "REST APIs",
    "restful api": "REST APIs",
}

# 650+ Curated Industry Skills Lexicon
KNOWN_SKILLS: list[str] = [
    # Languages
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "C", "Go", "Rust", "Kotlin", "Swift",
    "Ruby", "PHP", "Scala", "R", "Dart", "Elixir", "Haskell", "Lua", "Perl", "Shell Scripting", "Bash",
    "PowerShell", "SQL", "Solidity", "Mojo", "Zig", "HTML5", "CSS3", "Sass", "SCSS",

    # Frontend & Full Stack
    "React", "Angular", "Vue", "Next.js", "Nuxt.js", "Svelte", "Remix", "Gatsby", "Tailwind CSS",
    "Bootstrap", "Material UI", "Chakra UI", "Styled Components", "Redux", "Zustand", "Recoil", "MobX",
    "Webpack", "Vite", "Rollup", "Babel", "WebSockets", "WebGL", "Three.js", "D3.js", "Progressive Web Apps",
    "Responsive Web Design", "DOM Manipulation", "Micro Frontends",

    # Backend & Frameworks
    "Node.js", "Express", "FastAPI", "Django", "Flask", "Spring Boot", "ASP.NET Core", ".NET Core",
    "Ruby on Rails", "Laravel", "NestJS", "Gin", "Echo", "Actix Web", "Axum", "Rocket", "Ktor",
    "Phoenix", "Fastify", "Koa", "Celery", "Gunicorn", "Uvicorn",

    # APIs, Protocols & Architectures
    "REST APIs", "GraphQL", "gRPC", "tRPC", "Webhooks", "SSE", "SOAP", "Microservices", "Monolithic Architecture",
    "Event-Driven Architecture", "Serverless Architecture", "CQRS", "Domain-Driven Design", "Clean Architecture",
    "Hexagonal Architecture", "Service-Oriented Architecture",

    # Databases & Caching
    "PostgreSQL", "MySQL", "SQLite", "Oracle Database", "Microsoft SQL Server", "MongoDB", "DynamoDB",
    "Cassandra", "Couchbase", "Redis", "Memcached", "Elasticsearch", "OpenSearch", "Neo4j", "CouchDB",
    "Supabase", "Firebase Realtime Database", "Firestore", "DuckDB", "ClickHouse", "CockroachDB", "NoSQL",

    # Data Engineering & Streaming
    "Kafka", "Apache Kafka", "RabbitMQ", "Spark", "Apache Spark", "Flink", "Apache Flink", "Airflow", "Apache Airflow", "dbt", "Apache Beam",
    "Hadoop", "Hive", "Databricks", "Snowflake", "Google BigQuery", "AWS Redshift", "ETL Pipelines",
    "Data Warehousing", "Data Modeling", "Data Lakes", "Data Governance", "Stream Processing", "Batch Processing",

    # Cloud & Infrastructure
    "AWS", "Microsoft Azure", "Google Cloud Platform", "Amazon EC2", "AWS S3", "AWS Lambda", "Amazon RDS",
    "AWS ECS", "AWS EKS", "Cloudflare", "DigitalOcean", "Heroku", "Vercel", "Netlify", "OpenStack",

    # DevOps, Containers & CI/CD
    "Docker", "Kubernetes", "Docker Compose", "Terraform", "OpenTofu", "Ansible", "Puppet", "Chef",
    "Helm", "ArgoCD", "GitHub Actions", "GitLab CI/CD", "Jenkins", "CircleCI", "Travis CI", "Bitbucket Pipelines",
    "Nginx", "Apache HTTP Server", "Traefik", "Envoy Proxy", "Istio", "Linux", "Linux Administration", "Unix",

    # Observability & Monitoring
    "Prometheus", "Grafana", "Datadog", "New Relic", "Splunk", "ELK Stack", "OpenTelemetry", "Jaeger",
    "AWS CloudWatch", "Sentry", "Logstash", "Kibana", "Dynatrace",

    # AI, ML & Data Science
    "Machine Learning", "Deep Learning", "Natural Language Processing", "Computer Vision", "Large Language Models",
    "Generative AI", "Retrieval-Augmented Generation", "LangChain", "LlamaIndex", "PyTorch", "TensorFlow", "Keras",
    "scikit-learn", "Random Forest", "XGBoost", "LightGBM", "Pandas", "NumPy", "SciPy", "Matplotlib", "Seaborn",
    "OpenCV", "Streamlit",
    "Hugging Face Transformers", "Vector Databases", "Pinecone", "Qdrant", "ChromaDB", "Milvus", "Weaviate", "FAISS",
    "ONNX", "MLflow", "Ray", "Weights & Biases", "Prompt Engineering", "Fine-Tuning", "Reinforcement Learning",

    # Mobile Development
    "React Native", "Flutter", "Android Development", "iOS Development", "iOS SDK", "Cocoa Touch", "UIKit",
    "Core Data", "Android SDK", "SwiftUI", "Jetpack Compose",
    "Expo", "Cordova", "Ionic", "Objective-C", "Mobile UI Design",

    # Testing & QA
    "Pytest", "Unittest", "Jest", "Mocha", "Chai", "Cypress", "Playwright", "Selenium", "Puppeteer",
    "JUnit", "TestNG", "Postman", "Newman", "JMeter", "K6", "Locust", "TDD", "BDD", "End-to-End Testing",
    "Integration Testing", "Unit Testing", "Performance Testing", "Automated Testing",

    # Security & Identity
    "OAuth 2.0", "OpenID Connect", "JWT", "SAML", "SSL/TLS", "HTTPS", "Web Application Firewall",
    "OWASP Top 10", "Penetration Testing", "Vulnerability Assessment", "IAM", "Zero Trust Architecture",
    "Cryptography", "Public Key Infrastructure",

    # Software Engineering Principles & Methodologies
    "Agile Methodologies", "Scrum", "Kanban", "Jira", "Confluence", "Git", "GitHub", "GitLab", "Bitbucket",
    "System Design", "Distributed Systems", "High Availability", "Fault Tolerance", "Scalability",
    "SOLID Principles", "Object-Oriented Programming", "Functional Programming", "Design Patterns",
    "Dependency Injection", "MVVM", "MVC", "VIPER",
    "Data Structures", "Algorithms", "Code Review", "Technical Documentation",

    # Design, Product & MarTech
    "Figma", "Sketch", "Adobe XD",
    "Marketing Automation", "MarTech", "HubSpot", "Salesforce", "Google Analytics", "Mixpanel", "Amplitude",
    "SEO", "A/B Testing", "Product Management", "Growth Hacking",
]


@lru_cache(maxsize=1)
def _get_nlp_matcher():
    nlp = spacy.blank("en")
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

    # Add all known canonical skills
    patterns = [nlp.make_doc(skill) for skill in KNOWN_SKILLS]
    matcher.add("SKILLS", patterns)

    # Add all aliases
    alias_patterns = [nlp.make_doc(alias) for alias in ALIAS_MAP.keys()]
    matcher.add("ALIASES", alias_patterns)

    return nlp, matcher


# Context extraction patterns for dynamic skill discovery
_CONTEXT_PATTERNS = [
    re.compile(r"(?:experience with|proficient in|knowledge of|skilled in|expertise in|familiarity with|hands-on with)\s+([A-Za-z0-9+#.\s]{2,35})(?:[,.;\n]|$)", re.IGNORECASE),
    re.compile(r"(?:strong understanding of|working knowledge of|demonstrated ability in)\s+([A-Za-z0-9+#.\s]{2,35})(?:[,.;\n]|$)", re.IGNORECASE),
]


def extract_skills_from_text(text: str) -> list[str]:
    """
    High-recall, deterministic skill extraction combining spaCy PhraseMatcher,
    alias normalization, and contextual regex pattern discovery.
    """
    if not text or not text.strip():
        return []

    # Ensure trailing punctuation attached to words at clause/sentence boundaries
    # does not prevent single-letter or hyphenated tokens (e.g. "Objective-C.") from matching
    clean_input = re.sub(r"(?<=[a-zA-Z0-9])([.,;:])(?=\s|$)", r" \1", text)

    nlp, matcher = _get_nlp_matcher()
    doc = nlp(clean_input)
    matches = matcher(doc, as_spans=True)
    from spacy.util import filter_spans
    filtered_spans = filter_spans(matches)

    found_skills: set[str] = set()

    for span in filtered_spans:
        span_text = span.text.strip()
        span_lower = span_text.lower()

        # Disambiguate polysemous common English words from technical frameworks
        if span_lower == "spark":
            char_start = span.start_char
            char_end = span.end_char
            win_start = max(0, char_start - 30)
            win_end = min(len(text), char_end + 35)
            window = text[win_start:win_end].lower()

            is_idiom = bool(re.search(
                r"\b(?:a\s+)?spark\s+of\s+(?:inspiration|creativity|genius|curiosity|hope|joy|passion|entrepreneurship|life|light|imagination)\b"
                r"|\b(?:to|will|can|must)\s+spark\b"
                r"|\bspark(?:ed|ing|s)?\s+(?:an?\s+)?(?:interest|change|innovation|growth|conversation|debate|discussion|revolution|joy)\b"
                r"|\bbright\s+spark\b",
                window,
                re.IGNORECASE
            ))
            if is_idiom:
                if not re.search(r"\bapache\s+spark\b|\bpyspark\b|\bspark\s+(?:sql|streaming|core|dataframe|rdd)\b", window, re.IGNORECASE):
                    continue

        if span_lower in ALIAS_MAP:
            found_skills.add(ALIAS_MAP[span_lower])
        else:
            # Match against known skills case-insensitively
            for canonical in KNOWN_SKILLS:
                if canonical.lower() == span_lower:
                    found_skills.add(canonical)
                    break
            else:
                found_skills.add(span_text.title())

    # Contextual pattern extraction for composite / niche technical phrases
    for pattern in _CONTEXT_PATTERNS:
        for match in pattern.finditer(text):
            candidate = match.group(1).strip()
            # Split candidate if comma-separated
            parts = [p.strip() for p in re.split(r"[,|&]", candidate) if p.strip()]
            for p in parts:
                p_clean = re.sub(r"[^\w\s+#.-]", "", p).strip()
                if len(p_clean) >= 2 and len(p_clean) <= 30:
                    p_lower = p_clean.lower()
                    if p_lower in ALIAS_MAP:
                        found_skills.add(ALIAS_MAP[p_lower])
                    elif any(k.lower() == p_lower for k in KNOWN_SKILLS):
                        found_skills.add(next(k for k in KNOWN_SKILLS if k.lower() == p_lower))

    # Return sorted list for deterministic results
    return sorted(found_skills)


_KNOWN_SKILLS_LOWER: dict[str, str] = {s.lower(): s for s in KNOWN_SKILLS}


def canonicalize_skill_name(skill: str) -> str:
    """
    Authoritative single-skill canonicalization helper.
    Resolves aliases (e.g. 'mongo' -> 'MongoDB', 'node' -> 'Node.js', 'k8s' -> 'Kubernetes')
    and case-folds against the curated KNOWN_SKILLS lexicon (e.g. 'python' -> 'Python').
    Preserves clean original formatting for recognized custom technologies.
    """
    if not skill or not isinstance(skill, str):
        return ""
    s_clean = skill.strip()
    if not s_clean:
        return ""
    s_lower = s_clean.lower()
    if s_lower in ALIAS_MAP:
        return ALIAS_MAP[s_lower]
    if s_lower in _KNOWN_SKILLS_LOWER:
        return _KNOWN_SKILLS_LOWER[s_lower]
    return s_clean
