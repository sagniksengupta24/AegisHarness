---
description: "Aegis deterministic verification and safety rules for Antigravity"
trigger: always_on
globs: ["**/*"]
alwaysApply: true
---

# Aegis Deterministic Verification Rules

When working within this repository with AegisHarness:

1. **Verification Gate Invariant**:
   - A task is never complete merely because model text says "Done".
   - Completion is strictly defined as all configured verification gates passing without unresolved policy violations.
   
2. **Fail-Closed Lifecycle**:
   - The execution sequence is always: Plan → Implement → Verify → (Pass: Complete / Fail: Diagnose & Repair).
   - If repair budget is exceeded or repeated failure is detected, changes are automatically rolled back.

3. **Filesystem Boundaries**:
   - Never access, read, or modify protected files: `.git/**`, `.env*`, `secrets/**`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`.
   - Never perform path traversal outside the repository root.

4. **Preserve User Changes**:
   - Rollback is surgical: only changes introduced by the current Aegis session are reverted. Pre-existing user modifications and untracked files are preserved.
