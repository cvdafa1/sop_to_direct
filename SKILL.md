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
3. **XML**：Agent 只产 IR（`ir_schema.md`）；禁止手写节点/连线/Diagram XML。编译：`python scripts/ir_to_xml.py <ir.json> -o <out.xml>`
4. **白名单 / 校验**：仅 schema 元件；save 前 `validate_bpmn.py` 必须通过
5. **连线与布局**：仅由 `ir_to_xml` → `LayoutGenerator.assemble_full_xml`（规则见 golden）
6. **位号**：确认流程见 `interaction.md`；格式见 `node_reference.md`
7. **子程序**：见 `subprocess.md`（主 update / 子 add；`subId`=`get_next_id`）
8. **禁止** `deploy_program`；编译询问见 `interaction.md` Step 4.5（固定二选一）
9. **编译重试**：同 appid，≤3 次，只修数据/格式，不改拓扑
10. **保存前**：`accuracy_checklist.md` + `validate_bpmn.py` 通过

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

**Read** `element_split.md` 并执行其强制流程与覆盖自检；展示完整元件列表后再进 1.5。

### Step 1.5 — 是否拆分

**Read** `subprocess.md`（评估）+ `interaction.md`（只问拆/不拆）。不拆分则跳过 2.1。

### Step 2 — 创建主程序

**Read** `interaction.md` Step 2；同意后 `create_program`。

### Step 2.1 — 子程序信息（仅拆分）

**Read** `interaction.md` Step 2.1 + `subprocess.md`（name/subTitle/`subId` 写入规则）。创建成功后执行。

### Step 2.5 — 位号

**Read** `interaction.md` Step 2.5；拆分时先主后子。

### Step 3 — 生成 XML（确定性编译）

**Read** `ir_schema.md`（IR 已在 Step 1 / 2.5 写好位号）。  
禁止手搓 XML。执行：

```bash
python scripts/ir_to_xml.py <ir.json> -o <out.xml>
python scripts/validate_bpmn.py <out.xml>
```

必须退出码 0。细则：`element_schema.json` / `golden_xml_rules.md`（脚本侧）；位号示例按需 `node_reference.md`。

### Step 3.7 — 确认图

展示节点/连线摘要；未确认不得 save。

### Step 4 — 保存

清单通过后一次 `save_program`（子程序见 `subprocess.md`）。

### Step 4.5 / 5 — 编译

**Read** `interaction.md` Step 4.5。失败：位号再问用户；格式可自修；同 appid ≤3 次；禁止新建、禁止改拓扑。

### Step 6 — 报告

程序名、appid、节点/连线数、编译结果、补充项。

## 参考索引（主题 → 唯一来源）

| 主题 | 唯一来源 |
|------|----------|
| 任务编排 / 门禁 | `SKILL.md` |
| SOP→IR 原子拆分 | `element_split.md` |
| IR JSON 契约 | `ir_schema.md` |
| 拆分评估 / save payload / `flow:subproc` | `subprocess.md` |
| 用户确认文案（1.5/2/2.1/2.5/4.5） | `interaction.md` |
| XML 结构 / 连线 / 布局通则 | `golden_xml_rules.md` |
| 元件与 ext:data schema | `element_schema.json` |
| 节点示例 / 位号路径 / type | `node_reference.md` |
| 保存前勾选 | `accuracy_checklist.md`（只勾选，不写细则） |
| IR→XML 编译 | `ir_to_xml.py`（fixture：`fixtures/sample_ir.json`） |
| 布局组装实现 | `layout_generator.py` |
| API | `api_reference.py` |
| 结构+几何校验 | `validate_bpmn.py` |

**原则**：细则只写在唯一来源；其他文件最多一行指针。禁止在第二处再写完整规则或第二份 XML 示例。
