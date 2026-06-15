# Hermes Desktop 通过 SSH Tunnel 连接 WSL Hermes 后端

## 背景

Lulu 的 Win 笔记本上装了 Hermes Desktop，WSL（Ubuntu 26.04）通过 `install.sh` 装了 Hermes Agent CLI。目标：Desktop 通过 SSH Tunnel 模式连到 WSL 的 Hermes 后端，使所有屏幕（Chat、Sessions、Skills、Memory 等）都走远端 `~/.hermes`。

## 架构

```
Hermes Desktop (Windows)
  ↓ SSH Tunnel (127.0.0.1:22 → localhost:18642 → WSL:8642)
WSL Hermes Gateway (127.0.0.1:8642)
  ↓ 
MiMo API (https://api.xiaomimimo.com/v1)
```

Desktop 建立 SSH 隧道：`ssh -N -L localPort:127.0.0.1:8642 lulu@127.0.0.1`
所有后端请求通过隧道转发到 WSL 的 Hermes API（端口 8642）。

## 前置条件

- WSL 已安装 Hermes Agent（`curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`）
- WSL 的 SSH server 已运行（`sudo service ssh start`）
- 知道 WSL SSH 密码（Lulu 的 WSL：用户 `lulu`，密码 `111111`）
- Hermes Desktop 已安装在 Windows 上

## 连接步骤

### 1. 启动 Hermes Gateway（WSL 内）

```bash
# 杀死残留进程
pkill -f "hermes gateway" 2>/dev/null

# 清理旧日志
rm -f ~/.hermes/logs/gateway.log

# 后台启动网关（默认监听 8642 端口）
nohup hermes gateway run > ~/.hermes/logs/gateway.log 2>&1 &

# 确认监听
sleep 3
ss -tlnp | grep 8642
# 应显示 LISTEN
```

**注意：** `hermes gateway run` 不接受 `--port` 参数。端口 8642 是硬编码的默认值。

### 2. Desktop 配置 SSH Tunnel

打开 Hermes Desktop → Settings → Connection，选 **SSH Tunnel** 模式，填：

| 字段 | 值 |
|------|-----|
| SSH Host | `127.0.0.1` |
| SSH Port | `22` |
| Username | `lulu` |
| Private Key Pass | WSL 登录密码（`111111`） |
| Remote Hermes Port | `8642` |

### 3. 测试连接

点击 **Test SSH Connection**，应提示 `SSH tunnel connected!`。
然后 Save → 重启 Desktop。

### 4. 验证

- **Chat** — 能发消息并流式响应
- **Sessions** — 显示 WSL Hermes 的历史会话
- **Skills** — 显示 WSL 上已安装的技能

## SSH Tunnel vs Plain Remote 对比

| 功能 | Plain Remote (URL+Key) | SSH Tunnel |
|------|:----------------------:|:----------:|
| Chat | ✅ | ✅ |
| Sessions 列表 | ❌ 读本地 | ✅ 走SSH |
| Skills 管理 | ❌ 读本地 | ✅ 走SSH |
| Memory 编辑 | ❌ 读本地 | ✅ 走SSH |
| Gateway 状态 | ❌ 读本地 | ✅ 走SSH |
| Cron 任务 | ❌ 读本地 | ✅ 走SSH |
| Logs | ❌ 读本地 | ✅ 走SSH |
| 配置 | ❌ 读本地 | ✅ 走SSH |

Plain Remote 只代理聊天，所有管理页面读的是本地 `~/.hermes`。SSH Tunnel 才是真正的"远程全功能"模式。

## 已知问题

| 问题 | 原因 | 解决 |
|:----|:-----|:-----|
| SSH 连接超时 | WSL 休眠/重启后 SSH 服务掉了 | 重新 `sudo service ssh start` |
| Gateway 不在监听 | 后台进程被 kill 或 WSL 重启 | 重新 `nohup hermes gateway run &` |
| `Connection timed out during banner exchange` | WSL 关闭对话窗口后 SSH 端口转发失效 | 重开 WSL 并重启 SSH |
| `Permission denied (publickey)` | Windows 管理员默认只走密钥 | 改 `sshd_config` 注释掉 `Match Group administrators` 块 |