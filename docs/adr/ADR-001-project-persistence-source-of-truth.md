# ADR-001: Project Persistence Source of Truth

## Status
Accepted

## Context
Phase-16 refactoring introduces a domain aggregate `Project` that must own
slide lifecycle, pipeline state, and invariants. The existing persistence
layer stores `project.json` (Pydantic model) and `slides.json` (detection
output) as two independently modifiable files with no schema version,
revision tracking, or conflict detection.

## Decision
`project.json` is the **canonical source of truth** for the project
aggregate. `slides.json` is a **derived compatibility artifact** regenerated
by `FileProjectRepository.save()` on every commit.

### Schema Versioning
- `1.0` — legacy (pre-aggregate, boolean pipeline flags, no UID guarantee)
- `2.0` — aggregate persistence (revision, stable UIDs, schema_version field)

### Conflict Policy
If `project.json` and `slides.json` disagree, `project.json` wins. The
repository regenerates `slides.json` from the aggregate snapshot on save.

### Media Path Policy
Slide images and generated outputs (`deck.md`, `deck.pptx`,
`alignment_report.json`) are stored as relative `ArtifactRef` POSIX paths
within the project directory. Source video and subtitles may be external
absolute paths; the domain model stores them as plain strings until a
future `SourceMediaRef` value object is introduced.

### Atomic Writes
All JSON files are written via `write_json_atomic` (temp file + `os.replace`).
If a write fails, the previous version remains intact.

### Revision Tracking
Each `save()` generates a UUID revision. Callers may pass
`expected_revision` for optimistic concurrency control. A mismatch raises
`ProjectRevisionConflict`.

### UID Migration
Legacy slides without UIDs receive a generated `SlideId` on first load
through the mapper. The UIDs are persisted on the next save and remain
stable across subsequent loads.

## Consequences
- `slides.json` is no longer an independent edit target.
- GUI/MCP/CLI must route writes through the repository, not direct file I/O.
- Legacy projects are transparently upgraded on first load.
- Project directories remain portable (no absolute output paths persisted).
