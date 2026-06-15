---
name: hermes-cron-automation
description: 用 Hermes cron 系统创建自动化定时任务，支持 no_agent 脚本（零 token 消耗）和 agent 驱动任务
category: devops
trigger: 用户需要设置定时任务（余额检查、服务监控、数据采集、定期报告等），需要从旧系统（OpenClaw）迁移 cron 任务到 Hermes
---

# Hermes Cron 自动化

用 Hermes 内置的 cron 系统创建定时任务。支持两种模式：

| 模式 | token 消耗 | 适用场景 |
|------|-----------|---------|
| `no_agent=True` | **零消耗** | 纯脚本任务（余额检查、端口检测、日志扫描、API 轮询） |
| `no_agent=False`（默认） | 每次运行消耗 token | 需要 LLM 推理的任务（总结、翻译、智能分析） |

## 文件结构

```
~/.hermes/scripts/          # no_agent 脚本存放目录
├── check_deepseek_balance.py
└── hermes_watchdog.py
```

脚本路径在 cron 创建时用**相对文件名**，系统自动补全到 `~/.hermes/scripts/`。

## no_agent 模式（推荐用于数据型任务）

### 脚本编写规则

1. **自包含** — 脚本自己加载环境变量、API Key，不依赖外部传入
2. **输出即消息** — stdout 的全部内容会被投递给用户。只输出你想让用户看到的内容
3. **静默模式** — 正常运行时输出空内容，异常时才输出消息（监控/看门狗的典型模式）
4. **不要交互** — 脚本运行在无用户环境，不能请求输入
5. **依赖检查** — 脚本运行前确保所有 Python 模块已安装。如果脚本依赖第三方库（如 `akshare`、`pandas`），需要在系统环境中安装：`python3 -m pip install <package>`。注意：此系统上 `pip` 单独不可用，必须用 `python3 -m pip`

### 脚本模板：常规报告型

```python
#!/usr/bin/env python3
"""脚本描述"""
import json, os, sys
from urllib.request import Request, urlopen

# 从 .env 加载密钥（no_agent 脚本需自行加载环境）
env_path = '/root/.hermes/.env'
api_key = ''
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith('KEY_NAME=***                api_key = line.strip().split('=', 1)[1]
                break

# 调用 API、计算结果
# print() 的内容就是投递到用户微信的消息
print(f"📊 日报标题")
print(f"━━━━━━━━━━━━━")
print(f"数据项: 值")
```

### 重要：no_agent 模式的投递行为

- **空 stdout = 静默** — 脚本没有任何 stdout 输出时，cron **不会**向用户投递任何消息。看门狗利用这个特性：正常时闭嘴，异常时才输出。
- **非空 stdout = 投递** — 脚本打印的任何内容都会原样发送到用户的消息通道。
- **exit code ≠ 投递** — 脚本退出码不影响投递行为，只有 stdout 决定是否投递。

### 脚本模板：看门狗型（静默模式）

```python
#!/usr/bin/env python3
"""监控脚本，正常时无输出，异常时报错"""
import subprocess, os, json, time
from datetime import datetime

LOCK = '/tmp/watchdog.lock'

def get_lock():
    now = time.time()
    if os.path.exists(LOCK):
        try:
            with open(LOCK) as f:
                data = json.load(f)
            if now - data.get('ts', 0) > 1800:
                os.remove(LOCK)
            else:
                return False
        except:
            os.remove(LOCK)
    with open(LOCK, 'w') as f:
        json.dump({'pid': os.getpid(), 'ts': now}, f)
    return True

def release_lock():
    try:
        if os.path.exists(LOCK): os.remove(LOCK)
    except: pass

def main():
    if not get_lock(): return  # 已有实例运行
    try:
        # 检查服务状态
        # 如果一切正常，直接 return（静默）
        # 如果有问题，print() 输出异常信息
        pass
    finally:
        release_lock()

if __name__ == '__main__':
    main()
```

## 创建 cron 任务

通过 `cronjob` 工具创建：

```python
# no_agent 模式：脚本直接输出消息
cronjob(
    action='create',
    name='任务名称',
    schedule='0 9 * * *',      # crontab 格式（东八区）
    no_agent=True,
    script='check_deepseek_balance.py'   # 仅文件名，必须放在 ~/.hermes/scripts/
)

# agent 模式：由 LLM 处理
cronjob(
    action='create',
    name='任务名称',
    schedule='every 20m',       # 自然语言格式
    prompt='任务描述...',
    skills=['skill1', 'skill2']  # 可选：预加载技能
)
```

