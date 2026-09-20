#!/usr/bin/env python3
"""Host select via call_tool("request_interaction"); for skill Step 1.5 / 3.5.

  # Step 1.5 — split yes/no (exactly one of --recommend no_split|split)
  python scripts/request_interaction_select.py split \\
      --reason "设备边界清晰，建议拆分" --recommend split

  # Step 3.5 — compile yes/no
  python scripts/request_interaction_select.py compile

Exit codes:
  0  — user selected a valid value; stdout is one JSON object with "value"
  2  — tool unavailable / error / cancel / invalid value → Agent MUST fall back
       to dialogue numbering in interaction.md (stdout JSON has ok=false)
  1  — bad CLI args

Does NOT choose for the user. Does NOT default-select the recommended option.
detached is omitted (host default false).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


class InteractionUnavailable(Exception):
    """request_interaction missing or call failed — use dialogue fallback."""


def _call_select(title: str, message: str, options: list[dict[str, str]]) -> dict[str, Any]:
    try:
        from agent_tools import call_tool  # type: ignore
    except ImportError as exc:
        raise InteractionUnavailable(f"agent_tools unavailable: {exc}") from exc

    params = {
        "kind": "select",
        "title": title,
        "message": message,
        "options": options,
    }
    try:
        result = call_tool("request_interaction", params)
    except Exception as exc:  # noqa: BLE001
        raise InteractionUnavailable(f"request_interaction failed: {exc}") from exc

    if not isinstance(result, dict):
        raise InteractionUnavailable(f"unexpected result type: {type(result).__name__}")
    if not result.get("value"):
        raise InteractionUnavailable("no value in result (cancelled or empty)")
    return result


def ask_split(*, reason: str, recommend: str) -> dict[str, Any]:
    """Step 1.5. recommend must be 'no_split' or 'split'. Returns host result dict."""
    if recommend not in ("no_split", "split"):
        raise ValueError("recommend must be no_split or split")

    def desc(which: str, body: str) -> str:
        if which == recommend:
            return f"（推荐）{body}"
        return body

    options = [
        {
            "value": "no_split",
            "label": "不拆分",
            "description": desc("no_split", "保持单一主程序"),
        },
        {
            "value": "split",
            "label": "拆分",
            "description": desc("split", "按评估边界拆分子程序"),
        },
    ]
    message = (
        f"理由：{reason}\n"
        "请选择一项（不会自动替你选择；不选则无法继续）。"
    )
    result = _call_select("是否拆分子程序", message, options)
    value = str(result.get("value") or "").strip()
    if value not in ("no_split", "split"):
        raise InteractionUnavailable(f"invalid value: {value!r}")
    return result


def ask_compile() -> dict[str, Any]:
    """Step 3.5 after save success. Returns host result dict."""
    options = [
        {
            "value": "compile",
            "label": "确认编译",
            "description": "对主程序调用 compile_program",
        },
        {
            "value": "skip_compile",
            "label": "暂不编译",
            "description": "跳过编译，进入结果报告",
        },
    ]
    message = "主程序已保存。请选择（不会自动替你选择；不选则无法继续编译）。"
    result = _call_select("是否编译", message, options)
    value = str(result.get("value") or "").strip()
    if value not in ("compile", "skip_compile"):
        raise InteractionUnavailable(f"invalid value: {value!r}")
    return result


def _emit(payload: dict[str, Any], code: int) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return code


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="request_interaction select for Step 1.5 / 3.5")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_split = sub.add_parser("split", help="Step 1.5 split confirm")
    p_split.add_argument("--reason", required=True, help="one-line评估理由")
    p_split.add_argument(
        "--recommend",
        required=True,
        choices=("no_split", "split"),
        help="exactly one recommended option (shown in description only)",
    )

    sub.add_parser("compile", help="Step 3.5 compile confirm")

    args = p.parse_args(argv)

    try:
        if args.cmd == "split":
            result = ask_split(reason=args.reason, recommend=args.recommend)
        else:
            result = ask_compile()
    except InteractionUnavailable as exc:
        return _emit(
            {"ok": False, "fallback": True, "error": str(exc)},
            2,
        )
    except ValueError as exc:
        return _emit({"ok": False, "fallback": False, "error": str(exc)}, 1)

    return _emit(
        {
            "ok": True,
            "fallback": False,
            "value": result.get("value"),
            "label": result.get("label"),
            "description": result.get("description"),
        },
        0,
    )


if __name__ == "__main__":
    raise SystemExit(main())
