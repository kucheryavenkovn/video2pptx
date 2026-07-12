# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Video2PPTX standalone Windows build.
# Set REPO_ROOT env var before running, or run from repo root.
# Output: dist/windows/Video2PPTX/Video2PPTX.exe

import os
import sys

_REPO = os.environ.get("REPO_ROOT")
if not _REPO:
    _REPO = os.path.abspath(".")
_REPO = os.path.abspath(_REPO)
os.chdir(_REPO)
sys.path.insert(0, os.path.join(_REPO, "src"))

BLOCK_CIPHER = None

_ENTRY = os.path.join(_REPO, "src", "video2pptx", "desktop.py")

a = Analysis(
    [_ENTRY],
    pathex=[os.path.join(_REPO, "src")],
    binaries=[],
    datas=[],
    hiddenimports=[
        "video2pptx.gui.about_dialog",
        "video2pptx.gui.settings_project",
        "video2pptx.gui.settings_app",
        "video2pptx.gui.roi_selector",
        "video2pptx.gui.subtitle_editor",
        "video2pptx.gui.debug_dock",
        "video2pptx.gui.log_bridge",
        "video2pptx.gui.ui_state",
        "video2pptx.gui.main_window_ui",
        "video2pptx.gui.controllers.project_controller",
        "video2pptx.gui.controllers.pipeline_controller",
        "video2pptx.gui.controllers.pipeline_worker",
        "video2pptx.gui.controllers.timeline_controller",
        "video2pptx.gui.controllers.subtitle_editor_handler",
        "video2pptx.bootstrap.application",
        "video2pptx.application.base",
        "video2pptx.application.errors",
        "video2pptx.application.cancellation",
        "video2pptx.application.ports.slide_detector",
        "video2pptx.application.ports.preview_analyzer",
        "video2pptx.application.ports.alignment",
        "video2pptx.application.ports.notes_processor",
        "video2pptx.application.ports.presentation_exporter",
        "video2pptx.application.ports.project_repository",
        "video2pptx.application.services.detection_service",
        "video2pptx.application.services.preview_service",
        "video2pptx.application.services.alignment_service",
        "video2pptx.application.services.notes_service",
        "video2pptx.application.services.export_service",
        "video2pptx.application.services.validation_service",
        "video2pptx.application.services.auto_service",
        "video2pptx.application.update_service",
        "video2pptx.application.identity",
        "video2pptx.domain.project",
        "video2pptx.domain.slide",
        "video2pptx.domain.identifiers",
        "video2pptx.domain.time",
        "video2pptx.domain.artifacts",
        "video2pptx.domain.pipeline_state",
        "video2pptx.domain.errors",
        "video2pptx.infrastructure.persistence.file_project_repository",
        "video2pptx.infrastructure.persistence.dto",
        "video2pptx.infrastructure.persistence.mapper",
        "video2pptx.infrastructure.persistence.migrations",
        "video2pptx.infrastructure.github_release_provider",
        "video2pptx.adapters.cli.app",
        "video2pptx.adapters.cli.context",
        "video2pptx.adapters.cli.errors",
        "video2pptx.adapters.cli.exit_codes",
        "video2pptx.adapters.cli.observer",
        "video2pptx.adapters.cli.renderer",
        "video2pptx.adapters.legacy_detector",
        "video2pptx.adapters.legacy_preview",
        "video2pptx.adapters.legacy_aligner",
        "video2pptx.adapters.legacy_notes",
        "video2pptx.adapters.legacy_exporter",
        "video2pptx.backends.opencv_backend",
        "video2pptx.backends.pyav_backend",
        "video2pptx.backends.decord_backend",
        "video2pptx.utils.json_io",
        "video2pptx.validators.project_validator",
        "pysubs2",
        "PIL",
        "cv2",
        "imagehash",
        "pptx",
        "yaml",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "IPython",
        "notebook",
        "jupyter",
        "zmq",
        "tornado",
        "sphinx",
        "pytest",
        "mypy",
        "setuptools._distutils",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Video2PPTX",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(_REPO, "assets", "branding", "Video2PPTX-clean.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Video2PPTX",
)
