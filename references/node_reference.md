# Direct 平台节点参考（基于真实 XML 样例）

> 从 1.xml / 2.xml / 3.xml 提取的真实结构。生成 XML 时必须严格遵循此参考。

---

## 一、标签路径格式分类

| 路径模式 | 含义 | 示例 |
|----------|------|------|
| `#(M6.Device1.Direct.xxx)` | Direct 平台内部变量 | `#(M6.Device1.Direct.OVSC_3001)` |
| `#(M6-2.Device1.MOT.MOT_xxx)` | 电机设备位号 | `#(M6-2.Device1.MOT.MOT_P707B_MANON)` |
| `#(M6-2.Device1.PIDA.SCPxxx_OUT)` | PID 控制器输出 | `#(M6-2.Device1.PIDA.SCP0707B_OUT)` |
| `#(M6-2.Device1.VAL.EV_xxx)` | 阀门设备位号 | `#(M6-2.Device1.VAL.EV_0707B_MANON)` |
| `#(M6.DM.DI.xxx)` | 数字量输入（运行/反馈信号） | `#(M6.DM.DI.YL_P0707B)` |
| `#(M6.DM.DM.xxx)` | 数字量测量 | `#(M6.DM.DM.KY1_TX001)` |
| `#(M6.AM.AI.xxx)` | 模拟量输入（压力/温度/流量） | `#(M6.AM.AI.PI_403)` |
| `#(M6.AM.AM.xxx)` | 模拟量测量（振动等） | `#(M6.AM.AM.XI_P0707B_01)` |
| `$(xxx)` | 程序内部变量 | `$(JSQ_001)` |

**后缀约定**：
- `_MANON` → 启动/开（targetValue=1）
- `_MANOF` → 停止/关（targetValue=0）
- `_AUTOOPT` → 置手动（targetValue=0）
- `_OUT` → PID 输出（频率/开度）
- `_MODE` → PID 模式（0=手动）

---

## 二、type 字段值

| 值 | 含义 | 用于 |
|----|------|------|
| `1` | 模拟量（压力/温度/频率/电流） | io:dcs 模拟、flow:and 条件 |
| `3` | 数字量（运行/阀位/状态） | io:dcs 开关、flow:or 条件 |

---

## 三、节点类型详解

### 1. flow:start（开始）

```xml
<flow:start id="Event_xxx">
  <bpmn2:outgoing>Flow_xxx</bpmn2:outgoing>
</flow:start>
```

### 2. flow:end（结束，可有多入边）

```xml
<flow:end id="Event_xxx">
  <bpmn2:incoming>Flow_1</bpmn2:incoming>
  <bpmn2:incoming>Flow_2</bpmn2:incoming>
  <bpmn2:incoming>Flow_3</bpmn2:incoming>
</flow:end>
```

### 3. io:dcs（设备操作）

```xml
<io:dcs id="Activity_xxx" name="启动泵P0707B" tabKey="basic">
  <ext:data><![CDATA[{
    "subTitle": "(底层位号为707B)",
    "showDetail": true,
    "outputMod": "periodic",
    "data": [
      {"name":"#(M6-2.Device1.MOT.MOT_P707B_MANON)","targetValue":"1","lower":0,"tolerance":"0","upper":1000,"deviation":1,"row":0,"type":1},
      {"name":"#(M6-2.Device1.PIDA.SCP0707B_OUT)","targetValue":"15","lower":0,"tolerance":"0","upper":1000,"deviation":1,"row":1784889621585,"type":1}
    ],
    "checkData": [],
    "errorHandler": {"handler":"throw"}
  }]]></ext:data>
  <bpmn2:incoming>Flow_xxx</bpmn2:incoming>
  <bpmn2:outgoing>Flow_xxx</bpmn2:outgoing>
</io:dcs>
```

