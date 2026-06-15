---
name: task-manager
title: 后台任务管理器 - 异步执行复杂任务
description: 将长时间运行的任务（编程、数据处理）放到后台执行，不阻塞当前对话，完成后通过企微通知
category: automation
trigger: 用户有耗时任务需要执行，但不想等待
dependencies: [python, psutil]
---

# 后台任务管理器

解决"任务执行期间无法聊天"的问题。

## 核心问题

当你需要执行耗时任务时：
- 生成完整的考研复习资料（10分钟）
- 处理大量数据
- 运行复杂代码

**传统方式**：等待任务完成，期间无法聊天  
**后台模式**：任务放后台，继续聊天，完成后通知

## 服务器资源

```
CPU: 4核
内存: 3.6GB (可用 2.1GB)
建议并行任务: 最多 4-6 个
```

## 任务调度策略

### 任务分配原则

| 执行者 | 职责 | 资源限制 |
|--------|------|---------|
| Claude Code (子代理) | 编程/开发/代码审查 | 单文件/591MB内存/最多2并行 |
| 我 (主代理) | 协调/验证/系统操作 | 全局管理 |

### 工作流程

```
1. 我接收任务
2. 判断是否需要编程
   → 是: 生成任务清单，调用Claude
   → 否: 我自己执行
3. Claude完成后，我检查和整合结果
4. 汇报给你
```

## 使用方式

### 方式1：单线程模式（默认）

**适用**：简单任务，需要即时结果

```
你: 帮我写个排序函数
我: → 分析 → Claude生成代码 → 我汇报结果
```

### 方式2：后台任务模式（推荐）

**适用**：复杂任务，不需要立即结果

```
你: 帮我把这份50MB的PDF转成Word
我: ✅ 任务已放后台（ID: task-001）
    你可以继续聊天，完成后会通知你

[10分钟后]
企微通知: ✅ 任务完成
我: 发结果文件给你
```

## 命令使用

### 提交后台任务

```python
from scripts.task_manager import submit_task

# 提交任务
task_id = submit_task(
    type='code',                    # 任务类型
    title='生成考研资料',           # 任务标题
    description='生成完整的Markdown并转换为Word',
    handler='claude_code',          # 执行者
    context={                       # 任务上下文
        'input_file': '/path/to/input.pdf',
        'template': 'medical_exam'
    },
    notify_on_complete=True         # 完成后通知
)

print(f"任务已提交: {task_id}")
```

### 查看任务状态

```python
from scripts.task_manager import get_task_status, list_tasks

# 查看所有任务
active_tasks = list_tasks(status='running')
print(f"运行中任务: {len(active_tasks)}")

# 查看特定任务
status = get_task_status('task-001')
print(f"状态: {status['status']}")
print(f"进度: {status['progress']}")
```

### 命令行使用

```bash
# 提交任务
python scripts/task_manager.py submit --type code --title "生成考研资料" --handler claude_code

# 查看任务列表
python scripts/task_manager.py list

# 查看任务详情
python scripts/task_manager.py status task-001

# 取消任务
python scripts/task_manager.py cancel task-001
```

## 任务类型

| 类型 | 说明 | 执行者 |
|------|------|--------|
| `code` | 代码编写/调试 | Claude Code |
| `document` | 文档生成/转换 | Claude Code + 我 |
| `data` | 数据处理 | 我 |
| `research` | 资料搜索/整理 | 我 |

## 通知方式

任务完成后会通过以下方式通知：

1. **企微消息** - 发送到指定用户
2. **文件保存** - 结果保存到 `~/.hermes/task_manager/outputs/`
3. **日志记录** - 详情记录在 `~/.hermes/task_manager/notifications/`

## 实际示例

### 示例1：后台生成Word文档

```python
# 你发送
"帮我把这份PDF转成Word，表格要保留好"

# 我执行
from scripts.task_manager import submit_task

task_id = submit_task(
    type='document',
    title='PDF转Word',
    description='将306生理学考研资料PDF转为Word，保留表格结构',
    handler='claude_code',
    context={
        'input': '/root/input.pdf',
        'output': '/root/output.docx',
        'requirements': ['保留表格', '清理空行', '统一格式']
    },
    notify_on_complete=True,
    notify_target='wecom:LuHaiTian'  # 通知目标
)

# 我回复
"✅ 任务已放后台 (ID: doc-001)
预计耗时: 5-10分钟
完成后会企微通知你"

# 任务完成后
企微: "✅ PDF转Word完成
耗时: 8分32秒
输出: /root/output.docx"
```

### 示例2：批量数据处理

```python
# 提交数据处理任务
task_id = submit_task(
    type='data',
    title='批量处理日志',
    description='分析30天的日志文件，生成统计报告',
    handler='hermes',  # 我自己执行
    context={
        'log_dir': '/var/log/myapp',
        'days': 30,
        'output_format': 'excel'
    }
)
```

## 并行限制

为了防止资源耗尽，有以下限制：

```yaml
max_concurrent_tasks: 4      # 最大并行任务数
max_claude_tasks: 2          # Claude Code 最大并行
timeout_default: 1800        # 默认超时30分钟
memory_limit_per_task: 500MB # 单任务内存限制
```

## 故障处理

### 任务失败

```
企微通知: ❌ 任务失败
任务: PDF转Word
错误: 文件格式不支持
建议: 请检查输入文件是否为有效PDF
```

### 任务超时

```
企微通知: ⏱️ 任务超时
任务: 数据处理
耗时: 30分钟（超过限制）
状态: 已自动终止
建议: 任务可能太复杂，建议拆分为小任务
```

### 资源不足

```
我: ⚠️ 当前有4个任务在运行，请等待或取消其他任务
运行中:
  - doc-001: PDF转Word (85%)
  - code-002: 代码重构 (30%)
  ...
```

## 安装

```bash
# 安装依赖
cd ~/.hermes/skills/automation/task-manager
pip install -r requirements.txt

# 初始化
cp config.example.yaml config.yaml
# 编辑 config.yaml 设置企微通知

# 启动任务调度器
python scripts/daemon.py start
```

## 配置

`config.yaml`:

```yaml
notifications:
  wecom:
    enabled: true
    default_channel: "wecom:LuHaiTian"  # 默认通知目标
  
limits:
  max_concurrent: 4
  max_claude: 2
  timeout_default: 1800
  
paths:
  outputs: "~/.hermes/task_manager/outputs"
  logs: "~/.hermes/task_manager/logs"
```

## 注意事项

1. **不要提交敏感任务** - 后台任务可能被其他管理员看到
2. **检查任务结果** - 自动化任务可能有错误，请验证结果
3. **及时清理** - 定期清理完成的旧任务，释放空间
4. **避免循环依赖** - 任务A依赖任务B时，请顺序提交

## API 参考

### TaskManager

```python
class TaskManager:
    def submit(self, task: Task) -> str
    def cancel(self, task_id: str) -> bool
    def get_status(self, task_id: str) -> TaskStatus
    def list_tasks(self, status: Optional[str] = None) -> List[Task]
```

### Task

```python
@dataclass
class Task:
    id: str
    type: TaskType
    title: str
    description: str
    handler: str  # 'claude_code' 或 'hermes'
    status: TaskStatus
    context: Dict[str, Any]
    notify_on_complete: bool
    notify_target: Optional[str]
```
