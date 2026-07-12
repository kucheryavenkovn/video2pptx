# FILE: src/video2pptx/adapters/cli/exit_codes.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Centralized exit codes for CLI commands.
#   SCOPE: CliExitCode IntEnum with descriptive codes 0-7
#   DEPENDS: none
#   LINKS: M-CLI-ADAPTER
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   CliExitCode - mapping of semantic outcome to numeric exit code
# END_MODULE_MAP

from __future__ import annotations

from enum import IntEnum


class CliExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_APPLICATION_ERROR = 1
    CLI_USAGE_ERROR = 2
    PRECONDITION_ERROR = 3
    VALIDATION_ERROR = 4
    PERSISTENCE_CONFLICT = 5
    EXTERNAL_ADAPTER_ERROR = 6
    CANCELLED = 7
