# FILE: tests/conftest.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Shared pytest fixtures for video2pptx
#   SCOPE: loguru_sink capture fixture, synthetic frame generators
#   DEPENDS: pytest, loguru
#   LINKS: V-M-ALL
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import pytest
from loguru import logger


@pytest.fixture
def loguru_sink() -> list:
    """Capture loguru messages into a list for trace/log assertions."""
    messages: list[str] = []
    handler_id = logger.add(lambda msg: messages.append(str(msg)), level="DEBUG")
    yield messages
    logger.remove(handler_id)
