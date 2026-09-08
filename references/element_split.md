# 元件拆分规则（准确率核心）

**核心原则：一个元件 = 一个原子操作或一个独立判断。**  
复合步骤必须拆分；**禁止合并、禁止跳过、禁止用一句话概括多步。**

SOP 解析目标：原文中每一个可执行语义点，都必须在 IR 中有对应 `node_type`（且属于 `element_schema.json` 白名单）。

---

## 0. 解析强制流程（Step 1 必须按此做）

```
1. 全文通读 → 按阶段/条款切块（保留原文编号）
2. 逐句切分（逗号、顿号、分号、「后」「然后」「并」「同时」均可能是边界）
3. 对每句做语义标注：操作 / 反馈 / 等待 / 判断 / 提示 / 确认 / 报警 / 并行
4. 按 R 规则映射为原子元件序列（不得跳过任一类语义）
5. 覆盖自检：原文动作点数量 ≈ IR 元件数量（允许 start/end 额外存在）
6. 产出 IR JSON +「原文→元件」对照表，向用户展示后再进 Step 1.5
```

### 0.1 必须单独成元件的语义点（漏一个即解析不合格）

| 语义点 | 典型原文线索 | 元件 |
|--------|--------------|------|
| 写位号/开关/启停/调参 | 开、关、启、停、投、切、设定、写入、调至 | `io:dcs` |
| 写程序变量 | 赋值、置变量、清零计数 | `io:var` |
| 计算赋值 | 计算、累计、差值 | `io:calc` |
| 单条件判断 | 若、判断、是否、等于、到位、运行中 | `flow:or` |
| 多条件同时满足 | 且、同时满足、均 | `flow:and` |
| 多选一 | 分别判断、三种情况、哪一台 | `flow:branch` |
| 纯延时 | XX秒/分钟后、延时、等待一段时间 | `timer:wait` |
| 超时分支 | XX秒内未…则、超时 | `timer:cond`（常配 `timer:start`） |
| 仅提示不暂停 | 提示、弹窗告知、显示信息 | `msg:guide` |
| 暂停等人确认 | 确认是否、点击确认后、同意后继续 | `msg:confirm` |
| 报警提示 | 报警、告警 | `msg:alarm` |
| 同时无先后 | 同时、一并、同步 | `flow:parallel1` 包裹多操作 |
| 反馈信号 | 反馈、到位、收到信号、取反 | 通常独立 `flow:or`（见反馈表） |
| 上/下跳变 | 从0变1、上升沿、下降沿 | `flow:risingEdge` / `flow:fallingEdge` |

### 0.2 严禁的解析偷懒

- ❌ 把「关阀 + 等反馈 + 停泵 + 等反馈」写成 1 个 `io:dcs`
- ❌ 只写主操作，丢掉「收到反馈」「延时」「弹窗」
- ❌ 用阶段标题代替阶段内逐步操作
- ❌ 原文有「否则/不满足」双侧语义时，只画「是」或只画「否」
- ❌ 把「确认」做成 `msg:guide`，或把「仅提示」做成 `msg:confirm`
- ❌ 枚举 A、B、C 三台设备却只生成 1 个节点
- ❌ 发明 schema 未定义的元件名

### 0.3 覆盖自检（进入 1.5 前必须做）

对 SOP 原文统计并与 IR 对照：

| 统计项 | 原文约数 | IR 元件数 | 是否覆盖 |
|--------|----------|-----------|----------|
| 设备操作动词 | | `io:dcs` 等 | |
| 反馈/到位/取反 | | `flow:or` / checkData | |
| 延时 | | `timer:wait` | |
| 条件/若…否则 | | `flow:or`/`and`/`branch` | |
| 提示/确认/报警 | | `msg:*` | |
| 「同时」组 | | `flow:parallel1` | |

**任一类原文有而 IR 无 → 必须补拆，不得进入 Step 1.5。**

向用户展示：阶段列表 + **全部原子元件**（`node_type` + action + 位号/设备）+ 覆盖自检结果。

进入 1.5 前勾选：

- [ ] 已逐句拆分，非按段概括  
- [ ] 覆盖自检无缺口  
- [ ] 每个 step 有 `node_type` + `source_text`  
- [ ] 无未定义元件名  
- [ ] 已展示完整原子元件列表（不只摘要）

---

## 1. 拆分规则表

