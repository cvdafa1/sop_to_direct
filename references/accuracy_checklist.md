# 准确率检查清单

保存（Step 4）前全部勾选。**细则禁止写在本文件**；只勾选并打开对应唯一来源。

| 域 | 勾选 | 唯一来源 |
|----|------|----------|
| A 语义 | 逐句拆分 + 覆盖自检 + 完整列表已展示 | `element_split.md` |
| B 位号 | 已确认；`#()`/`$()`；type；无 PLACEHOLDER | `interaction.md` Step 2.5 + `node_reference.md` §一/二 |
| C XML | `ir_to_xml.py` + `validate_bpmn.py`=0 | `ir_schema.md` / `golden_xml_rules.md` |
| C 子程序 | 若有：字段与 save 正确 | `subprocess.md` |
| C timers | 若用 start/stop/pause/restart/cond：`sfc.timers` 已声明 | `subprocess.md` §timers |
| C variables | 若用程序变量（如 io:var）：`sfc.variables` 已声明且 dataType 正确 | `subprocess.md` §variables |
| D 门禁 | 3.5 已确认并保存；编译已选；未 deploy | `interaction.md` / `SKILL.md` |
| E 编译重试 | 同 appid；≤3；不改拓扑 | `SKILL.md` |
