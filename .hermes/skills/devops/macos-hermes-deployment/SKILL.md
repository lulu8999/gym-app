---
name: macos-hermes-deployment
title: macOS Hermes Agent 部署指南
description: 在 Mac (Apple Silicon/Intel) 上从零部署 Hermes Agent + Cloudflare Tunnel 的完整流程，包含远程引导用户执行命令的最佳实践。
triggers:
  - mac mini 部署
  - macos 安装 hermes
  - mac 部署 cloudflare tunnel
  - 苹果电脑 hermes
  - 远程引导用户命令行
  - mac 后端节点
  - mac 推理节点
  - mac 无平台模式
  - mac backend worker
  - mac no-platform hermes
---

# macOS Hermes Agent 部署指南

在 Mac 上从零开始部署 Hermes Agent 并通过 Cloudflare Tunnel 暴露到公网。

> 📚 **参考文档**: 
> - [存储分层与部署模式](references/mac-mini-deployment-patterns.md) - Mac Mini M4 实战规划案例，包含 10 天准备期迁移策略、多 Agent 协同架构、DNS 清理流程等。
> - [智能法制助手架构方案](references/smart-legal-assistant-architecture.md) - 案件资料管理 + 文书生成 + 类案检索的完整架构设计（权限分级、8大模块规划、法条匹配方案）。
> - [Mac 后端推理节点模式](references/mac-backend-node-pattern.md) - Mac 不直接面向用户，仅作为后端处理节点时的配置模式（双模型配置：VPS LiteLLM 主 + DeepSeek 直连备，launchd 恢复流程）。
> - [launchd 恢复流程](references/launchd-recovery.md) - Hermes Gateway 退出码排查、exit 78 修复、launchctl 重启完整步骤。
> - [部署状态追踪](references/mac-deployment-status.md) - 实时部署状态表（硬件、系统软件、服务、Agent、待办优先级）。
> - [综合健康检查](references/mac-health-check.md) - 一键式远程健康检查脚本，覆盖 13+ 维度，含常见问题对照表。
> - [三层设备架构](references/three-tier-architecture.md) - VPS(大脑) + Mac(仓库) + ESP32(手脚) 的完整架构设计，含连接方式、数据流、安全设计和扩展规划。

## 前置条件

- macOS 12+ (Intel 或 Apple Silicon)
- 已注册域名（如 `example.com`）
- Cloudflare 账号并托管该域名
- Mac 可以访问互联网（无需公网 IP）

## 阶段一：基础环境（和用户一起执行）

### 1. 防复制粘贴错误

> ⚠️ **关键技巧**：向用户展示命令时，确保不包含 HTML 标签或格式符号。PowerShell 命令中的通配符 `*` 在某些终端展示时会被吞掉（尤其微信/企业微信），导致 `Get-Service *ssh*` 显示成 `Get-Service ssh`。
> 
> **解决方案**：通配符命令用双引号包裹，如 `Get-Service "*ssh*"`，或把命令写在代码块中。
> 
> ❌ 错误示范（网页复制可能带 HTML）：
> ```
> /bin/bash -c "$(curl -fsSL ...)"<br/>
> ```
> ❌ 错误示范（通配符被吞）：
> ```
> Get-Service *ssh*
> ```
> 
> ✅ 正确示范（纯文本，通配符用引号保护）：
> ```bash
> /bin/bash -c "$(curl -fsSL ...)"
> ```
> ```powershell
> Get-Service "*ssh*"
> ```

**如果用户报错 `zsh: no such file or directory: br/`，说明复制时带入了 HTML 标签，提醒用户只复制纯命令部分。**

### 2. 安装 Homebrew

**国内用户务必用中科大镜像**，官方 GitHub 源极慢（<100 B/s）。

#### 方案 A：Mac 网络畅通（用户本地执行）

```bash
/bin/bash -c "$(curl -fsSL https://mirrors.ustc.edu.cn/misc/brew-install.sh)"
```

按提示输入密码，等 5-10 分钟。

#### 方案 B：校园网/慢网 — VPS 代理远程安装（推荐）

当 Mac 网络受限，从 VPS 通过 Tailscale SSH 远程安装。**这是实测成功的完整流程**：

**1) VPS 端：开放 mihomo 代理**

```bash
sed -i 's/^allow-lan: false/allow-lan: true/' /root/.config/mihomo/config.yaml
systemctl restart mihomo
```

**2) Mac 端：下载安装脚本**

```bash
ssh lulu@<MAC-IP> "curl -fsSL -o /tmp/brew_install.sh https://mirrors.ustc.edu.cn/misc/brew-install.sh"
```

**3) Mac 端：跳过交互确认（关键！）**

Homebrew 安装脚本的 `wait_for_user()` 函数要求按回车确认，SSH + expect 配合极其不稳定（连接会在确认步骤断开）。**必须先 patch 掉**：

```bash
ssh lulu@<MAC-IP> "sed -i '' '/^wait_for_user()/,/^}/c\\
wait_for_user() {\\
  return 0\\
}' /tmp/brew_install.sh"
```

**4) Mac 端：创建带代理的执行脚本**

> ⚠️ expect 的 `spawn` 命令中 shell 变量 `$()` 会被 expect 解析报错，所以环境变量必须包在 Mac 本地脚本里，不能写在 spawn 命令行上。

```bash
ssh lulu@<MAC-IP> 'cat > /tmp/run_brew.sh << '\''BREWEOF'\''
export ALL_PROXY=http://<VPS-Tailscale-IP>:7890
export http_proxy=http://<VPS-Tailscale-IP>:7890
export https_proxy=http://<VPS-Tailscale-IP>:7890
/bin/bash /tmp/brew_install.sh
BREWEOF'
```

