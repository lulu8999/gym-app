# OpenClaw → Hermes 迁移：远程勘查流程

当需要从另一台机器上的 OpenClaw 迁移到 Hermes 时，先用这个流程盘点所有可迁移资产。

## 前置条件

- 两台机器在同一 Tailscale 网络（或可互访）
- 目标机器有 Python 3（用于 HTTP server 回退方案）

## 连通性方案（按优先级）

### 方案 A：SSH（首选）

```bash
ssh user@<tailscale-ip> "echo ok"
```

如果超时 → 检查目标机器 SSH Server 是否运行：
- **Linux/Mac**: `systemctl status sshd`
- **Windows**: `Get-Service sshd`（Windows 10.0.26200 可能装不上 OpenSSH Server）

### 方案 B：Python HTTP Server（Windows SSH 失败时）

在目标机器上：
```powershell
cd $env:USERPROFILE\.openclaw
python -m http.server 8888 --bind 0.0.0.0
```

从 VPS 读：
```bash
curl -s http://<tailscale-ip>:8888/
```

⚠️ 用完记得 `Ctrl+C` 停掉 HTTP server。

## 资产盘点清单

### 1. 配置文件
```bash
curl -s http://<ip>:8888/openclaw.json
```
关注：`models.providers`、`plugins.entries`、`agents.defaults.model`、`gateway` 配置

### 2. 记忆/知识库
```bash
curl -s http://<ip>:8888/memory/              # 目录结构
curl -s http://<ip>:8888/memory/main.sqlite   # SQLite 记忆库
```

### 3. 自定义技能
```bash
curl -s http://<ip>:8888/hermes-workspace/skills/   # 列出
curl -s http://<ip>:8888/workspace/skills/          # 备用位置
```

逐个拉取 SKILL.md：
```bash
for skill in token-budget-guard plan-then-execute model-router; do
  curl -s "http://<ip>:8888/hermes-workspace/skills/$skill/SKILL.md"
done
```

### 4. 核心文件（工作区）
```bash
curl -s http://<ip>:8888/hermes-workspace/MEMORY.md
curl -s http://<ip>:8888/hermes-workspace/USER.md
curl -s http://<ip>:8888/hermes-workspace/SOUL.md
curl -s http://<ip>:8888/hermes-workspace/IDENTITY.md
curl -s http://<ip>:8888/hermes-workspace/AGENTS.md
curl -s http://<ip>:8888/hermes-workspace/TOOLS.md
```

### 5. 插件技能（OpenClaw 内置）
```bash
curl -s http://<ip>:8888/plugin-skills/
```

## 迁移价值评估

| 资产类型 | 优先级 | 迁移方式 |
|----------|:------:|----------|
| 配置文件（provider/model） | 高 | 对照写入 Hermes config.yaml |
| MEMORY.md / USER.md | 高 | 合并到 Hermes memory |
| 自定义技能 SKILL.md | 中 | 转为 Hermes skill |
| 工作区脚本/文件 | 低 | scp 或按需迁移 |
| SQLite 记忆库 | 低 | 通常为空或已体现在 MEMORY.md |

## 清理 OpenClaw

迁移完成后：
- **仅停服务**：`pm2 stop openclaw-gateway`（保留配置可回滚）
- **彻底卸载**：`npm uninstall -g openclaw` + 删除 `~/.openclaw/`
- **推荐**：先停服，等 Hermes 跑稳几天再彻底删
