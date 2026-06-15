---
name: macos-server-setup
description: 无公网IPv4的Mac设备远程配置指南（Tailscale组网、SSH开启、免密登录、Homebrew安装）
title: macOS Server Remote Setup
triggers:
  - macos setup
  - mac mini deploy
  - 无ipv4远程连接
  - tailscale ssh
  - macos环境配置
  - mac远程管理
---

# macOS Server 远程环境配置

适用于无公网 IPv4 的 Mac 设备（Mac Mini/Mac Studio）进行初始化配置和远程管理。

## 前置条件
- macOS 10.15+ (推荐 12.0+)
- 设备可以上网但无公网 IPv4
- 初始有物理访问权限（或已有人开启屏幕共享）

## 整体流程
1. **组网方案** — Tailscale 虚拟组网（比 CF Tunnel 更直接）
2. **开启 SSH** — 系统设置 + Full Disk Access
3. **免密登录** — VPS 公钥写入 Mac
4. **环境安装** — Homebrew + Python + 其他依赖

---

## Step 1: Tailscale 组网（推荐）

Mac 端（图形界面最简单）：
1. App Store 搜索 "Tailscale" 下载安装
2. 用 Google/微软/GitHub 账号登录
3. 记录 Mac 的 Tailscale IP：`100.x.x.x`

VPS 端：
```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
```

验证连通性：
```bash
# 从 VPS ping Mac
tailscale ping <mac-tailscale-ip>
```

> **为什么不用 CF Tunnel？** 对于 SSH 远程管理场景，Tailscale 更直接，无需域名和 ingress 配置。

---

## Step 2: 开启 SSH 服务

### 方法 A: 图形界面（推荐）
1. 系统设置 → 通用 → 共享
2. 打开「远程登录」(Remote Login)
3. 勾选「允许访问：所有用户」

### 方法 B: 命令行（需要 Full Disk Access）
```bash
# 给终端授权：系统设置 → 隐私与安全性 → 完全磁盘访问权限 → 添加 Terminal
sudo systemsetup -setremotelogin on
```

验证 SSH 服务：
```bash
sudo launchctl list | grep ssh
sudo lsof -i :22
```

---

## Step 3: 配置免密登录

在 **Mac** 上执行：

```bash
# 创建 .ssh 目录
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 写入 VPS 的公钥（替换为实际公钥）
echo "ssh-ed25519 AAAAC3N... root@your-vps" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 修复权限（关键！）
chmod 755 ~
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

在 **VPS** 上测试：
```bash
ssh -o StrictHostKeyChecking=no lulu@<mac-tailscale-ip> "whoami"
```

---

## Step 4: 安装 Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

安装后会提示执行两条命令把 brew 加入 PATH，按提示执行即可。

---

## 常见坑点

### 0. ⚠️ macOS Secure Token — 远程改密码不可行 ⚠️

#### 🔴 Mac 改密码后钥匙串同步提示（正常现象，非错误）

**场景**：在 Mac 上通过 `passwd` 或系统设置改了登录密码后，终端或弹窗显示：

```
# This tool does not update the login keychain password.
# To update it, run `security set-keychain-password` as the user in question,
# or as root providing a path to such user's login keychain.
```

**这是成功后的友情提醒，不是错误！** 🎉

- ✅ Mac 登录密码**已经改成功**
- ⚠️ 但**钥匙串**（存的 Wi-Fi 密码、网站密码、应用密码）密码还未同步
- 下次锁屏后再解锁，macOS 会自动弹窗问你要不要更新钥匙串密码

**两种处理方式：**

| 方式 | 操作 | 说明 |
|------|------|------|
| 不管它 | 什么都不做 | macOS 下次锁屏/解锁时自动弹窗，点 "Update Keychain" 即可 |
| 手动同步 | 本地或 `ssh -t` 跑 `security set-keychain-password` | 需输入旧钥匙串密码 → 新密码两次 |

**注意**：`security set-keychain-password` 也是交互式命令，通过 SSH 远程跑需要 `-t` 参数。

**症状**: 通过 SSH（密钥登录）远程改 Mac 用户密码失败
```bash
# ❌ 全部失败
sudo dscl . -passwd /Users/lulu <new-password>
# → eDSAuthFailed（要旧密码）

