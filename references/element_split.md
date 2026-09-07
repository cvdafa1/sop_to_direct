# 元件拆分规则（准确率核心）

**核心原则：一个元件 = 一个原子操作或一个独立判断。**  
复合步骤必须拆分；禁止把多个独立操作塞进同一个元件。

## 拆分规则表

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

## 反馈信号处理

| SOP 描述 | 处理方式 | 元件 |
|----------|---------|------|
| "操作A，收到反馈信号B" | 操作后加反馈判断 | `io:dcs` → `flow:or` |
| "操作A，收到反馈信号B后执行C" | 反馈作为后续操作前置条件 | `io:dcs` → `flow:or` → `io:dcs` |
| "操作A，XX秒未收到反馈B则报警C" | 超时判断+报警 | `io:dcs` → `timer:cond` → `msg:guide` |
| "操作A，反馈信号B取反" | 取反 = 判断信号==0 | `flow:or(B==0)` |
| "操作A，收到反馈信号B"（同一设备同类操作） | 可合并到 io:dcs 的 checkData | `io:dcs`（checkData 含B） |

## 复合步骤拆分示例

**SOP**："关循环水泵P0801A出口开关阀（EV-0801A），阀位反馈信号（ZSC-EV0801A），停运行的循环水泵P0801A，收到反馈信号（YL-P0801A取反）"

```
io:dcs(关EV-0801A) → flow:or(ZSC-EV0801A==到位) → io:dcs(停P0801A) → flow:or(YL_P0801A==0)
```

4 个元件。关阀与停泵是不同设备；反馈需独立判断。

**SOP**："收到停电机反馈信号15分钟后，弹窗确认是否关闭酸泵，点击确认后依次停泵A、B、C"

```
flow:or(停电机反馈) → timer:wait(15分钟) → msg:confirm(是否关闭酸泵) → io:dcs(停A) → io:dcs(停B) → io:dcs(停C)
```

**SOP**："判断风机运行信号（YL-C0801），若关闭则弹窗结束；若启动则变频调0→等反馈→停风机→等反馈→弹窗结束"

```
flow:or(YL-C0801==0)
  ├─ yes → msg:guide("循环水系统停车结束") → flow:end
  └─ no  → io:dcs(变频调0) → flow:or(SI-C0801到位) → io:dcs(停风机) → flow:or(YL-C0801取反) → msg:guide(...) → flow:end
```

## 结构化中间表示（IR）

解析后必须产出以下 JSON，再进入后续步骤。解析时即区分主/子程序边界。

```json
{
  "program_name": "从 SOP 标题提取（字母开头，仅字母数字下划线）",
  "description": "从 SOP 概述提取",
  "version": "v1.0",
  "main_program": {
    "description": "主程序",
    "steps": [
      {
        "step_no": 1,
        "action": "操作动作描述",
        "node_type": "io:dcs | flow:or | timer:wait | msg:guide | flow:subproc | ...",
        "subprogram_name": "仅 flow:subproc 时填写",
        "equipment": { "name": "", "tag": "", "action_type": "MANON|MANOF|AUTOOPT|..." },
        "parameters": [{ "name": "标签引用", "targetValue": "", "type": "1|3" }],
        "condition": {
          "tag": "", "judge": "==|!=|>|<", "targetValue": "",
          "branch_yes": "", "branch_no": ""
        },
        "safety": { "threshold_tag": "", "threshold_value": "", "action": "" }
      }
    ]
  },
  "subprograms": [
    {
      "name": "sub_name",
      "description": "子程序功能简述",
      "phases": [
        {
          "phase_name": "阶段名称",
          "is_parallel": false,
          "steps": []
        }
      ]
    }
  ]
}
```

- **纯子程序引用**：主程序 steps 仅含 `flow:subproc`
- **混合模式**：主程序可含自身操作 + `flow:subproc`
- **单程序**：全部步骤在 `main_program.steps`，`subprograms` 为空数组

## 解析后自检（进入 Step 1.5 前必须通过）

- [ ] 每个复合 SOP 句已按 R1–R13 拆成原子元件
- [ ] 操作与反馈未错误合并（除非明确适用 checkData 规则）
- [ ] `msg:guide` vs `msg:confirm` 选择正确（提示 vs 等待确认）
- [ ] 并行场景使用 `flow:parallel1`，串联场景不误用并行
- [ ] IR 中每个 step 有明确 `node_type`
- [ ] 设备/位号/参数/安全阈值字段已尽量从原文填入（缺失留空，Step 2.5 补）
