#!/usr/bin/env python3
"""BPMN XML 结构初检：保存前发现常见导致编译/显示失败的问题。

用法:
    python scripts/validate_bpmn.py path/to/main.xml [path/to/sub.xml ...]
退出码: 0=通过, 1=存在错误
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


FORBIDDEN_PATTERNS = [
    (r"<\?xml", "forbidden XML declaration"),
    (r"<bpmn2:definitions", "forbidden bpmn2:definitions wrapper"),
    (r"\sxmlns[:=]", "forbidden xmlns declaration"),
]


def _check_file(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")

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

    # PLACEHOLDER is OK only in the skill template file
    if "PLACEHOLDER" in text and path.name != "xml_template.xml":
        errors.append("PLACEHOLDER leftover in generated XML")

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
            # template uses #(PLACEHOLDER.TAG_NAME) which is fine
            if "PLACEHOLDER" in name:
                continue
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
    for tag in (
        "flow:start", "flow:end", "io:dcs", "io:var", "io:calc",
        "flow:or", "flow:and", "flow:branch", "flow:subproc",
        "flow:parallel1", "flow:parallel2", "flow:parallelStart", "flow:parallelEnd",
        "timer:wait", "timer:cond", "timer:start", "timer:restart", "timer:stop",
        "timer:pause", "timer:clock", "msg:guide", "msg:confirm", "msg:alarm",
        "flow:risingEdge", "flow:fallingEdge", "flow:request",
        "io:concat", "io:fileExport", "io:fileImport", "io:modifyLabel", "io:modifyProps",
        "util:text",
    ):
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
            if len(outs) != 2:
                nid = re.search(r'\bid="([^"]+)"', block.group(0))
                errors.append(
                    f"{tag} needs 2 outgoing, got {len(outs)}: "
                    f"{nid.group(1) if nid else '?'}"
                )

    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python scripts/validate_bpmn.py <xml> [xml...]", file=sys.stderr)
        return 2

    any_err = False
    for arg in argv[1:]:
        path = Path(arg)
        if not path.is_file():
            print(f"[FAIL] {path}: file not found")
            any_err = True
            continue
        errs = _check_file(path)
        if errs:
            any_err = True
            print(f"[FAIL] {path}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"[OK]   {path}")

    return 1 if any_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
