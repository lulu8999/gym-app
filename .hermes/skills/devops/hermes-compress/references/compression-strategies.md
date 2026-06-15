# 压缩策略详解

## Git 命令

### git-status
- 提取分支信息（`On branch` + `ahead/behind`）
- 分三类统计：Staged / Unstaged / Untracked
- 每类只显示前 5/10 个文件名，超过用 `... and N more`
- 122行 → 4行

### git-diff
- 每个文件提取 `+N -M` 统计
- 第一行汇总：`N files changed, +X -Y`
- 不保留具体diff内容（AI可以按需再跑详细diff）
- 14行 → 2行

### git-log（待实现）
- 只保留最近20条，格式：`<short_hash> <message>`
- 合并commit可跳过

## Docker 命令

### docker ps
- 只保留：容器名 | 镜像 | 状态 | 端口
- 去掉 CONTAINER ID、CREATED 等

### docker images
- 只保留：`repo:tag | size`

## 搜索命令

### grep
- 优先按 `file:line:content` 格式按文件分组
- 每文件只显示前3个匹配
- **兜底**：无 `file:line:` 格式时，按纯行输出，显示前5行 + `... and N more`
- 截断每行到 80-120 字符

### find
- 按目录分组，每目录显示前5个文件
- 超过用 `... and N more`
- 大目录（如 node_modules、venv）压缩效果最明显

## 系统命令

### env
- 按类型分组：PATH / Language / Cloud / Tools / Other
- 敏感变量（token/key/secret/password/auth）值替换为 `***`
- 长值截断到 100 字符
- PATH 只显示条目数，不展开

### log
- 统计各级别数量（ERROR/WARN/INFO/DEBUG）
- 去重连续相同行，显示 `... repeated N times`
- 限制总行数（默认500行）

### ls
- 提取文件类型（d/f）+ 文件名
- 去掉权限、大小、时间戳

## 通用压缩（fallback）
- 截断超长行（默认200字符）
- 去掉重复空行
- 限制总行数（默认500行）
