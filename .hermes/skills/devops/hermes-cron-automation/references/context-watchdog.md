# 上下文看门狗 (Context Watchdog)

## 功能
检测当前活跃会话的 token 用量，超阈值时提醒用户开新会话。

## 脚本位置
`~/.hermes/scripts/context_watchdog.py`

## cron 配置
```
job_id: b360bf33e3bc
name: 📊 上下文看门狗
schedule: every 15m
no_agent: true
script: context_watchdog.py
```

## 阈值设置
- ⚠️ 注意: 400,000 tokens
- 🔴 严重: 800,000 tokens
- 冷却时间: 1小时（避免重复提醒）

## 数据源
查询 `~/.hermes/state.db` 的 `sessions` 表，筛选 `ended_at IS NULL` 的活跃会话，累加 `input_tokens + output_tokens`。

## 扩展点
- 添加新的阈值级别
- 修改提醒频率（调整 cron schedule）
- 接入其他提醒通道（如企微消息）
