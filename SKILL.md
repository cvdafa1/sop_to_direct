---
name: sop-to-direct
description: >-
  Converts chemical-industry SOP documents into InPlant Direct BPMN process
  programs via REST API (parse → split confirm → create → confirm tags →
  generate XML → save → compile). Use when the user provides SOP
  (.docx/.pdf/.txt/.md) or asks to create/convert a Direct flow program,
  主程序, or 流程程序 from an operating procedure.
---

# SOP 转 Direct 平台流程程序

将化工 SOP 转为 Direct BPMN XML，经 API 创建、保存、编译。**目标：语义忠于 SOP，XML 可编译。**  
细则只在「参考索引」唯一来源中；本文件只负责任务编排与门禁指针。

## 绝对执行原则（加载本技能后立即生效）

**加载本技能后，必须严格按照本文件「工作流」与门禁执行，不得自创流程。**

| 禁止 | 要求 |
|------|------|
| 跳步、并步、换序 | 严格按 `1 → 1.5 → 2 → 2.5 → 3 → 3.5 → [5] → 6` |
| **`create_program` 成功前生成 XML** | Step 1–2.5 只允许 IR；**禁止**调用 `ir_to_xml` / 手写或落盘 BPMN XML |
| 凭经验/习惯代替文档 | 进入某步前须**阅读**该步指定参考；细则以「参考索引」唯一来源为准 |
| 因失败擅自简化 SOP/砍节点 | 见 Step 3「失败处置」与门禁 #10 |
| 因未设 `DIRECT_*` / 工具不便而跳过 API 或确认 | 用 `api_reference.py` 默认值；确认轮次不得省略 |
| 手写 BPMN XML 或绕过 `ir_to_xml` / `validate_bpmn` | **仅 Step 3**（create 成功且 2.5 完成后）才脚本编译；退出码 0 才进 3.5 |
| **自构平台 HTTP/payload**（curl、裸 `requests`、手写 addProcedures 等） | **只**经 `DirectPlatformClient`（create/save/compile/get_*） |

不确定时：**停下来按本文件与唯一来源执行**，不得用「更快/更简单」的替代路径。

## 触发

- 用户提供 SOP（`.docx` / `.pdf` / `.txt` / `.md`）并要求转 Direct 程序
- 用户说「建程序」「转成 Direct」「根据 SOP 生成主程序」等

## 准确率硬约束

| # | 门禁 | 细则唯一来源 |
|---|------|----------------|
| 0 | **加载技能后必须严格按本文件流程执行**；禁止跳步/换序/自创路径 | 本文件「绝对执行原则」 |
| 1 | 不得跳步；**仅 compile** 前须用户明确同意；**create / save 不询问**（字段自动填；3 校验通过后自动保存） | `interaction.md` |
| 2 | 原子拆分；**全文识别不可忽略**；大文件分块见 `element_split.md` §0.4 | `element_split.md` |
| 3 | 只产编译 IR；禁止手写 XML；**须 `create_program` 成功且 2.5 位号确认后**才允许 `ir_to_xml`；再 `validate_bpmn`=0；save 前再验 | `ir_schema.md` + `fixtures/sample_ir.json` |
| 4 | 仅 schema 元件；标识符命名 | `element_schema.json` / `subprocess.md` |
| 5 | 连线与布局仅由编译器组装 | `golden_xml_rules.md` |
| 6 | 位号确认与格式 | `interaction.md` Step 2.5 + `node_reference.md` |
| 7 | 拆分：主+全部子 XML，主含 `flow:subproc` | `subprocess.md` |
| 8 | 禁止 `deploy_program`；保存自动；**仅编译**二选一交互 | `interaction.md` Step 3.5 |
| 9 | 平台编译重试：同 appid ≤3；只修数据/格式，不改拓扑 | 本表 |
| 10 | **XML 生成失败禁止简化流程**（见下「失败处置」） | 本表 + `element_split.md` |
| 11 | 保存前勾选清单 | `accuracy_checklist.md` |
| 12 | 确认仅 1.5 / 2.5 / 3.5 **三轮**；**1.5 仅拆/不拆+唯一推荐**（子 name/描述自动生成）；**Step 2 无交互**；未确认 1.5 不得 create | `interaction.md` |
| 13 | API：**只**用 `DirectPlatformClient`；禁止自构 URL/payload/curl；未设 `DIRECT_*` 仍用脚本默认值 | `api_reference.py` |

## 工作流

```
1 解析 → 1.5 拆分方案 → 2 创建主程序（若拆则随后 get_next_id）
  → 2.5 位号确认 → 3 生成 XML → 3.5 自动保存 + 编译二选一 → [5 编译] → 6 报告
```