**字段说明**：
- `subTitle`：副标题，可为空 `""` 或描述文本
- `outputMod`：`"periodic"`（固定）
- `data[]`：操作位号数组
  - `name`：DCS 标签路径
  - `targetValue`：**字符串类型**（如 `"1"`, `"0"`, `"15"`, `"35"`）
  - `lower`/`upper`：上下限（数字）
  - `tolerance`：容差（**字符串**，如 `"0"` 或 `""`）
  - `deviation`：偏差（数字，通常 1）
  - `row`：行号（首项为 0，后续为时间戳数字）
  - `type`：1=模拟量, 3=数字量
- `checkData`：检查数据数组（通常为空 `[]`）
- `errorHandler`：`{"handler":"throw"}`（固定）

### 4. flow:or（条件或，单条件判断）

```xml
<flow:or id="Activity_xxx" name="运行信号反馈" tabKey="basic">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "keep": 0,
    "data": [
      {"name":"#(M6.DM.DI.YL_P0707B)","judge":"==","targetValue":"1","row":0,"type":3}
    ]
  }]]></ext:data>
  <bpmn2:incoming>Flow_xxx</bpmn2:incoming>
  <bpmn2:outgoing>Flow_yes</bpmn2:outgoing>
  <bpmn2:outgoing>Flow_no</bpmn2:outgoing>
</flow:or>
```

**字段说明**：
- `keep`：0（固定）
- `data[]`：条件数组（通常只有 1 项）
  - `judge`：`"=="`, `">="`, `"<="`, `">"`, `"<"`, `"!="`
  - `targetValue`：**字符串类型**
  - `type`：3=数字量判断, 1=模拟量判断
- 出边 2 条：`{"situation":"yes"}` 和 `{"situation":"no"}`

### 5. flow:and（条件与，多条件同时判断）

```xml
<flow:and id="Activity_xxx" name="条件与" tabKey="basic">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "keep": 0,
    "data": [
      {"name":"#(M6.AM.AI.PI_403)","judge":">=","targetValue":"0.4","row":0,"type":1},
      {"name":"#(M6.AM.AM.XI_P0707B_01)","judge":"<=","targetValue":"4.5","row":1784983516538,"type":1}
    ]
  }]]></ext:data>
  <bpmn2:incoming>Flow_xxx</bpmn2:incoming>
  <bpmn2:outgoing>Flow_yes</bpmn2:outgoing>
  <bpmn2:outgoing>Flow_no</bpmn2:outgoing>
</flow:and>
```

**与 flow:or 区别**：多条件 `and` 关系，出边同样是 yes/no。

### 6. flow:branch（多选一分支）

```xml
<flow:branch id="Activity_xxx" name="判断空压机有两台运行信号" tabKey="basic.branch_3">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "keep": 0,
    "branch": [
      {"relation":"and","desc":"A、B有运行信号","data":[
        {"name":"#(M6.DM.DM.KY1_TX001)","judge":"==","targetValue":"1","row":0,"type":3},
        {"name":"#(M6.DM.DM.KY2_TX001)","judge":"==","targetValue":"1","row":1780023350046,"type":3}
      ],"row":0},
      {"relation":"and","desc":"A、C有运行信号","data":[...],"row":1},
      {"relation":"and","desc":"B、C有运行信号","data":[...],"row":2}
    ]
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_0</bpmn2:outgoing>
  <bpmn2:outgoing>Flow_1</bpmn2:outgoing>
  <bpmn2:outgoing>Flow_2</bpmn2:outgoing>
</flow:branch>
```

**字段说明**：
- `tabKey`：`"basic.branch_N"`（N=分支数）
- `branch[]`：分支数组
  - `relation`：`"and"`（分支内条件关系）
  - `desc`：分支描述
  - `data[]`：条件数组
  - `row`：分支序号（0, 1, 2...）
- 出边 N 条：`{"situation":"0"}`, `{"situation":"1"}`, ..., `{"situation":"N-1"}`

### 7. timer:start（开始计时器）

```xml
<timer:start id="Activity_xxx" name="开始计时器">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "timer": "$(JSQ_001)"
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</timer:start>
```

### 8. timer:cond（计时器判断，超时分支）

```xml
<timer:cond id="Activity_xxx" name="计时器判断">
  <ext:data><![CDATA[{
    "subTitle": "",
    "version": 1,
    "showDetail": true,
    "timer": "$(JSQ_001)",
    "type": "specifiedTime",
    "integerTime": 10,
    "specifiedTime": "00:05:00"
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_yes</bpmn2:outgoing>
</timer:cond>
```

