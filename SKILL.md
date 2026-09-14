---
name: sop-to-direct
description: >-
  Converts chemical-industry SOP documents into InPlant Direct BPMN process
  programs via REST API (parse → confirm tags → generate XML → save → compile).
  Use when the user provides SOP (.docx/.pdf/.txt/.md) or asks to create/convert
  a Direct flow program, 主程序, or 流程程序 from an operating procedure.
---

# SOP 转 Direct 平台流程程序

将化工 SOP 转为 Direct BPMN XML，经 API 创建、保存、编译。**目标：语义忠于 SOP，XML 可编译。**  
细则只在下表权威文件中；本文件只负责任务编排与门禁。

## 触发

- 用户提供 SOP（`.docx` / `.pdf` / `.txt` / `.md`）并要求转 Direct 程序
- 用户说「建程序」「转成 Direct」「根据 SOP 生成主程序」等

## 准确率硬约束

1. **步骤门禁**：不得跳步；create/save/compile 前须用户明确同意
2. **原子拆分**：按 `element_split.md` 执行
3. **IR/XML**：只产编译 IR（形态=**`fixtures/sample_ir.json`**，契约=`ir_schema.md`）。写 IR 前必须 **Read** `sample_ir.json` + `element_schema.json`，字段名照搬。**禁止** `main_program`/`steps` 等废弃结构。编译：`ir_to_xml.py`（内含结构校验）→ `validate_bpmn.py` 均须退出码 0；禁止手写 XML
4. **白名单 / 校验**：仅 schema 元件；save 前 `validate_bpmn.py` 必须通过（含 XML 内子程序/计时器/变量名 `[A-Za-z0-9_]`；非法则改 IR 或 `validate_bpmn.py --fix` 后再校验）
5. **连线与布局**：仅由 `ir_to_xml` → `LayoutGenerator.assemble_full_xml`（规则见 golden）
6. **位号**：确认流程见 `interaction.md` Step 2.5；格式见 `node_reference.md`
7. **子程序**：用户确认拆分后必须 **主 XML + 全部子 XML**，且主 XML 用 `flow:subproc` 引用每一个子程序（见 `subprocess.md` 硬门禁）；`subId`=`get_next_id`；save 主 update / 子 add
8. **禁止** `deploy_program`；编译询问见 `interaction.md` Step 3.5（固定二选一）
9. **编译重试**：同 appid，≤3 次，只修数据/格式，不改拓扑
10. **保存前**：`accuracy_checklist.md` + `validate_bpmn.py` 通过（标识符命名见上）
11. **确认轮次**：仅 1.5 / 2 / 2.5 / 3.5 四轮（见 `interaction.md`）；禁止再拆多轮
12. **API 配置**：用 `api_reference.py` 的 `BASE_URL` / `AUTH_TOKEN`（环境变量可覆盖；**未设置则用脚本默认值，默认可用**）。禁止因「未配置 DIRECT_* 环境变量」而跳过 create/save；仅当实际 API 调用失败时再报错

## 工作流

```
1 解析 → 1.5 拆分方案（拆/不拆+子程序表）→ 2 创建主程序（若拆则随后 get_next_id）
  → 2.5 位号确认 → 3 生成 XML → 3.5 确认并保存（成功后编译二选一）→ [5 编译] → 6 报告
```

| 未完成 | 不得进入 |
|--------|----------|
| Step 1 | 1.5 |
| 1.5 用户确认拆分方案 | 2 |
| 2 用户同意创建 | 2.5（若拆分：create 后先 `get_next_id` 再 2.5） |
| 2.5 位号确认 | 3 |
| 3 validate 通过 | 3.5 |
| 3.5 同意保存 | save；保存成功后才能选编译 |
| 3.5 选「确认编译」 | 5 |

### Step 1 — 解析

**Read（缺一不可，且须在写 IR 之前）**：
1. `element_split.md` — 原子拆分与覆盖自检  
2. `fixtures/sample_ir.json` — **编译 IR 结构样板（照抄字段，勿自造）**  
3. `element_schema.json` — `type` / `ext`  
4. `ir_schema.md` — 契约  

