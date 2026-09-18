# 位号确认（JSON + 内嵌 HTML）

**样板 JSON**：`fixtures/tag_confirm_template.json`  
**编辑器壳**：`fixtures/tag_confirm_editor.html`  
**注入脚本**：`scripts/make_tag_confirm_editor.py`  
交互细则：`interaction.md` Step 2.5。

## JSON 契约

| 字段 | 提交时 | 说明 |
|------|--------|------|
| `id` | 是 | 行号，从 1 起 |
| `program` | 是 | `main` 或子程序 name |
| `step` | 是 | 步骤/节点名 |
| `usage` | 是 | 用途 |
| `tag` | 是 | 确认位号；识别不到预填时 `""`；提交不得空 |
| `type` | 是 | `"1"` / `"3"` |
| `value` | 按需 | 设定值 |
| `note` | 否 | 备注 |

写回 IR：`node_reference.md` §一。

## 生成与内嵌

```bash
python scripts/make_tag_confirm_editor.py artifacts/<run>/tag_confirm.json -o artifacts/<run>/tag_confirm.html
```

Agent 将 HTML **嵌入 Step 2.5 对话**（或请用户打开该文件）。用户改完点「提交并复制 JSON」，把 JSON **一次**贴回。