sudo sysadminctl -resetPasswordFor lulu -newPassword <new-pw>
# → "Operation is not permitted without secure token unlock"

sudo dscl . -create /Users/lulu Password <new-pw>
# → eDSAuthFailed（被 Secure Token 拦截）
```

**原因**: macOS Sequoia 15+ 引入了 **Secure Token** 保护机制。在启用 FileVault 的 Mac 上，只有拥有 Secure Token 的用户才能更改密码。即使通过 SSH 密钥以 `sudo` 执行也不行——这是苹果故意的安全设计，防止攻击者攻破 SSH 后直接改密码锁机。

**解决方案**:

| 方式 | 操作 | 适用 |
|------|------|------|
| ① Mac 本机操作 | 系统设置 → 用户与群组 → 改密码 | 最推荐，有物理/屏幕访问时 |
| ② 记得旧密码 | `ssh user@mac 'passwd'`，交互输入旧→新 | 远程可用，只需一次交互 |
| ③ macOS Recovery | 重启进恢复模式 → 终端 → `resetpassword` | 忘记密码时，需物理接触 |
| ④ 企业 MDM | 通过 MDM 下发密码重置命令 | MDM 托管设备 |

**验证密码是否匹配**:
```bash
# 不需 sudo，直接验证
dscl . -authonly lulu <password-to-test>
# exit 0 → 密码正确
# exit -14090 (eDSAuthFailed) → 密码错误
```

---

### 1. 复制粘贴 `<br/>` 问题 ⚠️
**症状**: `zsh: no such file or directory: br/`
**原因**: 从网页复制时粘入了 HTML 换行标签
**解决**: 提醒用户一次只复制一行，或直接使用代码块复制

### 2. SSH 免密不生效
**检查清单**:
- `~/.ssh` 权限必须是 700
- `~/.ssh/authorized_keys` 权限必须是 600
- 用户家目录权限不能是 777（会被 SSH 拒绝）
- 检查 `/etc/ssh/sshd_config` 中 `PubkeyAuthentication` 是否为 yes

### 3. Full Disk Access 缺失
**症状**: `setremotelogin: Turning Remote Login on or off requires Full Disk Access privileges`
**解决**: 系统设置 → 隐私与安全性 → 完全磁盘访问权限 → 添加 Terminal

### 4. 密码含空格
**症状**: 命令行传密码失败
**解决**: 使用交互式 SSH 或配置免密登录

### 5. SSH 免密未配置时的临时连接（expect）
**场景**: 用户还没有配置免密登录，但需要临时从 VPS SSH 到 Mac
**工具**: 使用 `expect` 工具处理交互式密码输入
**示例**:
```bash
# 安装 expect（VPS 上）
apt-get install -y expect  # Debian/Ubuntu
brew install expect        # macOS 本地

# 使用 expect 执行 SSH 命令
expect -c '
set timeout 20
spawn ssh -o StrictHostKeyChecking=no lulu@100.114.207.6
expect {
    "password:" {
        send "111111\r"
        expect "lulu@"
        send "df -h\r"
        expect eof
    }
    timeout {
        puts "Timeout"
        exit 1
    }
}
'
```
**注意**: 
- 这是临时方案，强烈建议后续配置免密登录
- 密码会出现在终端历史中，注意安全

### 6. Mac 存储规划：SSD 应用安装问题
**问题**: macOS 默认把应用装到 `/Applications`（内置硬盘），外接 SSD 不会被默认使用

**解决方案**:

#### 方案 A：DMG 安装后建软链接（推荐，最安全）
适用于：直接下载 `.dmg` 安装的应用

步骤：
1. 把 `.app` 拖到外接 SSD 的 Applications 文件夹
2. 在系统 `/Applications/` 建软链接指向 SSD

示例（以微信为例）：
```bash
# 在 SSD 创建 Applications 文件夹（只需执行一次）
mkdir -p /Volumes/ssd/Applications

