# 子程序拆分与保存（权威规则）

## 评估维度（辅助）

| 维度 | 阈值 |
|------|------|
| 步骤总数 | >10 |
| 独立子系统 | ≥2 |
| 节点预估数 | >25 |
| 阶段数 | >5 |
| 并行场景 | >3 |

**关联性分析是首要条件，数量维度仅作辅助。**

## 关联性四维度

| 关联维度 | 强关联示例 | 弱关联示例 |
|----------|------------|------------|
| 操作对象 | 同一泵系统的变频+停泵+关阀 | 泵系统 vs 风机系统 |
| 控制逻辑 | 切回路→调变频→判断温度→关阀 | 降负荷控制 vs 设备停车 |
| 触发条件 | 都依赖同一反馈信号 | 一个看温度、一个看液位 |
| 功能目标 | 都服务于「降负荷」 | 降负荷 vs 停风机 |

判断规则：

1. ≥2 个维度一致 → 强关联，同一子系统
2. ≥3 个维度不同 → 弱关联，可拆分
3. 仅有时序依赖但对象/逻辑/目标不同 → 仍应拆分

## 命名与描述（主/子）

| 对象 | 名称 | 描述 |
|------|------|------|
| **主程序** | 对话能提取 → 用提取名（规范为 `[A-Za-z0-9_]`）；提取不到 → 按文档标题/内容生成 | 对话能提取则用；否则按文档内容生成（Step 2 **不展示确认**） |
| **子程序** | 用户确认拆分后，**尽量依据该子划分文档的主题/设备/操作内容**生成可辨识 name（`[A-Za-z0-9_]`，可用英文或拼音转写）；禁止空洞占位名（如 `sub1`/`proc_a`，除非内容实在无法提炼且已用后缀保证唯一）；**不请用户填写**；各子 name 互不重复，且不得与主程序 `program_name` 相同；撞名时加 `_2` 等后缀 | **尽量依据该子文档内容**生成可读职责说明（写清对象/阶段/目的），写入 `subTitle`；禁止空串或与内容无关的套话；**不请用户填写** |

细则与确认文案见 `interaction.md` Step 1.5 / 2。

## 拆分决策与交互时机

评估后倾向：独立子系统≥2 且步骤>10 → 推荐拆分；仅 1 个子系统或步骤≤10 → 推荐不拆分。  
**Step 1.5**：仅确认拆/不拆并标唯一推荐（优先 `request_interaction_select.py`，否则对话编号；见 `interaction.md`）；子程序 name/描述在选定「拆分」后由 Agent 按子文档生成（不问用户）。本文件只规定评估、拆分原则、save 与 `flow:subproc`。

## 拆分原则

- 步骤守恒：子程序步骤之和 = 原 SOP 步骤总数
- 阶段不跨程序
- 每子程序约 3–8 步、10–20 节点
- 主程序可混合（自身步骤 + `flow:subproc`）
- 每个程序必须完整：`flow:start` → … → `flow:end`

### 拆分硬门禁（用户确认「拆分」后必须满足）

1. **产物齐全**：生成 **1 份主程序 IR + N 份子程序 IR**，再在 Step 3 各编 XML（N = 划分出的子文档数）；禁止只出主程序或只出子程序；**禁止 create 前编 XML**
2. **主程序必须引用**：主 XML 内须有 **恰好 N 个** `flow:subproc`，每个对应一个子程序；`name` / `subId` 与 `get_next_id` + save `subprograms[]` 一致  
3. **子程序完整 XML**：每个子程序独立 `ir_to_xml` → 完整 `flow:start`…`flow:end`；子 XML **禁止**再嵌套 `flow:subproc`  
4. **一次保存**：`save_program(..., xml_content=主XML, subprograms=[{id,name,xml_content}, ...])`；缺任一子 XML 或主未引用 → 拒绝保存  
5. **校验**：`python scripts/validate_bpmn.py main.xml sub1.xml ... subN.xml`（须把主文件放第一位）  
6. **子 name 唯一**：全部子程序 `name`（及主 XML 中各 `flow:subproc/@name`）两两不同；`save_program` / `check_split_bundle` 遇重复名则失败

禁止：把子步骤全部塞进主程序却无 `flow:subproc`；或有 `flow:subproc` 却未生成/未传入对应子 XML；或子程序重名。

## 时序专规（步骤编排见 `SKILL.md` 工作流）

本文件不复述 Step 编号。专规仅：

1. `get_next_id` 必须在 Step 1.5 用户确认拆分方案、且 Step 2 `create_program` 成功之后、生成 XML 之前  
2. **禁止**在 `create_program` 成功前对主/子调用 `ir_to_xml` 或落盘 BPMN XML（与 `SKILL.md` 绝对原则一致）  
3. 主程序 `flow:subproc` 字段映射见下方 §flow:subproc  
4. 一次 `save_program`；payload 见下方；编译用主 appid（询问文案见 `interaction.md` Step 3.5）

## save_program payload（权威，以此为准）

**主程序 → `updateProcedures`；子程序 → `addProcedures`。**  
禁止把子程序放进 `updateProcedures`。

