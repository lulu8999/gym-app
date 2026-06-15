---
name: hermes-tool-installation
description: "Install and configure Hermes ecosystem tools — deep crawling (Jina/Crawl4AI/Scrapling/CamoFox), token optimization (hcp/hermes-compress), search APIs (Tavily), and dependency conflict resolution."
version: 1.0.0
author: agent
metadata:
  hermes:
    tags: [devops, tools, installation, crawling, token-optimization, hcp]
---

# Hermes Tool Installation & Token Optimization

When the user asks to upgrade Hermes capabilities (crawling, search, token savings, etc.), follow this skill.

## User Workflow Preference

Lulu's standard upgrade flow:
1. **调研** — research available tools, compare options
2. **方案对比** — present comparison table with pros/cons
3. **确认** — wait for user approval before installing
4. **安装** — install tools (can use delegate_task for parallel)
5. **备份Git** — commit config changes to `/root` repo
6. **生成报告** — summary table with versions and status
7. **要API** — ask user for remaining API keys

**重要**：新工具安装前用户会问质量影响（如"RTK会降低输出质量吗"），必须先解释原理再动手。

---

## Network Proxy Configuration

If mihomo/clash proxy is running but tools fail to connect (e.g., Jina Reader API timeout), check proxy environment variables:

```bash
# Check if proxy is running
ps aux | grep -E "mihomo|clash" | grep -v grep

# Check proxy port (usually 7890)
cat ~/.config/mihomo/config.yaml | grep mixed-port

# Set proxy environment variables
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890

# Persist to .bashrc
echo '
# Network Proxy (mihomo)
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890
export HTTP_PROXY=$http_proxy
export HTTPS_PROXY=$https_proxy
export ALL_PROXY=$all_proxy' >> ~/.bashrc
```

**Pitfall**: GitHub access works (git uses system proxy), but `r.jina.ai` API requires explicit `http_proxy` environment variable.

---

## Deep Crawling Tools

### Tool Matrix

| Tool | Install | Best For | Pitfalls |
|------|---------|----------|----------|
| **Crawl4AI** | `pip install crawl4ai` | Batch crawling, markdown output | Requires lxml ~=5.3 |
| **Scrapling** | `pip install scrapling` | Anti-bot, stealth fetching | Requires lxml >=6.1 |
| **CamoFox** | `pip install camoufox` | Dynamic JS pages, fingerprint evasion | Browser binary download can timeout |
| **Jina Reader** | `npm install` from GitHub | Single page extraction | Needs GeoLite2 license for local mode |

### ⚠️ lxml Dependency Conflict

Crawl4AI (`lxml~=5.3`) and Scrapling (`lxml>=6.1`) have incompatible lxml requirements.

