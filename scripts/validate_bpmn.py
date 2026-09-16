#!/usr/bin/env python3
"""BPMN XML 结构初检：保存前发现常见导致编译/显示失败的问题。

用法:
    python scripts/validate_bpmn.py path/to/main.xml [path/to/sub.xml ...]
    python scripts/validate_bpmn.py --fix path/to/main.xml [path/to/sub.xml ...]
退出码: 0=通过, 1=存在错误

元件白名单来自 references/element_schema.json（另含并行内嵌的
flow:parallelStart / flow:parallelEnd）。未定义元件一律报错。

子程序 / 计时器 / 程序变量名须为 [A-Za-z0-9_]；`--fix` 时就地改写非法名。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from api_reference import (
    extract_subproc_refs,
    find_invalid_xml_idents,
    sanitize_xml_ident_names,
)
from schema_loader import components_by_element


FORBIDDEN_PATTERNS = [
    (r"<\?xml", "forbidden XML declaration"),
    (r"<bpmn2:definitions", "forbidden bpmn2:definitions wrapper"),
    (r"\sxmlns[:=]", "forbidden xmlns declaration"),
]

# 并行容器内嵌元件（在 schema 的 parallel 子结构中定义，非独立 components）
NESTED_ALLOWED = frozenset({"flow:parallelStart", "flow:parallelEnd"})


def _load_allowed_elements() -> frozenset[str]:
    return frozenset(components_by_element()) | NESTED_ALLOWED


def _check_undefined_elements(text: str, allowed: frozenset[str]) -> list[str]:
    """校验 process 内业务元件均在 element_schema 白名单中。"""
    errors: list[str] = []
    process_m = re.search(
        r"<bpmn2:process\b[^>]*>(.*?)</bpmn2:process>",
        text,
        re.DOTALL,
    )
    body = process_m.group(1) if process_m else text

    found = set()
    for m in re.finditer(
        r"<(flow|io|msg|timer|util):([A-Za-z][A-Za-z0-9]*)\b",
        body,
    ):
        tag = f"{m.group(1)}:{m.group(2)}"
        found.add(tag)
        if tag not in allowed:
            errors.append(f"undefined element (not in element_schema.json): {tag}")

    if not errors and not found:
        errors.append("no defined flow/io/msg/timer elements found in process")
    return errors


def _check_file(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    allowed = _load_allowed_elements()

    if not text.strip().startswith("<bpmn2:process"):
        errors.append("must start with <bpmn2:process")

    if "<bpmn2:process" not in text:
        errors.append("missing <bpmn2:process>")
    if "<bpmndi:BPMNDiagram" not in text:
        errors.append("missing <bpmndi:BPMNDiagram>")
    if "<flow:start" not in text:
        errors.append("missing flow:start")
    if "<flow:end" not in text:
        errors.append("missing flow:end")

    for pat, msg in FORBIDDEN_PATTERNS:
        if re.search(pat, text):
            errors.append(msg)

    # 强制：仅允许 schema 已定义元件
    errors.extend(_check_undefined_elements(text, allowed))

    if "PLACEHOLDER" in text:
        errors.append("PLACEHOLDER leftover in generated XML")

    # 子程序 / 计时器 / 程序变量标识符：仅 [A-Za-z0-9_]
    for kind, raw in find_invalid_xml_idents(text):
        errors.append(
            f"invalid {kind} name {raw!r}: only [A-Za-z0-9_] allowed "
            f"(re-run with --fix or fix IR then ir_to_xml)"
        )

    # Plane 内先全部 Edge，再全部 Shape（见 golden_xml_rules）
    plane_m = re.search(
        r"<bpmndi:BPMNPlane\b[^>]*>(.*?)</bpmndi:BPMNPlane>",
        text,
        re.DOTALL,
    )
    if plane_m:
        plane = plane_m.group(1)
        first_edge = plane.find("<bpmndi:BPMNEdge")
        first_shape = plane.find("<bpmndi:BPMNShape")
        last_edge = plane.rfind("<bpmndi:BPMNEdge")
        if first_edge != -1 and first_shape != -1:
            if first_shape < first_edge:
                errors.append(
                    "BPMNShape appears before BPMNEdge (golden: all Edges then all Shapes)"
                )
            elif last_edge > first_shape:
                errors.append(
                    "BPMNEdge appears after a BPMNShape (golden: all Edges then all Shapes)"
                )

    # 位号：name 字段里像路径但未用 #() 包裹的粗检
    for m in re.finditer(r'"name"\s*:\s*"([^"]+)"', text):
        name = m.group(1)
        if not name or name.startswith("$("):
            continue
        if name.startswith("#(") and name.endswith(")"):
            continue
        # 含点且像设备路径时提醒
        if "." in name and re.search(r"[A-Za-z]", name):
            errors.append(f"tag may need #() wrap: {name}")

    # ID 匹配：sequenceFlow id vs Edge bpmnElement
    flow_ids = set(re.findall(r'<bpmn2:sequenceFlow\s+[^>]*\bid="([^"]+)"', text))
    edge_refs = set(re.findall(r'<bpmndi:BPMNEdge\s+[^>]*\bbpmnElement="([^"]+)"', text))
    missing_edges = flow_ids - edge_refs
    orphan_edges = edge_refs - flow_ids
    if missing_edges:
        errors.append(
            f"sequenceFlow without Edge (lines will NOT show): {sorted(missing_edges)[:8]}"
        )
    if orphan_edges:
        errors.append(f"Edge without sequenceFlow: {sorted(orphan_edges)[:8]}")
    if not flow_ids:
        errors.append("no sequenceFlow elements (lines will NOT show)")
    if flow_ids and not edge_refs:
        errors.append("has sequenceFlow but zero BPMNEdge (lines will NOT show)")

    # 连线规则：
    # - plain：可自闭合，无 ext:data
    # - 条件：name 为 是/否，必须有 situation；禁止「条件成立/条件不成立」
    for m in re.finditer(r"<bpmn2:sequenceFlow\b([^>]*)(/?)\s*>", text):
        attrs = m.group(1)
        self_closing = m.group(2) == "/" or m.group(0).rstrip().endswith("/>")
        fid_m = re.search(r'\bid="([^"]+)"', attrs)
        fid = fid_m.group(1) if fid_m else "?"
        name_m = re.search(r'\bname="([^"]*)"', attrs)
        flow_name = name_m.group(1) if name_m else None

        if self_closing:
            if flow_name in ("是", "否", "条件成立", "条件不成立"):
                errors.append(f"condition sequenceFlow must not be self-closing: {fid}")
            continue

        start = m.end()
        end = text.find("</bpmn2:sequenceFlow>", start)
        if end == -1:
            errors.append(f"unclosed sequenceFlow: {fid}")
            continue
        body = text[start:end]
        if flow_name in ("是", "否") or flow_name in ("条件成立", "条件不成立"):
            if '"situation"' not in body:
                errors.append(f"condition sequenceFlow missing situation: {fid}")
            if flow_name in ("条件成立", "条件不成立"):
                errors.append(
                    f"use name 是/否 not 条件成立/条件不成立: {fid}"
                )
        elif flow_name is not None and re.fullmatch(r"\d+", flow_name or ""):
            pass
        # plain with body: if has ext:data, situation/lineType both acceptable; not required

    # Edge 至少 2 个 waypoint
    for m in re.finditer(
        r'<bpmndi:BPMNEdge\b[^>]*\bbpmnElement="([^"]+)"[^>]*>(.*?)</bpmndi:BPMNEdge>',
        text,
        re.DOTALL,
    ):
        wps = re.findall(r"<di:waypoint\b", m.group(2))
        if len(wps) < 2:
            errors.append(f"BPMNEdge needs >=2 waypoints: {m.group(1)}")

    # incoming/outgoing 引用的 Flow 必须存在
    for ref in re.findall(r"<bpmn2:incoming>([^<]+)</bpmn2:incoming>", text):
        if ref not in flow_ids:
            errors.append(f"incoming refs unknown flow: {ref}")
    for ref in re.findall(r"<bpmn2:outgoing>([^<]+)</bpmn2:outgoing>", text):
        if ref not in flow_ids:
            errors.append(f"outgoing refs unknown flow: {ref}")

    node_ids = set()
    for tag in sorted(allowed):
        node_ids.update(re.findall(rf'<{re.escape(tag)}\s+[^>]*\bid="([^"]+)"', text))

    shape_refs = set(re.findall(r'<bpmndi:BPMNShape\s+[^>]*\bbpmnElement="([^"]+)"', text))
    missing_shapes = node_ids - shape_refs
    if missing_shapes:
        errors.append(f"node without Shape: {sorted(missing_shapes)[:8]}")

    for tag in ("flow:or", "flow:and", "timer:cond"):
        for block in re.finditer(
            rf"<{re.escape(tag)}\b[^>]*>(.*?)</{re.escape(tag)}>",
            text,
            re.DOTALL,
        ):
            outs = re.findall(r"<bpmn2:outgoing>([^<]+)</bpmn2:outgoing>", block.group(1))
            nid = re.search(r'\bid="([^"]+)"', block.group(0))
            nid_s = nid.group(1) if nid else "?"
            if len(outs) not in (1, 2):
                errors.append(
                    f"{tag} outgoing must be 1 (yes only) or 2 (yes+no), got {len(outs)}: {nid_s}"
                )
                continue
            # 校验对应 sequenceFlow 的 situation
            situations = []
            for fid in outs:
                # find flow by id
                fm = re.search(
                    rf'<bpmn2:sequenceFlow\b[^>]*\bid="{re.escape(fid)}"[^>]*(?:/>|>(.*?)</bpmn2:sequenceFlow>)',
                    text,
                    re.DOTALL,
                )
                if not fm:
                    errors.append(f"{tag} outgoing {fid} has no sequenceFlow: {nid_s}")
                    continue
                chunk = fm.group(0)
                if '"situation":"yes"' in chunk or '"situation": "yes"' in chunk:
                    situations.append("yes")
                elif '"situation":"no"' in chunk or '"situation": "no"' in chunk:
                    situations.append("no")
            if "yes" not in situations:
                errors.append(f"{tag} must have situation=yes outgoing: {nid_s}")
            if len(outs) == 2 and "no" not in situations:
                errors.append(f"{tag} with 2 outgoing must include situation=no: {nid_s}")

    errors.extend(_check_layout_geometry(text))
    return errors


def _parse_bounds(text: str) -> dict[str, tuple[float, float, float, float]]:
    """bpmnElement → (x, y, x2, y2)"""
    out = {}
    for m in re.finditer(
        r'<bpmndi:BPMNShape\b[^>]*\bbpmnElement="([^"]+)"[^>]*>\s*'
        r'<dc:Bounds\s+x="([^"]+)"\s+y="([^"]+)"\s+width="([^"]+)"\s+height="([^"]+)"',
        text,
        re.DOTALL,
    ):
        nid, x, y, w, h = m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5))
        out[nid] = (x, y, x + w, y + h)
    return out


def _parse_edge_waypoints(text: str) -> dict[str, list[tuple[float, float]]]:
    out = {}
    for m in re.finditer(
        r'<bpmndi:BPMNEdge\b[^>]*\bbpmnElement="([^"]+)"[^>]*>(.*?)</bpmndi:BPMNEdge>',
        text,
        re.DOTALL,
    ):
        pts = [
            (float(a), float(b))
            for a, b in re.findall(r'<di:waypoint\s+x="([^"]+)"\s+y="([^"]+)"', m.group(2))
        ]
        out[m.group(1)] = pts
    return out


def _rects_overlap(a, b, gap=0.0) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (
        ax2 + gap <= bx1 or bx2 + gap <= ax1 or ay2 + gap <= by1 or by2 + gap <= ay1
    )


def _seg_hits_rect(x1, y1, x2, y2, rx1, ry1, rx2, ry2, pad=4.0) -> bool:
    rx1 -= pad
    ry1 -= pad
    rx2 += pad
    ry2 += pad
    eps = 0.5
    if abs(x1 - x2) < 1e-6:
        x = x1
        ymin, ymax = sorted([y1, y2])
        if x <= rx1 + eps or x >= rx2 - eps:
            return False
        return ymax > ry1 + eps and ymin < ry2 - eps
    if abs(y1 - y2) < 1e-6:
        y = y1
        xmin, xmax = sorted([x1, x2])
        if y <= ry1 + eps or y >= ry2 - eps:
            return False
        return xmax > rx1 + eps and xmin < rx2 - eps
    return False


def _hv_proper_cross(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2) -> bool:
    a_vert = abs(ax1 - ax2) < 1e-6
    b_vert = abs(bx1 - bx2) < 1e-6
    if a_vert == b_vert:
        return False
    if a_vert:
        vx, ymin, ymax = ax1, *sorted([ay1, ay2])
        hy, xmin, xmax = by1, *sorted([bx1, bx2])
    else:
        hy, xmin, xmax = ay1, *sorted([ax1, ax2])
        vx, ymin, ymax = bx1, *sorted([by1, by2])
    return xmin < vx < xmax and ymin < hy < ymax


def _hv_collinear_overlap(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2, min_len=1.0) -> bool:
    a_vert = abs(ax1 - ax2) < 1e-6
    a_horz = abs(ay1 - ay2) < 1e-6
    b_vert = abs(bx1 - bx2) < 1e-6
    b_horz = abs(by1 - by2) < 1e-6
    if a_vert and b_vert:
        if abs(ax1 - bx1) > 1e-6:
            return False
        a0, a1 = sorted([ay1, ay2])
        b0, b1 = sorted([by1, by2])
        return min(a1, b1) - max(a0, b0) > min_len
    if a_horz and b_horz:
        if abs(ay1 - by1) > 1e-6:
            return False
        a0, a1 = sorted([ax1, ax2])
        b0, b1 = sorted([bx1, bx2])
        return min(a1, b1) - max(a0, b0) > min_len
    return False


def _point_near(x, y, px, py, tol=2.0) -> bool:
    return abs(x - px) <= tol and abs(y - py) <= tol


def _seg_touches_port(seg, bounds_map, node_id, port: str) -> bool:
    rect = bounds_map.get(node_id)
    if not rect:
        return False
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) / 2.0
    py = y1 if port == "top" else y2
    sx1, sy1, sx2, sy2 = seg
    return _point_near(sx1, sy1, cx, py) or _point_near(sx2, sy2, cx, py)


# 与 layout_generator.EDGE_OVERLAP_MIN_LEN 对齐
_EDGE_OVERLAP_MIN_LEN = 12.0


def _check_layout_geometry(text: str) -> list[str]:
    """节点重叠、连线穿节点、正交边交叉、无关连线长距离共线重叠。"""
    errors: list[str] = []
    bounds = _parse_bounds(text)
    edges = _parse_edge_waypoints(text)
    if not bounds:
        return errors

    # 跳过极扁/极窄（pstart/pend）与明显大容器
    skip = set()
    for nid, (x1, y1, x2, y2) in bounds.items():
        w, h = x2 - x1, y2 - y1
        if h <= 8 or w <= 8 or w >= 500 or h >= 400:
            skip.add(nid)

    ids = [i for i in bounds if i not in skip]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if _rects_overlap(bounds[a], bounds[b]):
                errors.append(f"shape overlap: {a} / {b}")

    # flow endpoints for through-node exemption
    flow_ends = {}
    for m in re.finditer(
        r'<bpmn2:sequenceFlow\s+[^>]*\bid="([^"]+)"[^>]*\bsourceRef="([^"]+)"[^>]*\btargetRef="([^"]+)"',
        text,
    ):
        flow_ends[m.group(1)] = (m.group(2), m.group(3))
    # attribute order may vary
    for m in re.finditer(r"<bpmn2:sequenceFlow\b([^>]*)(/?)\s*>", text):
        attrs = m.group(1)
        fid = re.search(r'\bid="([^"]+)"', attrs)
        src = re.search(r'\bsourceRef="([^"]+)"', attrs)
        tgt = re.search(r'\btargetRef="([^"]+)"', attrs)
        if fid and src and tgt:
            flow_ends[fid.group(1)] = (src.group(1), tgt.group(1))

    for eid, pts in edges.items():
        if len(pts) < 2:
            continue
        ends = flow_ends.get(eid, (None, None))
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            for nid, rect in bounds.items():
                if nid in skip or nid in ends:
                    continue
                if _seg_hits_rect(x1, y1, x2, y2, *rect):
                    errors.append(f"edge through node: {eid} → {nid}")
                    break

    eids = list(edges.keys())
    for i in range(len(eids)):
        pa = edges[eids[i]]
        if len(pa) < 2:
            continue
        segs_a = [(pa[k][0], pa[k][1], pa[k + 1][0], pa[k + 1][1]) for k in range(len(pa) - 1)]
        src_a, tgt_a = flow_ends.get(eids[i], (None, None))
        for j in range(i + 1, len(eids)):
            pb = edges[eids[j]]
            if len(pb) < 2:
                continue
            segs_b = [(pb[k][0], pb[k][1], pb[k + 1][0], pb[k + 1][1]) for k in range(len(pb) - 1)]
            src_b, tgt_b = flow_ends.get(eids[j], (None, None))
            crossed = False
            overlapped = False
            share_tgt = bool(tgt_a and tgt_a == tgt_b)
            share_src = bool(src_a and src_a == src_b)
            for sa in segs_a:
                for sb in segs_b:
                    if _hv_proper_cross(*sa, *sb):
                        crossed = True
                    if _hv_collinear_overlap(*sa, *sb, min_len=_EDGE_OVERLAP_MIN_LEN):
                        # 同宿汇合总线 / 同源扇出：允许共线
                        if share_tgt or share_src:
                            pass
                        else:
                            overlapped = True
                if crossed and overlapped:
                    break
            if crossed:
                errors.append(f"edge cross: {eids[i]} × {eids[j]}")
            if overlapped:
                errors.append(f"edge overlap: {eids[i]} × {eids[j]}")

    return errors


def _check_split_files(paths: list[Path], texts: list[str]) -> list[str]:
    """多文件：第一个为主程序，其后为子程序；主 XML 必须引用全部子程序。

    单文件若含 flow:subproc，视为拆分包不完整。
    """
    errors: list[str] = []
    if not texts:
        return errors

    main_text = texts[0]
    refs = extract_subproc_refs(main_text)

    if len(paths) == 1:
        if refs:
            errors.append(
                f"{paths[0].name}: has {len(refs)} flow:subproc but no sub XML "
                f"passed; when split, run: validate_bpmn.py main.xml sub1.xml ..."
            )
        return errors

    # 子程序 XML 自身不应再嵌套未声明的拆分包要求（可有 0 个 flow:subproc）
    sub_paths = paths[1:]
    sub_texts = texts[1:]
    if len(refs) != len(sub_paths):
        errors.append(
            f"split bundle: main has {len(refs)} flow:subproc but "
            f"{len(sub_paths)} sub XML file(s) given"
        )

    for i, ref in enumerate(refs):
        if not ref["name"]:
            errors.append(f"main flow:subproc[{i}] missing name")
        if not ref["subId"]:
            errors.append(f"main flow:subproc[{i}] missing subId")

    for p, t in zip(sub_paths, sub_texts):
        nested = extract_subproc_refs(t)
        if nested:
            errors.append(
                f"{p.name}: subprogram XML should not contain flow:subproc "
                f"({len(nested)} found); nest only in main"
            )
        if not str(t).strip():
            errors.append(f"{p.name}: empty subprogram XML")

    return errors


def main(argv: list[str]) -> int:
    args = argv[1:]
    do_fix = False
    if args and args[0] == "--fix":
        do_fix = True
        args = args[1:]

    if not args:
        print(
            "Usage: python scripts/validate_bpmn.py [--fix] <main.xml> [sub.xml...]",
            file=sys.stderr,
        )
        return 2

    any_err = False
    paths: list[Path] = []
    texts: list[str] = []

    for arg in args:
        path = Path(arg)
        if not path.is_file():
            print(f"[FAIL] {path}: file not found")
            any_err = True
            continue

        if do_fix:
            text = path.read_text(encoding="utf-8")
            new_text, renames = sanitize_xml_ident_names(text)
            if renames:
                path.write_text(new_text, encoding="utf-8")
                print(f"[FIX]  {path}")
                for kind, old, new in renames:
                    print(f"  - {kind}: {old!r} → {new!r}")

        errs = _check_file(path)
        if errs:
            any_err = True
            print(f"[FAIL] {path}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"[OK]   {path}")
        paths.append(path)
        texts.append(path.read_text(encoding="utf-8"))

    if paths:
        split_errs = _check_split_files(paths, texts)
        if split_errs:
            any_err = True
            print("[FAIL] split bundle")
            for e in split_errs:
                print(f"  - {e}")
        elif len(paths) > 1:
            print(f"[OK]   split bundle: main + {len(paths) - 1} sub(s)")

    return 1 if any_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
