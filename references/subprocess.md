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

## 拆分决策

```
关联性分析 → 识别强/弱关联组
  → 独立子系统≥2 且步骤>10 → 可拆分（向用户推荐）
  → 仅 1 个子系统或步骤≤10 → 不拆分
  → 用户最终选择拆分/不拆分
```

向用户展示方案时：

- 可拆分：方案 A 不拆分 / 方案 B 拆分（标注推荐）
- 程序名、子程序名：仅字母数字下划线，字母开头，禁止中文

## 拆分原则

- 步骤守恒：子程序步骤之和 = 原 SOP 步骤总数
- 阶段不跨程序
- 每子程序约 3–8 步、10–20 节点
- 主程序可混合（自身步骤 + `flow:subproc`）
- 每个程序必须完整：`flow:start` → … → `flow:end`

## 子程序执行顺序

```
1. create_program          → 主 appid（用户确认后）
2. get_next_id × N         → 真实子程序 ID（禁止捏造）
3. Step 2.5 位号确认       → 先主后子
4. 生成主程序 XML          → flow:subproc.subId = 预生成 ID
5. 生成各子程序 XML
6. save_program 一次保存   → 见下方 payload 权威规则
7. 用户确认后 compile      → 用主 appid 统一编译
```

## save_program payload（权威，以此为准）

**主程序 → `updateProcedures`；子程序 → `addProcedures`。**  
禁止把子程序放进 `updateProcedures`。

| 字段 | 主程序 | 子程序 |
|------|--------|--------|
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

使用 `scripts/api_reference.py` 的 `save_program(..., subprograms=[...])`，不要手写 payload。

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

```xml
<flow:subproc id="Activity_xxx" name="SUB_NAME" subId="<real_id>">
  <ext:data><![CDATA[{"subTitle":"","showDetail":true,"showQueue":false,"subTitle2":"","data":[],"interval":0,"trends":[],"resourceGroupId":"0","conditions":[],"deviceId":""}]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</flow:subproc>
```

| | `flow:subproc` | `flow:otherMainProc` |
|--|----------------|----------------------|
| 用途 | 新建从属子程序，同次保存 | 引用已存在的独立主程序 |
| 本 skill | **使用这个** | 不使用 |
