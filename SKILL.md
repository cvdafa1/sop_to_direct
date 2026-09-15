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
细则只在「参考索引」唯一来源中；本文件只负责任务编排与门禁指针。

## 触发

- 用户提供 SOP（`.docx` / `.pdf` / `.txt` / `.md`）并要求转 Direct 程序
- 用户说「建程序」「转成 Direct」「根据 SOP 生成主程序」等

## 准确率硬约束

| # | 门禁 | 细则唯一来源 |
|---|------|----------------|
| 1 | 不得跳步；create/save/compile 前须用户明确同意 | `interaction.md` |
| 2 | 原子拆分；**全文识别不可忽略**；大文件分块见 `element_split.md` §0.4 | `element_split.md` |
| 3 | 只产编译 IR；禁止手写 XML；`ir_to_xml` → `validate_bpmn` 退出码 0 | `ir_schema.md` + `fixtures/sample_ir.json` |
| 4 | 仅 schema 元件；标识符命名 | `element_schema.json` / `subprocess.md` |
| 5 | 连线与布局仅由编译器组装 | `golden_xml_rules.md` |
| 6 | 位号确认与格式 | `interaction.md` Step 2.5 + `node_reference.md` |
| 7 | 拆分：主+全部子 XML，主含 `flow:subproc` | `subprocess.md` |
| 8 | 禁止 `deploy_program`；编译二选一 | `interaction.md` Step 3.5 |
| 9 | 平台编译重试：同 appid ≤3；只修数据/格式，不改拓扑 | 本表 |
| 10 | **XML 生成失败禁止简化流程**（见下「失败处置」） | 本表 + `element_split.md` |
| 11 | 保存前勾选清单 | `accuracy_checklist.md` |
| 12 | 确认仅 1.5 / 2 / 2.5 / 3.5 四轮 | `interaction.md` |
| 13 | API：`api_reference.py` 默认值可用；禁止因未设 `DIRECT_*` 而跳过调用 | `api_reference.py` |

## 工作流

```
1 解析 → 1.5 拆分方案 → 2 创建主程序（若拆则随后 get_next_id）
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

写 IR 前 **Read**：`element_split.md` → `fixtures/sample_ir.json` → `element_schema.json` → `ir_schema.md`。  
全文识别、大文件分块：`element_split.md` §0.4。对照表只展示、不写入 IR。产出后进 1.5（本步不单独要「同意解析」）。

### Step 1.5 — 拆分方案

**Read** `subprocess.md` + `interaction.md` Step 1.5。

### Step 2 — 创建主程序

**Read** `interaction.md` Step 2。同意后 `create_program`。拆分时序见 `subprocess.md`。

### Step 2.5 — 位号

**Read** `interaction.md` Step 2.5。单独一轮，不与其它合并。

### Step 3 — 生成 XML

禁止手搓 XML。**Read** `ir_schema.md`（位号已在 2.5 写好）。

```bash
python scripts/ir_to_xml.py <ir.json> -o <out.xml>
python scripts/validate_bpmn.py <out.xml>
```

拆分：每个子 IR 各编译一次；`validate_bpmn.py <main.xml> <sub1.xml> …`（主文件第一位）。须退出码 0。

#### 失败处置（`ir_to_xml` / `validate_bpmn` / 布局重叠交叉）

**禁止**为通过校验而简化 SOP 语义或流程，包括但不限于：删节点、合并多步、去掉分支/否则、改串行以「少连线」、用一句话概括多操作、减少 `flow:subproc`。

**允许**：修 `ext`/位号/标识符；补 `IR.layout`；调间距/走线相关参数；按报错修结构字段；仍失败则向用户说明卡点并请求指示——**不得擅自砍流程**。

覆盖自检与禁止合并见 `element_split.md`。

### Step 3.5 — 确认并保存 + 编译选择

**Read** `interaction.md` Step 3.5。

### Step 5 — 编译（若用户选确认编译）

失败：位号再问用户；格式可自修；同 appid ≤3 次；禁止新建、禁止改拓扑、**禁止简化流程**（同 Step 3 失败处置）。

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
| IR→XML 编译 | `ir_to_xml.py` |
| 布局组装实现 | `layout_generator.py` |
| API | `api_reference.py` |
| 结构+几何校验 | `validate_bpmn.py` |

**原则**：细则只写在唯一来源；其他文件最多一行指针。禁止在第二处再写完整规则或第二份 XML 示例。
