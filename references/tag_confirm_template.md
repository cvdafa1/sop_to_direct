# 位号确认（JSON + 内嵌 HTML）

**样板 JSON**：`fixtures/tag_confirm_template.json`  
**编辑器壳**：`fixtures/tag_confirm_editor.html`  
**注入脚本**：`scripts/make_tag_confirm_editor.py`  
交互细则：`interaction.md` Step 2.5。

## JSON 契约

| 字段 | 用户可否改 | 说明 |
|------|------------|------|
| `id` | 否（锁定） | 行号，从 1 起 |
| `program` | 否（锁定） | `main` 或子程序 name |
| `step` | 否（锁定） | 步骤/节点名 |
| `usage` | 否（锁定） | 用途 |
| `tag` | **是** | 确认位号；识别不到预填时 `""`；**提交不得空** |
| `type` | **是** | `"1"` / `"3"`；**提交必须合法** |
| `value` | **是** | 设定值；**提交不得空**（`"0"` 合法，空串非法） |
| `note` | 否（锁定） | 备注 |

**禁止**新增/删除行；系统重写 JSON 时只合并 `tag`/`type`/`value`。  
**完整度校验**（页面提交 + 系统写回均执行）：每一行的 `tag`、`type`、`value` 必须齐全；缺位号、非法 type、或缺设定值 → 拒绝并指出行号。  
写回 IR：`node_reference.md` §一。

## 流程（系统为主，用户只改三字段）

```
系统预写 JSON → 系统跑脚本出 HTML → 系统内嵌
  → 用户仅改 位号/type/设定值 并提交（不可增删行）
  → 系统按行合并重写 tag_confirm.json → 写回 IR
```

```bash
python scripts/make_tag_confirm_editor.py artifacts/<run>/tag_confirm.json -o artifacts/<run>/tag_confirm.html
```

系统嵌入 HTML 后，用户只改位号/type/设定值并点提交；系统按预写行序合并覆盖这三字段再写 IR。用户不增删行、不手写 JSON、不跑脚本。
