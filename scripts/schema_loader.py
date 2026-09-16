"""Load element_schema.json: templates, defaults, layout-type map, ext validation."""

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

# 允许中文的文案类字段（不跑「禁止中文裸标识」）
_TEXT_OK_KEYS = frozenset(
    {
        "message",
        "desc",
        "subTitle",
        "subTitle2",
        "path",
        "url",
        "fileFormat",
        "mainProcedure",
    }
)

# 表达式 / 位号类：禁止中文裸词
_EXPR_LIKE_KEYS = frozenset({"express", "name", "targetVar", "timer", "targetValue"})

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_TAG_REF_RE = re.compile(r"#\([^)]+\)")
_VAR_REF_RE = re.compile(r"\$\(([^)]+)\)")
_BAD_VAR_REF_RE = re.compile(r"\$\{([^}]+)\}")


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


def _type_ok(value: Any, expected: str | list | None) -> bool:
    if expected is None:
        return True
    types = expected if isinstance(expected, list) else [expected]
    for t in types:
        if t == "string" and isinstance(value, str):
            return True
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if t == "boolean" and isinstance(value, bool):
            return True
        if t == "array" and isinstance(value, list):
            return True
        if t == "object" and isinstance(value, dict):
            return True
        if t == "null" and value is None:
            return True
    return False


def _validate_against_schema(
    value: Any,
    schema: dict[str, Any],
    path: str,
    errors: list[str],
) -> None:
    """Validate value against a JSON-schema-like fragment from element_schema."""
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must be const {schema['const']!r}, got {value!r}")
        return

    expected = schema.get("type")
    if expected is not None and not _type_ok(value, expected):
        errors.append(f"{path}: expected type {expected!r}, got {type(value).__name__}")
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum {schema['enum']}")

    if schema.get("type") == "object" or (
        isinstance(schema.get("type"), list) and "object" in schema["type"]
    ):
        if not isinstance(value, dict):
            return
        props = schema.get("properties") or {}
        required = schema.get("required") or []
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required field {key!r}")
        additional = schema.get("additionalProperties", True)
        if additional is False:
            allowed = set(props.keys())
            for key in value:
                if key not in allowed:
                    errors.append(
                        f"{path}: forbidden key {key!r}; "
                        f"allowed={sorted(allowed)} (see element_schema.json)"
                    )
        for key, child in value.items():
            if key not in props:
                continue
            prop = props[key]
            if not isinstance(prop, dict):
                continue
            _validate_against_schema(child, prop, f"{path}.{key}", errors)

    if schema.get("type") == "array" or (
        isinstance(schema.get("type"), list) and "array" in schema["type"]
    ):
        if not isinstance(value, list):
            return
        # 业务数组：required 且无 default → 不允许空
        if "default" not in schema and len(value) == 0:
            # 仅当父级把该数组标为 required 时由上层保证存在；此处对无 default 的数组禁空
            errors.append(f"{path}: array must not be empty (business required)")
            return
        items = schema.get("items")
        if isinstance(items, dict):
            for i, item in enumerate(value):
                _validate_against_schema(item, items, f"{path}[{i}]", errors)


def validate_ext(
    element: str,
    ext: dict[str, Any] | None,
    *,
    node_id: str = "",
) -> list[str]:
    """Validate ext against element_schema.xml.ext_data_schema. Empty list = OK."""
    prefix = f"{node_id} ({element})" if node_id else element
    comp = components_by_element().get(element)
    if not comp:
        return [f"{prefix}: unknown element"]
    schema = (comp.get("xml") or {}).get("ext_data_schema")
    if schema is None:
        if ext:
            return [f"{prefix}: element has no ext_data_schema but ext was provided"]
        return []
    if ext is None:
        return [f"{prefix}: ext is required by schema"]
    if not isinstance(ext, dict):
        return [f"{prefix}: ext must be object"]

    errors: list[str] = []
    _validate_against_schema(ext, schema, "ext", errors)

    # 无 default 的 required 数组：禁止空（_validate 对 array 本身也会查）
    props = schema.get("properties") or {}
    for key in schema.get("required") or []:
        prop = props.get(key)
        if not isinstance(prop, dict) or prop.get("type") != "array":
            continue
        if "default" in prop:
            continue
        arr = ext.get(key)
        if isinstance(arr, list) and len(arr) == 0:
            msg = f"ext.{key}: array must not be empty"
            if msg not in errors and f"ext.{key}: array must not be empty (business required)" not in errors:
                errors.append(f"ext.{key}: array must not be empty (business required)")

    for e in _cross_cutting_string_errors(ext):
        errors.append(e)

    return [f"{prefix}: {e}" for e in errors]


