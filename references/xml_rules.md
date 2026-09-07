# XML 生成硬规则（摘要）

生成前 **必须 Read**：

| 文件 | 用途 |
|------|------|
| `references/element_schema.json` | 元件结构、ext:data、必填字段 |
| `references/node_reference.md` | 完整节点示例与坐标 |
| `references/xml_template.xml` | 唯一模板骨架 |

**唯一规则来源 = 上述文件。** 禁止凭记忆。编译失败后修正前必须重新 Read。

---

## 连线不显示：根因与强制做法（最高优先级）

Direct 画布上「有节点、无连线」几乎总是下面几类问题：

| # | 根因 | 后果 |
|---|------|------|
| 1 | 有 `sequenceFlow` 但缺少对应 `BPMNEdge` | **不画线** |
| 2 | `sequenceFlow.id` ≠ `BPMNEdge.bpmnElement` | **不画线** |
| 3 | `sequenceFlow` 自闭合、缺少 `<ext:data>`（plain 缺 `lineType:1`） | **常不画线** |
| 4 | 只写了节点 `incoming`/`outgoing`，未写 sequenceFlow + Edge | **不画线** |
| 5 | Shape/Edge 顺序颠倒，或未调用 layout（坐标全 0） | 线叠在一起或异常 |

**强制流程（禁止手拼连线）：**

```python
from layout_generator import LayoutGenerator

gen = LayoutGenerator()
# 1) add_node / add_flow（与节点 id、flow id 规划一致）
# 2) layout_vertical(...) 或 layout_parallel1(...)
# 3) assert not gen.check_connection_integrity()
# 4) assert not gen.check_overlaps()
# 5) 准备 node_xml_by_id = {每个节点 id: 节点 XML（可无 incoming/outgoing）}
full_xml = gen.assemble_full_xml(node_xml_by_id)  # 一次产出 process+diagram
# 6) python scripts/validate_bpmn.py out.xml
```

`assemble_full_xml` 保证：同一套 flow id → sequenceFlow + Edge、先 Shape 后 Edge、plain 带 `lineType`、节点 IO 与 flow 一致。

**禁止：**

- 手写 `<bpmn2:sequenceFlow ... />` 自闭合
- 只生成 Shape、忘了 Edge
- process 里 flow id 与 diagram 里 `bpmnElement` 各写一套
- 跳过 `assemble_full_xml`，自行字符串拼接 diagram

---

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

## 标签格式

- DCS：`#(path.tag)` —— type `1` 模拟量，`3` 数字量
- 变量/计时器：`$(NAME)`

## 布局

- 垂直间距 ≥100px；并行分支水平间距 ≥300px
- 并行容器含 `parallelStart` / `parallelEnd`，Shape 设 `isExpanded="true"`
- 生成后：`check_overlaps()`、`check_connection_integrity()` 必须为空

完整示例与尺寸表见 `node_reference.md`。
