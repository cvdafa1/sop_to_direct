"""Load element_schema.json: templates, defaults, layout-type map."""

from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "references" / "element_schema.json"

# schema element → LayoutGenerator NODE_SIZES key
_LAYOUT_TYPE_MAP = {
    "flow:start": "start",
    "flow:end": "end",
    "flow:subproc": "subproc",
    "flow:and": "and",
    "flow:or": "or",
    "flow:branch": "branch",
    "flow:parallel1": "parallel1",
    "flow:parallel2": "parallel2",
    "flow:risingEdge": "rising_edge",
    "flow:fallingEdge": "falling_edge",
    "flow:otherMainProc": "other_main_proc",
    "flow:request": "request",
    "io:dcs": "dcs",
    "io:var": "var",
    "io:calc": "calc",
    "io:concat": "concat",
    "io:fileExport": "file_export",
    "io:fileImport": "file_import",
    "io:modifyLabel": "modify_label",
    "io:modifyProps": "modify_props",
    "timer:cond": "cond",
    "timer:start": "timer_start",
    "timer:wait": "wait",
    "timer:restart": "timer_restart",
    "timer:stop": "timer_stop",
    "timer:pause": "timer_pause",
    "timer:clock": "timer_clock",
    "msg:guide": "guide",
    "msg:confirm": "confirm",
    "msg:alarm": "alarm",
}

_SHORT_TO_ELEMENT = {v: k for k, v in _LAYOUT_TYPE_MAP.items()}


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def components_by_element() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for comp in load_schema().get("components", []):
        xml = comp.get("xml") or {}
        el = xml.get("element")
        if el:
            out[el] = comp
    return out


def resolve_element(type_name: str) -> str:
    """Accept full `io:dcs` or short `dcs`; return schema element name."""
    if not type_name:
        raise ValueError("node.type is required")
    if type_name in components_by_element():
        return type_name
    if type_name in _SHORT_TO_ELEMENT:
        return _SHORT_TO_ELEMENT[type_name]
    # camelCase short → try prefix scan
    for el in components_by_element():
        local = el.split(":", 1)[-1]
        if local == type_name:
            return el
    raise ValueError(f"unknown node type (not in element_schema): {type_name}")


def layout_type(element: str) -> str:
    if element in _LAYOUT_TYPE_MAP:
        return _LAYOUT_TYPE_MAP[element]
    local = element.split(":", 1)[-1]
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", local).lower()
    return snake


def _prop_seed(prop: dict[str, Any]) -> Any:
    if "default" in prop:
        return copy.deepcopy(prop["default"])
    if "const" in prop:
        return copy.deepcopy(prop["const"])
    if prop.get("type") == "object" and "properties" in prop:
        nested: dict[str, Any] = {}
        for nk, nv in prop["properties"].items():
            if not isinstance(nv, dict):
                continue
            if "default" in nv or "const" in nv:
                nested[nk] = _prop_seed(nv)
        return nested if nested else None
    return None


def defaults_for_element(element: str) -> dict[str, Any] | None:
    comp = components_by_element().get(element)
    if not comp:
        return None
    schema = (comp.get("xml") or {}).get("ext_data_schema")
    if not schema:
        return None
    result: dict[str, Any] = {}
    for key, prop in (schema.get("properties") or {}).items():
        if not isinstance(prop, dict):
            continue
        seed = _prop_seed(prop)
        if seed is not None:
            result[key] = seed
    return result


def _fill_item_defaults(item_schema: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    for key, prop in (item_schema.get("properties") or {}).items():
        if not isinstance(prop, dict):
            continue
        if key in out:
            continue
        seed = _prop_seed(prop)
        if seed is not None:
            out[key] = seed
    return out


def merge_ext(element: str, user_ext: dict[str, Any] | None) -> dict[str, Any] | None:
    """Merge schema defaults/consts with IR ext (IR wins)."""
    comp = components_by_element().get(element)
    if not comp:
        raise ValueError(f"unknown element: {element}")
    schema = (comp.get("xml") or {}).get("ext_data_schema")
    if schema is None:
        if user_ext:
            raise ValueError(f"{element} has no ext_data_schema but IR provided ext")
        return None

    base = defaults_for_element(element) or {}
    merged = _deep_merge(base, user_ext or {})

    # array item defaults (e.g. io:dcs data[].lower)
    props = schema.get("properties") or {}
    for key, prop in props.items():
        if not isinstance(prop, dict) or prop.get("type") != "array":
            continue
        items_schema = prop.get("items")
        if not isinstance(items_schema, dict) or items_schema.get("type") != "object":
            continue
        arr = merged.get(key)
        if isinstance(arr, list):
            merged[key] = [
                _fill_item_defaults(items_schema, x) if isinstance(x, dict) else x
                for x in arr
            ]
    return merged


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def render_node_xml(
    element: str,
    node_id: str,
    name: str = "",
    ext: dict[str, Any] | None = None,
    attrs: dict[str, Any] | None = None,
) -> str:
    """Fill schema template; incoming/outgoing left empty (assemble injects)."""
    comp = components_by_element().get(element)
    if not comp:
        raise ValueError(f"unknown element: {element}")
    xml = comp.get("xml") or {}
    template = xml.get("template")
    if not template:
        raise ValueError(f"no template for {element}")

    # strip HTML comments in template (e.g. branch)
    template = re.sub(r"<!--.*?-->", "", template, flags=re.DOTALL)

    merged_ext = merge_ext(element, ext)
    mapping: dict[str, str] = {
        "id": node_id,
        "name": name or "",
        "ext_json": json.dumps(merged_ext, ensure_ascii=False, separators=(",", ":"))
        if merged_ext is not None
        else "",
        "incoming": "",
        "outgoing": "",
        "outgoing_yes": "",
        "outgoing_no": "",
        "outgoing_0": "",
        "outgoing_1": "",
    }
    if attrs:
        for k, v in attrs.items():
            mapping[str(k)] = "" if v is None else str(v)

    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return ""

    try:
        rendered = template.format_map(_Safe(mapping))
    except Exception as e:
        raise ValueError(f"template fill failed for {element}/{node_id}: {e}") from e

    # drop empty io lines so assemble injects cleanly
    rendered = re.sub(r"\s*<bpmn2:incoming>\s*</bpmn2:incoming>\s*", "\n", rendered)
    rendered = re.sub(r"\s*<bpmn2:outgoing>\s*</bpmn2:outgoing>\s*", "\n", rendered)
    return rendered.strip()