### schedule 格式

| 格式 | 示例 | 说明 |
|------|------|------|
| ISO 时间 | `2026-06-04T09:00:00` | 单次定时 |
| Crontab | `0 9 * * *` | 标准 cron（东八区） |
| 自然语言 | `every 20m` | 每20分钟 |
| 自然语言 | `every 2h` | 每2小时 |
| 自然语言 | `0 9 * * 1-5` | 工作日 09:00 |

### 一次性提醒的日期确认（重要）

创建一次性提醒（schedule 用 ISO 时间戳）时，**必须先确认具体日期**，不能自行假设。

**错误做法：** 用户说"提醒我周日做某事"，直接用最近的周日创建，不确认是哪个周日。

**正确做法：** 先问清楚是哪一天，例如：
> 你是指今天（6月5日）还是下周日（6月7日）？

用户可能在测试你是否仔细。日期含糊时必须澄清。

### 测试脚本

创建 cron 前先手动运行脚本验证：

```bash
python3 ~/.hermes/scripts/check_deepseek_balance.py
```

### 查看和管理

```python
cronjob(action='list')              # 查看所有任务
cronjob(action='pause', job_id='')  # 暂停
cronjob(action='resume', job_id='') # 恢复
cronjob(action='remove', job_id='') # 删除（先 list 获取 id）
cronjob(action='run', job_id='')    # 立即执行一次
```

### 变更接收者名单（安全策略）

滚动上线时先只发给自己确认，再改为全员：

```python
# 阶段1：只发给自己测试
RECIPIENTS = ['KuHai']  # 先只发自己确认格式

# 阶段2：确认为后再改为所有人
RECIPIENTS = ['KuHai', 'UserB', 'UserC']
```

通过修改脚本中的接收者列表，no_agent 模式的下次运行就会自动采用新名单。无需暂停/重启 cron 任务。

## 从旧系统（如 OpenClaw）迁移 cron 任务

迁移步骤：

1. **看旧脚本** — 看原系统中用的是什么脚本和逻辑
2. **判断模式** — 纯数据操作 → no_agent；需要分析推理 → agent 模式
3. **改看门狗脚本** — 旧看门狗可能监控 `openclaw-gateway.service`，改成监控 Hermes 的 PM2 进程
4. **测试** — 先手动跑一遍脚本确认输出正确
5. **创建 cron** — 用 `cronjob` 工具创建

### Hermes PM2 服务检查

```python
import subprocess, json

def pm2_status(name):
    """检查 PM2 进程状态"""
    r = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True, timeout=10)
    processes = json.loads(r.stdout)
    for p in processes:
        if p.get('name') == name:
            status = p.get('pm2_env', {}).get('status', '')
            return status == 'online', p.get('pid', '')
    return False, ''
```

Hermes 的 PM2 服务名：
- `hermes-gateway` — Gateway（消息通道/Webhook）
- `hermes-dashboard` — Web Dashboard

## 多用户推送：隐私隔离策略

当给多个用户推送同一类报告时，注意**每个用户只能看到自己的私有数据**（持仓、消费记录等）。

### 安全隔离模式

**核心原则：生成一次，按用户裁剪。** 不要为每个用户分别跑完整的数据采集流程。

```
[脚本]
  ├─ 1. 跑一次 main.py 生成完整报告（含私有数据）
  ├─ 2. 对 owner 直接用完整报告
  ├─ 3. 对其他用户，用正则/字符串去掉私有段落（零额外 subprocess 开销）
  └─ 4. 分别推送给不同用户
```

### ⚠️ 脚本超时配置（重要）

Hermes cron 的 `no_agent` 脚本默认超时 **120 秒**，可通过 `config.yaml` 配置：

```yaml
cron:
  script_timeout_seconds: 300  # 建议改为 300 秒（5分钟）
```

修改后需重启网关生效。数据抓取类脚本（akshare 等）网络抖动时可能需要更长时间。

**典型超时陷阱：** 循环内对每个用户分别调用 `subprocess.run(['python3', 'main.py', ...])`，每次 ~50s，3 个用户 = 150s，直接超时。

**正确做法（skip_official 模式）：** 只跑一次 `main.py --official` 生成完整报告，其他用户通过 `skip_official=True` 跳过重复采集，用 `--report --user` 复用数据（<1s）。

