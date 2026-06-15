# 文件损坏问题：embedded null byte 修复

## 问题描述

2026-06-10 修改 `/root/admin/static/kanban.js` 时，文件出现"embedded null byte"错误，导致：
- Node.js 语法检查崩溃（`node --check` 返回 134）
- PM2 重启后页面无法正常加载
- 所有 fetch 请求返回 500 或空响应

## 根本原因

patch 工具在处理包含特殊字符或被截断的内容时，可能引入 null 字节（`\x00`），导致文件损坏。

## 修复步骤

### 1. 检查文件状态

```bash
# 语法检查会崩溃
node --check /root/admin/static/kanban.js

# 查看文件是否有异常字符
cat /root/admin/static/kanban.js | head -5
ls -la /root/admin/static/kanban.js
```

### 2. 从备份恢复

```bash
# 从 hermes-agent 目录复制干净的版本
cp /root/.hermes/hermes-agent/admin/static/kanban.js /root/admin/static/kanban.js
```

### 3. 重启服务

```bash
pm2 restart admin-panel
```

### 4. 验证

```bash
# 检查服务状态
curl -s http://localhost:9802/api/kanban/agents
```

## 预防措施

1. **修改前备份**：每次 patch 前可以 `cp file file.bak`
2. **用 sed 替代 patch**：对于简单替换，用 `sed -i 's/old/new/' file`
3. **修改后立即测试**：用 `curl` 验证 API 响应
4. **避免大段替换**：分多次小范围修改，降低损坏风险

## 快速恢复命令

```bash
# 一行命令恢复 + 重启
cp /root/.hermes/hermes-agent/admin/static/kanban.js /root/admin/static/kanban.js && pm2 restart admin-panel && sleep 3 && curl -s http://localhost:9802/api/kanban/agents | head -50
```
