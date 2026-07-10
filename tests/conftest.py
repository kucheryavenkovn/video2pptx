# FILE: tests/conftest.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Shared pytest fixtures for video2pptx
#   SCOPE: loguru capture plus deterministic repository, workspace, video, and subtitle fixtures
#   DEPENDS: pytest, loguru, OpenCV, tests/fixtures/gen_test_video.py
#   LINKS: V-M-ALL
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from pathlib import Path
import subprocess
import sys

import cv2
import pytest
from loguru import logger


@pytest.fixture(scope="session")
def repo_dir() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def tests_fixtures_dir(repo_dir: Path) -> Path:
    fixture_dir = repo_dir / "tests" / "fixtures"
    video = fixture_dir / "test_slides.mp4"
    subtitles = fixture_dir / "test_slides.srt"
    if not video.is_file() or not subtitles.is_file():
        subprocess.run(
            [sys.executable, str(fixture_dir / "gen_test_video.py")],
            check=True,
        )
    return fixture_dir


@pytest.fixture(scope="session")
def synthetic_video_path(tests_fixtures_dir: Path) -> Path:
    path = tests_fixtures_dir / "test_slides.mp4"
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise RuntimeError(f"Synthetic fixture cannot be decoded: {path}")
    finally:
        capture.release()
    return path


@pytest.fixture(scope="session")
def synthetic_subtitle_path(tests_fixtures_dir: Path) -> Path:
    return tests_fixtures_dir / "test_slides.srt"


@pytest.fixture(scope="session")
def workspace_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("video2pptx-characterization")


@pytest.fixture
def loguru_sink() -> list:
    """Capture loguru messages into a list for trace/log assertions."""
    messages: list[str] = []
    handler_id = logger.add(lambda msg: messages.append(str(msg)), level="DEBUG")
    yield messages
    logger.remove(handler_id)
