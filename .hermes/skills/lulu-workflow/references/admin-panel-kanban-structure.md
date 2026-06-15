# Admin Panel 结构与 Kanban 入口（2026-06-10）

## 问题背景

用户反馈：
1. 访问 admin.lulugame.fun 直接看到 kanban，里面什么都没有
2. 用户管理界面找不到了

## 根本原因

- Admin panel 登录后默认跳转到 `/` → 用户管理界面
- Kanban 位于 `/kanban` 子路径
- 用户直接访问 `/kanban` 但没有登录 cookie → API 返回 302 → 前端没有正确显示数据

## 正确访问方式

| 功能 | URL | 说明 |
|:-----|:----|:-----|
| 用户管理 | https://admin.lulugame.fun/ | 登录后默认显示 |
| 任务看板 | https://admin.lulugame.fun/kanban | 需要先登录 |
| 登录页 | https://admin.lulugame.fun/login | 独立登录页面 |

## 关键修复

### 1. API 请求需要携带登录 Cookie

```javascript
// ❌ 之前 - fetch 默认不携带 cookie
const res = await fetch('/api/kanban/agents');

// ✅ 修复后 - 添加 credentials
const res = await fetch('/api/kanban/agents', { 
    credentials: 'include' 
});
```

### 2. 前端登录跳转处理

```javascript
// 统一处理 302/401 跳转
if (res.status === 302 || res.status === 401) {
    window.location.href = '/login?next=/kanban';
    return null;
}
```

## 文件路径对照

| 组件 | 路径 |
|:-----|:-----|
| Flask 入口 | /root/admin/app.py |
| 用户管理模板 | /root/admin/templates/index.html |
| Kanban 模板 | /root/admin/templates/kanban.html |
| Kanban JS | /root/admin/static/kanban.js |
| 备份源（可恢复） | /root/.hermes/hermes-agent/admin/static/kanban.js |

## 文件损坏处理

**问题**：kanban.js 包含 null bytes (\\x00)，导致文件损坏无法解析

**解决**：
```python
# 清理 null bytes
with open('/root/admin/static/kanban.js', 'rb') as f:
    data = f.read()
data = data.replace(b'\\x00', b'')
with open('/root/admin/static/kanban.js', 'wb') as f:
    f.write(data)
```

或者从备份源恢复：
```bash
cp /root/.hermes/hermes-agent/admin/static/kanban.js /root/admin/static/kanban.js
```
