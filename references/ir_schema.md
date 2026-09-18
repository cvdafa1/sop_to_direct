# IR 契约（SOP → 确定性编译）

Agent **只产出本文件 + `fixtures/sample_ir.json` 描述的 IR JSON**；XML 由 `scripts/ir_to_xml.py` 生成（**时机**：须已 `create_program` 成功且 Step 2.5 位号确认后，见 `SKILL.md`；禁止提前试编）。
禁止在 IR 中写坐标、`incoming`/`outgoing`、sequenceFlow 几何或 Diagram。

## 强制参照（写 IR 前必须 Read，禁止凭记忆）

| 文件 | 作用 |
|------|------|
| `fixtures/sample_ir.json` | **唯一结构样板**——顶层与节点/边字段名必须与此一致 |
| `references/element_schema.json` | `type` 白名单与每个元件 `ext` 字段 |

**禁止**产出废弃结构：`main_program` / `steps` / `subprograms`（包 steps）/ `coverage` / `program_name`。  
结构门禁内置在 `ir_to_xml.py`（不合规则编译失败）。

元件白名单与 `ext` 字段：`element_schema.json`（唯一来源）。  
写 IR 时每个节点的 `ext` **必须符合该元件 `ext_data_schema`**（required、禁止多余键）。`ir_to_xml` 会按 schema 合并 default/const 后校验；失败则编译失败，禁止自造 `conditions`/`formula` 等非 schema 键。壳字段可省略（由脚本补默认）；业务字段（`data`/`branch`/`message`/`timer`/`url` 等）必须显式填写。表达式与位号用 `#()` / `$()`，禁止中文裸名、禁止 `${Name}`。

---

## 顶层

```json
{
  "process_id": "Process_1",
  "nodes": [ /* Node */ ],
  "flows": [ /* Flow */ ],
  "layout": [ /* LayoutOp，可选；省略则自动布局 */ ],
  "timers": [ /* 可选；见下方 */ ],
  "variables": [ /* 可选；见下方 */ ]
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `process_id` | 否 | 默认 `Process_1` |
| `nodes` | 是 | 顺序即 process 内节点顺序 |
| `flows` | 是 | 全部连线；条件边带 `situation` |
| `layout` | 否 | 显式槽位；缺省时：仅 yes 主链竖排，yes+no 用 `branch_columns` |
| `timers` | 条件 | 使用 start/stop/pause/restart/cond 时声明；亦可省略，由 save 从 XML 提取 |
| `variables` | 条件 | 使用 `io:var` 等程序变量时声明（含 dataType）；权威见 `subprocess.md` §variables |

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

**条件边：** IR 用 `situation`；条数与是否带 no 的规则见 `golden_xml_rules.md` §3。IR 不要写 `incoming`/`outgoing`。
---

## timers / variables（可选）

字段与命名权威：`subprocess.md` §timers / §variables。  
IR 可写 `timers: ["JSQ1"]` 或完整项；`variables` 同该文件结构。计时器只进 `timers`。`timer:wait` / `timer:clock` 不必列入 `timers`。

---

## LayoutOp（可选）

| `op` | 字段 | 对应 API |
|------|------|----------|
| `vertical` | `nodes`, 可选 `center_x`/`start_y`/`gap` | `layout_vertical` |
| `branch_columns` | `decision`, `yes`, `no`, 可选 `merge`/`center_x` | `layout_branch_columns` |
| `multi_columns` | `decision`, `branches`（多路节点列表）, 可选 `merge`/`center_x` | `layout_multi_columns` |
| `vertical_continue` | `after`, `nodes`, 可选 `center_x`/`gap` | 自 `after` 底边继续竖排 |

**自动布局（省略 `layout` 时）已支持：**

- 直线；仅 yes；一层 yes+no
- **嵌套是/否**与**菱形链**（先定汇合点再展臂，臂内递归）
- **`flow:branch` 多路**（situation `0/1/2…`）
- **支路内再套一层 yes/no**（如三路里每路一个 `flow:and`）
- 高扇入汇合用共享总线走线（同源/同宿共线允许，见 `golden_xml_rules.md`）

`parallel1` / `parallel2`：禁止写入 IR，见 `element_split.md` R5。

---

## 编译 / fixture

`fixtures/sample_ir.json`：直线 + 一层是/否。编译命令见 `SKILL.md` Step 3。
