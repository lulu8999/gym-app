---
name: openclaw-gateway
description: Set up, configure, and manage OpenClaw Gateway with browser automation, PM2 persistence, and Chrome integration.
---

# OpenClaw Gateway Setup & Management

Use when the user needs to set up, restart, or troubleshoot the OpenClaw Gateway, especially with browser automation (Chrome/Playwright) and PM2 persistence.

## Common Pitfalls

### 1. `openclaw gateway` ≠ `openclaw gateway run`
`openclaw gateway` shows subcommands help — **does not start the server**.  
You MUST use `openclaw gateway run` to actually start the gateway.

**Wrong:**
```bash
openclaw gateway --port 9000 --auth none   # shows help, exits
```

**Correct:**
```bash
openclaw gateway run --port 9000 --auth none --bind loopback
```

### 2. `--auth none` requires `--bind loopback`
OpenClaw refuses to bind to LAN/WAN without authentication.  
With `--auth none`, you MUST also pass `--bind loopback`, or it exits with:

> Refusing to bind gateway to lan without auth.

### 3. Systemd service startup: `bind=lan` + `auth.mode=none` fails silently
When OpenClaw gateway is installed as a **systemd user service** (`openclaw gateway install`), it reads config from `~/.openclaw/openclaw.json`. If config has `"bind": "lan"` with `"auth": {"mode": "none"}`, the service starts and immediately fails with:

```
Refusing to bind gateway to lan without auth.
Set gateway.auth.token/password (or OPENCLAW_GATEWAY_TOKEN/OPENCLAW_GATEWAY_PASSWORD)
```

The `journalctl --user -xeu openclaw-gateway.service` log shows exit code 0 but state=failed.

**Fix:** Either change `"bind"` to `"loopback"`, or change `"auth"` → `"mode": "token"` if a valid token already exists in config:

```bash
# Edit ~/.openclaw/openclaw.json
# Option A: bind loopback
# "bind": "loopback"

# Option B: auth token (if token already configured)
# "auth": { "mode": "token", "token": "existing-token..." }
```

Then reinstall and restart:
```bash
openclaw gateway install
openclaw gateway start
```

### 3. PM2 startup: launcher respawn trap

The `openclaw` binary (openclaw.mjs) is a **launcher** that spawns the real process as a child for compile-cache management. PM2 tracks the parent launcher PID, not the child — so the process shows "online" but never listens on the port, and logs are empty.

**❌ Fails silently:** `pm2 start openclaw --name openclaw-gateway -- gateway --port 18789`

**✅ Correct approach (2 options):**

**Option A (recommended — bypass launcher):** Use the direct Node.js entry point:
```bash
pm2 start node --name openclaw-gateway -- \
  /home/lulu/.local/lib/node_modules/openclaw/dist/entry.js \
  gateway --port 18789
```

**Option B (bash wrapper):** Use a `bash -c` wrapper that keeps the process alive as the main PID:
```bash
pm2 start bash --name "openclaw-gateway" -- \
  -c "openclaw gateway run --port 9000 --auth none --allow-unconfigured --bind loopback"
```

### 4. `--allow-unconfigured`
If the gateway has no config file yet, this flag skips the config validation check.  
Safe to always include on first run.

## Chrome / Browser Setup

The gateway auto-enables the `browser` plugin when it detects Chrome/Chromium.

### Install Chrome on non-Debian systems (e.g. OpenCloudOS, RHEL, CentOS)

```bash
# Install dependencies first
yum install -y wget which libX11.so*

# Download Chrome directly from Google
wget -q -O /tmp/chrome.rpm 'https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm'

# Install (ignore missing dependencies, they're optional)
yum install -y /tmp/chrome.rpm 2>/dev/null || rpm -ivh --nodeps /tmp/chrome.rpm

# Verify
google-chrome --version
```

### Run headless (required for root / server environments)

```bash
google-chrome --no-sandbox --headless --disable-gpu --disable-dev-shm-usage
```