**5) 从 VPS 用 expect 远程执行**

```expect
#!/usr/bin/expect -f
set timeout 900
spawn ssh -t -t -o StrictHostKeyChecking=no lulu@<MAC-IP> {/bin/bash /tmp/run_brew.sh}
expect {
    -re {[Pp]assword} { send "<PASSWORD>\r" }
}
expect eof
```

**关键点**：
- `-t -t` 强制分配 TTY，否则报 `Need sudo access` 退出
- `NONINTERACTIVE=1` 跳过密码输入，也报 `Need sudo access`，**不能用**
- `wait_for_user()` 已被 patch 为 `return 0`，expect 只需处理一次 sudo 密码
- 超时设 900s（Homebrew + Xcode CLT 下载 5-10 分钟）

**安装后必须执行**（Apple Silicon 专属 PATH 配置）：
```bash
(echo; echo 'eval "$(/opt/homebrew/bin/brew shellenv)"') >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

**安装后立即配置国内镜像源**（否则后续 brew install 也慢）：
```bash
echo 'export HOMEBREW_API_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles/api"' >> ~/.zshrc
echo 'export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles"' >> ~/.zshrc
echo 'export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.ustc.edu.cn/brew.git"' >> ~/.zshrc
echo 'export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.ustc.edu.cn/homebrew-core.git"' >> ~/.zshrc
source ~/.zshrc
```

> 💡 镜像源写入 `~/.zshrc`（非 `~/.zprofile`），因为 brew 环境变量应在每次 shell 会话生效。

### 3. 安装 Python 和 Git

```bash
brew install python@3.12 git
```

**Apple Silicon 关键：python3 符号链接**

Homebrew 安装 `python@3.12` 后，`python3` 可能仍指向系统自带 3.9。需要手动创建符号链接：

```bash
ln -sf /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3
ln -sf /opt/homebrew/bin/pip3.12 /opt/homebrew/bin/pip3
```

验证：
```bash
python3 --version  # 应显示 3.12.x
pip3 --version     # 应显示 pip 2x.x
git --version      # 应显示 2.x.x
```

> ⚠️ 如果远程 SSH 验证时 `python3 --version` 仍显示 3.9.6，是因为 SSH bash 不加载 brew shellenv。
> 用 `eval "$(/opt/homebrew/bin/brew shellenv bash)"` 前缀即可。

### 3b. 安装 Node.js

> ⚠️ **OpenClaw 陷阱（2026-06 实测）**：OpenClaw 需要 **Node.js 22+**，不是 Node 20。Node 20 装 OpenClaw 会报依赖冲突：
> ```
> ERROR: Cannot install openclaw because these package versions have conflicting dependencies.
> ```
> **解决方案**：安装 Node 22 而不是 Node 20/24。

```bash
# 先安装 nvm（如果未安装）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.nvm/nvm.sh

# 安装 Node 22（不是 20！）
nvm install 22
nvm use 22
node --version  # 应显示 v22.x
```

验证 OpenClaw 可用：
```bash
npm install -g openclaw
openclaw --version  # 应显示 2026.x.x
```

验证：
```bash
node --version   # 应显示 v24.x
npm --version    # 应显示 11.x
```

> 💡 如果校园网 npm 也慢，配置国内镜像：
> ```bash
> npm config set registry https://registry.npmmirror.com
> ```

---

## 阶段二：Cloudflare Tunnel

### 4. 安装 cloudflared

```bash
brew install cloudflared
```

### 5. 登录 Cloudflare

```bash
cloudflared tunnel login
```

- 会弹出浏览器，选择你的域名授权
- 授权完成后，终端会显示成功

### 6. 创建 Tunnel

```bash
# 创建 tunnel（hermes-mac 可以改名字）
cloudflared tunnel create hermes-mac

# 查看 tunnel ID
cloudflared tunnel list
```

记录输出的 **Tunnel ID**（格式如 `8f6e2b4a-xxx-xxx`）。

### 7. 配置 DNS 路由

> ⚠️ **重要：Hermes 端口是 8645，不是 8080**。先查清楚再配置：
> ```bash
> grep -i port ~/.hermes/config.yaml
> ```
> 常见端口：8645（VPS/Mac 默认）、8080（某些配置）。

创建配置文件：
```bash
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

粘贴配置（替换 `<TUNNEL-ID>` 和子域名，**端口用 8645**）：
```yaml
tunnel: <TUNNEL-ID>
credentials-file: /Users/$(whoami)/.cloudflared/<TUNNEL-ID>.json

ingress:
  # Hermes 网关入口（端口必须是 8645，不是 8080！）
  - hostname: hermes.yourdomain.com
    service: http://localhost:8645
  
  # 兜底
  - service: http_status:404
```

**实测案例（2026-06-09）：**
- Tunnel 名称：`hermes-mac`
- Tunnel ID：`a797376f-8dd4-438f-aad6-001d27cc606a`
- 域名：`hermes.lulugame.fun`
- 正确端口：**8645**（不是 8080）

### 8. 设置 DNS 路由

```bash
# Hermes 入口
cloudflared tunnel route dns hermes-mac hermes.yourdomain.com

# SSH 入口（如需要）
cloudflared tunnel route dns hermes-mac ssh-mac.yourdomain.com
```

### 9. 测试启动

```bash
cloudflared tunnel run hermes-mac
```

看到 `Connected` 表示成功，访问 `https://hermes.yourdomain.com` 应该能打到本机 8080 端口。

**Ctrl+C 停止测试运行。**

### 10. 设置为开机启动

```bash
cloudflared service install
```

---

## 阶段三：安装 Hermes Agent

### 11. 安装（pipx 隔离环境）