# 假设 DMG 安装后，WeChat.app 在 /Applications/WeChat.app
# 移动到 SSD
mv /Applications/WeChat.app /Volumes/ssd/Applications/

# 建软链接，系统应用列表还能找到
ln -s /Volumes/ssd/Applications/WeChat.app /Applications/WeChat.app
```

#### 方案 B：Homebrew 指定安装目录
适用于：通过 Homebrew 安装的应用

```bash
# 安装时指定 appdir
brew install --appdir=/Volumes/ssd/Applications <app>

# 让 brew 能找到
export HOMEBREW_CASK_OPTS="--appdir=/Volumes/ssd/Applications"
```

---

### 7. Mac 存储分层架构（案例：Lulu 的 Mac Mini M4）

实际部署时常见的三层存储：

| 盘 | 挂载点 | 用途 | 容量 |
|---|--------|------|------|
| 内置 SSD | / | macOS 系统 + 必要App | 251GB |
| 外接 SSD | /Volumes/ssd | 工作/娱乐应用 | 1TB |
| 外接 4T 机械 | /Volumes/data | 案件数据库 | 4TB |

**配置流程**：
1. 外接 SSD 格式化为 APFS，创建挂载点
2. 外接机械同样处理
3. 每装一个 DMG 应用，按方案 A 移到 SSD 并建软链接

**注意**：macOS 无法修改默认安装位置（/Applications 是系统级硬编码），只能通过手动移动 + 软链接的方式实现。

---

## 用户协作模式（Lulu 偏好）

### 先规划，后动手
- 不急于执行命令
- 先讨论清楚架构、存储规划、域名分配
- 确认后再开始配置

### 分步报告
用户要求："走一步报告一步"
- 每完成一个阶段，主动报告状态
- 格式：✅ 已完成 / 🔄 正在执行 / ⏳ 等待中
- 让用户掌握进度，而非黑盒执行

### 敏感数据处理
- 密码等敏感信息让用户自己输入
- 或临时修改简单密码，配置完改回
- 不通过聊天记录传递长期凭据

## SSH 免密登录排错流程

如果按上述步骤配置后仍然需要密码登录：

1. **检查密钥格式**
   ```bash
   cat ~/.ssh/authorized_keys
   # 确保是 ssh-ed25519 或 ssh-rsa 开头的完整密钥
   ```

2. **确认权限**
   ```bash
   ls -la ~ | grep "^d"  # 家目录应该是 drwxr-xr-x (755)
   ls -la ~/.ssh/         # 目录应该是 drwx------ (700)
   ls -la ~/.ssh/authorized_keys  # 文件应该是 -rw------- (600)
   ```

3. **修复权限**
   ```bash
   chmod 755 ~
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/authorized_keys
   ```

4. **重新生成并添加密钥**
   - 在 VPS 上生成新的密钥对：`ssh-keygen -t ed25519 -f ~/.ssh/mac_mini`
   - 把公钥内容粘贴到 Mac 的 authorized_keys

5. **SSH 调试模式**（看具体拒绝原因）：
   ```bash
   ssh -v lulu@<mac-tailscale-ip>
   ```

## Mac 当服务器用：pmset 电源设置

Mac Mini/Mac Studio 当服务器时，默认电源设置会导致网络断连。必须配置 `pmset`：

```bash
# 查看当前设置
pmset -g

