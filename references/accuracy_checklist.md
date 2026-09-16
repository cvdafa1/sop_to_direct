# 准确率检查清单

保存（**Step 3.5**）前全部勾选（本 skill 无独立 Step 4，已并入 3.5；**保存本身不询问用户**）。**细则禁止写在本文件**；只勾选并打开对应唯一来源。

| 域 | 勾选 | 唯一来源 |
|----|------|----------|
| 0 流程 | 已严格按 `SKILL.md` 工作流执行；未跳步/换序/自创路径；**1.5 与 2 已分轮确认** | `SKILL.md`「绝对执行原则」+ `interaction.md` |
| A 语义 | 全文识别 + 逐句拆分 + 覆盖自检 + 完整列表已展示 | `element_split.md` |
| A IR 形态 | `ir_to_xml.py` 能编过；结构= `sample_ir.json`（无 main_program/steps） | `ir_schema.md` + `fixtures/sample_ir.json` |
| B 位号 | 已确认；`#()`/`$()`；type；无 PLACEHOLDER | `interaction.md` Step 2.5 + `node_reference.md` §一/二 |
| C XML | `ir_to_xml.py` + `validate_bpmn.py`=0 | `ir_schema.md` / `golden_xml_rules.md` |
| C 标识符 | XML 内子程序/计时器/变量名均为 `[A-Za-z0-9_]`；非法已改 | `subprocess.md` + `validate_bpmn.py` |
| C 子程序 | 若拆分：主 XML + N 子 XML 均已生成；主含 N 个 `flow:subproc`；save 传入全部 `xml_content` | `subprocess.md` 硬门禁 |
| C timers | 若用 start/stop/pause/restart/cond：`sfc.timers` 已声明 | `subprocess.md` §timers |
| C variables | 若用程序变量（如 io:var）：`sfc.variables` 已声明且 dataType 正确 | `subprocess.md` §variables |
| D 门禁 | 3.5 save 已成功（code=0）；编译已选；未 deploy | `interaction.md` / `SKILL.md` |
| E 生成/编译重试 | 未因失败简化流程；平台编译同 appid≤3、不改拓扑 | `SKILL.md` Step 3 失败处置 / §9 |
