#!/usr/bin/env python3
"""Deterministic IR → BPMN XML compiler.

Usage:
    python scripts/ir_to_xml.py path/to/ir.json -o out.xml
    python scripts/ir_to_xml.py path/to/ir.json          # stdout
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from layout_generator import LayoutGenerator
from schema_loader import (
    collect_program_vars_from_ext,
    components_by_element,
    layout_type,
    normalize_ext_strings,
    render_node_xml,
    resolve_element,
)
from api_reference import (
    ensure_ident_name,
    sanitize_xml_ident_names,
    strip_timer_ref,
    strip_var_ref,
    unique_rename_map,
)

UNSUPPORTED_LAYOUT = frozenset({"parallel1", "parallel2"})
DECISION_YN_TYPES = frozenset({"or", "and", "cond"})

# 编译 IR 结构门禁（对齐 fixtures/sample_ir.json；拒绝废弃 main_program/steps）
_FORBIDDEN_TOP = frozenset({"main_program", "subprograms", "coverage", "program_name"})
_NODE_DRAFT_FIELDS = frozenset(
    {"step_no", "source_text", "node_type", "equipment", "parameters"}
)


def _validate_ir_structure(ir: Any, *, path: str = "<ir>") -> list[str]:
    """结构检查；有错返回消息列表（空=通过）。由 compile_ir 强制调用。"""
    errors: list[str] = []
    if not isinstance(ir, dict):
        return [f"{path}: root must be object"]

    for key in _FORBIDDEN_TOP:
        if key in ir:
            errors.append(
                f"{path}: forbidden top-level key {key!r} "
                f"(use fixtures/sample_ir.json: process_id/nodes/flows)"
            )

    for key in ("nodes", "flows"):
        if key not in ir:
            errors.append(f"{path}: missing required top-level key {key!r}")

    nodes = ir.get("nodes")
    flows = ir.get("flows")
    if nodes is not None and not isinstance(nodes, list):
        errors.append(f"{path}: nodes must be array")
        nodes = None
    if flows is not None and not isinstance(flows, list):
        errors.append(f"{path}: flows must be array")
        flows = None
    if isinstance(nodes, list) and len(nodes) < 2:
        errors.append(f"{path}: nodes must include at least start and end")

    allowed = set(components_by_element())
    for full in list(allowed):
        if ":" in full:
            allowed.add(full.split(":", 1)[1])

    node_ids: set[str] = set()
    if isinstance(nodes, list):
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                errors.append(f"{path}: nodes[{i}] must be object")
                continue
            for k in ("id", "type"):
                if not node.get(k):
                    errors.append(f"{path}: nodes[{i}] missing {k}")
            for bad in _NODE_DRAFT_FIELDS:
                if bad in node:
                    errors.append(
                        f"{path}: nodes[{i}] forbidden field {bad!r} "
                        f"(use id/type/name/ext like sample_ir.json)"
                    )
            nid = node.get("id")
            if isinstance(nid, str):
                if nid in node_ids:
                    errors.append(f"{path}: duplicate node id {nid!r}")
                node_ids.add(nid)
            ntype = str(node.get("type") or "")
            if ntype:
                short = ntype.split(":", 1)[-1]
                if ntype not in allowed and short not in allowed:
                    errors.append(
                        f"{path}: nodes[{i}] type {ntype!r} not in element_schema.json"
                    )
            if "ext" in node and node["ext"] is not None and not isinstance(
                node["ext"], dict
            ):
                errors.append(f"{path}: nodes[{i}].ext must be object")

        if not any(
            isinstance(n, dict) and n.get("type") in ("flow:start", "start")
            for n in nodes
        ):
            errors.append(f"{path}: missing flow:start node")
        if not any(
            isinstance(n, dict) and n.get("type") in ("flow:end", "end") for n in nodes
        ):
            errors.append(f"{path}: missing flow:end node")

    if isinstance(flows, list):
        for i, flow in enumerate(flows):
            if not isinstance(flow, dict):
                errors.append(f"{path}: flows[{i}] must be object")
                continue
            for k in ("id", "source", "target"):
                if not flow.get(k):
                    errors.append(f"{path}: flows[{i}] missing {k}")
            for end in ("source", "target"):
                ref = flow.get(end)
                if ref and node_ids and ref not in node_ids:
                    errors.append(f"{path}: flows[{i}].{end}={ref!r} not in nodes")

    return errors


def _rewrite_dollar_refs(text: str, mapping: dict[str, str]) -> str:
    if not text or not mapping:
        return text

    def repl(m: re.Match) -> str:
        inner = m.group(1)
        new = mapping.get(inner)
        return f"$({new})" if new else m.group(0)

    ordered = sorted(mapping.keys(), key=len, reverse=True)
    pat = re.compile(r"\$\((" + "|".join(re.escape(k) for k in ordered) + r")\)")
    return pat.sub(repl, text)


def _walk_ext_rewrite(obj: Any, mapping: dict[str, str]) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "timer" and isinstance(v, str):
                bare = strip_timer_ref(v)
                new = mapping.get(bare, bare)
                out[k] = f"$({new})" if v.strip().startswith("$(") else new
            else:
                out[k] = _walk_ext_rewrite(v, mapping)
        return out
    if isinstance(obj, list):
        return [_walk_ext_rewrite(x, mapping) for x in obj]
    if isinstance(obj, str):
        return _rewrite_dollar_refs(obj, mapping)
    return obj


def sanitize_ir_idents(ir: dict[str, Any]) -> dict[str, Any]:
    """规范 IR 中子程序名、timers/variables、ext 内 $()/timer 引用。"""
    import copy

    ir = copy.deepcopy(ir)
    nodes = ir.get("nodes") or []

    dollar_raw: list[str] = []
    for node in nodes:
        element = resolve_element(node.get("type", ""))
        if element == "flow:subproc":
            node["name"] = ensure_ident_name(
                node.get("name") or "", fallback_prefix="sub"
            )
        ext = node.get("ext")
        if not ext:
            continue
        blob = json.dumps(ext, ensure_ascii=False)
        for m in re.finditer(r"\$\(([^)]+)\)", blob):
            dollar_raw.append(m.group(1).strip())
        if isinstance(ext, dict):
            t = ext.get("timer")
            if isinstance(t, str) and t.strip():
                dollar_raw.append(strip_timer_ref(t))

    timers = ir.get("timers")
    if timers:
        fixed = []
        for item in timers:
            if isinstance(item, str):
                fixed.append(
                    ensure_ident_name(strip_timer_ref(item), fallback_prefix="tm")
                )
            elif isinstance(item, dict):
                item = dict(item)
                item["name"] = ensure_ident_name(
                    strip_timer_ref(str(item.get("name", ""))), fallback_prefix="tm"
                )
                fixed.append(item)
            else:
                fixed.append(item)
        ir["timers"] = fixed

    variables = ir.get("variables")
    if variables:
        fixed = []
        for item in variables:
            if isinstance(item, str):
                fixed.append(
                    ensure_ident_name(strip_var_ref(item), fallback_prefix="var")
                )
            elif isinstance(item, dict):
                item = dict(item)
                item["name"] = ensure_ident_name(
                    strip_var_ref(str(item.get("name", ""))), fallback_prefix="var"
                )
                fixed.append(item)
            else:
                fixed.append(item)
        ir["variables"] = fixed

    mapping = {
        k: v
        for k, v in unique_rename_map(dollar_raw, fallback_prefix="n").items()
        if k != v
    }
    if mapping:
        for node in nodes:
            if node.get("ext") is not None:
                node["ext"] = _walk_ext_rewrite(node["ext"], mapping)

    return ir


def compile_ir(ir: dict[str, Any]) -> str:
    ir_errs = _validate_ir_structure(ir, path="<compile_ir>")
    if ir_errs:
        raise ValueError("IR structure invalid:\n  - " + "\n  - ".join(ir_errs))
    ir = sanitize_ir_idents(ir)
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
                f"ir_to_xml does not support {element}: "
                "parallel containers are disabled in this skill; "
                "split SOP '同时' into sequential io:dcs (etc.) per element_split.md R5"
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

    declared_vars: set[str] = set()
    for item in ir.get("variables") or []:
        if isinstance(item, str):
            declared_vars.add(strip_var_ref(item))
        elif isinstance(item, dict) and item.get("name"):
            declared_vars.add(strip_var_ref(str(item["name"])))
    if declared_vars:
        used_vars: set[str] = set()
        for node in nodes:
            ext = node.get("ext")
            if ext:
                used_vars |= collect_program_vars_from_ext(normalize_ext_strings(ext))
        missing_vars = sorted(used_vars - declared_vars)
        if missing_vars:
            raise ValueError(
                "IR.variables missing program vars used in ext: "
                + ", ".join(missing_vars)
                + " (see subprocess.md §variables / element_schema.json)"
            )

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

    xml = gen.assemble_full_xml(node_xml_by_id, process_id=process_id)
    xml, _renames = sanitize_xml_ident_names(xml)
    return xml


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
        elif kind == "multi_columns":
            decision = op.get("decision")
            groups = op.get("branches") or op.get("branch_groups") or []
            if not decision:
                raise ValueError(f"layout[{i}] multi_columns missing decision")
            gen.layout_multi_columns(
                decision_id=decision,
                branch_groups=groups,
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
            raise ValueError(
                f"layout op {kind} disabled: use sequential nodes "
                "(element_split.md R5), not parallel containers"
            )
        else:
            raise ValueError(f"unknown layout op: {kind}")


def _auto_layout(gen: LayoutGenerator, meta: dict[str, dict[str, Any]]) -> None:
    """直线 + 是/否 + 多路 branch；支持支路内再套一层是/否。

    几何硬门禁仍由 assemble_full_xml / validate_bpmn 负责。
    """
    outgoing: dict[str, list] = {}
    incoming: dict[str, list] = {}
    for flow in gen.flows:
        outgoing.setdefault(flow.source, []).append(flow)
        incoming.setdefault(flow.target, []).append(flow)

    starts = [nid for nid, m in meta.items() if m["layout_type"] == "start"]
    if len(starts) != 1:
        raise ValueError("auto layout requires exactly one flow:start")

    placed: set[str] = set()
    center_x = 500
    cursor_y = 60

    def find_merge(arm_starts: list[str]) -> str | None:
        """各臂下游共同汇合点（入度来自多臂，或共享后继）。"""
        if len(arm_starts) < 2:
            return None
        # 每臂收集直到 end 的节点集（含起点）
        arm_sets: list[set[str]] = []
        for s in arm_starts:
            seen: set[str] = set()
            stack = [s]
            while stack:
                n = stack.pop()
                if n in seen:
                    continue
                seen.add(n)
                for f in outgoing.get(n, []):
                    stack.append(f.target)
            arm_sets.append(seen)
        common = set.intersection(*arm_sets) if arm_sets else set()
        # 汇合点：在 common 中，且有来自「非仅单臂内部」的汇入；取拓扑上最早
        # 简化：common 里入度>=2 的节点，按到 start 的大致顺序选第一个
        candidates = [n for n in common if len(incoming.get(n, [])) >= 2]
        if not candidates:
            # 退：所有臂都到同一个 end
            ends = [n for n in common if meta[n]["layout_type"] == "end"]
            return ends[0] if len(ends) == 1 else None
        # 选不被其他 candidate 支配的「最上」：y 未定，用 BFS 层
        order: list[str] = []
        seen_b: set[str] = set()
        q = list(arm_starts)
        while q:
            n = q.pop(0)
            if n in seen_b:
                continue
            seen_b.add(n)
            order.append(n)
            for f in outgoing.get(n, []):
                if f.target not in seen_b:
                    q.append(f.target)
        for n in order:
            if n in candidates:
                return n
        return candidates[0]

    def collect_linear(start: str, stop: str | None) -> list[str]:
        """从 start 沿唯一出边走到 stop（不含 stop）；遇分叉则停在分叉节点（含）。"""
        path: list[str] = []
        cur: str | None = start
        seen: set[str] = set()
        while cur and cur not in seen and cur != stop:
            seen.add(cur)
            path.append(cur)
            outs = outgoing.get(cur, [])
            lt = meta[cur]["layout_type"]
            if lt == "branch" or (
                lt in DECISION_YN_TYPES and len(outs) == 2
            ):
                break
            if len(outs) != 1:
                break
            nxt = outs[0].target
            if nxt == stop:
                break
            cur = nxt
        return path

    def place_vertical_at(ids: list[str], cx: int, y0: int) -> int:
        if not ids:
            return y0
        gen.layout_vertical(ids, center_x=cx, start_y=y0)
        placed.update(ids)
        last = gen.nodes[ids[-1]]
        return last.bottom + gen.VERTICAL_GAP

    def place_yn_decision(
        decision_id: str, cx: int, y0: int, stop: str | None, col_gap: int = 200
    ) -> int:
        """放置 and/or/cond 的是/否分叉。

        必须先由调用方传入正确的 stop（=汇合点或外层边界），避免臂展开吞掉后续菱形。
        臂内若再遇二分/多路，则对该臂递归 place_from。
        """
        node = gen.nodes[decision_id]
        node.x = cx - node.w // 2
        node.y = y0
        placed.add(decision_id)

        outs = outgoing.get(decision_id, [])
        yes_f = next((f for f in outs if f.situation == "yes"), None)
        no_f = next((f for f in outs if f.situation == "no"), None)
        if not yes_f:
            raise ValueError(f"decision {decision_id} missing situation=yes")
        if not no_f:
            raise ValueError(f"decision {decision_id} missing situation=no")

        def _arm_recursive(head: str | None) -> bool:
            if not head or head == stop:
                return False
            hlt = meta[head]["layout_type"]
            houts = outgoing.get(head, [])
            if hlt in DECISION_YN_TYPES and len(houts) == 2:
                return True
            if hlt == "branch" and len(houts) >= 2:
                return True
            path = collect_linear(head, stop)
            if not path:
                return False
            last = path[-1]
            llt = meta[last]["layout_type"]
            louts = outgoing.get(last, [])
            if llt in DECISION_YN_TYPES and len(louts) == 2:
                return True
            if llt == "branch" and len(louts) >= 2:
                return True
            return False

        yes_rec = _arm_recursive(yes_f.target)
        no_rec = _arm_recursive(no_f.target)
        gap = 720 if (yes_rec or no_rec) else col_gap
        start_y = node.bottom + gen.VERTICAL_GAP
        yes_cx = int(cx - gap)
        no_cx = int(cx + gap)
        bottoms = [start_y]

        def _place_linear_arm(head: str | None, arm_cx: int) -> int:
            if not head or head == stop:
                return start_y
            ids = [n for n in collect_linear(head, stop) if n not in placed]
            # collect_linear 若停在嵌套分叉上，分叉本身留给递归；纯线性则整列放下
            if ids and (
                (
                    meta[ids[-1]]["layout_type"] in DECISION_YN_TYPES
                    and len(outgoing.get(ids[-1], [])) == 2
                )
                or meta[ids[-1]]["layout_type"] == "branch"
            ):
                # 不应走到这里：_arm_recursive 应为 True
                ids = ids[:-1]
            if not ids:
                return start_y
            gen.layout_vertical(ids, center_x=arm_cx, start_y=start_y)
            placed.update(ids)
            return gen.nodes[ids[-1]].bottom + gen.VERTICAL_GAP

        if yes_rec:
            bottoms.append(place_from(yes_f.target, yes_cx, start_y, stop))
        else:
            bottoms.append(_place_linear_arm(yes_f.target, yes_cx))

        if no_rec:
            bottoms.append(place_from(no_f.target, no_cx, start_y, stop))
        else:
            bottoms.append(_place_linear_arm(no_f.target, no_cx))

        return max(bottoms)

    def place_from(nid: str | None, cx: int, y0: int, stop: str | None) -> int:
        """从 nid 布局到 stop 之前，返回新的 y 游标。"""
        nonlocal_y = y0
        cur = nid
        while cur and cur not in placed and cur != stop:
            lt = meta[cur]["layout_type"]
            outs = outgoing.get(cur, [])

            # 多路择一
            if lt == "branch" and len(outs) >= 2:
                node = gen.nodes[cur]
                node.x = cx - node.w // 2
                node.y = nonlocal_y
                placed.add(cur)
                # 稳定排序：数字 situation 优先，否则字符串
                def _sit_key(f):
                    s = f.situation
                    if s is None:
                        return (2, "")
                    if str(s).isdigit():
                        return (0, int(s))
                    return (1, str(s))

                arms = sorted(outs, key=_sit_key)
                arm_starts = [f.target for f in arms]
                merge = find_merge(arm_starts)
                if stop and merge is None:
                    merge = stop
                # 每臂：先展开线性节点；若臂首是嵌套决策，整臂用 place_from
                groups: list[list[str]] = []
                arm_meta: list[tuple[str, bool]] = []  # (start, needs_recursive)
                for f in arms:
                    head = f.target
                    if head == merge:
                        groups.append([])
                        arm_meta.append((head, False))
                        continue
                    hlt = meta[head]["layout_type"]
                    houts = outgoing.get(head, [])
                    if hlt in DECISION_YN_TYPES and len(houts) == 2:
                        groups.append([])  # 列内递归，不预填线性
                        arm_meta.append((head, True))
                    elif hlt == "branch" and len(houts) >= 2:
                        groups.append([])
                        arm_meta.append((head, True))
                    else:
                        # 线性前缀若以嵌套分叉结尾，整臂递归（先竖排前缀再分叉易丢节点）
                        path = collect_linear(head, merge)
                        nest = bool(
                            path
                            and (
                                (
                                    meta[path[-1]]["layout_type"] in DECISION_YN_TYPES
                                    and len(outgoing.get(path[-1], [])) == 2
                                )
                                or meta[path[-1]]["layout_type"] == "branch"
                            )
                        )
                        if nest:
                            groups.append([])
                            arm_meta.append((head, True))
                        else:
                            groups.append(path)
                            arm_meta.append((head, False))

                # 先用 multi_columns 放线性组 + decision；递归臂稍后按列坐标放
                linear_groups = []
                for g, (_h, rec) in zip(groups, arm_meta):
                    linear_groups.append([] if rec else g)

                gen.layout_multi_columns(
                    decision_id=cur,
                    branch_groups=linear_groups,
                    merge_id=None,
                    center_x=cx,
                )
                for g in linear_groups:
                    placed.update(g)

                # 列中心：支路内再分叉时加宽列距，避免与邻列嵌套 yes/no 重叠
                n = len(arms)
                has_nested = any(rec for _h, rec in arm_meta)
                col_gap = 720 if has_nested else gen.HORIZONTAL_GAP
                total_span = (n - 1) * col_gap
                left_center = cx - total_span / 2.0
                # 同步加宽 multi_columns 已放的线性臂（若有）
                if has_nested and any(linear_groups):
                    gen.layout_multi_columns(
                        decision_id=cur,
                        branch_groups=linear_groups,
                        merge_id=None,
                        center_x=cx,
                        col_gap=col_gap,
                    )
                col_bottoms = []
                start_y = gen.nodes[cur].bottom + gen.VERTICAL_GAP
                for i, (head, rec) in enumerate(arm_meta):
                    col_cx = int(left_center + i * col_gap)
                    if rec:
                        # stop=merge 但不在子调用里放置 merge
                        by = place_from(head, col_cx, start_y, merge)
                        col_bottoms.append(by)
                    elif linear_groups[i]:
                        last = linear_groups[i][-1]
                        col_bottoms.append(
                            gen.nodes[last].bottom + gen.VERTICAL_GAP
                        )
                    else:
                        col_bottoms.append(start_y)

                bottom = max(col_bottoms) if col_bottoms else start_y
                if merge and merge not in placed:
                    m = gen.nodes[merge]
                    m.x = cx - m.w // 2
                    m.y = bottom + 160
                    placed.add(merge)
                    nonlocal_y = m.bottom + gen.VERTICAL_GAP
                    mout = outgoing.get(merge, [])
                    if len(mout) == 1:
                        cur = mout[0].target
                        continue
                    break
                elif merge and merge in placed:
                    # 已被子布局误放：拉到所有臂下方
                    m = gen.nodes[merge]
                    m.x = cx - m.w // 2
                    m.y = max(m.y, bottom)
                    nonlocal_y = m.bottom + gen.VERTICAL_GAP
                    mout = outgoing.get(merge, [])
                    cur = mout[0].target if len(mout) == 1 else None
                    if cur:
                        continue
                    break
                nonlocal_y = bottom
                break

            # 是/否二分：先算汇合点，再放置（禁止 stop=None 时吞掉后续菱形）
            if lt in DECISION_YN_TYPES and len(outs) == 2:
                yes_f = next(f for f in outs if f.situation == "yes")
                no_f = next(f for f in outs if f.situation == "no")
                merge = find_merge([yes_f.target, no_f.target])
                if stop and merge is None:
                    merge = stop
                arm_stop = merge if merge else stop
                by = place_yn_decision(cur, cx, nonlocal_y, arm_stop, col_gap=200)
                # 外层指定了 stop 时，不在这里放置 stop（交给上层多路布局）
                if merge and merge == stop:
                    nonlocal_y = by
                    break
                if merge and merge not in placed:
                    m = gen.nodes[merge]
                    m.x = cx - m.w // 2
                    m.y = by
                    placed.add(merge)
                    nonlocal_y = m.bottom + gen.VERTICAL_GAP
                    mout = outgoing.get(merge, [])
                    cur = mout[0].target if len(mout) == 1 else None
                    continue
                if merge and merge in placed:
                    m = gen.nodes[merge]
                    m.x = cx - m.w // 2
                    m.y = max(m.y, by)
                    nonlocal_y = m.bottom + gen.VERTICAL_GAP
                    mout = outgoing.get(merge, [])
                    cur = mout[0].target if len(mout) == 1 else None
                    if cur and cur not in placed:
                        continue
                    break
                nonlocal_y = by
                break

            # 仅 yes 或普通单出
            if lt in DECISION_YN_TYPES and len(outs) == 1:
                if outs[0].situation not in (None, "yes"):
                    raise ValueError(
                        f"single-out decision {cur} must be situation=yes"
                    )

            chain = collect_linear(cur, stop)
            # collect_linear 在分叉处会包含分叉节点；若当前就是分叉已在上面处理
            if chain and meta[chain[-1]]["layout_type"] == "branch":
                # 放到分叉前的线性，再 loop 分叉
                pre, dec = chain[:-1], chain[-1]
                nonlocal_y = place_vertical_at(pre, cx, nonlocal_y)
                cur = dec
                continue
            if (
                chain
                and meta[chain[-1]]["layout_type"] in DECISION_YN_TYPES
                and len(outgoing.get(chain[-1], [])) == 2
            ):
                pre, dec = chain[:-1], chain[-1]
                nonlocal_y = place_vertical_at(pre, cx, nonlocal_y)
                cur = dec
                continue

            nonlocal_y = place_vertical_at(chain, cx, nonlocal_y)
            if not chain:
                break
            last = chain[-1]
            outs_l = outgoing.get(last, [])
            if meta[last]["layout_type"] == "end" or not outs_l:
                break
            if len(outs_l) != 1:
                cur = last  # 交给下一轮分叉逻辑
                if last in placed:
                    # 已放置但仍有多出边 — 异常
                    raise ValueError(
                        f"auto layout stuck at {last} with {len(outs_l)} outs"
                    )
                continue
            nxt = outs_l[0].target
            if nxt == stop or nxt in placed:
                break
            cur = nxt

        return nonlocal_y

    place_from(starts[0], center_x, cursor_y, None)

    missing = [nid for nid in gen.node_order if nid not in placed]
    if missing:
        raise ValueError(
            f"auto layout left nodes unplaced: {missing}; provide IR.layout"
        )


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
