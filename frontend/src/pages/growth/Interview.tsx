import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  MessageCircleQuestion, ExternalLink, Sparkles,
  ChevronDown, ChevronUp, AlertTriangle, Lightbulb,
  Video, Code2, Users, Briefcase, Target,
} from "lucide-react";
import { getProfile } from "../../lib/profile";
import { type InterviewQuestion } from "../../lib/interview";

const TARGET_ROLE_OPTIONS = [
  "Full Stack Developer",
  "Backend Developer",
  "Frontend Developer",
  "Data Scientist",
  "DevOps Engineer",
  "Software Engineer",
];

const MOCK_PLATFORMS = [
  {
    name: "Pramp",
    url: "https://www.pramp.com/",
    desc: "Free 1-on-1 peer technical and behavioral mock interviews with live video & collaborative code editor.",
    tag: "Free Peer Mocks",
  },
  {
    name: "interviewing.io",
    url: "https://interviewing.io/",
    desc: "Free recorded technical mock interviews with senior FAANG and Tier-1 engineers.",
    tag: "Real FAANG Recordings",
  },
  {
    name: "LeetCode Discuss",
    url: "https://leetcode.com/discuss/interview-question",
    desc: "Active community repository of real interview questions reported by candidates across companies.",
    tag: "Company Question Sets",
  },
  {
    name: "Exponent",
    url: "https://www.tryexponent.com/",
    desc: "Free system design breakdowns and behavioral frameworks for technical candidates.",
    tag: "Framework Guides",
  },
  {
    name: "Tech Interview Handbook",
    url: "https://www.techinterviewhandbook.org/",
    desc: "Curated algorithms cheat sheets, behavioral STAR guides, and resume preparation tips.",
    tag: "Free Guides & Cheatsheets",
  },
];

