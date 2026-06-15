# Hermes 会话数据库（state.db）结构与查询

用于构建管理面板时查询用户的聊天记录和会话统计。

## 数据库位置

```
/root/.hermes/state.db
```

## 核心表

### sessions — 会话列表

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,              -- 会话唯一 ID
    source TEXT NOT NULL,              -- 来源渠道（cli, weixin, wecom, cron 等）
    user_id TEXT,                      -- 用户 ID（微信/企微的 chatId）
    model TEXT,                        -- 使用的模型
    started_at REAL NOT NULL,          -- 开始时间（Unix 时间戳）
    ended_at REAL,                     -- 结束时间
    end_reason TEXT,                   -- 结束原因
    message_count INTEGER DEFAULT 0,   -- 消息数
    tool_call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,    -- 输入 tokens
    output_tokens INTEGER DEFAULT 0,   -- 输出 tokens
    estimated_cost_usd REAL,           -- 估算费用
    actual_cost_usd REAL,              -- 实际费用
    title TEXT,                        -- 会话标题/摘要
    api_call_count INTEGER DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0
);
```

### messages — 每条消息

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,                -- user / assistant / tool
    content TEXT,                      -- 消息内容（文本）
    tool_call_id TEXT,                 -- 工具调用 ID
    tool_calls TEXT,                   -- 工具调用（JSON）
    tool_name TEXT,                    -- 工具名
    timestamp REAL NOT NULL,           -- 时间戳
    token_count INTEGER,               -- 本条 tokens
    finish_reason TEXT,
    reasoning TEXT,
    active INTEGER NOT NULL DEFAULT 1
);
```

## 常用查询

### 获取所有会话（按时间倒序）

```python
import sqlite3, json

conn = sqlite3.connect('/root/.hermes/state.db')
conn.row_factory = sqlite3.Row

rows = conn.execute('''
    SELECT id, source, user_id, title, message_count,
           input_tokens, output_tokens,
           datetime(started_at, 'unixepoch', '+8 hours') as start_time,
           datetime(ended_at, 'unixepoch', '+8 hours') as end_time,
           estimated_cost_usd
    FROM sessions
    WHERE source = 'weixin'  -- 或 'wecom', 'cli', 'cron'
    ORDER BY started_at DESC
    LIMIT 50
''').fetchall()
```

### 获取某会话的聊天记录

```python
msgs = conn.execute('''
    SELECT role, content, tool_name,
           datetime(timestamp, 'unixepoch', '+8 hours') as time,
           token_count
    FROM messages
    WHERE session_id = ? AND active = 1
    ORDER BY id ASC
''', (session_id,)).fetchall()
```

### 按用户 ID 查找会话

```python
rows = conn.execute('''
    SELECT id, title, message_count, started_at
    FROM sessions
    WHERE user_id LIKE ?  -- 企微/微信的 chatId
    ORDER BY started_at DESC
    LIMIT 20
''', (f'%{user_chat_id}%',)).fetchall()
```

### 统计 Token 消耗

```python
stats = conn.execute('''
    SELECT SUM(input_tokens) as total_input,
           SUM(output_tokens) as total_output,
           SUM(estimated_cost_usd) as total_cost,
           COUNT(*) as session_count
    FROM sessions
    WHERE datetime(started_at, 'unixepoch') >= date('now', '-7 days')
''').fetchone()
```

## 注意事项

- 时间戳是 Unix 时间戳（秒），东八区需要 +8 小时
- content 字段在 assistant 角色时可能包含大量工具调用结果（JSON 字符串），显示时建议截取前 200 字或过滤掉 tool 角色的消息
- source 字段标识来源：`weixin`（微信）、`wecom`（企微）、`cli`（命令行）、`cron`（定时任务）
- user_id 字段内容取决于平台：微信是 chatId，企微是用户标识
- 数据库是 WAL 模式，查询不会阻塞写操作
