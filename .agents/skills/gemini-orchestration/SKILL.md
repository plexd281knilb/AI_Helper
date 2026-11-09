---
name: gemini-orchestration
description: Multi-tier Gemini subagent orchestration guide for Portalarr. Establishes the 4-layer hierarchy (L1 Deep Architect on Argon 4 with Flash 3.8 fallback, L2 Parallel Researchers, L3 Execution Worker, L4 QA Verifier), root Gemini 3.8 Flash session operation, strict Gemini-only models, and quota preservation rules.
---

# Multi-Tier Gemini Subagent Orchestration Architecture

Portalarr leverages a strict, multi-tiered Google Gemini subagent architecture designed to maximize execution speed, eliminate quota exhaustion, prevent SQLite lockups, and ensure 100% code correctness.

## 🌟 Core Philosophy: "Flash as Daily Driver, Argon on Escalation"

- **Root Session:** Locked to **Gemini 3.8 Flash (High)** by default. This delivers near-instant response times, handles 95%+ of daily tasks, and keeps conversational turns lightweight and cost-effective.
- **Escalation Layer (Argon 4 / Pro):** Called **only when deeply needed** for high-complexity system architecture, database migrations, security isolation models, or difficult algorithmic puzzles.
- **Quota Fallback:** If Gemini 4 Argon runs out of usage (HTTP 429 / resource exhausted), execution **automatically falls back to Gemini 3.8 Flash** without interruption.
- **Strict Model Rule:** **ONLY Google Gemini models** are used throughout Portalarr (`gemini-4-argon-high`, `gemini-3.8-flash-high`, and `gemini-3.5-flash-lite`). Third-party models are forbidden.

---

## 🏛️ The 4-Layer Subagent Hierarchy

```
                   ┌────────────────────────────────────────┐
                   │        Root Orchestrator / User        │
                   │      (Gemini 3.8 Flash - Default)      │
                   └──────────────────┬─────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│ L1: Architect    │        │ L2: Researchers  │        │ L3: Execution    │
│ (Argon 4 / Pro)  │        │ (Flash 3.8/Lite) │        │ (Flash 3.8)      │
│ Fallback: Flash  │        │ (1-3 in parallel)│        │ (Pinky Worker)   │
└──────────────────┘        └──────────────────┘        └─────────┬────────┘
                                                                  │
                                                        ┌─────────┴────────┐
                                                        ▼                  ▼
                                                  npm test            npm run build
                                                        │                  │
                                                        └─────────┬────────┘
                                                                  ▼
                                                        ┌──────────────────┐
                                                        │ L4: QA Verifier  │
                                                        │ (Flash Lite)     │
                                                        │ Route / Git / DB │
                                                        └──────────────────┘
```

### Layer 1: Deep Architect (`deep-architect`)
- **Primary Model:** Gemini 4 Argon / Pro (`Model: "pro"`).
- **Fallback Model:** Gemini 3.8 Flash (`Model: "flash"`).
- **When to Invoke:**
  - Redesigning database schemas (`prisma/schema.prisma`).
  - Edge security architecture and Cloudflare proxy gate restructuring.
  - Designing brand-new subsystem integrations (e.g. new curation studios, billing gateways).
  - Diagnosing complex, intermittent race conditions.
- **When NOT to Invoke:**
  - Simple bug fixes, UI styling, adding buttons, updating text, or running tests.
- **Tools:** Read tools + subagent tools (cannot directly write files or run bash loops).

### Layer 2: Fast Parallel Researchers (`repo-researcher`)
- **Primary Model:** Gemini 3.8 Flash (`Model: "flash"`).
- **Light Alternative:** Gemini 3.5 Flash Lite (`Model: "flash_lite"`).
- **Concurrency:** Can launch 2–3 in parallel safely.
- **When to Invoke:**
  - Auditing multiple disparate modules simultaneously (e.g. Plex API + Seerr requests + Discord bot).
  - Tracing imports and verifying API signatures.
  - Gathering facts across documentation and skills.
