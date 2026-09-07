# 黄金 XML 规则（权威结构）

生成/修正 XML 时以本文为准；节点字段见 `element_schema.json` / `node_reference.md`；骨架见 `xml_template.xml`。

---

## 1. 整体结构

```
<bpmn2:process id="Process_1" isExecutable="true">
  …节点与 sequenceFlow（可交错）…
</bpmn2:process>
<bpmndi:BPMNDiagram id="BPMNDiagram_1">
  <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
    …全部 BPMNEdge…
    …全部 BPMNShape…
  </bpmndi:BPMNPlane>
</bpmndi:BPMNDiagram>
```

- 无 `<?xml` / `definitions` / `xmlns`
- process 与 diagram 为兄弟
- **Diagram：先全部 Edge，再全部 Shape**

---

## 2. ID

| 类型 | 模式 |
|------|------|
| 开始/结束 | `Event_` + 随机串 |
| 活动 | `Activity_` + 随机串 |
| 连线 | `Flow_` + 随机串 |
| Shape / Edge | `{id}_di` |

`bpmnElement` / `sourceRef` / `targetRef` / `incoming` / `outgoing` 必须逐字一致。

---

## 3. 连线（防「有节点无连线」）

**plain（非条件出边）— 自闭合、无 ext:data：**

```xml
<bpmn2:sequenceFlow id="Flow_xxx" sourceRef="A" targetRef="B" />
```

**条件（or/and/cond）— name 用 `是`/`否`，仅 situation：**

```xml
<bpmn2:sequenceFlow id="Flow_yes" name="是" sourceRef="Or" targetRef="A">
  <ext:data><![CDATA[{"situation":"yes"}]]></ext:data>
</bpmn2:sequenceFlow>
<bpmn2:sequenceFlow id="Flow_no" name="否" sourceRef="Or" targetRef="B">
  <ext:data><![CDATA[{"situation":"no"}]]></ext:data>
</bpmn2:sequenceFlow>
```

禁止：`条件成立`/`条件不成立`；禁止 plain 强制 `lineType`；禁止条件边带 `lineType`。

**BPMNEdge：** 每条 Flow 一条；`bpmnElement` = Flow id；≥2 waypoint；是/否边宜含 `BPMNLabel`。

条件节点必须 2 条 outgoing。

---

## 4. 尺寸

| 类型 | 宽×高 |
|------|--------|
| start / end | 54×54 |
| 活动节点 | 200×60 |

---

## 5. 标签

- DCS：`#(…)` 变量：`$(…)`

---

## 6. 强制生成

```python
from layout_generator import LayoutGenerator
gen = LayoutGenerator()
# add_node / add_flow / layout_*
xml = gen.assemble_full_xml(node_xml_by_id)
# python scripts/validate_bpmn.py out.xml  # 必须通过
```

禁止手拼 sequenceFlow / Edge / Diagram。
