# 文件系统看门狗 — 监测目录变化并自动同步

配合 `no_agent=True` cron 使用，零 token 消耗。

## 适用场景

- 共享目录文件变化检测（Hermes ↔ OpenClaw 等跨 agent 同步）
- 配置文件热更新（监控特定目录，新文件出现时执行操作）
- 日志目录变化通知

## 脚本模板

```bash
#!/bin/bash
# watch_shared_dir.sh — 监测目录变化，零 token 消耗
# 配合 cronjob no_agent=True 使用

SHARED_DIR="/path/to/watch"
STATE_FILE="/path/to/.watch_state"

# 生成当前目录状态指纹（统计新/修改的文件数）
current_hash=$(find "$SHARED_DIR" -type f -name "*.md" -newer "$STATE_FILE" 2>/dev/null | wc -l)

# 首次运行
if [ ! -f "$STATE_FILE" ]; then
    date +%s > "$STATE_FILE"
    exit 0
fi

# 无变化 → 静默退出
if [ "$current_hash" -eq 0 ]; then
    exit 0
fi

# 有变化 → 输出报告（将被 cron 投递到用户）
echo "📥 检测到新内容："
find "$SHARED_DIR" -type f -name "*.md" -newer "$STATE_FILE" | while read f; do
    echo "  📄 ${f#$SHARED_DIR/}"
done

# 按目录分类报告
new_tasks=$(find "$SHARED_DIR/tasks" -type f -name "*.md" -newer "$STATE_FILE" 2>/dev/null | wc -l)
new_memory=$(find "$SHARED_DIR/memory" -type f -name "*.md" -newer "$STATE_FILE" 2>/dev/null | wc -l)
[ "$new_tasks" -gt 0 ] && echo "  📋 新任务: $new_tasks 个"
[ "$new_memory" -gt 0 ] && echo "  🧠 新记忆: $new_memory 个"

# 执行同步操作
if [ -f "$SHARED_DIR/sync.sh" ]; then
    bash "$SHARED_DIR/sync.sh" 2>/dev/null
fi

# 更新时间戳
date +%s > "$STATE_FILE"
```

## 关键设计要点

| 要素 | 说明 |
|------|------|
| **状态文件** | 记录上次检查时间，后续用 `-newer` 比较，无需额外计算 |
| **首次运行静默** | 初始化状态文件但不输出，避免每次部署都产生空通知 |
| **无变化静默** | `exit 0` 无输出 = 不投递，利用空 stdout 特性 |
| **有变化才出声** | 检测到新文件才输出，输出即投递到用户 |
| **目录分类** | 区分 tasks/memory/skills，用户一眼看出哪里变了 |

## Cron 配置

```python
cronjob(
    action='create',
    name='共享目录看门狗',
    schedule='every 5m',       # 每5分钟检查一次（频率根据需求调整）
    no_agent=True,             # 零 token 消耗
    script='watch_shared_dir.sh'
)
```
