# PM2 网关停止不自动重启 — 诊断样本

> 2026-06-12 实际案例：微信突然断联 → 网关 stopped → PM2 没自动拉起来

## 症状

- 用户报告微信（企微）连不上
- `pm2 list` 显示 `hermes-gateway: stopped, restarts=0`
- `ps aux | grep "[h]ermes gateway"` 无进程

## 根因

PM2 的 `autorestart` 只在进程 **crash（非零退出码）** 时触发。
网关收到 SIGINT 正常退出（exit 0），PM2 不重启。

## 日志证据

**gateway.log 最后几行（正常退出）：**
```
2026-06-12 21:58:27,641 INFO gateway.run: Received SIGINT as a planned gateway stop — exiting cleanly
2026-06-12 21:58:27,645 INFO gateway.run: Stopping gateway...
2026-06-12 21:58:27,869 INFO gateway.run: Sent shutdown notification to active chat weixin:xxx
```

**PM2 状态：**
```
id │ name           │ status  │ restarts │ uptime
19 │ hermes-gateway │ stopped │ 0        │ 0
```

restarts=0 说明 PM2 从未尝试重启。

**gateway-exit-diag.log（退出诊断）：**
```json
{"tag": "gateway.exit_nonzero", ...}  ← 没有这条（正常退出不会有）
```

## 修复步骤

```bash
# 1. 确认 systemd 不干扰（VPS 容器里应该是 Failed to connect）
systemctl --user is-enabled hermes-gateway 2>&1

# 2. 清 pycache（防止旧代码）
find /root/.hermes/hermes-agent/agent/__pycache__ -delete

# 3. 手动拉起来
pm2 restart hermes-gateway

# 4. 验证
pm2 list | grep hermes-gateway
tail -10 /root/.hermes/logs/gateway.log | grep -i "weixin\|connect"
```

## 对比：systemd 冲突案例（2026-06-12 早期）

当时 systemd `Restart=always` + PM2 `autorestart` 同时管网关 → 端口冲突 → 崩溃 77 次。现在 systemd user bus 不可用（VPS 容器环境正常现象），反而避免了冲突。
