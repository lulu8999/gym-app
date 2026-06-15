# Session 上下文管理诊断

## 问题症状

用户反馈"AI 一直在重复回答问题"、"答非所问"、"不听指令"。

## 根本原因

Session 上下文过长，模型被海量历史信息淹没，无法正确理解用户的最新指令。

## 诊断流程

### Step 1: 查看 session 状态

```python
import sqlite3

conn = sqlite3.connect('/root/.hermes/state.db')
cursor = conn.cursor()

session_id = '目标session_id'

# 查看 session 信息
cursor.execute('''
    SELECT id, title, source, model, message_count, 
           input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
           started_at, ended_at
    FROM sessions 
    WHERE id = ?
''', (session_id,))

result = cursor.fetchone()
print(f'消息数: {result[4]}')
print(f'输入token: {result[5]}')
print(f'缓存读取token: {result[7]}')
```

### Step 2: 检查压缩是否触发

```python
# 查看压缩次数
cursor.execute('''
    SELECT COUNT(*) as compress_count
    FROM compression_locks 
    WHERE session_id = ?
''', (session_id,))

compress_count = cursor.fetchone()
print(f'压缩次数: {compress_count[0]}')
```

### Step 3: 检查压缩配置

```bash
grep -A 10 "compression:" ~/.hermes/config.yaml
```

关键参数：
- `threshold`: 压缩触发阈值（0.5 = 50%）
- `target_ratio`: 压缩目标比例（0.2 = 20%）
- `protect_last_n`: 保护最后 N 条消息
- `hygiene_hard_message_limit`: 硬性消息限制

## 诊断标准

| 指标 | 正常范围 | 异常信号 |
|------|----------|----------|
| 消息数 | < 100 | > 150 |
| 输入 token | < 200K | > 500K |
| 缓存读取 token | < 5M | > 10M |
| 压缩次数 | > 0 | = 0（压缩没触发） |

## 优化方案

当压缩没触发时，调整配置：

```yaml
compression:
  threshold: 0.65       # 从 0.5 提到 0.65，上下文 65% 再压缩
  target_ratio: 0.30    # 从 0.2 提到 0.30，保留更多信息
  protect_last_n: 30    # 从 20 提到 30，保护更多最近消息
  hygiene_hard_message_limit: 200  # 从 400 降到 200，更早强制压缩
```

## 用户体验影响

当上下文过长时：
1. 模型重复回答之前的问题
2. 模型答非所问，不理解最新指令
3. 模型在同一个问题上循环

## 预防措施

1. 定期检查 session 的 token 使用量
2. 监控压缩是否正常触发
3. 及时调整压缩参数

## 诊断命令速查

```bash
# 查看 session 列表
hermes sessions list

# 查看 session 详情
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/state.db')
cursor = conn.cursor()
cursor.execute('SELECT id, message_count, input_tokens, cache_read_tokens FROM sessions ORDER BY started_at DESC LIMIT 5')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} msgs, {row[2]} input tokens, {row[3]} cache tokens')
"

# 查看压缩配置
grep -A 10 "compression:" ~/.hermes/config.yaml

# 查看压缩次数
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/state.db')
cursor = conn.cursor()
cursor.execute('SELECT session_id, COUNT(*) FROM compression_locks GROUP BY session_id')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} compressions')
"
```
