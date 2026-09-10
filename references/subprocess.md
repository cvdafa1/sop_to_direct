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

## 拆分决策与交互时机

评估后倾向：独立子系统≥2 且步骤>10 → 推荐拆分；仅 1 个子系统或步骤≤10 → 推荐不拆分。  
**交互文案与确认表见 `interaction.md`（Step 1.5）**；本文件只规定评估、拆分原则、save 与 `flow:subproc`。

## 拆分原则

- 步骤守恒：子程序步骤之和 = 原 SOP 步骤总数
- 阶段不跨程序
- 每子程序约 3–8 步、10–20 节点
- 主程序可混合（自身步骤 + `flow:subproc`）
- 每个程序必须完整：`flow:start` → … → `flow:end`

## 时序专规（步骤编排见 `SKILL.md` 工作流）

本文件不复述 Step 编号。专规仅三条：

1. `get_next_id` 必须在 Step 1.5 用户确认拆分方案、且 Step 2 `create_program` 成功之后、生成 XML 之前  
2. 主程序 `flow:subproc` 字段映射见下方 §flow:subproc  
3. 一次 `save_program`；payload 见下方；编译用主 appid（询问文案见 `interaction.md` Step 3.5）

## save_program payload（权威，以此为准）

**主程序 → `updateProcedures`；子程序 → `addProcedures`。**  
禁止把子程序放进 `updateProcedures`。

| 字段 | 主程序 | 子程序 |
|------|--------|--------|
| `sfc.timers` | 见下方 §timers | 同左（按该程序 XML） |
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

使用 `scripts/api_reference.py` 的 `save_program(..., subprograms=[...], timers=...)`，不要手写 payload。  
`timers` 可省略：客户端会从该程序 XML 的 `ext.timer` 自动提取。

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

**Step 1.5 确认的 name / 描述必须写入主程序中的子程序元件（禁止留空、禁止另起一名）：**

| Step 1.5 字段 | 写入位置 | 规则 |
|---------------|----------|------|
| `name` | XML 属性 `name`，且与 save 子程序 `name` 一致 | `[A-Za-z][A-Za-z0-9_]*` |
| `描述/职责` | `ext:data.subTitle`（必填，禁止 `""`） | 与用户确认文案一致 |

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
