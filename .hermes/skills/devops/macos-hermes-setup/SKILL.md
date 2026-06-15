---
id: macos-hermes-setup
name: macOS Hermes Deployment
description: Deploy Hermes Agent on fresh macOS (Mac Mini) via remote delegation using Tailscale. Handles SSH enablement and firewall configuration for headless setup.
category: devops
trigger:
  - macOS setup
  - Mac Mini deployment
  - Tailscale remote access
  - fresh macOS install
  - no IPv4 macOS server
  - macOS server delegation
---

# macOS Hermes 部署流程

适用于全新安装的 macOS（特别是 Mac Mini M4），无公网 IPv4，需要快速远程部署 Hermes Agent 的场景。

## 核心决策点

**用户说"帮我远程配"时** → 立即停止手动步骤指导，切到 Tailscale 快速通道：
- 避免让用户等 Homebrew（会触发 Xcode CLT 几百 MB 下载）
- 优先 App Store 装 Tailscale，5 分钟内建立 SSH 通道

## 快速部署流程

### 1. Tailscale 接入（用户操作）
```bash
# 最快路径：App Store 搜索 "Tailscale" 安装登录
# 或命令行（如果已有 Homebrew）
brew install tailscale
sudo tailscaled install
sudo tailscale up

# 获取 IP
tailscale ip -4
# 输出: 100.x.x.x
```

### 2. 启用远程 SSH（用户操作）
```bash
# 开启远程登录（macOS 默认关闭）
sudo systemsetup -setremotelogin on

# 验证状态
sudo systemsetup -getremotelogin
```

### 3. 防火墙处理（如连接失败）
```bash
# 如果 SSH 连不上，关闭应用防火墙
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off
```

### 4. 代理连接（Agent 操作）
```bash
# 从 VPS 或已有服务器 SSH 到 Mac
ssh <username>@<tailscale-ip>

# 例：
ssh lulu@100.114.207.6
```

## 常见陷阱

| 问题 | 原因 | 解决 |
|------|------|------|
| `brew install` 卡住 | 正在后台下载 Xcode CLT | 改用 App Store 装 Tailscale，建立 SSH 后再装 Homebrew |
| `ssh: Connection refused` | 远程登录未启用 | `系统设置 → 通用 → 共享 → 开启远程登录` |
| SSH 启用后仍连不上 | 应用防火墙拦截 | 临时关闭防火墙或添加 SSH 例外 |
| Tailscale IP 不通 | 未登录或网络隔离 | 检查 Tailscale 状态栏图标显示 "Connected" |
| `Permission denied (publickey)` | 密钥认证失败 | 检查 authorized_keys 权限(600)、.ssh(700)、家目录(755) |
| 密钥配置后仍需密码 | 公钥格式错误或文件路径不对 | 确认公钥是一整行，末尾有换行；检查 sshd_config 中 AuthorizedKeysFile 路径 |
| `setremotelogin: 需要完全磁盘访问权限` | 终端没有权限 | 系统设置 → 隐私与安全性 → 完全磁盘访问权限 → 添加终端 |

## 技巧：快速检查清单

## SSH 密钥认证配置（免密登录）

SSH 连通后，建议配置密钥认证，避免每次输入密码。

### Mac 端添加公钥
```bash
# 1. 创建 .ssh 目录并设置权限
mkdir -p ~/.ssh && chmod 700 ~/.ssh

# 2. 添加跳板机/远程服务器的公钥
echo "ssh-ed25519 AAAAC3NzaC1lZ... <key-name>" >> ~/.ssh/authorized_keys

# 3. 关键：设置正确的权限！
chmod 600 ~/.ssh/authorized_keys
chmod 755 ~
ls -la ~/.ssh/
# 应该显示：
# - ~/.ssh 是 drwx------
# - authorized_keys 是 -rw-------
```

### 验证免密连接
从跳板机测试：
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null user@100.x.x.x "echo 'SSH OK'"
```

### 密钥认证失败排查
如果还是提示密码：
1. 检查公钥是否正确写入：`cat ~/.ssh/authorized_keys`
2. 确认权限严格正确（600/700/755）
3. 检查 SSH 服务配置是否允许密钥：`cat /etc/ssh/sshd_config | grep PubkeyAuthentication`
4. 查看 SSH 日志定位问题：`sudo log stream --predicate 'process == "sshd"' --info --debug`

## 后续步骤

一旦 SSH 连通，即可自动化完成：
1. 安装 Homebrew（现在可以等 Xcode CLT 了）
2. 安装 Python 3.12 + git
3. 配置 Cloudflare Tunnel
4. 部署 Hermes Agent

## 变体方案

**有屏幕共享需求时**：
- 系统设置 → 通用 → 共享 → 屏幕共享 → 开启
- 配合 Tailscale IP 可使用 VNC 客户端远程桌面

**长期稳定运行**：
- Tailscale 建议设置为 "始终在线"
- macOS 电源设置：防止休眠（系统设置 → 锁定屏幕 → 永不关闭显示器）