**字段说明**：
- `timer`：引用 `timer:start` 中定义的变量
- `type`：`"specifiedTime"`（固定）
- `integerTime`：秒数（数字）
- `specifiedTime`：`"HH:MM:SS"` 格式

### 9. timer:wait（等待）

```xml
<timer:wait id="Activity_xxx" name="等待">
  <ext:data><![CDATA[{
    "subTitle": "",
    "version": 1,
    "showDetail": true,
    "type": "specifiedTime",
    "integerTime": 10,
    "specifiedTime": "00:00:03"
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</timer:wait>
```

### 10. msg:confirm（确认消息，暂停等待）

```xml
<msg:confirm id="Activity_xxx" name="确认消息" tabKey="basic">
  <ext:data><![CDATA[{
    "set": [{"upper":100,"lower":0,"targetVar":"","row":1784983651841}],
    "showDetail": true,
    "isMute": false,
    "data": [],
    "select": [],
    "labelIds": [],
    "subTitle": "",
    "message": "除盐水泵开车异常，请确认",
    "type": "only",
    "display": "yes",
    "resourceGroupId": "0",
    "needPhoto": false,
    "needPublish": true,
    "needHandWritting": false,
    "partialConfirmLevel": 0,
    "messageLevel": 0,
    "isSelectFile": false,
    "filePath": "",
    "version": "1"
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</msg:confirm>
```

**关键字段**：
- `message`：提示文本
- `type`：`"only"`（仅确认）或其他类型
- `display`：`"yes"`（显示）
- `needPhoto`/`needPublish`/`needHandWritting`：布尔值
- `version`：`"1"`（字符串）

### 11. msg:guide（引导消息，不暂停）

```xml
<msg:guide id="Activity_xxx" name="引导消息" tabKey="basic">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "message": "循环水系统停车结束",
    "display": "yes",
    "version": "1"
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</msg:guide>
```

### 12. flow:parallel1（并行容器）

```xml
<flow:parallel1 id="Activity_xxx">
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
  <flow:parallelStart id="Activity_start">
    <bpmn2:outgoing>Flow_branch1</bpmn2:outgoing>
    <bpmn2:outgoing>Flow_branch2</bpmn2:outgoing>
    <bpmn2:outgoing>Flow_branch3</bpmn2:outgoing>
  </flow:parallelStart>
  <flow:parallelEnd id="Activity_end">
    <bpmn2:incoming>Flow_branch1_end</bpmn2:incoming>
    <bpmn2:incoming>Flow_branch2_end</bpmn2:incoming>
    <bpmn2:incoming>Flow_branch3_end</bpmn2:incoming>
  </flow:parallelEnd>
  <!-- 分支节点放在 parallelStart 和 parallelEnd 之间 -->
  <io:dcs id="Activity_branch1_node">...</io:dcs>
  <io:dcs id="Activity_branch2_node">...</io:dcs>
  <io:dcs id="Activity_branch3_node">...</io:dcs>
  <!-- 分支连线 -->
  <bpmn2:sequenceFlow id="Flow_branch1" sourceRef="Activity_start" targetRef="Activity_branch1_node" />
  <bpmn2:sequenceFlow id="Flow_branch1_end" sourceRef="Activity_branch1_node" targetRef="Activity_end" />
  ...
</flow:parallel1>
```

**结构**：parallelStart → N 分支 → parallelEnd。分支节点和连线都在 parallel1 内部。

### 13. util:text（文本注释）

```xml
<util:text id="Text_xxx" desc="备注&#10;1、增加空压机A/B/C压力及温度故障检查状态">
  <ext:data><![CDATA[{
    "fontSize": 14,
    "fontWeight": "normal",
    "color": "#d0021b"
  }]]></ext:data>
</util:text>
```

**用途**：在流程图中添加红色备注文本。`desc` 属性存放文本内容，`&#10;` 为换行符。

---

## 四、连线 (sequenceFlow) 规则

