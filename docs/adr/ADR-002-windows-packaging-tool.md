# ADR-002: Windows Packaging Tool

## Status

Accepted for first public beta.

## Context

Video2PPTX needs to be distributed as a standalone Windows desktop application that users can install and run without Python. Two candidate packaging tools are available:

- **PyInstaller**: mature, widely used, onedir output, extensive hook ecosystem
- **Nuitka**: Python-to-C++ compiler, standalone output, smaller bundle, better startup

Both tools support PySide6, hidden imports, Qt plugin bundling, and console-mode disable.

## Decision

Select **PyInstaller** for the first public beta without a full comparative benchmark.

### Rationale

Minimize release risk, simplify native dependency debugging, and obtain a stable inspectable onedir Windows bundle.

Key factors:
- PyInstaller has existing community PySide6 hooks and mature Qt plugin handling.
- onedir output is inspectable — critical for debugging missing DLLs and native dependencies in a first-time packaging effort.
- Build toolchain is well understood: PyInstaller spec + Inno Setup installer.
- Nuitka would require separate native dependency configuration and has longer build cycles.

### Nuitka benchmark

Deferred. No comparative benchmark has been run for Video2PPTX.

The ADR will be revisited with a real comparative benchmark when:
- A stable packaged release is in use
- Build infrastructure is established
- Sufficient CI capacity exists for parallel packaging experiments

### Trade-offs

- PyInstaller onedir is larger than a hypothetical Nuitka build. Actual size comparison requires a benchmark.
- Startup time impact of PyInstaller vs Nuitka is not measured for Video2PPTX.
- Python runtime is bundled as a DLL in both cases.

## Consequences

- Build scripts use PyInstaller spec as the primary artifact.
- Nuitka build script directory (packaging/windows/nuitka/) is maintained as a placeholder but not CI-tested.
- First public beta ships PyInstaller onedir with Inno Setup installer.
- Nuitka benchmark is tracked as a deferred evaluation item, not as evidence for this decision.
