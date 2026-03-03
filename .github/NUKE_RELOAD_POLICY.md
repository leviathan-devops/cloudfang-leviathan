# Nuke-Reload Policy — Leviathan DevOps

## CRITICAL: Read Before Any Cross-Repo Push

### The Incident (2026-03-01)
A nuke-reload pushed Python code from cloudfang-leviathan to the openfang repo,
deleting 202,096 lines of Rust kernel code. All 5 Leviathan agents went down.

### New Rules (Effective 2026-03-03)
1. NEVER push to openfang or openfang-kernel-recovered without human review
2. ALWAYS run scripts/deploy-safety-check.sh before cross-repo pushes
3. ALWAYS create a backup branch on the target repo first
4. NEVER use --force or --mirror without explicit owner authorization
5. Standing Order #18: OPENFANG KERNEL IS SACRED
6. All nuke-reload operations must be logged in #infrastructure-changelog

### Safe Repos for Nuke-Reload
- cloudfang-leviathan: SAFE (testing sandbox)
- super-brain: REQUIRES OWNER AUTHORIZATION
- openfang: BLOCKED (kernel protection)
- openfang-kernel-recovered: BLOCKED (5-layer protection)

### Usage
Always use scripts/safe-nuke-reload.sh instead of raw git push --force.
Start with --dry-run to preview changes.
