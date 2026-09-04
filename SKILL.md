***

name: "sop-to-direct"
description: "Converts chemical industry SOP documents into Direct platform BPMN XML process programs via API. Invoke when user provides SOP procedures (.docx/.pdf/.txt/.md) and wants to generate Direct platform flow programs."
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# SOP 转 Direct 平台流程程序

将化工行业 SOP 规程文档转换为 Direct 平台的 BPMN XML 流程程序，并通过 REST API 创建、保存、编译。

## 触发条件

- 用户提供 SOP 规程文档（.docx / .pdf / .txt / .md），需要转换为 Direct 平台流程程序

- 用户明确要求"将 SOP 转为 Direct 程序"或类似表述

- 用户上传化工操作规程并提到 Direct 平台

***

## 完整工作流程

**必须严格按以下顺序执行，不得跳过或调换步骤：**

```
Step 1: 解析文档 → Step 1.5: 复杂度评估与子程序拆分 → Step 2: 创建程序 → Step 2.5: 缺失信息交互 → Step 3: 生成XML → Step 4: 保存程序 → Step 5: 编译程序
```

- Step 1 未完成不得执行 Step 1.5

- Step 1.5 未完成不得执行 Step 2

- Step 2 未完成（用户未确认）不得执行 Step 2.5

- Step 2.5 未完成不得执行 Step 3

- Step 3 未完成不得执行 Step 4

- Step 4 未完成不得执行 Step 5

### Step 1: 解析文档

**目标**：从 SOP 文档中提取所有结构化信息，**解析时即区分主程序与子程序内容**。

SOP 文档没有标准格式，需要灵活解析。采用 **AI 语义理解 + 技能辅助读取** 策略。解析过程中根据步骤间关联性识别主程序与子程序边界，将弱关联的步骤组标记为独立子程序，主程序仅串联各子程序引用。

#### 1.1 读取文档内容

根据输入类型选择读取方式：

- `.docx`：使用 `docx` 技能提取段落和表格（不使用第三方库）

- `.pdf`：使用 `pdf` 技能提取文本和表格（不使用第三方库）

- `.txt` / `.md`：直接读取文本

- 用户提供文字内容：直接作为 SOP 文本处理

#### 1.2 提取的信息维度

从 SOP 文档中提取以下 **五大信息维度**，同时**识别主程序与子程序边界**，并**按元件拆分规则将每个步骤拆分为独立元件**：

| 维度        | 说明              | 示例                                       |
| --------- | --------------- | ---------------------------------------- |
| **阶段划分**  | SOP 的工序/阶段/步骤编号 | "一、准备工作" → "二、开车操作" → "三、停车操作"           |
| **操作步骤**  | 每步的具体操作动作和参数    | "打开反应釜R-01进料阀，设定流量50kg/h"                |
| **设备/管路** | 涉及的设备名称和位号      | "反应釜R-01"、"循环水泵P0801A"、"出口开关阀EV\_0801A2" |
| **参数值**   | 温度/压力/流量/时间等设定值 | "温度设定80℃"、"搅拌转速60rpm"、"反应时间30min"        |
| **安全/联锁** | 安全阈值、报警条件、联锁逻辑  | "压力超过0.5MPa时触发联锁停车"                      |

#### 1.2.1 元件拆分规则

**核心原则：一个元件 = 一个原子操作或一个独立判断。** 解析 SOP 时必须将复合步骤拆分为独立元件，不允许多个独立操作合并到一个元件中。

##### 拆分规则表

| # | SOP 文本模式 | 拆分结果 | 说明 |
|---|-------------|---------|------|
| R1 | "关/开/停/启动设备A，反馈信号B" | `io:dcs(A操作)` → `flow:or(B==到位)` | 操作和反馈拆为两个元件 |
| R2 | "变频调为X，反馈信号Y收到后执行Z" | `io:dcs(调X)` → `flow:or(Y到位)` → `io:dcs(Z)` | 操作→判断反馈→下一步操作 |
| R3 | "同一设备同时设置多参数" | 1个 `io:dcs`（data 含多项） | 如同一泵的 MANON + PIDA_OUT |
| R4 | "依次关闭A、B、C阀门" | `io:dcs(A)` → `io:dcs(B)` → `io:dcs(C)` | 不同设备串联，不合并 |
| R5 | "同时操作A/B/C，没有先后顺序" | `flow:parallel1`(3个 `io:dcs`) | 并行容器包裹 |
| R6 | "XX秒/分钟后执行A" | `timer:wait(XX)` → 下一步 | 纯时间等待 |
| R7 | "XX秒未收到反馈B则弹窗C" | `io:dcs(操作)` → `timer:cond(XX)` → `msg:guide(C)` | 超时判断+报警 |
| R8 | "弹窗提示XXX" | `msg:guide(XXX)` | 仅提示不暂停 |
| R9 | "弹窗确认是否XXX，点击确认后执行A" | `msg:confirm(XXX)` → 下一步 | 暂停等待人工确认 |
| R10 | "若A是B则...否则..." | `flow:or(A==B)` → yes/no 分支 | 单条件二选一 |
| R11 | "若A且B都满足则...否则..." | `flow:and(A,B)` → yes/no 分支 | 多条件二选一 |
| R12 | "3台泵中判断哪2台运行" | `flow:branch`(N个分支) | 多选一互斥分支 |
| R13 | "全部完成后弹窗提示" | 末端加 `msg:guide` | 汇总提示 |

##### 反馈信号处理规则

SOP 中"收到反馈信号""反馈信号到位"等描述，按以下规则处理：

| SOP 描述 | 处理方式 | 元件 |
|----------|---------|------|
| "操作A，收到反馈信号B" | 操作后加反馈判断 | `io:dcs` → `flow:or` |
| "操作A，收到反馈信号B后执行C" | 反馈作为后续操作前置条件 | `io:dcs` → `flow:or` → `io:dcs` |
| "操作A，XX秒未收到反馈B则报警C" | 超时判断+报警 | `io:dcs` → `timer:cond` → `msg:guide` |
| "操作A，反馈信号B取反" | 取反 = 判断信号==0 | `flow:or(B==0)` |
| "操作A，收到反馈信号B"（同一设备同类操作） | 可合并到 io:dcs 的 checkData | `io:dcs`（checkData 含B） |

##### 复合步骤拆分示例

**SOP**："关循环水泵P0801A出口开关阀（EV-0801A），阀位反馈信号（ZSC-EV0801A），停运行的循环水泵P0801A，收到反馈信号（YL-P0801A取反）"

**拆分结果**：
```
io:dcs(关EV-0801A) → flow:or(ZSC-EV0801A==到位) → io:dcs(停P0801A) → flow:or(YL_P0801A==0)
```
4 个元件，不可合并。原因：关阀和停泵是不同设备的独立操作，反馈信号需独立判断。

**SOP**："收到停电机反馈信号15分钟后，弹窗确认是否关闭酸泵，点击确认后依次停泵A、B、C"

**拆分结果**：
```
flow:or(停电机反馈) → timer:wait(15分钟) → msg:confirm(是否关闭酸泵) → io:dcs(停A) → io:dcs(停B) → io:dcs(停C)
```
6 个元件。原因：反馈判断→延时→人工确认→串联操作，每步逻辑独立。

**SOP**："判断风机运行信号（YL-C0801），若风机是关闭状态则弹窗提示结束；若风机是启动状态则变频调0→等反馈→停风机→等反馈→弹窗提示结束"

**拆分结果**：
```
flow:or(YL-C0801==0)
  ├─ yes → msg:guide("循环水系统停车结束") → flow:end
  └─ no  → io:dcs(变频调0) → flow:or(SI-C0801到位) → io:dcs(停风机) → flow:or(YL-C0801取反) → msg:guide("循环水系统停车结束") → flow:end
```
7 个元件。原因：条件分支后各分支独立操作串联。

#### 1.3 结构化中间表示

将提取的信息组织为以下 JSON 结构（中间表示）。**解析时即区分主程序与子程序内容**：