// Curated Top 20 Standard Questions for Technical, Managerial, and HR rounds
const STANDARD_ROUND_QUESTIONS: Record<string, InterviewQuestion[]> = {
  technical: [
    {
      question: "How do you design a scalable RESTful API with proper pagination, rate limiting, and versioning?",
      category: "technical",
      star_hint: "Discuss REST constraints, cursor vs offset pagination, token-bucket rate limiting, and URI/header versioning.",
      strategy: "1. Clarify API endpoints and data model -> 2. Explain cursor pagination for large datasets -> 3. Discuss rate limiting using Redis token bucket -> 4. Detail versioning strategies (e.g. /v1/ vs custom headers).",
      sample_answer: "\"I design RESTful APIs by standardizing resources around nouns and HTTP verbs. For datasets exceeding 1,000 records, I implement cursor-based pagination over offset to avoid slow database scans. Rate limiting is enforced via Redis token-bucket middleware (e.g. 100 req/min per IP/token) with 429 Too Many Requests responses, and URI versioning (/api/v1/) is applied to ensure backwards compatibility.\"",
      pitfalls: "Recommending offset/limit for millions of rows without mentioning performance degradation, or forgetting HTTP status codes.",
    },
    {
      question: "What is the N+1 query problem in ORMs, and how do you diagnose and fix it in production?",
      category: "technical",
      star_hint: "Mention SQL logging, EXPLAIN ANALYZE, eager loading (select_related / joinedload), and batch fetching.",
      strategy: "1. Define what causes N+1 (looping over parent records to query children) -> 2. Explain how to detect it with APM or query profilers -> 3. Demonstrate eager join solutions.",
      sample_answer: "\"The N+1 problem occurs when an application executes 1 initial query to fetch N parent records, then N separate queries to fetch related child entities. In production, I detect this using APM query count alerts or SQL query loggers. I resolve it by enforcing eager loading—such as `select_related` for foreign keys and `prefetch_related` for many-to-many relationships in Django/SQLAlchemy, reducing N+1 queries to just 1 or 2 efficient JOINs.\"",
      pitfalls: "Confusing eager loading with caching without fixing the root database query.",
    },
    {
      question: "How do you implement caching with Redis, and how do you handle cache invalidation and the Thundering Herd problem?",
      category: "technical",
      star_hint: "Cover Cache-Aside pattern, TTL expiration, write-through vs write-back, and mutex locking for thundering herds.",
      strategy: "Explain the Cache-Aside pattern -> Discuss TTL strategy -> Explain mutex locks or probabilistic early expiration for thundering herd.",
      sample_answer: "\"I typically use the Cache-Aside pattern: the application reads from Redis first; on a cache miss, it fetches from the DB and writes to Redis with a reasonable TTL. To prevent the Thundering Herd problem when high-traffic keys expire, I use distributed mutex locks (Redlock) or add small random jitter to TTLs so multiple processes don't hit the primary DB simultaneously.\"",
      pitfalls: "Not setting TTLs or ignoring cache consistency on database updates.",
    },
    {
      question: "Explain the differences between SQL and NoSQL databases. When would you choose one over the other?",
      category: "technical",
      star_hint: "Contrast ACID guarantees, schema rigidity, horizontal scaling, and access patterns.",
      strategy: "Compare ACID vs BASE -> Structured relational queries vs document/key-value access -> Match to specific use cases.",
      sample_answer: "\"I choose relational SQL (e.g., PostgreSQL) when data relationships are highly relational, require strict ACID transactional integrity (such as payment processing or order management), and benefit from structured schemas. I choose NoSQL (e.g., MongoDB, DynamoDB) for high-write velocity, hierarchical document storage, or when horizontal partition sharding is essential for massive scale.\"",
      pitfalls: "Claiming NoSQL is always faster or that SQL cannot scale.",
    },
    {
      question: "How do you handle asynchronous processing and background tasks in web applications?",
      category: "technical",
      star_hint: "Mention message brokers (RabbitMQ/Kafka/Redis), task queues (Celery/BullMQ), idempotency, and retries with backoff.",
      strategy: "1. Decouple request/response from long-running jobs -> 2. Message queue architecture -> 3. Idempotent workers with exponential backoff.",
      sample_answer: "\"For operations taking over 200ms (like emails, PDF generation, or third-party webhooks), I offload work to background task queues like Celery with Redis or RabbitMQ. Workers process messages asynchronously, acknowledging upon success. I ensure task idempotency by tracking unique job UUIDs to prevent duplicate execution during network retries.\"",
      pitfalls: "Performing long blocking operations directly inside the synchronous HTTP request handler.",
    },
    {
      question: "How do you optimize frontend bundle size and web performance (Core Web Vitals)?",
      category: "technical",
      star_hint: "Discuss code splitting, dynamic imports, tree-shaking, lazy loading images, and minimizing LCP/CLS.",
      strategy: "1. Asset optimization (Vite/Webpack chunks) -> 2. Component-level lazy loading -> 3. Web vitals (LCP, FID, CLS).",
      sample_answer: "\"I optimize frontend performance by enabling route-based and component-based code splitting using `React.lazy()` and dynamic imports, tree-shaking unused library code, compressing assets with WebP/Brotli, and prefetching critical resources. This minimizes initial JavaScript execution time, improving Largest Contentful Paint (LCP) and First Input Delay (FID).\"",
      pitfalls: "Importing entire heavy icon/utility libraries without named/tree-shaken imports.",
    },
    {
      question: "Explain the concept of database indexing. How do B-Trees work, and when can indexes hurt performance?",
      category: "technical",
      star_hint: "Cover B-Tree search complexity O(log N), composite indexes, and write overhead on INSERT/UPDATE.",
      strategy: "Explain B-Tree balanced structure -> Composite index left-prefix rule -> Write amplification cost.",
      sample_answer: "\"Database indexes are separate data structures (typically B-Trees) that allow O(log N) lookup times on indexed columns instead of O(N) table scans. While indexes dramatically accelerate SELECT queries, they add overhead to INSERT, UPDATE, and DELETE operations because the index tree must be updated on every write. Therefore, indexes should be added strategically on filtered and joined columns.\"",
      pitfalls: "Suggesting indexing every column in a table.",
    },
    {
      question: "How does JWT authentication work, and how do you securely manage access vs refresh tokens?",
      category: "technical",
      star_hint: "Discuss header/payload/signature, short-lived access tokens in memory, and httpOnly Secure refresh tokens.",
      strategy: "Explain token structure -> Token issuance and validation flow -> Secure storage preventing XSS and CSRF.",
      sample_answer: "\"A JWT consists of Header, Payload, and Signature signed with a secret key. In a secure architecture, short-lived access tokens (15 mins) are stored in memory/headers to authorize API requests, while refresh tokens (7 days) are stored in `httpOnly, Secure, SameSite=Strict` cookies to prevent XSS theft. When the access token expires, the client silently requests a new pair.\"",
      pitfalls: "Storing sensitive credentials inside JWT payload or saving tokens in localStorage vulnerable to XSS.",
    },
    {
      question: "How do you design a database schema for an e-commerce order management system?",
      category: "technical",
      star_hint: "Cover Users, Products, Orders, OrderItems, normalized tables, and snapshot pricing.",
      strategy: "1. Entities & relationships -> 2. Schema normalization -> 3. Snapshotting product price at time of purchase.",
      sample_answer: "\"I design the schema with Users, Products, Orders, and OrderItems tables. Crucially, the OrderItems table must store a snapshot of the unit price at the time of purchase rather than linking dynamically to the Products table, ensuring historical orders remain accurate even if catalog prices change later.\"",
      pitfalls: "Not snapshotting unit price or inventory count at order time.",
    },
    {
      question: "What are microservices, and how do you manage distributed transactions without two-phase commit?",
      category: "technical",
      star_hint: "Discuss domain-driven services, API Gateways, Saga pattern (orchestration vs choreography), and compensating actions.",
      strategy: "Explain microservice boundaries -> The problem with 2PC -> Implement Saga pattern with compensating transactions.",
      sample_answer: "\"Microservices break applications into independently deployable domain services communicating via REST, gRPC, or event buses. Instead of blocking two-phase commits, I implement the Saga pattern: each service executes a local transaction and publishes an event. If a subsequent step fails, compensating transactions are triggered in reverse to rollback the distributed workflow.\"",
      pitfalls: "Advocating for distributed monoliths or shared databases across microservices.",
    },
    {
      question: "What is the difference between concurrency and parallelism, and how does your language handle async I/O?",
      category: "technical",
      star_hint: "Contrast dealing with a lot of things at once vs doing a lot of things at once (event loop vs threads/GIL).",
      strategy: "Define concurrency vs parallelism -> Detail event loop / coroutines (Node.js/Python asyncio) vs thread pools.",
      sample_answer: "\"Concurrency is about structure—handling multiple tasks at once by interleaving them (e.g. non-blocking I/O in single-threaded event loops), whereas parallelism is about simultaneous execution on multiple CPU cores. In asynchronous runtimes like Node.js or Python AsyncIO, non-blocking network calls allow the thread to process other requests while waiting for I/O to complete.\"",
      pitfalls: "Claiming multi-threading and asynchronous I/O are the exact same thing.",
    },
    {
      question: "How do you detect and fix memory leaks in web applications?",
      category: "technical",
      star_hint: "Mention heap snapshots, lingering event listeners, unclosed DB connections, and global references.",
      strategy: "1. Diagnostic tools (Heap profilers, memory graphs) -> 2. Common root causes (listeners, closures, circular refs) -> 3. Cleanup hooks.",
      sample_answer: "\"I detect memory leaks by taking sequential heap snapshots under simulated load using browser dev tools or Node.js `--inspect`. Common causes include unremoved event listeners in React `useEffect` cleanups, lingering global variables, or unclosed database connection pools. I resolve them by ensuring proper component unmount teardowns and connection recycling.\"",
      pitfalls: "Restarting servers periodically instead of identifying the underlying object reference leak.",
    },
    {
      question: "Explain the CORS (Cross-Origin Resource Sharing) mechanism and how to configure it securely.",
      category: "technical",
      star_hint: "Discuss preflight OPTIONS requests, Access-Control-Allow-Origin, credentials, and avoiding wildcard origins in production.",
      strategy: "Explain same-origin policy -> Preflight handshake -> Setting specific allowed origins over `*`.",
      sample_answer: "\"CORS is a browser security mechanism that restricts web pages from requesting resources from a different domain, port, or protocol. For complex requests (like PUT or custom headers), the browser sends a preflight `OPTIONS` request. In production, I configure CORS middleware to explicitly allow only trusted frontend domains rather than using wildcard `*`, especially when handling authenticated credentials.\"",
      pitfalls: "Setting `Access-Control-Allow-Origin: *` while passing authorization cookies/tokens.",
    },
    {
      question: "How do you handle schema migrations in production databases with zero downtime?",
      category: "technical",
      star_hint: "Discuss expand-and-contract pattern, non-blocking ALTER TABLE, backfilling data, and phased deprecation.",
      strategy: "1. Expand phase (add new column as nullable) -> 2. Dual-write in code -> 3. Backfill data -> 4. Contract phase (remove old column).",
      sample_answer: "\"I use the Expand-and-Contract pattern: First, add the new column as nullable without locking tables. Next, deploy code that writes to both old and new columns. Then, run a background worker to backfill historical rows in batches. Finally, switch reads to the new column and deploy a migration to safely drop the deprecated field.\"",
      pitfalls: "Running a blocking ALTER TABLE on a 10M row table during peak business traffic.",
    },
    {
      question: "What is CI/CD, and how do you design an automated deployment pipeline?",
      category: "technical",
      star_hint: "Cover GitHub Actions, automated linting, unit/integration test suites, container builds, and blue-green deployments.",
      strategy: "Explain commit hook -> Build & test verification -> Container artifact push -> Zero-downtime rolling/blue-green deploy.",
      sample_answer: "\"A robust CI/CD pipeline triggers on pull requests to run static linting, unit tests, and integration tests. On merging to `main`, it builds Docker container images, scans for security vulnerabilities, and deploys to staging. After automated smoke tests pass, it promotes to production using rolling updates or Blue-Green deployments to ensure zero user downtime.\"",
      pitfalls: "Deploying directly to production without automated regression testing or rollback triggers.",
    },
    {
      question: "How do you prevent common web security vulnerabilities like SQL Injection, XSS, and CSRF?",
      category: "technical",
      star_hint: "Mention parameterized queries/ORMs, output escaping, Content Security Policy, and SameSite cookie attributes.",
      strategy: "1. SQLi: Parameterized queries -> 2. XSS: Contextual escaping & CSP -> 3. CSRF: Anti-CSRF tokens & SameSite cookies.",
      sample_answer: "\"I prevent SQL Injection by strictly using parameterized queries or ORMs that never concatenate raw user input into SQL strings. For XSS, I enforce automatic HTML output escaping and strict Content Security Policy (CSP) headers. For CSRF, I use `SameSite=Strict` cookie attributes alongside anti-CSRF token verification on state-changing POST/PUT requests.\"",
      pitfalls: "Relying on manual regex sanitization rather than parameterized statements.",
    },
    {
      question: "How do you design a URL shortener service (like bit.ly)?",
      category: "technical",
      star_hint: "Cover Base62 encoding, unique counter / UUID hashing, Redis caching for hot redirects, and DB schema.",
      strategy: "1. Requirements & scale (100M URLs) -> 2. Base62 encoding on auto-incrementing ID -> 3. High-read caching in Redis -> 4. Redirect 301 vs 302.",
      sample_answer: "\"I calculate storage scale and use Base62 encoding (a-z, A-Z, 0-9) over a distributed ID generator (e.g. Snowflake or DB auto-increment) to produce a 6-7 character hash capable of encoding trillions of unique URLs. Read lookups are cached in Redis with a 301/302 redirect strategy, reducing database load for viral links.\"",
      pitfalls: "Using MD5/SHA256 without collision resolution, or using 301 redirect when click analytics are required.",
    },
    {
      question: "What are WebSockets and Server-Sent Events (SSE), and how do you choose between them?",
      category: "technical",
      star_hint: "Contrast full-duplex bi-directional communication vs server-to-client streaming over HTTP.",
      strategy: "Compare protocol overhead -> Bi-directional (WebSockets) vs Uni-directional (SSE) -> Reconnection handling.",
      sample_answer: "\"WebSockets provide full-duplex, bi-directional TCP communication ideal for live chats, collaborative whiteboards, or multiplayer gaming. Server-Sent Events (SSE) provide lightweight, uni-directional streaming from server to client over standard HTTP, making them ideal and far easier to scale for live dashboards, stock tickers, or AI streaming replies.\"",
      pitfalls: "Defaulting to heavy WebSocket servers when the data flow is strictly one-directional from server to client.",
    },
    {
      question: "How do you implement rate limiting across distributed server clusters?",
      category: "technical",
      star_hint: "Discuss sliding window counter vs token bucket in centralized Redis with Lua scripts.",
      strategy: "Explain why in-memory rate limits fail on multi-instance clusters -> Use Redis sliding window with atomic Lua execution.",
      sample_answer: "\"In a distributed cluster, in-memory rate limiters fail because traffic is spread across multiple pods. I implement a Redis-backed Sliding Window Counter or Token Bucket executed via atomic Lua scripts to prevent race conditions. The script checks timestamps in a sorted set (ZADD), counts requests within the current window, and rejects excess traffic with HTTP 429.\"",
      pitfalls: "Using local server memory for rate limiting behind a round-robin load balancer.",
    },
    {
      question: "What are the SOLID principles of Object-Oriented Design, and how do they improve code maintainability?",
      category: "technical",
      star_hint: "Briefly explain Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion.",
      strategy: "Walk through each principle concisely with a practical real-world software engineering example.",
      sample_answer: "\"SOLID stands for: Single Responsibility (a class should have one reason to change), Open/Closed (open for extension, closed for modification via abstractions), Liskov Substitution (derived classes must substitute base classes without breaking behavior), Interface Segregation (small, focused interfaces), and Dependency Inversion (depend on abstractions, not concrete implementations via DI). Following these creates decoupled, easily testable systems.\"",
      pitfalls: "Reciting definitions without explaining how they prevent architectural fragility in large codebases.",
    },
  ],
  managerial: [
    {
      question: "Walk me through the most technically complex project you've built. What architectural trade-offs did you make?",
      category: "managerial",
      star_hint: "Use STAR: Situation, Technical constraints, specific Action/code choices, and quantifiable Business Results.",
      strategy: "Situation -> Architecture constraints -> 2 competing choices with trade-offs -> Result with numbers.",
      sample_answer: "\"In my primary project, we needed real-time updates for thousands of active users. I evaluated WebSockets vs Server-Sent Events and chose SSE because our data flow was strictly server-to-client, saving ~40% server memory overhead. As a result, API response latency dropped by 35% with 99.9% uptime. If re-doing it today, I would implement automated contract testing earlier in the sprint.\"",
      pitfalls: "Talking vaguely about team accomplishments without specifying your own individual engineering decisions and metrics.",
    },
    {
      question: "How do you balance technical debt against delivering urgent business features under tight sprint deadlines?",
      category: "managerial",
      star_hint: "Frame tech debt as business risk, quantify developer velocity impact, and propose an 80/20 capacity model.",
      strategy: "1. Acknowledge product goals -> 2. Categorize tech debt by risk & velocity cost -> 3. Allocate regular sprint capacity.",
      sample_answer: "\"I categorize technical debt into critical stability risks and maintenance friction. For critical stability blockers, I fix them immediately. For general debt, I quantify the velocity tax on the engineering team and work with product managers to allocate ~15-20% of each sprint toward refactoring and test coverage, framing it around long-term shipping speed and uptime.\"",
      pitfalls: "Treating tech debt as purely an engineering preference rather than a business risk.",
    },
    {
      question: "Describe a time when you had a serious technical disagreement with a teammate or lead. How did you resolve it?",
      category: "managerial",
      star_hint: "Show emotional intelligence, data-driven benchmarking, objective criteria, and 'disagree and commit' maturity.",
      strategy: "Describe the disagreement objectively -> Propose an empirical benchmark -> Focus on data over ego -> Commit to the outcome.",
      sample_answer: "\"When deciding between two state management libraries, my teammate and I disagreed on bundle size versus developer ergonomics. Instead of arguing theoretically, I created a quick prototype testing both options on build times, memory usage, and component rendering speeds. The data proved the lighter library reduced bundle size by 38%, which we both agreed best served our users.\"",
      pitfalls: "Blaming the colleague or appearing stubborn and unwilling to compromise.",
    },
    {
      question: "How do you conduct code reviews? What do you look for, and how do you give constructive feedback?",
      category: "managerial",
      star_hint: "Focus on correctness, security, edge cases, test coverage, architectural alignment, and kind empathetic communication.",
      strategy: "1. Automated tools first (linters/tests) -> 2. Review architecture, security, edge cases -> 3. Frame comments constructively (e.g. 'What do you think about...?').",
      sample_answer: "\"I rely on CI automation to catch style and formatting issues so human reviews can focus on architectural integrity, edge case handling, database query efficiency, and security boundaries. I phrase feedback constructively—asking questions like 'What happens if this input is null?' or offering code snippets—and ensure I praise elegant implementations as well.\"",
      pitfalls: "Nitpicking syntax issues that a linter should catch, or being overly critical without proposing better solutions.",
    },
    {
      question: "Tell me about a situation where a production incident occurred. How did you diagnose, mitigate, and prevent recurrence?",
      category: "managerial",
      star_hint: "Cover calm triage, rollback/hotfix mitigation, communication with stakeholders, and a blameless post-mortem.",
      strategy: "1. Triage & mitigate impact immediately -> 2. Root cause diagnosis -> 3. Blameless post-mortem with preventative action items.",
      sample_answer: "\"When an unindexed database query spiked CPU usage to 100%, our immediate priority was mitigation: we rolled back to the previous stable release to restore service in under 6 minutes. Once traffic normalized, I investigated APM slow-query logs, added the missing composite index, and instituted automated query profiling in our CI pipeline to prevent future regressions.\"",
      pitfalls: "Trying to debug live in production for hours before mitigating user impact, or assigning personal blame.",
    },
    {
      question: "How do you estimate engineering tasks, and what do you do when you realize a deadline will be missed?",
      category: "managerial",
      star_hint: "Discuss breaking tasks into small sub-components, adding buffer for unknowns, and proactive early communication.",
      strategy: "Explain estimation method -> Proactive early communication -> Negotiating scope with product managers.",
      sample_answer: "\"I estimate tasks by breaking them down into 1-2 day deliverables and accounting for testing, code review, and edge cases. If unexpected blockers threaten a deadline, I communicate proactively with product leads at the earliest signal—never on the day of the release—presenting clear options such as scoping down nice-to-have features to ship the core MVP on schedule.\"",
      pitfalls: "Hiding delays until the deadline day, or silently burning out to hit an impossible estimate.",
    },
    {
      question: "How do you onboard new engineers or mentor junior teammates to help them become productive quickly?",
      category: "managerial",
      star_hint: "Mention comprehensive documentation, starter good-first-issues, pair programming, and psychological safety.",
      strategy: "1. Clear setup docs & reproducible environments -> 2. Quick first PR on Day 1 -> 3. Regular 1-on-1 check-ins and pair coding.",
      sample_answer: "\"I set up new engineers for success by maintaining streamlined Dockerized onboarding scripts so their local environment runs in minutes. I assign a small, high-confidence 'good first issue' to help them deploy to production on their first week, and schedule regular pair programming sessions to encourage questions in a supportive environment.\"",
      pitfalls: "Dumping large complex codebases on newcomers without guidance or starter milestones.",
    },
    {
      question: "How do you approach refactoring a large legacy codebase without breaking existing business logic?",
      category: "managerial",
      star_hint: "Discuss characterization tests, strangler fig pattern, incremental modularity, and feature flags.",
      strategy: "1. Write end-to-end tests to lock down current behavior -> 2. Strangler Fig pattern -> 3. Feature flags for gradual rollout.",
      sample_answer: "\"Before touching legacy code, I write comprehensive characterization and regression tests to guarantee existing behavior is preserved. I then use the Strangler Fig pattern—incrementally replacing legacy modules behind feature flags—enabling us to route a small percentage of traffic to the new code and safely roll back if anomalies occur.\"",
      pitfalls: "Attempting a massive 'big bang' rewrite from scratch that delays shipping for months.",
    },
    {
      question: "How do you handle scope creep when product requirements change mid-sprint?",
      category: "managerial",
      star_hint: "Demonstrate collaborative partnership: evaluate impact on sprint goals, trade off lower-priority items, and document decisions.",
      strategy: "1. Assess technical impact -> 2. Discuss trade-offs with stakeholders -> 3. Adjust backlog transparently.",
      sample_answer: "\"When new requirements emerge mid-sprint, I evaluate the technical effort and impact on our committed deliverables. I discuss this with the product manager collaboratively, explaining that accommodating the new feature requires swapping out a lower-priority task of equivalent effort to maintain high code quality and prevent missed sprint commitments.\"",
      pitfalls: "Saying a blunt 'no' without explaining constraints, or saying 'yes' to everything and producing rushed, buggy code.",
    },
    {
      question: "How do you evaluate and choose new technologies or third-party libraries for a project?",
      category: "managerial",
      star_hint: "Discuss community health, maintenance activity, security vulnerabilities, license compliance, and team learning curve.",
      strategy: "1. Define business & technical requirements -> 2. Criteria evaluation (license, GitHub activity, bundle size) -> 3. Spike prototype.",
      sample_answer: "\"I evaluate third-party tools against a structured checklist: license compatibility (MIT/Apache vs restrictive licenses), active maintainer support, security audit history, documentation quality, and team familiarity. I build a 1-day spike prototype to validate whether the library solves our core problem before introducing it into production dependencies.\"",
      pitfalls: "Adopting trendy new libraries without evaluating maintenance health, bundle overhead, or security vulnerabilities.",
    },
    {
      question: "Describe a project where you had to make significant performance optimizations. How did you identify the bottleneck?",
      category: "managerial",
      star_hint: "Emphasize measuring before optimizing: APM tools, flame graphs, database query logs, and verified benchmark improvements.",
      strategy: "1. Measurement phase -> 2. Identified bottleneck -> 3. Implemented targeted fix -> 4. Verified post-optimization metrics.",
      sample_answer: "\"When an endpoint experienced 1.8-second response times, I avoided guessing and used APM tracing to identify the bottleneck: 80% of the latency was caused by sequential database lookups in a loop. By rewriting the query with a single bulk fetch and adding Redis caching for immutable reference data, endpoint response time dropped to 120ms (a 93% improvement).\"",
      pitfalls: "Applying premature micro-optimizations without profiling real application bottlenecks.",
    },
    {
      question: "How do you foster a culture of quality, documentation, and continuous learning within an engineering team?",
      category: "managerial",
      star_hint: "Mention blameless post-mortems, Architecture Decision Records (ADRs), tech talks, and automated quality gates.",
      strategy: "1. Living documentation & ADRs -> 2. Knowledge sharing (lunch & learns) -> 3. Automated quality standards.",
      sample_answer: "\"I champion team quality by instituting Architecture Decision Records (ADRs) to document why technical choices were made for future developers. I also organize bi-weekly engineering tech-sharing sessions and ensure automated testing and linting gates protect master branches, making code quality an automated standard rather than an afterthought.\"",
      pitfalls: "Treating documentation as a one-time chore that is never updated.",
    },
    {
      question: "How do you handle working with non-technical stakeholders (Product, Sales, Design)?",
      category: "managerial",
      star_hint: "Translate technical trade-offs into business impact: customer experience, revenue, reliability, and delivery speed.",
      strategy: "1. Speak in business outcomes -> 2. Visual diagrams/demos -> 3. Collaborative empathy.",
      sample_answer: "\"When communicating with non-technical stakeholders, I avoid engineering jargon and frame discussions around business outcomes: user conversion, page load speeds, and system reliability. I use visual workflow diagrams and interactive prototypes to align on requirements early, ensuring everyone shares a common understanding of project milestones.\"",
      pitfalls: "Burying stakeholders in technical acronyms or dismissing non-technical feedback.",
    },
    {
      question: "Tell me about a time you identified a major risk in a project before it caused problems. What did you do?",
      category: "managerial",
      star_hint: "Demonstrate proactive risk management: capacity planning, single points of failure, third-party API dependencies.",
      strategy: "1. Identified risk -> 2. Quantified probability & impact -> 3. Proactively engineered mitigation.",
      sample_answer: "\"While designing a feature dependent on a third-party SMS API, I recognized that their rate limits would become a hard bottleneck during marketing campaigns. I proactively designed an asynchronous queue with circuit-breaker protection and a secondary fallback SMS provider, ensuring user verification messages succeeded seamlessly during peak traffic.\"",
      pitfalls: "Ignoring known risks and waiting for production failures before addressing them.",
    },
    {
      question: "How do you manage stress and maintain high team morale during high-pressure release cycles?",
      category: "managerial",
      star_hint: "Prioritize clear focus, eliminate distractions, celebrate small milestones, and ensure sustainable pace.",
      strategy: "1. Ruthless prioritization -> 2. Remove blockers -> 3. Maintain calm, supportive team leadership.",
      sample_answer: "\"During crunch periods, I help maintain team morale by clarifying the top 2-3 essential blockers and removing non-essential meetings. I ensure transparent status tracking so no single engineer is overloaded, encourage healthy work boundaries, and openly celebrate completed milestones to keep team motivation high.\"",
      pitfalls: "Passing panic down to teammates or encouraging unsustainable burnout.",
    },
    {
      question: "How do you approach testing in software development? What is your testing philosophy?",
      category: "managerial",
      star_hint: "Discuss the Testing Pyramid: unit tests for core logic, integration tests for API/DB contracts, and focused E2E tests.",
      strategy: "Explain Test Pyramid -> Cost vs confidence ratio -> Emphasize fast, automated test feedback.",
      sample_answer: "\"My testing philosophy follows the Testing Pyramid: a strong base of fast, isolated unit tests covering business logic; integration tests validating API contracts and database queries; and a minimal set of critical-path end-to-end tests for user checkout/auth. This provides high release confidence while keeping CI test suites fast.\"",
      pitfalls: "Relying solely on manual QA or having only slow, flaky end-to-end tests.",
    },
    {
      question: "What is your process for designing a new software feature from scratch?",
      category: "managerial",
      star_hint: "Cover requirements gathering, Design Doc (RFC), API schema design, peer review, implementation, and telemetry monitoring.",
      strategy: "1. Requirements -> 2. Technical Design Doc -> 3. Review & feedback -> 4. Phased build & monitoring.",
      sample_answer: "\"I start by clarifying requirements and edge cases with product and design leads. I write a concise Technical Design Doc covering architecture, database schema, API contracts, and security considerations. After team review and alignment, I break the work into phased milestones, build with tests, and configure APM dashboards to monitor performance upon release.\"",
      pitfalls: "Writing code immediately without understanding requirements or aligning on architecture with teammates.",
    },
    {
      question: "Describe a time you had to learn an entirely new technology or framework on a short deadline. How did you master it?",
      category: "managerial",
      star_hint: "Show structured self-learning: official documentation, building proof-of-concept prototypes, and understanding core concepts.",
      strategy: "1. Core concepts over surface syntax -> 2. Build hands-on MVP -> 3. Ship production-ready code.",
      sample_answer: "\"When tasked with building a microservice in Go within two weeks, I focused on core fundamentals first: goroutines, channels, interface semantics, and error handling patterns through official documentation. I built a proof-of-concept CRUD service in 3 days to test database drivers and concurrency, enabling me to deliver the production service on schedule.\"",
      pitfalls: "Copy-pasting code snippets from online forums without understanding language idioms or error handling.",
    },
    {
      question: "How do you decide when a feature is truly 'Done' and ready for production release?",
      category: "managerial",
      star_hint: "Definition of Done (DoD): unit/integration tests pass, code reviewed, docs updated, telemetry/alerts configured.",
      strategy: "Explain rigorous Definition of Done across code, tests, documentation, and operational readiness.",
      sample_answer: "\"A feature is 'Done' when code meets our full Definition of Done: automated unit and integration tests pass with high coverage, peer code reviews are approved, API documentation is updated, and telemetry monitoring/alerts are configured to track errors and latency in production.\"",
      pitfalls: "Considering code done the moment it runs locally on the developer's laptop.",
    },
    {
      question: "Where do you see yourself technically and professionally in the next 3 to 5 years?",
      category: "managerial",
      star_hint: "Highlight continuous technical mastery, system architecture ownership, mentorship, and driving measurable business impact.",
      strategy: "1. Deepen stack mastery -> 2. Own large-scale system architecture -> 3. Mentor teammates and influence technical roadmap.",
      sample_answer: "\"In the next 3-5 years, my goal is to evolve into a Lead Software Engineer, taking end-to-end ownership of core distributed systems and architectural standards while mentoring early-career engineers. I want to continue driving measurable business impact through reliable, elegant engineering.\"",
      pitfalls: "Giving a vague generic answer or expressing disinterest in engineering growth.",
    },
  ],
  hr: [
    {
      question: "Tell me about yourself and your background in software engineering.",
      category: "hr",
      star_hint: "Present Present-Past-Future framework: current focus/skills, key proud engineering achievements, and future career goals.",
      strategy: "1. Present: Current core stack & passion -> 2. Past: Key projects/experience & measurable metrics -> 3. Future: Why this role excites you.",
      sample_answer: "\"I am a software engineer specializing in scalable full-stack web applications, with hands-on experience across Python, TypeScript, React, and PostgreSQL. In my recent work, I built and deployed responsive systems with optimized database schemas and REST APIs, improving latency by 30%. I'm passionate about building reliable user-facing products and excited about this opportunity to contribute to high-impact systems.\"",
      pitfalls: "Reciting your entire resume chronologically or sharing non-professional personal trivia.",
    },
    {
      question: "Why do you want to work for our company specifically?",
      category: "hr",
      star_hint: "Demonstrate genuine research: mention specific products, engineering culture, scale challenges, and shared values.",
      strategy: "1. Express specific appreciation for company product/tech -> 2. Connect to your skills -> 3. State how you will create immediate value.",
      sample_answer: "\"I've followed your company's engineering milestones and product growth closely, especially your focus on high-availability systems and developer experience. This position is the exact intersection of my strengths in clean backend architecture and fast user interfaces, and I am eager to bring my problem-solving energy to help your team scale.\"",
      pitfalls: "Giving a generic template answer that could apply to any company without naming specific reasons.",
    },
    {
      question: "What are your greatest professional strengths, and what is one area you are actively working to improve?",
      category: "hr",
      star_hint: "Strength: Grounded in real technical problem-solving. Weakness: A genuine developmental area with active steps you take to improve.",
      strategy: "Strength with proof -> Real weakness -> Concrete actionable habits you use to overcome it.",
      sample_answer: "\"My greatest strength is my structured approach to debugging complex distributed problems and writing well-tested, maintainable code. One area I am actively improving is delegating tasks earlier during intense sprints; I've started setting up clear sub-task ownership in sprint planning to ensure balanced team bandwidth.\"",
      pitfalls: "Giving fake weaknesses like 'I'm a perfectionist' or 'I work too hard'.",
    },
    {
      question: "Tell me about a time you made a significant mistake or a project failed. What happened and what did you learn?",
      category: "hr",
      star_hint: "Take 100% accountability, explain the root cause, show how you resolved it, and detail permanent process improvements.",
      strategy: "1. Honest situation -> 2. Owned mistake -> 3. Fast remediation -> 4. Long-term systemic safeguard created.",
      sample_answer: "\"Early on, an unhandled API edge case caused an unexpected error in testing. Rather than finding a quick patch, I conducted a root-cause review, added strict schema validation, and instituted automated regression tests. That experience taught me the critical value of proactive boundary testing, which has made all my subsequent releases significantly more resilient.\"",
      pitfalls: "Claiming you've never failed, or blaming teammates, management, or external clients.",
    },
    {
      question: "Describe a situation where you had to work under tight deadlines with competing priorities. How did you manage?",
      category: "hr",
      star_hint: "Use STAR: Show prioritization criteria, transparent communication, and disciplined execution.",
      strategy: "Situation -> Prioritization framework (urgency vs impact) -> Action taken -> Successful outcome.",
      sample_answer: "\"During a major release, two critical features faced unexpected API changes simultaneously. I evaluated both by customer impact and business risk, communicated the revised delivery schedule to stakeholders, and focused on delivering the primary auth workflow first before completing the secondary reporting tool on time.\"",
      pitfalls: "Panicking, cutting testing corners, or failing to communicate priority adjustments.",
    },
    {
      question: "How do you handle constructive criticism or critical feedback from a manager or peer?",
      category: "hr",
      star_hint: "Demonstrate emotional maturity, curiosity, listening without defensiveness, and implementing actionable improvements.",
      strategy: "1. Welcome feedback objectively -> 2. Ask clarifying questions -> 3. Action plan -> 4. Follow-up verification.",
      sample_answer: "\"I view constructive feedback as the fastest catalyst for professional growth. When a senior engineer pointed out that my PR descriptions lacked testing steps, I thanked them, adopted a standardized PR template with test matrices, and followed up two weeks later to confirm the documentation met team standards.\"",
      pitfalls: "Becoming defensive, arguing during feedback delivery, or holding grudges.",
    },
    {
      question: "Tell me about a time you went above and beyond your standard job duties for a project or user.",
      category: "hr",
      star_hint: "Show initiative, customer empathy, and ownership beyond your immediate job description.",
      strategy: "1. Problem noticed proactively -> 2. Initiative taken beyond assigned scope -> 3. Positive impact on team/users.",
      sample_answer: "\"While working on an internal API, I noticed our team was spending 30 minutes daily manually resetting local mock test data. On my own initiative, I created a Dockerized mock database seeding script with one-click reset, saving the entire engineering team over 2.5 hours weekly.\"",
      pitfalls: "Describing standard required tasks as if they were extraordinary efforts.",
    },
    {
      question: "How do you stay updated with emerging technologies and industry best practices?",
      category: "hr",
      star_hint: "Mention reputable blogs, open-source repositories, hands-on weekend experiments, and technical newsletters.",
      strategy: "1. Specific resources (e.g. Hacker News, GitHub Trending, ByteByteGo) -> 2. Building small sandbox projects.",
      sample_answer: "\"I stay current by reading engineering blogs from companies like Netflix and Uber, following GitHub trending repositories, and subscribing to newsletters like ByteByteGo. Crucially, I test new libraries by building small weekend proof-of-concept apps to evaluate their real-world developer ergonomics.\"",
      pitfalls: "Giving vague answers like 'I browse social media' without naming technical sources or practices.",
    },
    {
      question: "Describe a time when you had to collaborate with a difficult team member or stakeholder.",
      category: "hr",
      star_hint: "Demonstrate empathy, seeking to understand underlying concerns, finding common ground, and professional focus.",
      strategy: "1. Professional framing -> 2. Identified root issue (differing communication styles) -> 3. Aligned on shared goals.",
      sample_answer: "\"I once worked with a teammate who was hesitant about adopting automated PR checks. Instead of escalating, I set up a 1-on-1 to understand their concerns, which stemmed from fears that CI would slow down daily commits. I demonstrated how local pre-commit hooks catch errors in seconds, and we agreed to pilot it together successfully.\"",
      pitfalls: "Speaking negatively about former colleagues or painting yourself as entirely blameless.",
    },
    {
      question: "What motivates you most in your daily engineering work?",
      category: "hr",
      star_hint: "Highlight building solutions that solve real user problems, solving complex technical puzzles, and team collaboration.",
      strategy: "Connect technical curiosity with real-world user and business impact.",
      sample_answer: "\"I am motivated by the tangible impact of software—knowing that clean, reliable code directly simplifies an end user's life or speeds up a critical business workflow. I also thrive on the collaborative problem-solving aspect of engineering: taking an ambiguous challenge and turning it into an elegant system.\"",
      pitfalls: "Mentioning purely compensation or perks as your sole motivation.",
    },
    {
      question: "How do you handle ambiguity when project requirements are vague or incomplete?",
      category: "hr",
      star_hint: "Show proactive initiative: ask clarifying questions, create mockups/PRDs, build small prototypes, and align early.",
      strategy: "1. Embrace ambiguity -> 2. Create structured proposal/questions -> 3. Align with stakeholders before building.",
      sample_answer: "\"When faced with ambiguous requirements, I break down what is known versus what needs validation. I draft a concise 1-page proposal outlining assumptions, expected user flows, and open questions, and schedule a quick 15-minute sync with the product manager to align before writing code.\"",
      pitfalls: "Building assumptions blindly without asking questions, or sitting idle waiting for perfect requirements.",
    },
    {
      question: "Describe a situation where you had to persuade someone to see your point of view.",
      category: "hr",
      star_hint: "Use objective facts, data, user empathy, and collaborative persuasion rather than emotional arguments.",
      strategy: "Situation -> Initial resistance -> Presented data/prototype -> Mutual consensus achieved.",
      sample_answer: "\"When advocating for automated unit testing in our build pipeline, our lead was concerned about setup time. I prepared a short demo showing how 3 recent production bugs would have been caught instantly by 5 unit tests in under 2 seconds. The data clearly demonstrated the time savings, and the lead approved the rollout.\"",
      pitfalls: "Describing persuasion as 'winning an argument' rather than finding the best collective solution.",
    },
    {
      question: "What type of work environment or engineering culture allows you to do your best work?",
      category: "hr",
      star_hint: "Emphasize psychological safety, clear goals, high engineering standards, and collaborative ownership.",
      strategy: "1. Autonomy & high standards -> 2. Collaborative communication -> 3. Focus on continuous learning.",
      sample_answer: "\"I thrive in an engineering culture that values ownership, open communication, and high quality standards. An environment where engineers are empowered to propose architectural improvements, conduct respectful code reviews, and learn from mistakes allows me to contribute my best work.\"",
      pitfalls: "Demanding unrealistic perks or giving negative descriptions of past employers.",
    },
    {
      question: "Tell me about a time you had to adapt quickly to an unexpected organizational or priority change.",
      category: "hr",
      star_hint: "Demonstrate adaptability, positive attitude, fast context switching, and maintaining productivity.",
      strategy: "1. The sudden shift -> 2. Positive mindset & replanning -> 3. Successful execution in new direction.",
      sample_answer: "\"When our company shifted strategic focus from a reporting module to an urgent compliance integration, I reorganized my task backlog that afternoon, reviewed the new compliance API specifications, and assisted teammates in context-switching, successfully shipping the integration 2 days ahead of deadline.\"",
      pitfalls: "Complaining about management shifts or resisting necessary business changes.",
    },
    {
      question: "How do you manage your work-life balance and prevent burnout during intense quarters?",
      category: "hr",
      star_hint: "Show maturity: time management, setting clear boundaries, physical fitness, and sustainable engineering pacing.",
      strategy: "1. Time blocking & focus hours -> 2. Clear communication of capacity -> 3. Healthy recharging habits.",
      sample_answer: "\"I maintain sustainable productivity through strict time blocking—allocating focused deep-work hours in the morning for complex coding and afternoons for collaboration. Outside work, I stay active with regular exercise and hobbies, which helps me return to daily problem-solving with renewed focus.\"",
      pitfalls: "Claiming you work 16 hours every day without breaks, or giving an answer that suggests low commitment.",
    },
    {
      question: "Describe a proud accomplishment outside of formal academics or work duties.",
      category: "hr",
      star_hint: "Highlight curiosity: personal open-source projects, hackathons, organizing meetups, or self-taught skills.",
      strategy: "1. Project/Initiative -> 2. Challenge overcome -> 3. Personal growth and takeaway.",
      sample_answer: "\"I am particularly proud of an open-source developer tool I built during a weekend hackathon that helps developers format JSON API schemas automatically. Seeing it reach over 200 GitHub stars and receive pull requests from global contributors was an incredibly rewarding validation of building for the community.\"",
      pitfalls: "Sharing irrelevant personal stories with no connection to problem-solving or passion.",
    },
    {
      question: "How do you ensure you are writing clean, maintainable, and readable code?",
      category: "hr",
      star_hint: "Mention descriptive naming conventions, single-purpose functions, self-documenting code, and DRY principles.",
      strategy: "1. Readability as a first-class feature -> 2. Small testable functions -> 3. Empathy for the next maintainer.",
      sample_answer: "\"I write code with empathy for the engineer who will maintain it next year. I use descriptive variable names, keep functions focused on a single responsibility, eliminate magic numbers, and write comprehensive tests so the code is clear and self-documenting without relying on excessive comments.\"",
      pitfalls: "Believing clever, convoluted one-line code is superior to readable, clean code.",
    },
    {
      question: "What are your salary and compensation expectations for this position?",
      category: "hr",
      star_hint: "Be professional, market-aware, flexible, and emphasize finding the right mutual career fit.",
      strategy: "1. Acknowledge market research -> 2. State reasonable range based on experience -> 3. Express openness to overall package.",
      sample_answer: "\"Based on market research for this role and my technical skill set, I am targeting a compensation range between ₹7 LPA and ₹12 LPA. However, I am open to discussing the total compensation package including performance incentives and learning opportunities for the right long-term role.\"",
      pitfalls: "Refusing to give any indication, or demanding an unrealistic number without justification.",
    },
    {
      question: "Why should we hire you over other qualified candidates?",
      category: "hr",
      star_hint: "Summarize your unique intersection: strong technical skills, rapid learning velocity, proactive ownership, and culture fit.",
      strategy: "1. Technical core fit -> 2. Proven execution velocity -> 3. High ownership mindset.",
      sample_answer: "\"You should hire me because I bring both strong full-stack technical competencies and a proactive ownership mindset. I don't just write code to specification; I actively optimize for system reliability, communicate transparently with teammates, and possess the fast learning velocity to deliver value on Day 1.\"",
      pitfalls: "Arrogance or putting down other candidates.",
    },
    {
      question: "Do you have any questions for us?",
      category: "hr",
      star_hint: "Always ask insightful questions about engineering culture, deployment frequency, onboarding, and business growth.",
      strategy: "Ask 2-3 thoughtful questions about team challenges, engineering culture, and success metrics.",
      sample_answer: "\"Yes, thank you! I'd love to ask: 1. What does a typical deployment and sprint cycle look like for this team? 2. What is the single biggest technical or scalability challenge the team is tackling this quarter? 3. How do you measure success for someone in this role during their first 90 days?\"",
      pitfalls: "Saying 'No, I don't have any questions' (signals lack of interest).",
    },
  ],
};