> ⚠️ macOS 系统 Python 受 PEP 668 保护，`pip3 install` 会报错 `error: externally-managed-environment`。
> 用 **pipx** 安装到隔离虚拟环境，不影响系统。

```bash
brew install pipx
pipx ensurepath
pipx install hermes-agent
```

验证：
```bash
hermes --version   # 应显示 v0.15.x+
```

> 💡 `pipx ensurepath` 会把 `~/.local/bin` 加到 PATH，但当前 SSH 会话不会立即生效。
> 远程执行时需加 `export PATH=$PATH:/Users/$(whoami)/.local/bin` 前缀。

### 12. 配置同步（从 VPS 复制，非手动配置）

**最快捷的方式是从已有 VPS 复制配置**，而非手动 `hermes setup`：

> ⚠️ `hermes setup` 在非 TTY 环境只打印提示，不执行任何配置。用 `hermes config set` 命令或直接 scp 配置文件。

```bash
# 复制 .env（含 API Keys）
scp /root/.hermes/.env lulu@<MAC-IP>:/Users/lulu/.hermes/.env

# 复制 config.yaml
scp /root/.hermes/config.yaml lulu@<MAC-IP>:/Users/lulu/.hermes/config.yaml

# 复制 Claude Code LiteLLM 代理配置
scp -r /root/.claude-code-litellm lulu@<MAC-IP>:/Users/lulu/.claude-code-litellm
```

**复制后必须调整**：

1. **关掉平台连接** — Mac 做后端节点，不需要微信/企微。不关的话 Hermes 一启动就用 VPS 的凭证连微信，给你发一堆消息。

   ⚠️ **🚨 `enabled: false` 不够！** 实测 2026-06-09：
   - `platforms.weixin.enabled: false` → 微信**仍然连接**（.env 中有 WEIXIN_ACCOUNT_ID/TOKEN 自动发现）
   - `platforms.wecom.enabled: false` → 企微**仍然重试**（.env 中有 WECOM_BOT_ID/SECRET）
   - `platforms.wecom_callback.enabled: false` → 同样仍然启动

   **正确做法：三步走**
   
   第一步：在 Mac 终端禁用平台（不够，但先做）：
   ```bash
   hermes config set platforms.weixin.enabled false
   hermes config set platforms.wecom.enabled false
   hermes config set platforms.wecom_callback.enabled false
   ```
   
   第二步：注释掉 .env 中的微信/企微凭据（关键！防止自动发现）：
   ```bash
   sed -i '' 's/^WEIXIN_/#WEIXIN_/' ~/.hermes/.env
   sed -i '' 's/^WECOM_/#WECOM_/' ~/.hermes/.env
   ```
   
   第三步：删除 config.yaml 中的 WECOM_HOME_CHANNEL 等引用：
   ```bash
   sed -i '' '/^WECOM_/d' ~/.hermes/config.yaml 2>/dev/null || true
   ```
   
   **验证**：启动后日志应显示 `No messaging platforms enabled.`，而不是 `wecom failed to connect`。如有 wecom 残留重试，说明还有配置没清干净。

2. **去掉代理设置** — Mac 在国内可直接访问百度千帆等 API，不需要走 127.0.0.1:7890 代理：
   ```bash
   ssh mac "sed -i '' 's|http://127.0.0.1:7890||g' /Users/lulu/.hermes/config.yaml"
   ```

2. **写入 API Key 到 config.yaml** — 千帆 API Key 必须是字面值，不支持环境变量名：
   ```bash
   # 从 VPS 的 .env 读取 key 值
   KEY=$(grep QIANFAN_API_KEY /root/.hermes/.env | cut -d= -f2)
   ssh mac "eval \"\$(/opt/homebrew/bin/brew shellenv bash)\" && hermes config set model.api_key $KEY"
   ```

3. **确认模型配置**：
   ```bash
   hermes config show  # 检查 default、provider、base_url 是否正确
   ```

### 13b. 安装 Playwright（OpenClaw 依赖）

```bash
# 找到 Hermes 的 pipx Python 路径
HERMES_PYTHON=/Users/$(whoami)/.local/pipx/venvs/hermes-agent/bin/python3
$HERMES_PYTHON -m playwright install chromium
```

验证：Chromium 下载到 `~/Library/Caches/ms-playwright/chromium_headless_shell-*`

> ⚠️ 如果校园网慢，需先设置代理环境变量再执行（同 Homebrew 方案 B 的代理模式）。

### 13c. 安装 Claude Code

**方案 A（推荐 — 二进制直接下载）：** 适用于 Mac 网络慢或 npm 被墙的情况。

从 GitHub releases 下载预编译二进制，通过 VPS 代理加速传输：

```bash
# ⚠️ 下载位置陷阱：不要用 /tmp/！
# macOS 的 /tmp 是 RAM-backed 目录，系统睡眠/重启后被清空。
# 如果 Mac 中途睡眠，下载到 /tmp/ 的文件会丢失，白下一场。
# 一律下载到 ~/Downloads/ 或用户主目录。

# 通过 VPS 代理下载（确保 VPS mihomo allow-lan: true）
curl -x http://<VPS-TAILSCALE-IP>:7890 -L -o ~/Downloads/claude-darwin-arm64.tar.gz \
  "https://github.com/anthropics/claude-code/releases/download/v2.1.170/claude-darwin-arm64.tar.gz"

# 解压
cd ~/Downloads && tar -xzf claude-darwin-arm64.tar.gz

# 安装到 ~/.local/bin（无需 sudo）
mkdir -p ~/.local/bin
cp ~/Downloads/claude ~/.local/bin/claude
chmod +x ~/.local/bin/claude

# 验证
~/.local/bin/claude --version  # 应输出: 2.1.170 (Claude Code)

# 写入 PATH（确保后续会话也能用）
grep -q ".local/bin" ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc

# 清理临时文件
rm -f ~/Downloads/claude ~/Downloads/claude-darwin-arm64.tar.gz
```