```json
{
  "program_name": "从 SOP 标题提取",
  "description": "从 SOP 概述提取",
  "version": "v1.0",
  "main_program": {
    "description": "主程序",
    "steps": [
      {
        "step_no": 1,
        "action": "操作动作描述（主程序自身的步骤）",
        "node_type": "io:dcs | flow:or | timer:wait | msg:guide | flow:subproc",
        "subprogram_name": "子程序名称（仅 flow:subproc 时有）",
        "equipment": {
          "name": "设备名称",
          "tag": "位号(如有)",
          "action_type": "MANON | MANOF | AUTOOPT | ..."
        },
        "parameters": [
          {
            "name": "标签引用",
            "targetValue": "目标值",
            "type": "1 | 3"
          }
        ],
        "condition": {
          "tag": "条件标签",
          "judge": "== | != | > | <",
          "targetValue": "条件值",
          "branch_yes": "满足时跳转",
          "branch_no": "不满足时跳转"
        },
        "safety": {
          "threshold_tag": "监控标签",
          "threshold_value": "阈值",
          "action": "联锁动作"
        }
      }
    ]
  },
  "subprograms": [
    {
      "name": "降负荷",
      "description": "切除自控回路→三情况降负荷→关蒸喷",
      "phases": [
        {
          "phase_name": "阶段名称",
          "is_parallel": false,
          "steps": [
            {
              "step_no": 1,
              "action": "操作动作描述",
              "node_type": "io:dcs | flow:or | timer:wait | msg:guide",
              "equipment": {
                "name": "设备名称",
                "tag": "位号(如有)",
                "action_type": "MANON | MANOF | AUTOOPT | ..."
              },
              "parameters": [
                {
                  "name": "标签引用",
                  "targetValue": "目标值",
                  "type": "1 | 3"
                }
              ],
              "condition": {
                "tag": "条件标签",
                "judge": "== | != | > | <",
                "targetValue": "条件值",
                "branch_yes": "满足时跳转",
                "branch_no": "不满足时跳转"
              },
              "safety": {
                "threshold_tag": "监控标签",
                "threshold_value": "阈值",
                "action": "联锁动作"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

**主程序步骤的两种情况**：
- **纯子程序引用**：主程序仅含 `flow:subproc` 步骤，所有操作在子程序中
- **混合模式**：主程序既有自身操作步骤（如条件判断、弹窗提示），也有 `flow:subproc` 引用步骤

**单程序模式**（不拆分时）：`main_program.steps` 中直接包含全部操作步骤，`subprograms` 为空数组。

### Step 1.5: 复杂度评估与子程序拆分

**目标**：评估 SOP 文档复杂度，判断是否需要拆分为子程序。

#### 1.5.1 评估维度

| 维度 | 说明 | 阈值 |
|------|------|------|
| 步骤总数 | SOP 中的操作步骤数量 | >10 |
| 独立子系统 | 关联性弱的独立操作单元数量 | ≥2 |
| 节点预估数 | 映射为 BPMN 节点后的预估数量 | >25 |
| 阶段数 | SOP 中明确的阶段划分数量 | >5 |
| 并行场景 | 存在并行操作的场景数量 | >3 |

#### 1.5.2 触发子程序拆分的条件

**关联性分析是拆分判断的首要条件，数量维度仅作辅助确认。**

##### 关联性分析（首要判断）

AI 从以下 4 个维度分析步骤间关联性：

| 关联维度 | 说明 | 强关联示例 | 弱关联示例 |
|----------|------|------------|------------|
| **操作对象** | 涉及的设备和管路是否相同/相关 | 同一泵系统的变频+停泵+关阀 | 泵系统操作 vs 风机系统操作 |
| **控制逻辑** | 是否共享控制回路、条件判断、数据依赖 | 切回路→调变频→判断温度→关阀（连续控制链） | 降负荷控制 vs 设备停车操作 |
| **触发条件** | 是否依赖同一信号或前置步骤完成 | 都依赖"风机液偶归0反馈"触发 | 一个依赖温度达标，一个依赖液位到90% |
| **功能目标** | 是否服务于同一功能目标 | 都是"降负荷"这一件事 | 降负荷 vs 停风机是两个不同功能 |

##### 关联性判断规则

1. **强关联**：4 个维度中 ≥2 个维度一致 → 归为同一子系统
2. **弱关联**：4 个维度中 ≥3 个维度不同 → 可拆分为不同子程序
3. **边界情况**：有时序依赖但操作对象/控制逻辑/功能目标均不同 → 仍应拆分（如降负荷完成后才停风机，但两者操作对象和控制逻辑完全不同）

##### 拆分决策流程

```
Step 1: 关联性分析（首要）
  ├─ 4 维度逐一分析步骤间关联性
  ├─ 识别强关联步骤组 → 归为同一子系统
  └─ 识别弱关联边界 → 标记为拆分候选

Step 2: 数量维度确认（辅助）
  ├─ 独立子系统 ≥2 且步骤总数 >10 → 拆分
  ├─ 仅有 1 个子系统（串联流水线）→ 不拆分
  └─ 步骤总数 ≤10 → 不拆分

Step 3: 用户选择拆分/不拆分
  ├─ 不需要拆分 → 展示主程序信息表（程序名称、描述 AI 填写，用户可修改）
  ├─ 可以拆分 → 展示两个方案：
  │    ├─ 方案A：不拆分（单程序）
  │    └─ 方案B：拆分（主程序 + 子程序）— 标注 ⭐ 推荐
  ├─ 用户选择不拆分 → 按方案A执行，展示主程序信息表
  └─ 用户选择拆分 → 按方案B执行：
       ├─ 展示主程序信息表（名称、描述 AI 填写，用户可修改）
       ├─ 展示子程序信息表（每个子程序名称、描述 AI 填写，用户可修改）
       └─ 子程序名称和描述对应到主程序 XML 中 flow:subproc 元素的 name 和 subTitle 属性（subTitle 可为空字符串）
```

##### 示例：降负荷 + 停风机关阀

| 步骤 | 操作对象 | 控制逻辑 | 触发条件 | 功能目标 |
|------|----------|----------|----------|----------|
| ①切自控回路 | TIC-306/FIC-202 串级 | 切除控制回路 | 降负荷启动 | 降负荷 |
| ②三种情况降负荷 | 精硫泵变频、风机液偶 | 调变频→调液偶→判断温度 | ①完成 | 降负荷 |
| ③关蒸喷 | FV-910 | 关阀操作 | ②完成 | 降负荷 |
| ④停风机+关阀 | 主风机C301电机、磺枪阀 | 停电机+延时关阀 | 降负荷完成 | 设备停车 |

→ ①②③ 强关联（4 维度一致），归为"降负荷"子系统；④ 与①②③ 弱关联（操作对象/控制逻辑/功能目标均不同），归为"停风机"子系统 → **拆分为 2 个子程序**

#### 1.5.3 拆分原则

- **步骤守恒**：各子程序步骤数之和 = 原始 SOP 步骤总数
- **阶段不跨程序**：一个阶段不能拆散到多个子程序中
- **每个子程序步骤数控制在 3-8 步**，节点数控制在 10-20 个
- **主程序可混合**：主程序既可以包含 `flow:subproc`（引用子程序），也可以包含自身操作步骤（如条件判断、弹窗提示等），不强求仅含引用
- **子程序间关联性弱**：子程序之间通过主程序串联，无直接数据依赖
- **子程序命名规则与主程序一致**：仅支持字母、数字、下划线，必须字母开头，不允许中文
- **完整流程约束**：主程序和每个子程序都必须是完整流程，即包含 `flow:start`（开始节点）和 `flow:end`（结束节点），中间通过连线串联
  - 主程序：`开始 → [自身操作步骤] → flow:subproc(子程序1) → [自身操作步骤] → flow:subproc(子程序2) → ... → 结束`
  - 子程序：`开始 → 具体操作节点 → 结束`
  - 禁止生成只有开始没有结束、或只有操作节点没有开始/结束的不完整流程

#### 1.5.4 子程序方案的完整流程

```
1. create_program          → 创建主程序，返回主 appid
2. get_next_id × N        → 预生成 N 个子程序 ID
3. Step 2.5 位号确认       → 先主程序位号（通常无）→ 再逐个子程序位号
4. 生成主程序 XML          → flow:subproc 的 subId = 子程序预生成 ID
5. 逐个生成子程序 XML      → 结构同主程序（bpmn2:process + bpmndi:BPMNDiagram）
6. save_program 统一保存   → updateProcedures 数组包含主程序 + 所有子程序
7. compile_program        → 用主程序 appid 统一编译
```

#### 1.5.5 save_program payload 结构（子程序场景）

主程序放在 `updateProcedures` 数组中，子程序放在 `addProcedures` 数组中，**主程序和子程序字段结构不同**。完整 payload 示例详见 1.5.9 节。

**主程序 vs 子程序字段对比**：

| 字段 | 主程序 | 子程序 | 说明 |
|------|--------|--------|------|
| `sfc.refServerVariables` | `{"list": []}` | `{}` | 子程序用空对象 |
| `description` | ✅ 有 | ❌ 无 | 子程序无描述字段 |
| `id` | 主 appid | 预生成 ID | 子程序 ID = 主程序 XML 中 `flow:subproc` 的 `subId` |
| `deviceId` | ✅ "0" | ❌ 无 | — |
| `parentId` | "0" | 主 appid | — |
| `rootId` | 主 appid | 主 appid | — |
| `name` | ✅ 有 | ✅ 有 | — |
| `resourceGroupId` | ✅ "0" | ❌ 无 | — |
| `customOrder` | 固定 1 | 从 1 累计 | 主程序始终 1，子程序按顺序 1,2,3... |
| `schedulePeriod` | ✅ 1000 | ❌ 无 | — |
| `signPathId` | ✅ "0" | ❌ 无 | — |
| `branchSignPathId` | ✅ "0" | ❌ 无 | — |
| `formulaGroupId` | ✅ "0" | ❌ 无 | — |

#### 1.5.6 子程序 ID 预生成

主程序创建后，使用 `get_next_id` API 预生成子程序 ID：

```python
from api_reference import DirectPlatformClient

