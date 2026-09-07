# 准确率检查清单

在 **保存（Step 4）之前** 必须全部勾选通过。可用 `scripts/validate_bpmn.py` 做结构初检。

## A. 语义与拆分

- [ ] IR 已按 `element_split.md` 拆成原子元件
- [ ] SOP 关键动作在流程中均有对应节点（无漏步）
- [ ] 无多余节点（未引入 SOP 没有的操作）
- [ ] guide/confirm、or/and/branch、串行/并行选择正确
- [ ] 主/子程序边界与用户确认方案一致；步骤守恒

## B. 位号与数据

- [ ] 所有操作/条件位号已经用户确认
- [ ] XML 内 DCS 位号均为 `#(…)` 形式
- [ ] 计时器/变量为 `$(…)` 形式
- [ ] type（1/3）与模拟量/数字量匹配
- [ ] 无占位符 `PLACEHOLDER` 残留

## C. XML 结构与连线（连线不显示重点查这里）

- [ ] 使用 `assemble_full_xml`，未手写 Edge/sequenceFlow
- [ ] 每条 sequenceFlow 都有同 id 的 BPMNEdge
- [ ] 无自闭合 `<sequenceFlow ... />`；plain 含 `{"lineType":1}`
- [ ] 已 Read schema/模板；无 xml 声明 / definitions / xmlns
- [ ] 每个程序含 start→…→end；Shape 全部在 Edge 之前
- [ ] `check_overlaps` / `check_connection_integrity` 通过
- [ ] 条件节点恰有 yes/no 两条出边
- [ ] `validate_bpmn.py` 退出码 0
- [ ] 子程序：`subId` = `get_next_id` 真值；save 时主在 update、子在 add

## D. 保存与编译门禁

- [ ] 用户已确认流程图（节点数、连线数、路径摘要）
- [ ] 一次 `save_program` 提交全部 XML（禁止分批）
- [ ] 保存成功后列出 XML/统计，**询问**是否编译；未同意不 compile
- [ ] 未调用 `deploy_program`

## E. 编译失败重试（最多 3 次）

- [ ] 仅在同一 appid 上修正；禁止新建程序
- [ ] 禁止删节点、改拓扑、改业务逻辑
- [ ] 仅允许：位号、参数值、XML 格式、ID 匹配修复
- [ ] 位号类错误必须再与用户确认
- [ ] 修正前重新 Read 三份 XML 参考文件
- [ ] 路径：修正 → save → compile（**不**回退到重新设计流程，除非用户要求）