| 字段 | 主程序 | 子程序 |
|------|--------|--------|
| `sfc.timers` | 见下方 §timers | 同左（按该程序 XML） |
| `sfc.variables` | 见下方 §variables | 同左（按该程序 XML） |
| `sfc.refServerVariables` | `{"list": []}` | `{}` |
| `description` | 有 | 无 |
| `id` | 主 appid | `get_next_id` 返回值（= XML `subId`） |
| `deviceId` | `"0"` | 无 |
| `parentId` | `"0"` | 主 appid |
| `rootId` | 主 appid | 主 appid |
| `name` | 有 | 有 |
| `resourceGroupId` | `"0"` | 无 |
| `customOrder` | 1 | 1,2,3… |
| `schedulePeriod` | 1000 | 无 |
| `signPathId` / `branchSignPathId` / `formulaGroupId` | `"0"` | 无 |

使用 `scripts/api_reference.py` 的 `save_program(..., subprograms=[...], timers=..., variables=...)`，不要手写 payload。  
`timers` / `variables` 可省略：客户端会从该程序 XML 自动提取（变量自动提取时 dataType 默认浮点，精确类型应显式传入）。

### sfc.timers（计时器变量）

使用下列元件时，**必须**在对应程序的 `sfc.timers.list` 声明变量（`timer:wait` / `timer:clock` 不需要）：

- `timer:start` / `timer:stop` / `timer:pause` / `timer:restart` / `timer:cond`

```json
"timers": {
  "list": [
    { "name": "JSQ1", "dataType": 3, "defaultValue": "00:00:00" }
  ]
}
```

| 字段 | 规则 |
|------|------|
| `name` | 裸名，仅 `[A-Za-z0-9_]`；与 XML `ext.timer` 一致但**不含** `$()`；`$(JSQ1)` → `JSQ1` |
| `dataType` | 固定 `3` |
| `defaultValue` | 固定 `"00:00:00"` |

同一程序内按 `name` 去重；主/子各自一份 `timers`（只声明本程序 XML 用到的）。  
保存前：`validate_bpmn.py` 校验 XML 内计时器名；非法则改 IR 或 `--fix`（`save_program` / `ir_to_xml` 也会自动 sanitize）。

### sfc.variables（程序变量）

元件使用程序变量（如 `io:var` 写变量、`io:calc` 的 `$(BL)` 等）时，**必须**在对应程序的 `sfc.variables.list` 声明。  
计时器名进 `timers`，**不要**重复进 `variables`。

```json
"variables": {
  "list": [
    { "name": "BL", "dataType": 1, "unit": "", "isEnum": false, "defaultValue": "0.000" },
    { "name": "3", "dataType": 2, "unit": "", "isEnum": false, "defaultValue": "" },
    { "name": "2", "dataType": 3, "unit": "", "isEnum": false, "defaultValue": "0" }
  ]
}
```

| 字段 | 规则 |
|------|------|
| `name` | 与 §timers 相同：裸名，仅 `[A-Za-z0-9_]`；`$(BL)` → `BL` |
| `dataType` | `1`=浮点，`2`=字符串，`3`=整型 |
| `unit` | 默认 `""` |
| `isEnum` | 默认 `false` |
| `defaultValue` | 浮点默认 `"0.000"`；字符串默认 `""`；整型默认 `"0"` |

### 单程序示例结构

```json
{
  "addProcedures": [],
  "updateProcedures": [{ "id": "<appid>", "parentId": "0", "rootId": "<appid>", "...": "..." }],
  "deleteProcedureIds": "",
  "rootId": "<appid>"
}
```

### 含子程序示例结构

```json
{
  "addProcedures": [
    { "id": "<sub_id>", "parentId": "<appid>", "rootId": "<appid>", "name": "SUB1", "customOrder": 1 }
  ],
  "updateProcedures": [
    { "id": "<appid>", "parentId": "0", "rootId": "<appid>", "name": "main", "...": "含 flow:subproc" }
  ],
  "deleteProcedureIds": "",
  "rootId": "<appid>"
}
```

## flow:subproc

使用 `flow:subproc`（不是 `flow:otherMainProc`）。`subId` 必须等于 `get_next_id` 返回值。

**用户确认「拆分」后，Agent 按各子划分文档生成的 name / 描述必须写入主程序中的子程序元件（禁止留空、禁止另起一名、禁止再问用户填）。**

| 字段 | 写入位置 | 规则 |
|------|----------|------|
| `name` | XML 属性 `name`，且与 save 子程序 `name` 一致 | 仅 `[A-Za-z0-9_]`；**尽量按该子文档内容提炼**；全部分子间唯一（亦不得与主程序名相同） |
| `描述/职责` | `ext:data.subTitle`（必填，禁止 `""`） | **尽量按该子文档内容提炼**可读职责（对象/阶段/目的） |

```xml
<flow:subproc id="Activity_xxx" name="load_down" subId="<real_id>">
  <ext:data><![CDATA[{"subTitle":"降负荷相关操作","showDetail":true,"showQueue":false,"subTitle2":"","data":[],"interval":0,"trends":[],"resourceGroupId":"0","needPublish":true,"showInReport":true,"conditions":[],"deviceId":""}]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</flow:subproc>
```

| | `flow:subproc` | `flow:otherMainProc` |
|--|----------------|----------------------|
| 用途 | 新建从属子程序，同次保存 | 引用已存在的独立主程序 |
| 本 skill | **使用这个** | 不使用 |
