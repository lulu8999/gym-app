# 文件同步问题：hermes-agent vs admin 目录

## 问题背景

2026-06-10 开发 L123 看板功能时，Claude Code 在 `.hermes/hermes-agent/admin/` 下创建了新文件，但实际运行的是 `/root/admin/` 目录。

两个目录结构：
```
/root/.hermes/hermes-agent/admin/    ← Claude Code 创建的位置
/root/admin/                          ← 实际运行的位置
```

## 症状

- 修改了 A 目录的文件，但页面没变化
- 重启服务无效，因为改的是错误目录

## 快速同步命令

```bash
# 同步 kanban.js
cp /root/.hermes/hermes-agent/admin/static/kanban.js /root/admin/static/kanban.js

# 同步 kanban.html
cp /root/.hermes/hermes-agent/admin/static/kanban.html /root/admin/templates/kanban.html
```

## 预防措施

1. **任务开始前确认路径** — 问用户或查 PM2 确认实际运行目录
2. **PM2 describe 查看** — `pm2 describe admin-panel` 显示 `exec cwd`
3. **修改后立即验证** — 用 curl 测试 API 响应

## 路径记忆

| 服务 | 运行目录 | PM2 名称 |
|------|----------|----------|
| admin-panel | `/root/admin` | admin-panel |
| hermes-gateway | `/root/.hermes/hermes-agent` | hermes-gateway |
