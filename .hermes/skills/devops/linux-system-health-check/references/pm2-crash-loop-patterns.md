# PM2 崩溃循环 — 真实错误日志样本

## 模式B：PM2 vs 独立进程

### 场景
hermes-gateway 已通过 `hermes gateway run` 在终端独立运行（不在 PM2 里）。  
PM2 的 `ecosystem-hermes-gateway.json` 又配置了一份 → 启动就崩 → 28,899 次重启。

### PM2 stdout 日志特征（`~/.pm2/logs/<app>-out.log`）

```
┌─────────────────────────────────────────────────────────┐
│           ⚕ Hermes Gateway Starting...                 │
├─────────────────────────────────────────────────────────┤
│  Messaging platforms + cron scheduler                    │
│  Press Ctrl+C to stop                                   │
└─────────────────────────────────────────────────────────┘

❌ Gateway already running (PID 3230431).
   Use 'hermes gateway restart' to replace it,
   or 'hermes gateway stop' to kill it first.
   Or use 'hermes gateway run --replace' to auto-replace.
```

上面这段会重复 N 次（每次 PM2 拉起就重复）。

### PM2 stderr 日志特征（`~/.pm2/logs/<app>-error.log`）

大量重复的 deprecated 警告 + KeyboardInterrupt traceback：

```
⚠ Deprecated .env settings detected:
  ⚠ TERMINAL_CWD=/root found in .env — this is deprecated.
  Move to config.yaml instead:  terminal:
    cwd: /your/project/path
  Then remove the old entries from /root/.hermes/.env

Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  ...
  File "/root/.hermes/hermes-agent/hermes_cli/config.py", line 6530, in <module>
    _inject_platform_plugin_env_vars()
  ...
KeyboardInterrupt
```

### 诊断 checklist

1. `pm2 list` → 看 restarts 列表（>100 就可疑）
2. `pm2 show <app>` → uptime 0s + 高 restarts = 确认循环
3. `cat ~/.pm2/logs/<app>-out.log | tail -30` → 找 "already running"
4. `ps aux | grep <app> | grep -v grep` → 找独立运行的真正进程
5. `pm2 stop <app> && pm2 delete <app>` → 删掉 PM2 重复条目
6. 检查 ecosystem JSON 文件（`/root/ecosystem-*.json`）是否有残留配置

### 修复后验证

```bash
# 确认 PM2 里已无重复
pm2 list

# 确认真正进程还在运行
ps aux | grep <app> | grep -v grep

# 确认 CPU 恢复正常
top -bn1 | head -5
```
