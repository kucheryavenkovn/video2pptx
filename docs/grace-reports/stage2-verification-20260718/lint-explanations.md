# Stage 2 — Lint Explanations

Source: `grace lint --explain <code>` (GRACE CLI v3.11.0)

## Verification coverage scope codes

### autonomy.verification-missing-observable-evidence
- **Title:** Verification Missing Observable Evidence
- **Explanation:** A V-M entry should require log markers or trace assertions so failures can be debugged without hidden reasoning.
- **Remediation:**
  - Add `required-log-markers` or `required-trace-assertions` to the V-M entry.
  - Keep markers stable and map them back to semantic blocks.

### autonomy.verification-missing-wave-follow-up
- **Title:** Autonomy Readiness Gate Failure
- **Explanation:** The project is missing one of the packet, verification, or evidence guarantees needed for long autonomous execution.
- **Remediation:** Strengthen `docs/verification-plan.xml` (`<wave-checks>` block).

### autonomy.verification-missing-phase-follow-up
- **Title:** Autonomy Readiness Gate Failure
- **Explanation:** The project is missing one of the packet, verification, or evidence guarantees needed for long autonomous execution.
- **Remediation:** Strengthen `docs/verification-plan.xml` (`<phase-checks>` block).

### autonomy.module-missing-verification
- **Title:** Module Missing Verification Entry
- **Explanation:** Each shared module needs a matching V-M entry before autonomous execution can treat it as governed and observable.
- **Remediation:**
  - Add a V-M entry for the module in `docs/verification-plan.xml`.
  - Run `$grace-verification` for the affected module or phase.

### autonomy.module-missing-implementation-files
- **Title:** Module Missing Implementation Files
- **Explanation:** A module cannot be autonomy-ready if it has no linked non-test governed runtime files.
- **Remediation:**
  - Implement the module via `$grace-execute` or `$grace-multiagent-execute`.
  - Link the runtime file to the module through LINKS in MODULE_CONTRACT.

### autonomy.verification-missing-module-checks
- **Title:** Verification Missing Module Checks
- **Explanation:** A V-M entry needs executable commands so workers and CI can run the intended checks directly.
- **Remediation:** Add `<module-checks>` commands to the V-M entry.

### autonomy.verification-missing-scenarios
- **Title:** Verification Missing Scenarios
- **Explanation:** Autonomous execution needs named success and failure behavior, not only file paths or commands.
- **Remediation:** Add success and failure `<scenarios>` to the V-M entry.

### autonomy.verification-test-file-unlinked-module
- **Title:** Verification Test File Not Linked To Module
- **Explanation:** A governed test file should belong to the same module it verifies so agents can navigate ownership precisely.
- **Remediation:**
  - Add the module ID to LINKS in the test file MODULE_CONTRACT.
  - Or update the V-M entry to point at a test file that belongs to the module.

### autonomy.verification-module-check-does-not-reference-test-file
- **Title:** Module Check Does Not Reference Test File
- **Explanation:** The verification commands do not clearly mention the declared test file or its containing directory.
- **Remediation:**
  - Make at least one module-check reference the test file path or its directory.
  - Keep the commands and declared test-files aligned.

### autonomy.verification-missing-test-files
- **Title:** Verification Missing Test Files
- **Explanation:** A verification entry without test files is not actionable for worker loops or CI.
- **Remediation:** Add one or more `<test-files>` entries to the V-M record.

### autonomy.verification-test-file-missing-on-disk
- **Title:** Verification References Missing Test File
- **Explanation:** The verification plan references a test file that does not currently exist on disk.
- **Remediation:**
  - Create the test file or update the V-M entry to the real path.
  - Keep `docs/verification-plan.xml` synchronized with the codebase.

### autonomy.step-missing-verification
- **Title:** Plan Step Missing Verification Ref
- **Explanation:** Execution steps should name the verification gate they depend on so agents do not improvise success criteria.
- **Remediation:**
  - Add `verification="V-M-..."` to the step in `docs/development-plan.xml`.
  - Make sure the referenced V-M entry exists in `docs/verification-plan.xml`.

## Structural codes (out of Stage 2 scope, recorded for reference)

### graph.module-missing-from-plan
- Structural inconsistency between knowledge-graph.xml and development-plan.xml.
- **Stage 2 policy:** Do not address — that belongs to structural repair, not verification coverage. Kept as-is.