| 未完成 | 不得进入 |
|--------|----------|
| Step 1 | 1.5 |
| 1.5 用户确认拆分方案 | 2（自动 create，不询问） |
| 2 `create_program` 成功 | 2.5（若拆分：create 后先 `get_next_id` 再 2.5） |
| 2.5 位号确认 | 3（**此前禁止** `ir_to_xml` / 生成 XML） |
| 3 validate 通过 + checklist | 3.5（直接 save，不询问） |
| 3.5 **save 成功**（`code` 为 0/`"0"`） | 才能问编译二选一；失败展示 code/msg 并停止 |
| 3.5 选「确认编译」 | 5 |

### Step 1 — 解析

写 IR 前须阅读：`element_split.md` → `fixtures/sample_ir.json` → `element_schema.json` → `ir_schema.md`。  
全文识别、大文件分块：`element_split.md` §0.4。对照表只展示、不写入 IR。产出后进 1.5（本步不单独要「同意解析」）。  
**禁止**本步调用 `ir_to_xml` 或生成/落盘任何 BPMN XML。

### Step 1.5 — 拆分方案

阅读 `subprocess.md` + `interaction.md` Step 1.5。  
**仅**对话编号确认拆/不拆并标唯一推荐；**不问**子程序 name/描述。用户选拆后，name/描述**尽量根据各子划分文档内容**提炼生成（禁止空洞占位名）。禁止宿主单选控件；禁止夹带创建字段；未确认前不得进入 Step 2。

### Step 2 — 创建主程序（无交互）

阅读 `interaction.md` Step 2。1.5 确认后**直接**按规则填字段并 `create_program`，**不询问用户**。  
字段：对话能提取则用对话；否则 `group_id`/`version` 用默认，`program_name`/`description` 结合文档生成。拆分时序见 `subprocess.md`。  
**禁止**在 `create_program` 成功前调用 `ir_to_xml` 或生成 XML。

### Step 2.5 — 位号

阅读 `interaction.md` Step 2.5 + `tag_confirm_template.md`。  
**系统**：预写 JSON → 跑脚本出 HTML → 内嵌 → 用户提交后按行合并重写 JSON → 写回 IR。  
**用户**：仅改位号 / type / 设定值并提交；三者须完整非空；**禁止**增删行。

### Step 3 — 生成 XML

**前置硬门禁**：`create_program` 已成功（已有主 appid）；Step 2.5 位号已确认。**此前禁止**跑 `ir_to_xml`、手写 XML、或预生成 XML「备用」。

禁止手搓 XML。阅读 `ir_schema.md`（位号已在 2.5 写好）。  
`ir_to_xml` 按 `element_schema.json` 全量校验每个元件 `ext`；失败则按报错改 IR 字段，禁止简化流程。

```bash
python scripts/ir_to_xml.py <ir.json> -o <out.xml>
python scripts/validate_bpmn.py <out.xml>
```

拆分：每个子 IR 各编译一次；`validate_bpmn.py <main.xml> <sub1.xml> …`（主文件第一位）。须退出码 0。

#### 失败处置（`ir_to_xml` / `validate_bpmn` / 布局重叠交叉）

**禁止**为通过校验而简化 SOP 语义或流程，包括但不限于：删节点、合并多步、去掉分支/否则、改串行以「少连线」、用一句话概括多操作、减少 `flow:subproc`。

**允许**：修 `ext`/位号/标识符；补 `IR.layout`；调间距/走线相关参数；按报错修结构字段；仍失败则向用户说明卡点并请求指示——**不得擅自砍流程**。

覆盖自检与禁止合并见 `element_split.md`。

### Step 3.5 — 自动保存 + 编译选择

阅读 `interaction.md` Step 3.5。须 **Step 3 本地校验已通过**；`save_program` 会再次跑 `validate_bpmn`（结构/几何/`ext` schema），失败则 **不请求平台**。校验通过后直接 save（不询问）；须以返回 **`code`/`msg`** 判定成功，**仅成功后**再问是否编译。

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
| 用户确认文案（1.5 / 2.5 / 3.5；Step 2 无交互） | `interaction.md` |
| 位号确认 JSON/内嵌 HTML | `fixtures/tag_confirm_template.json` + `tag_confirm_editor.html` + `make_tag_confirm_editor.py` |
| XML 结构 / 连线 / 布局通则 | `golden_xml_rules.md` |
| 元件与 ext:data schema | `element_schema.json` |
| 节点示例 / 位号路径 / type | `node_reference.md` |
| 保存前勾选 | `accuracy_checklist.md`（只勾选，不写细则） |
| IR→XML 编译 | `ir_to_xml.py` |
| 布局组装实现 | `layout_generator.py` |
| API | `api_reference.py` |
| 结构+几何校验 | `validate_bpmn.py` |

**原则**：细则只写在唯一来源；其他文件最多一行指针。禁止在第二处再写完整规则或第二份 XML 示例。
