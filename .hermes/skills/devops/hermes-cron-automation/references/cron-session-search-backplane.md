# 使用 session_search 作为 Cron 跨次数据存储

## 问题

Agent 模式 cron 任务中 `memory` 工具不可用，但很多任务需要跨次跟踪状态（如学习进度、累计计数、上次处理位置）。每次运行都从零开始，无法推进。

## 方案：用 session_search 替代 memory

`session_search` 在 cron agent 模式下正常可用（搜索 Hermes 会话 SQLite DB），且每次 cron 运行都会创建一个新会话——之前的输出就是永久的"存储"。

## 模式 1：查找上次进度

```python
# 在 cron prompt 中写：
"""
通过 session_search 查找之前的进度记录：
1. session_search(query="关键字1 OR 关键字2", sort="newest", limit=3)
2. 从结果中找到上一次 cron 的输出
3. 注意 bookend_end 包含上次的完整输出
4. 确认上次做了什么，确定这次的起始状态
"""
```

## 模式 2：用 job id 直接查找

每个 cron 任务都有一个 job ID（如 `5f54611e1294`）。每次运行产生的会话 ID 格式为 `cron_{job_id}_{timestamp}`。可以用 job ID 的前缀找到所有历史运行：

```python
session_search(query="cron_5f54611e1294", sort="newest", limit=5)
```

## 模式 3：读 jobs.json 获取 repeat 计数

`~/.hermes/cron/jobs.json` 包含每个 cron 任务的完整状态，包括 `repeat.completed`（已运行次数）。这个文件在任何 agent 模式下都可读：

```python
import json
with open('/root/.hermes/cron/jobs.json') as f:
    data = json.load(f)
for job in data['jobs']:
    if job['id'] == '5f54611e1294':
        completed = job['repeat']['completed']
        total = job['repeat']['times']
        # completed/total 就是当前进度
```

## 模式 4：用文件系统记录状态

如果任务需要写入持久状态（而非只读），可以在 cron prompt 中指示 agent 用 `write_file` 写入状态文件，下次运行时用 `read_file` 读取：

```markdown
# 在 cron prompt 中：
1. 读取 /root/.hermes/cron/data/任务名/state.json 获取上次状态
2. ...执行任务...
3. 用 write_file 更新 /root/.hermes/cron/data/任务名/state.json
```

注意：使用前需要创建目录 `mkdir -p /root/.hermes/cron/data/任务名/`

## 总结

| 存储方式 | 读 | 写 | 适合场景 |
|---------|----|----|---------|
| session_search | ✅ 查上次输出 | ❌ 只读 | 查找历史、确认进度 |
| jobs.json | ✅ 查 repeat 计数 | ❌ 只读 | 获取任务元数据 |
| 文件系统 | ✅ read_file | ✅ write_file | 跨次持久化状态 |

推荐：**文件系统存储实际进度，session_search 做历史回溯**，两者互补。