client = DirectPlatformClient()
main_appid = client.create_program(
    program_name="sop_shutdown_circ_water",
    description="循环水系统停车流程程序",
    group_id=selected_group_id
)

# 预生成 N 个子程序 ID
sub_ids = [client.get_next_id(id_type=0) for _ in range(N)]
# sub_ids[0] = "1343289941900010000", sub_ids[1] = ...
```

预生成的子程序 ID 用于：
- 主程序 XML 中 `flow:subproc` 的 `subId` 属性
- `save_program` 时 `updateProcedures` 中子程序的 `id` 字段

**⚠️ 强制约束：子程序 ID 必须由 `get_next_id` API 实际调用返回，严禁凭空捏造或使用示例中的 ID 值。** 生成 XML 前必须先完成 API 调用拿到真实 ID，再填入 `subId` 和 `save_program` 的 `id` 字段。

#### 1.5.7 `flow:subproc` 元素结构与 ext:data

主程序 XML 中引用子程序使用 `flow:subproc` 元素（非 `flow:otherMainProc`）：

```xml
<flow:subproc id="Activity_0s8r446" name="XHS" subId="1343295989000010000">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "showQueue": false,
    "subTitle2": "",
    "data": [],
    "interval": 0,
    "trends": [],
    "resourceGroupId": "0",
    "conditions": [],
    "deviceId": ""
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</flow:subproc>
```

**ext:data 字段说明**：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| subTitle | string | "" | 子标题 |
| showDetail | boolean | true | 是否显示详情 |
| showQueue | boolean | false | 是否显示队列 |
| subTitle2 | string | "" | 子标题2 |
| data | array | [] | 数据数组 |
| interval | integer | 0 | 间隔（0=默认） |
| trends | array | [] | 趋势数据数组 |
| resourceGroupId | string | "0" | 资源组ID |
| conditions | array | [] | 条件数组 |
| deviceId | string | "" | 设备ID |

**`flow:subproc` 与 `flow:otherMainProc` 的区别**：

| 对比项 | `flow:subproc` | `flow:otherMainProc` |
|--------|----------------|---------------------|
| 用途 | 新建从属子程序，与主程序一起保存 | 引用已生效的独立主程序 |
| ext:data | 含 resourceGroupId、conditions、deviceId | 含 mainProcedure（主程序名称[版本]） |
| 使用场景 | SOP 拆分子程序（我们的场景） | 引用平台上已有的程序 |
| 保存方式 | 子程序在同一个 save_program 中保存 | 引用的程序已存在，无需再保存 |

#### 1.5.8 不拆分时的流程

当评估结果为不拆分时，执行标准单程序流程：Step 2 → Step 2.5 → Step 3 → Step 4 → Step 5，与现有流程一致。

#### 1.5.9 真实示例参考（save_program payload）

以下为平台真实保存示例，供学习参考：

**示例 1：不含子程序（单程序保存）**

```json
{
  "addProcedures": [],
  "updateProcedures": [
    {
      "sfc": {
        "params": {"list": []},
        "refServerVariables": {"list": []},
        "variables": {"list": []},
        "timers": {"list": []},
        "aliases": {"list": []},
        "sfcRunning": {"value": "<bpmn2:process>...</bpmn2:process>\n<bpmndi:BPMNDiagram>...</bpmndi:BPMNDiagram>"},
        "sfcPausing": {"value": ""},
        "sfcResuming": {"value": ""},
        "sfcStopping": {"value": ""}
      },
      "description": {"value": "程序描述"},
      "id": "1343289709700000000",
      "deviceId": "0",
      "parentId": "0",
      "rootId": "1343289709700000000",
      "name": "t123",
      "resourceGroupId": "0",
      "customOrder": 1,
      "signPathId": "0",
      "branchSignPathId": "0",
      "formulaGroupId": "0",
      "schedulePeriod": 1000
    }
  ],
  "deleteProcedureIds": "",
  "rootId": "1343289709700000000"
}
```

**关键点**：单程序时 `parentId: "0"`、`rootId` = `id`、`updateProcedures` 仅 1 个条目。

**示例 2：含子程序（主程序 + 子程序一起保存）**

主程序 XML 中使用 `<flow:subproc subId="1343295989000010000">` 引用子程序。**主程序在 `updateProcedures`，子程序在 `addProcedures`**：

```json
{
  "addProcedures": [
    {
      "sfc": {
        "params": {"list": []},
        "refServerVariables": {},
        "variables": {"list": []},
        "timers": {"list": []},
        "aliases": {"list": []},
        "sfcRunning": {"value": "<子程序XML>"},
        "sfcPausing": {"value": ""},
        "sfcResuming": {"value": ""},
        "sfcStopping": {"value": ""}
      },
      "id": "1343295989000010000",
      "parentId": "1343289709700000000",
      "rootId": "1343289709700000000",
      "name": "XHS",
      "customOrder": 1
    }
  ],
  "updateProcedures": [
    {
      "sfc": {
        "params": {"list": []},
        "refServerVariables": {"list": []},
        "variables": {"list": []},
        "timers": {"list": []},
        "aliases": {"list": []},
        "sfcRunning": {"value": "<主程序XML，含flow:subproc引用>"},
        "sfcPausing": {"value": ""},
        "sfcResuming": {"value": ""},
        "sfcStopping": {"value": ""}
      },
      "description": {"value": "主程序描述"},
      "id": "1343289709700000000",
      "deviceId": "0",
      "parentId": "0",
      "rootId": "1343289709700000000",
      "name": "t123",
      "resourceGroupId": "0",
      "customOrder": 1,
      "schedulePeriod": 1000,
      "signPathId": "0",
      "branchSignPathId": "0",
      "formulaGroupId": "0"
    }
  ],
  "deleteProcedureIds": "",
  "rootId": "1343289709700000000"
}
```

**关键点**：详见 1.5.5 节字段对比表。

### Step 2: 生成主程序（API 调用）

**目标**：调用 Direct 平台 API 创建主程序，获取 appid。

解析完成后，**先调用 API 创建主程序**，获取 appid 供后续保存和编译使用。此时仅需与用户交互程序名称、分组、版本、描述（非必填），缺失信息交互在 Step 2.5 进行。

#### 2.1 API 配置

API 客户端配置（BASE_URL、HEADERS 等）详见 `scripts/api_reference.py`。

#### 2.2 创建主程序 (create\_program)

**创建前必须与用户交互，用户同意后才可创建，严格按流程执行，不得跳过**：

##### 2.2.1 获取分组列表

创建程序前，**必须先调用 `get_data_groups` API** 获取平台分组列表，建立 `groupId → groupName` 映射，供用户选择。完整实现详见 `scripts/api_reference.py` 的 `DirectPlatformClient.get_data_groups()`：

```python
from api_reference import DirectPlatformClient

