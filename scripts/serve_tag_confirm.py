#!/usr/bin/env python3
"""Serve tag-confirm HTML on localhost; block until browser submit.

  python scripts/serve_tag_confirm.py artifacts/run/tag_confirm.json \\
      --html-out artifacts/run/tag_confirm.html \\
      --confirmed-out artifacts/run/tag_confirm.confirmed.json

Hard gate: process exits 0 only after a valid browser POST /submit.
Until then the workflow must not continue to Step 3.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from make_tag_confirm_editor import (  # noqa: E402
    TEMPLATE_HTML,
    inject,
    load_payload,
)


EDITABLE = ("tag", "type", "value")
LOCKED = ("id", "program", "step", "usage", "note")


def merge_and_validate(baseline: dict, submitted: dict) -> dict:
    base_items = baseline.get("items") or []
    sub_items = submitted.get("items")
    if not isinstance(sub_items, list):
        raise ValueError("items must be array")
    if len(sub_items) != len(base_items):
        raise ValueError(f"row count mismatch: got {len(sub_items)}, expect {len(base_items)}")

    merged_items = []
    errors: list[str] = []
    for i, (base, sub) in enumerate(zip(base_items, sub_items)):
        if not isinstance(sub, dict):
            errors.append(f"row {i + 1}: not object")
            continue
        row = {k: base.get(k, "") for k in (*LOCKED, *EDITABLE)}
        row["id"] = int(base.get("id") or i + 1)
        for k in EDITABLE:
            row[k] = str(sub.get(k, "")).strip()
        # locked fields must match baseline if present in submit
        for k in ("program", "step", "usage", "note"):
            if k in sub and str(sub.get(k, "")).strip() != str(base.get(k, "")).strip():
                errors.append(f"row {i + 1}: locked field {k} changed")
        miss = []
        if not row["tag"]:
            miss.append("tag")
        if row["type"] not in ("1", "3"):
            miss.append("type")
        if not row["value"]:
            miss.append("value")
        if miss:
            errors.append(f"row {i + 1}: incomplete {','.join(miss)}")
        merged_items.append(row)

    if errors:
        raise ValueError("; ".join(errors))

    return {
        "version": int(baseline.get("version") or submitted.get("version") or 1),
        "items": merged_items,
    }


def pick_port(preferred: int) -> int:
    if preferred > 0:
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def open_browser(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] auto-open failed: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Serve tag confirm page; block until submit")
    p.add_argument("json_path", type=Path, help="prefilled tag_confirm.json")
    p.add_argument(
        "--html-out",
        type=Path,
        required=True,
        help="write injected HTML here (also served)",
    )
    p.add_argument(
        "--confirmed-out",
        type=Path,
        required=True,
        help="write confirmed JSON after browser submit",
    )
    p.add_argument("--done-out", type=Path, default=None, help="touch marker file on success")
    p.add_argument("--template", type=Path, default=TEMPLATE_HTML)
    p.add_argument("--port", type=int, default=0, help="0 = ephemeral")
    p.add_argument("--timeout", type=float, default=0, help="seconds; 0 = wait forever")
    p.add_argument("--no-open", action="store_true", help="do not auto-open browser")
    args = p.parse_args(argv)

    if not args.json_path.is_file():
        print(f"[FAIL] missing {args.json_path}", file=sys.stderr)
        return 1
    if not args.template.is_file():
        print(f"[FAIL] missing {args.template}", file=sys.stderr)
        return 1

    baseline = load_payload(args.json_path)
    html = inject(args.template.read_text(encoding="utf-8"), baseline)
    args.html_out.parent.mkdir(parents=True, exist_ok=True)
    args.confirmed_out.parent.mkdir(parents=True, exist_ok=True)
    args.html_out.write_text(html, encoding="utf-8")
    html_bytes = html.encode("utf-8")

    done_path = args.done_out or args.confirmed_out.with_suffix(".done")
    if done_path.exists():
        done_path.unlink()

    port = pick_port(args.port)
    state: dict = {"result": None}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "TagConfirm/1.0"

        def log_message(self, fmt: str, *a) -> None:  # noqa: A003
            print(f"[HTTP] {self.address_string()} {fmt % a}")

        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in ("/", "/index.html", "/tag_confirm.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_bytes)))
                self.send_header("Cache-Control", "no-store")
                self._cors()
                self.end_headers()
                self.wfile.write(html_bytes)
                return
            if path == "/status":
                body = json.dumps(
                    {"waiting": state["result"] is None, "ok": state["result"] is not None},
                    ensure_ascii=False,
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self._cors()
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404, "not found")

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path != "/submit":
                self.send_error(404, "not found")
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                submitted = json.loads(raw.decode("utf-8"))
                merged = merge_and_validate(baseline, submitted)
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                body = json.dumps({"ok": False, "error": msg}, ensure_ascii=False).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self._cors()
                self.end_headers()
                self.wfile.write(body)
                print(f"[REJECT] {msg}", file=sys.stderr)
                return

            text = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
            args.confirmed_out.write_text(text, encoding="utf-8")
            args.json_path.write_text(text, encoding="utf-8")
            done_path.write_text("ok\n", encoding="utf-8")

            with lock:
                state["result"] = merged

            body = json.dumps(
                {
                    "ok": True,
                    "items": len(merged["items"]),
                    "path": str(args.confirmed_out.resolve()),
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            print(f"[OK] confirmed → {args.confirmed_out.resolve()}", flush=True)
            threading.Thread(target=server.shutdown, daemon=True).start()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"[URL]  {url}", flush=True)
    print(f"[HTML] {args.html_out.resolve()}", flush=True)
    print(
        "[WAIT] Blocking until browser submit. Do NOT continue workflow before exit 0.",
        flush=True,
    )
    if not args.no_open:
        threading.Timer(0.35, lambda: open_browser(url)).start()

    serve_thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.3}, daemon=True)
    serve_thread.start()

    started = time.time()
    exit_code = 0
    try:
        while True:
            with lock:
                if state["result"] is not None:
                    break
            if args.timeout > 0 and (time.time() - started) > args.timeout:
                print("[FAIL] timeout waiting for browser confirm", file=sys.stderr)
                exit_code = 2
                break
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("[FAIL] interrupted before confirm", file=sys.stderr)
        exit_code = 130
    finally:
        try:
            server.shutdown()
        except Exception:  # noqa: BLE001
            pass
        try:
            server.server_close()
        except Exception:  # noqa: BLE001
            pass
        serve_thread.join(timeout=2)

    if exit_code != 0:
        return exit_code
    if state["result"] is None:
        print("[FAIL] no browser confirm", file=sys.stderr)
        return 1

    print("[DONE] browser confirm received; safe to write IR / continue Step 3", flush=True)
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    raise SystemExit(main())