The gateway handles browser launch internally — no manual Playwright install needed if Chrome is on `$PATH`.

## WSL (Windows Subsystem for Linux) Deployment

Use when deploying OpenClaw on WSL (Ubuntu), especially when access is via Tailscale SSH from a VPS and GitHub is blocked.

### Prerequisites
- WSL2 with systemd enabled (`[boot]\nsystemd=true` in `/etc/wsl.conf`)
- SSH access via Tailscale (`ssh <user>@<wsl-ip>`)

### 1. Install Node.js (when GitHub/nvm are blocked)

Download the Linux binary tarball directly from nodejs.org:

```bash
# Download
curl -L 'https://nodejs.org/dist/v24.9.0/node-v24.9.0-linux-x64.tar.xz' -o /tmp/node.tar.xz

# Extract to ~/.local
mkdir -p ~/.local
tar -xf /tmp/node.tar.xz
cp -r node-v24.9.0-linux-x64/* ~/.local/

# Add to PATH (also add to ~/.bashrc)
export PATH=$HOME/.local/bin:$PATH
node --version  # Should show v24.x.x
```

### 2. Install OpenClaw

```bash
npm install -g openclaw@latest
openclaw --version
```

### 3. Migrate config from Windows native

```bash
# Copy config
cp /mnt/c/Users/<username>/.openclaw/openclaw.json ~/.openclaw/

# Update Windows paths → Linux paths
python3 -c "
import json
with open('/home/<user>/.openclaw/openclaw.json') as f:
    config = json.load(f)
config['agents']['defaults']['workspace'] = '/home/<user>/.openclaw/workspace'
# Update any other C:\\ paths to Linux paths
with open('/home/<user>/.openclaw/openclaw.json', 'w') as f:
    json.dump(config, f, indent=2)
"
```

### 4. Start via PM2 (bypass launcher respawn)

```bash
pm2 start node --name openclaw-gateway -- \
  /home/<user>/.local/lib/node_modules/openclaw/dist/entry.js \
  gateway --port 18789
pm2 save
```

### 5. Auto-start on WSL boot (systemd user service)

```bash
# Create service file
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/pm2-openclaw.service << 'EOF'
[Unit]
Description=PM2 process manager for OpenClaw Gateway
Documentation=https://pm2.keymetrics.io
After=network.target

[Service]
Type=forking
Environment=PATH=/home/<user>/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PM2_HOME=/home/<user>/.pm2
ExecStart=/home/<user>/.local/bin/pm2 resurrect
ExecReload=/home/<user>/.local/bin/pm2 reload all
ExecStop=/home/<user>/.local/bin/pm2 kill

[Install]
WantedBy=default.target
EOF

# Enable
systemctl --user daemon-reload
systemctl --user enable pm2-openclaw
loginctl enable-linger <user>
```

### Pitfalls

1. **File ownership from VPS write_file**: When writing files to WSL via the VPS agent's `write_file` tool, files end up owned by `root`. Fix by writing via SSH heredoc (`cat > file << 'EOF'`) instead.

2. **Chinese username paths**: WSL needs `/mnt/c/Users/<中文用户名>/` which often breaks with wildcards and shell globbing. Use `find` with `-maxdepth` or write scripts via base64 encoding.

3. **API keys stored in Windows Credential Manager**: Keys set via OpenClaw on Windows are NOT in the config file — they're in Windows Credential Manager. After migration, re-set keys:
   ```bash
   openclaw auth set-provider deepseek --api-key <your-key>
   ```

4. **Gateway port not immediately listening**: Even with PM2 showing "online", the gateway takes 5-10s to start the HTTP server (compiling cache, loading config). Wait 8s before health-checking.

## Windows Native Cleanup

After migrating to WSL, clean Windows native OpenClaw:

```powershell
# Stop and remove Scheduled Tasks
Stop-ScheduledTask -TaskName "OpenClaw Gateway" -ErrorAction SilentlyContinue
Stop-ScheduledTask -TaskName "OpenClaw Node" -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "OpenClaw Gateway" -Confirm:$false
Unregister-ScheduledTask -TaskName "OpenClaw Node" -Confirm:$false

# Uninstall npm global
npm uninstall -g openclaw

# Delete .openclaw directory (kill any locking processes first)
Stop-Process -Name "node" -Force  # if openclaw-related
Remove-Item -Recurse -Force "$env:USERPROFILE\.openclaw"

# Clean temp logs
Remove-Item -Recurse -Force "$env:TEMP\openclaw" -ErrorAction SilentlyContinue
```

**🔴 Key pitfall:** SQLite `.openclaw\state\openclaw.sqlite` files are locked by the running Node.js process. Kill the process first, then delete.

Windows 安装 SSH Server 可能失败（尤其非正式版如 10.0.26200）。踩坑记录和替代方案见 `references/windows-ssh-troubleshooting.md`。首选 Tailscale SSH。

## Mac (Apple Silicon) Installation

**Prerequisites**: OpenClaw requires **Node.js 22+** (not 20!).

```bash
# Install nvm (if not already)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Install Node 22 (required!)
source $HOME/.nvm/nvm.sh
nvm install 22
nvm use 22
node --version  # Should show v22.x.x

# Install OpenClaw
npm install -g openclaw
openclaw --version
```

**Pitfall**: OpenClaw 2026.6.1 requires Node 22+. If you install Node 20, you'll get dependency conflicts:
```
ERROR: Cannot install openclaw because these package versions have conflicting dependencies.
npm warn EBADENGINE Unsupported engine { node: '>=22.19.0' }
```

Use `nvm` to manage multiple Node versions — macOS doesn't use apt-get, so nvm is the easiest way.

## PM2 Status Parsing Gotcha

`pm2 show <name>` output includes ANSI color codes. When parsing programmatically
(via `subprocess` in Python), always strip ANSI escapes first:

```python
import re
clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw_output)
```

See `references/pm2-ansi-parsing.md` for full details and the JSON-alternative approach.

## Gateway Verification

After starting, verify:
```bash
# Check listening port
ss -tlnp | grep 9000

# Check logs for "ready" signal
pm2 logs openclaw-gateway --lines 5 --nostream
```

Healthy output includes: `http server listening (N plugins: ...; Xs)` and `ready`.

### Pitfall: Self-Heal Script Restart Loops

If a watchdog/self-heal script is running and repeatedly restarts the gateway, it creates
an infinite loop that kills all active user sessions. The loop:
1. Script detects "port not responding" → `pm2 restart hermes-gateway`
2. Gateway receives SIGINT → all active sessions interrupted
3. Gateway restarts, port takes a few seconds to come up
4. Script checks port again → still not ready → restarts again → **loop**

**Fix:** The self-heal script must have:
- Cooldown (≥120s between restarts of the same service)
- ANSI-stripped status parsing (PM2 output uses color codes)
- Duplicate detection (skip if same issue existed on previous check)
- Grace for transient states (process online but port not yet listening is normal)

See also `gateway-administration` skill → `references/self-heal-design.md` for
full watchdog design notes.

## OpenClaw → Hermes 迁移

迁移前需盘点源环境的记忆、技能、配置。完整勘查流程见：
📕 `references/remote-migration-inspection.md` — Tailscale + curl 远程盘点，含 SSH 失败时的 HTTP server 回退方案。

## Web Search via Tavily

OpenClaw Gateway has a built-in Tavily web search plugin. No browser needed:

```bash
openclaw infer web search --query "搜索关键词"
```

Returns 5 results with title, URL, and snippet. Provider is Tavily (needs API key in config).

This is useful for quick web lookups without launching a full browser instance.

## Overlapping Credentials Warning