### 4.1 普通连线（无条件）

```xml
<bpmn2:sequenceFlow id="Flow_xxx" sourceRef="Activity_A" targetRef="Activity_B" />
```

无 `name` 属性，无 `ext:data`。

### 4.2 条件连线（yes/no）

```xml
<bpmn2:sequenceFlow id="Flow_xxx" name="是" sourceRef="Activity_or" targetRef="Activity_B">
  <ext:data><![CDATA[{"situation":"yes"}]]></ext:data>
</bpmn2:sequenceFlow>
```

- `name`：`"是"` 或 `"否"`
- `ext:data`：`{"situation":"yes"}` 或 `{"situation":"no"}`
- **注意**：不要包含 `lineType` 字段

### 4.3 分支连线（多选一）

```xml
<bpmn2:sequenceFlow id="Flow_xxx" name="A、B有运行信号" sourceRef="Activity_branch" targetRef="Activity_B">
  <ext:data><![CDATA[{"situation":"0"}]]></ext:data>
</bpmn2:sequenceFlow>
```

- `name`：分支描述文本
- `ext:data`：`{"situation":"0"}`, `{"situation":"1"}`, ... `{"situation":"N-1"}`

### 4.4 连线 ext:data 汇总

| 场景 | ext:data |
|------|----------|
| 普通连线 | 无 ext:data |
| 条件为真 | `{"situation":"yes"}` |
| 条件为否 | `{"situation":"no"}` |
| 分支 0 | `{"situation":"0"}` |
| 分支 1 | `{"situation":"1"}` |
| 分支 N | `{"situation":"N"}` |

---

## 五、节点选择规则

| SOP 描述 | 节点类型 | type | 判断 |
|----------|----------|------|------|
| 启动/停止/开关阀门 | io:dcs | 3 | - |
| 设变频频率/设开度 | io:dcs | 1 | - |
| 置手动模式 | io:dcs | 1 | - |
| 判断运行信号=1 | flow:or | 3 | `==` |
| 判断阀位反馈=1 | flow:or | 3 | `==` |
| 压力≥X 且 振动≤Y | flow:and | 1 | `>=` `<=` |
| 流量≥X 且 振动≤Y | flow:and | 1 | `>=` `<=` |
| 3台泵中选2台运行 | flow:branch | 3 | `==` |
| 等待N秒 | timer:wait | - | - |
| 开始计时 | timer:start | - | - |
| 超时判断 | timer:cond | - | - |
| 弹窗确认（暂停） | msg:confirm | - | - |
| 仅提示（不暂停） | msg:guide | - | - |
| 多设备同时操作 | flow:parallel1 | - | - |
| 添加备注 | util:text | - | - |

---

## 六、BPMN Diagram 坐标规则

### 6.1 元素顺序

**BPMNPlane 中 BPMNShape 在前、BPMNEdge 在后**（严格按照 `references/xml_template.xml` 模板格式）：

```xml
<bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
  <!-- 1. 先输出所有 BPMNShape -->
  <bpmndi:BPMNShape id="Event_start_di" bpmnElement="Event_start">...</bpmndi:BPMNShape>
  <bpmndi:BPMNShape id="Activity_1_di" bpmnElement="Activity_1">...</bpmndi:BPMNShape>
  <!-- 2. 再输出所有 BPMNEdge -->
  <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">...</bpmndi:BPMNEdge>
  <bpmndi:BPMNEdge id="Flow_2_di" bpmnElement="Flow_2">...</bpmndi:BPMNEdge>
</bpmndi:BPMNPlane>
```

### 6.2 BPMNShape（每个节点对应一条 Shape）

**基本格式**：
```xml
<bpmndi:BPMNShape id="Event_start_di" bpmnElement="Event_start">
  <dc:Bounds x="500" y="60" width="54" height="54" />
</bpmndi:BPMNShape>
```

**Shape id 格式**：`{node_id}_di`（如 `Event_start_di`）

### 6.3 BPMNEdge（每条 sequenceFlow 对应一条 Edge）

