# 上下文压缩诊断指南

## 场景

AI 重复回答、答非所问、不按用户最新指令执行。怀疑是上下文膨胀导致模型看不清最新消息。

## 诊断流程

### 1. 查 Session 统计

```python
# 通过 Hermes state.db 查看
session_id = '...'
# 输入 token = 累计发送给模型的 token
# 缓存读取 token = 从 prompt cache 读的
# 如果输入 token 很大（50万+）但压缩次数=0 → 压缩没触发
```

关键指标：
| 指标 | 正常 | 异常 |
|------|------|------|
| 消息数 | < 100 | > 150 |
| 输入 token | < 100K | > 300K |
| 压缩次数 | ≥ 1 | **0** |
| 缓存读取 / 输入 | < 10x | > 30x（说明每次请求都在重发历史）|

### 2. 查压缩配置

```yaml
compression:
  enabled: true           # 必须 true
  threshold: 0.65         # 上下文使用到 65% 时压缩
  target_ratio: 0.30      # 压缩后保留 30%
  protect_last_n: 30      # 保护最近 30 条消息
  protect_first_n: 5      # 保护前 5 条
  hygiene_hard_message_limit: 200  # 200 条消息强制压缩
```

### 3. 查 `model.context_length`

```yaml
model:
  context_length: 131072  # 必须显式设置！默认 256K 可能导致阈值计算错误
```

**这是最常见的问题**——没有设置 `context_length`，压缩器不知道上下文多长算「满」。

### 4. 查压缩触发逻辑

压缩在 `agent/conversation_loop.py` 约 3812 行触发：

```python
if agent.compression_enabled and _compressor.should_compress(_real_tokens):
```

其中 `_real_tokens` 来自 API 响应的 `usage.prompt_tokens`。**如果 API 提供商不返回精确用量（国产模型常见），`last_prompt_tokens` 保持 0，fallback 用 `estimate_request_tokens_rough()` 估算——估算可能偏小，导致压缩跳过。**

### 5. 验证压缩是否实际工作

```bash
# 查压缩锁表（压缩行为记录）
sqlite3 ~/.hermes/state.db "SELECT session_id, holder, acquired_at FROM compression_locks"

# 查 session 压缩次数
sqlite3 ~/.hermes/state.db "SELECT id, message_count, input_tokens FROM sessions WHERE input_tokens > 100000 ORDER BY started_at DESC LIMIT 5"
```

## 修复方案优先级

| 优先级 | 操作 | 原因 |
|:---:|:---|:---|
| 1 | 设置 `model.context_length` | 压缩器才能算明白阈值 |
| 2 | 降低 `hygiene_hard_message_limit` 到 200 | 防消息条数过多不压缩 |
| 3 | 提高 `threshold` 到 0.65-0.75 | 更早压缩 |
| 4 | 提高 `protect_last_n` 到 30 | 保护更多最近消息 |
| 5 | 提高 `target_ratio` 到 0.30 | 压缩后保留更多上下文 |

## 根源排查链（Hermes 源码）

```
conversation_loop.py:3812  should_compress(_real_tokens)
  → _real_tokens 来自 last_prompt_tokens
    → last_prompt_tokens 由 update_from_response() 从 API usage 设置
    → 如果 API 不返回 usage.prompt_tokens → 走 estimate_request_tokens_rough()
      → 估算偏小 → should_compress() 返回 False → 不压缩 → 上下文膨胀

turn_context.py:249-252  预检压缩条件
  → len(messages) > protect_first_n + protect_last_n + 1

context_compressor.py:785-805  should_compress()
  → tokens < threshold_tokens → 不压缩
    → threshold_tokens = max(context_length × threshold_percent, MINIMUM_CONTEXT_LENGTH=64000)

context_engine.py:225-226  阈值计算
  → context_length × threshold_percent
  → 如果 context_length=0（未设置）→ 用 model_context_length 的默认 fallback 256K
```

## 常见陷阱

| 陷阱 | 表现 | 原因 |
|:---|:---|:---|
| `model.context_length` 未设置 | 压缩不触发 | 默认 256K + 50% = 128K 阈值，但 provider 实际用量小 → 永远达不到 |
| MiMo 不返回 usage | 压缩不触发 | `last_prompt_tokens` 保持 0，fallback 估算偏小 |
| 反复网关重启 | session 到 150 条但压缩 0 次 | 每次中断重置状态，压缩器来不及触发 |
| 只改 skill 不改代码 | 文档说过修了但实际没修 | 修复必须应用到实际 `.py` 文件 + 清 pycache 重启 |