def _cross_cutting_string_errors(obj: Any, path: str = "ext") -> list[str]:
    """跨切：${}→应 $()；express/name 等位号表达式禁中文裸标识。"""
    errors: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{path}.{k}"
            if isinstance(v, str):
                errors.extend(_check_string_field(k, v, child))
            else:
                errors.extend(_cross_cutting_string_errors(v, child))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            errors.extend(_cross_cutting_string_errors(v, f"{path}[{i}]"))
    return errors


def _check_string_field(key: str, value: str, path: str) -> list[str]:
    errors: list[str] = []
    if _BAD_VAR_REF_RE.search(value):
        errors.append(
            f"{path}: use $(Name) for program vars, not ${{Name}} (found in {value!r})"
        )
    if key in _TEXT_OK_KEYS:
        return errors
    if key not in _EXPR_LIKE_KEYS and key != "express":
        return errors
    if key == "targetVar":
        if value and not (value.startswith("$(") and value.endswith(")")):
            # 也允许 #(...) 极少见；程序变量必须 $()
            if not (value.startswith("#(") and value.endswith(")")):
                errors.append(
                    f"{path}: targetVar must be $(Name) or #(tag), got {value!r}"
                )
        return errors
    if key == "timer":
        # $(JSQ) 或裸名
        return errors
    # express / name / targetValue：含中文且未整体包在 #()/$() 内则拒
    if _CJK_RE.search(value):
        # 允许消息式混排？表达式中出现中文一律拒
        if key == "express" or (
            key in ("name", "targetValue") and not value.startswith("#(")
        ):
            errors.append(
                f"{path}: Chinese identifiers not allowed in {key}; "
                f"use #(tag) or $(var), got {value!r}"
            )
    return errors


def normalize_ext_strings(obj: Any) -> Any:
    """${X} → $(X) recursively in strings."""
    if isinstance(obj, dict):
        return {k: normalize_ext_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_ext_strings(v) for v in obj]
    if isinstance(obj, str):
        return _BAD_VAR_REF_RE.sub(r"$(\1)", obj)
    return obj


def collect_program_vars_from_ext(ext: Any) -> set[str]:
    """Collect bare names from $(...) in ext tree."""
    found: set[str] = set()

    def walk(o: Any) -> None:
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str):
            for m in _VAR_REF_RE.finditer(o):
                name = m.group(1).strip()
                if name:
                    found.add(name)

    walk(ext)
    return found


def merge_ext(element: str, user_ext: dict[str, Any] | None) -> dict[str, Any] | None:
    """Merge schema defaults/consts with IR ext (IR wins). Does not validate."""
    comp = components_by_element().get(element)
    if not comp:
        raise ValueError(f"unknown element: {element}")
    schema = (comp.get("xml") or {}).get("ext_data_schema")
    if schema is None:
        if user_ext:
            raise ValueError(f"{element} has no ext_data_schema but IR provided ext")
        return None

    base = defaults_for_element(element) or {}
    user = normalize_ext_strings(user_ext or {})
    if user is not None and not isinstance(user, dict):
        raise ValueError(f"{element}: ext must be object")
    merged = _deep_merge(base, user or {})

    # force const fields
    for key, prop in (schema.get("properties") or {}).items():
        if isinstance(prop, dict) and "const" in prop:
            merged[key] = copy.deepcopy(prop["const"])

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


def merge_and_validate_ext(
    element: str,
    user_ext: dict[str, Any] | None,
    *,
    node_id: str = "",
) -> dict[str, Any] | None:
    """Merge defaults then validate; raise ValueError with all issues."""
    merged = merge_ext(element, user_ext)
    errs = validate_ext(element, merged, node_id=node_id)
    if errs:
        raise ValueError("ext schema invalid:\n  - " + "\n  - ".join(errs))
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

    template = re.sub(r"<!--.*?-->", "", template, flags=re.DOTALL)

    merged_ext = merge_and_validate_ext(element, ext, node_id=node_id)
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

    rendered = re.sub(r"\s*<bpmn2:incoming>\s*</bpmn2:incoming>\s*", "\n", rendered)
    rendered = re.sub(r"\s*<bpmn2:outgoing>\s*</bpmn2:outgoing>\s*", "\n", rendered)
    return rendered.strip()
