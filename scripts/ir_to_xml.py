#!/usr/bin/env python3
"""Deterministic IR → BPMN XML compiler.

Usage:
    python scripts/ir_to_xml.py path/to/ir.json -o out.xml
    python scripts/ir_to_xml.py path/to/ir.json          # stdout
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from layout_generator import LayoutGenerator
from schema_loader import layout_type, render_node_xml, resolve_element

UNSUPPORTED_LAYOUT = frozenset({"parallel1", "parallel2"})
DECISION_LAYOUT_TYPES = frozenset({"or", "and", "cond"})


def compile_ir(ir: dict[str, Any]) -> str:
    nodes = ir.get("nodes") or []
    flows = ir.get("flows") or []
    if not nodes:
        raise ValueError("IR.nodes is empty")
    if not flows:
        raise ValueError("IR.flows is empty")

    process_id = ir.get("process_id") or "Process_1"
    gen = LayoutGenerator()
    node_xml_by_id: dict[str, str] = {}
    meta: dict[str, dict[str, Any]] = {}

    for node in nodes:
        nid = node.get("id")
        if not nid:
            raise ValueError("node missing id")
        element = resolve_element(node.get("type", ""))
        lt = layout_type(element)
        if lt in UNSUPPORTED_LAYOUT:
            raise ValueError(
                f"phase-1 ir_to_xml does not support {element}; "
                "omit parallel containers or extend compiler"
            )
        name = node.get("name") or ""
        gen.add_node(nid, lt, name)
        node_xml_by_id[nid] = render_node_xml(
            element,
            nid,
            name=name,
            ext=node.get("ext"),
            attrs=node.get("attrs"),
        )
        meta[nid] = {"element": element, "layout_type": lt}

    for flow in flows:
        fid = flow.get("id")
        src = flow.get("source")
        tgt = flow.get("target")
        if not fid or not src or not tgt:
            raise ValueError(f"flow missing id/source/target: {flow}")
        gen.add_flow(
            fid,
            src,
            tgt,
            situation=flow.get("situation"),
            name=flow.get("name"),
        )

    layout_ops = ir.get("layout")
    if layout_ops:
        _apply_layout_ops(gen, layout_ops)
    else:
        _auto_layout(gen, meta)

    return gen.assemble_full_xml(node_xml_by_id, process_id=process_id)


def _apply_layout_ops(gen: LayoutGenerator, ops: list[dict[str, Any]]) -> None:
    for i, op in enumerate(ops):
        kind = op.get("op")
        if kind == "vertical":
            node_ids = op.get("nodes") or []
            gen.layout_vertical(
                node_ids,
                center_x=op.get("center_x", 500),
                start_y=op.get("start_y", 60),
                gap=op.get("gap"),
            )
        elif kind == "branch_columns":
            decision = op.get("decision")
            if not decision:
                raise ValueError(f"layout[{i}] branch_columns missing decision")
            gen.layout_branch_columns(
                decision_id=decision,
                yes_ids=op.get("yes") or [],
                no_ids=op.get("no") or [],
                merge_id=op.get("merge"),
                center_x=op.get("center_x", 500),
                col_gap=op.get("col_gap"),
                row_gap=op.get("row_gap"),
            )
        elif kind == "vertical_continue":
            after = op.get("after")
            node_ids = op.get("nodes") or []
            if not after or after not in gen.nodes:
                raise ValueError(f"layout[{i}] vertical_continue bad after={after}")
            gap = op.get("gap") or gen.VERTICAL_GAP
            start_y = gen.nodes[after].bottom + gap
            gen.layout_vertical(
                node_ids,
                center_x=op.get("center_x", 500),
                start_y=start_y,
                gap=op.get("gap"),
            )
        elif kind in ("parallel1", "parallel2"):
            raise ValueError(f"layout op {kind} not supported in phase-1")
        else:
            raise ValueError(f"unknown layout op: {kind}")


def _auto_layout(gen: LayoutGenerator, meta: dict[str, dict[str, Any]]) -> None:
    """Linear spine; yes-only decisions stay on spine; yes+no uses branch_columns."""
    outgoing: dict[str, list] = {}
    incoming: dict[str, list] = {}
    for flow in gen.flows:
        outgoing.setdefault(flow.source, []).append(flow)
        incoming.setdefault(flow.target, []).append(flow)

    starts = [nid for nid, m in meta.items() if m["layout_type"] == "start"]
    if len(starts) != 1:
        raise ValueError("auto layout requires exactly one flow:start")
    start_id = starts[0]

    placed: set[str] = set()
    center_x = 500
    cursor_y = 60

    def place_vertical(ids: list[str]) -> None:
        nonlocal cursor_y
        if not ids:
            return
        gen.layout_vertical(ids, center_x=center_x, start_y=cursor_y)
        placed.update(ids)
        last = gen.nodes[ids[-1]]
        cursor_y = last.bottom + gen.VERTICAL_GAP

    current = start_id
    spine: list[str] = []

    while current is not None:
        if current in placed:
            break
        outs = outgoing.get(current, [])
        lt = meta[current]["layout_type"]

        if lt in DECISION_LAYOUT_TYPES and len(outs) == 2:
            spine.append(current)
            place_vertical(spine)
            spine = []

            yes_flow = next((f for f in outs if f.situation == "yes"), None)
            no_flow = next((f for f in outs if f.situation == "no"), None)
            if not yes_flow:
                raise ValueError(f"decision {current} missing situation=yes")
            if not no_flow:
                raise ValueError(f"decision {current} missing situation=no")

            yes_path, yes_merge = _collect_branch_path(
                yes_flow.target, incoming, outgoing, meta, until_multi_in=True
            )
            no_path, no_merge = _collect_branch_path(
                no_flow.target, incoming, outgoing, meta, until_multi_in=True
            )
            merge_id = yes_merge or no_merge
            if yes_merge and no_merge and yes_merge != no_merge:
                raise ValueError(
                    f"branch merge mismatch from {current}: {yes_merge} vs {no_merge}"
                )

            gen.layout_branch_columns(
                decision_id=current,
                yes_ids=yes_path,
                no_ids=no_path,
                merge_id=merge_id,
                center_x=center_x,
            )
            placed.update(yes_path)
            placed.update(no_path)
            if merge_id:
                placed.add(merge_id)
                cursor_y = gen.nodes[merge_id].bottom + gen.VERTICAL_GAP
                outs_m = outgoing.get(merge_id, [])
                current = outs_m[0].target if len(outs_m) == 1 else None
            else:
                current = None
            continue

        spine.append(current)
        if lt == "end" or not outs:
            place_vertical(spine)
            break
        if len(outs) != 1:
            place_vertical(spine)
            raise ValueError(
                f"auto layout cannot handle node {current} with {len(outs)} outs "
                f"(use explicit layout)"
            )
        current = outs[0].target

    missing = [nid for nid in gen.node_order if nid not in placed]
    if missing:
        raise ValueError(
            f"auto layout left nodes unplaced: {missing}; provide IR.layout"
        )


def _collect_branch_path(
    start: str,
    incoming: dict[str, list],
    outgoing: dict[str, list],
    meta: dict[str, dict[str, Any]],
    until_multi_in: bool,
) -> tuple[list[str], str | None]:
    """Walk until a merge candidate (in-degree>=2) or end; exclude merge from path."""
    path: list[str] = []
    cur = start
    merge_id = None
    seen: set[str] = set()
    while cur and cur not in seen:
        seen.add(cur)
        in_deg = len(incoming.get(cur, []))
        if until_multi_in and in_deg >= 2 and path:
            merge_id = cur
            break
        if until_multi_in and in_deg >= 2 and not path:
            # first node is already merge (empty branch) — unusual
            merge_id = cur
            break
        path.append(cur)
        outs = outgoing.get(cur, [])
        if meta[cur]["layout_type"] == "end" or not outs:
            break
        if len(outs) != 1:
            break
        nxt = outs[0].target
        if len(incoming.get(nxt, [])) >= 2:
            merge_id = nxt
            break
        cur = nxt
    return path, merge_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile IR JSON to Direct BPMN XML")
    parser.add_argument("ir_path", type=Path, help="path to IR JSON")
    parser.add_argument("-o", "--output", type=Path, help="output XML path (default stdout)")
    args = parser.parse_args(argv)

    ir = json.loads(args.ir_path.read_text(encoding="utf-8"))
    try:
        xml = compile_ir(ir)
    except Exception as e:
        print(f"ir_to_xml error: {e}", file=sys.stderr)
        return 1

    if args.output:
        args.output.write_text(xml, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(xml)
        if not xml.endswith("\n"):
            sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
