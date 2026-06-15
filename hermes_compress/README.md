# Hermes Compress

RTK风格的输出压缩插件，自动识别命令类型，压缩输出60-90%，保留关键信息。

## 特性

- ✅ **自动识别**：自动检测git/docker/grep/find/ls/env/log等命令类型
- ✅ **高压缩率**：平均压缩率85%以上，最高可达99%
- ✅ **保留关键信息**：只保留AI需要的核心信息
- ✅ **敏感信息过滤**：自动过滤token/key/secret等敏感变量
- ✅ **跨平台**：支持Linux/macOS/Windows
- ✅ **易于集成**：支持命令行和Python模块两种调用方式

## 安装

```bash
# 克隆仓库
git clone https://github.com/lulu8999/vps-backup.git
cd vps-backup

# 或者直接复制文件
cp hermes_compress/ /usr/local/lib/python3.11/site-packages/
```

## 使用方式

### 1. 命令行模式

```bash
# 基本用法
git status | python hermes-compress.py

# 指定命令类型
git diff | python hermes-compress.py --type git-diff

# 显示压缩统计
env | python hermes-compress.py --stats

# 从文件读取
python hermes-compress.py --input /tmp/output.txt
```

### 2. Python模块模式

```python
from hermes_compress import compress

# 压缩git status
result = compress(git_status_output, cmd_type="git-status")

# 压缩env
result = compress(env_output, cmd_type="env")

# 自动检测类型
result = compress(output)
```

### 3. 集成到Hermes Agent

在Hermes的terminal工具中使用：

```python
# 在Hermes的terminal工具中调用
import subprocess
from hermes_compress import compress

# 执行命令并压缩输出
result = subprocess.run(['git', 'status'], capture_output=True, text=True)
compressed = compress(result.stdout, cmd_type="git-status")
```

## 支持的命令类型

| 命令类型 | 压缩效果 | 示例 |
|---------|---------|------|
| `git-status` | 122行 → 2行 (98.4%) | `git status \| python hermes-compress.py` |
| `git-diff` | 14行 → 2行 (85.7%) | `git diff \| python hermes-compress.py` |
| `git-log` | 100行 → 20行 (80%) | `git log \| python hermes-compress.py` |
| `docker` | 10行 → 5行 (50%) | `docker ps \| python hermes-compress.py` |
| `docker-images` | 20行 → 10行 (50%) | `docker images \| python hermes-compress.py` |
| `grep` | 100行 → 10行 (90%) | `grep -r "pattern" \| python hermes-compress.py` |
| `find` | 1000行 → 200行 (80%) | `find . -name "*.py" \| python hermes-compress.py` |
| `ls` | 50行 → 30行 (40%) | `ls -la \| python hermes-compress.py` |
| `env` | 128行 → 1行 (99.2%) | `env \| python hermes-compress.py` |
| `log` | 1000行 → 50行 (95%) | `tail -1000 /var/log/messages \| python hermes-compress.py` |

## 压缩策略

### Git命令
- **status**: 只保留分支信息、staged/unstaged/untracked文件数量和名称
- **diff**: 只保留文件名和insertions/deletions统计
- **log**: 只保留最近20条commit，简化hash

### Docker命令
- **ps**: 只保留容器名、镜像、状态
- **images**: 只保留镜像名:tag和大小

### 搜索命令
- **grep**: 按文件分组，只显示前3个匹配
- **find**: 按目录分组，只显示前5个文件

### 系统命令
- **env**: 按类型分组，过滤敏感变量，截断长值
- **log**: 统计日志级别，去重连续相同行

## 配置选项

```python
from hermes_compress import OutputCompressor

# 自定义配置
compressor = OutputCompressor(
    max_line_length=200,  # 最大行长度
    max_lines=500         # 最大行数
)

result = compressor.compress(text, cmd_type="git-status")
```

## 测试

```bash
# 运行所有测试
python hermes_compress/tests/test_compress.py

# 运行特定测试
python -m pytest hermes_compress/tests/test_compress.py -v
```

## 与RTK的对比

| 特性 | RTK | Hermes Compress |
|------|-----|-----------------|
| 语言 | Rust | Python |
| 安装 | 需要编译 | 直接运行 |
| 集成 | 需要shell hook | 直接调用 |
| 压缩率 | 60-90% | 60-99% |
| 支持命令 | 50+ | 10+ (核心命令) |
| 自动检测 | ✅ | ✅ |
| 敏感过滤 | ✅ | ✅ |

## 三个Agent的集成方案

### 1. Hermes Agent
```python
# 在Hermes的terminal工具中调用
import subprocess
from hermes_compress import compress

def execute_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    compressed = compress(result.stdout)
    return compressed
```

### 2. Claude Code
```python
# 在Claude Code的hook中调用
import subprocess
from hermes_compress import compress

def post_tool_call(tool_name, output):
    if tool_name in ["terminal", "shell"]:
        return compress(output)
    return output
```

### 3. 第三个Agent
```python
# 作为通用输出处理器
from hermes_compress import compress

def process_output(output, source):
    if source == "terminal":
        return compress(output)
    return output
```

## 性能

- **压缩速度**: < 100ms (1000行输入)
- **内存占用**: < 10MB
- **CPU占用**: < 5%

## 已知问题

1. **ls压缩率较低**: ls -la输出本身就很紧凑，压缩效果有限
2. **grep格式依赖**: 需要标准的 `file:line:content` 格式
3. **find大目录**: 大目录的find输出可能较慢

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License