# 黄金 XML 规则（权威来源：`test/1.xml`）

本文件由平台导出的标准 XML 归纳。**与本文冲突时，以 `test/1.xml` 为准。**

覆盖元件：`flow:start` / `flow:end` / `msg:confirm` / `flow:or` / `flow:and` / `flow:subproc` / `msg:alarm` / `msg:guide` / `timer:wait` / `io:dcs` / `io:var`

---

## 1. 整体结构

```
<bpmn2:process id="Process_1" isExecutable="true">
  …节点与 sequenceFlow（可交错排列）…
</bpmn2:process>
<bpmndi:BPMNDiagram id="BPMNDiagram_1">
  <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
    …BPMNEdge（全部）…
    …BPMNShape（全部）…
  </bpmndi:BPMNPlane>
</bpmndi:BPMNDiagram>
```

硬性约定：

- 无 `<?xml`、无 `definitions`、无 `xmlns`
- process 与 diagram 为**兄弟**，不是嵌套
- **Diagram 内：先全部 Edge，后全部 Shape**（与旧文档「先 Shape 后 Edge」相反；以本黄金样例为准）

---

## 2. ID 命名

| 类型 | 模式 | 示例 |
|------|------|------|
| 开始/结束 | `Event_` + 随机串 | `Event_0vi0df5` |
| 活动节点 | `Activity_` + 随机串 | `Activity_0lr9tlo` |
| 连线 | `Flow_` + 随机串 | `Flow_0hujyfp` |
| Shape | `{nodeId}_di` | `Event_0vi0df5_di` |
| Edge | `{flowId}_di` | `Flow_0hujyfp_di` |

`bpmnElement` / `sourceRef` / `targetRef` / `incoming` / `outgoing` 必须与上述 id **逐字相同**。

---

## 3. 连线（sequenceFlow）— 画线关键

### 3.1 普通连线（plain）

平台导出为**自闭合、无 ext:data**：

```xml
<bpmn2:sequenceFlow id="Flow_0hujyfp" sourceRef="Event_0vi0df5" targetRef="Activity_0lr9tlo" />
```

适用于：start、confirm、subproc、alarm、guide、wait、dcs、var 等非条件出边。

**不要**强制加 `{"lineType":1}`（黄金样例没有）。

### 3.2 条件连线（or / and / timer:cond）

必须带 `name` + `ext:data.situation`：

```xml
<bpmn2:sequenceFlow id="Flow_0kokvtf" name="是" sourceRef="Activity_1ue7wmo" targetRef="Activity_0s8r446">
  <ext:data><![CDATA[{"situation":"yes"}]]></ext:data>
</bpmn2:sequenceFlow>
<bpmn2:sequenceFlow id="Flow_03drof5" name="否" sourceRef="Activity_1ue7wmo" targetRef="Event_1j5qm9u">
  <ext:data><![CDATA[{"situation":"no"}]]></ext:data>
</bpmn2:sequenceFlow>
```

| 项 | 黄金值 | 禁止 |
|----|--------|------|
| name | `是` / `否` | `条件成立` / `条件不成立` |
| ext:data | 仅 `situation` | 同时带 `lineType` |

条件节点必须 2 条 outgoing（是 + 否）。outgoing 书写顺序不强制。

### 3.3 BPMNEdge

- 每条 sequenceFlow **必须**有一条 Edge：`id="{flowId}_di"`，`bpmnElement="{flowId}"`
- 至少 2 个 `<di:waypoint>`；折线常见 4 个点
- **带 name 的连线**（是/否）Edge 内宜含 `BPMNLabel`：

```xml
<bpmndi:BPMNEdge id="Flow_0kokvtf_di" bpmnElement="Flow_0kokvtf">
  <di:waypoint x="320" y="320" />
  <di:waypoint x="320" y="360" />
  <bpmndi:BPMNLabel>
    <dc:Bounds x="260" y="324" width="120" height="12" />
  </bpmndi:BPMNLabel>
</bpmndi:BPMNEdge>
```

---

## 4. 节点尺寸（黄金样例）

| 类型 | 宽×高 |
|------|--------|
| flow:start / flow:end | 54×54 |
| 活动类（confirm/or/and/subproc/alarm/guide/wait/dcs/var…） | 200×60 |

---

## 5. 各元件 ext:data 要点（摘自样例）

### msg:confirm

- `message`、`type:"only"`、`display:"yes"`
- `set` 数组可含 `row` 时间戳风格数值

### flow:or / flow:and

```json
{
  "subTitle": "",
  "showDetail": true,
  "keep": 0,
  "data": [{ "name": "#(TAG)", "judge": ">", "targetValue": "10", "row": 0, "type": 3 }]
}
```

### flow:subproc

- 属性：`name` + `subId`（真实子程序 ID）
- ext:data：`subTitle/showDetail/showQueue/data/interval/trends/resourceGroupId/conditions/deviceId`

### msg:alarm / msg:guide

- 均有 `message`、`display`、`isMute`、`isPersistent` 等；**不暂停**流程语义由元件类型区分

### timer:wait

```json
{
  "type": "specifiedTime",
  "integerTime": 10,
  "specifiedTime": "00:00:10",
  "version": 1,
  "showDetail": true
}
```

### io:dcs

- 位号：`#(…)`；`outputMod:"periodic"`；`errorHandler.handler` 可为 `"retry"`
- `data[].type`：数字量常用 `3`

### io:var

- 变量：`$(name)`；`data[].type` 为数值类型

---

## 6. 标签引用

| 形式 | 用途 | 样例 |
|------|------|------|
| `#(…)` | DCS 位号 | `#(HIC_V1001A_1.MAN)` |
| `$(…)` | 程序变量 | `$(bl)` |

---

## 7. 生成强制流程（防「有节点无连线」）

```python
from layout_generator import LayoutGenerator
gen = LayoutGenerator()
# add_node / add_flow / layout_*
xml = gen.assemble_full_xml(node_xml_by_id)  # Edge 在前、Shape 在后；plain 自闭合；是/否命名
# python scripts/validate_bpmn.py out.xml
```

对照检查：

1. `len(sequenceFlow) == len(BPMNEdge)` 且 id 一一对应  
2. Diagram 中第一个图形子元素是 `BPMNEdge`，Shape 在全部 Edge 之后  
3. 条件边 `name` 为 `是`/`否`，且仅有 `situation`  
4. 与 `test/1.xml` 结构一致后再 save  

---

## 8. 样例拓扑（便于回归）

```
start → confirm → or
                 ├─ 否 → end
                 └─ 是 → subproc → and
                                  ├─ 是 → end
                                  └─ 否 → alarm → guide → wait → dcs → var → end
```