- **Tools:** Strictly read-only (`view_file`, `search_web`, `read_url_content`). No file modifications.

### Layer 3: Autonomous Execution Worker (`execution-worker` / `pinky`)
- **Model:** Gemini 3.8 Flash (`Model: "flash"`).
- **Concurrency:** **STRICTLY 1 WORKER AT A TIME** for active coding and test runs.
- **Why Single-Threaded Execution:**
  - Prevents SQLite database write locks (`SQLITE_BUSY: database is locked`).
  - Prevents Next.js Turbopack cache corruption (`.next/` race conditions).
  - Avoids file collision and conflicting line replacements in `src/app/actions.ts`.
- **Self-Healing Protocol:**
  1. Applies precise code edits.
  2. Runs `cmd /c "npm test"`. If tests fail, diagnoses the stack trace, applies corrections, and reruns until 100% pass.
  3. Runs `cmd /c "npm run build"`. Verifies zero Turbopack/TypeScript errors.
  4. Returns a crisp, 10-line summary to the caller.

### Layer 4: Quality & Route Security Verifier (`qa-verifier`)
- **Primary Model:** Gemini 3.5 Flash Lite (`Model: "flash_lite"`).
- **Secondary Model:** Gemini 3.8 Flash (`Model: "flash"`).
- **When to Invoke:**
  - Auditing `src/proxy.ts` and `CLOUDFLARE_ADMIN_PATHS` to ensure any newly added API routes or pages are gated.
  - Checking `git status` for untracked files or leftover scratch artifacts.
  - Verifying SemVer version bumps in `package.json` and git commit hook compatibility.

---

## 🔔 Proactive User Model-Switching Notification Rule (Mandatory)

Because the root chat UI model selector directly controls whether turns consume **Gemini 4 Argon** quota or **Gemini 3.8 Flash** quota, ALWAYS notify the user when to toggle between models:
- **Switch TO Argon 4.0**: Recommend switching to **Gemini 4 Argon** before laying out new subsystem architectures, complex Prisma schema migrations, or deep security/algorithmic designs.
- **Switch BACK to Flash 3.8**: Immediately notify the user to switch back to **Gemini 3.8 Flash** as soon as the Argon architectural/backend foundation is complete—before writing large React UI pages, running `npm test`, or running `npm run build`.

---

## ⚡ Quota Depletion & Graceful Fallback Protocol

When calling Layer 1 (`deep-architect`) with `Model: "pro"`:
1. **Detection:** If the API returns a rate limit (HTTP 429), quota exhaustion, or timeout error:
2. **Immediate Fallback:** Do NOT crash or ask the user for a new key. Immediately invoke or delegate to `deep-architect` with `Model: "flash"` (Gemini 3.8 Flash High).
3. **Prompt Adaptation:** When falling back to Flash, provide structured scaffolding:
   - Provide explicit file paths.
   - Enforce step-by-step reasoning: "Step 1: Analyze schema impact. Step 2: Formulate interface. Step 3: Output plan."
   - Gemini 3.8 Flash achieves near-Argon architectural accuracy when guided with structured technical constraints.

---

## 🛠️ VS Code Tasks Integration