function QuestionCard({
  q,
  index,
  role,
}: {
  q: InterviewQuestion;
  index: number;
  role: string;
}) {
  const [expanded, setExpanded] = useState(false);

  const isTechnical = q.category === "technical";
  const isManagerial = q.category === "managerial" || q.category === "project_defense";

  const badgeStyle = isTechnical
    ? "bg-signal-500/10 text-signal-700 border-signal-500/20"
    : isManagerial
    ? "bg-purple-500/10 text-purple-700 border-purple-500/20"
    : "bg-amber-500/10 text-amber-700 border-amber-500/20";

  const roundName = isTechnical
    ? "Technical Round"
    : isManagerial
    ? "Managerial Round"
    : "HR & Culture Round";

  return (
    <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs transition-shadow hover:shadow-md">
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider border ${badgeStyle}`}>
            {roundName}
          </span>
          <span className="text-[11px] text-ink-400 font-mono">Q{index + 1}</span>
        </div>
        <span className="text-xs text-ink-500 font-medium">{role}</span>
      </div>

      <h3 className="text-sm font-semibold text-ink-900 mb-2 leading-relaxed">
        {q.question}
      </h3>

      {q.star_hint && (
        <div className="rounded-lg bg-ink-50/80 p-3 mb-3 border border-ink-100/60">
          <p className="text-xs font-semibold text-ink-700 mb-0.5 flex items-center gap-1.5">
            <Sparkles size={12} className="text-signal-600" /> Focus Strategy:
          </p>
          <p className="text-xs text-ink-600 leading-relaxed">{q.star_hint}</p>
        </div>
      )}

      {/* Generate Answer & Strategy Button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3.5 py-2 rounded-lg bg-ink-50 hover:bg-ink-100 text-ink-800 text-xs font-semibold transition-colors mt-2"
      >
        <span className="flex items-center gap-1.5">
          <Lightbulb size={14} className="text-amber-500" />
          {expanded ? "Hide Answer Strategy & Approach" : "💡 How to Answer & Sample Model Response"}
        </span>
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-ink-100 space-y-3 text-xs animate-fade-in-up">
          {q.strategy && (
            <div className="p-3 bg-signal-500/5 border border-signal-500/20 rounded-lg">
              <p className="font-bold text-signal-800 uppercase tracking-wider text-[11px] mb-1 flex items-center gap-1">
                🎯 Structured Attempt Strategy:
              </p>
              <p className="text-ink-700 leading-relaxed font-sans">{q.strategy}</p>
            </div>
          )}

          {q.sample_answer && (
            <div className="p-3 bg-ink-50 rounded-lg border border-ink-100">
              <p className="font-bold text-ink-900 uppercase tracking-wider text-[11px] mb-1 flex items-center gap-1">
                💬 Sample Model Response:
              </p>
              <p className="text-ink-700 leading-relaxed italic font-sans">{q.sample_answer}</p>
            </div>
          )}

          {q.pitfalls && (
            <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
              <p className="font-bold text-amber-800 uppercase tracking-wider text-[11px] mb-1 flex items-center gap-1">
                <AlertTriangle size={12} className="text-amber-600" /> Key Pitfall to Avoid:
              </p>
              <p className="text-amber-900/90 leading-relaxed">{q.pitfalls}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function Interview() {
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });

  const defaultRole = profile?.target_roles?.[0] || "Full Stack Developer";
  const [selectedRole, setSelectedRole] = useState<string>(defaultRole);
  const [customRoleInput, setCustomRoleInput] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"technical" | "managerial" | "hr">("technical");

  const effectiveRole = customRoleInput || selectedRole || defaultRole;

  // Use Top 20 Questions for the active round
  const currentQuestions = useMemo(() => {
    return STANDARD_ROUND_QUESTIONS[activeTab] || STANDARD_ROUND_QUESTIONS.technical;
  }, [activeTab]);

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <MessageCircleQuestion size={24} className="text-signal-600" />
          <h1 className="font-display text-2xl text-ink-900">Interview Preparation</h1>
        </div>
        <p className="text-ink-500 text-sm">
          Master the Top 20 standard, essential interview questions for each round, complete with structured attempt strategies, sample answers, and free mock interview practice links.
        </p>
      </div>

      {/* Target Role Confirmation Card */}
      <div className="bg-white rounded-xl border border-ink-100 p-5 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold uppercase tracking-wider text-ink-800 flex items-center gap-1.5">
            <Target size={14} className="text-signal-600" /> Target Job Role:
          </label>
          <span className="text-xs font-semibold text-signal-700 bg-signal-500/10 px-2.5 py-0.5 rounded-full">
            Active: {effectiveRole}
          </span>
        </div>

        {/* Quick select role pills */}
        <div className="flex flex-wrap gap-1.5">
          {TARGET_ROLE_OPTIONS.map((r) => {
            const isSelected = selectedRole.toLowerCase() === r.toLowerCase() && !customRoleInput;
            return (
              <button
                key={r}
                onClick={() => {
                  setSelectedRole(r);
                  setCustomRoleInput("");
                }}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  isSelected
                    ? "bg-ink-950 text-white shadow-xs"
                    : "bg-ink-50 text-ink-700 hover:bg-ink-100"
                }`}
              >
                {r}
              </button>
            );
          })}
        </div>

        <div>
          <input
            value={customRoleInput}
            onChange={(e) => {
              setCustomRoleInput(e.target.value);
              setSelectedRole("");
            }}
            placeholder="Or type any specific job role (e.g. Mobile Engineer, Cloud Architect)…"
            className="w-full rounded-lg border border-ink-100 px-3.5 py-2 text-xs outline-none focus:border-signal-500 shadow-2xs"
          />
        </div>
      </div>

      {/* Categorized Round Tabs (Technical, Managerial, HR) */}
      <div className="flex border-b border-ink-100 gap-2 pb-1">
        <button
          onClick={() => setActiveTab("technical")}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-all flex items-center gap-1.5 ${
            activeTab === "technical"
              ? "border-b-2 border-signal-600 text-signal-700 bg-signal-500/5 shadow-2xs"
              : "text-ink-500 hover:text-ink-800"
          }`}
        >
          <Code2 size={14} /> 💻 Technical Round (Top 20)
        </button>
        <button
          onClick={() => setActiveTab("managerial")}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-all flex items-center gap-1.5 ${
            activeTab === "managerial"
              ? "border-b-2 border-purple-600 text-purple-700 bg-purple-500/5 shadow-2xs"
              : "text-ink-500 hover:text-ink-800"
          }`}
        >
          <Users size={14} /> 👔 Managerial Round (Top 20)
        </button>
        <button
          onClick={() => setActiveTab("hr")}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-all flex items-center gap-1.5 ${
            activeTab === "hr"
              ? "border-b-2 border-amber-600 text-amber-700 bg-amber-500/5 shadow-2xs"
              : "text-ink-500 hover:text-ink-800"
          }`}
        >
          <Briefcase size={14} /> 🤝 HR & Culture Round (Top 20)
        </button>
      </div>

      {/* Round Header Summary */}
      <div className="flex items-center justify-between px-1 text-xs text-ink-500">
        <span>
          Showing <strong>{currentQuestions.length} essential questions</strong> for {activeTab.toUpperCase()} ROUND
        </span>
        <span className="text-[11px] font-semibold text-signal-700">All Answers & Strategies Included ✓</span>
      </div>

      {/* Question Cards List */}
      <div className="space-y-4">
        {currentQuestions.map((q, idx) => (
          <QuestionCard key={idx} q={q} index={idx} role={effectiveRole} />
        ))}
      </div>

      {/* Free Mock Interview Practice Platforms */}
      <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
        <h3 className="font-display text-base text-ink-900 mb-1 flex items-center gap-2">
          <Video size={18} className="text-signal-600" /> Free Mock Interview Practice Platforms
        </h3>
        <p className="text-xs text-ink-500 mb-4">
          Practice live technical coding and behavioral mock interviews for free with peer candidates and engineers.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {MOCK_PLATFORMS.map((plat) => (
            <a
              key={plat.name}
              href={plat.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-3.5 rounded-lg border border-ink-100 bg-ink-50/40 hover:bg-white hover:border-signal-500 hover:shadow-xs transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-xs text-ink-900 group-hover:text-signal-700">{plat.name}</span>
                  <span className="text-[10px] font-semibold text-signal-700 bg-signal-500/10 px-2 py-0.5 rounded-full">
                    {plat.tag}
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">{plat.desc}</p>
              </div>
              <span className="text-[11px] font-semibold text-signal-600 mt-2 flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                Practice on {plat.name} <ExternalLink size={10} />
              </span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