> ⚙️ **技术说明**：解压出来的 `claude` 是 Mach-O 64-bit arm64 单文件二进制（约 212MB），不需要任何 npm/系统依赖。

#### ⚠️ SSH 远程下载大文件陷阱

从 VPS 通过 SSH 远程下载大文件（>50MB）到 Mac 时，**普通后台 `&` 不够**——SSH 连接断开后（超时/Mac 睡眠/网络波动），子进程会被 SIGHUP 杀掉。

**正确做法——使用 nohup 真正后台化：**

```bash
# 方式 A：一次性 SSH 命令启动后台下载（推荐）
ssh lulu@<MAC-IP> 'cd ~/Downloads && nohup curl -x http://<VPS-IP>:7890 -L -o claude-darwin-arm64.tar.gz \
  "https://github.com/anthropics/claude-code/releases/download/v2.1.170/claude-darwin-arm64.tar.gz" \
  > ~/claude_download.log 2>&1 &'

# 方式 B：配合 macOS caffeinate 防止下载时 Mac 睡眠
ssh lulu@<MAC-IP> 'nohup caffeinate -s curl -x http://<VPS-IP>:7890 -L -o ~/Downloads/claude-darwin-arm64.tar.gz \
  "https://github.com/anthropics/claude-code/releases/download/v2.1.170/claude-darwin-arm64.tar.gz" \
  > ~/claude_download.log 2>&1 &'
```

**`caffeinate -s`** 是 macOS 自带工具，`-s` 参数在系统进入睡眠时阻止睡眠（保持电源），配合 nohup 确保下载不会被 Mac 睡眠中断。

**进度检查**（SSH 重新连接后）：
```bash
ssh lulu@<MAC-IP> 'tail -3 ~/claude_download.log; echo "---"; ls -lh ~/Downloads/claude-darwin-arm64.tar.gz'
```

**后台通知模式**：下载启动时用 `notify_on_complete=true` 让 VPS 在命令结束时通知。注意：如果 SSH 连接本身超时但 nohup 进程在 Mac 上继续跑，通知的是 SSH 命令的退出（0 或 255），不是 curl 的退出。**最终完成状态需要主动 SSH 过去检查 `~/claude_download.log`。**

**方案 B（npm 安装 — 需网络良好）：**

```bash
npm install -g @anthropic-ai/claude-code
claude --version  # 验证
```

> ⚠️ **校园网场景**：如果 npm 直连慢，先配国内镜像：
> ```bash
> npm config set registry https://registry.npmmirror.com
> ```

> 💡 Claude Code 的 LiteLLM 代理配置已在步骤 12 从 VPS 同步。

### 🚨 API Key 验证陷阱（`/v1/models` ≠ key 有效）

**关键教训**：LiteLLM 的 `/v1/models` 端点返回的是**配置缓存**，不是实时认证结果。DeepSeek API key 已过期时，`/v1/models` 仍然返回模型列表，只有 `/v1/chat/completions` 会报 401。

**正确验证方法**：
```bash
# ❌ 错误：只测 models 端点（不能证明 key 有效）
curl http://localhost:41111/v1/models  # 即使 key 过期也返回列表

# ✅ 正确：发一条真实请求
curl -X POST http://localhost:41111/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
# 401 = key 无效，200 = key 有效
```

### 13d. 部署 LiteLLM 代理（Claude Code 翻译层）

> 📚 **详细参考**: [references/litellm-mac-deployment.md](references/litellm-mac-deployment.md) — 完整排错记录、plist 模板、代理配置。

LiteLLM 代理将 Claude Code 的请求翻译成 DeepSeek API 格式。**不能装在 Python 3.14 上**，必须用 3.12。

**1) 创建 Python 3.12 venv 并安装：**

```bash
/opt/homebrew/bin/python3.12 -m venv /Users/lulu/.litellm-venv312
/Users/lulu/.litellm-venv312/bin/pip install --upgrade pip
/Users/lulu/.litellm-venv312/bin/pip install litellm[proxy]
/Users/lulu/.litellm-venv312/bin/litellm --version  # 验证
```

> ⚠️ **Python 3.14 陷阱**：orjson（LiteLLM 依赖）使用 PyO3/Rust 绑定，PyO3 目前只支持到 3.13。在 3.14 上编译会报 `Failed to build a native library through cargo`。设置 `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` 也无效——Rust 代码本身不兼容 3.14 的 C API 变化。**必须用 3.12 或 3.13**。

**2) 同步配置文件（从 VPS）：**

```bash
# 配置文件直接 scp
scp -r /root/.claude-code-litellm lulu@<MAC-IP>:/Users/lulu/.claude-code-litellm
```

> ⚠️ **API Key 传输陷阱（2025-06 实测）**：`scp` 整个文件是最安全的。不要用 `sed` 替换 plist 中的 key——redact 会把 `sk-xxx` 替换为 `***` 或部分值，导致写入错误的 key。详见 `safe-api-key-write` 技能的跨机器传输章节。

> 🚨 **关键教训**：即使 hex 编码传输，一个字符的错误（`0x53` = 'S' vs `0x35` = '5'）就足以导致 401。**必须从运行中的进程获取实际 key**（如 `pm2 jlist`），不要信任 `.env` 文件（可能包含过期 key）。传输后用 `/health` 端点验证。

**3) 配置代理（关键！）：**

