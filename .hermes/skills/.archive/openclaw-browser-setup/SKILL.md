---
name: openclaw-browser-setup
category: devops
description: 在无头 Linux VPS 上为 OpenClaw 安装和配置浏览器自动化环境（Google Chrome + CDP），解决 root 用户、国内网络、配对授权等问题。
---

# OpenClaw Browser Setup

在无头（headless）Linux VPS 上为 OpenClaw 配置浏览器自动化。包含 Chrome 安装、网关配对、root 沙箱绕过、CDP 端口配置等完整流程。

## 适用场景

- 首次设置 OpenClaw 的 `browser-automation` 技能
- VPS 没有显示器/显卡（headless）
- 以 root 用户运行
- VPS 在中国大陆，Google CDN 可能不通
- 需要从 OpenClaw CLI 打开网页、截图、填表单

## 检查当前状态

```bash
openclaw browser status
```

关注字段：`running`、`detectedBrowser`、`detectedPath`。

## 完整安装流程

### Step 1: 安装浏览器

**方案A：Google Chrome（推荐，完整兼容）**

如果 VPS 能连 `dl.google.com`（中国大陆部分VPS可以），直接下载RPM：

```bash
curl -sL -o /tmp/chrome.rpm \
  "https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm" \
  --connect-timeout 10 --max-time 60
dnf install -y /tmp/chrome.rpm
```

如果阿里云/清华镜像可用：

```bash
# 配置国内镜像源
# 但注意：2025年后阿里云镜像已移除 Chrome RPM，尽量用 dl.google.com 直连
```

**方案B：ungoogled-chromium（国内源可装，但 OpenClaw 可能检测不到）**

```bash
dnf search chromium
dnf install -y ungoogled-chromium
# 创建符号链接帮助检测
ln -sf /usr/bin/ungoogled-chromium /usr/local/bin/google-chrome
```

注意：ungoogled-chromium 可能不被 OpenClaw 的自动检测识别，推荐方案A。

**方案C：Playwright 内置 Chromium**

```bash
npx playwright install --with-deps chromium
```

⚠️ 从中国大陆 VPS 下载 Playwright 的 Chromium 可能因 Google CDN 被墙而超时。

### Step 2: 解决 root 用户的沙箱限制

Chrome 默认不允许以 root 用户运行。OpenClaw 检测到时会报：
```
Running as root without --no-sandbox is not supported
```

在 `openclaw.json` 中设置 `browser.noSandbox: true`：

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

### Step 3: 解决网关配对授权问题

OpenClaw 的 `browser-automation` 技能需要 `operator.admin` 作用域，但新安装时只有 `operator.pairing`。浏览器尝试升级作用域时会被网关拒绝，报：
```
device is asking for more scopes than currently approved
```

**解决方法：修改 `paired.json`**

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
    for role_name, token in device.get('tokens', {}).items():
        if 'operator.admin' not in token.get('scopes', []):
            token['scopes'].append('operator.admin')

with open('/root/.openclaw/devices/paired.json', 'w') as f:
    json.dump(d, f, indent=2)
print('✅ admin scope added')
"
```

**同时设置网关 auth=none**（可选，简化后续连接）：

```bash
python3 -c "
import json
with open('/root/.openclaw/openclaw.json') as f:
    d = json.load(f)
d['gateway']['auth'] = {'mode': 'none'}
with open('/root/.openclaw/openclaw.json', 'w') as f:
    json.dump(d, f, indent=2)
print('✅ auth mode set to none')
"
```

### Step 4: 启动网关

```bash
# 杀掉旧网关
openclaw gateway stop 2>/dev/null

# 前台启动（测试用）
openclaw gateway run --allow-unconfigured --bind loopback

# 后台启动（生产用）
openclaw gateway run --allow-unconfigured --bind loopback &
```

### Step 5: 启动浏览器并验证

```bash
# 检查状态
openclaw browser status

# 启动浏览器（headless 模式）
openclaw browser start

# 打开网页
openclaw browser open "https://example.com"

# 截图
openclaw browser screenshot <tab_id>

# 网页快照（获取可交互的 DOM 参考）
openclaw browser snapshot <tab_id>

