"""
Curated Discipline-Specific Top 20 Interview Question Banks for RoleRadar.
Provides comprehensive coverage across Technical, Managerial, and HR rounds
for 6 core software engineering disciplines.
"""
from typing import Literal

ROLE_QUESTION_BANKS: dict[str, list[dict]] = {
    "full_stack": [
        {
            "category": "technical",
            "question": "How do you architect an end-to-end full stack web application from frontend client to database?",
            "star_hint": "Cover SPA/SSR frontend (React/Next.js), reverse proxy/API Gateway, REST/GraphQL backend, DB layer, and caching.",
            "strategy": "1. Client layer (React/TypeScript) -> 2. Gateway/Nginx -> 3. Node/Python API -> 4. PostgreSQL & Redis Cache.",
            "sample_answer": "I architect full stack apps in layers: a React/Next.js frontend communicating over HTTPS to an API Gateway. The backend service validates payloads using schemas (Zod/Pydantic), executes business logic, queries PostgreSQL with connection pooling, and leverages Redis for sub-millisecond session and reference caching.",
            "pitfalls": "Tightly coupling frontend components directly to database queries without an API abstraction layer.",
        },
        {
            "category": "technical",
            "question": "What is the difference between Server-Side Rendering (SSR), Client-Side Rendering (CSR), and Static Site Generation (SSG)?",
            "star_hint": "Compare SEO, Time to First Byte (TTFB), build times, and user interaction latency.",
            "strategy": "Define each rendering model -> Discuss trade-offs -> Match to realistic use cases (e-commerce vs dashboard).",
            "sample_answer": "CSR renders HTML dynamically in the browser via JavaScript, ideal for private interactive dashboards. SSR generates HTML on every server request, providing fast TTFB and dynamic SEO for live feeds. SSG pre-renders HTML pages at build time, yielding the highest CDN performance for marketing and documentation pages.",
            "pitfalls": "Choosing SSR for internal dashboards where SEO is irrelevant and server load is amplified.",
        },
        {
            "category": "technical",
            "question": "How do you prevent CORS issues and manage cross-origin authentication securely?",
            "star_hint": "Cover Access-Control headers, preflight requests, and httpOnly SameSite cookie attributes.",
            "strategy": "Explain browser same-origin policy -> OPTIONS preflight handling -> Whitelisting trusted origin domains.",
            "sample_answer": "I configure CORS middleware to explicitly whitelist our production frontend origins, avoid wildcard '*' headers, and allow credentials. For auth, I use httpOnly, Secure, SameSite=Strict cookies to protect refresh tokens from XSS theft while keeping access tokens in memory.",
            "pitfalls": "Using wildcard origins when sending authenticated credentials.",
        },
        {
            "category": "technical",
            "question": "How do you optimize full stack database queries to prevent the N+1 problem?",
            "star_hint": "Explain eager loading (JOINs / select_related) versus lazy loading in ORMs.",
            "strategy": "Identify N+1 in ORM loop -> Profile SQL queries -> Apply eager fetching or composite joins.",
            "sample_answer": "The N+1 problem occurs when an application executes 1 query for parent records and N separate queries for child rows. In full stack apps, I diagnose this with SQL profilers and solve it by applying eager joins (select_related or include) in ORMs, reducing database roundtrips from N+1 to 1.",
            "pitfalls": "Applying caching before fixing the underlying inefficient database query.",
        },
        {
            "category": "technical",
            "question": "How do you handle real-time bi-directional events vs uni-directional streaming in a full stack app?",
            "star_hint": "Compare WebSockets (Socket.io) vs Server-Sent Events (SSE) and HTTP long-polling.",
            "strategy": "Explain bi-directional chat/gaming (WebSockets) vs server-to-client notifications/AI streaming (SSE).",
            "sample_answer": "For bi-directional features like live collaborative editing or chats, I use WebSockets. For uni-directional server-to-client updates like live progress feeds, financial tickers, or LLM token streaming, I prefer Server-Sent Events (SSE) because it runs seamlessly over standard HTTP with automatic reconnection.",
            "pitfalls": "Using heavy WebSockets when the data flow is purely one-way.",
        },
        {
            "category": "managerial",
            "question": "How do you prioritize technical debt versus urgent product feature deadlines when leading a full-stack sprint?",
            "star_hint": "Propose the 20% tech debt sprint allocation rule, measuring risk via error budgets and user-facing latency.",
            "strategy": "Frame tech debt in terms of developer velocity, customer churn risk, and operational costs.",
            "sample_answer": "I maintain a dedicated technical debt backlog quantified by engineering friction and system reliability risk. I advocate allocating 15-20% of every sprint to paying down debt, prioritizing items that reduce customer-facing latency or unblock upcoming product initiatives.",
            "pitfalls": "Treating tech debt as purely developer preference rather than business risk.",
        },
        {
            "category": "managerial",
            "question": "How do you ensure high code quality across both frontend and backend repositories?",
            "star_hint": "Describe CI pipelines, automated linting, unit/integration test coverage, and strict PR review standards.",
            "strategy": "1. Automated CI gates (ESLint, Prettier, Ruff) -> 2. Testing pyramid -> 3. Mandatory 2-reviewer PR approvals.",
            "sample_answer": "I institute automated pre-commit hooks and GitHub Actions workflows that run linters, type checks, and unit tests before any PR can be merged. I also establish a standardized PR checklist requiring clear description of changes, test coverage, and staging verification.",
            "pitfalls": "Relying entirely on manual peer reviews without automated CI test gates.",
        },
        {
            "category": "hr",
            "question": "Tell me about a time you made a significant mistake or an API broke in testing. What happened and what did you learn?",
            "star_hint": "Take 100% accountability, explain the root cause, show how you resolved it, and detail permanent process improvements.",
            "strategy": "1. Honest situation -> 2. Owned mistake -> 3. Fast remediation -> 4. Long-term systemic safeguard created.",
            "sample_answer": "Early on, an unhandled API edge case caused an unexpected error in testing. Rather than finding a quick patch, I conducted a root-cause review, added strict schema validation, and instituted automated regression tests. That experience taught me the critical value of proactive boundary testing.",
            "pitfalls": "Claiming you've never failed, or blaming teammates, management, or external clients.",
        },
        {
            "category": "hr",
            "question": "Why are you interested in this Full Stack position and how does it fit your career growth goals?",
            "star_hint": "Connect full-stack architectural ownership, continuous deployment, and mentoring junior engineers.",
            "strategy": "Highlight ownership of entire feature lifecycles from DB schema design to responsive UI polish.",
            "sample_answer": "I thrive on building complete product experiences end-to-end, taking full ownership from database optimization to responsive frontend components. This role gives me the opportunity to architect high-impact features and collaborate closely across cross-functional teams.",
            "pitfalls": "Giving a generic answer without mentioning technical alignment.",
        },
    ],
    "backend": [
        {
            "category": "technical",
            "question": "How do you design a high-throughput backend architecture handling 50,000 requests per second?",
            "star_hint": "Discuss load balancing (NGINX/HAProxy), stateless services, Redis caching, DB read replicas, and horizontal scaling.",
            "strategy": "1. Traffic routing (DNS + Load Balancers) -> 2. Stateless API pods -> 3. Redis caching -> 4. PostgreSQL Primary/Replica + Sharding.",
            "sample_answer": "I design high-throughput backend systems using stateless application containers behind an NGINX load balancer. Read-heavy traffic (typically 80%) is intercepted by Redis caching. Persistent data writes go to a Primary PostgreSQL database, with read traffic distributed across read replicas and database connection pooling (PgBouncer) to prevent connection saturation.",
            "pitfalls": "Keeping stateful sessions on application servers or allowing all read requests to hit the primary database.",
        },
        {
            "category": "technical",
            "question": "How do you diagnose and resolve slow database queries in PostgreSQL or MySQL?",
            "star_hint": "Mention EXPLAIN (ANALYZE, BUFFERS), sequential scans vs index scans, composite indexes, and lock contention.",
            "strategy": "1. Profiling (slow query log / pg_stat_statements) -> 2. Analyze query execution plan -> 3. Apply targeted index or schema fix.",
            "sample_answer": "I identify slow queries using `pg_stat_statements` and execute `EXPLAIN (ANALYZE, BUFFERS)` to inspect the execution plan. If I observe sequential scans or high buffer reads, I add composite B-Tree indexes matching the WHERE and ORDER BY clauses, and optimize JOIN conditions to eliminate nested loop scans.",
            "pitfalls": "Adding random indexes without inspecting the query execution plan.",
        },
        {
            "category": "technical",
            "question": "How do you implement distributed locking in microservices using Redis (Redlock)?",
            "star_hint": "Discuss SET NX PX, lock expiration TTL, unique lock tokens, and safe release via Lua scripts.",
            "strategy": "1. Acquire lock with SET key token NX PX 5000 -> 2. Execute critical section -> 3. Release lock atomically via Lua script checking token.",
            "sample_answer": "I acquire distributed locks using Redis `SET resource_id token NX PX 5000` where the token is a unique UUID. The NX flag ensures only one process acquires the lock, and the TTL prevents deadlocks if a server crashes. To release, I execute an atomic Lua script verifying that the current token matches before deleting the key.",
            "pitfalls": "Releasing a lock with a simple `DEL` without verifying the token, which can accidentally release another process's lock if execution exceeded TTL.",
        },
        {
            "category": "technical",
            "question": "What is the Saga pattern in distributed microservices, and how does it compare to 2-Phase Commit (2PC)?",
            "star_hint": "Compare blocking 2PC vs non-blocking Saga (Choreography vs Orchestration) with compensating transactions.",
            "strategy": "Explain why 2PC causes bottlenecks in microservices -> Explain Saga workflow -> Detail compensating rollback actions.",
            "sample_answer": "Two-Phase Commit (2PC) blocks all services and databases until consensus is reached, creating high latency. The Saga pattern manages distributed transactions as a sequence of local transactions. If a step fails (e.g. payment decline), the Saga orchestrator triggers compensating transactions in reverse to safely revert prior database changes.",
            "pitfalls": "Assuming distributed transactions can be rolled back with standard SQL rollback statements.",
        },
        {
            "category": "managerial",
            "question": "Walk me through how you handled a high-severity production outage or latency spike under pressure.",
            "star_hint": "Use STAR: Situation (outage), Task (restore service), Action (rollback/circuit breaking), Result (post-mortem).",
            "strategy": "Emphasize MTTR (Mean Time to Recovery) first via rollback/traffic redirection before deep root-cause debugging.",
            "sample_answer": "During a sudden database CPU spike to 98%, I immediately routed traffic to read replicas and rolled back the latest migration, reducing latency to normal within 4 minutes. Following stabilization, I conducted a post-mortem identifying a missing index and instituted query plan linting in CI.",
            "pitfalls": "Attempting live patching directly on production DB rather than stabilizing first.",
        },
        {
            "category": "hr",
            "question": "Tell me about a time when you received constructive feedback on your code or system design. How did you respond?",
            "star_hint": "Demonstrate receptiveness, ego detachment, and applying the lesson to elevate engineering standards.",
            "strategy": "Describe a specific code review critique (e.g. error handling or boundary tests) and how you adopted it.",
            "sample_answer": "During a code review, a senior engineer noted that my asynchronous task pipeline lacked exponential backoff on third-party API retries. I welcomed the feedback, researched retry algorithms, and standardized it across the team.",
            "pitfalls": "Defensiveness or blaming legacy code.",
        },
    ],
    "frontend": [
        {
            "category": "technical",
            "question": "How do you optimize Core Web Vitals (LCP, INP, CLS) in a modern React Single Page Application?",
            "star_hint": "Explain route-based code splitting (React.lazy), image srcset/WebP compression, layout dimensions, and memoization.",
            "strategy": "1. LCP (Preload hero assets, font-display: swap) -> 2. INP (useTransition, web workers) -> 3. CLS (explicit aspect ratios).",
            "sample_answer": "I optimize LCP by preloading key assets, using WebP/AVIF formats, and dynamically splitting routes with React.lazy. For CLS, I enforce fixed aspect ratio containers on dynamic cards and skeleton loaders. For INP, I offload expensive calculations using Web Workers and React 18 `useTransition`.",
            "pitfalls": "Focusing only on bundle size while ignoring layout shift and main thread blocking tasks.",
        },
        {
            "category": "technical",
            "question": "How does the React 18 Fiber reconciler and concurrent rendering architecture work under the hood?",
            "star_hint": "Cover Fiber node tree, render vs commit phases, interruptible work, useDeferredValue, and automatic batching.",
            "strategy": "Explain Fiber as a linked list tree -> Render phase (time-sliced/interruptible) -> Commit phase (synchronous DOM mutations).",
            "sample_answer": "Fiber represents virtual DOM components as a linked-list tree. Unlike legacy synchronous rendering, Fiber splits work into small priority units that can be paused, aborted, or resumed during the render phase. Once the priority queue finishes, the commit phase applies all DOM changes in a single synchronous pass.",
            "pitfalls": "Confusing the Virtual DOM diff with the physical DOM update.",
        },
        {
            "category": "technical",
            "question": "How do you architect a reusable, accessible design system component library in TypeScript & Tailwind?",
            "star_hint": "Discuss WAI-ARIA standards, compound component patterns, keyboard navigation (tabindex/focus trap), and design tokens.",
            "strategy": "1. Headless primitives (Radix/Aria) -> 2. Tokenized styling (Tailwind/CSS variables) -> 3. Compound component APIs.",
            "sample_answer": "I build component libraries on top of unstyled accessible primitives (like Radix UI), ensuring full keyboard navigation and screen-reader ARIA compliance. I expose flexible compound component APIs (e.g. `<Modal.Header>`, `<Modal.Body>`) and standardize color palettes and typography via semantic CSS design tokens.",
            "pitfalls": "Writing custom modal dialogs that lack focus trapping or Escape key listeners.",
        },
        {
            "category": "managerial",
            "question": "How do you balance adding new UI features with maintaining 60 FPS frontend performance?",
            "star_hint": "Mention bundle size budgets, Lighthouse CI auditing, avoiding unnecessary re-renders, and profiling.",
            "strategy": "Establish Lighthouse budgets in CI -> Profile component renders using React DevTools Profiler.",
            "sample_answer": "I establish performance budgets in CI where PRs that increase JavaScript bundle size by more than 5% require review. I regularly profile heavy component trees to prevent unnecessary parent-child cascading re-renders via `React.memo` and localized state management.",
            "pitfalls": "Treating UI performance as a post-launch cleanup task rather than a sprint requirement.",
        },
        {
            "category": "hr",
            "question": "How do you approach working with UI/UX designers when technical feasibility or time constraints conflict?",
            "star_hint": "Highlight constructive collaboration, proposing phased implementation, and finding elegant ergonomic compromises.",
            "strategy": "1. Appreciate design intent -> 2. Explain technical latency/feasibility bottlenecks -> 3. Propose Phase 1 MVP + Phase 2 polish.",
            "sample_answer": "I maintain an open, proactive dialog with designers. When a complex animation would delay sprint delivery, I schedule a quick walkthrough to understand the user experience goal, and propose a lightweight, performant CSS transition that achieves 90% of the visual impact in half the build time.",
            "pitfalls": "Dismissing designs as 'impossible' without proposing actionable alternatives.",
        },
    ],
    "data_science": [
        {
            "category": "technical",
            "question": "How do you handle severe class imbalance in machine learning classification pipelines?",
            "star_hint": "Discuss SMOTE, focal loss, class weights, precision-recall AUC instead of accuracy, and stratified sampling.",
            "strategy": "1. Evaluation metrics (PR-AUC / F1) -> 2. Resampling (SMOTE/Tomek links) -> 3. Algorithmic adjustments (Class weights/Focal loss).",
            "sample_answer": "In imbalanced datasets (e.g., 99:1 fraud detection), accuracy is misleading. I evaluate models using Precision-Recall AUC and Macro F1 score. During training, I apply stratified k-fold cross-validation, adjust class weights in the loss function, and use SMOTE oversampling on the training split only to avoid data leakage.",
            "pitfalls": "Applying SMOTE before splitting into train/validation sets, causing severe data leakage.",
        },
        {
            "category": "technical",
            "question": "Explain the architecture of Retrieval-Augmented Generation (RAG) and how you minimize hallucinations in production LLMs.",
            "star_hint": "Cover chunking strategies, dense embeddings, vector indexing (HNSW/IVFFlat), re-ranking (Cross-Encoders), and prompt grounding.",
            "strategy": "1. Ingestion (semantic chunking + embeddings) -> 2. Hybrid search (BM25 + Vector) -> 3. Cross-encoder re-ranking -> 4. Grounded prompting.",
            "sample_answer": "A production RAG pipeline uses semantic chunking with metadata tags, indexed in vector databases using HNSW. At query time, I execute hybrid search combining BM25 keyword matching with dense vector similarity, pass top candidates to a Cohere/Cross-Encoder re-ranker, and ground the LLM with strict instructions to cite retrieved evidence.",
            "pitfalls": "Using huge static chunk sizes that dilute vector relevance or failing to ground system prompts.",
        },
        {
            "category": "technical",
            "question": "How do you detect and mitigate feature drift and concept drift in production ML models?",
            "star_hint": "Discuss Kolmogorov-Smirnov test, Population Stability Index (PSI), automated retraining triggers, and Evidently AI/Whylabs.",
            "strategy": "1. Feature drift (input distribution shifts) -> 2. Concept drift (input-to-target relationship shifts) -> 3. Automated monitoring & retraining.",
            "sample_answer": "I monitor incoming feature distributions against training baselines using the Kolmogorov-Smirnov test and PSI. When drift exceeds statistical thresholds, automated alerts trigger data profiling and retrain models on sliding time windows, with shadow deployments to validate accuracy before promoting to live traffic.",
            "pitfalls": "Assuming a trained model maintains its accuracy indefinitely without monitoring distribution shifts.",
        },
        {
            "category": "managerial",
            "question": "How do you translate ambiguous business problems into rigorous, quantifiable machine learning problem statements?",
            "star_hint": "Connect business ROI (e.g. churn reduction) to proxy ML metrics (e.g. Top-K Recall), defining baseline heuristics first.",
            "strategy": "1. Define business objective -> 2. Establish heuristic baseline -> 3. Select ML metric that directly impacts the business KPI.",
            "sample_answer": "I start by understanding the economic cost of false positives versus false negatives. I build a simple rule-based heuristic baseline first, then formulate the ML objective—such as optimizing Recall@K for customer retention—ensuring the team can measure direct ROI improvements over the baseline.",
            "pitfalls": "Jumping straight into complex deep learning models before establishing a simple baseline.",
        },
        {
            "category": "hr",
            "question": "Tell me about a data science or ML project where the model did not perform as expected. How did you diagnose it?",
            "star_hint": "Demonstrate systematic debugging: feature importance, data quality checks, residual analysis, and iterative improvement.",
            "strategy": "Situation -> Model underperformance -> Systematic diagnosis -> Resolution and key takeaway.",
            "sample_answer": "In a recommendation model, offline validation accuracy was high but real click-through rates lagged. I analyzed residual errors and discovered temporal target leakage in a feature calculation. Fixing the data transformation pipeline resolved the issue and made subsequent models far more reliable.",
            "pitfalls": "Giving up on the project or blaming data engineers for poor data quality.",
        },
    ],
    "devops": [
        {
            "category": "technical",
            "question": "How do you design a zero-downtime Kubernetes CI/CD deployment pipeline with automated rollbacks?",
            "star_hint": "Explain GitOps (ArgoCD/Flux), Blue/Green or Canary deployments, Prometheus metric analysis, and health probes.",
            "strategy": "1. Code commit -> 2. Automated testing & container build -> 3. GitOps release -> 4. Canary deployment with Prometheus health analysis.",
            "sample_answer": "I build GitOps pipelines using GitHub Actions and ArgoCD. Changes trigger automated linting and unit testing before publishing signed Docker images. ArgoCD deploys canary releases to Kubernetes, routing 5% traffic while Prometheus monitors 5xx error rates. If latency or error thresholds are breached, automated rollbacks trigger immediately.",
            "pitfalls": "Deploying all pods at once without readiness/liveness probes or automated rollback criteria.",
        },
        {
            "category": "technical",
            "question": "How do you manage Infrastructure as Code (IaC) with Terraform across multi-environment cloud setups?",
            "star_hint": "Cover remote state locking (S3 + DynamoDB), reusable modules, Terraform workspaces/terragrunt, and drift detection.",
            "strategy": "1. Remote state backend with locking -> 2. Parameterized modules -> 3. Environment segregation (dev/stage/prod).",
            "sample_answer": "I structure Terraform using reusable modules and remote S3 state backends with DynamoDB locking. I segregate environments with dedicated state files, enforce least-privilege IAM roles via CI, and run scheduled `terraform plan` workflows to detect and alert on unauthorized manual infrastructure drift.",
            "pitfalls": "Storing state files locally or hardcoding environment credentials in repository code.",
        },
        {
            "category": "technical",
            "question": "How do you implement comprehensive observability (Metrics, Logs, Traces) across distributed cloud microservices?",
            "star_hint": "Discuss OpenTelemetry, Prometheus, Grafana, Jaeger/Tempo, structured JSON logging, and correlation IDs.",
            "strategy": "1. OpenTelemetry distributed tracing -> 2. Prometheus metrics & alerts -> 3. Centralized log aggregation with trace-id correlation.",
            "sample_answer": "I standardize observability using OpenTelemetry collectors. Every incoming request receives a unique `X-Correlation-ID` header propagated across all downstream microservice calls. Logs are emitted in structured JSON with trace context, and Prometheus metrics trigger actionable PagerDuty alerts based on SLO burn rates.",
            "pitfalls": "Logging massive unindexed unstructured strings without correlation IDs.",
        },
        {
            "category": "managerial",
            "question": "How do you manage incident response and conduct effective, blameless post-mortems after critical outages?",
            "star_hint": "Cover Incident Commander role, timely status communication, root-cause 5 Whys analysis, and preventive action items.",
            "strategy": "1. Immediate incident containment -> 2. Stakeholder updates -> 3. Blameless retrospective focused on systemic fixes.",
            "sample_answer": "During critical incidents, I establish clear roles including an Incident Commander and a Communications Lead to maintain external transparency. Following resolution, I facilitate a blameless post-mortem using the 5 Whys technique, focusing on systemic safeguards, monitoring gaps, and process improvements.",
            "pitfalls": "Blaming individual engineers or closing incidents without documenting preventive action items.",
        },
        {
            "category": "hr",
            "question": "How do you foster a culture of DevOps and shared operational responsibility among product developers?",
            "star_hint": "Discuss internal developer platforms, standardized templates, self-service tooling, and pairing during on-call rotations.",
            "strategy": "1. Self-service developer tooling -> 2. Clear documentation and CI templates -> 3. Collaborative on-call pairing.",
            "sample_answer": "I believe DevOps is a collaborative culture, not just a job title. I build internal developer platforms with self-service CI templates and clear telemetry dashboards, empowering software engineers to deploy and monitor their own services with confidence while providing expert mentorship.",
            "pitfalls": "Creating an isolated silo where developers throw code over the wall for DevOps to run.",
        },
    ],
    "core_swe": [
        {
            "category": "technical",
            "question": "How do you analyze algorithmic time and space complexity, and how do you optimize memory-intensive algorithms?",
            "star_hint": "Cover Big-O notation, CPU cache locality, garbage collection pressure, and in-place vs extra memory algorithms.",
            "strategy": "1. Identify Big-O bottlenecks -> 2. Memory optimization (pointers, generators, bitwise ops) -> 3. Cache locality.",
            "sample_answer": "I evaluate algorithms for both worst-case Big-O time and auxiliary space. In memory-intensive applications, I replace recursive call stacks with iterative loops, use streaming generators instead of allocating large arrays, and utilize contiguous memory structures (like arrays) to maximize CPU L1/L2 cache hits.",
            "pitfalls": "Optimizing micro-benchmarks prematurely without profiling the actual computational bottleneck.",
        },
        {
            "category": "technical",
            "question": "How do you design thread-safe concurrent systems and prevent race conditions and deadlocks?",
            "star_hint": "Discuss mutexes, atomic operations, read-write locks, lock ordering hierarchies, and channel/actor patterns.",
            "strategy": "1. Immutability where possible -> 2. Fine-grained locking with strict acquisition order -> 3. Atomic variables.",
            "sample_answer": "I prevent concurrency bugs by prioritizing immutable data structures. When shared mutable state is required, I use fine-grained Read-Write locks or atomic primitives. To prevent deadlocks, I enforce a strict global lock acquisition ordering hierarchy and utilize lock timeouts.",
            "pitfalls": "Acquiring multiple locks in different orders across different threads, inevitably causing deadlocks.",
        },
        {
            "category": "technical",
            "question": "What are the SOLID design principles, and how do you apply them to build scalable software architecture?",
            "star_hint": "Explain Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion with concrete examples.",
            "strategy": "Define each principle briefly -> Provide a practical example of Dependency Inversion & Single Responsibility.",
            "sample_answer": "SOLID principles guide maintainable software design. For instance, Single Responsibility ensures each class has one reason to change, while Dependency Inversion decouples high-level business logic from low-level storage details through interfaces, allowing seamless swapping and unit testing with mock dependencies.",
            "pitfalls": "Over-engineering simple scripts with excessive layers of abstraction before requirements warrant them.",
        },
        {
            "category": "managerial",
            "question": "How do you approach refactoring large legacy codebases without breaking existing functionality in production?",
            "star_hint": "Discuss characterization tests, the Strangler Fig pattern, feature flags, and incremental modular extraction.",
            "strategy": "1. Write end-to-end integration tests (golden tests) -> 2. Strangler Fig pattern -> 3. Feature flag rollout.",
            "sample_answer": "I never perform high-risk 'big bang' rewrites. Instead, I write characterization tests around legacy code to capture exact existing behavior, wrap the new implementation in feature flags, and use the Strangler Fig pattern to migrate traffic incrementally with automated regression monitoring.",
            "pitfalls": "Rewriting legacy systems from scratch without unit tests or characterization baselines.",
        },
        {
            "category": "hr",
            "question": "What motivates you most as a software engineer, and how do you ensure you are writing clean, maintainable code?",
            "star_hint": "Emphasize empathy for teammates, maintainability as a first-class feature, and solving real user problems.",
            "strategy": "1. Personal motivation (impact + elegance) -> 2. Engineering discipline (clean naming, test coverage).",
            "sample_answer": "I write code with empathy for the engineer who will maintain it next year. I use descriptive variable names, keep functions focused on a single responsibility, eliminate magic numbers, and write comprehensive tests so the code is clear, self-documenting, and durable.",
            "pitfalls": "Prioritizing clever, convoluted one-liners over readable and maintainable code.",
        },
    ],
}


