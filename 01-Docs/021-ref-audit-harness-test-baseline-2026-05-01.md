# 021-ref-audit-harness-test-baseline-2026-05-01

**Document type**: Reference (`ref`) — testing baseline record
**Date**: 2026-05-01
**Program**: VPS-as-the-home (`OPS-5nm`), Priority 6 (`OPS-z9b`) — pilot repo

---

## What this records

This repo received the **Intent Solutions Testing SOP baseline** as the pilot pass of P6 (per-repo SOPS+age + audit-tests rollout).

## What got installed

| Artifact | Location | Purpose |
|---|---|---|
| `@intentsolutions/audit-harness v0.1.0` (vendored) | `.audit-harness/` | Deterministic test-enforcement scripts — hash-pinning, escape-scan, CRAP, architecture, bias, Gherkin lint |
| Wrapper | `scripts/audit-harness` | Single CLI entry point (dispatches to vendored scripts) |

Install command used:
```bash
curl -sSL https://raw.githubusercontent.com/jeremylongshore/audit-harness/main/install.sh | bash
```

The harness is **vendored, not installed via package manager**, because this repo has no Node `package.json` and the IS Testing SOP requires the enforcement to travel with the code (no `~/.claude/` paths from hooks or CI).

## What did NOT happen yet (deferred)

- `/audit-tests` skill has not been run yet → no `TEST_AUDIT.md` produced
- `tests/TESTING.md` policy file not authored → no coverage / mutation / CRAP thresholds
- No pre-commit hook wiring → `scripts/audit-harness escape-scan --staged` not yet invoked at commit time
- No CI gate wiring → harness verify/escape-scan not yet enforced in GitHub Actions
- Smoke-endpoint contract for VPS-deploy gate (Priority 7) not yet defined

These follow in subsequent sessions per the IS Testing SOP. The harness install is the precondition; engineer-policy authorship + CI wiring is the next step.

## Cross-references

- Program plan: `~/000-projects/intentsolutions-vps-runbook/plans/2026-05-01-vps-as-the-home/00-plan.md` § Priority 6
- Repo baseline tracker: `~/000-projects/intentsolutions-vps-runbook/docs/repo-baseline-tracker.md`
- IS Testing SOP: `~/000-projects/CLAUDE.md` § "Intent Solutions Testing SOP" + global `~/.claude/CLAUDE.md`
- Bead: `OPS-z9b` (P6) — this repo logged as pilot
- Harness package: `https://github.com/jeremylongshore/audit-harness`

## Why this repo was the pilot

From the inventory pass on 2026-05-01:
- Branch clean (no uncommitted dev work to disturb)
- SOPS-OK already (4-file pattern present from earlier "Adopt SOPS+age secrets standard" commit)
- Has a real `tests/` directory (audit-tests has something to grade later)
- Python project with `requirements.txt` + Docker — vendored install path is the correct one
- Real codebase (not a markdown skill repo, not an OSS-fork umbrella)

Six of the seven SOPS-OK candidates were either pure-markdown skill repos, fork umbrellas, or had dirty working trees. This repo was the cleanest viable pilot.
