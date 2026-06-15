# Cron 调试方法

当 cron 任务看起来没有按时触发时，按此方法链排查。

## 排查链条（从快到慢）

### 第0步：确认任务是否存在

```python
cronjob(action='list')
```

关注字段：`next_run_at`、`last_run_at`、`last_status`。

**⚠️ 关键陷阱：`next_run_at` 显示的是下次执行时间，不是本次**

调度器使用 `advance_next_run` 机制——在任务**执行前**就把 `next_run_at` 推进到下一次了（at-most-once 语义，防止崩溃后重复触发）。所以不要因为 `next_run_at` 显示的是未来的时间就断定本次没触发。

### 第1步：检查 jobs.json 原始数据

```bash
cat ~/.hermes/cron/jobs.json
```

查看原始字段（不被工具格式化过的）：
- `next_run_at` — 精确的 ISO 时间戳
- `last_run_at` — 上次执行时间
- `last_status` — "ok" 或 "error"
- `created_at` — 创建时间
- `schedule.kind` — cron/interval/once

### 第2步：查 agent.log 确认任务是否启动

```bash
grep "Running job '任务名'\|4cf04b710f5d\|任务ID" ~/.hermes/logs/agent.log
```

信号：
- `Running job 'XXXX'` → 调度器已触发
- 该行的时间就是实际触发时间
- 如果看到这个日志但用户没收到结果，说明**执行阶段**出问题（API 卡顿、内容过滤等），不是调度问题

### 第3步：查 agent.log 看执行过程

```bash
grep "cron_[job_id]\|stale\|api_call\|completed\|delivered" ~/.hermes/logs/agent.log
```

重点关注：
- `Stream stale for 180s` → API 请求卡住超时。cron 任务会恢复重试
- `Turn ended: reason=text_response` → 执行完成
- `delivered to weixin:xxxx via live adapter` → 已投递

### 第4步：查 gateway.log 看调度器状态

```bash
grep "tick\|Cron ticker\|get_due\|No jobs due" ~/.hermes/logs/gateway.log
```

信号：
- `Cron ticker started (interval=60s)` → 调度器在运行
- 如果最后一条 Cron ticker 日志是几个小时前的，说明网关可能重启过
- 静默期间没有任何 tick 日志是正常的——调度器每60秒 tick 一次，但只有有任务时才打日志

### 第5步：查输出目录

```bash
ls -la ~/.hermes/cron/output/<job_id>/
```

每次运行会生成一个 `YYYY-MM-DD_HH-MM-SS.md` 文件。文件的存在说明任务确实执行了。

## 常见误判

| 现象 | 真正原因 |
|------|---------|
| next_run_at 显示未来时间，以为没触发 | `advance_next_run` 已提前推进，任务正在执行中 |
| cron list 显示 job 存在但没收到消息 | 可能是 API 卡顿（stale stream 超时）导致延迟，等1-3分钟 |
| 手动 `cronjob(action='run')` 后马上出了结果 | 其实原始任务也在同时运行，最终可能收到两条 |
| 6:00 的任务 6:02 还没到 | 检查 agent.log 是否有 `Running job` + `stale`，可能是 API 慢 |

## advance_next_run 机制详解

`scheduler.py` 中的 `tick()` 函数：

```python
# 步骤1：获取到期任务
due_jobs = get_due_jobs()

# 步骤2：对每个到期任务，先推进下次时间（at-most-once）
for job in due_jobs:
    advance_next_run(job["id"])

# 步骤3：再执行任务
for job in due_jobs:
    run_job(job)
```

`advance_next_run` 会：
1. 取当前时间作为 `last_run_at`
2. 用 `croniter` 计算从 `last_run_at` 之后的下一次时间
3. 写入 `next_run_at`
4. 所以你在执行过程中查 list，看到的已经是下次的时间了

## "Stale stream" 超时

当 DeepSeek（或其他 API）响应慢时，agent 会打：
```
Stream stale for 180s (threshold 180s) — no chunks received. Killing connection.
```

这时 API 连接被杀死，agent 会自动重试。这会导致 cron 任务看起来"卡了3分钟"，但最终会完成。

## 最简调试流程

```python
# 1. 查列表
cronjob(action='list')

# 2. 查原始数据
import json; print(json.dumps(jobs, indent=2))

# 3. 查日志
grep "Running job\|stale\|delivered" ~/.hermes/logs/agent.log
```

## 不要犯我的错误

今天（2026-06-04）我犯了两个错误：
1. 看到 `next_run_at = 2026-06-05` 就断定 6:00 没触发，没意识到这是执行前推进的
2. 没先查 agent.log 确认 `Running job` 日志，就直接手动触发了任务
3. 结果原始任务和手动触发同时运行，用户可能收到两条报告

**正确做法：先查 agent.log 确认是否已触发，再决定是否需要手动干预。**