client = DirectPlatformClient()
groups = client.get_data_groups()  # 返回 [{groupId, groupName}, ...]
```

**返回格式**：`[{groupId: "1001", groupName: "默认分组"}, {groupId: "1002", groupName: "停车程序"}, ...]`

**分组选择流程**：

1. 调用 `get_data_groups()` 获取分组列表
2. 从返回结果中找到 `groupId == "1001"` 的分组，其 `groupName` 作为**默认选中项**
3. 使用 AskUserQuestion 向用户展示所有分组的 `groupName` 列表供选择，默认选中 id 为 "1001" 对应的分组名称
4. 用户选择后，记录对应的 `groupId` 用于后续 `create_program` 调用

##### 2.2.2 参数确认

分组选定后，使用 AskUserQuestion 向用户展示以下字段（AI 根据 SOP 文档自动填充建议值，用户可修改）：

| 字段                  | 说明       | 命名规则                      | 默认值                | 示例                         |
| ------------------- | -------- | ------------------------- | ------------------ | -------------------------- |
| 程序名称(program\_name) | 主程序名称    | 仅支持字母、数字、下划线，必须字母开头，不允许中文 | 无（必填）              | sop\_shutdown\_circ\_water |
| 描述(description)     | 程序功能描述   | 无限制                       | 空（非必填）             | 循环水系统停车流程程序                |
| 版本(version)         | 程序版本号    | 无限制                       | v1.0               | v1.0                       |
| 分组(group\_id)       | 程序分组/分类  | 从 get\_data\_groups 返回列表选择 | 1001 对应的 groupName | 默认分组                       |

**program\_name 校验规则**：

- 仅允许：字母（a-z, A-Z）、数字（0-9）、下划线（\_）

- 必须以字母开头

- 不允许：中文、空格、特殊符号、数字开头

- AI 生成建议值时自动遵守此规则（如 SOP 标题"循环水停车"→ `circ_water_shutdown`）

- 用户修改时也必须校验，不符合规则时提示用户重新输入

**流程**：获取分组列表 → 展示分组选择（默认 1001 对应名称）→ 用户选择分组 → 展示程序参数建议值 → 用户确认或修改 → 用户明确同意后才调用 API。用户未同意前禁止调用 create\_program。

```python
from api_reference import DirectPlatformClient

client = DirectPlatformClient()
appid = client.create_program(
    program_name="sop_shutdown_circ_water",
    description="循环水系统停车流程程序",
    group_id=selected_group_id  # 用户从分组列表中选择的 groupId
)
```

**调用时机**：文档解析完成后即可调用。**必须等用户确认程序信息（含分组选择）后才可调用。**

### Step 2.5: 缺失信息交互

**目标**：创建程序后、生成 XML 之前，与用户交互补充 SOP 中缺失或需要确认的信息。

#### 2.5.1 位号信息确认（必须执行）

**此步骤为强制执行步骤，无论 SOP 中是否包含明确位号信息，都必须汇总所有位号并展示给用户逐条确认。**

**子程序场景**：当 Step 1.5 评估为拆分时，位号确认按以下顺序执行：
1. 先展示主程序位号（主程序仅含 `flow:subproc` 引用节点，通常无位号，可跳过）
2. 再逐个展示子程序位号（每个子程序的所有位号汇总展示给用户确认）

1. **位号信息确认**：SOP 文档中所有涉及位号的地方，均需汇总展示给用户逐条确认

   - 解析 SOP 时，提取所有需要位号的元件（io:dcs 操作位号、flow:or/flow:and/flow:branch 条件位号、timer 变量等），汇总为位号确认清单

   - 每条位号展示其所属步骤和用途（如「Step 3 - 启动泵 P0801A 的 MANON 位号」），让用户清楚位号的上下文

   - SOP 中已有明确位号（如 `P0801A`）时，先默认填入位号输入框，展示给用户，用户可直接修改

   - 位号输入框旁设有「搜索」按钮，点击后调用 `get_tags` 接口，弹框展示位号选择器供用户选择（完整实现详见 `scripts/api_reference.py`）

   - 用户也可以直接在输入框中自己填写位号信息

   - 以上所有方式填入的位号，写入 XML 时均须用 `#()` 包裹（如 `HIC_V1001A_1.MANON` → `#(HIC_V1001A_1.MANON)`），编译失败修复时新位号也须遵循此规则

     **位号选择器 UI 布局**（点击「搜索」按钮后弹出）：

     - **顶部筛选区**：位号名输入框（模糊搜索）+ 数据类型下拉框（浮点/整型/字符串）+ 查询按钮 + 重置按钮

     - **中部表格区**：分页展示位号列表，列为「位号名」「数据类型」「备注」，每行带单选按钮，支持滚动

     - **底部分页区**：总记录数 + 页码导航 + 每页条数选择 + 取消/确定按钮

     | type 值 | 类型 | 适用场景               |
     | ------ | ---- | -------------------- |
     | 1      | 浮点  | 温度、压力、流量、频率等模拟量 |
     | 2      | 整型  | 次数、计数等整型量           |
     | 3      | 字符串 | 开关、运行/停止、阀位等数字量     |

   - 用户通过选择器选中位号或手动填写后，记录对应的位号信息

2. **参数值缺失补充**：SOP 描述了操作但缺少具体参数值（如"加热至适当温度"）

   - 向用户展示缺失参数的上下文，请用户提供具体数值

3. **安全阈值补充**：SOP 描述了安全要求但未给具体阈值（如"压力过高时报警"）

   - 向用户展示安全要求描述，请提供具体阈值和联锁动作

4. **模糊描述澄清**：SOP 描述有歧义（如"适当加热"、"缓慢开启"）

   - 向用户展示原文，请澄清为可量化参数

#### 2.5.2 交互方式

- 使用 `AskUserQuestion` 工具，每次提问不超过 4 个问题

- 每个问题提供合理的选项（基于 SOP 上下文推断）

- 始终提供"我来手动填写"选项

- 问题使用中文

### Step 3: 生成 BPMN XML

**目标**：根据结构化中间表示，生成符合 Direct 平台格式的 BPMN XML。

**子程序场景**：当 Step 1.5 评估为拆分时，需要生成多份 XML：
- 1 份主程序 XML（包含 `flow:subproc` 引用各子程序，`subId` = 预生成的子程序 ID）
- N 份子程序 XML（每个子程序独立一份，结构同主程序：`bpmn2:process` + `bpmndi:BPMNDiagram`）
- 主程序 XML 中 `flow:subproc` 的 `subId` 属性必须与 `save_program` 时子程序的 `id` 字段一致

#### 3.0 前置读取（强制执行）

**生成 XML 前，必须使用 Read 工具读取 `references/` 目录下的 `element_schema.json`, `node_reference.md`, `xml_template.xml` 参考文件，将其内容加入上下文，作为后续生成 XML 的唯一规则来源。**

必须读取的文件：

| 文件 | 用途 |
|------|------|
| `references/element_schema.json` | 元件结构定义、必填属性、子元素规则、ID 模式、ext_data 结构 |
| `references/node_reference.md` | 各元件类型完整示例（Process XML + BPMNDiagram XML）、坐标规则 |
| `references/xml_template.xml` | XML 基础模板，生成时以此为基础，仅在注释标记的可扩展位置插入新元素 |

**严格限制**：

- **唯一规则来源**：生成 XML 时只能参考上述 `references/` 目录中的文件内容，不允许参考其他来源（如训练知识、网络搜索、历史记忆等）

- **禁止凭记忆生成**：所有元件结构、属性、子元素、ext_data 格式必须对照 `references/` 中的定义和示例生成

- **禁止修改模板**：以 `xml_template.xml` 为基础时，严禁修改、删除、替换任何原始模板内容（标签、属性、文本、注释、格式），仅允许在注释标记的可扩展位置插入新元素

