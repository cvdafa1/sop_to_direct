# Direct 平台节点参考

按节点类型提供 Process 片段与关键字段。  
**单源原则**：连线/Diagram/布局 → `golden_xml_rules.md`；ext:data schema → `element_schema.json`；子程序元件 → `subprocess.md`；位号路径/type → 本文 §一/§二。

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

（示例为是+否结构。出边条数与 name/situation：**唯一来源** `golden_xml_rules.md` §3。）

**字段说明**：
- `keep`：0（固定）
- `data[]`：条件数组（通常只有 1 项）
  - `judge`：`"=="`, `">="`, `"<="`, `">"`, `"<"`, `"!="`
  - `targetValue`：**字符串类型**
  - `type`：见上文「二、type 字段值」

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

**与 flow:or 区别**：多条件 `and` 关系。出边规则见 `golden_xml_rules.md` §3。

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
  - `relation`：该支自己的条件关系。`"or"` = 该支内任一成立；`"and"` = 该支内须同时成立。**各支独立，可混用，不必整步只有一种**
  - `desc`：分支描述
  - `data[]`：条件数组
  - `row`：分支序号（0, 1, 2...）
- 出边 **N** 条（与 `branch` 长度一致，**不限 3**）：`{"situation":"0"}` … `{"situation":"N-1"}`

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

### 12. flow:parallel1 / parallel2

本 skill **禁用**（`ir_to_xml` 拒绝）。SOP「同时」见 `element_split.md` R5。平台模板见 `element_schema.json`，勿经本 skill 产出。

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

### 21. flow:subproc / flow:otherMainProc

- **本 skill 使用** `flow:subproc`：XML 与 name/`subId`/`subTitle` 写入规则的**唯一来源** → `subprocess.md` §flow:subproc  
- `flow:otherMainProc`：本 skill **不使用**（勿生成）

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

## 其它规则（勿在此重复）

| 主题 | 权威文件 |
|------|----------|
| 连线 / Edge-Shape 顺序 / ID | `golden_xml_rules.md` |
| IR / 编译入口 | `ir_schema.md` / `ir_to_xml.py` |
| ext:data schema | `element_schema.json` |
| SOP→节点选择 | `element_split.md` |
| 布局坐标 | `scripts/layout_generator.py` |

