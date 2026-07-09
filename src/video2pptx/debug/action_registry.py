# FILE: src/video2pptx/debug/action_registry.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: @mcp_action decorator + ActionRegistry. Auto-discovers MCP tools from decorated methods.
#   SCOPE: Decorate any method with @mcp_action → ActionRegistry.scan() finds it → tools/list
#   DEPENDS: inspect
#   LINKS: M-DEBUG-ACTION
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   mcp_action -
#   ActionRegistry -
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.1.0 - Initial implementation
# END_CHANGE_SUMMARY

from __future__ import annotations

import inspect
from typing import Any, Callable


def mcp_action(name: str | None = None, desc: str = "", kind: str = "action"):
    """Декоратор: помечает метод как MCP-экшен.

    Args:
        name: имя инструмента (по умолчанию имя метода без _)
        desc: описание для tools/list
        kind: "action" | "detect" | "export" | "navigation"
    """
    def decorator(fn):
        action_name = name or fn.__name__.lstrip("_").replace("_", "_")
        fn._mcp_meta = {"name": action_name, "desc": desc, "kind": kind}
        return fn
    return decorator


class ActionRegistry:
    """Реестр экшенов. Сканирует объект, строит MCP tool descriptors, маршрутизирует вызовы."""

    def __init__(self, instance: Any = None) -> None:
        self._actions: dict[str, dict] = {}
        self._bindings: dict[str, tuple[Any, str]] = {}
        if instance is not None:
            self.scan(instance)

    def scan(self, instance: Any) -> None:
        for method_name in dir(instance):
            try:
                fn = getattr(instance, method_name, None)
            except Exception:
                continue
            meta = None
            if fn is not None:
                meta = getattr(fn, "_mcp_meta", None)
                if meta is None and hasattr(fn, "__func__"):
                    meta = getattr(fn.__func__, "_mcp_meta", None)
            if meta is not None:
                aname = meta["name"]
                schema = self._build_schema(fn)
                self._actions[aname] = {**meta, "schema": schema}
                self._bindings[aname] = (instance, method_name)

    def tools(self) -> list[dict]:
        return [
            {
                "name": name,
                "description": meta.get("desc", ""),
                "inputSchema": meta.get("schema", {"type": "object"}),
            }
            for name, meta in self._actions.items()
        ]

    def call(self, name: str, args: dict[str, Any] | None = None) -> Any:
        meta = self._actions.get(name)
        if meta is None:
            raise KeyError(f"Unknown action: {name}")
        instance, method_name = self._bindings[name]
        fn = getattr(instance, method_name, None)
        if fn is None:
            raise AttributeError(f"Method {method_name} not found for action {name}")
        sig = inspect.signature(fn)
        bound = sig.bind(**(args or {}))
        return fn(*bound.args, **bound.kwargs)

    def has(self, name: str) -> bool:
        return name in self._actions

    @staticmethod
    def _build_schema(fn: Callable) -> dict:
        sig = inspect.signature(fn)
        props = {}
        for pname, param in sig.parameters.items():
            if pname in ("self", "cls", "args", "kwargs"):
                continue
            ann = param.annotation
            if ann is inspect.Parameter.empty:
                props[pname] = {"type": "string"}
            elif isinstance(ann, str):
                ann_str = ann
                if ann_str in ("float", "int", "number"):
                    props[pname] = {"type": "number"}
                elif ann_str == "bool":
                    props[pname] = {"type": "boolean"}
                else:
                    props[pname] = {"type": "string"}
            elif ann is float or ann is int:
                props[pname] = {"type": "number"}
            elif ann is bool:
                props[pname] = {"type": "boolean"}
            else:
                props[pname] = {"type": "string"}
        return {"type": "object", "properties": props} if props else {"type": "object"}