```python
def generate_report(user_id='lulu', skip_official=False):
    if not skip_official:
        subprocess.run(['python3', 'main.py', '--official'], ...)
    if user_id != 'lulu':
        subprocess.run(['python3', 'main.py', '--report', '--user', user_id], ...)
    # 读取报告文件返回

# 主流程
lulu_report = generate_report('lulu')           # 跑一次 official（~50s）
other_report = generate_report('UserB', skip_official=True)  # 跳过 official（<1s）
```

### 实现方式：生成一次 + 文本裁剪

```python
import re

def generate_report():
    """只跑一次 main.py，返回完整报告（含持仓）"""
    try:
        subprocess.run(['python3', 'main.py', '--official'],
            cwd=STOCK_DIR, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        print("⚠️ 报告生成超时，尝试读取已有数据")
    except Exception as e:
        print(f"⚠️ 报告生成异常: {e}")

    files = sorted(glob.glob(os.path.join(REPORT_DIR, 'report_*.md')), reverse=True)
    if files:
        with open(files[0], encoding='utf-8') as f:
            return f.read().strip()
    return '⚠️ 报告生成失败'


def strip_portfolio(report):
    """去掉报告中的持仓段落（非 owner 不需要看）"""
    pattern = r'──────────────────────────────\n📋 持仓.*?(?=──────────────────────────────|$)'
    return re.sub(pattern, '', report, flags=re.DOTALL).strip()


def main():
    # 只跑一次 main.py
    full_report = generate_report()

    for uid in RECIPIENTS:
        if uid == 'KuHai':
            report = full_report          # owner 看完整持仓
        else:
            report = strip_portfolio(full_report)  # 其他人去掉持仓
        msg = f"📊 报告\n{report}"
        send_wecom(uid, msg)
```

### 常见坑

- ❌ **把owner的完整报告发给所有人** — 持仓/余额等私人信息会泄露
- ❌ **测试时发给多人** — 用户明确说过"测试你发给他们干啥，只要发给我"。测试阶段 RECIPIENTS 只放自己，确认无误后再加人
- ❌ **循环内对每个用户分别跑 subprocess** — 每次 ~50s × N 用户 = 超过 cron 超时。应只跑一次 `main.py --official`，其他用户用 `skip_official=True` + `--report --user` 复用数据
- ❌ **为每个用户分别采集一次数据** — 浪费API配额和时间。应只采集一次，然后复用数据生成不同版本
- ❌ **使用`capture_output`直接取stdout** — 如果子进程包含调试日志(`[WARN]`、`[OK]`、进度条)，会污染消息内容。应改为读取报告文件
- ❌ **用户ID映射错误** — 脚本中判断`if uid == 'lulu'`但接收者列表是`['KuHai', ...]`，导致owner收不到持仓报告。应使用实际的用户ID（如`KuHai`）进行判断
- ❌ **忽略 cron 120s 硬超时** — `no_agent` 脚本总运行时间（数据采集 + 天气 + 发送）必须 <120s，否则被强制中断。用 `time python3 script.py` 测试实际耗时
- ✅ **数据只采集一次，报告按用户分别生成** — 用 `skip_official=True` 模式，非 owner 用户跳过 `main.py --official`
- ✅ **子进程超时设为300s（5分钟）** — 股市API在收盘后/开盘前高峰期响应慢，120s不够
- ✅ **cron 超时配置为 300s** — `config.yaml` → `cron.script_timeout_seconds: 300`，修改后重启网关生效
- ✅ **读文件代替抓stdout** — 避免调试日志混入最终消息
- ✅ **用户ID判断使用实际ID** — 在企微等平台中，用户ID可能是`KuHai`而不是`lulu`，需根据实际接收者列表调整判断逻辑
- ✅ **检查连续报告是否一致** — 如果晨/收盘报告连续多天内容完全相同，说明数据采集失败（如缺少`akshare`模块），脚本在读取旧文件而非生成新数据。排查：`python3 -c "import akshare"` 验证模块是否可用

### 模式：生成 + 推送

```
[no_agent 脚本]
    ├─ 1. 生成数据（运行分析、查询 API）
    ├─ 2. 推送外部（通过企微 API 发消息）
    └─ 3. 输出日志（可选，投递到 Hermes 消息通道）
```

### 示例结构

