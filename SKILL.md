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
Step 1: 解析文档 → Step 2: 创建程序 → Step 3: 生成XML → Step 4: 保存程序 → Step 5: 编译程序
```

- Step 1 未完成不得执行 Step 2

- Step 2 未完成（用户未确认）不得执行 Step 3

- Step 3 未完成不得执行 Step 4

- Step 4 未完成不得执行 Step 5

### Step 1: 解析文档（含缺失信息交互）

**目标**：从 SOP 文档中提取所有结构化信息。

SOP 文档没有标准格式，需要灵活解析。采用 **AI 语义理解 + Python 脚本辅助** 双重策略：

#### 1.1 读取文档内容

根据文件类型选择读取方式：

- `.docx`：使用 `python-docx` 库提取段落和表格

- `.pdf`：使用 `PyPDF2` 或 `pdfplumber` 提取文本和表格

- `.txt` / `.md`：直接读取文本

Python 辅助解析脚本示例：

```python
# 标准库导入
import sys

# 第三方库导入
from docx import Document

def extract_docx(path: str) -> dict:
    """提取 docx 中的段落和表格"""
    doc = Document(path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    tables = []
    for table in doc.tables:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)
        tables.append(rows)
    return {"paragraphs": paragraphs, "tables": tables}
```

#### 1.2 提取的信息维度

从 SOP 文档中提取以下 **五大信息维度**：

| 维度        | 说明              | 示例                                       |
| --------- | --------------- | ---------------------------------------- |
| **阶段划分**  | SOP 的工序/阶段/步骤编号 | "一、准备工作" → "二、开车操作" → "三、停车操作"           |
| **操作步骤**  | 每步的具体操作动作和参数    | "打开反应釜R-01进料阀，设定流量50kg/h"                |
| **设备/管路** | 涉及的设备名称和位号      | "反应釜R-01"、"循环水泵P0801A"、"出口开关阀EV\_0801A2" |
| **参数值**   | 温度/压力/流量/时间等设定值 | "温度设定80℃"、"搅拌转速60rpm"、"反应时间30min"        |
| **安全/联锁** | 安全阈值、报警条件、联锁逻辑  | "压力超过0.5MPa时触发联锁停车"                      |

#### 1.3 结构化中间表示

将提取的信息组织为以下 JSON 结构（中间表示）：

```json
{
  "program_name": "从 SOP 标题提取",
  "description": "从 SOP 概述提取",
  "version": "v1.0",
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
```

#### 1.4 缺失信息交互（解析过程中触发）

**目标**：当 SOP 中缺少信息时，与用户交互补充。

##### 1.4.1 交互触发条件（四类场景）

1. **设备位号匹配确认**：SOP 中设备只有名称（如"反应釜R-01"），缺少 Direct 平台位号（如 `M6-2.Device1.MOT.P0801A_MANON`）

   - 向用户展示设备名称，请用户提供或确认对应的位号

   - 如 SOP 中已有位号（如 `P0801A`），尝试自动推导标签格式并请用户确认

2. **参数值缺失补充**：SOP 描述了操作但缺少具体参数值（如"加热至适当温度"）

   - 向用户展示缺失参数的上下文，请用户提供具体数值

3. **安全阈值补充**：SOP 描述了安全要求但未给具体阈值（如"压力过高时报警"）

   - 向用户展示安全要求描述，请提供具体阈值和联锁动作

4. **模糊描述澄清**：SOP 描述有歧义（如"适当加热"、"缓慢开启"）

   - 向用户展示原文，请澄清为可量化参数

##### 1.4.2 交互方式

- 使用 `AskUserQuestion` 工具，每次提问不超过 4 个问题

- 每个问题提供合理的选项（基于 SOP 上下文推断）

- 始终提供"我来手动填写"选项

- 问题使用中文

### Step 2: 生成主程序（API 调用）

**目标**：调用 Direct 平台 API 创建主程序，获取 appid。

解析完成并补全信息后，**先调用 API 创建主程序**，获取 appid 供后续保存和编译使用。

#### 2.1 API 配置

```python
BASE_URL = "http://direct-proxy/"
AUTH_TOKEN = ""
REQUEST_TIMEOUT = 60
HEADERS = {
    "Accept-Language": "zh-CN",
    "Authorization": AUTH_TOKEN,
    "Content-Type": "application/json",
}
```

#### 2.2 创建主程序 (create\_program)

**创建前必须与用户交互，用户同意后才可创建，严格按流程执行，不得跳过**：

使用 AskUserQuestion 向用户展示以下字段（AI 根据 SOP 文档自动填充建议值，用户可修改）：

| 字段                  | 说明       | 命名规则                      | 示例                         |
| ------------------- | -------- | ------------------------- | -------------------------- |
| 程序名称(program\_name) | 主程序名称    | 仅支持字母、数字、下划线，必须字母开头，不允许中文 | sop\_shutdown\_circ\_water |
| 描述                  | 程序功能描述   | 无限制                       | 循环水系统停车流程程序                |
| 被指                  | 指派对象/负责人 | 无限制                       | 张三                         |
| 版本                  | 程序版本号    | 无限制                       | 1.0                        |
| 分组                  | 程序分组/分类  | 无限制                       | 停车程序                       |

**program\_name 校验规则**：

- 仅允许：字母（a-z, A-Z）、数字（0-9）、下划线（\_）

- 必须以字母开头

- 不允许：中文、空格、特殊符号、数字开头

- AI 生成建议值时自动遵守此规则（如 SOP 标题"循环水停车"→ `circ_water_shutdown`）

- 用户修改时也必须校验，不符合规则时提示用户重新输入

**流程**：展示建议值 → 用户确认或修改 → 用户明确同意后才调用 API。用户未同意前禁止调用 create\_program。

```python
import requests

def create_program(name: str, description: str = "", assignee: str = "", version: str = "1.0", group: str = "") -> str:
    """创建主程序，返回 appid"""
    url = f"{BASE_URL}/api/model/app/create"
    payload = {
        "name": name,
        "description": description,
        "assignee": assignee,
        "version": version,
        "group": group
    }
    resp = requests.post(url, json=payload, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 200:
        raise RuntimeError(f"创建失败: {data}")
    return data["data"]["appid"]
```

**调用时机**：文档解析 + 缺失信息交互完成后，生成 XML 之前调用。**必须等用户确认程序信息后才可调用。**

### Step 3: 生成 BPMN XML

**目标**：根据结构化中间表示，生成符合 Direct 平台格式的 BPMN XML。

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
| 引用主程序        | `<flow:otherMainProc>` | 引用已生效主程序             |
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

动作后缀规律：

- `_MANON` — 手动开

- `_MANOF` — 手动关

- `_AUTOOPT` — 自动优化

#### 3.4 连线规则（关键修正）

sequenceFlow 的 ext:data 格式**取决于源节点类型**，situation 连线**不能包含 lineType**：

| 源节点类型                                                                                                                                                                                             | 连线变体               | name 属性        | ext:data               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | -------------- | ---------------------- |
| flow:start, flow:end, flow:risingEdge, flow:fallingEdge, flow:otherMainProc, flow:request, io:*, timer:wait, timer:start, timer:restart, timer:stop, timer:pause, timer:clock, msg:*（含 msg:alarm） | **plain**          | 无              | `{"lineType":1}`       |
| flow:and, flow:or, timer:cond 的"是"分支                                                                                                                                                              | **situation\_yes** | `name="条件成立"`  | `{"situation":"yes"}`  |
| flow:and, flow:or, timer:cond 的"否"分支                                                                                                                                                              | **situation\_no**  | `name="条件不成立"` | `{"situation":"no"}`   |
| flow:branch 的每个分支                                                                                                                                                                                 | **branch\_option** | `name="{选项名}"` | `{"situation":"{索引}"}` |

**约束**：

- `situation_yes/no` 的 ext:data **只含** **`situation`** **字段，禁止包含** **`lineType`**

- 条件判断节点（flow:and, flow:or, timer:cond）**必须有两条 outgoing**（yes + no）

- 非条件节点的 outgoing 使用 **plain** 格式

- 每条 sequenceFlow 必须有对应的 BPMNEdge（含 di:waypoint 坐标）

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
| flow:otherMainProc / flow:request                                           | 200×60      |
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

#### 4.1 保存程序 (save\_program)

**接口**：`POST {BASE_URL}/vxdirect/procedure/all`

请求体：

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
        "sfcRunning": {"value": "<BPMN_XML字符串>"},
        "sfcPausing": {"value": ""},
        "sfcResuming": {"value": ""},
        "sfcStopping": {"value": ""}
      },
      "description": {"value": "程序描述"},
      "id": "appid",
      "deviceId": "0",
      "parentId": "0",
      "rootId": "appid",
      "name": "程序名称",
      "resourceGroupId": "0",
      "customOrder": 1,
      "branchSignPathId": "0",
      "formulaGroupId": "0",
      "schedulePeriod": 1000
    }
  ],
  "deleteProcedureIds": "",
  "rootId": "appid"
}
```

**关键**：`sfcRunning.value` 存放 Step 3 生成的完整 BPMN XML 字符串。`id` 和 `rootId` 使用 Step 2 返回的 appid。

#### 4.2 API 客户端参考代码

完整的 API 客户端实现详见 `scripts/api_reference.py` 文件。

### Step 5: 编译（API 调用）

**目标**：编译已保存的程序，验证流程逻辑正确性。

#### 5.1 编译程序 (compile\_program)

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

- **严格限制：禁止创建任何新程序（包括测试程序）** — 只允许在本次已创建的程序（同一 appid）上修正 XML，重新 save\_program → compile\_program

- create\_program 在整个流程中只允许调用一次

**重试时核心约束（必须遵守）**：

- **禁止减少元件** — 不得删除任何节点

- **禁止修改结构** — 不得删除连线、不得改变节点间连接关系、不得改变流程逻辑

- **必须按照用户在 Step 3.7 确认的流程结构进行保存与编译** — 节点数量、连线数量、连接关系必须与用户确认时完全一致

- 仅允许修正数据层面的错误：位号补全、参数值修正、XML 格式修复、ID 不匹配修复

**最大重试 3 次**，每次重试前：

1. 分析编译错误原因
2. **缺数据/参数**（如位号缺失、参数值为空）→ 使用 AskUserQuestion 与用户交互补充
3. **不缺数据**（如 XML 格式错误、ID 不匹配等）→ 自行修复，不打扰用户
4. 修正后重新 save\_program → compile\_program

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
  │    ├─ 构建结构化中间表示 (JSON)
  │    └─ 检查缺失信息
  │         ├─ 设备位号缺失? → 交互确认
  │         ├─ 参数值缺失? → 交互补充
  │         ├─ 安全阈值缺失? → 交互补充
  │         └─ 描述模糊? → 交互澄清
  │
  ├─ Step 2: 生成主程序 (API)
  │    └─ create_program → 返回 appid
  │
  ├─ Step 3: 生成 BPMN XML
  │    ├─ 映射节点类型
  │    ├─ 生成 ext:data JSON
  │    ├─ 生成 sequenceFlow 连线
  │    └─ 生成 BPMNDiagram 坐标（使用 layout_generator.py）
  │
  ├─ Step 4: 保存 (API)
  │    └─ save_program → 将 XML 保存到 appid
  │
  ├─ Step 5: 编译 (API)
  │    └─ compile_program → 编译验证
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

