## 0. 元件白名单

定义源：`element_schema.json`（+ 并行内嵌 Start/End）。校验：`validate_bpmn.py`。本文件不列举元件名。

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

**条件（or/and/cond）：**

- **默认 1 条 outgoing（是）**：SOP 只描述「条件成立后做什么」、未写否则/不成立时，只出 `name="是"` + `situation:yes`
- **仅当明确需要否分支时再加第 2 条**：原文有「否则 / 不满足 / 未到位则…」等，才增加 `name="否"` + `situation:no`
- 禁止无依据硬凑「否」空分支；有「否」时两侧都要落到真实后续节点（或 end）

```xml
<!-- 仅「是」 -->
<bpmn2:sequenceFlow id="Flow_yes" name="是" sourceRef="Or" targetRef="A">
  <ext:data><![CDATA[{"situation":"yes"}]]></ext:data>
</bpmn2:sequenceFlow>

<!-- 明确有否则时：是 + 否 -->
<bpmn2:sequenceFlow id="Flow_yes" name="是" sourceRef="Or" targetRef="A">
  <ext:data><![CDATA[{"situation":"yes"}]]></ext:data>
</bpmn2:sequenceFlow>
<bpmn2:sequenceFlow id="Flow_no" name="否" sourceRef="Or" targetRef="B">
  <ext:data><![CDATA[{"situation":"no"}]]></ext:data>
</bpmn2:sequenceFlow>
```

禁止 plain 强制 `lineType`；禁止条件边带 `lineType`。

**BPMNEdge：** 每条 Flow 一条；`bpmnElement` = Flow id；≥2 waypoint；是/否边宜含 `BPMNLabel`。

条件节点 outgoing：**1（仅是）或 2（是+否）**，不得为 0，不得只有「否」没有「是」。

---

## 4. 尺寸与布局（防重叠 / 防交叉）

| 类型 | 宽×高 |
|------|--------|
| start / end | 54×54 |
| 活动节点 | 200×60 |

**槽位（必须用 `LayoutGenerator`）：**

- 主链：`layout_vertical`，垂直间距 ≥100
- 是/否分叉：`layout_branch_columns`（是→左列，否→右列，列距 ≥300）；仅「是」时主链继续竖排即可
- 多路：`layout_multi_columns`
- 并行槽位：本 skill 禁用，见 `element_split.md` R5

**走线：**

- 正交折线；水平段走行间走廊，同层错开 lane；**同源扇出 / 同宿汇合总线允许共线**（无关边禁止长距离叠线）
- 逆向上行/侧向汇合用 U 形绕行
- 保存前 `assemble_full_xml` 会自动扩距/重路由；仍失败则禁止组装——**不得**靠删节点/简化流程过门禁（见 `SKILL.md` Step 3 失败处置）

**硬校验（`validate_bpmn.py` + layout）：** 节点不重叠；边不穿节点；正交边不内部交叉；**无关连线不长距离共线重叠**（同源扇出、同宿汇合总线、端口短重合、以及 ≤12px 的重叠除外）。

---

## 5. 标签

路径与 `#()` / `$()`：**唯一来源** `node_reference.md` §一。

---

## 6. 强制生成

禁止 Agent 手拼节点 / sequenceFlow / Edge / Diagram。命令见 `SKILL.md` Step 3；IR 契约见 `ir_schema.md`。
