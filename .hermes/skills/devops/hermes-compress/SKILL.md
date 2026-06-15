---
name: hermes-compress
description: "RTK-style output compression plugin — compresses terminal command output 60-99% before it hits LLM context. Works as Python module + CLI wrapper (hcp)."
triggers:
  - "compress output"
  - "rtk style"
  - "节省token"
  - "输出压缩"
  - "command output compression"
---

# Hermes Compress — 输出压缩插件

## 项目位置

- **Python模块**: `/root/hermes_compress/`
- **CLI wrapper**: `/root/hcp` → `/usr/local/bin/hcp`
- **独立版本**: `/root/hermes-compress.py`
- **Git仓库**: `https://github.com/lulu8999/vps-backup.git`

## 快速使用

```bash
# CLI wrapper — 自动识别命令类型并压缩
hcp git status
hcp env
hcp grep "pattern" /path
hcp find . -name "*.py"
hcp --stats git diff        # 显示压缩统计
hcp --force ls -la          # 强制压缩任意命令
hcp --no-compress git log   # 跳过压缩

# Python模块
from hermes_compress import compress
result = compress(output, cmd_type="git-status")
```

## 压缩效果

| 命令 | 压缩率 | 说明 |
|------|--------|------|
| `git status` | 96-98% | 只保留分支+文件计数 |
| `git diff` | 85% | 只保留文件名+增删统计 |
| `env` | 95-99% | 按类型分组+敏感过滤 |
| `grep` | 60-95% | 按文件分组或纯行截断 |
| `find` | 40-80% | 按目录分组 |
| `log` | 95% | 级别统计+去重 |

## 支持的命令类型

`git-status`, `git-diff`, `git-log`, `git-show`, `git-branch`, `docker`, `docker-images`, `grep`, `find`, `ls`, `env`, `log`, `generic`

## 压缩策略详情

见 `references/compression-strategies.md`

## Agent自动调用（用户明确要求）

**用户指令（2026-06-15）**："你自己调用这个自己压缩，不需要我来输命令"+"在保证输出质量的同时来压缩，不要本末倒置"

**规则**：
1. Agent执行命令时自动加 `hcp` 前缀（`git status` → `hcp git status`）
2. 用户不需要手动输入 `hcp`，由agent在内部决定是否压缩
3. **质量优先**：需要对输出做二次处理（解析、写入文件）时，不加 hcp，保留原始输出
4. 不确定时宁可不压缩，不要丢失关键信息

## RTK 已废弃

RTK (Rust Token Killer) 已于 2026-06-15 卸载，被 hcp 完全替代。删除项：
- `/usr/local/bin/rtk`
- `/etc/profile.d/rtk-aliases.sh`
- `~/.rtk/` 配置目录
- `~/.claude/RTK.md`

原因：RTK 需要用户手动 `rtk <command>` 调用，无法在 Hermes terminal 中自动生效（每次命令启动新shell进程，alias/函数不持久化）。hcp 作为 agent 内部工具，由 agent 自行决定调用。

## Pitfalls

### 1. grep 压缩必须处理无 file:line 格式
单文件 `grep pattern file` 不带 `-n` 时，输出是纯行没有 `file:line:` 前缀。必须有 plain_lines 兜底，否则所有输出被吞。

**修复**：`_compress_grep()` 中当 `file_groups` 为空但 `plain_lines` 非空时，按纯行输出：
```python
elif plain_lines:
    total = len(plain_lines)
    result.append(f"{total} matches:")
    for line in plain_lines[:5]:
        result.append(f"  {line}")
    if total > 5:
        result.append(f"  ... and {total - 5} more")
```

### 2. env 压缩率随环境变量数量变化
Hermes cron 会话的环境变量比交互会话少很多（cron会话压缩率可能只有7%），这是正常的。

### 3. hcp 导入路径
hcp 脚本必须用绝对路径 `sys.path.insert(0, '/root')` 导入 hermes_compress，不能依赖相对路径。

### 4. ls 压缩效果有限
`ls -la` 输出本身就很紧凑，压缩率只有 2-4%。主要价值是提取文件名去掉权限信息。

## 测试

```bash
# 运行全部测试（11个用例）
python hermes_compress/tests/test_compress.py
```

## 三个Agent集成方案

见 `references/agent-integration.md`

## 扩展新命令类型

1. 在 `OutputCompressor` 类中添加 `_compress_xxx()` 方法
2. 在 `_detect_command_type()` 中添加检测规则
3. 在 `COMPRESS_COMMANDS` dict（hcp脚本）中添加命令
4. 编写测试用例
