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

## 触发

- 用户提供 SOP（`.docx` / `.pdf` / `.txt` / `.md`）并要求转 Direct 程序
- 用户说「建程序」「转成 Direct」「根据 SOP 生成主程序」等

## 准确率硬约束

1. **步骤门禁**：不得跳步；create/save/compile 前须用户明确同意
2. **原子拆分**：见 `references/element_split.md`
3. **XML 唯源**：结构以 `golden_xml_rules.md` 为准；生成前 Read 它 + `xml_template.xml` + `element_schema.json`；节点示例按需 Read `node_reference.md`
4. **元件白名单**：生成 XML 只用 `element_schema.json` 已定义元件；`validate_bpmn.py` **必须**校验，未定义元件禁止 save
5. **连线**：只用 `LayoutGenerator.assemble_full_xml`（先 Edge 后 Shape；plain 自闭合；条件边 `是`/`否`）
6. **位号**：DCS `#()`、变量 `$()`；须用户确认
7. **子程序**：主 ∈ `updateProcedures`，子 ∈ `addProcedures`；`subId` 来自 `get_next_id`（见 `subprocess.md`）
8. **禁止** `deploy_program`；是否编译**始终用二选一**（确认编译 / 暂不编译），禁止开放式询问
9. **编译重试**：同 appid，≤3 次，只修数据/格式，不改拓扑
10. **保存前**：`accuracy_checklist.md` + `validate_bpmn.py` 通过（含未定义元件检查）

## 工作流

```
1 解析 → 1.5 是否拆分 → 2 创建主程序 → [拆分则 2.1 确认子程序信息] → 2.5 位号确认
  → 3 生成 XML → 3.7 确认流程图 → 4 保存 → 4.5 询问编译 → 5 编译 → 6 报告
```

| 未完成 | 不得进入 |
|--------|----------|
| Step 1 | 1.5 |
| 1.5 用户选择拆/不拆 | 2 |
| 2 用户同意创建 | 2.1 或 2.5 |
| 2.1（仅拆分）子程序信息确认 | 2.5 |
| 2.5 位号确认 | 3 |
| 3 + 3.7 确认图 | 4 |
| 4 保存成功 | 4.5 |
| 4.5 同意编译 | 5 |

### Step 1 — 解析

**Read** `element_split.md`。提取阶段/步骤/设备/参数/联锁 → IR。展示摘要，歧义先澄清。

### Step 1.5 — 是否拆分

**Read** `subprocess.md`。AI 做关联性评估后，**只询问用户：拆分 / 不拆分**（可标注推荐，但勿展开子程序明细）。

- 选**不拆分** → 进入 Step 2，之后跳过 2.1  
- 选**拆分** → 进入 Step 2，创建成功后再做 2.1  

### Step 2 — 创建主程序

**Read** `interaction.md`；用 `DirectPlatformClient`。  
`get_data_groups` → 选分组 → 确认主程序 name/version/description → **同意后** `create_program`。

### Step 2.1 — 子程序信息（仅当 1.5 选择拆分）

创建主程序成功后执行。AI 生成子程序列表（name、描述/职责、对应 SOP 步骤范围），**展示给用户并可修改**。命名：`[A-Za-z][A-Za-z0-9_]*`。  
用户确认后：`get_next_id` × N，再进入 2.5。

不拆分时**不进入本步**，创建后直接 2.5。

### Step 2.5 — 位号

**Read** `interaction.md`。强制确认表；可用 `get_tags` / `search_tags_by_name`。补参数与阈值。  
拆分时：先主后子。

### Step 3 — 生成 XML

**Read** `golden_xml_rules.md` + `xml_template.xml` + `element_schema.json`（按需 `node_reference.md`）。

- `LayoutGenerator` → `layout_*` → `assemble_full_xml`
- `python scripts/validate_bpmn.py <xml...>` **必须通过**（含：仅允许 `element_schema.json` 已定义元件；未定义元件 → 失败、禁止 save）

### Step 3.7 — 确认图

展示节点/连线摘要；未确认不得 save。

### Step 4 — 保存

清单通过后一次 `save_program`（子程序用 `subprograms=`）。

### Step 4.5 / 5 — 编译

保存成功后，**必须用选项方式**询问（禁止开放式「要不要编译？」）：

- **选项 1：确认编译** — 执行 `compile_program(主 appid)`
- **选项 2：暂不编译** — 跳过编译，进入 Step 6 报告（用户可稍后在平台手动编译）

用户未明确选择上述选项之一前，不得调用 `compile_program`。

编译失败：位号类错误必须再问用户；格式类可自修 → 同 appid save→compile，≤3 次。禁止新建程序、禁止改拓扑。

### Step 6 — 报告

程序名、appid、节点/连线数、编译结果、补充项。

## 参考索引

| 文件 | 职责（唯一） |
|------|----------------|
| `element_split.md` | SOP 拆分 / IR |
| `subprocess.md` | 是否拆分评估与 save payload |
| `interaction.md` | 拆分选择 / 创建 / 子程序信息 / 位号 |
| `golden_xml_rules.md` | XML 结构与连线 |
| `xml_template.xml` | 最小骨架 |
| `element_schema.json` | 节点 ext:data schema |
| `node_reference.md` | 节点示例（不含连线通则） |
| `accuracy_checklist.md` | 保存前勾选 |
| `layout_generator.py` | 布局与组装 |
| `api_reference.py` | API |
| `validate_bpmn.py` | 结构校验 |
