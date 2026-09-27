# Coding Conventions

**Analysis Date:** 2026-09-16

## Code Style

- **Python (PEP 8 Compliant):**
  - Type hints are strictly used across all function signatures and data structures (`str | None`, `list[dict]`, `dict[str, Any]`).
  - Runtime validation using Pydantic v2 `BaseModel` for all request and response boundaries.
  - Double quotes for docstrings and standard string literals.
  - Logging via standard library `logging.getLogger(__name__)` with informative structured messages.
- **TypeScript & React:**
  - Strict TypeScript configuration (`noImplicitAny`, typed props, interface declarations).
  - Functional React components with hooks (`useState`, `useEffect`, `useMemo`, `useCallback`).
  - React Query (`@tanstack/react-query`) for remote server-state handling.
  - Tailwind utility classes combined with custom CSS tokens for design consistency.

---

## Naming Conventions

- **Models & Schemas:**
  - Pydantic models: `CreateCustomJobRequest`, `JobOut`, `EvidenceUnit`, `TailoringPlan`.
  - Enums: PascalCase with UPPER_CASE values (`UrlType.DIRECT_REQUISITION`, `VerificationStatus.VERIFIED_ACTIVE`).
- **Route Definitions:**
  - RESTful HTTP methods (`GET` for idempotent queries, `POST` for mutations/sync, `DELETE` for removal).
  - Explicit response models (`response_model=JobOut` or `response_model=list[JobOut]`).
- **Constants:**
  - Module-level constants in `UPPER_SNAKE_CASE` (`BASE_URL`, `GENERIC_ROLE_TOKENS`, `SENIORITY_ROLE_MODIFIERS`).

---

## Common Patterns

- **Dependency Injection in FastAPI:**
  - Database access injected via `db: AsyncIOMotorDatabase = Depends(get_db)`.
  - Application settings injected via `settings: Settings = Depends(get_settings)`.
  - Authentication injected via `current_user: dict = Depends(get_current_user)`.
- **Truth Guard Pattern:**
  - All AI-generated content (e.g. tailored bullets, resume summaries) must be cross-referenced against candidate source evidence units before persisting or returning to the client.
  - Fallback logic: If AI generation fails, returns malformed JSON, or fails Truth Guard checks, the system deterministically falls back to safe template generation with zero hallucinated technologies.
- **Resilient External Integrations:**
  - All external ATS requests are wrapped in explicit timeouts (`httpx.TimeoutException`) and try-except blocks.
  - Network failures never drop existing active database state; errors are logged, and existing records are safely retained.

---

## Error Handling

- **HTTP Status Codes:**
  - `401 Unauthorized` for missing/invalid bearer tokens.
  - `403 Forbidden` for resource ownership violations.
  - `404 Not Found` for nonexistent entities.
  - `422 Unprocessable Entity` for schema validation failures.
  - `429 Too Many Requests` when rate limits are exceeded.
- **Custom Exceptions:**
  - Domain exceptions (e.g., `AshbyProviderError`, `AshbyNetworkError`) inherit from descriptive base exceptions and are caught at service boundaries.
