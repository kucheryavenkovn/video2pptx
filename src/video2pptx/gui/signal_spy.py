# FILE: src/video2pptx/gui/signal_spy.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Watch Qt signals on any QObject, log via loguru→LogBridge for real-time inspection.
#   SCOPE: SignalSpy.watch(obj, signal_name), SignalSpy.watch_all(obj).
#   DEPENDS: PySide6.QtCore, M-GUI-LOG-BRIDGE
#   LINKS: M-GUI-SIGNAL-SPY
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   SignalSpy - watch/watch_all for Qt signal tracing
# END_MODULE_MAP

from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QObject


class SignalSpy:
    """Captures Qt signals and logs them via loguru (→ LogBridge → DebugDock)."""

    @staticmethod
    def watch(obj: QObject, signal_name: str) -> None:
        signal = getattr(obj, signal_name, None)
        if signal is None:
            logger.warning(f"[SignalSpy] Signal '{signal_name}' not found on {obj.__class__.__name__}")
            return
        cls_name = obj.__class__.__name__

        def _on_emit(*args: object) -> None:
            args_repr = ", ".join(repr(a)[:80] for a in args)
            logger.debug(f"[SignalSpy] {cls_name}.{signal_name} | args=({args_repr})")

        signal.connect(_on_emit)
        logger.info(f"[SignalSpy] Watching {cls_name}.{signal_name}")

    @staticmethod
    def watch_all(obj: QObject) -> None:
        import inspect
        cls = type(obj)
        cls_name = cls.__name__
        seen: set[str] = set()
        for name in dir(obj):
            if name in seen or name.startswith("__"):
                continue
            attr = getattr(obj, name, None)
            if attr is None:
                continue
            try:
                if isinstance(attr, type) and hasattr(attr, "connect"):
                    seen.add(name)
                    SignalSpy.watch(obj, name)
            except Exception:
                pass
        logger.info(f"[SignalSpy] Watching {len(seen)} signals on {cls_name}")