```python
# ~/.hermes/scripts/stock_morning_report.py
import subprocess, json, glob, os, re

STOCK_DIR = '/path/to/project'
WECOM_SCRIPT = os.path.join(STOCK_DIR, 'send_wecom.py')
REPORT_DIR = os.path.join(STOCK_DIR, 'reports')

RECIPIENTS = ['UserA', 'UserB', 'UserC']

def generate_report():
    """只跑一次 main.py，返回完整报告（含持仓）"""
    try:
        subprocess.run(['python3', 'main.py', '--official'],
            cwd=STOCK_DIR, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        pass  # 超时也尝试读已有文件
    files = sorted(glob.glob(os.path.join(REPORT_DIR, 'report_*.md')), reverse=True)
    if files:
        with open(files[0], encoding='utf-8') as f:
            return f.read().strip()
    return '⚠️ 报告生成失败'

def strip_portfolio(report):
    """去掉持仓段落（非 owner 不需要看）"""
    pattern = r'──────────────────────────────\n📋 持仓.*?(?=──────────────────────────────|$)'
    return re.sub(pattern, '', report, flags=re.DOTALL).strip()

def send_wecom(uid, msg):
    # 调用企微 API（见 wecom-message-push 技能）
    ...

def main():
    today = datetime.now().strftime('%Y-%m-%d')
    # 只跑一次 main.py
    full_report = generate_report()

    for uid in RECIPIENTS:
        if uid == 'UserA':
            report = full_report          # owner 看完整持仓
        else:
            report = strip_portfolio(full_report)  # 其他人去掉持仓
        msg = f"📊 {today}晨报\n━━━━━━━━━━━\n\n{report}"
        send_wecom(uid, msg)
    print(f"✅ 已发送: {', '.join(RECIPIENTS)}")
```

**要点说明：**
- **main.py 只跑一次** — 其他用户用正则裁剪，零额外 subprocess 开销（<1s vs 每次 ~50s）
- **120s 超时预算** — 数据采集 ~50s + 天气 ~10s + 发送 ~30s ≈ 90s，留 30s 余量
- **读文件代替抓stdout** — 避免子进程的调试日志污染最终消息
- **子进程异常用try/except兜底** — 超时或异常时不崩溃，尝试读已有的报告文件
- **读文件代替抓stdout** — 避免子进程的调试日志（`[WARN]`, `[OK]`, 进度条）污染最终消息
- **多用户各自生成** — 先用`--official`采集一次数据，其他人用`--report --user <name>`复用数据生成不同版本（零额外API调用）
- **子进程异常用try/except兜底** — 超时或异常时不崩溃，尝试读已有的报告文件

### 投递架构决策

| 场景 | 推荐方式 | 原因 |
|------|---------|------|
| 仅发到微信/企微/Telegram | **脚本内直接调用 API** | 零 token 消耗，可靠 |
| 先发给自己 + 手动转发 | **cron deliver 到微信** | 利用 Hermes 投递通道 |
| 发给多人 | **脚本内批量调用 API** | 避免重复投递，可统一处理失败 |
| 需要 LLM 格式化后再发 | **agent 模式** | 用 LLM 润色报告内容 |

相关技能：`wecom-message-push` — 企微消息推送的完整实现。

相关参考：`references/interactive-api-failover.md` — 模型 API 健康检测 + 企微交互式故障切换看门狗。`references/cron-script-optimization-patterns.md` — skip_official 模式、文本裁剪、数据源超时处理。

## 文件系统看门狗

用于监测目录文件变化并自动同步。见 `references/directory-watchdog-pattern.md`。

适用场景：跨 agent 共享目录同步、配置文件热更新监控。零 token 消耗。

## Agent 任务中的多层模型策略

如果 cron 任务使用 agent 模式，且需要处理复杂任务（如生成分析报告、代码审查），可以参考**多层模型委托**策略：
- 主 agent 用便宜模型处理日常对话和简单 cron 报告
- 子 agent（通过 `delegate_task`）用更强模型处理复杂子任务
- 配置方式见 `references/token-cost-awareness.md` → 成本优化策略：多层模型委托

## Agent 驱动的每日总结报告

除了纯脚本任务，cron 也适合运行 agent 模式的任务，例如每日总结前一天的会话活动。

### 创建方式

