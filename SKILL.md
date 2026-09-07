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

## 准确率硬约束（全程遵守）

1. **步骤门禁**：不得跳步；改平台状态的 API 必须先获用户明确同意
2. **原子拆分**：一个元件 = 一个原子操作或独立判断（详见 `references/element_split.md`）
3. **XML 唯源**：生成/修正 XML 前必须 Read `element_schema.json`、`node_reference.md`、`xml_template.xml`；禁止凭记忆
4. **连线必须用 `assemble_full_xml`**：禁止手写 sequenceFlow/Edge；漏 Edge 或 id 不一致会导致平台「有节点无连线」
5. **位号格式**：DCS 用 `#(…)`，变量用 `$(…)`；全部位号经用户确认
6. **子程序保存**：主程序 ∈ `updateProcedures`，子程序 ∈ `addProcedures`；`subId` 必须来自 `get_next_id`（详见 `references/subprocess.md`）
7. **禁止自动编译**：保存后必须询问；禁止调用 `deploy_program`
8. **编译重试**：同一 appid，最多 3 次；只修数据/格式，不改拓扑；位号问题必须再问用户
9. **保存前清单**：逐项完成 `references/accuracy_checklist.md`，必须跑 `scripts/validate_bpmn.py`（失败不得 save）

## 工作流（严格顺序）

```
1 解析 → 1.5 拆分评估 → 2 创建程序 → 2.5 位号/缺失确认
  → 3 生成 XML → 3.7 用户确认流程图 → 4 保存 → 4.5 询问编译 → 5 编译 → 6 报告
```

| 未完成 | 不得进入 |
|--------|----------|
| Step 1 | 1.5 |
| 1.5 用户确认方案 | 2 |
| 2 用户同意创建 | 2.5 |
| 2.5 位号确认 | 3 |
| 3 + 3.7 用户确认图 | 4 |
| 4 保存成功 | 4.5 |
| 4.5 用户同意编译 | 5 |

### Step 1 — 解析文档

**Read**：`references/element_split.md`

读取方式：

- `.txt` / `.md` / 粘贴文本：直接读
- `.docx` / `.pdf`：用可用的文档提取方式（系统 docx/pdf 能力或等价工具）；提取段落与表格全文

提取五维：阶段划分、操作步骤、设备/管路、参数值、安全/联锁。  
按拆分规则得到原子元件，产出 IR JSON（schema 见 `element_split.md`）。  
向用户展示 IR 摘要（阶段、步骤数、拟用节点类型），有明显歧义先澄清。

### Step 1.5 — 复杂度与子程序

**Read**：`references/subprocess.md`

关联性分析优先；可拆分时给出 A 不拆分 / B 拆分（推荐）供用户选。  
确认命名（字母开头，`[A-Za-z0-9_]`）。

### Step 2 — 创建主程序

**Read**：`references/interaction.md`  
**Code**：`scripts/api_reference.py` → `DirectPlatformClient`

`get_data_groups` → 用户选分组 → 确认 name/version/description → **同意后** `create_program`。  
若拆分：再 `get_next_id` × N，保存真实 sub ids。

### Step 2.5 — 缺失信息

**Read**：`references/interaction.md`

强制位号确认表（步骤/用途/建议值/type）；可用 `get_tags` / `search_tags_by_name` 辅助。  
补参数、阈值、模糊描述。全部确认后再生成 XML。

### Step 3 — 生成 BPMN XML

**Read**：`references/xml_rules.md` + 三份 schema/模板文件

- 单程序：1 份 XML
- 拆分：1 份主（含 `flow:subproc`）+ N 份子；`subId` = 预生成 ID
- **布局与连线（强制）**：`LayoutGenerator` → `layout_*` → `assemble_full_xml(node_xml_by_id)`；禁止手拼 diagram
- `check_overlaps` / `check_connection_integrity`（并行加 `check_parallel_integrity`）必须通过
- 写盘后 **必须** 通过：`python scripts/validate_bpmn.py <xml文件...>`（含连线/Edge/ext:data 检查）

### Step 3.7 — 流程图确认

向用户展示：节点列表与连线关系摘要、节点/连线数量、主路径。  
允许增删改节点后重生 XML 并再确认。**未确认不得 save。**

### Step 4 — 保存

清单 `references/accuracy_checklist.md` 通过后，一次 `save_program` 提交全部 XML。  
子程序用 `subprograms=` 参数；payload 规则以 `subprocess.md` 为准。

### Step 4.5 / 5 — 编译门禁

展示保存结果与文件统计，询问是否编译。同意后 `compile_program(主 appid)`。

失败处理：

1. 分析错误 → 位号类则问用户；格式类自修
2. 重新 Read XML 参考 → 修正 → save → compile
3. 最多 3 次；仍失败则报告原因、建议、appid，停止

**禁止**为重试新建程序；**禁止**删节点或改连接关系。

### Step 6 — 报告

程序名、appid、节点/连线数、编译结果、用户补充的位号/参数列表。

## 参考索引（按需 Read）

| 文件 | 何时读 |
|------|--------|
| `references/element_split.md` | Step 1 |
| `references/subprocess.md` | Step 1.5 / 保存子程序 |
| `references/interaction.md` | Step 2 / 2.5 |
| `references/xml_rules.md` | Step 3 |
| `references/element_schema.json` | Step 3 / 修 XML |
| `references/node_reference.md` | Step 3 / 修 XML |
| `references/xml_template.xml` | Step 3 / 修 XML |
| `references/accuracy_checklist.md` | Step 4 前 |
| `scripts/layout_generator.py` | 布局与连线 |
| `scripts/api_reference.py` | 全部 API |
| `scripts/validate_bpmn.py` | 保存前结构校验 |

## 决策树（简）

```
SOP
 → 解析+原子拆分 → IR
 → 关联性评估 → 用户确认单程序/主子程序
 → 确认分组与程序名 → create_program [(+ get_next_id)]
 → 位号与参数确认
 → Read schema → 生成 XML + layout 校验 + validate_bpmn
 → 用户确认流程图
 → save_program（主 update / 子 add）
 → 询问 → compile（失败则同 appid 数据修复≤3次）
 → 报告
```