Located in [`.vscode/tasks.json`](file:///C:/Users/kyraj/Documents/Github/portalarr/.vscode/tasks.json):
- `agy: Root Orchestrator (Gemini 3.8 Flash High - Default)`: Runs `agy --model gemini-3.8-flash-high`.
- `agy: Deep Architect (Gemini 4 Argon High - Escalation)`: Runs `agy --model gemini-4-argon-high`.
- `agy: Fallback Architect (Gemini 3.8 Flash High - Quota Fallback)`: Runs `agy --model gemini-3.8-flash-high`.
- `agy: Parallel Worker / Pinky (Gemini 3.8 Flash High)`: Runs `agy --model gemini-3.8-flash-high`.
- `agy: Quick Task on Flash (Print Mode)`: Runs `agy --model gemini-3.8-flash-high --print "<prompt>"`.
- `agy: Light Recon & Search (Gemini 3.5 Flash Lite)`: Runs `agy --model gemini-3.5-flash-lite --print "<prompt>"`.
- `Portalarr: Run Integration Tests`: Runs `npm test`.
- `Portalarr: Production Build`: Runs `npm run build`.

---

## 🚨 Mandatory Task Completion Protocol (Strict SemVer)

To guarantee 100% reliability, quality control, and consistency, the following protocol MUST be executed across all agent turns:

### Step 0: Read Skill Upfront (Task Start)
Before editing or creating ANY files, call `read_file` on the relevant `.agents/skills/<skill>/SKILL.md` (e.g. `plex-api-expert`, `iptv-expert`, `portalarr-ui`, etc.) to load all architectural rules, API contracts, and edge cases into context. Never code on assumptions.

### The 5-Step Pre-Push Verification Battery
1. **Step 1: Integration Testing**: Execute `cmd /c "npm test"` (`scripts/verify-all.ts`). All test suites must pass (0 failures).
2. **Step 2: Production Build Verification**: Execute `cmd /c "npm run build"`. Ensure 100% clean compilation, zero TypeScript errors, and zero Turbopack runtime errors.
3. **Step 3: Edge Security & Cloudflare Policy Audit**: Whenever ANY page route (`src/app/**/page.tsx`) or API route (`src/app/api/**/route.ts`) is created, moved, or updated, register it in `src/lib/edge-policy-paths.ts` and inform the user.
4. **Step 4: Skills & Documentation Sync**: Review and update relevant `.agents/skills/` documents to record any new UI patterns, API contracts, formulas, or operational guidelines **BEFORE** committing.
5. **Step 5: SemVer Version Increment & Git Deployment Push**: Increment version in `package.json` according to SemVer (PATCH `+1` for fixes/polish, MINOR `+1` for features), stage all changes (`git add -A`), commit with freshly incremented semantic version prefix (`[v<version>] feat/fix(scope): message`), push strictly to `origin/main` (Beta). NEVER push to `stable` unless the user explicitly instructs.

---

### 🛑 Mandatory Extended Build Verification for Stable Releases (`npm run test:extended`)

Whenever merging or pushing to the `stable` branch (production release environment), you MUST execute the 7-tier Extended Build Verification suite via `cmd /c "npm run test:extended"` (`scripts/verify-extended.ts`). Pushing to `stable` is strictly blocked unless all 7 tiers are 100% green:
1. **Tier 1: Strict TypeScript Type Integrity (`npx tsc --noEmit`)**: Validates complete type safety with zero compiler errors across the entire codebase.
2. **Tier 2: Curation Presets & Schedule Validator (`scripts/test-all-presets.ts`)**: Audits all 49 curation presets, seasonal date ranges, and TMDb query definitions.
3. **Tier 3: AI Server Assistant & Security Guardrails (`scripts/test-ai-agent.ts`)**: Audits all 30 security guardrails, cross-user stream termination blocks, query extraction, and diagnostic tools.
4. **Tier 4: Payment Scraper Lookback & Financial Engine (`scripts/test-payment-lookback.ts`)**: Audits payment parsing, lookback retention, and settings synchronization (12 assertions).
5. **Tier 5: Plex User Matching & Identity Resolution (`scripts/test-plex-lookup.ts`)**: Audits identity collision guards, alphanumeric tokens, and user aliases (7 assertions).
6. **Tier 6: Core System & Architecture 22-Suite Battery (`scripts/verify-all.ts`)**: Full 22 integration suites (79 core assertions) covering DB schema, encryption, Cloudflare Access coverage, user accounts, Plex sync, billing, and subscriptions.
7. **Tier 7: Production Turbopack Next.js Build (`next build`)**: 100% clean production compilation across all 42 static and dynamic routes.
