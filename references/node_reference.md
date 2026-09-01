# Direct 平台节点参考（基于真实 XML 样例）

生成 XML 时必须严格遵循此参考。

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

### 12. flow:parallel1（并行容器，竖向）

**结构**：`parallelStart → N 分支 → parallelEnd`。分支节点和连线都在 parallel1 内部。

**连线关系**：
- 外部节点 → `flow:parallel1`（容器 incoming）
- `parallelStart` → 各分支首节点（N 条 outgoing）
- 各分支内部节点间连线
- 各分支末节点 → `parallelEnd`（N 条 incoming）
- `flow:parallel1` → 外部节点（容器 outgoing）

#### 12.1 Process XML（以 2 分支为例）

```xml
<!-- 外部节点（容器前） -->
<io:dcs id="Activity_prev" name="前序操作" tabKey="basic">
  <ext:data><![CDATA[{"subTitle":"","showDetail":true,"outputMod":"periodic","data":[{"name":"#(M6-2.Device1.MOT.MOT_P707A_MANON)","targetValue":"1","lower":0,"tolerance":"0","upper":1000,"deviation":1,"row":0,"type":1}],"checkData":[],"errorHandler":{"handler":"throw"}}]]></ext:data>
  <bpmn2:incoming>Flow_prev_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_to_parallel</bpmn2:outgoing>
</io:dcs>

<!-- 并行容器 -->
<flow:parallel1 id="Activity_par1" layout="vertical">
  <bpmn2:incoming>Flow_to_parallel</bpmn2:incoming>
  <bpmn2:outgoing>Flow_from_parallel</bpmn2:outgoing>
  <flow:parallelStart id="Activity_par1_start">
    <bpmn2:outgoing>Flow_branch_a</bpmn2:outgoing>
    <bpmn2:outgoing>Flow_branch_b</bpmn2:outgoing>
  </flow:parallelStart>
  <flow:parallelEnd id="Activity_par1_end">
    <bpmn2:incoming>Flow_branch_a_end</bpmn2:incoming>
    <bpmn2:incoming>Flow_branch_b_end</bpmn2:incoming>
  </flow:parallelEnd>
  <!-- 分支 A 节点 -->
  <io:dcs id="Activity_pump_a" name="启动泵A" tabKey="basic">
    <ext:data><![CDATA[{"subTitle":"","showDetail":true,"outputMod":"periodic","data":[{"name":"#(M6-2.Device1.MOT.MOT_P707A_MANON)","targetValue":"1","lower":0,"tolerance":"0","upper":1000,"deviation":1,"row":0,"type":1}],"checkData":[],"errorHandler":{"handler":"throw"}}]]></ext:data>
    <bpmn2:incoming>Flow_branch_a</bpmn2:incoming>
    <bpmn2:outgoing>Flow_branch_a_end</bpmn2:outgoing>
  </io:dcs>
  <!-- 分支 B 节点 -->
  <io:dcs id="Activity_pump_b" name="启动泵B" tabKey="basic">
    <ext:data><![CDATA[{"subTitle":"","showDetail":true,"outputMod":"periodic","data":[{"name":"#(M6-2.Device1.MOT.MOT_P707B_MANON)","targetValue":"1","lower":0,"tolerance":"0","upper":1000,"deviation":1,"row":0,"type":1}],"checkData":[],"errorHandler":{"handler":"throw"}}]]></ext:data>
    <bpmn2:incoming>Flow_branch_b</bpmn2:incoming>
    <bpmn2:outgoing>Flow_branch_b_end</bpmn2:outgoing>
  </io:dcs>
</flow:parallel1>

<!-- 外部节点（容器后） -->
<io:dcs id="Activity_next" name="后续操作" tabKey="basic">
  <ext:data><![CDATA[{"subTitle":"","showDetail":true,"outputMod":"periodic","data":[{"name":"#(M6-2.Device1.VAL.EV_0707A_MANON)","targetValue":"1","lower":0,"tolerance":"0","upper":1000,"deviation":1,"row":0,"type":1}],"checkData":[],"errorHandler":{"handler":"throw"}}]]></ext:data>
  <bpmn2:incoming>Flow_from_parallel</bpmn2:incoming>
  <bpmn2:outgoing>Flow_next_out</bpmn2:outgoing>
</io:dcs>

<!-- 连线 -->
<!-- 外部 → 容器 -->
<bpmn2:sequenceFlow id="Flow_to_parallel" sourceRef="Activity_prev" targetRef="Activity_par1" />
<!-- parallelStart → 分支首节点 -->
<bpmn2:sequenceFlow id="Flow_branch_a" sourceRef="Activity_par1_start" targetRef="Activity_pump_a" />
<bpmn2:sequenceFlow id="Flow_branch_b" sourceRef="Activity_par1_start" targetRef="Activity_pump_b" />
<!-- 分支末节点 → parallelEnd -->
<bpmn2:sequenceFlow id="Flow_branch_a_end" sourceRef="Activity_pump_a" targetRef="Activity_par1_end" />
<bpmn2:sequenceFlow id="Flow_branch_b_end" sourceRef="Activity_pump_b" targetRef="Activity_par1_end" />
<!-- 容器 → 外部 -->
<bpmn2:sequenceFlow id="Flow_from_parallel" sourceRef="Activity_par1" targetRef="Activity_next" />
```