The OpenClaw Gateway's config may contain wecom channel settings that **share credentials with Hermes' wecom_callback** (same corpId/agentId/secret). Even if the wecom plugin is "not installed" (so OpenClaw can't send messages through it), having stale config is a hygiene issue. See `references/credentials-conflict.md` for detection and cleanup.

## Plugin List (auto-enabled when dependencies exist)
- `active-memory`, `browser`, `canvas`, `device-pair`
- `file-transfer`, `memory-core`, `phone-control`, `talk-voice`

The browser plugin requires Chrome/Chromium on `$PATH`.

---

## Browser Setup for Headless VPS (Chinese VPS Specific)

> This section consolidates detailed browser setup from the now-archived `openclaw-browser-setup` skill. It covers special considerations for headless Linux VPS, especially in China.

### Root User Sandbox Restriction

Chrome默认不允许以 root 用户运行。OpenClaw 检测到时会报：
```
Running as root without --no-sandbox is not supported
```

**Fix:** 在 `openclaw.json` 中设置 `browser.noSandbox: true`：

```bash
python3 -c "
import json
with open('/root/.openclaw/openclaw.json') as f:
    d = json.load(f)
d.setdefault('browser', {})
d['browser']['noSandbox'] = True
with open('/root/.openclaw/openclaw.json', 'w') as f:
    json.dump(d, f, indent=2)
print('✅ noSandbox: true set')
"
```

### Gateway Pairing Scope Issues

OpenClaw 的 `browser-automation` 技能需要 `operator.admin` 作用域，但新安装时只有 `operator.pairing`。浏览器尝试升级作用域时会被网关拒绝，报：
```
device is asking for more scopes than currently approved
```

**Fix:** 修改 `paired.json`：

```bash
python3 -c "
import json
with open('/root/.openclaw/devices/paired.json') as f:
    d = json.load(f)

for device_id, device in d.items():
    # 添加 admin 作用域
    if 'operator.admin' not in device.get('scopes', []):
        device['scopes'].append('operator.admin')
    if 'operator.admin' not in device.get('approvedScopes', []):
        device['approvedScopes'].append('operator.admin')
    # 更新令牌作用域
    for role_name, token in device.get('tokens', {}.items():
        if 'operator.admin' not in token.get('scopes', []):
            token['scopes'].append('operator.admin')

with open('/root/.openclaw/devices/paired.json', 'w') as f:
    json.dump(d, f, indent=2)
print('✅ admin scope added')
"
```

### Chinese VPS Chrome Installation

如果 VPS 能连 `dl.google.com`（中国大陆部分VPS可以），直接下载RPM：

```bash
curl -sL -o /tmp/chrome.rpm \
  "https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm" \
  --connect-timeout 10 --max-time 60
dnf install -y /tmp/chrome.rpm
```

如果阿里云/清华镜像可用（注意：2025年后阿里云镜像已移除 Chrome RPM）：

```bash
# 配置国内镜像源（可能已失效）
```

**方案B：ungoogled-chromium（国内源可装，但 OpenClaw 可能检测不到）**

```bash
dnf search chromium
dnf install -y ungoogled-chromium
# 创建符号链接帮助检测
ln -sf /usr/bin/ungoogled-chromium /usr/local/bin/google-chrome
```

⚠️ 从中国大陆 VPS 下载 Playwright 的 Chromium 可能因 Google CDN 被墙而超时。

### Browser Verification Commands

```bash
# 检查 Chrome 是否安装
which google-chrome google-chrome-stable

# 检查 OpenClaw 是否检测到
openclaw browser status | grep -E "detectedBrowser|detectedPath"

# 检查 noSandbox 配置
grep noSandbox ~/.openclaw/openclaw.json

# 检查作用域
grep admin ~/.openclaw/devices/paired.json

# 检查网关是否运行
ss -tlnp | grep 18789

# 启动浏览器测试
openclaw browser start
openclaw browser open "https://example.com"
```

### Browser Automation Commands

核心操作模式：

1. `openclaw browser open <url>` — 打开页面
2. `openclaw browser snapshot <target>` — 获取页面结构
3. `openclaw browser act <target> --click <ref>` — 点击元素
4. `openclaw browser screenshot <target>` — 截图
5. `openclaw browser close <target>` — 关闭标签页
6. `openclaw browser tabs` — 列出当前标签页
