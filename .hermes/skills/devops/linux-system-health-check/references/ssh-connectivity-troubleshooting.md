# SSH 连通性排查 — 系统化诊断流程

## 使用场景
SSH 连接超时或失败，需要判断是网络问题、服务问题还是配置问题。

## 诊断流程（由外到内）

### Step 1: 确认机器是否在线
```bash
ping -c 3 -W 3 <ip>
```
- 成功 → 机器在线，问题在 SSH 服务层
- 失败 → 网络不通，检查 Tailscale/VPN/物理连接

### Step 2: 检查 Tailscale 状态
```bash
tailscale status | grep <ip/hostname>
```
- `active` + `relay "xxx"` → 通过中继连接，延迟高但可用
- `active` + 无 relay → 直连，延迟低
- 不出现 → Tailscale 不可达

### Step 3: 端口扫描（找开放端口）
```bash
for port in 22 80 443 2222 3389 8080 9119; do
  timeout 3 bash -c "echo >/dev/tcp/<ip>/$port" 2>/dev/null \
    && echo "端口 $port ✅ 开放" \
    || echo "端口 $port ❌ 关闭"
done
```

### Step 4: 逐端口尝试 SSH
```bash
# 尝试所有开放的 SSH 端口
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p <port> user@ip "whoami"
```

### Step 5: 解读错误信息

| 错误 | 含义 | 解决方向 |
|------|------|---------|
| `Connection timed out` | 端口未开放或被防火墙拦截 | 检查防火墙、SSH 服务是否启动 |
| `Connection reset by peer` | TCP 握手成功但 SSH 服务拒绝 | SSH 服务卡死/崩溃，需重启 sshd |
| `kex_exchange_identification: read: Connection reset` | SSH 协议握手阶段被重置 | 服务端 sshd 问题，可能是 max connections 或 fail2ban |
| `Permission denied (publickey,password)` | 认证失败 | 密钥/密码错误 |
| `Connection timed out during banner exchange` | 连上了但 SSH 握手超时 | 网络延迟太高（Tailscale 中继）或 sshd 响应慢 |

### Step 6: 端口误判排查
如果端口显示开放但 SSH 连不上，**可能是其他服务占了该端口**：
```bash
# 测试是否是 HTTP 服务
curl -s --connect-timeout 5 http://<ip>:<port>/ | head -5

# 用 telnet 看 banner
echo "" | timeout 5 telnet <ip> <port>
```

## 常见场景

### 场景 A：Windows SSH (2222) 不通
1. 检查 Windows OpenSSH 服务：`Get-Service sshd`
2. 检查端口转发（WSL）：`netsh interface portproxy show all`
3. 检查防火墙：`Get-NetFirewallRule -DisplayName "*SSH*"`

### 场景 B：WSL SSH (22) 握手被重置
1. WSL 的 sshd 可能没启动：`sudo service ssh restart`
2. 端口转发规则丢失：需要从 Windows 重新配置 netsh

### 场景 C：通过 Tailscale 中继延迟高
- 正常现象，中继延迟 200-300ms
- SSH 的 `ConnectTimeout` 设大一点（30s）
- `ServerAliveInterval=5` 保持连接活跃