- **编译失败重试也必须重新读取**：编译失败后修正 XML 前，必须重新 Read 上述参考文件，禁止凭记忆修改

#### 3.1 XML 整体结构

**生成的 XML 必须严格遵循以下结构，不允许包含任何额外的包装层：**

- 禁止 `<?xml version="1.0"?>` 声明

- 禁止 `<bpmn2:definitions>` 根元素

- 禁止 `xmlns` 命名空间声明

- 禁止任何模板中不存在的元素

**正确结构**（直接以 `<bpmn2:process>` 开头）：

```xml
<bpmn2:process id="Process_1" isExecutable="true">
  <!-- 节点定义区（组态信息） -->
  <!-- 1. 开始节点 flow:start -->
  <!-- 2. 流程节点（io:dcs / io:var / io:calc / flow:and / flow:or / flow:branch / timer:wait / timer:cond / timer:start / timer:restart / timer:stop / msg:guide / msg:confirm / flow:parallel1 / flow:parallel2 / flow:subproc） -->
  <!-- 3. 结束节点 flow:end -->
  <!-- 4. 连线 bpmn2:sequenceFlow -->
</bpmn2:process>
<bpmndi:BPMNDiagram id="BPMNDiagram_1">
  <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
    <!-- 图形布局区 -->
    <!-- 1. 先输出所有 bpmndi:BPMNShape（节点坐标） -->
    <!-- 2. 再输出所有 bpmndi:BPMNEdge（连线路径） -->
  </bpmndi:BPMNPlane>
</bpmndi:BPMNDiagram>
```

**必须严格按照** **`references/xml_template.xml`** **模板格式生成，不得偏离。**

**4 条关键生成规则（违反会导致平台显示异常）**：

1. **BPMNPlane 中 BPMNShape 在前、BPMNEdge 在后** — 先节点后连线，顺序不能颠倒
2. **ID 必须完全匹配** — sequenceFlow 的 `id` 必须与 BPMNEdge 的 `bpmnElement` 完全一致；节点的 `id` 必须与 BPMNShape 的 `bpmnElement` 完全一致。不匹配则连线不显示
3. **Shape id 格式**：`{node_id}_di`（如 `Event_start_di`）
4. **Edge id 格式**：`{flow_id}_di`（如 `Flow_1_di`）

#### 3.2 节点类型映射规则

详见 `references/node_reference.md` 文件。核心映射逻辑：

| SOP 内容       | BPMN 节点类型              | 说明                   |
| ------------ | ---------------------- | -------------------- |
| 流程开始         | `<flow:start>`         | 每个流程唯一开始节点           |
| 流程结束         | `<flow:end>`           | 可有多条入边               |
| 设备操作（开/关/写值） | `<io:dcs>`             | 对 DCS 位号 `#(xxx)` 写值 |
| 条件判断-单条件     | `<flow:or>`            | 单条件成立→是，不成立→否        |
| 条件判断-多条件全满足  | `<flow:and>`           | 所有条件成立→是，任一不成立→否     |
| 多选一分支        | `<flow:branch>`        | N 个分支，沿最先满足的执行       |
| 等待/延时        | `<timer:wait>`         | 等待指定时间后继续            |
| 计时器判断        | `<timer:cond>`         | 超时判断，二选一分支           |
| 开始计时器        | `<timer:start>`        | 定义并启动计时器变量           |
| 提示消息（不暂停）    | `<msg:guide>`          | 提示信息，程序继续            |
| 确认消息（暂停等待）   | `<msg:confirm>`        | 需人工确认才继续             |
| 并行操作         | `<flow:parallel1>`     | 多分支同时执行              |
| 文本注释         | `<util:text>`          | 红色备注文本               |
| 信号上跳变        | `<flow:risingEdge>`    | 检测信号从0→非0            |
| 信号下跳变        | `<flow:fallingEdge>`   | 检测信号从非0→0            |
| 字符串拼接        | `<io:concat>`          | 拼接字符串赋值给变量           |
| 文件导出         | `<io:fileExport>`      | 导出数据至csv/xlsx        |
| 文件导入         | `<io:fileImport>`      | 从csv/xlsx导入数据        |
| 修改标签         | `<io:modifyLabel>`     | 动态修改主程序标签            |
| 修改属性         | `<io:modifyProps>`     | 修改程序自定义字段            |
| 引用子程序        | `<flow:subproc>` | 新建从属子程序，与主程序一起保存 |
| HTTP请求       | `<flow:request>`       | 向外部URL发送请求           |
| 报警消息         | `<msg:alarm>`          | 报警提示，程序不暂停           |
| 暂停计时器        | `<timer:pause>`        | 暂停计时器计时              |
| 时钟           | `<timer:clock>`        | 等待到指定时间点             |

**关键选择规则**：

| SOP 场景            | 选择                   | 理由         |
| ----------------- | -------------------- | ---------- |
| "弹窗提示XXX"         | msg:guide            | 仅提示，不暂停    |
| "弹窗确认是否XXX，点击是/否" | msg:confirm          | 需用户确认才继续   |
| "请输入XXX值"         | msg:confirm + set\[] | 需用户输入      |
| "判断A是否为B"         | flow:or              | 单条件判断      |
| "判断A且B都满足"        | flow:and             | 多条件同时满足    |
| "流量≥900且振动≤4.5"   | flow:and             | 复合条件，都须满足  |
| "3台泵中判断哪2台运行"     | flow:branch          | 多选一分支      |
| "同时操作A/B/C三台泵"    | flow:parallel1       | 并行执行       |
| "判断是A泵还是B泵"       | flow:branch          | 多选一互斥分支    |
| "信号从0变1时触发"       | flow:risingEdge      | 上跳变检测      |
| "信号从1变0时触发"       | flow:fallingEdge     | 下跳变检测      |
| "报警提示但不暂停"        | msg:alarm            | 报警消息，不暂停程序 |
| "暂停计时器"           | timer:pause          | 暂停计时       |
| "每天01:00执行"       | timer:clock          | 时钟定时触发     |
| "拼接字符串赋值"         | io:concat            | 字符串操作      |
| "导出数据到文件"         | io:fileExport        | 文件导出       |
| "从文件读取数据"         | io:fileImport        | 文件导入       |

#### 3.3 标签引用格式

Direct 平台有两种引用格式：

**DCS 位号**（用于 io:dcs, flow:or, flow:and, flow:branch）：`#(系统.子系统.类型.位号_动作)`

**程序变量**（用于 timer）：`$(变量名)`

**标签路径分类**（从真实 XML 提取）：

| 路径模式                              | 含义            | 示例                                      |
| --------------------------------- | ------------- | --------------------------------------- |
| `#(M6.Device1.Direct.xxx)`        | Direct 平台内部变量 | `OVSC_3001`, `START_STATE_3401`         |
| `#(M6-2.Device1.MOT.MOT_xxx)`     | 电机设备位号        | `MOT_P707B_MANON`, `_MANOF`, `_AUTOOPT` |
| `#(M6-2.Device1.PIDA.SCPxxx_OUT)` | PID 控制器输出     | `SCP0707B_OUT`, `_MODE`                 |
| `#(M6-2.Device1.VAL.EV_xxx)`      | 阀门设备位号        | `EV_0707B_MANON`, `_MANOF`, `_AUTOOPT`  |
| `#(M6.DM.DI.xxx)`                 | 数字量输入（运行/反馈）  | `YL_P0707B`, `ZSO_EV0707B`              |
| `#(M6.DM.DM.xxx)`                 | 数字量测量         | `KY1_TX001`                             |
| `#(M6.AM.AI.xxx)`                 | 模拟量输入（压力/温度）  | `PI_403`, `SI_P0707B`                   |
| `#(M6.AM.AM.xxx)`                 | 模拟量测量（振动等）    | `XI_P0707B_01`                          |

**位号后缀约定**：

- `_MANON` → 启动/开（targetValue=1）

- `_MANOF` → 停止/关（targetValue=0）

- `_AUTOOPT` → 置手动（targetValue=0）

- `_OUT` → PID 输出（频率/开度值）

- `_MODE` → PID 模式（0=手动）

**type 字段**：