```python
cronjob(
    action='create',
    name='每日总结报告',
    schedule='0 8 * * *',      # 每天早上8点（东八区）
    prompt='''今天是 {{now}}。请生成一份昨天的工作总结报告。

重要：{{now}} 会被替换为当前日期时间，据此推算昨天的日期范围。如果 {{now}} 未被替换，请根据当前实际时间推算。

步骤如下：
1. 根据当前时间推算昨天的确切日期（年-月-日）
2. 用 session_search 查找昨天的会话记录
3. 如果昨天没有任何活动，输出"昨天没有活动记录"并结束
4. 如有活动，简洁总结主要工作、关键决策、未完成事项
5. 报告标题必须写明正确的日期和星期（不要把前一天的内容归错日期）
6. 跳过没有实际活动的日子，不发空报告
''',
    deliver='origin'            # 自动投递到当前聊天
)
```

### 关键设置

- `schedule='0 8 * * *'` 用 crontab 格式精确控时
- 自然语言 schedule（如 `every 20m`）适合看门狗，定点的报告用 crontab
- `deliver='origin'` 自动投递到用户当前聊天通道（微信等）
- `prompt` 必须自包含，cron 运行在无上下文的环境中

### 执行时的标准工作流（以每日报告为例）

当 cron 任务实际触发时，按以下步骤执行：

1. **确定日期范围** — 用 `date` 确认当前时间，推算前一天
2. **查找昨天的会话** — 用 `session_search(query="2026-06-03 OR ...")` 检索前一天的会话活动
3. **判断是否有活动** — 若无任何会话，输出 `[SILENT]` 并结束（不发送空报告）
4. **获取 token 统计** — `hermes insights --days 1` 获取精确的输入/输出 token 数
5. **检查余额** — 从 `.env` 加载 API Key 后调 DeepSeek 余额 API
6. **生成报告** — 按约定格式（概况 → Token → 余额 → 待办）用中文输出

### 无活动时的 [SILENT] 模式

如果 cron 触发后发现前一天没有活动会话，直接输出 `[SILENT]` 并结束。Hermes cron 系统识别到仅输出 `[SILENT]` 时会**静默跳过，不投递任何消息给用户**。

```python
# 没有活动时
if not sessions:
    print("[SILENT]")
    exit(0)
```

### 报告格式约定

以每日总结报告为例的标准格式（全部用中文）。**数学计算必须逐步列出，不能跳步。**

```markdown
【昨日概况】
- 会话次数：X 次
- 主要工作：列出做了什么

【Token 消耗】

    Input tokens:      X,XXX,XXX
    Output tokens:     X,XXX,XXX
    缓存命中 tokens:  X,XXX,XXX

    ① Input cache miss:  X.XXM × ¥1.02 = ¥X.XX
    ② Input cache hit:   X.XXM × ¥0.02 = ¥X.XX
    ③ Output:            X.XXM × ¥2.04 = ¥X.XX
    ─────────────────────────────────────
    合计: ¥X.XX

【余额】
- DeepSeek 余额：X.XX CNY ✅/🔴

【待办】
- 未完成事项列表；无则写"无"
```

**关键规则：涉及数字计算必须列出每一步，不能只给最终结果。**
用户明确要求了此格式，违反会引发纠正。

### 注入脚本上下文（script 参数）

agent-mode cron 任务支持设置 `script` 参数。脚本在 LLM prompt
执行前运行，其 stdout 输出自动注入到 prompt 的 `[SCRIPT OUTPUT]` 区块：

### 陷阱：{{now}} 模板变量与日期准确度

Cron prompt 中的 `{{now}}` 会被替换为当前日期时间，但如果 prompt 只写"查找昨天的会话"而没有强调根据 `{{now}}` 推算日期，agent 可能搞错日期范围，把前天的会话归到昨天。

**修复模式**：在 prompt 中明确要求：
1. "根据 {{now}} 计算出昨天的日期"
2. "报告标题必须写明正确的日期和星期"
3. 不要用模糊描述，给具体的日期计算指令

```python
cronjob(
    action='create',
    name='每日总结报告',
    schedule='0 6 * * *',
    prompt='''基于上面的 [SCRIPT OUTPUT] 生成报告...''',
    script='calculate_token_cost.py',   # 预跑脚本，输出作为上下文
)
```

脚本输出的全部内容直接插入 LLM prompt 的开头，LLM 在生成回复时可以引用。
适合：数据采集、费用计算、状态检查等有固定输出格式的前置任务。

注意：script 参数和 no_agent 参数互斥。有 script 但 no_agent=False 时，
脚本先跑 → prompt 后执行（agent 模式）。

```
【昨日概况】
- 会话次数：X 次
- 主要工作：列出做了什么

【Token 消耗】
- Input：X tokens
- Output：X tokens
- 合计约 X 万 token
- ⚠️ 超过 50 万时加此标记

【余额】
- DeepSeek 余额：X.XX CNY ✅/🔴

【待办】
- 未完成事项列表；无则写"无"
```

