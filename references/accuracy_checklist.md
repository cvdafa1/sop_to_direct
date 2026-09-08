# 准确率检查清单

保存（Step 4）前全部勾选。细则见对应权威文件；结构以 `validate_bpmn.py` 为准。

## A. 语义 — `element_split.md`

- [ ] 逐句原子拆分；覆盖自检无缺口
- [ ] 每步有 `node_type`（∈ schema）与 `source_text`
- [ ] 元件类型与串/并行选择正确；已展示完整列表

## B. 位号 — `interaction.md` / `node_reference.md`

- [ ] 已用户确认；DCS `#()` / 变量 `$()`；无 PLACEHOLDER
- [ ] type 为 1（模拟量）或 3（数字量）

## C. XML — `golden_xml_rules.md` / `subprocess.md`

- [ ] `assemble_full_xml` + `validate_bpmn.py` 退出码 0
- [ ] 若有子程序：字段与 save 分工符合 `subprocess.md`

## D. 门禁 — `interaction.md`

- [ ] 已确认流程图；一次 save
- [ ] Step 4.5 二选一已选；未调用 `deploy_program`

## E. 编译重试 — `SKILL.md`

- [ ] 同 appid；≤3；不改拓扑；位号问题再问用户
