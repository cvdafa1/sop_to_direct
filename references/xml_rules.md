# XML 生成硬规则（摘要）

**权威来源优先级：**

1. `test/1.xml`（平台导出黄金样例）
2. `references/golden_xml_rules.md`（从黄金样例归纳）
3. `references/xml_template.xml` / `element_schema.json` / `node_reference.md`

生成前必须 Read：`golden_xml_rules.md` + `xml_template.xml` + `element_schema.json`。

---

## 连线不显示：按黄金样例修正后的规则

| # | 规则（来自 test/1.xml） |
|---|-------------------------|
| 1 | 每条 `sequenceFlow` 必须有同 id 的 `BPMNEdge` |
| 2 | Diagram：**先全部 Edge，再全部 Shape** |
| 3 | **普通连线自闭合、无 ext:data** |
| 4 | 条件连线：`name="是"`/`name="否"` + `{"situation":"yes|no"}` |
| 5 | 条件 Edge 宜含 `BPMNLabel` |

```python
from layout_generator import LayoutGenerator
gen = LayoutGenerator()
# add_node / add_flow / layout_*
full_xml = gen.assemble_full_xml(node_xml_by_id)
# python scripts/validate_bpmn.py out.xml
```

禁止手拼 diagram；禁止再用「条件成立/条件不成立」命名；禁止要求 plain 必须带 `lineType`（与黄金样例冲突）。

---

## 输出形态

- 禁止 `<?xml`、`<bpmn2:definitions>`、`xmlns`
- `<bpmn2:process>` 后接 `<bpmndi:BPMNDiagram>`
- Shape id = `{node_id}_di`；Edge id = `{flow_id}_di`

## 节点映射（速查）

| SOP | 节点 |
|-----|------|
| 开/关/写值 | `io:dcs` |
| 写变量 | `io:var` |
| 单条件 | `flow:or` |
| 多条件全满足 | `flow:and` |
| 延时 | `timer:wait` |
| 仅提示 | `msg:guide` |
| 等待确认 | `msg:confirm` |
| 报警 | `msg:alarm` |
| 引用子程序 | `flow:subproc` |

## 标签

- DCS：`#(…)` 变量：`$(…)`

完整字段与拓扑见 `golden_xml_rules.md` 与 `test/1.xml`。