#### 12.2 BPMNDiagram XML（对应上方 Process）

```xml
<bpmndi:BPMNDiagram id="BPMNDiagram_1">
  <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
    <!-- ── BPMNShape（先节点后连线）── -->
    <!-- 前序节点 -->
    <bpmndi:BPMNShape id="Activity_prev_di" bpmnElement="Activity_prev">
      <dc:Bounds x="400" y="60" width="200" height="60" />
    </bpmndi:BPMNShape>
    <!-- 并行容器（isExpanded="true" 必须设置） -->
    <bpmndi:BPMNShape id="Activity_par1_di" bpmnElement="Activity_par1" isExpanded="true">
      <dc:Bounds x="60" y="195" width="780" height="230" />
    </bpmndi:BPMNShape>
    <!-- parallelStart（横条，宽=容器内宽，高=5） -->
    <bpmndi:BPMNShape id="Activity_par1_start_di" bpmnElement="Activity_par1_start">
      <dc:Bounds x="100" y="235" width="700" height="5" />
    </bpmndi:BPMNShape>
    <!-- 分支 A 节点 -->
    <bpmndi:BPMNShape id="Activity_pump_a_di" bpmnElement="Activity_pump_a">
      <dc:Bounds x="100" y="280" width="200" height="60" />
    </bpmndi:BPMNShape>
    <!-- 分支 B 节点 -->
    <bpmndi:BPMNShape id="Activity_pump_b_di" bpmnElement="Activity_pump_b">
      <dc:Bounds x="600" y="280" width="200" height="60" />
    </bpmndi:BPMNShape>
    <!-- parallelEnd（横条，宽=容器内宽，高=5） -->
    <bpmndi:BPMNShape id="Activity_par1_end_di" bpmnElement="Activity_par1_end">
      <dc:Bounds x="100" y="380" width="700" height="5" />
    </bpmndi:BPMNShape>
    <!-- 后续节点 -->
    <bpmndi:BPMNShape id="Activity_next_di" bpmnElement="Activity_next">
      <dc:Bounds x="400" y="480" width="200" height="60" />
    </bpmndi:BPMNShape>

    <!-- ── BPMNEdge（每条 sequenceFlow 一条 Edge）── -->
    <!-- 外部 → 容器（情况5 incoming） -->
    <bpmndi:BPMNEdge id="Flow_to_parallel_di" bpmnElement="Flow_to_parallel">
      <di:waypoint x="500" y="120" />
      <di:waypoint x="500" y="145" />
      <di:waypoint x="450" y="145" />
      <di:waypoint x="450" y="235" />
    </bpmndi:BPMNEdge>
    <!-- parallelStart → 分支 A（情况3） -->
    <bpmndi:BPMNEdge id="Flow_branch_a_di" bpmnElement="Flow_branch_a">
      <di:waypoint x="200" y="240" />
      <di:waypoint x="200" y="280" />
    </bpmndi:BPMNEdge>
    <!-- parallelStart → 分支 B（情况3） -->
    <bpmndi:BPMNEdge id="Flow_branch_b_di" bpmnElement="Flow_branch_b">
      <di:waypoint x="700" y="240" />
      <di:waypoint x="700" y="280" />
    </bpmndi:BPMNEdge>
    <!-- 分支 A → parallelEnd（情况4） -->
    <bpmndi:BPMNEdge id="Flow_branch_a_end_di" bpmnElement="Flow_branch_a_end">
      <di:waypoint x="200" y="340" />
      <di:waypoint x="200" y="380" />
    </bpmndi:BPMNEdge>
    <!-- 分支 B → parallelEnd（情况4） -->
    <bpmndi:BPMNEdge id="Flow_branch_b_end_di" bpmnElement="Flow_branch_b_end">
      <di:waypoint x="700" y="340" />
      <di:waypoint x="700" y="380" />
    </bpmndi:BPMNEdge>
    <!-- 容器 → 外部（情况5 outgoing） -->
    <bpmndi:BPMNEdge id="Flow_from_parallel_di" bpmnElement="Flow_from_parallel">
      <di:waypoint x="450" y="385" />
      <di:waypoint x="450" y="475" />
      <di:waypoint x="500" y="475" />
      <di:waypoint x="500" y="480" />
    </bpmndi:BPMNEdge>
  </bpmndi:BPMNPlane>
</bpmndi:BPMNDiagram>
```