- `type:1` → 模拟量（压力/温度/频率/电流），用于 io:dcs 模拟操作、flow:and 条件

- `type:3` → 数字量（运行/阀位/状态），用于 io:dcs 开关操作、flow:or 条件

程序变量模式：

- 计时器变量：`$(JSQ_001)` — 用于 timer:start/cond

- 自定义变量：`$(VAR_001)` — 用于 io:var 写值

- 计算目标：`$(TOTAL_FLOW)` — 用于 io:calc 赋值

#### 3.4 连线规则（关键修正）

sequenceFlow 的 ext:data 格式**取决于源节点类型**，situation 连线**不能包含 lineType**：

| 源节点类型                                                                                                                                                                                             | 连线变体               | name 属性        | ext:data               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | -------------- | ---------------------- |
| flow:start, flow:end, flow:risingEdge, flow:fallingEdge, flow:subproc, flow:request, io:*, timer:wait, timer:start, timer:restart, timer:stop, timer:pause, timer:clock, msg:*（含 msg:alarm） | **plain**          | 无              | `{"lineType":1}`       |
| flow:and, flow:or, timer:cond 的"是"分支                                                                                                                                                              | **situation\_yes** | `name="条件成立"`  | `{"situation":"yes"}`  |
| flow:and, flow:or, timer:cond 的"否"分支                                                                                                                                                              | **situation\_no**  | `name="条件不成立"` | `{"situation":"no"}`   |
| flow:branch 的每个分支                                                                                                                                                                                 | **branch\_option** | `name="{选项名}"` | `{"situation":"{索引}"}` |

**约束**：

- `situation_yes/no` 的 ext:data **只含** **`situation`** **字段，禁止包含** **`lineType`**

- 条件判断节点（flow:and, flow:or, timer:cond）**必须有两条 outgoing**（yes + no）

- 非条件节点的 outgoing 使用 **plain** 格式

- 每条 sequenceFlow 必须有对应的 BPMNEdge（含 di:waypoint 坐标）

##### 3.4.1 连线生成流程（使用 layout_generator.py 自动生成）

**禁止手写连线 XML**，必须使用 `layout_generator.py` 的方法自动生成，避免遗漏：

```python
from layout_generator import LayoutGenerator

gen = LayoutGenerator()

# 1. 添加节点
gen.add_node("Event_start", "start", "开始")
gen.add_node("Activity_1", "dcs", "操作1")
gen.add_node("Activity_2", "or", "条件判断")

# 2. 添加连线（指定 situation 参数）
gen.add_flow("Flow_1", "Event_start", "Activity_1")                          # plain
gen.add_flow("Flow_2", "Activity_1", "Activity_2")                           # plain
gen.add_flow("Flow_yes", "Activity_2", "Activity_3", situation="yes")       # situation_yes
gen.add_flow("Flow_no", "Activity_2", "Activity_4", situation="no")         # situation_no

# 3. 布局
gen.layout_vertical(["Event_start", "Activity_1", "Activity_2"], center_x=500, start_y=60)

# 4. 自动生成 XML（三部分缺一不可）
node_io = gen.get_incoming_outgoing_xml("Activity_1")    # 节点的 incoming/outgoing 引用
flows   = gen.get_sequence_flow_xml()                   # 所有 <bpmn2:sequenceFlow> 元素
diagram = gen.get_diagram_xml()                         # 完整 <bpmndi:BPMNDiagram> 节

# 5. 完整性校验（生成 XML 前必须执行）
issues = gen.check_connection_integrity()
if issues:
    for issue in issues:
        print(f"连线问题: {issue}")
```

**三部分 XML 必须同时生成**：

| XML 部分 | 方法 | 放置位置 | 作用 |
|---------|------|---------|------|
| 节点 incoming/outgoing | `get_incoming_outgoing_xml(node_id)` | 节点元素内部 | 声明节点的入边和出边 |
| sequenceFlow | `get_sequence_flow_xml()` | `<bpmn2:process>` 内、节点之后 | 定义连线本身（含变体和 ext:data） |
| BPMNEdge | `get_diagram_xml()` 内含 | `<bpmndi:BPMNDiagram>` 内 | 定义连线的图形路径（坐标） |

##### 3.4.2 连线完整性检查清单

生成 XML 前必须逐项确认：

- [ ] 每条 sequenceFlow 的 `id` 与 BPMNEdge 的 `bpmnElement` 完全一致
- [ ] 每个节点的 `incoming`/`outgoing` 文本与对应的 sequenceFlow `id` 完全一致
- [ ] plain 连线包含 `<ext:data>{"lineType":1}</ext:data>`（非自闭合标签）
- [ ] situation_yes 连线包含 `<ext:data>{"situation":"yes"}</ext:data>`，`name="条件成立"`
- [ ] situation_no 连线包含 `<ext:data>{"situation":"no"}</ext:data>`，`name="条件不成立"`
- [ ] situation 连线的 ext:data **不含 lineType 字段**
- [ ] 条件节点（and/or/cond）有且仅有 2 条 outgoing（yes + no）
- [ ] 起始节点只有 outgoing，无 incoming
- [ ] 结束节点只有 incoming，无 outgoing
- [ ] 中间节点同时有 incoming 和 outgoing
- [ ] 调用 `check_connection_integrity()` 返回空列表（无问题）

#### 3.5 布局坐标生成（禁止重叠 + 连线可见）

**核心原则：元件不允许重叠，连线必须明显并可见。**

##### 3.5.1 节点尺寸

| 类型                                                                          | 宽×高         |
| --------------------------------------------------------------------------- | ----------- |
| flow:start / flow:end                                                       | 54×54       |
| io:dcs / io:var / io:calc                                                   | 200×60      |
| flow:and / flow:or / flow:branch                                            | 200×60      |
| flow:risingEdge / flow:fallingEdge                                          | 200×60      |
| io:concat / io:fileExport / io:fileImport / io:modifyLabel / io:modifyProps | 200×60      |
| flow:subproc / flow:request                                           | 200×60      |
| timer:\* / msg:\*（含 timer:pause / timer:clock / msg:alarm）                  | 200×60      |
| flow:parallel1                                                              | 800×600     |
| flow:parallel2                                                              | 1460×1290   |
| parallelStart / parallelEnd                                                 | 宽=容器宽度, 高=5 |

##### 3.5.2 防重叠间距规则

**垂直方向（同列堆叠）**：

- 节点间最小间距：**≥100px**（含连线和标签空间）

- 计算公式：`node_B.y = node_A.y + node_A.height + 100`

**水平方向（并行分支）**：

- 分支间最小间距：**≥300px**（含连线弯折空间）

- 计算公式：`column_B.x = column_A.x + column_A.width + 300`

**并行容器边界**：

- 容器必须包含所有子节点

- 子节点与容器边缘 padding：**≥40px** 四周

- 容器宽度 = 最右子节点右边缘 - 最左子节点左边缘 + 80

- 容器高度 = 最底子节点底边缘 - 最顶子节点顶边缘 + 80

**重叠检查**（生成后必须验证）：

```
对任意两个节点 A、B：
  不重叠条件 = A.x + A.w + 间距 ≤ B.x  或  B.x + B.w + 间距 ≤ A.x
  或          A.y + A.h + 间距 ≤ B.y  或  B.y + B.h + 间距 ≤ A.y
若不满足，必须调整坐标。
```

##### 3.5.3 连线可见性规则

**BPMNEdge 生成要求**：

- 每条 sequenceFlow **必须**有对应的 BPMNEdge

- 每个 BPMNEdge **至少 2 个 di:waypoint**

- 连线路径**不得穿过任何节点矩形区域**

**路径点计算规则**（`calc_waypoints` 自动识别 5 种场景）：

