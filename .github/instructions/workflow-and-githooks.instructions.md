# Workflow and Git Hooks Strategy

## Overview

This project uses a **two-level quality assurance approach**:

1. **Local Pre-commit Hooks** (`.githooks/pre-commit`) — Fast, immediate feedback
2. **GitHub Actions Workflows** (`wrapup` and `ready`) — Safety net and CI enforcement

Both use the same validation script (`.scripts/trunk-worthy`) to ensure consistency.

---

## Why This Approach?

### The Problem with "CI-Only" Validation

Traditional CI-first workflows have become the norm, but they have significant downsides:

**Slow Feedback Loop:**

- Developer commits code
- Waits 30-40+ seconds for GitHub Actions runner to boot, install dependencies, run checks
- Discovers failures only after pushing to remote
- Rinse and repeat with incremental fixes

**Wasted Developer Time:**

- Multiple failed commits = 2-3 minutes of CI waits
- Developers context-switch while waiting
- Momentum is lost

**Cost:**

- GitHub Actions minutes add up
- Every failed CI run is wasted compute

### The Git Hooks Solution

**Immediate Feedback (1.5 seconds):**

- Run checks **before** committing
- Problems caught instantly
- No remote push, no CI wait
- Developer stays in flow

**Example Timeline:**

| Approach | Time | Experience |
|----------|------|------------|
| CI-only | Commit → 38s wait → Discover failure → Fix → Commit → 38s wait | 76s total, frustrating |
| Git Hooks | Write code → 1.5s check → Pass → Commit → Push | 1.5s, satisfying |

---

## How It Works

### 1. Local Pre-commit Hook

```bash
# .githooks/pre-commit
#!/bin/bash
source ./.scripts/trunk-worthy
```

**Setup:**

```bash
git config core.hooksPath .githooks
```

This tells Git to use hooks from `.githooks/` instead of `.git/hooks/`.

**When it runs:**

- Every time you try to `git commit`
- If any check fails, the commit is blocked
- You see the problem immediately, fix it, retry

**Time cost:** ~1.5 seconds per commit (overhead of running checks)

### 2. Wrapup Workflow

Triggered when you push to an issue branch (e.g., `123-feature-name`):

```yaml
jobs:
  trunk-worthy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v6
      - name: Set up runner environment
        uses: ./.github/actions/prep-runner
      - name: Run trunk-worthy
        run: ./.scripts/trunk-worthy
```

**Purpose:** Catch anything that slipped through locally (rare, but possible)

**Time:** 38 seconds (mostly environment setup)

### 3. Ready Workflow

Triggered when you create a `ready/*` branch (from `gh tt deliver`):

```yaml
jobs:
  trunk-worthy:
    # Blocks merge to main unless all checks pass
  mark-trunk-worthy:
    # Sets GitHub status check
  merge-to-trunk:
    # Auto-merges to main
```

**Purpose:** Final safety net before code reaches production branch

**Philosophy:** "You can't merge to main without passing checks"

---

## The Script: `.scripts/trunk-worthy`

Definitive source of truth for what gets checked.

Configured in one place (the script), used in two contexts:

- Locally (pre-commit hook) — instant feedback
- CI (wrapup/ready workflows) — safety net

**Key advantage:** If you change what to check, it changes everywhere automatically.

### Checks Run (In Parallel)

```bash
CHECK_NAMES=("cspell" "markdownlint" "prettier" "format-check" "lint" "test")
```

**Duration:** ~1.5s locally (all in parallel)

**Why parallel?** Because these checks don't depend on each other. Running them sequentially would be 3x slower.

---

## Workflow: Complete Picture

```
Developer         Local Git Hook         GitHub Actions
─────────────────────────────────────────────────────────────

Code changes                                    
     ↓                                          
  git commit ──→ .githooks/pre-commit  
     ↓           (1.5s check)                   
  Pass? ─────→ Commit created
     ↓
  git push ────────────────────→ wrapup.yml runs
                                (38s, optional safety net)
                                     ↓
                                  gh tt deliver
                                     ↓
                         ready/* branch created
                                     ↓
                              ready.yml runs
                                (sets status check)
                                     ↓
                         Auto-merge to main (if pass)
```

---

## Configuration

### Enable Git Hooks Locally

After cloning:

```bash
git config core.hooksPath .githooks
```

Or add to your git config globally:

```bash
git config --global core.hooksPath .githooks
```

### Disable a Check Temporarily

Edit `.scripts/trunk-worthy`:

```bash
# Comment out the check name
# CHECK_NAMES=("cspell" "markdownlint" "prettier" "format-check" "lint" "test")
CHECK_NAMES=("format-check" "lint" "test")  # Skip linting tools
```

### Bypass Pre-commit Hook (Not Recommended)

```bash
git commit --no-verify  # Skips pre-commit hook
```

Use only when absolutely necessary (e.g., emergency hotfix). The hook exists for a reason.

---

## Why This Matters

### For Development

1. **Stay in Flow** — 1.5s feedback vs. 38s+ CI wait
2. **Fewer Mistakes** — Catch issues before they're recorded in git history
3. **Confidence** — Code that passes locally will pass CI (same checks)
4. **Respect for CI** — Don't waste compute resources on preventable failures

### For CI/CD

1. **Safety Net** — Catches the 1% of issues that slip through
2. **Documentation** — Workflow is explicit and reproducible
3. **Consistency** — Same checks run everywhere (devcontainer, local, CI)
4. **Parallel Execution** — Checks run in parallel, not sequentially

---

## Philosophy: "Fail Fast, Fail Locally"

This approach embodies the principle:

> **Problems should be caught at the earliest point possible, by the person who introduced them, with the fastest possible feedback loop.**

- **Earliest point:** Before the commit exists
- **By the person:** Developer, not CI system seeing it later
- **Fastest feedback:** 1.5 seconds, not 38 seconds

This shifts quality left and keeps developers happy.

---

## Related Files

- [web-scraper-rag-tool.instructions.md](web-scraper-rag-tool.instructions.md) — Project-specific setup
- [../copilot-instructions.md](../copilot-instructions.md) — Python development conventions
- `.scripts/trunk-worthy` — The check runner (orchestrates all validations)
- `.githooks/pre-commit` — Entry point for local checks
- `.github/workflows/wrapup.yml` — Push branch validation
- `.github/workflows/ready.yml` — Ready-to-merge validation

---

## Footnote: Why Developers Forget About Git Hooks

Git hooks have become less visible since CI systems (GitHub Actions, CircleCI, etc.) took over quality enforcement. But hooks are **still valuable** because they're faster and give immediate feedback. They're not a replacement for CI — they're a **complement**.

The best projects use both:

- **Git hooks** for speed and developer experience
- **CI** for consistency and safety net

This project does exactly that. 🚀
