# Architecture — video2pptx

## Context diagram

```
┌─────────────────────┐     ┌──────────────────────┐
│     User (CLI)      │     │  User (GUI Desktop)  │
│   video2pptx detect │     │  PySide6 QMainWindow │
└────────┬────────────┘     └──────────┬───────────┘
         │                             │
         ▼                             ▼
┌─────────────────────────────────────────────┐
│              Adapters Layer                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │   CLI    │  │   GUI    │  │   MCP     │  │
│  │  Typer   │  │ Qt Ctrl  │  │ JSON-RPC  │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  │
└───────┼──────────────┼──────────────┼────────┘
        │              │              │
        ▼              ▼              ▼
┌─────────────────────────────────────────────┐
│           Application Layer                  │
│  ┌────────┐ ┌────────┐ ┌──────────────────┐  │
│  │Commands │ │Services│ │     DTOs        │  │
│  │ UseCase │ │ UseCase│ │  Command/Result  │  │
│  └────┬───┘ └───┬────┘ └──────────────────┘  │
└───────┼──────────┼────────────────────────────┘
        │          │
        ▼          ▼
┌─────────────────────────────────────────────┐
│              Ports (Protocols)               │
│  Repo │ Video │ Subs │ Detector │ LLM │ ...  │
└───────┼──────────┼────────────────────────────┘
        │          │
        ▼          ▼
┌─────────────────────────────────────────────┐
│          Infrastructure Layer                │
│  FileRepo │ OpenCV │ PyAV │ python-pptx │   │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│           Domain Layer                       │
│  Project │ Slide │ TimeInterval │ Pipeline   │
│  Events │ Exceptions │ Value Objects        │
│  PySide6-FREE                                │
└─────────────────────────────────────────────┘
```

## Layers and dependency rules

| Layer | Depends on | Forbidden imports |
|-------|-----------|-------------------|
| `domain/` | nothing, stdlib | `application`, `infrastructure`, `adapters`, `PySide6` |
| `application/` | `domain/` | `gui`, `mcp`, `cli`, `PySide6` |
| `infrastructure/` | `domain/`, `application/ports/` | `gui` |
| `adapters/` | `application/`, `domain/` | circular adapter deps |
| `bootstrap.py` | everything | — |

## Aggregate boundaries

```
Project (aggregate root)
├── Slide[] (entities, stable SlideId)
│   ├── TimeInterval (visual)
│   ├── TimeInterval (aligned, optional)
│   ├── ArtifactRef (image)
│   ├── Transcript (raw, cleaned, llm)
│   └── manual: bool
├── VideoRef
├── SubtitleRef
├── PipelineState[]
├── ScoreData (timestamps, values)
└── ArtifactRef[] (md, pptx, alignment_report)
```

## Pipeline state machine

```
States: NOT_STARTED → RUNNING → SUCCEEDED | FAILED | CANCELLED
                              ↘ STALE (on upstream re-run)

Transitions:
  detect succeeded → align NOT_STARTED (or stale if already done)
  align succeeded  → notes NOT_STARTED (or stale)
  notes succeeded  → export STALE
  re-detect        → align STALE, notes STALE, md STALE, pptx STALE
```

## Operation lifecycle (MCP)

```
client.submit(tool, args)
  → OperationRegistry.create()    status=queued
  → OpRunnerThread.run()          status=running
  → ApplicationService.execute()   progress updates
  → OperationRegistry.update()    status=succeeded|failed
  → drain_completed_ops            Qt timer picks up
  → refresh_from_disk()            GUI auto-updates
```

## Sequence diagrams

### Detect (canonical)

```
Adapter                  Application              Domain              Infra
   │                         │                      │                   │
   ├─ DetectCommand ────────►│                      │                   │
   │                         │                      │                   │
   │                   DetectionService             │                   │
   │                         ├─ repo.load() ────────►│                   │
   │                         │                      │                   │
   │                         ├─ decoder.info() ─────┤───► VideoDecoder  │
   │                         ├─ decoder.frames() ───┤───►              │
   │                         │                      │                   │
   │                         ├─ strategy.detect() ──┤───► SlideDetector │
   │                         │                      │                   │
   │                         │   project.replace_   │                   │
   │                         │   detected_slides() ─►│ (invariant check) │
   │                         │                      │                   │
   │                         ├─ repo.save() ────────►│                   │
   │                         ├─ eventbus.publish() ─►│                   │
   │                         │                      │                   │
   │◄─ DetectResult ────────┤                      │                   │
   │                         │                      │                   │
   │  (GUI controller        │                      │                   │
   │   receives SlidesDetected event)               │                   │
```

