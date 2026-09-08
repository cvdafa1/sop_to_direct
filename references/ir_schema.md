# IR 契约（SOP → 确定性编译）

Agent **只产出本文件描述的 IR JSON**；XML 由 `scripts/ir_to_xml.py` 生成。  
禁止在 IR 中写坐标、`incoming`/`outgoing`、sequenceFlow 几何或 Diagram。

元件白名单与 `ext` 字段：`element_schema.json`（唯一来源）。

---

## 顶层

```json
{
  "process_id": "Process_1",
  "nodes": [ /* Node */ ],
  "flows": [ /* Flow */ ],
  "layout": [ /* LayoutOp，可选；省略则自动布局 */ ]
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `process_id` | 否 | 默认 `Process_1` |
| `nodes` | 是 | 顺序即 process 内节点顺序 |
| `flows` | 是 | 全部连线；条件边带 `situation` |
| `layout` | 否 | 显式槽位；缺省时脚本自动 `vertical` + `branch_columns` |

---

## Node

```json
{
  "id": "Activity_xxxxxxx",
  "type": "io:dcs",
  "name": "开泵",
  "attrs": {},
  "ext": {}
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 与 golden 规则一致（`Event_` / `Activity_` …） |
| `type` | 是 | schema 元件名，如 `flow:or`、`io:dcs`；亦接受短名 `or`/`dcs` |
| `name` | 视元件 | 无 name 的元件可省略 |
| `attrs` | 否 | 额外 XML 属性占位，如 `subproc` 的 `subId` |
| `ext` | 视元件 | 业务字段；与 schema default/const **深合并**（IR 覆盖默认） |

`start` / `end` / 无 `ext_data_schema` 的元件：不要 `ext`。

---

## Flow

```json
{ "id": "Flow_xxxxxxx", "source": "A", "target": "B", "situation": "yes", "name": "是" }
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | |
| `source` / `target` | 是 | 节点 id |
| `situation` | 条件边 | `yes` / `no` / 数字字符串（branch） |
| `name` | 否 | 一般可省略；yes/no 由脚本生成「是/否」 |

普通边不要 `situation`。

---

## LayoutOp（可选）

| `op` | 字段 | 对应 API |
|------|------|----------|
| `vertical` | `nodes`, 可选 `center_x`/`start_y`/`gap` | `layout_vertical` |
| `branch_columns` | `decision`, `yes`, `no`, 可选 `merge`/`center_x` | `layout_branch_columns` |
| `vertical_continue` | `after`, `nodes`, 可选 `center_x`/`gap` | 自 `after` 底边继续竖排 |

一期不在 IR 里展开 `parallel1`/`parallel2`（容器 + pstart/pend）；需要时再扩展。

---

## 编译命令 / fixture

唯一示例链：`fixtures/sample_ir.json` → `ir_to_xml` → `fixtures/sample_from_ir.xml`（可由命令重生成）。

```bash
python scripts/ir_to_xml.py fixtures/sample_ir.json -o fixtures/sample_from_ir.xml
python scripts/validate_bpmn.py fixtures/sample_from_ir.xml
```
