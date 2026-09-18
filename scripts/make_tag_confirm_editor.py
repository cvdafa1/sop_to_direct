#!/usr/bin/env python3
"""Inject tag_confirm.json into editable HTML (chat embed or local open).

  python scripts/make_tag_confirm_editor.py artifacts/run/tag_confirm.json \\
      -o artifacts/run/tag_confirm.html
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_HTML = ROOT / "fixtures" / "tag_confirm_editor.html"


def load_payload(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("root must be object")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise SystemExit("items must be non-empty array")
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise SystemExit(f"items[{i}] must be object")
        for key in ("program", "step", "usage", "tag", "type"):
            if key not in it:
                raise SystemExit(f"items[{i}] missing {key}")
    if "version" not in data:
        data["version"] = 1
    return data


def inject(html: str, payload: dict) -> str:
    blob = json.dumps(payload, ensure_ascii=False)
    pattern = re.compile(
        r"/\*__TAG_CONFIRM_DATA__\*/.*?/\*__END_DATA__\*/",
        re.DOTALL,
    )
    out, n = pattern.subn(
        f"/*__TAG_CONFIRM_DATA__*/{blob}/*__END_DATA__*/",
        html,
        count=1,
    )
    if n != 1:
        raise SystemExit("marker /*__TAG_CONFIRM_DATA__*/ not found")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("json_path", type=Path)
    p.add_argument("-o", "--output", type=Path, required=True)
    p.add_argument("--template", type=Path, default=TEMPLATE_HTML)
    args = p.parse_args(argv)

    if not args.json_path.is_file():
        print(f"[FAIL] {args.json_path}", file=sys.stderr)
        return 1
    if not args.template.is_file():
        print(f"[FAIL] {args.template}", file=sys.stderr)
        return 1

    payload = load_payload(args.json_path)
    html = inject(args.template.read_text(encoding="utf-8"), payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"[OK]   {args.output} ({len(payload['items'])} items)")
    print(
        "[HINT] Prefer embedding this HTML in the Step 2.5 message. "
        "User submits by pasting the copied JSON once."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