# 服务器模式推荐配置
sudo pmset -a sleep 0              # 禁止系统自动睡眠
sudo pmset -a networkoversleep 1   # 睡眠时保持网络连接
sudo pmset -a disksleep 0          # 禁止磁盘自动休眠
```

| 设置 | 默认值 | 服务器推荐 | 说明 |
|------|--------|-----------|------|
| `sleep` | 1（1小时后睡眠） | **0** | 系统不自动睡眠 |
| `networkoversleep` | 0 | **1** | 保持网络连接（防止 Tailscale 掉线） |
| `disksleep` | 10 | **0** | 磁盘不休眠（防止服务卡顿） |
| `displaysleep` | 10 | 180 或 0 | 无所谓，显示器不影响服务 |

### ⚠️ pmset 止不住手动睡眠

`pmset` 只阻止**自动**睡眠。用户手动触发睡眠（点击 → 睡眠、合盖）、系统更新后自动重启、或特定应用调用 `pmset sleepnow`，Mac 仍然会睡。

**远程任务保护 — `caffeinate`**：

```bash
# 保持 Mac 清醒执行命令（-s = 阻止系统睡眠触发）
caffeinate -s long-running-command

# 配合 nohup 用于 SSH 后台下载
nohup caffeinate -s curl -L -o ~/Downloads/bigfile.tar.gz https://example.com/bigfile.tar.gz > download.log 2>&1 &
```

`caffeinate` 是 macOS 自带工具，创建了一个电源断言阻止睡眠，任务完成后自动退出。**SSH 远程执行长时间任务时务必搭配 nohup + caffeinate 使用。**

### macOS /tmp 目录陷阱

macOS 的 `/tmp` 是 **RAM-backed** 目录（符号链接到 `/private/tmp`）。系统进入睡眠后重新唤醒或重启时，`/tmp` 内容可能被清空。

**教训**：不要通过 SSH 远程下载大文件到 `/tmp/`。如果 Mac 中途睡眠，文件丢失且下载进程也被 SIGHUP 杀掉。**一律下载到 `~/Downloads/` 或用户主目录。**

```bash
# ❌ 错误：下载到 /tmp（Mac 睡眠后消失）
curl -L -o /tmp/bigfile.tar.gz https://example.com/bigfile.tar.gz

# ✅ 正确：下载到用户目录
curl -L -o ~/Downloads/bigfile.tar.gz https://example.com/bigfile.tar.gz
```

### Tailscale 断线排查

Tailscale 基于 WireGuard，**没有超时自动掉线机制**，设计上就是长连接。如果 Mac 的 Tailscale 频繁 offline：

1. **检查 `sleep` 设置** — `pmset -g | grep sleep`，如果非0则 Mac 在空闲后进入睡眠，网卡断电
2. **检查 `networkoversleep`** — 即使 `sleep=0`，如果 `networkoversleep=0`，某些低功耗模式下网络仍会断
3. **确认 Tailscale 开机自启** — Tailscale → Preferences → 勾选 "Launch at login"，防止重启后忘记连
4. **验证连接** — 从 VPS 端：`tailscale ping <mac-ip>`，走 DERP 中继（延迟 300-600ms）也算通

### 远程执行 sudo 的注意事项

SSH 远程到 Mac 执行 `sudo` 命令时：
- 交互式密码输入不可用（非 PTY 模式）
- `echo 'password' | sudo -S` 被 Hermes 安全策略拦截（防暴力破解）
- **解决方式**：让用户在 Mac 本地终端执行 `sudo` 命令，或配置 NOPASSWD sudoers

## 后续步骤

环境就绪后，从 VPS 连入 Mac：
```bash
ssh lulu@<mac-tailscale-ip>
```

然后即可安装 Hermes、配置服务、部署应用等。

---

## 备选方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **Tailscale** | 简单、无域名、内网穿透 | 需要双方装客户端 | 个人设备远程管理 |
| CF Tunnel | 域名访问、可暴露 Web | 配置复杂、需域名 | 对外提供 Web 服务 |
| 内网穿透(frp/ngrok) | 灵活 | 需要中转服务器 | 临时调试 |
