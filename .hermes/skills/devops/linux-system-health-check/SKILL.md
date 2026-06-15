---
name: linux-system-health-check
title: Linux 系统健康检查与优化
description: 系统级健康诊断、故障排查和优化流程
triggers:
  - 用户说"系统优化"、"自检"、"健康检查"、"系统检查"
  - 系统故障排查或性能问题
  - 定期维护检查
---

# Linux 系统健康检查与优化

> 📄 macOS 远程诊断命令集：`references/macos-remote-health-check.md`
> 📄 SSH 连通性排查流程：`references/ssh-connectivity-troubleshooting.md`

## 诊断流程（按优先级顺序）

### 1. 基础资源检查
首先获取系统整体状态快照：

```bash
echo "=== 磁盘空间 ===" && df -h
echo -e "\n=== 内存使用 ===" && free -h  
echo -e "\n=== 系统负载 ===" && uptime
echo -e "\n=== 进程数 ===" && ps aux | wc -l
```

关注指标：
- 磁盘使用率 > 80% 需警惕
- 内存使用 + Swap 使用 > 90% 可能内存不足
- 负载 > CPU核心数 表示高负载

### 2. 服务状态双检法
**关键技巧：不要只信任 systemctl**

systemctl 可能报告服务未运行，但实际进程可能存在（如通过 PM2 或手动启动）。正确做法：

```bash
# 方法一：systemctl 检查
systemctl is-active <service>

# 方法二：必须用 ps 验证实际进程
ps aux | grep -i <service> | grep -v grep
```

如果 systemctl 显示未运行但 ps 能看到进程，说明服务是通过其他方式启动的（如 PM2、手动启动等）。

### 3. 重复服务配置检查（三种冲突模式）

**模式A：systemd + PM2 双重管理**
同一应用同时被 systemd 和 PM2 管理，互相抢进程。

```bash
# 查看systemd配置
cat /etc/systemd/system/<service>.service
# 查看PM2进程
pm2 list
pm2 show <app-name>
```

**模式B：PM2 vs 独立进程（⚠️ 高频陷阱）**
> 📄 详细错误日志样本：`references/pm2-crash-loop-patterns.md`
应用已经通过非 PM2 方式运行（手动启动、其他 supervisor），PM2 又配了一份 → 启动即检测到已有进程 → 退出 → PM2 autorestart 拉起 → 又退出 → 无限循环。

**诊断信号：**
- `pm2 list` 显示超高重启次数（上千甚至上万）
- `pm2 show <app>` 显示 uptime 接近 0s
- CPU 占用异常高（启动-退出循环吃满）

**诊断步骤：**
```bash
# 1. 看 PM2 日志，找关键词 "already running"
pm2 logs <app> --lines 50 --nostream
# 或直接读日志文件
cat /root/.pm2/logs/<app>-out.log | tail -30

# 2. 找到真正运行的独立进程
ps aux | grep -i <app> | grep -v grep

# 3. 确认：如果 ps 能看到非 PM2 管理的进程，那就是根因
```

**修复：**
```bash
# 停掉 PM2 的重复条目（保留独立运行的那个）
pm2 stop <app> && pm2 delete <app>

# 如果是 ecosystem JSON 文件导致的，删除它
rm /root/ecosystem-<app>.json

# ⚠️ 关键：delete 后必须 save，否则 dump.pm2 残留条目会在 resurrect 时复活
pm2 save
```

**⚠️ `max_restarts` 不等于循环保护：** ecosystem 文件里设的 `max_restarts: 10` 在 PM2 进程本身重启后会重置计数器。如果 PM2 被 systemd/cron/watchdog 重启过，restart 计数能飙到上万。所以看到 restarts > 100 时不要以为 max_restarts 生效了——检查 PM2 自身是否在被外部重启。

**模式C：PM2 dump 残留**
`pm2 delete` 后 `~/.pm2/dump.pm2` 仍保留条目，下次 `pm2 resurrect` 会复活已删除的服务。清理后需 `pm2 save` 更新 dump。

如果发现重复，选择一种方式管理，停用另一种。

### 4. 问题服务诊断
如果发现服务异常重启：

```bash
# 查看详细状态
systemctl status <service> --no-pager

# 查看日志
journalctl -u <service> --no-pager -n 50

# 查看系统错误日志
journalctl -p err --since "24 hours ago" --no-pager | tail -20
```

常见异常状态：
- `activating (auto-restart)` + 返回码非零 → 配置错误或依赖缺失
- `status=200/CHDIR` → WorkingDirectory 不存在
- `status=203/EXEC` → ExecStart 指定的可执行文件不存在

