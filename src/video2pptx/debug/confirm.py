# FILE: src/video2pptx/debug/confirm.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Destructive-op confirmation — require explicit confirm=true for delete/overwrite/re-detect/shutdown.
#            VIDEO2PPTX_TEST_MODE=1 still needs explicit args. No global auto-confirm.
#   SCOPE: require_confirm(), is_destructive(), ConfirmRequiredError
#   DEPENDS: M-STRUCTURED-ERRORS
#   LINKS: M-CONFIRM-POLICY
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   require_confirm - raise if args lacks confirm=true for destructive tool
#   is_destructive - classify tool name as destructive
#   ConfirmRequiredError - raised when confirm is missing
# END_MODULE_MAP

from __future__ import annotations

from video2pptx.debug.errors import OperationError


class ConfirmRequiredError(OperationError):
    def __init__(self, tool: str) -> None:
        super().__init__(
            type="ConfirmRequired",
            message=f"Destructive operation '{tool}' requires confirm=true",
            stage="confirm",
            recoverable=True,
        )


_DESTRUCTIVE_TOOLS: set[str] = {
    "detect",
    "auto_align",
    "process_notes",
    "llm_process",
    "export_md",
    "export_pptx",
    "auto",
    "project_close",
    "project_delete",
    "slide_delete",
    "slide_move",
    "slide_resize",
    "slide_clear_image",
    "app_shutdown",
    "cancel_operation",
}


def is_destructive(tool: str) -> bool:
    return tool in _DESTRUCTIVE_TOOLS


def require_confirm(tool: str, args: dict | None = None) -> None:
    if not is_destructive(tool):
        return
    if args and args.get("confirm") is True:
        return
    raise ConfirmRequiredError(tool)