### Auto Align

```
Adapter                  Application              Domain              Infra
   │                         │                      │                   │
   ├─ AlignCommand ─────────►│                      │                   │
   │                   AlignmentService              │                   │
   │                         ├─ repo.load() ────────►│                   │
   │                         ├─ anchor_provider     │                   │
   │                         │   .get_anchors() ─────┤───► Subs parser  │
   │                         │                      │                   │
   │                         ├─ strategy.align()    │                   │
   │                         │   (slides, anchors)  │                   │
   │                         │                      │                   │
   │                         │   project.align_      │                   │
   │                         │   boundaries(result)─►│ (invariant check) │
   │                         │                      │                   │
   │                         ├─ repo.save() ────────►│                   │
   │                         ├─ eventbus.publish() ─►│                   │
   │◄─ AlignResult ─────────┤                      │                   │
```

### Auto pipeline

```
Adapter                  AutoService           services            Domain
   │                         │                      │                   │
   ├─ AutoCommand ──────────►│                      │                   │
   │                         │                      │                   │
   │                   detect() ───────► DetectionService              │
   │                         │◄──── DetectResult ───┤                   │
   │                         │                      │                   │
   │                   align() ────────► AlignmentService               │
   │                         │◄──── AlignResult ────┤                   │
   │                         │                      │                   │
   │                   notes() ─────────► NotesService                  │
   │                         │◄──── NotesResult ────┤                   │
   │                         │                      │                   │
   │                   export_md() ─────► ExportService                 │
   │                         │◄──── MDResult ───────┤                   │
   │                         │                      │                   │
   │                   export_pptx() ───► ExportService                 │
   │                         │◄──── PptxResult ─────┤                   │
   │                         │                      │                   │
   │                   validate() ─────► ValidationService              │
   │                         │◄──── ValResult ──────┤                   │
   │                         │                      │                   │
   │◄─ AutoResult ──────────┤                      │                   │
```

## Error handling hierarchy

```
Video2PptxError (base)
├── DomainError
│   ├── ValidationError           (invalid TimeInterval, etc.)
│   ├── ProjectStateError         (invalid state transition)
│   └── OperationConflictError    (detect while already running)
├── ProjectPersistenceError       (JSON read/write failure)
├── VideoDecodeError              (cannot open/decode)
├── SubtitleParseError            (malformed SRT/VTT)
├── DetectionError                (pipeline failure)
├── AlignmentError                (boundary computation failure)
├── NotesProcessingError          (notes pipeline failure)
├── ExportError                   (MD/PPTX generation failure)
└── LlmError                      (LLM API/connection failure)
```

## Persistence strategy

- `Project` is the canonical source of truth.
- `project.json` is the primary persistence file, written atomically (temp + rename).
- `slides.json` is a DERIVED artifact — a portable subset of `Project` for external consumption. Regenerated on save.
- FileProjectRepository handles both in one `save()` transaction.
- On load, `slides.json` is re-read into `Project.slides` only if present; otherwise slides are reconstructed from `project.json > slides[]`.

## Key design decisions

1. **No Big Bang Rewrite** — each phase keeps the application runnable.
2. **Domain is PySide6-free** — domain tests run without Qt.
3. **Application is PySide6-free** — use cases testable with fake ports.
4. **Strategy pattern** only where real alternatives exist (video decoder, slide detector mode, alignment anchor provider, export format).
5. **CV functions stay functional** — `frame_features.py`, `slide_detector.py` algorithms remain pure functions, not wrapped in classes.
6. **Event bus is synchronous** for MVP — no async infrastructure needed.
7. **Manual DI** — no framework; `bootstrap.py` wires everything.
8. **Characterization tests first** — Phase 1 freezes current valid behavior before any refactoring.