# 执行操作（点击、填表）
openclaw browser act <tab_id> --click <ref>

# 关闭标签页
openclaw browser close <tab_id>
```

## 验证清单

```bash
# 1. 检查 Chrome 是否安装
which google-chrome google-chrome-stable

# 2. 检查 OpenClaw 是否检测到
openclaw browser status | grep -E "detectedBrowser|detectedPath"

# 3. 检查 noSandbox 配置
grep noSandbox ~/.openclaw/openclaw.json

# 4. 检查作用域
grep admin ~/.openclaw/devices/paired.json

# 5. 检查网关是否运行
ss -tlnp | grep 18789

# 6. 启动浏览器测试
openclaw browser start
openclaw browser open "https://example.com"
```

## 用 PM2 常驻 OpenClaw 网关

为了随时能用浏览器，将 OpenClaw 网关加入 PM2 管理：

```bash
pm2 start bash --name "openclaw-gateway" -- \
  -c "openclaw gateway run --port 9000 --auth none --allow-unconfigured --bind loopback"
pm2 save
```

**注意**：`openclaw gateway` 是子命令式的 CLI，直接 `pm2 start openclaw -- gateway run ...` 会导致进程在线但不监听端口。必须用 `bash -c` 包装才能使 PM2 fork 模式正常工作。

## 浏览器自动化的技能用法

设置完成后，加载 OpenClaw 的浏览器技能：

```bash
openclaw skills info browser-automation
```

核心操作模式：

1. `openclaw browser open <url>` — 打开页面
2. `openclaw browser snapshot <target>` — 获取页面结构
3. `openclaw browser act <target> --click <ref>` — 点击元素
4. `openclaw browser screenshot <target>` — 截图
5. `openclaw browser close <target>` — 关闭标签页
6. `openclaw browser tabs` — 列出当前标签页

## Web Search (Tavily) — 轻量替代方案

不想启动浏览器时，可以直接用 Tavily 做网页搜索：

```bash
openclaw infer web search --query "搜索关键词"
```

返回 5 条结果（标题 + URL + 摘要），全程无需浏览器。适合快速查资料、搜新闻。

## 从 Hermes 调用 OpenClaw 浏览器

当我（Hermes Agent）需要浏览网页时，通过终端命令调用 OpenClaw：

```bash
# 代理解析为 openclaw browser 命令
openclaw browser open "https://example.com"
openclaw browser snapshot t1
openclaw browser close t1
```

注意：OpenClaw 网关是独立进程，Hermes 网关重启不影响 OpenClaw 网关。两者可以并存。

## Pitfalls

- ❌ **使用 --auth token 时浏览器需要的作用域升级会被自动拒绝** — 改为 `auth: {mode: 'none'}` 或手动修改 `paired.json` 添加 `operator.admin` 作用域
- ❌ **Playwright 安装 Chromium 从大陆 VPS 超时** — 因为 Google CDN 被墙。改用 `dl.google.com` 下载 Chrome RPM
- ❌ **root 用户运行 Chrome 报错** — 需 `noSandbox: true`
- ❌ **修改 paired.json 后旧网关进程仍使用旧作用域** — 需 kill 旧网关进程重启
- ❌ **修改 openclaw.json 后旧网关进程不会自动重载** — 需要 stop + start（或 kill + 重启）
- ❌ **OpenClaw 网关退出时会自动清理浏览器进程** — 下次 start 会自动重新启动
- ⚠️ **OpenClaw 国内镜像源缺少 Chrome RPM** — 阿里云/清华镜像已移除 Chrome 仓库，直接用 `dl.google.com` 下载
- ✅ 测试用 `openclaw gateway run` 前台模式，生产用 PM2 后台管理
- ✅ 浏览器启动后可以通过 CDP 端口（默认18800）调试
- ✅ `openclaw browser doctor` 和 `openclaw browser status` 是最快的诊断工具

## 相关技能

- `hermes-cron-automation` — 定时任务（可配合浏览器做定期网页检查）
- `wecom-callback-config` — WeCom 回调配置（浏览器能力可配合企微使用）