产出 **仅** `process_id` + `nodes` + `flows`（±可选 layout/timers/variables）形态的合法 JSON；  
用 `python scripts/ir_to_xml.py <ir.json> -o <tmp.xml>` 试编译（结构不对会直接报错），通过后再展示对照表并进 1.5。  
**禁止**输出 `main_program` / `steps` / `coverage` 等废弃草稿当 IR。

### Step 1.5 — 拆分方案

**Read** `subprocess.md`（评估）+ `interaction.md` Step 1.5。  
一次确认：拆/不拆 +（若拆）子程序 name/描述表。

### Step 2 — 创建主程序

**Read** `interaction.md` Step 2；同意后 `create_program`。  
若 1.5 为拆分：创建成功后立即 `get_next_id` × N 并写入 IR（`subprocess.md`），不再另开确认。

### Step 2.5 — 位号

**Read** `interaction.md` Step 2.5；拆分时先主后子。单独一轮，不与其它合并。

### Step 3 — 生成 XML（确定性编译）

**Read** `ir_schema.md`（IR 已在 Step 1 / 2.5 写好位号；结构须与 `sample_ir.json` 一致）。  
禁止手搓 XML。

```bash
python scripts/ir_to_xml.py <ir.json> -o <out.xml>
python scripts/validate_bpmn.py <out.xml>
```

**不拆分**：上述对主 IR 跑一遍。  

**拆分**（必须主 + 全部子；主须含 `flow:subproc`）：

```bash
python scripts/ir_to_xml.py <main_ir.json> -o <main.xml>
python scripts/ir_to_xml.py <sub1_ir.json> -o <sub1.xml>
# …每个子程序各编译一次…
python scripts/validate_bpmn.py <main.xml> <sub1.xml> … <subN.xml>
```

必须退出码 0。细则：`element_schema.json` / `golden_xml_rules.md`（脚本侧）；位号示例按需 `node_reference.md`。  
命名：XML 内 `flow:subproc` 的 `name`、`ext.timer` / `$(…)` 程序变量须 `[A-Za-z0-9_]`（与 `subprocess.md` 一致）；`ir_to_xml` / `save_program` 会对非法名自动改写，但 Agent 应在 IR 中直接使用合法名。  
拆分硬门禁唯一来源：`subprocess.md`。

### Step 3.5 — 确认并保存 + 编译选择

**Read** `interaction.md` Step 3.5。  
展示节点/连线摘要 → 同意后 `save_program` → 成功后编译二选一。未确认不得 save；未选编译选项不得 compile。

### Step 5 — 编译（若用户选确认编译）

失败：位号再问用户；格式可自修；同 appid ≤3 次；禁止新建、禁止改拓扑。

### Step 6 — 报告

程序名、appid、节点/连线数、编译结果、补充项。

## 参考索引（主题 → 唯一来源）

| 主题 | 唯一来源 |
|------|----------|
| 任务编排 / 门禁 | `SKILL.md` |
| SOP→IR 原子拆分 | `element_split.md` |
| IR JSON 契约 | `ir_schema.md` + 样板 `fixtures/sample_ir.json` |
| 拆分评估 / save payload / `flow:subproc` | `subprocess.md` |
| 用户确认文案（1.5/2/2.5/3.5） | `interaction.md` |
| XML 结构 / 连线 / 布局通则 | `golden_xml_rules.md` |
| 元件与 ext:data schema | `element_schema.json` |
| 节点示例 / 位号路径 / type | `node_reference.md` |
| 保存前勾选 | `accuracy_checklist.md`（只勾选，不写细则） |
| IR→XML 编译 | `ir_to_xml.py`（fixture：`fixtures/sample_ir.json`） |
| 布局组装实现 | `layout_generator.py` |
| API | `api_reference.py` |
| 结构+几何校验 | `validate_bpmn.py` |

**原则**：细则只写在唯一来源；其他文件最多一行指针。禁止在第二处再写完整规则或第二份 XML 示例。