### 常见坑与边界情况

以下是在实际运行每日总结报告时发现的问题：

#### 重要：Agent 模式 cron 中不可用的工具

当编写 agent 模式 cron 的 prompt 时，必须注意以下工具在 cron 环境中**不可用**或被限制：

| 工具 | 状态 | 原因 |
|------|------|------|
| `memory` / `fact_store` | ❌ 不可用 | cron 上下文无持久化记忆系统 |
| `send_message` | ❌ 不可用 | 投递由 cron 系统自动处理 |
| `clarify` | ❌ 不可用 | cron 无用户可交互 |
| `execute_code` | ❌ 不可用 | 安全限制（leaf agent 权限） |

**常见陷阱：自指式 prompt**

```markdown
❌ 错误写法（cron prompt 中）：
先查 memory 获取 Linux 学习进度...
学完后，更新 memory 里的 Linux学习进度...
```
→ 运行时报错 `"Memory is not available."`，数据查不到也存不上。

✅ 正确做法：使用 `session_search` 替代 memory
```
先通过 session_search 查找历史记录中的学习进度...
```

**session_search 作为 cron 持久化数据存储**

`session_search()` 工具在 cron agent 模式下**正常可用**。它搜索的是 Hermes 会话数据库（SQLite FTS5），可以：
- 查询关键字找出以前的 cron 输出
- 用 `bookend_end` 获取上次执行的结果
- 用 `sort='newest'` 获取最新记录

```python
# session_search 查询模式示例
session_search(query="Linux学习进度 OR 第几课", sort="newest", limit=3)
# → 返回包含 bookend_start（任务起点）、messages（窗口上下文）、bookend_end（结果）
```

**补充数据源：直接读取 jobs.json**

当需要查看 cron 任务的完整配置（当前 repeat 计数、prompt 原文、schedule 细节），可以直接读取 jobs.json：

```python
import json
with open('/root/.hermes/cron/jobs.json') as f:
    data = json.load(f)
for job in data['jobs']:
    if '关键字' in job.get('name', ''):
        progress = f"{job['repeat']['completed']}/{job['repeat']['times']}"
```

**设计原则：** cron prompt 必须自包含，只能依赖 `session_search`、`file tools`（read_file 等）、`terminal` 和 `web tools` 来获取外部数据。不能依赖 `memory` 或任何需要用户交互的工具。

#### Cron prompt 不要引用自身

Cron job 的 prompt 会在每次运行时被完整执行。如果 prompt 中写了一句"检查进度并更新进度"但进度只能存在 memory（cron 不可用），那每次运行都从零开始，永远无法推进。如果需要跨次跟踪状态，用 session_search 查找之前自己的输出。

1. **`{{now}}` 模板变量在 agent prompt 中可能不被替换**
   — cron prompt 中的 `{{now}}` 在某些情况下可能保留为字面文本而非实际日期时间，导致 agent 无法确定"今天是几号"，进而搜索错误日期范围的会话，把前天的内容归到昨天的总结里。**防御措施：**（a）prompt 中明确说明"{{now}} 会被替换为当前日期时间，据此推算昨天日期"；（b）要求报告标题标注正确的日期和星期，便于用户一眼发现错误；（c）如果 `{{now}}` 不可靠，可在 script 前置脚本中用 `date` 命令输出当前时间，agent 从 [SCRIPT OUTPUT] 中获取。

2. **`hermes insights --days 1` 是滚动窗口，不是自然天**
   — 如果 cron 在 06:00 执行，`--days 1` 覆盖的是 06:00→次日 06:00 的滚动 24h，其中可能包含当前天早上的活动。如果 cron 在 20:00 执行，覆盖的是昨天 20:00 → 今天 20:00，数据会混入今天的活动。获取精确的自然天数据需要组合 `--days 2` 输出与 `--days 1` 输出手动推算差值，或在系统空闲时段（如 00:00-01:00）执行以避免跨天污染。

2. **cron 重复触发导致同一天的报告重复发送**
   — 如果同一 cron 任务被手动触发或多次执行（如 06:00 一次、20:40 又一次），两次生成的报告内容完全重复。建议：创建 cron 时将 `schedule` 设为精确 crontab（如 `0 6 * * *` 每天 06:00）而非 `every 24h` 这样的自然语言格式，防止 Hermes 调度器产生歧义。对已出现的重复情况，直接复用前一次的输出数据生成报告（不重复采集），不做额外动作。

