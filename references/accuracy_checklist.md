# 准确率检查清单

保存（Step 4）前全部勾选；结构项以 `validate_bpmn.py` 为准。

## A. 语义

- [ ] 按 `element_split.md` 原子拆分；无漏步、无多余节点
- [ ] guide/confirm、or/and/branch、串行/并行选择正确
- [ ] 主/子边界与用户方案一致

## B. 位号

- [ ] 位号已用户确认；DCS `#()` / 变量 `$()`；无 PLACEHOLDER
- [ ] type（1/3）匹配

## C. XML / 连线

- [ ] `assemble_full_xml` 生成；`validate_bpmn.py` 退出码 0
- [ ] 子程序：`subId`=真 ID；save 主 update / 子 add

## D. 门禁

- [ ] 用户已确认流程图；一次 save；编译前已询问
- [ ] 未调用 `deploy_program`

## E. 编译重试（≤3）

- [ ] 同 appid；不改拓扑；位号问题再问用户；修正→save→compile