| # | SOP 文本模式 | 拆分结果 | 说明 |
|---|-------------|---------|------|
| R1 | "关/开/停/启动设备A，反馈信号B" | `io:dcs(A)` → `flow:or(B)` | 操作与反馈分离 |
| R2 | "变频调为X，反馈Y后执行Z" | `io:dcs(X)` → `flow:or(Y)` → `io:dcs(Z)` | 操作→反馈→再操作 |
| R3 | "同一设备同时设多参数" | 1×`io:dcs`（data 多项） | 仅同一设备可合并 |
| R4 | "依次关闭A、B、C" | `io:dcs(A)`→`io:dcs(B)`→`io:dcs(C)` | 不同设备不合并 |
| R5 | "同时操作A/B/C，无先后" | `flow:parallel1` 内 3×`io:dcs` | 并行 |
| R6 | "XX秒/分钟后执行A" | `timer:wait` → 下一步 | 纯等待 |
| R7 | "XX秒未收到B则提示/报警C" | `io:dcs?` → `timer:cond` → `msg:guide`/`msg:alarm` | 超时分支 |
| R8 | "弹窗提示XXX"（不等人） | `msg:guide` | |
| R9 | "确认是否XXX，确认后继续" | `msg:confirm` → 下一步 | |
| R10 | "若A则…"（无否则） | `flow:or` → IR 仅 `branch_yes` | 不硬凑否；出边 XML → `golden_xml_rules.md` §3 |
| R11 | "若A则…否则…" | `flow:or`/`and` → yes + no | 仅此时 IR 填 `branch_no`；出边 XML → 同上 |
| R12 | "分别判断三种情况/哪台运行" | `flow:branch`（N 支） | 多选一 |
| R13 | "全部完成后提示" | 末端 `msg:guide` | |
| R14 | "报警XXX"（不暂停） | `msg:alarm` | 与 guide 区分 |
| R15 | "开始计时/停止计时/暂停计时" | `timer:start` / `stop` / `pause` | |
| R16 | "信号从0变1 / 从1变0" | `flow:risingEdge` / `fallingEdge` | |
| R17 | "变量赋值为X" | `io:var` | |
| R18 | "切除/投入自控、切手动" | `io:dcs`（如 AUTOOPT/MODE） | 勿漏 |

---

## 2. 反馈信号处理

| SOP 描述 | 处理 | 元件 |
|----------|------|------|
| 操作A，收到反馈B | 操作后独立判断 | `io:dcs` → `flow:or` |
| 操作A，反馈B后执行C | 反馈作前置 | `io:dcs` → `flow:or` → `io:dcs` |
| 操作A，XX秒未收到B则报警C | 超时 | `io:dcs` → `timer:cond` → `msg:*` |
| 反馈B取反 | 判 ==0 | `flow:or(B==0)` |
| 同一设备同类操作的反馈 | 可进 `io:dcs.checkData` | 仅此情况可合并 |

**默认：反馈单独成 `flow:or`。** 只有明确「同一设备、同类操作、文案紧绑」才用 checkData。

---

## 3. 复合拆分示例（对照用）

**原文**：「关循环水泵P0801A出口开关阀（EV-0801A），阀位反馈（ZSC-EV0801A），停循环水泵P0801A，反馈（YL-P0801A取反）」

```
io:dcs(关EV) → flow:or(ZSC到位) → io:dcs(停P0801A) → flow:or(YL==0)
```

4 个元件，不可压成 2 个。

**原文**：「判断风机运行（YL-C0801）；若关闭则提示结束；若启动则变频调0→等反馈→停风机→等反馈→提示结束」

```
flow:or(YL==0)
  ├─ yes → msg:guide(结束) → end
  └─ no  → io:dcs(变频0) → flow:or(SI到位) → io:dcs(停风机) → flow:or(YL取反) → msg:guide(结束) → end
```

两支都有「否则」语义时才完整展开；若原文无否则，只保留 yes 支。

---

## 4. IR 结构（每个 step 落到一个 schema 元件）

```json
{
  "program_name": "circ_water_shutdown",
  "description": "...",
  "version": "v1.0",
  "coverage": {
    "source_action_points": 0,
    "ir_elements": 0,
    "notes": "覆盖说明/缺口"
  },
  "main_program": {
    "description": "主程序",
    "steps": [
      {
        "step_no": 1,
        "source_text": "尽量保留对应原文片段",
        "action": "原子动作描述",
        "node_type": "io:dcs",
        "equipment": { "name": "", "tag": "", "action_type": "MANON|MANOF|AUTOOPT|..." },
        "parameters": [{ "name": "", "targetValue": "", "type": "1|3" }],
        "condition": {
          "tag": "", "judge": "==|!=|>|<", "targetValue": "",
          "branch_yes": [], "branch_no": []
        },
        "safety": { "threshold_tag": "", "threshold_value": "", "action": "" }
      }
    ]
  },
  "subprograms": []
}
```

要求：

- 每个 step 必须有 `node_type`（∈ schema）与 `source_text`（可追溯）  
- 分支：`branch_yes` 必填；`branch_no` 仅当原文有否则时填写（见 R10/R11）；出边 XML **唯一来源** `golden_xml_rules.md` §3  
- 并行：父 step `node_type=flow:parallel1`，子 steps 为各分支序列  
- 单程序：步骤全在 `main_program.steps`；`subprograms` 为空  

---

（解析完成门禁已并入 §0.3，勿在他处复述。）