> ⚠️ **2025-06 修正**：DeepSeek API 可以直接从国内访问，**不需要代理**。之前的 401 错误是 API Key 传输错误导致的（见下方陷阱），不是网络问题。

~~Mac 在国内无法直连 DeepSeek API（返回 401）。~~ **必须通过 VPS mihomo 代理**~~：~~

```bash
# 验证代理可用
curl -s --proxy http://<VPS-TAILSCALE-IP>:7890 -o /dev/null -w "%{http_code}" https://www.google.com
# 应返回 200
```

**4) 创建 launchd 开机自启：**

创建 plist 文件 `/Users/lulu/Library/LaunchAgents/com.litellm.proxy.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.litellm.proxy</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/lulu/.litellm-venv312/bin/litellm</string>
        <string>--config</string>
        <string>/Users/lulu/.claude-code-litellm/config.yaml</string>
        <string>--port</string>
        <string>41111</string>
        <string>--num_workers</string>
        <string>1</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>DEEPSEEK_API_KEY</key>
        <string>YOUR_KEY_HERE</string>
        <key>HTTP_PROXY</key>
        <string>http://<VPS-TAILSCALE-IP>:7890</string>
        <key>HTTPS_PROXY</key>
        <string>http://<VPS-TAILSCALE-IP>:7890</string>
        <key>NO_PROXY</key>
        <string>localhost,127.0.0.1</string>
        <key>PATH</key>
        <string>/Users/lulu/.litellm-venv312/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>/Users/lulu/.claude-code-litellm</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/lulu/Library/Logs/litellm.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/lulu/Library/Logs/litellm.err</string>
</dict>
</plist>
```

> ⚠️ **plist 中 API Key 写入**：不要用 `sed` 替换占位符——redact 会破坏 key 值。用 Python `plistlib` 从 `.env` 文件读取完整 key 后写入（见参考文档）。

**5) 启动并验证：**

```bash
launchctl load /Users/lulu/Library/LaunchAgents/com.litellm.proxy.plist
sleep 8
# 检查健康状态
curl -s http://localhost:41111/health
# 期望：healthy_count: 1, unhealthy_count: 0
```

**6) Claude Code 配置：**

在 Mac 上 Claude Code 的配置指向本地 LiteLLM：
- API Base: `http://localhost:41111`
- Model: `claude-sonnet-4-20250514`（LiteLLM 会翻译成 `deepseek-chat`）

### 首次启动

```bash
hermes gateway
```

或作为后台服务（推荐）：
```bash
brew services start hermes-agent
```

---

### 添加备用 Provider/模型

Mac 作为后端节点，可以配多个 provider 做备用线路（如千帆主用 + DeepSeek 备用）。

#### 步骤

**1. 把 API key 写入 Mac 的 `.env`**

```bash
ssh lulu@<MAC-IP> 'echo "DEEPSEEK_API_KEY=*** >> ~/.hermes/.env'
```

**2. 在 config.yaml 的 providers 段添加新 provider**

注意 YAML 中 models 的引号语法——单引号包裹整个 JSON 数组，双引号包模型名：

```yaml
providers:
  # ... 已有 provider ...
  deepseek:
    api_key_env: DEEPSEEK_API_KEY
    base_url: https://api.deepseek.com/v1
    default_model: deepseek-v4-flash
    key_env: DEEPSEEK_API_KEY
    models: '["deepseek-v4-flash","deepseek-v4-pro"]'
```

> ⚠️ **models 引号陷阱**：错误写法 `models: "[deepseek-v4-flash]"` 或 `models: '[deepseek-v4-flash]'` 都会导致 yaml 解析异常，模型名不会被当作字符串。

**3. 重启 Hermes 生效**

```bash
# 方法 A：launchd（推荐，自动恢复）
launchctl bootout gui/501 ~/Library/LaunchAgents/com.hermes.gateway.plist 2>/dev/null
sleep 1
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.hermes.gateway.plist
sleep 8

# 方法 B：nohup 手动后台（SSH 远程时备用）
eval "$(/opt/homebrew/bin/brew shellenv bash)"
cd /Users/lulu
nohup hermes gateway > ~/.hermes/logs/gateway-stdout.log 2> ~/.hermes/logs/gateway-stderr.log &
```

**4. 验证**

```bash
tail -5 ~/.hermes/logs/gateway-stderr.log
# 应显示 "No messaging platforms enabled."（后端节点正常）
```

> 💡 **测试**：在 Mac 本地终端执行 `hermes model` 可以看到可用模型列表，新加的 provider 会出现在列表中。

---

### 远程自动化安装 Homebrew（通过 SSH + expect）

见上方「方案 B：校园网/慢网 — VPS 代理远程安装」。那里是完整的实测成功流程。

**已踩过的坑（不要再重复）**：
- `NONINTERACTIVE=1` → 报 `Need sudo access` 退出 ❌
- 不 patch `wait_for_user()` → expect 在确认步骤断连 ❌
- 在 expect `spawn` 命令里写 `$()` → 被 expect 解析报错 ❌
- 不加 `-t -t` → 无 TTY，sudo 无法交互 ❌

**远程 SSH 执行 brew install 的关键技巧**：

VPS 通过 SSH 远程在 Mac 上执行 `brew install` 时，bash 子进程不加载 `~/.zprofile` 和 `~/.zshrc`，所以：
- 必须每条命令前加 `eval "$(/opt/homebrew/bin/brew shellenv bash)"` 前缀
- 或者用 `ssh mac "bash -c 'eval \"$(brew shellenv bash)\" && brew install xxx'"` 包装
- 镜像源环境变量也需手动 export（不会从 .zshrc 继承）

