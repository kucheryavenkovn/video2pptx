# GRACE Framework - Project Engineering Protocol

## Keywords
video, slides, markdown, presentation, open-cv, computer-vision, slide-detection, subtitle-alignment, srt, vtt, marp, educational-video, frame-diff, perceptual-hash, Python, Typer, Pydantic, Loguru, Hatchling, OpenCV, numpy, Clean Architecture, GRACE

## Annotation
video2pptx — инструмент для автоматического извлечения интервалов слайдов из обучающих видео, привязки к субтитрам SRT/VTT и экспорта в Markdown-презентации (Marp). Ядро проекта: детекция смены слайдов через сравнение статичных областей кадра (целевая область слайда за вычетом вебкамеры/интерфейса), генерация структурированного JSON с интервалами, сохранение representative screenshots, привязка фрагментов транскрипта по таймкодам. Экспорт в PPTX/PDF — вторичный слой. Проект рассчитан на локальную обработку с CUDA/NVDEC-ускорением (RTX 4090) и fallback на CPU.

## Core Principles

### 1. Never Write Code Without a Contract
Before generating or editing any module, create or update its MODULE_CONTRACT with PURPOSE, SCOPE, INPUTS, and OUTPUTS. The contract is the source of truth. Code implements the contract, not the other way around.

### 2. Semantic Markup Is Load-Bearing Structure
Markers like `// START_BLOCK_<NAME>` and `// END_BLOCK_<NAME>` are navigation anchors, not documentation. They must be:
- uniquely named
- paired
- proportionally sized so one block fits inside an LLM working window

### 3. Knowledge Graph Is Always Current
`docs/knowledge-graph.xml` is the project map. When you add a module, move a module, rename exports, or add dependencies, update the graph so future agents can navigate deterministically.

### 4. Verification Is a First-Class Artifact
Testing, traces, and log anchors are designed before large execution waves. `docs/verification-plan.xml` is part of the architecture, not an afterthought. Logs are evidence. Tests are executable contracts.

### 5. Top-Down Synthesis
Code generation follows:
`RequirementsAnalysis -> TechnologyStack -> DevelopmentPlan -> VerificationPlan -> Code + Tests`

Never jump straight to code when requirements, architecture, or verification intent are still unclear.

### 6. Governed Autonomy
Agents have freedom in HOW to implement, but not in WHAT to build. Contracts, plans, graph references, and verification requirements define the allowed space.

### 7. Record Findings (mandatory)
During work, agents inevitably discover non-obvious facts about the environment, tools, and incompatibilities. Such findings **must be recorded** in `docs/findings.md` — knowledge must not disappear with the completed task.

