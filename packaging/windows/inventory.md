# Windows Packaging Inventory

## Runtime Dependencies

| Dependency | Python Package | Native DLL | Dynamic Import | Required Feature | Packaging Notes |
|---|---|---|---|---|---|
| PySide6 | PySide6 | Qt6Core, Qt6Gui, Qt6Widgets, Qt6Multimedia, Qt6Network | no | GUI, MCP | Qt plugins (platform, image, multimedia, styles) must be bundled |
| PySide6 Addons | PySide6-Addons | Qt6MultimediaWidgets | no | Video playback | Required for QVideoWidget |
| numpy | numpy | none | no | Score computation | Vendored by PyInstaller |
| opencv-python | opencv-python | opencv_world, ffmpeg | no | CV detection | opencv_ffmpeg.dll for video I/O |
| Pillow | Pillow | none | no | Image processing | Pure Python + C extensions |
| imagehash | imagehash | none | no | Deduplication | Pure Python |
| pysubs2 | pysubs2 | none | no | Subtitle parsing | Pure Python |
| python-pptx | python-pptx | lxml | no | PPTX export | Pure Python + lxml |
| httpx | httpx | none | yes (import inside functions) | LLM client | Pure Python + httpcore |
| typer | typer | none | no | CLI | Pure Python + click |
| rich | rich | none | no | CLI output | Pure Python |
| PyYAML | pyyaml | none | no | Config parsing | C extension |
| loguru | loguru | none | no | Logging | Pure Python |
| matplotlib | matplotlib | none | no | Debug plots | Optional, large |
| scikit-image | scikit-image | none | no | Frame features | Large, optional |
| packaging | packaging | none | no | Versioning | Pure Python |

## Dynamic Imports

All module-level dynamic imports found in src:

| Module | Dynamic Import | Context |
|---|---|---|
| gui/main_window.py | `from video2pptx.domain.artifacts import ArtifactRef` | Lazy inside _on_set_slide_frame |
| gui/main_window.py | `from video2pptx.domain.project import DetectionConfig` | Lazy inside _on_project_settings |
| gui/main_window_ui.py | `from video2pptx.gui.about_dialog import show_about_dialog` | Lazy inside _show_about |
| gui/main_window_ui.py | `from video2pptx.application.identity import application_identity` | Lazy inside _open_github |
| gui/about_dialog.py | `from PySide6.QtCore import qVersion` | Lazy inside _qt_version |
| mcp_server.py | `from video2pptx.gui.log_bridge import LogBridge` | Module-level |
| mcp_server.py | `from video2pptx.gui.ui_state import read_ui_state` | Inside function |
| bootstrap/application.py | (all imports are module-level) | OK |

## Qt Plugins

Required Qt plugins for bundled application:

| Plugin | Path in Qt | Needed For |
|---|---|---|
| windows | plugins/platforms/qwindows.dll | Window rendering |
| minimal | plugins/platforms/qminimal.dll | Fallback/offscreen |
| offscreen | plugins/platforms/qoffscreen.dll | Headless/test mode |
| imageformats | plugins/imageformats/qjpeg.dll, qpng.dll, etc. | Image loading |
| styles | plugins/styles/qwindowsvistastyle.dll | Native look |
| multimedia | plugins/multimedia/qffmpegmediaplugin.dll | Video playback |
| tls | plugins/tls/qcertonlybackend.dll, qschannelbackend.dll | HTTPS |

## Excluded Dev Dependencies

These must NOT be included in the packaged build:

- pytest, pytest-qt, pytest-cov
- mypy
- sphinx
- any test fixtures

## Video Backend Native Dependencies

| Backend | Required DLL | Notes |
|---|---|---|
| OpenCV CPU | opencv_ffmpeg*.dll | Bundled with opencv-python wheel |
| PyAV CPU | av*.dll, ffmpeg*.dll | Requires FFmpeg native libraries |
| PyAV NVDEC | av*.dll, nvcuda.dll, nvdec.dll | NVIDIA GPU + CUDA required at runtime |

## Build Environment

- OS: Windows 10/11 x64
- Python: 3.12.x (from GitHub Actions windows-latest)
- Packaging tools: PyInstaller 6.x or Nuitka 2.x
- Installer: Inno Setup 6.x