#### 12.3 坐标规则要点

| 元件 | 定位规则 |
|------|----------|
| `flow:parallel1` 容器 | 包围所有子节点，四周 padding ≥ 40px |
| `parallelStart` | 容器顶部内 padding 后，横条（宽=容器内宽，高=5） |
| `parallelEnd` | 容器底部内 padding 前，横条（宽=容器内宽，高=5） |
| 分支节点 | 在 pstart 和 pend 之间，分支间水平间距 ≥ 300px |
| 外部→容器连线 | 从外部底部→容器上方弯折→pstart 顶部 |
| pstart→分支连线 | 从 pstart 底部对齐到分支 x 中心→分支顶部 |
| 分支→pend 连线 | 从分支底部→对齐到 pend 顶部 |
| 容器→外部连线 | 从 pend 底部→穿出容器边界→弯折→外部顶部 |

> 使用 `layout_parallel1()` 自动生成以上所有坐标，无需手动计算。

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

### 14. flow:risingEdge（上跳变）

```xml
<flow:risingEdge id="Activity_xxx" name="上跳变">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "keep": 0,
    "relation": "and",
    "data": [
      {"name":"#(HIC_V1001A_1.AOF)","desc":"","row":0,"type":3}
    ]
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</flow:risingEdge>
```

**字段说明**：
- `keep`：0（固定）
- `relation`：`"and"`（多条件关系）
- `data[]`：检测位号数组
  - `name`：位号路径 `#(xxx)`
  - `desc`：描述（可空）
  - `type`：3=数字量
- 出边 1 条：plain 连线

### 15. flow:fallingEdge（下跳变）

```xml
<flow:fallingEdge id="Activity_xxx" name="下跳变">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "keep": 0,
    "relation": "and",
    "data": [
      {"name":"#(HIC_V1001A_1.AOF)","desc":"","row":0,"type":3}
    ]
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</flow:fallingEdge>
```

**与 flow:risingEdge 区别**：检测信号从非0→0的下跳变。字段结构完全相同。

### 16. io:concat（字符串操作）

```xml
<io:concat id="Activity_xxx" name="字符串操作">
  <ext:data><![CDATA[{
    "subTitle": "",
    "version": 1,
    "showDetail": true,
    "data": [
      {"targetVar":"$$$(YF_ST13)","express":[{"value":"$$$(KC_GY)"}]}
    ]
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</io:concat>
```

**字段说明**：
- `version`：1（固定）
- `data[]`：拼接数组
  - `targetVar`：目标变量 `$$$(XXX)`
  - `express[]`：拼接值数组，每项 `{"value":"xxx"}`
- 出边 1 条：plain 连线

### 17. io:fileExport（文件导出）

```xml
<io:fileExport id="Activity_xxx" name="文件导出">
  <ext:data><![CDATA[{
    "version": "1",
    "showDetail": true,
    "fileFormat": "csv",
    "path": "22.csv",
    "data": [
      {"col":"SS","rowNumber":"1","value":"$(dy)","row":0}
    ]
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</io:fileExport>
```

**字段说明**：
- `fileFormat`：`"csv"` 或 `"xlsx"`
- `path`：文件路径
- `data[]`：导出数据数组
  - `col`：列标识
  - `rowNumber`：行号
  - `value`：变量引用 `$(XXX)`
- 出边 1 条：plain 连线

### 18. io:fileImport（文件导入）

```xml
<io:fileImport id="Activity_xxx" name="文件导入">
  <ext:data><![CDATA[{
    "version": "1",
    "showDetail": true,
    "fileFormat": "csv",
    "path": "1.csv",
    "data": [
      {"col":"","rowNumber":"","value":"$(dy)","row":0}
    ]
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</io:fileImport>
```

**与 io:fileExport 区别**：从文件读取数据到变量。字段结构相同，`value` 为接收导入值的变量引用。

### 19. io:modifyLabel（修改标签）