```
情况1：源和目标在同一列（x 中心差 < 10px）
  → 垂直直连
  waypoint1 = (src.cx, src.bottom)
  waypoint2 = (tgt.cx, tgt.top)

情况2：源和目标不在同一列
  → L 形路径（3~4 个 waypoint）
  mid_y = (src.bottom + tgt.top) / 2
  waypoint1 = (src.cx, src.bottom)
  waypoint2 = (src.cx, mid_y)
  waypoint3 = (tgt.cx, mid_y)
  waypoint4 = (tgt.cx, tgt.top)

情况3：parallelStart → 分支首节点（容器内连线）
  → 从 pstart 底部对齐到分支节点 x 中心
  waypoint1 = (branch.cx, pstart.bottom)
  waypoint2 = (branch.cx, branch.top)

情况4：分支末节点 → parallelEnd（容器内连线）
  → 从分支节点底部对齐到 pend 顶部
  waypoint1 = (branch.cx, branch.bottom)
  waypoint2 = (branch.cx, pend.top)

情况5：并行容器 ↔ 外部节点
  → 穿越容器边界的路径
  容器 incoming（外部→容器）：
    waypoint1 = (src.cx, src.bottom)
    waypoint2 = (src.cx, container.top - 50)   # 容器上方
    waypoint3 = (pstart.cx, container.top - 50)
    waypoint4 = (pstart.cx, pstart.top)        # 进入 pstart
  容器 outgoing（容器→外部）：
    waypoint1 = (pend.cx, pend.bottom)          # 从 pend 底部出发
    waypoint2 = (pend.cx, container.bottom + 50) # 离开容器
    waypoint3 = (tgt.cx, container.bottom + 50)  # 水平移动
    waypoint4 = (tgt.cx, tgt.top)                # 进入目标
```

**连线避让规则**：

- mid\_y 必须落在两个节点之间的空白区域（不与任何节点 y 范围重叠）

- 若 mid\_y 落在某节点内，调整为该节点下方 + 20px

- 水平线段不得穿过其他节点的 x 范围（若穿过，改用 U 形绕行）

- 容器节点不参与避让检测（连线可穿越容器边界）

##### 3.5.4 坐标生成工具

使用 `scripts/layout_generator.py` 脚本自动生成防重叠坐标和可见连线路径：

```python
# 标准库导入
import json
import sys
import os

# 本地模块导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
from layout_generator import LayoutGenerator

gen = LayoutGenerator()

# 添加节点（自动匹配尺寸）
gen.add_node("start_1", "start")
gen.add_node("dcs_1", "dcs", "启动泵")
gen.add_node("or_1", "or", "判断运行信号")
gen.add_node("end_1", "end")

# 添加连线
gen.add_flow("f1", "start_1", "dcs_1")
gen.add_flow("f2", "dcs_1", "or_1")
gen.add_flow("f3", "or_1", "end_1", situation="yes")

# 垂直布局（自动 100px 间距，居中对齐）
gen.layout_vertical(["start_1", "dcs_1", "or_1", "end_1"],
                    center_x=500, start_y=60)

# 验证无重叠
overlaps = gen.check_overlaps()
assert not overlaps, f"发现重叠: {overlaps}"

# 输出 BPMNShape 和 BPMNEdge XML
print(gen.get_shape_xml())
print(gen.get_edge_xml())
```

**并行布局示例（竖向 flow:parallel1）**：

```python
# 1. 添加并行容器、parallelStart、parallelEnd 节点
gen.add_node("parallel_1", "parallel1")
gen.add_node("pstart_1", "pstart")
gen.add_node("pend_1", "pend")

# 2. 添加各分支节点
branch_a = ["dcs_pump_a", "or_pump_a", "dcs_valve_a", "or_valve_a"]
branch_b = ["dcs_pump_b", "or_pump_b", "dcs_valve_b", "or_valve_b"]
branch_c = ["dcs_pump_c", "or_pump_c", "dcs_valve_c", "or_valve_c"]
for nid in branch_a + branch_b + branch_c:
    gen.add_node(nid, "dcs" if nid.startswith("dcs") else "or")

# 3. 竖向并行布局（分支竖向堆叠，分支间水平排列）
gen.layout_parallel1(
    container_id="parallel_1",
    pstart_id="pstart_1",
    pend_id="pend_1",
    branch_groups=[branch_a, branch_b, branch_c],
    start_x=100, start_y=280
)

# 4. 添加连线（calc_waypoints 自动识别并行场景）
# 外部 → 容器
gen.add_flow("f_ext_in", "prev_node", "parallel_1")
# parallelStart → 各分支首节点
gen.add_flow("f_a_start", "pstart_1", "dcs_pump_a")
gen.add_flow("f_b_start", "pstart_1", "dcs_pump_b")
gen.add_flow("f_c_start", "pstart_1", "dcs_pump_c")
# 各分支内部连线
gen.add_flow("f_a_mid", "dcs_pump_a", "or_pump_a")
gen.add_flow("f_b_mid", "dcs_pump_b", "or_pump_b")
gen.add_flow("f_c_mid", "dcs_pump_c", "or_pump_c")
# 各分支末节点 → parallelEnd
gen.add_flow("f_a_end", "or_valve_a", "pend_1")
gen.add_flow("f_b_end", "or_valve_b", "pend_1")
gen.add_flow("f_c_end", "or_valve_c", "pend_1")
# 容器 → 外部
gen.add_flow("f_ext_out", "parallel_1", "next_node")

# 5. 验证
overlaps = gen.check_overlaps()  # 容器-子节点自动豁免
assert not overlaps, f"发现重叠: {overlaps}"
issues = gen.check_parallel_integrity()  # 验证并行结构完整
assert not issues, f"并行结构问题: {issues}"
```

**并行布局示例（横向 flow:parallel2）**：

```python
gen.add_node("parallel_2", "parallel2")
gen.add_node("pstart_2", "pstart")
gen.add_node("pend_2", "pend")

# 横向并行布局（分支水平排列，分支间垂直堆叠）
gen.layout_parallel2(
    container_id="parallel_2",
    pstart_id="pstart_2",
    pend_id="pend_2",
    branch_groups=[branch_a, branch_b, branch_c],
    start_x=100, start_y=280
)
```

**核心功能**：

- `layout_vertical()`：垂直堆叠，100px 间距

- `layout_parallel1()`：竖向并行（flow:parallel1），分支竖向堆叠+水平排列，自动定位 pstart/pend

- `layout_parallel2()`：横向并行（flow:parallel2），分支水平排列+垂直堆叠，自动定位 pstart/pend

- `layout_container()`：手动计算容器边界

- `calc_waypoints()`：自动识别 5 种场景（普通/pstart→branch/branch→pend/容器入/容器出）

- `calc_u_waypoints()`：U 形绕行（复杂场景）

- `check_overlaps()`：验证无重叠（容器-子节点自动豁免）

- `check_parallel_integrity()`：验证并行结构完整性（pstart/pend 存在、子节点在容器范围内）

#### 3.6 完整元素 schema 参考

节点类型的完整 schema 定义见 `references/element_schema.json`，包含：

- 18 种节点类型的 XML 模板、ext:data schema、必选/可选字段

- sequenceFlow 4 种变体（plain/situation\_yes/situation\_no/branch\_option）

- 连线选择规则（按源节点类型确定变体）

- BPMNShape/BPMNEdge 图形模板

#### 3.7 生成后用户确认

**生成 XML 后必须向用户展示流程图，用户确认后才可执行 Step 4。**

展示内容：

- 使用 PureShowWidget 或可视化方式展示流程图（节点 + 连线）

- 列出节点数量、连线数量

- 列出关键流程路径摘要

用户可在此步骤进行：

- **添加**：新增节点或连线（如遗漏的步骤）

- **删除**：移除不需要的节点或连线

- **修改**：调整节点参数、标签、连接关系

处理流程：

1. 展示流程图给用户
2. 用户提出修改意见（如有）
3. 根据修改意见修正 XML
4. 重新展示修改后的流程图
5. 用户确认无误后进入 Step 4

**用户未确认前禁止执行 Step 4。**

### Step 4: 保存（API 调用）

**目标**：将生成的 BPMN XML 通过 API 保存到 Step 2 创建的主程序。

**⚠️ 保存前置条件（强制）**：`save_program` 必须在全部 XML 生成完毕后才可调用。子程序场景下，主程序 XML + 所有子程序 XML 必须全部生成完毕，一次性拼接到同一个 `save_program` 调用中保存。禁止先保存部分 XML 再补存。

**子程序场景**：当 Step 1.5 评估为拆分时，主程序和所有子程序的 XML 拼接到同一个 `save_program` 调用的 `updateProcedures` 数组中。具体 payload 结构详见 Step 1.5.5 节。

