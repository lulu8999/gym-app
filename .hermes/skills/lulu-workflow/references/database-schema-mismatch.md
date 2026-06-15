# 数据库 Schema 不匹配问题

> 日期：2026-06-10

## 问题

错误日志：
```
Error: in prepare, no such column: card_count
SELECT task_id, description, status, is_collaborative, card_count FROM tasks
```

## 原因

代码期望的表结构：
```sql
CREATE TABLE tasks (
    ...
    card_count INTEGER DEFAULT 0,
    ...
);
```

实际数据库表结构：
```sql
CREATE TABLE tasks (
    task_id       TEXT PRIMARY KEY,
    description   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    mode          TEXT NOT NULL DEFAULT 'parallel',
    is_collaborative INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    finished_at   TEXT,
    report        TEXT
    -- 缺少 card_count 列
);
```

## 修复

```bash
sqlite3 /root/.hermes/l123_taskpool.db "ALTER TABLE tasks ADD COLUMN card_count INTEGER DEFAULT 0;"
```

## 预防

- 修改代码前先检查 `.schema`
- 代码和数据库 schema 一起版本管理
- 复杂功能发布前做 schema 验证测试
