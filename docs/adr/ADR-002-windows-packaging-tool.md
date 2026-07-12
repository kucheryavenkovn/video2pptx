# ADR-002: Windows Packaging Tool

## Status

Accepted (provisional)

## Context

Video2PPTX needs to be distributed as a standalone Windows desktop application that users can install and run without Python. Two candidate packaging tools are available:

- **PyInstaller**: mature, widely used, onedir output, extensive hook ecosystem
- **Nuitka**: Python-to-C++ compiler, standalone output, smaller bundle, better startup

Both tools support PySide6, hidden imports, Qt plugin bundling, and console-mode disable.

## Decision

Select **PyInstaller** as the primary packaging tool.

### Reasons

1. **Maturity**: PyInstaller 6.x has been used in production for years with PySide6. The hook system automatically handles most hidden imports. Nuitka's PySide6 support is newer and less battle-tested.

2. **Build speed**: PyInstaller completes a onedir build in 2-5 minutes. Nuitka takes 15-30+ minutes because it compiles Python to C++. This significantly impacts CI pipeline time.

3. **Debugging**: PyInstaller onedir output is inspectable — you can browse the bundle, check DLLs, and debug missing imports. Nuitka standalone produces a single EXE with embedded runtime, making debugging harder.

4. **Qt plugin handling**: PyInstaller's `--collect-all PySide6` reliably bundles Qt plugins. Nuitka relies on `--enable-plugin=pyside6` and `--include-qt-plugins=sensible` which has had regressions.

5. **Community**: PyInstaller has a larger community, more documentation, and better PySide6 support. Issues are resolved faster.

### Trade-offs

- **Bundle size**: PyInstaller onedir is larger (200-400 MB) than Nuitka standalone (100-200 MB). This is acceptable for a desktop application.
- **Startup time**: PyInstaller onedir starts 1-3 seconds slower because it extracts to temp. Acceptable for a video processing app.
- **Python runtime**: PyInstaller bundles CPython as a DLL. This is transparent to the user.

### Future

If Nuitka matures and addresses the build-time and Qt-plugin concerns, it may become the primary tool. The ADR should be revisited when:
- Nuitka reduces build time to under 5 minutes for this project
- PySide6 plugin handling becomes fully reliable
- A performance benchmark shows >30% improvement in startup or detection speed

## Consequences

- Build scripts use PyInstaller spec as the primary artifact
- Nuitka build script is maintained as an alternative but not CI-tested
- Future optimization phase may revisit this decision