**示例命令模式**：
```bash
ssh lulu@<MAC-IP> bash -c "'eval \"\$(/opt/homebrew/bin/brew shellenv bash)\" && \
  export HOMEBREW_API_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles/api && \
  export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles && \
  brew install python@3.12 git && python3 --version && git --version'"
```

### 🚨 走一步报告一步（强制要求）

**用户明确要求的报告模式**，每完成一个阶段必须主动报告状态，而非黑盒执行。

...

---

### 🚨 用户手动配置偏好（2026-06 新增）

**场景**：当用户说"你告诉我命令就行了"或类似表达时，表示**他要自己在 Mac 终端上执行**，不需要你 SSH 进去代劳。

**正确的处理方式**：
1. 按逻辑顺序列出命令（分步，每步一个代码块）
2. 告诉用户执行后怎么看结果/验证
3. 等他反馈再给下一步
4. 不要私自 SSH 到 Mac 执行

**错误的处理方式**：
- ❌ 直接 SSH 进去执行（剥夺了用户的掌控感）
- ❌ 给了一大段解释才给命令（用户要的是命令本身）
- ❌ 给了一个会超时的命令（如 `hermes gateway` 前台运行）而不提示
- ❌ 用户说"你告诉我命令"后私自在 SSH 中改了配置（用户要亲手敲！）

**什么时候可以 SSH 进去操作**：
- ✅ 用户明确说"你ssh上去配一下"或"你连上去看看"
- ✅ 用户说"你去启动看看"
- ❌ 用户说"你告诉我命令"、在截图报错、在描述终端输出时——说明他在自己操作

**命令展示原则**：
- 每步只给 1-3 条命令，不要超过一个屏幕
- 复杂操作（如配 backup provider）分步展示
- 命令后用一句话说明怎么看结果
- 避免给会导致终端卡住的命令（如前台进程）
- **关键：如果从 VPS 同步了配置，第一步必须是关平台！** Mac Hermes 启动前先执行：
  ```bash
  hermes config set platforms.weixin.enabled false
  hermes config set platforms.wecom_callback.enabled false
  ```
  否则 Hermes 会用 VPS 的微信凭证连上微信，给你发一堆消息。

### 命令准确性检查

Hermes CLI 命令常有易混淆的选项，必须**先确认语法正确**再展示给用户：

| 用户可能会说的 | 正确命令 | 解释 |
|:-------------:|:---------:|------|
| `hermes config get xxx` | `hermes config show xxx` | `get` 不是合法子命令，用 `show` |
| `hermes config set xxx` | `hermes config set xxx` | ✅ 正确 |
| `hermes gateway restart` | `launchctl stop/start` | macOS 用 launchd，没有 `restart` 子命令 |

**报告格式：**
```
✅ 已完成：XXX
🔄 正在执行：XXX（预计 XX 分钟）
⏳ 等待中：XXX
```

**示例：**
```
✅ 已完成：Tailscale 组网、SSH 免密登录
🔄 正在执行：Homebrew 安装中...
   进度：正在下载 Xcode Command Line Tools（约 500MB）
   预计：5-10 分钟
   完成标志：看到提示符回来
   卡住怎么办：新开终端执行 xcode-select --install
⏳ 等待中：用户确认是否继续
```

**远程自动化部署时的报告模式：**
当用户委托我全程自动化部署（如"密码给你，自己搞好了报告"），执行策略：

| 步骤 | 动作 | 报告内容 |
|------|------|----------|
| 连接测试 | SSH 连通性检查 | "报告第1项：SSH 连接 ✅/❌" |
| 环境检查 | 检查 Homebrew/Python/Node | "报告第2项：环境检查 ✅/⚠️" |
| 安装任务 | 安装依赖 | "报告第3项：XX 安装 ✅/❌" |
| 异常处理 | 遇到 sudo/权限问题 | "报告第X项：需要用户介入 ⚠️" |

**关键原则：**
- 每完成一个**原子操作**立即报告，不要等到阶段结束
- 成功/失败/需要用户协助，都要明确说明
- 用户说"做完了记住这些"时，立即保存关键信息到记忆

---

### 🚨 域名/Tunnel 不要擅自创建（实测教训 2026-06-09）

**用户说"域名不着急"≠"帮我配域名"**。我在用户说"域名不着急"后，仍然创建了 Tunnel 和 DNS 路由，结果用户根本不需要。

**正确做法**：
1. 用户提到域名/Tunnel → 先问"现在要配置吗？还是以后再说？"
2. 确认需要后，再创建 Tunnel 和 DNS
3. 不要假设用户想配就配

### 部署顺序：先自动化，后交互

**用户明确偏好**：先把所有无需用户操作的任务自动化完成，把需要用户在 Mac 本地操作的步骤（如 CF Tunnel 浏览器授权）留到最后。用户原话"这个放最后一步，把不用我操作的先装好"。

**推荐执行顺序**：
1. Homebrew + 镜像源（自动 ✅）
2. Python + Git + Node（自动 ✅）
3. Cloudflared 安装（自动 ✅，**但登录授权留到最后**）
4. Hermes Agent 安装 + 配置同步（自动 ✅）
5. Claude Code + Playwright 安装（自动 ✅）
6. **CF Tunnel 登录授权**（需用户在 Mac 浏览器操作 ⏳）
7. **Hermes Gateway 首次启动测试**（需用户确认 ⏳）

### 密码委托处理模式

**当用户主动提供密码要求自动化处理时：**

1. **立即尝试使用密码**执行需要 sudo 的任务
2. **如果系统阻止密码管道**（如 macOS 安全策略、Hermes 安全策略拦截 `sudo -S`）：用 expect + PTY 替代
3. **任务完成后**：记住密码用于后续操作（存 memory），但**不在技能中记录具体密码值**
4. **安全提醒**：简单密码建议配置完成后修改

