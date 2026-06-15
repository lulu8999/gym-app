# WSL 环境复制指南

将 VPS 上的 Hermes 生态（技能、脚本、配置记忆）复制到 WSL 环境，实现远程环境快速搭建。

## 使用场景

- 新装 WSL 后快速同步工作环境
- 多机器间保持配置一致
- 备份/恢复 Hermes 配置

## 复制清单

| 内容 | 来源 | 目标 | 说明 |
|:-----|:-----|:-----|:-----|
| 技能 | `~/.hermes/skills/` | `~/.hermes/skills/` | 工作流程、L123等 |
| 脚本 | `~/scripts/` | `~/scripts/` | 监控、备份、初始化 |
| 记忆 | `~/MEMORY.md` | `~/MEMORY.md` | 配置摘要 |
| 桌面快捷方式 | `*.bat` | `/mnt/c/Users/<用户>/Desktop/` | 用户双击用 |

## 完整流程

### 1. 打包（VPS端）

```bash
# 打包技能
cd ~/.hermes/skills
tar czf /tmp/hermes-skills.tar.gz lulu-workflow/ l123-l1/ l123-l2/

# 打包脚本
tar czf /tmp/hermes-scripts.tar.gz -C ~/ scripts/

# 打包记忆
cp ~/MEMORY.md /tmp/
```

### 2. 传输到 WSL

```bash
# 确保 WSL 目录存在
sshpass -p '密码' ssh lulu@host "mkdir -p ~/.hermes/skills ~/scripts"

# 传输
sshpass -p '密码' scp /tmp/hermes-skills.tar.gz lulu@host:~/.hermes/skills/
sshpass -p '密码' scp /tmp/hermes-scripts.tar.gz lulu@host:~/
sshpass -p '密码' scp /tmp/MEMORY.md lulu@host:~/
```

### 3. 解压（WSL端）

```bash
sshpass -p '密码' ssh lulu@host "cd ~/.hermes/skills && tar xzf hermes-skills.tar.gz && rm hermes-skills.tar.gz"
sshpass -p '密码' ssh lulu@host "tar xzf hermes-scripts.tar.gz && rm hermes-scripts.tar.gz"
```

### 4. 桌面快捷方式

```bash
# 复制 .bat 到 Windows 桌面
sshpass -p '密码' scp ~/scripts/启动监控.bat lulu@host:/mnt/c/Users/陆海天/Desktop/
```

### 5. 验证

```bash
sshpass -p '密码' ssh lulu@host "echo '=== 技能 ===' && ls ~/.hermes/skills/ && echo '=== 脚本 ===' && ls ~/scripts/ && echo '=== 记忆 ===' && head -10 ~/MEMORY.md"
```

## 创建 MEMORY.md 模板

```markdown
# WSL 配置记忆

## 系统信息
- 用户: <用户名>
- IP: <IP>
- WSL: Ubuntu <版本>

## SSH配置
- Windows原生SSH: 端口2222, 用户<名>, 密码<密码>
- WSL SSH: 端口22, 用户<名>, 密码<密码>

## 已安装软件
- Python <版本>
- Node.js <版本>

## 重要目录
- ~/scripts/ - 脚本目录
- ~/.hermes/skills/ - 技能目录

## 已传技能
- lulu-workflow - 工作流程标准
- ...

## 已传脚本
- ~/scripts/monitor.ps1 - 监控脚本
- ...

## 待处理
- ...
```

## 注意事项

- **NVM PATH**：非交互式 SSH 需要 `source ~/.nvm/nvm.sh` 才能用 node/npm
- **heredoc 变量**：复杂文件本地创建 + SCP，不要用 SSH heredoc
- **权限**：WSL 用户需要对目标目录有写权限
- **编码**：.bat 文件用 ANSI 编码避免中文乱码