```xml
<io:modifyLabel id="Activity_xxx" name="修改标签">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "data": [
      {"desc":"修改标签","currentLabelId":"0","targetLabelId":"0"}
    ],
    "errorHandler": {"handler":0}
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</io:modifyLabel>
```

**字段说明**：
- `data[]`：标签修改数组
  - `desc`：修改描述
  - `currentLabelId`：当前标签ID
  - `targetLabelId`：目标标签ID
- `errorHandler`：`{"handler":0}`

### 20. io:modifyProps（修改属性）

```xml
<io:modifyProps id="Activity_xxx" name="修改属性">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "customField": "$(dy)"
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</io:modifyProps>
```

**字段说明**：
- `customField`：自定义字段值，变量引用 `$(XXX)`

### 21. flow:otherMainProc（引用主程序）

```xml
<flow:otherMainProc id="Activity_xxx" name="BXCS_copy" subId="1343271715200010000">
  <ext:data><![CDATA[{
    "subTitle": "",
    "subTitle2": "",
    "showDetail": true,
    "mainProcedure": "BXCS[V1.1]",
    "showQueue": false,
    "interval": 0,
    "trends": []
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</flow:otherMainProc>
```

**字段说明**：
- `subId`（属性）：子程序ID
- `mainProcedure`：主程序名称[版本]，如 `"BXCS[V1.1]"`
- `showQueue`：是否显示队列
- `interval`：间隔（0=默认）
- `trends`：趋势数据数组（通常为空）

### 22. flow:request（请求）

```xml
<flow:request id="Activity_xxx" name="请求">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "url": "https://example.com/api",
    "method": "get",
    "version": 1,
    "authType": 1,
    "headerData": [],
    "requestData": [],
    "responseData": [],
    "errorHandler": {"handler":"retry"},
    "retryCount": 5
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</flow:request>
```

**字段说明**：
- `url`：请求URL
- `method`：`"get"` / `"post"` / `"put"` / `"delete"`
- `authType`：1=无认证
- `headerData`/`requestData`/`responseData`：数组（通常为空）
- `errorHandler.handler`：`"retry"` / `"throw"` / `"ignore"`
- `retryCount`：重试次数

### 23. msg:alarm（报警消息）

```xml
<msg:alarm id="Activity_xxx" name="报警消息" tabKey="basic">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "isMute": false,
    "isPersistent": false,
    "message": "设备异常报警",
    "display": "yes",
    "data": [],
    "resourceGroupId": "0",
    "needPhoto": false,
    "needHandWritting": false
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</msg:alarm>
```

**字段说明**：
- `isMute`：是否静音
- `isPersistent`：是否持久报警
- `message`：报警消息文本
- `display`：`"yes"`（显示）
- 与 msg:guide 区别：报警消息不暂停程序，但可后续确认；msg:guide 仅提示

### 24. timer:pause（暂停计时器）

```xml
<timer:pause id="Activity_xxx" name="暂停计时器">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "timer": "$(ds)"
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</timer:pause>
```

**字段说明**：
- `timer`：引用 `timer:start` 中定义的变量 `$(XXX)`

### 25. timer:clock（时钟）

```xml
<timer:clock id="Activity_xxx" name="时钟">
  <ext:data><![CDATA[{
    "subTitle": "",
    "showDetail": true,
    "type": "everyday",
    "everyday": "01:00:00",
    "everyHour": "00:00",
    "everyMinute": "10"
  }]]></ext:data>
  <bpmn2:incoming>Flow_in</bpmn2:incoming>
  <bpmn2:outgoing>Flow_out</bpmn2:outgoing>
</timer:clock>
```

**字段说明**：
- `type`：`"everyday"`（每日）/ `"everyHour"`（每小时）/ `"everyMinute"`（每分钟）
- `everyday`：每日触发时间 `"HH:MM:SS"`
- `everyHour`：每小时触发 `"MM:SS"`
- `everyMinute`：每分钟触发（分钟数）

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
| 检测信号 0→非0 | flow:risingEdge | 3 | - |
| 检测信号 非0→0 | flow:fallingEdge | 3 | - |
| 拼接字符串 | io:concat | - | - |
| 导出数据到文件 | io:fileExport | - | - |
| 从文件读取数据 | io:fileImport | - | - |
| 修改程序标签 | io:modifyLabel | - | - |
| 修改程序属性 | io:modifyProps | - | - |
| 引用其他主程序 | flow:otherMainProc | - | - |
| 发送HTTP请求 | flow:request | - | - |
| 报警提示（不暂停） | msg:alarm | - | - |
| 暂停计时器 | timer:pause | - | - |
| 等待到指定时刻 | timer:clock | - | - |

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