def get_curated_role_questions(role_name: str, count: int = 20) -> list[dict]:
    """
    Intelligently matches a candidate's target role string to the most relevant
    curated discipline question bank.
    """
    lower = (role_name or "").lower()

    if any(k in lower for k in ["full stack", "fullstack", "web developer", "mean", "mern"]):
        selected = ROLE_QUESTION_BANKS["full_stack"]
    elif any(k in lower for k in ["backend", "python", "java", "node", "golang", "go developer", "api"]):
        selected = ROLE_QUESTION_BANKS["backend"]
    elif any(k in lower for k in ["frontend", "front end", "react", "vue", "angular", "ui", "ux"]):
        selected = ROLE_QUESTION_BANKS["frontend"]
    elif any(k in lower for k in ["data science", "data scientist", "machine learning", "ml engineer", "ai engineer", "data analyst", "nlp", "deep learning"]):
        selected = ROLE_QUESTION_BANKS["data_science"]
    elif any(k in lower for k in ["devops", "cloud", "sre", "site reliability", "infrastructure", "platform engineer", "kubernetes", "aws"]):
        selected = ROLE_QUESTION_BANKS["devops"]
    else:
        # Default to core software engineering / general SWE
        selected = ROLE_QUESTION_BANKS["core_swe"]

    return selected[:count]
