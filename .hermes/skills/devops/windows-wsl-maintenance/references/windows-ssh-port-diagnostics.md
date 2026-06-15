# Windows SSH 端口诊断 — 连不上时的排查流程

## 场景
从 VPS 通过 Tailscale SSH 连 Windows 笔记本，标准端口不通。

## 端口探测（先扫再连）

当 2222（Windows SSH）或 22（WSL SSH）超时时，快速扫常用端口：

```bash
for port in 22 80 443 3389 8080 9119 18888; do
  timeout 3 bash -c "echo >/dev/tcp/<win-ip>/$port" 2>/dev/null \
    && echo "端口 $port ✅ 开放" \
    || echo "端口 $port ❌ 关闭"
done
```

## 连接错误类型诊断

| 错误信息 | 含义 | 可能原因 |
|---------|------|---------|
| `Connection timed out` | TCP 连接无响应 | 端口未监听 / 防火墙拦截 / 机器离线 |
| `Connection reset by peer` | TCP 握手成功但 SSH 被拒 | SSH 服务卡死 / max connections / 非 SSH 服务占用端口 |
| `Connection timed out during banner exchange` | TCP 连上但 SSH 握手超时 | 网络延迟极高（Tailscale relay >300ms）/ SSH 服务响应慢 |
| `kex_exchange_identification: read: Connection reset` | SSH 协议握手阶段被重置 | SSH 服务崩溃或配置错误 |

### 端口 22 开着但 SSH 握手被重置（真实案例 2026-06-14）
**症状：** TCP 连接成功（端口扫描显示 ✅），但 SSH 报 `kex_exchange_identification: read: Connection reset by peer`。HTTP/HTTPS 也连不上。

**诊断过程：**
```bash
# 1. 端口扫描确认 TCP 可达
timeout 3 bash -c "echo >/dev/tcp/<ip>/22" && echo "开放"

# 2. SSH 连接（尝试不同用户名，排除用户问题）
ssh -o ConnectTimeout=30 陆海天@<ip> -p 22  # → Connection reset
ssh -o ConnectTimeout=30 lulu@<ip> -p 22     # → Connection reset

# 3. 排除 HTTP 服务占用端口
curl -s --connect-timeout 5 http://<ip>:22/   # → 超时（不是 Web 服务）
```

**根因：** SSH 服务（sshd）处于异常状态 —— 能 accept TCP 连接但无法完成 SSH 握手。常见于：
- Hermes Desktop 设置了开机自启，与 SSH 服务冲突
- sshd 进程卡死（accept 连接但不处理协议）
- Windows OpenSSH 服务需要重启

**解决方案：** 需要用户本地操作：
```powershell
Get-Service sshd                    # 检查状态
Restart-Service sshd                # 重启 SSH 服务
```

### 常见问题

#### 端口 22 开着但不是 SSH
Hermes Desktop 或其他服务可能占用 22 端口。测试方法：
```bash
# 尝试 SSH
ssh -v -o ConnectTimeout=10 user@ip -p 22 2>&1 | head -20

# 尝试 HTTP（排除是 Web 服务）
curl -s --connect-timeout 5 http://ip:22/ | head -5

# 尝试 HTTPS
curl -s --connect-timeout 5 -k https://ip:22/ | head -5
```

### 端口 2222 完全不通
Windows OpenSSH 服务未启动：
- 需要本地操作：`Get-Service sshd` 检查状态
- 或通过 Windows 设置 → 系统 → 可选功能 → 检查 OpenSSH 是否安装

### Tailscale relay 延迟导致超时
当 `tailscale status` 显示 `relay "xxx"` 时，延迟可能 200-400ms。
SSH 默认握手超时可能不够，加大超时：
```bash
ssh -o ConnectTimeout=30 -o ServerAliveInterval=5 user@ip
```

## 诊断流程

```
1. ping 测基本连通性
2. tailscale status 看是否在线、是否走 relay
3. 端口扫描（22, 2222, 443, 3389）
4. 根据错误类型判断：
   - timeout → 检查服务是否启动
   - reset → 检查 SSH 服务状态
   - banner exchange timeout → 加大超时
5. 如果都不行 → 需要用户本地操作
```
