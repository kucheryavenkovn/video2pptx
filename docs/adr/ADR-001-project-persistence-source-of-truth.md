# ADR-001: Project Persistence Source of Truth

## Status
Accepted, amended by Step 4.7 PersistenceContractStabilization

## Context
Phase-16 refactoring introduces a domain aggregate `Project` that must own
slide lifecycle, pipeline state, and invariants. The existing persistence
layer stores `project.json` (Pydantic model) and `slides.json` (detection
output) as two independently modifiable files with no schema version,
revision tracking, or conflict detection.

Step 4 established the initial repository foundation. Step 4.7 stabilizes
the persistence contract before application services depend on it.

## Decision
`project.json` is the **canonical source of truth** for the project
aggregate. `slides.json` is a **derived compatibility artifact** regenerated
by `FileProjectRepository.save()` on every commit.

### Schema Versioning
- `1.0` — legacy (pre-aggregate, boolean pipeline flags, no UID guarantee)
- `2.0` — aggregate persistence (revision, stable UIDs, full PipelineState, schema_version field)

Schema 2.0 is parsed through `ProjectDocumentV2`, not legacy `Project`.
Legacy `Project` is used only for reading schema 1.0 during migration.

### Conflict Policy
If `project.json` and `slides.json` disagree, `project.json` wins. The
repository regenerates `slides.json` from the aggregate snapshot on save.

`slides.json` contains `source_revision` matching the canonical revision.
If revisions differ, the derived artifact is marked stale.

### Media Path Policy
Slide images and generated outputs (`deck.md`, `deck.pptx`,
`alignment_report.json`) are stored as relative `ArtifactRef` POSIX paths
within the project directory. Source video and subtitles may be external
absolute paths; the domain model stores them as plain strings until a
future `SourceMediaRef` value object is introduced.

`output_dir` is NOT persisted in schema 2.0. Project root is a runtime
context provided by `LoadedProject.location`.

### Atomic Writes
All JSON files are written via `write_json_atomic` (temp file + `os.replace`).
If a write fails, the previous version remains intact.

The save model is: **atomic canonical commit + revisioned derived artifact**.
If `project.json` commits but `slides.json` fails, the canonical project
is valid; the derived artifact is stale and regenerated on next save.

### Revision Tracking
Each `save()` generates a UUID revision. Callers may pass
`expected_revision` for optimistic concurrency control. A mismatch raises
`ProjectRevisionConflict`.

`load()` returns `LoadedProject(project, location, revision, warnings, migrated)`.
Application services use `loaded.revision` for the subsequent save.

### Rehydration
Aggregate rehydration from persistence has NO business side effects.
`ProjectMapper.to_domain()` does NOT call `replace_detected_slides()`.
PipelineState is restored as-is without transitions or invalidation.

### Corrupt Document Handling
A corrupt existing `project.json` with `expected_revision` raises
`ProjectDocumentCorrupted`. Automatic overwrite of corrupt canonical
documents is forbidden. Recovery is a separate explicit operation.

### UID Migration
Legacy slides without UIDs receive a generated `SlideId` on first load
through the mapper. The UIDs are persisted on the next save and remain
stable across subsequent loads.

`SlideId.new()` generates a full 128-bit UUID4 (`uuid4().hex`, 32 hex chars).
Legacy 12-char UIDs are preserved as-is during migration.

### Unknown Legacy Fields
Unknown legacy fields (detection config, video config, LLM config, markers,
export settings) are preserved in `extensions.legacy` during migration.

## Consequences
- `slides.json` is no longer an independent edit target.
- GUI/MCP/CLI must route writes through the repository, not direct file I/O.
- Legacy projects are transparently upgraded on first load.
- Project directories remain portable (no absolute output paths persisted).
- Application services receive revision from load and use it for save.
