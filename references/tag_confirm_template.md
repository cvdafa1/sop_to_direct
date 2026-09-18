# 位号确认（本机 HTTP + 浏览器提交）

**样板 JSON**：`fixtures/tag_confirm_template.json`  
**编辑器壳**：`fixtures/tag_confirm_editor.html`  
**生成（可选）**：`scripts/make_tag_confirm_editor.py`  
**确认服务（强制）**：`scripts/serve_tag_confirm.py`  
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

**禁止**新增/删除行；服务端只合并 `tag`/`type`/`value`。  
**完整度**：每一行的 `tag`、`type`、`value` 必须齐全，否则页面与服务端均拒绝。

## 流程（硬门禁）

```
系统预写 JSON
  → 系统运行 serve_tag_confirm.py（出 HTML + 本机 http://127.0.0.1:port/ + 自动打开）
  → 【阻塞】用户未点「提交确认」则脚本不退出 → 禁止进入 Step 3
  → 用户提交 → 服务端写 confirmed JSON → 退出码 0
  → 系统写回 IR → Step 3
```

```bash
python -u scripts/serve_tag_confirm.py artifacts/<run>/tag_confirm.json \
  --html-out artifacts/<run>/tag_confirm.html \
  --confirmed-out artifacts/<run>/tag_confirm.confirmed.json
```

- 对话展示脚本打印的 `[URL]`（可点击的 `http://127.0.0.1:…/`）
- **禁止**内嵌 HTML；**禁止**在退出码 0 前继续流程
- 用户须通过该 HTTP 地址打开页面（直接双击本地 html 无法 POST 生效）