3. **用 session_search 的 bookend_end 获取前一次结果**
   — 当 cron 需要参考之前执行的结果（如昨天已发的报告内容），可以通过 `session_search(query="...")` 找到上一次 cron 会话的 `bookend_end`，其中包含了前一次的完整输出。这是无上下文的 cron 环境中获取历史上下文的可靠方式。

4. **同个时间段同时运行多个 cron 任务**
   — 如果多个 agent 模式的 cron 任务（如 6:00 总结报告 + 6:05 余额检查）恰好在相近时间触发，它们属于独立的 LLM 会话，数据不共享。每个任务应自包含地获取所需数据，不能假设前一个任务的结果已就位。

相关参考：`references/cron-session-search-backplane.md` — 使用 session_search 和文件系统作为 cron 跨次数据存储的方案。

## 监控 Token 消耗

用 Hermes 内置的 `hermes insights` 命令查看用量：

```bash
hermes insights                    # 默认最近 30 天
hermes insights --days 1           # 仅昨天
hermes insights --days 7           # 最近一周
```

输出包括：会话数、输入/输出 tokens、总累计 tokens、模型用量分平台统计、最活跃时段、技能使用情况。

如果需要查询 DeepSeek 余额（从 agent 对话中执行）：
```bash
# 从 .env 加载 API Key 并查询
source /root/.hermes/.env 2>/dev/null
curl -s https://api.deepseek.com/user/balance \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY"
```
返回 JSON 中 `balance_infos[0].total_balance` 字段即为可用余额（CNY）。

### 余额报警阈值

- 日消耗 > 50 万 tokens → 报告中加 ⚠️ 提醒注意
- 余额 < 1 CNY → 报告中标记 🔴 余额不足

### 精确 Token 费用计算脚本

`calculate_token_cost.py` 读取 Hermes Insights 数据 + DeepSeek 余额 API，
按官方美元定价换算成人民币，输出格式化的费用明细。

**添加方式：** 在 cron agent-mode 任务中设置 `script` 参数，脚本输出会
注入到 prompt 的 `[SCRIPT OUTPUT]` 区块中作为上下文：

```python
cronjob(
    action='update',
    job_id='xxx',
    prompt='...引用上面的[SCRIPT OUTPUT]中的费用数据...',
    script='calculate_token_cost.py'   # 脚本输出 → [SCRIPT OUTPUT]
)
```

**定时执行：** 默认 6:00 每日总结报告已集成。另外建议配合 `check_deepseek_balance.py`
（6:05）做二次确认，两个数字应基本吻合。

详细定价和计算逻辑见 `references/token-cost-awareness.md`。

## 用户偏好：不要报告常规完成状态

本用户不希望被报告日常维护、技能创建、配置优化等常规任务的完成状态。以下规则适用于所有 cron 任务和后台维护：

- **静默执行** — no_agent 脚本若一切正常，直接静默完成（利用空 stdout 不投递的特性）
- **异常才出声** — 出问题时报具体错误，正常无需"已执行完成✅"类通知
- **agent 模式同样适用** — 不在回复中报告"定时任务已创建/更新"等状态信息
- **创建时说明一次** — 仅第一次设置时简要说明做了什么，后续不再汇报

### Token 消耗：长会话的上下文堆积风险

**问题：** 同一会话持续对话（即使跨天但只要未满 24 小时空闲），所有历史上下文会打包发给 API，输入 token 消耗呈规模级增长而输出变化不大。

**Hermes 的防护：** 自动上下文压缩 + `agent.max_turns: 90` 上限自动切会话 + prompt caching。

**日耗监控参考：** 参考 `references/token-cost-awareness.md` 了解本用户的余额阈值和报警规则。

## 服务检查陷阱：systemd vs PM2

当监控 Hermes 网关服务时，必须确认服务是通过 systemd 还是 PM2 托管的。Hermes 网关（`hermes-gateway`）在大多数部署中是 systemd 用户服务，而不是 PM2 进程。

**错误做法：** 使用 `pm2 jlist` 检查 `hermes-gateway` 状态，会始终返回未运行，导致误报和不必要的重启循环。

**正确做法：** 使用 `systemctl --user is-active hermes-gateway` 检查状态。

```python
def check_systemd_service(name):
    """检查 systemd 用户服务状态"""
    r = subprocess.run(['systemctl', '--user', 'is-active', name],
        capture_output=True, text=True, timeout=10)
    return r.stdout.strip() == 'active'
```