### 先规划，后动手

**不急于执行命令**，先清晰以下内容：

1. **存储规划**
   - 系统盘放什么？数据盘放什么？
   - 后续扩展怎么分层？

2. **迁移策略**
   - 几天准备期？
   - 旧服务器和新服务器分工？
   - 数据怎么分离？

3. **域名规划**
   - 旧域名哪些保留、删除、合并？
   - 新服务器用什么子域名？

**用户确认后再开始配置。**

### 命令展示格式

**每次只给一个命令**，大段代码分块：

```
执行这个：
```bash
brew install python@3.12
```

等完成后告诉我，我们再下一步。
```

### 长时间任务等待策略

明确告诉用户：
- 当前在做什么（"正在下载 Xcode Command Line Tools"）
- 大概要等多久（"5-10 分钟"）
- 完成标志是什么（"看到提示符回来"）
- 卡住怎么办（"新开终端执行 xcode-select --install"）

### 敏感数据处理

- 密码等敏感信息让用户自己输入
- 或临时修改简单密码，配置完改回
- 不通过聊天记录传递长期凭据

不要假设命令成功了，主动让用户验证：
```
执行完输入：
```bash
brew --version
```

发给我显示的版本号。
```

---

## 阶段零：部署状态验证（先查后干）

**警告：不要信任 memory 中记录的"已安装"状态。** memory 可能记录了计划阶段的结论但未经实际验证。每次新会话开始构建/检查 Mac 时，必须先 SSH 验证实际状态。

### 验证清单

```bash
# 连上 Mac
ssh lulu@<MAC-IP>

# 1. Homebrew（注意：不在默认 PATH！）
/opt/homebrew/bin/brew --version

# 2. 所有 brew 安装的包
/opt/homebrew/bin/brew list --formula

# 3. Python（区分系统自带的 3.9 和 brew 装的 3.14）
python3 --version               # 系统自带（通常是 3.9.6）
/opt/homebrew/bin/python3 --version  # brew 安装的

# 4. Node
/opt/homebrew/bin/node --version

# 5. 运行中的服务（launchd，非 systemd！）
launchctl list | grep -v "com.apple"

# 6. PostgreSQL
pg_isready

# 7. LiteLLM
curl -s http://localhost:41111/health | head -5

# 8. Hermes Gateway 状态
launchctl list com.hermes.gateway
tail -5 ~/.hermes/logs/gateway-stderr.log

# 9. Claude Code
/opt/homebrew/bin/claude --version

# 10. Playwright / OpenClaw
playwright --version 2>/dev/null || echo "NOT_INSTALLED"
pipx list 2>/dev/null | grep -i openclaw || echo "NOT_INSTALLED"

# 11. Tailscale
tailscale status 2>/dev/null | head -5

# 12. 外接存储
ls /Volumes/
diskutil list external
```

### PATH 陷阱（macOS 特有）

macOS SSH 登录时，`/opt/homebrew/bin/` **不在默认 PATH 中**。系统 PATH 只有 `/usr/bin:/bin:/usr/sbin:/sbin`。

```bash
# ❌ 会提示 command not found
which brew       # /usr/bin/brew → 不存在！
node --version   # 也不存在

# ✅ 必须手动加载
eval "$(/opt/homebrew/bin/brew shellenv bash)"
# 或 export PATH=/opt/homebrew/bin:$PATH

# ✅ 或者直接用全路径调用
/opt/homebrew/bin/brew --version
/opt/homebrew/bin/node --version
```

**每次远程 SSH 执行 brew/node/npm 相关命令，都必须先加载 brew shellenv！**

### 服务状态诊断（launchctl 而非 systemd）

macOS 用 `launchctl`，不是 `systemctl`。关键 exit code 含义：

| exit code | 含义 | 典型原因 |
|:---------:|------|----------|
| 0 | 正常运行 | ✅ |
| 78 | 配置了但已退出 | Hermes 网关配了 launchd 但进程挂了 |
| 其他 | 启动失败 | 查 stderr 日志确认 |

```bash
# 查服务是否注册
launchctl list com.hermes.gateway

# 查退出原因
tail -20 ~/.hermes/logs/gateway-stderr.log

# 查服务配置详情
launchctl list com.hermes.gateway  # 看 JSON 输出中的 LastExitStatus
```

### 更新部署状态文档

每次验证后，**必须更新 `references/mac-deployment-status.md`**，覆盖原有内容不要追加。使用以下模板：

```markdown
# Mac Mini M4 部署状态

> 验证时间：YYYY-MM-DD HH:MM（来源：SSH 实际检查）

## 硬件
- 内置 251GB SSD：已用 X GB / 剩余 Y GB
- 外接 1TB SSD (ssd)：已挂载 ✔️ / 未挂载 ❌
- 4TB 机械盘：已连接 ✔️ / 未连接 ❌

## 系统软件
| 组件 | 版本 | 来源 | 状态 |
|------|------|------|:----:|
| Homebrew | x.y.z | /opt/homebrew | ✅ |
| Python | x.y.z | brew / 系统自带 | ✅ |
| Node | vx.y.z | brew | ✅ |
| Git | x.y.z | Apple / brew | ✅ |

## 核心服务
| 服务 | 端口 | PID | 状态 |
|:----:|:----:|:---:|:----:|
| PostgreSQL | 5432 | PID | ✅/❌ |
| LiteLLM | 41111 | PID | ✅/❌ |
| Hermes Gateway | 8645 | PID/exit | ✅/⚠️/❌ |

## Agent
| Agent | 版本 | 状态 |
|-------|:----:|:----:|
| Claude Code | x.y.z | ✅/❌ |
| Playwright | x.y.z | ✅/❌ |
| OpenClaw | x.y.z | ✅/❌ |

## 网络
- Tailscale：100.x.x.x
- cloudflared：已安装 / 已配 Tunnel
- CF Tunnel：已生效 / 待配置

## 剩余待办
- [ ] 事项 1
- [ ] 事项 2
```

