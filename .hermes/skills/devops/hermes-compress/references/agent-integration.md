# 三个 Agent 集成方案

## 1. Hermes Agent

### 方式A：hcp wrapper（推荐，已实现）
直接在 terminal 命令前加 `hcp`：
```bash
hcp git status
hcp env
```

### 方式B：Python模块直接调用
```python
import subprocess
from hermes_compress import compress

result = subprocess.run(['git', 'status'], capture_output=True, text=True)
compressed = compress(result.stdout, cmd_type='git-status')
print(compressed)
```

### 方式C：terminal工具后处理（待实现）
Hermes 的 terminal 工具在返回输出前自动调用压缩：
- 需要修改 `/root/.hermes/hermes-agent/tools/environments/local.py`
- 或通过 plugin 的 post_tool_call hook 实现

## 2. Claude Code

### 方式A：hcp 前缀（最简单，已验证可用）
```bash
hcp git status
hcp env
hcp docker ps
```
Claude Code 的 terminal 是交互式 shell，`/usr/local/bin/hcp` 全局可用。

### 方式B：自定义 hook 脚本（高级）
在 `.claude/settings.json` 的 hooks 中配置 post-tool-call 脚本，自动对输出调用 compress()。

### 方式C：Python 模块直接调用
```python
import sys
sys.path.insert(0, '/root')
from hermes_compress import compress
# 在脚本中处理命令输出时使用
```

> ⚠️ RTK 已于 2026-06-15 卸载，`rtk init -g` 不再可用。hcp 完全替代。

## 3. 其他 Agent / 脚本

### 作为管道过滤器
```bash
any_command | python3 /root/hermes_compress.py
any_command | python3 /root/hermes_compress.py --type git-diff --stats
```

### 作为Python库
```python
import sys
sys.path.insert(0, '/root')
from hermes_compress import compress, OutputCompressor

# 使用自动检测
result = compress(raw_output)

# 指定类型
result = compress(raw_output, cmd_type='env')

# 自定义参数
compressor = OutputCompressor(max_line_length=100, max_lines=200)
result = compressor.compress(raw_output)
```

## 技术难点：Hermes Terminal 的 shell 限制

Hermes 的 terminal 工具每次命令都启动新的非交互式 bash 子进程：
```python
# local.py 中的执行方式
bash -c "source ~/.bashrc; <command>"
```

这意味着：
- `.bashrc` 中的 alias 和函数**不会**被继承到下一次命令
- 环境变量（export）可以持久化
- `BASH_ENV` 环境变量无效
- `terminal.auto_source_bashrc` 配置项无效

所以 hcp wrapper 不能自动生效，只能在每个命令前手动加 `hcp` 前缀。
要实现真正的"自动压缩"，需要修改 Hermes 的 terminal 工具源码或用 plugin hook。