What counts as a finding:
- version/build incompatibilities (Python, libraries, CUDA, drivers) and their symptoms;
- API differences (missing/renamed functions, signature quirks);
- blockers and their resolution (what didn't work, why, how fixed);
- toolchain behaviour (encodings, path discovery, caching);
- unexpected platform/OS effects (code pages, locale, permissions).

Format:
```
### F-NNNN — <short title>
- Date: YYYY-MM-DD
- Area: <video | detection | subtitles | export | ui | tooling | os>
- Finding: <what discovered>
- Symptom/Reproduction: <how it manifests>
- Impact: <what it affects>
- Resolution/Status: <what done or open>
- LINKS: <M-*, V-M-*, files, commands>
```

### 8. Separation of Concerns: CV vs LLM
Slide detection is a deterministic computer-vision task. LLM may only be used after slides and intervals are already found:
- **CV layer:** find intervals, save images, dedupe, compute confidence, debug artifacts
- **Subtitle layer:** align text by timestamps
- **LLM layer** (post-MVP): short slide descriptions, thesis extraction, speaker notes, slide titles, topic grouping

Never use LLM as the primary mechanism for slide change detection.

## Grep-First Navigation

Navigation order:
1. Shared/public truth: `docs/knowledge-graph.xml`, `docs/development-plan.xml`, `docs/verification-plan.xml`
2. File-local/private truth: `MODULE_CONTRACT`, `MODULE_MAP`, `CHANGE_SUMMARY`, function contracts, semantic blocks
3. Full file reads only after the target module, file, or block is narrowed

Canonical search anchors:
- `START_MODULE_CONTRACT` / `END_MODULE_CONTRACT`
- `START_MODULE_MAP` / `END_MODULE_MAP`
- `START_CONTRACT:` / `END_CONTRACT:`
- `START_BLOCK_` / `END_BLOCK_`
- `START_CHANGE_SUMMARY` / `END_CHANGE_SUMMARY`
- `LINKS:` for graph-linked references
- `M-` for module IDs
- `V-M-` for verification IDs
- `CrossLink` for graph edges

## Semantic Markup Reference

### Module Level
```
# FILE: path/to/file.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: [What this module does - one sentence]
#   SCOPE: [What operations are included]
#   DEPENDS: [List of module dependencies]
#   LINKS: [Knowledge graph references]
#   ROLE: [Optional: RUNTIME | TEST | BARREL | CONFIG | TYPES | SCRIPT]
#   MAP_MODE: [Optional: EXPORTS | LOCALS | SUMMARY | NONE]
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   exportedSymbol - one-line description
# END_MODULE_MAP
```

### Function or Component Level
```
# START_CONTRACT: function_name
#   PURPOSE: [What it does]
#   INPUTS: { param_name: Type - description }
#   OUTPUTS: { ReturnType - description }
#   SIDE_EFFECTS: [External state changes or "none"]
#   LINKS: [Related modules/functions]
# END_CONTRACT: function_name
```

### Code Block Level
```
# START_BLOCK_VALIDATE_INPUT
# ... code ...
# END_BLOCK_VALIDATE_INPUT
```

### Change Tracking
```
# START_CHANGE_SUMMARY
#   LAST_CHANGE: [v1.2.0 - What changed and why]
# END_CHANGE_SUMMARY
```

## Logging and Trace Convention

Use Loguru structured logging:
```python
logger.info("[ModuleName][function_name][BLOCK_NAME] message | key=value")
```

Rules:
- prefer structured key=value fields over prose-heavy log lines
- redact secrets and high-risk payloads
- treat missing log anchors on critical branches as a verification defect
- update tests when log markers change intentionally

## Verification Conventions

Testing rules:
- deterministic assertions first
- trace or log assertions when trajectory matters
- test files may also carry MODULE_CONTRACT, MODULE_MAP, semantic blocks, and CHANGE_SUMMARY
- module-local tests should stay close to the module they verify

Metrics for MVP:
- missed_slide_rate <= 5%
- false_split_rate <= 10%
- timestamp_error_seconds <= 1.5 sec at sample_fps=2

## File Structure
```
docs/
  requirements.xml         - Product requirements and use cases
  technology.xml           - Stack decisions, tooling, observability, testing
  development-plan.xml     - Modules, phases, data flows
  verification-plan.xml    - Test strategy, trace expectations, gates
  knowledge-graph.xml      - Project-wide navigation graph
  operational-packets.xml  - Canonical packet templates
  findings.md              - F-NNNN problem/constraint journal
src/video2pptx/
  ... code with GRACE markup ...
tests/
  ... tests with GRACE-aware evidence where appropriate ...
```

## Rules for Modifications

1. Read the MODULE_CONTRACT before editing any file.
2. After editing source or test files, update MODULE_MAP in a way that matches the file's role and map mode.
3. After adding or removing modules, update `docs/knowledge-graph.xml`.
4. After changing test files, commands, critical scenarios, or log markers, update `docs/verification-plan.xml`.
5. After fixing bugs, add a CHANGE_SUMMARY entry and strengthen nearby verification if the old evidence was weak.
6. Never remove semantic markup anchors unless the structure is intentionally replaced with better anchors.