### 看门狗脚本防卡死策略

简单的重启循环可能导致服务不断被中断。推荐加入以下防护：

1. **最大重试次数** — 连续重启最多 3 次，失败后停止自动重启，输出"需人工介入"
2. **冷却期延长** — 重启后冷却期至少 30 分钟，避免频繁尝试
3. **服务列表精简** — 只检查实际存在的服务（如 `hermes-gateway`），不要检查不存在的服务（如 `hermes-dashboard` 可能不是 systemd 服务）

```python
MAX_RETRIES = 3
COOLDOWN = 1800  # 30分钟

def main():
    # ... 检查服务状态 ...
    if not ok:
        retry_count = get_retry_count()
        if retry_count >= MAX_RETRIES:
            log(f'❌ 连续重启 {MAX_RETRIES} 次失败，需人工介入')
            return
        # 尝试重启
        if restart_service(name):
            reset_retry_count()
        else:
            increment_retry_count()
```

**相关脚本：** `hermes_watchdog.py` 已修复为使用 systemd 检查并包含防卡死策略。如需参考，查看 `/root/.hermes/scripts/hermes_watchdog.py`。

## 注意事项

- no_agent 脚本必须放在 `~/.hermes/scripts/`，`cronjob` 的 `script` 参数只传文件名
- 脚本需要自加载环境变量（.env 文件），因为 cron 环境不同于交互式 shell
- 看门狗脚本必须用**锁文件**防并发（多个 cron 触发时间重叠时）
- 冷却期（cooldown）防止重复重启导致服务抖动
- 东八区时间：Hermes cron 默认用服务器时区，确认 `date` 返回 CST
- 脚本内调第三方 API 时，注意设置 timeout 防止脚本卡死
- **脚本超时** — no_agent 脚本默认 120 秒超时，可通过 `cron.script_timeout_seconds` 配置（建议 300s）。用 `time python3 script.py` 验证实际耗时。超时会被强制中断，日志显示 "Script timed out after Xs"
- **不要在循环内跑 subprocess** — 多用户推送场景，对每个用户分别跑 `subprocess.run(['python3', 'main.py', ...])` 会导致总时间 ×N，极易超时。应只跑一次生成报告，其他用户用文本裁剪
- **输出清洗：不要直接传递子进程的 stdout** — 如果调用的脚本包含调试日志（`[WARN]`, `[OK]`, `📡 采集...` 等），会污染最终消息。应改为**读取生成的报告文件**，或过滤日志行只保留关键行
- **修复验证：在声称"已修复"之前，必须实际测试验证** — 运行脚本、检查输出、确认问题已解决。不要只修改了代码就声称修复完成，用户可能会亲自验证并发现并未真正修复。
- **脚本必须覆盖所有边界情况** — 用户明确要求：写脚本应该把所有情况都考虑到。例如多用户推送场景，必须处理"用户没有持仓/没有数据"的情况，不能假设所有用户都有数据。在报告生成、数据展示等脚本中，为"空数据"路径设计合理的降级显示（如"暂无记录"、通用建议），而不是直接跳过或报错。

## 调试 cron 任务

### 用户问"那个 XX cron 去哪了"时

用户可能用**描述**而不是名称来指代 cron 任务（如"之前那个上下文过长的cron"）。用 `cronjob(action='list')` 列出所有任务，按 `name` 或 `prompt` 的文本匹配：

```python
# cronjob(action='list') 返回所有任务，逐个匹配 name 和 prompt
# 输出示例：
# b360bf33e3bc | 📊 上下文看门狗 | 15m | running | every 15 minutes
# 匹配关键词：上下文、长度、token、看门狗等
```

**常见用户描述 → 实际名称映射：**

| 用户说 | 可能是 |
|--------|-------|
| "上下文过长的" | 上下文看门狗（context_watchdog.py） |
| "余额检查的" | DeepSeek 余额检查 |
| "每天早上的报告" | 每日总结报告 |
| "提醒我..." | 一次性 cron 任务 |

当 cron 任务看起来没有按时触发时，参考 `references/cron-debugging.md` 进行排查。

**核心原则：先查 agent.log 确认调度器是否已触发，再决定是否手动干预。不要只看 `next_run_at` 就下结论**——调度器在执行前就推进了下一次时间（`advance_next_run`），所以看到的 `next_run_at` 永远是"下次"时间。