**格式（严格按模板）**：
```xml
<bpmndi:BPMNEdge id="Flow_xxx_di" bpmnElement="Flow_xxx">
  <di:waypoint x="600" y="120" />
  <di:waypoint x="600" y="160" />
</bpmndi:BPMNEdge>
```

**Edge id 格式**：`{flow_id}_di`（如 `Flow_1_di`）

**waypoint 规则**：
- 起点：源节点底部中心 (x+width/2, y+height)
- 终点：目标节点顶部中心 (x+width/2, y)
- 直连：2 个 waypoint
- L 形：3 个 waypoint（中点转折）

### 6.4 ID 匹配规则（关键！）

**节点 ID 匹配**：
- 节点定义中的 `id`（如 `Event_start`）必须与 BPMNShape 的 `bpmnElement` 完全一致
- 例：`<flow:start id="Event_start">` ↔ `<bpmndi:BPMNShape bpmnElement="Event_start">`

**连线 ID 匹配**：
- sequenceFlow 的 `id`（如 `Flow_01`）必须与 BPMNEdge 的 `bpmnElement` 完全一致
- 例：`<bpmn2:sequenceFlow id="Flow_01">` ↔ `<bpmndi:BPMNEdge bpmnElement="Flow_01">`
- **ID 不匹配 = 连线不显示**（最常见 bug）

### 6.5 坐标规则

- 垂直间距：100px
- 水平间距：300px
- 元件不允许重叠
- 连线不得穿过节点矩形
- 使用 `scripts/layout_generator.py` 自动生成

---

## 七、完整 XML 模板

**严格遵循以下格式，禁止任何额外的包装层：**
- 禁止 `<?xml version="1.0"?>` 声明
- 禁止 `<bpmn2:definitions>` 根元素
- 禁止 `xmlns` 命名空间声明
- 禁止任何模板中不存在的元素
- 直接以 `<bpmn2:process>` 开头，以 `</bpmndi:BPMNDiagram>` 结尾

此内容存入 API 的 `sfcRunning.value` 字段。

```xml
<bpmn2:process id="Process_1" isExecutable="true">
  <!-- 节点定义 -->
  <flow:start id="Event_start">
    <bpmn2:outgoing>Flow_1</bpmn2:outgoing>
  </flow:start>
  <io:dcs id="Activity_1" name="操作名称" tabKey="basic">
    <ext:data><![CDATA[...]]></ext:data>
    <bpmn2:incoming>Flow_1</bpmn2:incoming>
    <bpmn2:outgoing>Flow_2</bpmn2:outgoing>
  </io:dcs>
  <flow:end id="Event_end">
    <bpmn2:incoming>Flow_2</bpmn2:incoming>
  </flow:end>
  <!-- 连线定义 -->
  <bpmn2:sequenceFlow id="Flow_1" sourceRef="Event_start" targetRef="Activity_1" />
  <bpmn2:sequenceFlow id="Flow_2" sourceRef="Activity_1" targetRef="Event_end" />
</bpmn2:process>
<bpmndi:BPMNDiagram id="BPMNDiagram_1">
  <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
    <bpmndi:BPMNShape id="Event_start_di" bpmnElement="Event_start">
      <dc:Bounds x="500" y="60" width="54" height="54" />
    </bpmndi:BPMNShape>
    <bpmndi:BPMNShape id="Activity_1_di" bpmnElement="Activity_1">
      <dc:Bounds x="427" y="154" width="200" height="60" />
    </bpmndi:BPMNShape>
    <bpmndi:BPMNShape id="Event_end_di" bpmnElement="Event_end">
      <dc:Bounds x="500" y="254" width="54" height="54" />
    </bpmndi:BPMNShape>
    <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
      <di:waypoint x="527" y="114" />
      <di:waypoint x="527" y="154" />
    </bpmndi:BPMNEdge>
    <bpmndi:BPMNEdge id="Flow_2_di" bpmnElement="Flow_2">
      <di:waypoint x="527" y="214" />
      <di:waypoint x="527" y="254" />
    </bpmndi:BPMNEdge>
  </bpmndi:BPMNPlane>
</bpmndi:BPMNDiagram>
```
