# XML 生成硬规则（摘要）

生成前 **必须 Read**：

| 文件 | 用途 |
|------|------|
| `references/element_schema.json` | 元件结构、ext:data、必填字段 |
| `references/node_reference.md` | 完整节点示例与坐标 |
| `references/xml_template.xml` | 唯一模板骨架 |

**唯一规则来源 = 上述文件。** 禁止凭记忆、禁止用训练知识 invent 元件结构。  
编译失败后修正前，必须重新 Read 上述文件。

## 输出形态

- 禁止 `<?xml`、`<bpmn2:definitions>`、`xmlns`
- 直接以 `<bpmn2:process>` 开头，后接 `<bpmndi:BPMNDiagram>`
- BPMNPlane：**先全部 Shape，再全部 Edge**
- Shape id = `{node_id}_di`；Edge id = `{flow_id}_di`
- `bpmnElement` / `sourceRef` / `targetRef` / `incoming` / `outgoing` ID 必须完全一致

## 节点映射（速查）

| SOP | 节点 |
|-----|------|
| 开/关/写值 | `io:dcs` |
| 单条件 | `flow:or` |
| 多条件全满足 | `flow:and` |
| 多选一 | `flow:branch` |
| 延时 | `timer:wait` |
| 超时判断 | `timer:cond` |
| 仅提示 | `msg:guide` |
| 等待确认 | `msg:confirm` |
| 同时操作 | `flow:parallel1` |
| 引用子程序 | `flow:subproc` |

条件节点（or/and/cond）**必须**两条 outgoing：yes + no。

## 连线 ext:data

| 源节点 | 变体 | ext:data |
|--------|------|----------|
| 普通节点 | plain | `{"lineType":1}` |
| or/and/cond 是 | situation_yes | `{"situation":"yes"}`（禁止含 lineType） |
| or/and/cond 否 | situation_no | `{"situation":"no"}` |
| branch 分支 | branch_option | `{"situation":"{索引}"}` |

**禁止手写连线 XML。** 必须用 `scripts/layout_generator.py`：

```python
from layout_generator import LayoutGenerator
gen = LayoutGenerator()
# add_node / add_flow / layout_vertical 或 layout_parallel1
assert not gen.check_overlaps()
assert not gen.check_connection_integrity()
# get_incoming_outgoing_xml / get_sequence_flow_xml / get_diagram_xml
```

## 标签格式

- DCS：`#(path.tag)` —— type `1` 模拟量，`3` 数字量
- 变量/计时器：`$(NAME)`
- 后缀：`_MANON` 启、`_MANOF` 停、`_AUTOOPT` 切手动、`_OUT` 输出、`_MODE` 模式

## 布局

- 垂直间距 ≥100px；并行分支水平间距 ≥300px
- 并行容器含 `parallelStart` / `parallelEnd`，Shape 设 `isExpanded="true"`
- 生成后：`check_overlaps()`、`check_connection_integrity()`、并行时 `check_parallel_integrity()` 必须为空

完整示例与尺寸表见 `node_reference.md`。
