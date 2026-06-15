# CSS Class 验证检查清单

## 问题背景

2026-06-10 开发 Kanban 看板时，JS 代码 targeting `agent-block` class，但 HTML 实际使用 `agent-card` class。

## 验证步骤

在修改 JS/TS 文件前：

1. **读取 HTML 模板** — 找到实际使用的 CSS 类名
2. **匹配 JS 选择器** — 确认 `document.querySelectorAll()` 参数与 HTML 一致
3. **检查渲染函数** — JS 动态生成的 HTML 也要验证 class 名称

## 常见陷阱

| 陷阱 | 解决方案 |
|------|----------|
| JS 用 `agent-block` 但 HTML 是 `agent-card` | 先 grep HTML 模板 |
| 动态渲染时 class 名拼写错误 | 用 `search_files` 搜两处确认一致 |
| 复制代码时带过来了旧 class 名 | 粘贴后立即 grep 验证 |

## 快速检查命令

```bash
# 检查 JS 中使用的 class
grep -n "agent-" /root/admin/static/kanban.js

# 检查 HTML 中的实际 class  
grep -n "class=\"agent" /root/admin/templates/kanban.html
```