**Resolution**: Keep lxml 6.1.1 (Scrapling's requirement). Crawl4AI works fine with 6.1 despite the version constraint — only produces a compatibility warning, not a failure.

**Do NOT** let pip downgrade lxml to 5.x — it will break Scrapling.

### Verification Commands

```bash
# Crawl4AI
pip show crawl4ai && python3 -c "from crawl4ai import AsyncWebCrawler; print('OK')"
crwl crawl https://example.com -o markdown  # CLI test

# Scrapling
python3 -c "from scrapling import StealthyFetcher, Fetcher; print('OK')"

# CamoFox
python3 -c "from camoufox import Camoufox, AsyncCamoufox; print('OK')"
```

---

## ~~RTK (Rust Token Killer)~~ → 已被 hcp 替代

> ⚠️ **RTK 已于 2026-06-15 卸载**，被自研 `hcp`（hermes-compress）完全替代。以下内容仅保留供参考。

Terminal output compression tool — saves 60-90% tokens on CLI operations. **已被 hcp 取代，详见 `hermes-compress` skill。**

### 安装（已废弃，仅供参考）

**Official install.sh may timeout** (downloads Rust toolchain). Use precompiled binary instead:

```bash
# 以下命令不再需要 — RTK 已卸载
# RTK_VERSION="0.42.4"
# curl -fsSL -o /tmp/rtk.tar.gz ...
```

### Usage

```bash
# Wrap any command
rtk git log
rtk git status
rtk ls /path
rtk docker ps

# Auto-hook (optional, makes rtk transparent)
rtk init -g
```

**What `rtk init -g` does**:
- Registers global shell hook in `~/.claude/RTK.md`
- After init: `git status` auto-compresses through RTK
- Without init: must manually prefix `rtk git status`
- **Note**: This is for Claude Code integration. For Hermes, manual `rtk` prefix is still needed.

### Quality Impact

RTK does NOT reduce information quality — it removes:
- Redundant blank lines
- Decorative characters (borders, progress bars)
- Duplicate error stack traces
- Verbose log noise

Core information (commit hashes, file names, error messages, exit codes) is always preserved.

---

## Token Cost Management

### Strategy 1: hcp (hermes-compress) — 已替代 RTK

**RTK 已于 2026-06-15 卸载**，被自研的 `hcp` 工具完全替代。

- **Skill**: `hermes-compress`（详见该 skill 的完整文档）
- **位置**: `/root/hermes_compress/`（Python模块）+ `/usr/local/bin/hcp`（CLI wrapper）
- **用法**: `hcp git status`、`hcp env`、`hcp grep ...`
- **压缩率**: 60-99%，自动识别命令类型
- **替代原因**: RTK 需要用户手动调用，无法在 Hermes terminal 中自动生效。hcp 由 agent 内部自动调用。

**旧 RTK 安装说明（仅供参考，不再使用）**：

<details>
<summary>RTK 安装（已废弃）</summary>

```bash
# 曾经的安装方式，现已不需要
RTK_VERSION="0.42.4"
curl -fsSL -o /tmp/rtk.tar.gz \
  "https://github.com/rtk-ai/rtk/releases/download/v${RTK_VERSION}/rtk-x86_64-unknown-linux-musl.tar.gz"
tar -xzf /tmp/rtk.tar.gz -C /tmp/
cp /tmp/rtk /usr/local/bin/rtk
chmod +x /usr/local/bin/rtk
```

</details>

### Strategy 2: Auxiliary Model Configuration

Switch background tasks (compression, web extraction, memory writes) to cheap models:

```bash
# In ~/.hermes/config.yaml
auxiliary:
  compression:
    model: "google/gemini-2.0-flash"  # ~$0.10/1M tokens
    provider: "openrouter"
  web_extract:
    model: "google/gemini-2.0-flash"
    provider: "openrouter"
```

### Strategy 3: Display Cost Tracking

```bash
hermes config set display.show_cost true
hermes insights --days 7
```

### Strategy 4: Context Compression

```bash
hermes config set compression.enabled true
hermes config set compression.threshold 0.50
hermes config set compression.target_ratio 0.20
```

---

## Search API: Tavily

AI-optimized search engine. 1000 free calls/month.

### Configuration

```bash
# Set API key in .env
echo 'TAVILY_API_KEY=tvly-xxxxx' >> ~/.hermes/.env

# Or via hermes config
hermes config set search.tavily.api_key "tvly-xxxxx"
```

### Verification

```bash
# Test with curl
curl -X POST "https://api.tavily.com/search" \
  -H "Content-Type: application/json" \
  -d '{"api_key":"tvly-xxxxx","query":"test"}'
```

---

## 爬取能力评估

针对特定网站的爬取可行性测试结果，见 `references/chinese-legal-site-crawling.md`（中国法律网站测试）。

## Git Backup Pattern

After tool installation, always backup config:

```bash
cd /root
git add .hermes/config.yaml .hermes/auth.json
git commit -m "chore: install [tool names]"
git push origin main
```

**注意**: 不要用 `git add -A` — 会超时（太多未跟踪文件）。