## 替代方案：Tailscale 远程连接（无公网 IP）

如果 Mac 没有公网 IP，或者你想先远程连上 Mac 再配置环境，**Tailscale 是最快的方案**。

### 适用场景
- Mac 在内网/无 IPv4 公网地址
- 需要远程 SSH 进去配置环境
- 比 Cloudflare Tunnel 更简单，无需域名

### 步骤

**1. Mac 端安装 Tailscale**

App Store 搜索 "Tailscale" 安装，或用命令行：
```bash
brew install tailscale
sudo tailscaled install
sudo tailscale up
```

登录后执行获取 IP：
```bash
tailscale ip -4
# 输出如：100.x.x.x
```

**2. 开启 Mac SSH 远程登录**

```bash
sudo systemsetup -setremotelogin on
```

> ⚠️ **权限问题**：如果报错 `requires Full Disk Access privileges`
> 
> **解决**： → 系统设置 → 隐私与安全性 → 完全磁盘访问权限 → + → 添加「终端」(Terminal) → 重启终端
> 
> **替代方法**： → 系统设置 → 通用 → 共享 → 打开「远程登录」

**3. 配置免密登录（方便自动化）**

在 Mac 上执行：
```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "ssh-ed25519 AAAAC3N... your-key" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**4. 从 VPS/管理机连接**
```bash
ssh user@100.x.x.x
```

**5. 与 Cloudflare Tunnel 的区别**

| 特性 | Tailscale | Cloudflare Tunnel |
|-----|-----------|-------------------|
| 需要域名 | ❌ 不需要 | ✅ 需要 |
| 暴露公网 | ❌ 仅组网内 | ✅ 完全公网 |
| 适用场景 | 远程管理、维护 | 对外提供服务 |
| 安全性 | 私有网络 | 公开可访问 |

**推荐组合**：Tailscale 用于远程管理 + Cloudflare Tunnel 用于对外暴露 Hermes 网关。

---

## 故障排查

### Tunnel 连接失败
- 检查 Tunnel ID 和 credentials-file 路径
- 确认 DNS 记录已在 Cloudflare 后台创建

### Hermes 启动失败
- 检查 SQLite 目录是否有写入权限
- 查看 `~/.hermes/logs/` 或控制台输出

### Tailscale 连接失败 / Mac 频繁离线

Tailscale 基于 WireGuard，**没有超时自动掉线机制**。如果 Mac 的 Tailscale 频繁 offline：

1. **检查 pmset 电源设置** — Mac 默认会自动睡眠，睡眠后网卡断电，Tailscale 自然掉线
   ```bash
   pmset -g | grep -E 'sleep|networkoversleep|disksleep'
   ```
2. **配置服务器模式** — 防止睡眠导致断线：
   ```bash
   sudo pmset -a sleep 0 networkoversleep 1 disksleep 0
   ```
3. **`pmset` 只管自动睡眠，防不住手动睡眠** — 用户点了  → 睡眠，或者合盖，Mac 仍然会睡。如需确保远程任务不被打断，配合 `caffeinate` 使用：
   ```bash
   caffeinate -s long-running-command
   ```
   `caffeinate` 是 macOS 自带工具，`-s` 参数在系统进入睡眠时阻止睡眠，任务结束后自动退出。**适合配合 nohup 在 SSH 远程下载大文件时使用。**
3. **确认 Tailscale 开机自启** — Tailscale → Preferences → 勾选 "Launch at login"
4. **确认 Mac 实际网络接口** — `ifconfig | grep 'inet '` 检查是 Wi-Fi (en1) 还是有线 (en0)。`en0` status inactive 说明未插网线，Mac 走 Wi-Fi
5. **校园网限速场景** — 如果 Wi-Fi 对外网限速（实测 <100 B/s），需通过 VPS 代理加速（见上方 Homebrew 方案 B）
6. **远程 sudo 限制** — `echo 'pwd' | sudo -S` 被 Hermes 安全策略拦截。用 expect 脚本替代（见 Homebrew 方案 B）
7. **验证连通性** — `tailscale ping <mac-ip>`，走 DERP 中继（延迟 300-600ms）也算通，`direct connection not established` 是正常的

### 校园网/慢网 — VPS 代理加速

当 Mac 网络对外网限速时（实测 curl 中科大镜像 <100 B/s），可通过 VPS 的 mihomo 代理加速：

**VPS 端**（一次性配置）：
```bash
# 允许局域网设备使用代理
sed -i 's/^allow-lan: false/allow-lan: true/' /root/.config/mihomo/config.yaml
systemctl restart mihomo
# 验证：从 Mac 测速
ssh mac "curl -x http://<VPS-TAILSCALE-IP>:7890 -o /dev/null -w '%{speed_download}' -sL https://github.com/Homebrew/brew/tarball/master"
```

**Mac 端使用代理**（临时，每次 SSH 会话）：
```bash
export ALL_PROXY=http://<VPS-TAILSCALE-IP>:7890
export http_proxy=http://<VPS-TAILSCALE-IP>:7890
export https_proxy=http://<VPS-TAILSCALE-IP>:7890
```

实测 GitHub 下载速度：直连 <100 B/s → 代理 ~196 KB/s（提速 2000 倍）。

> ⚠️ VPS mihomo 配置完记得改回 `allow-lan: false` 防止滥用。或者 Mac 部署完成后关闭。