### 5. 可清理空间扫描
```bash
# 大文件扫描（>100MB）
find /root -type f -size +100M 2>/dev/null | head -20

# 日志目录
ls -lh /var/log
du -sh /root/.hermes/logs
du -sh /root/.pm2/logs

# 缓存目录
du -sh /root/.cache
du -sh /tmp
du -sh /var/tmp
```

### 6. 僵尸进程检查
```bash
ps aux | awk '$8 ~ /^[Zz]/ {print}' | wc -l
```
僵尸进程表示父进程未正确回收子进程。

## 优化清理流程（安全优先）

### 核心原则：先备份，再清理

所有清理操作前必须创建备份目录，保留关键文件：
```bash
BACKUP_DIR="/root/backups/cleanup_$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR
# 将不确定是否可删的文件先移入备份目录，清理后验证无误再决定是否删除
```

### 安全清理步骤（执行前必须向用户确认）

1. **停用异常服务**
   ```bash
   systemctl stop <service>
   systemctl disable <service>
   rm /etc/systemd/system/<service>.service
   systemctl daemon-reload
   ```

2. **识别可清理项（三分类法）**

   **A. 明确可删（临时/已安装完成）**
   - `.rpm`、`.deb` 安装包（已安装后无用）
   - 旧的内核包、旧版本应用缓存
   - 已废弃的测试脚本、snap 文件
   
   **B. 需检查内容后决定**
   - `/tmp/*.json`、日志文件 → 查看内容确认是否过期
   - 大文件 → `ls -lh` 确认用途
   
   **C. 保留（运行时依赖）**
   - Playwright 运行时（`/root/.cache/ms-playwright/`）
   - Electron 依赖（如已配置）
   - 当前服务的必要缓存

3. **清理缓存**（保留必要的）
   ```bash
   # pip/uv 缓存（可重建，通常可删）
   pip cache purge
   rm -rf /root/.cache/uv/*
   
   # npm 缓存（谨慎）
   npm cache clean --force
   ```

4. **日志轮转**
   ```bash
   # systemd journal 保留最近7天
   journalctl --vacuum-time=7d
   
   # 手动轮转（保留最近5000行）
   tail -n 5000 /var/log/syslog > /var/log/syslog.tmp
   mv /var/log/syslog.tmp /var/log/syslog
   ```

## 常见问题与解决方案

| 问题现象 | 可能原因 | 解决方案 |
|---------|---------|---------|
| systemctl 显示 failed，但进程存在 | 多种启动方式冲突 | 确定主要管理方式，停用其他 |
| 无限重启循环 | WorkingDirectory/ExecStart 路径错误 | 检查路径存在性，修复配置 |
| PM2 重启上万次 + uptime 0s | PM2 重复条目 vs 独立进程冲突 | `pm2 delete` 去掉重复，保留独立进程 |
| 磁盘空间快满 | 日志/缓存/大文件 | 扫描大文件，轮转日志 |
| 负载过高 | 资源不足或某服务异常 | top/htop 定位消耗资源的进程 |

### 7. 版本管理与自动更新检查
Hermes 等应用的更新状态检查：

```bash
# 检查当前版本
hermes --version

# 检查是否落后于上游
cd /root/.hermes/hermes-agent
git log --oneline HEAD..origin/main | wc -l  # 待更新提交数

# 检查自动更新 cron 任务
hermes cron list | grep -i update
```

如果发现更新失败：
1. 检查网络/代理是否正常
2. 手动执行更新：`git pull --rebase origin main`
3. 处理本地修改冲突（如有）

---

## 校验清单

检查完成后验证：
- [ ] 无新的系统错误日志（`journalctl -p err --since "1 minute ago"`）
- [ ] 服务状态符合预期
- [ ] 磁盘空间释放成功
- [ ] 进程数无异常增加
- [ ] 备份目录内容确认（重要文件已保留）
- [ ] 应用版本为最新（或明确知晓落后原因）

---

## 示例流程：完整系统优化

### 第一步：诊断
```bash
# 基础资源
df -h && free -h && uptime

# 服务检查
systemctl is-active hermes-gateway
ps aux | grep -c '[h]ermes'
pm2 list

# 问题诊断
journalctl -p err --since "24 hours ago" | tail -20
```

### 第二步：识别问题
常见情况：
- 服务双重配置（systemd + PM2）→ 选一种管理方式
- 异常重启循环（配置错误）→ 停用并删除
- 资源不足（磁盘/内存）→ 扫描可清理项

### 第三步：备份与清理
1. 创建备份目录
2. 将不确定项移入备份
3. 执行清理（服务/缓存/日志）
4. 验证无误

### 第四步：版本更新（如需要）
```bash
cd /root/.hermes/hermes-agent
git fetch origin main
git pull --rebase origin main
hermes --version
```
