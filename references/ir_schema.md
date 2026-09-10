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
  "layout": [ /* LayoutOp，可选；省略则自动布局 */ ],
  "timers": [ /* 可选；见下方 */ ]
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `process_id` | 否 | 默认 `Process_1` |
| `nodes` | 是 | 顺序即 process 内节点顺序 |
| `flows` | 是 | 全部连线；条件边带 `situation` |
| `layout` | 否 | 显式槽位；缺省时：仅 yes 主链竖排，yes+no 用 `branch_columns` |
| `timers` | 条件 | 使用 start/stop/pause/restart/cond 时声明；亦可省略，由 save 从 XML 提取 |

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
{ "id": "Flow_xxxxxxx", "source": "A", "target": "B", "situation": "yes" }
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | |
| `source` / `target` | 是 | 节点 id |
| `situation` | 条件边 | `yes` / `no` / 数字字符串（branch） |
| `name` | 否 | 一般可省略；yes/no 由脚本生成「是/否」 |

普通边不要 `situation`。

**条件边（`or` / `and` / `cond`）— 与 `golden_xml_rules.md` §3 一致：**

- **必须**有一条 `situation: "yes"`
- **`situation: "no"` 仅当 SOP 有否则/不满足语义时才加**
- 合法：仅 yes，或 yes+no；禁止只有 no、禁止无依据硬凑空否
- 入出边由编译器按 `flows` 注入，IR 不要写 `incoming`/`outgoing`

---

## timers（可选）

程序内使用 `timer:start` / `stop` / `pause` / `restart` / `cond` 时，save 的 `sfc.timers` 必须声明对应变量（权威字段见 `subprocess.md` §timers）。

IR 可写：

```json
"timers": ["JSQ1", "$(JSQ_001)"]
```

或完整项：`{"name":"JSQ1","dataType":3,"defaultValue":"00:00:00"}`。  
节点 `ext.timer` 用 `$(JSQ1)`；`timers[].name` 为裸名 `JSQ1`，**仅允许字母、数字、下划线**（`[A-Za-z0-9_]`）。`timer:wait` / `timer:clock` 不必列入。

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

唯一示例：`fixtures/sample_ir.json`（XML 由命令生成，不入库）。

```bash
python scripts/ir_to_xml.py fixtures/sample_ir.json -o out.xml
python scripts/validate_bpmn.py out.xml
```
