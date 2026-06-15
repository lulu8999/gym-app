# 文件损坏：Null Byte 问题

## 问题描述

文件写入时经常包含 null byte (`\x00`)，导致：
- Python 读取报错：`embedded null byte`
- JavaScript 检查报错：`Invalid or unexpected token`
- 文件无法被正确解析或执行

## 发生场景

1. **patch 工具损坏文件** — patch 操作失败时可能留下 null byte
2. **write_file 中断** — 写入大文件时被中断
3. **跨进程文件操作** — 不同进程同时写入同一文件

## 解决方案

### Python 清理脚本

```python
with open('/path/to/file', 'rb') as f:
    data = f.read()
# 替换 null bytes
data = data.replace(b'\x00', b'')
with open('/path/to/file', 'wb') as f:
    f.write(data)
```

### 预防措施

1. **写入前检查** — 大文件写入使用 `write_file` 而非 patch
2. **写入后验证** — 检查文件是否可以正常读取
3. **失败后清理** — patch 失败后立即用上述脚本清理

## 涉及文件（2026-06-10）

- `/root/admin/static/kanban.js` — 多次遇到，需定期清理
- `/root/admin/templates/kanban.html` — 遇到一次

## 相关 Skill

- `lulu-workflow` — 包含"常见错误"章节