#### 4.1 保存程序 (save\_program)

**接口**：`POST {BASE_URL}/vxdirect/procedure/all`

请求体结构详见 1.5.9 节示例。`sfcRunning.value` 存放 Step 3 生成的完整 BPMN XML 字符串。`id` 和 `rootId` 使用 Step 2 返回的 appid。

#### 4.2 API 客户端参考代码

完整的 API 客户端实现详见 `scripts/api_reference.py` 文件。

### Step 5: 编译（API 调用）

**目标**：编译已保存的程序，验证流程逻辑正确性。

**⚠️ 硬性要求（必须严格执行）：保存成功后禁止自动编译。无论单程序还是包含子程序，必须先列出已生成的 XML 文件信息，经用户确认后才可执行编译。违反此规则属于严重错误。**

#### 5.0 保存后确认

保存成功后，向用户展示：

| 展示项 | 说明 |
|--------|------|
| XML 文件列表 | 主程序 XML 路径 + 各子程序 XML 路径 |
| 节点/连线统计 | 每个 XML 的节点数、连线数 |
| 程序信息 | 程序名称、appid、分组 |
| 保存结果 | 成功/失败 |

使用 AskUserQuestion 询问用户：
- **是否编译程序** — 用户确认后才执行 compile_program
- 用户可选择"暂不编译"（后续在平台手动编译）

#### 5.1 编译程序 (compile\_program)

**子程序场景**：使用主程序 appid 统一编译，平台会自动编译关联的所有子程序。无需逐个编译子程序。

**接口**：`POST {BASE_URL}/vxdirect/procedureHead/cmd`

请求体：

```json
{
  "ids": "appid",
  "cmd": 1
}
```

**编译失败处理**：

- 返回错误信息中包含具体节点/连线问题

- 根据错误信息修正 XML 后重新执行 Step 4→5（仅 save → compile，不回退到 Step 3）

- **严格限制：禁止创建任何新程序（包括测试程序）** — `create_program` 在整个流程中只允许调用一次，只允许在本次已创建的程序（同一 appid）上修正 XML，重新 save\_program → compile\_program

**重试时核心约束（必须遵守）**：

- **禁止减少元件** — 不得删除任何节点

- **禁止修改结构** — 不得删除连线、不得改变节点间连接关系、不得改变流程逻辑

- **必须按照用户在 Step 3.7 确认的流程结构进行保存与编译** — 节点数量、连线数量、连接关系必须与用户确认时完全一致

- 仅允许修正数据层面的错误：位号补全、参数值修正、XML 格式修复、ID 不匹配修复

**最大重试 3 次**，每次重试前：

1. 分析编译错误原因
2. **位号相关问题**（位号不存在、位号路径错误、位号类型不匹配、位号缺少 `#()` 包裹等）→ **必须通过 AskUserQuestion 向用户交互**：
   - 展示出错节点名称、错误位号、错误原因
   - 提供三种修改方式供用户选择：
     - **手动输入新位号** — 用户直接填写正确位号
     - **调用 `get_tags` 接口搜索** — 按名称/类型查询位号列表，弹框展示候选列表供用户选择
     - **从 SOP 重新提取** — 回到 SOP 原文确认设备对应位号
   - 用户确认后，修正 XML 中对应位号，重新 save\_program → compile\_program
3. **其他缺数据/参数**（如参数值为空）→ 使用 AskUserQuestion 与用户交互补充
4. **不缺数据**（如 XML 格式错误、ID 不匹配等）→ 自行修复，不打扰用户
5. 修正后重新 save\_program → compile\_program

**3 次后仍失败**：停止重试，向用户报告：

- 失败原因（编译错误详情）

- 建议解决方案（具体到哪个节点/连线需要什么数据）

- 已创建的程序 appid（用户可在 Direct 平台手动修正）

### Step 6: 结果确认

向用户报告：

- 程序名称、appid

- 生成的节点数量、连线数量

- 编译结果（成功/失败）

- 如有交互补充的信息，列出补充项

***

## 处理流程决策树

```
SOP 文档输入
  │
  ├─ Step 1: 解析文档
  │    ├─ 读取文档内容（按格式选择读取方式）
  │    ├─ AI 理解文档结构，提取五大信息维度
  │    │    ├─ 阶段划分
  │    │    ├─ 操作步骤 + 参数
  │    ├─ 设备/管路信息
  │    ├─ 参数值
  │    └─ 安全/联锁条件
  │
  │    └─ 构建结构化中间表示 (JSON)
  │
  ├─ Step 1.5: 复杂度评估与子程序拆分
  │    ├─ 评估步骤数、关联性、独立子系统数
  │    ├─ 关联性弱且步骤多?
  │    │    ├─ 是 → 拆分为子程序（与用户讨论确认方案）
  │    │    │    ├─ create_program → 主程序 appid
  │    │    │    ├─ get_next_id × N → 子程序 ID
  │    │    │    ├─ 位号确认（主程序 → 逐个子程序）
  │    │    │    ├─ 生成主程序 XML（flow:subproc subId=子程序ID）
  │    │    │    ├─ 逐个生成子程序 XML
  │    │    │    ├─ save_program（统一保存主+子）
  │    │    │    └─ compile_program（主程序 appid 统一编译）
  │    │    └─ 否 → 走标准单程序流程
  │    │
  ├─ Step 2: 创建主程序 (API)
  │    ├─ get_data_groups → 获取分组列表（默认选 1001）
  │    ├─ 用户选择分组 + 确认程序名称/版本/描述
  │    └─ create_program → 返回 appid
  │
  ├─ Step 2.5: 缺失信息交互
  │    ├─ 位号信息确认 → 逐条确认/搜索/手动填写
  │    ├─ 参数值缺失? → 交互补充
  │    ├─ 安全阈值缺失? → 交互补充
  │    └─ 描述模糊? → 交互澄清
  │
  ├─ Step 3: 生成 BPMN XML
  │    ├─ 读取 references/ 参考文件（强制）
  │    ├─ 映射节点类型
  │    ├─ 生成 ext:data JSON
  │    ├─ 生成 sequenceFlow 连线
  │    └─ 生成 BPMNDiagram 坐标（使用 layout_generator.py）
  │
  ├─ Step 4: 保存 (API)
  │    └─ save_program → 将 XML 保存到 appid
  │         （子程序场景：主+子拼接到 updateProcedures 数组）
  │
  ├─ Step 5: 编译 (API)
  │    └─ compile_program → 编译验证（子程序用主程序 appid 统一编译）
  │         ├─ 成功 → Step 6
  │         └─ 失败 → 修正 XML → 回到 Step 3
  │
  └─ Step 6: 报告结果
```

***

## 注意事项

1. **ID 唯一性**：所有节点 id 和连线 id 必须唯一，使用 `Activity_` + 随机字符串 或 `Flow_` + 随机字符串 格式
2. **引用完整性**：`sourceRef` 和 `targetRef` 必须指向已定义的节点 id；`bpmn2:incoming`/`bpmn2:outgoing` 必须指向已定义的 Flow id
3. **并行处理**：当 SOP 中有"同时"操作多台设备时，使用 `flow:parallel1`（竖向）或 `flow:parallel2`（横向）容器。并行容器必须包含 `flow:parallelStart` 和 `flow:parallelEnd` 子元件。使用 `layout_parallel1()` 或 `layout_parallel2()` 自动布局，`calc_waypoints()` 自动识别 5 种并行连线场景。容器 BPMNShape 必须设置 `isExpanded="true"` 属性。生成后用 `check_parallel_integrity()` 验证结构完整性
4. **条件分支**：`flow:or` 节点必须有两个 outgoing（是/否），不能只有一个
5. **XML 转义**：XML 内容放入 `sfcRunning.value` 时，注意 JSON 字符串中的转义（`<` → 无需转义，因 XML 已在 JSON 字符串内，但 `"` 需转义为 `\"`）
6. **时间戳**：`createdTime` 和 `updatedTime` 使用毫秒级 Unix 时间戳（`int(time.time() * 1000)`）
7. **错误处理**：API 调用失败时展示错误信息，不自动重试，由用户决定下一步

