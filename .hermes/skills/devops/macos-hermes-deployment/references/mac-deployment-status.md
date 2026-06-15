# Mac Mini M4 部署状态

> 验证时间：2026-06-09 21:36（来源：SSH 实际检查）
> 最后更新：2026-06-09 工作阶段：Hermes 启动测试 —— 遇到 wecom/weixin 平台残留、DeepSeek key 全局失效

## 硬件

| 项目 | 规格 | 状态 |
|:----:|:----:|:----:|
| 内置 251GB SSD | disk3, APFS | ✅ 已用 ~46Gi/228Gi (20%) |
| 外接 1TB SSD | `/Volumes/ssd` (disk5, APFS) | ✅ 已挂载，1.4Gi 已用 |
| **4TB 机械盘** | 未检测到 | ❌ **未连接！** 需要用户插上 |

## 系统软件

| 组件 | 版本 | 安装路径 | 状态 |
|------|:----:|----------|:----:|
| macOS | 15.7.7 (Sequoia, 24G720) | 内置 SSD | ✅ |
| Homebrew | 5.1.15 | `/opt/homebrew` | ✅ |
| Python | 3.14.5 | brew | ✅ |
| Python | 3.9.6 | 系统自带 | ✅ 但不用 |
| Node | v24.16.0 (npm 11.13.0) | brew | ✅ |
| Git | 2.39.5 | Apple | ✅ |
| SQLite | 3.43.2 | 系统自带 | ✅ |

> ⚠️ **PATH 问题**：`/opt/homebrew/bin/` 不在 SSH 默认 PATH，远程执行 brew/node/python 需要 `eval "$(/opt/homebrew/bin/brew shellenv bash)"`

## brew 已装包

```
brotli, c-ares, ca-certificates, cloudflared, gettext, git,
hdrhistogram_c, icu4c@78, krb5, libgit2, libnghttp2, libnghttp3,
libngtcp2, libssh2, libunistring, libuv, llhttp, llvm, lz4,
mpdecimal, node@24, openssl@3, pcre2, pipx, pkgconf,
postgresql@16, python@3.12, python@3.14, readline, rust
```

## 核心服务

| 服务 | 端口 | PID/State | 状态 | 说明 |
|:----:|:----:|:---------:|:----:|------|
| **PostgreSQL 16** | 5432 | PID 863 ✅ | ✅ 运行中 | `pg_isready` 确认 |
| **LiteLLM** | 41111 | PID 852 ✅ | ✅ 运行中 | launchd 自启正常 |
| **Hermes Gateway** | 8645 | exit 78 ⚠️ | ⚠️ **已退出** | launchd 配了但进程挂了 |
| **SSH** | 22 | ✅ | ✅ | 远程可达 |
| **Tailscale** | — | PID 640 ✅ | ✅ 运行中 | IP: 100.114.207.6 |
| **Chrome** | — | PID 634 ✅ | ✅ | Google Chrome 常驻 |

## Agent

| Agent | 状态 | 说明 |
|-------|:----:|------|
| **Claude Code** | ✅ 已安装 | `/opt/homebrew/bin/claude` |
| **Playwright** | ❌ 未安装 | brew 未装，需安装 |
| **OpenClaw** | ❌ 未安装 | 需先装 Playwright |

## 网络

### Tailscale
- Mac IP：`100.114.207.6`
- 服务进程：运行中（launchd）

### cloudflared
- 已安装（brew）
- Tunnel：待确认是否已配置

## Hermes 配置状态

### 模型配置（用户已配置，但需改为主线路千帆）⚠️
```yaml
model:
  base_url: http://100.80.33.29:41111/v1
  default: deepseek-v4-flash
  provider: custom
  api_key: sk-no-key-required
```
- 主线路：VPS LiteLLM（`100.80.33.29:41111`）→ **但 DeepSeek key 已过期**，需改为千帆
- 备用线路：待配置（用户刚重生了 DeepSeek key，但 key 需要先验证有效性）
- **Key 验证教训**：`/v1/models` 返回列表 ≠ key 有效，必须测 `/v1/chat/completions`

### 平台配置（已清理）✅
- wecom 和 wecom_callback 段已从 config.yaml 和 gateway 段中删除
- weixin 已 `enabled: false`
- 注意：`enabled: false` 对 wecom 不够——必须彻底删除配置段

### 目录结构
- `~/.hermes/` 存在（35 项）
- `skills/`：31 个 skill
- `sessions/`：会话数据库存在
- `SOUL.md`, `auth.json` 存在

### 问题
- Hermes 退出码 78，launchd 未自动拉起
- 需要排查 stderr 日志 + 可能残留的 weixin/wecom 平台配置

## 存储架构

```
内置 251GB SSD（/dev/disk3）
├── Macintosh HD - Data: 30.3G    ← 用户数据
├── Macintosh HD: 11.3G           ← 系统
└── Preboot/Recovery/VM           ← 系统保留

外接 1TB SSD（/dev/disk5 → /Volumes/ssd）
├── Applications/                  ← 应用目录（已有）
├── .Spotlight-V100
└── .fseventsd

4TB 机械盘                       ← ❌ 未连接，无挂载点
```

## 当前剩余待办

| 优先级 | 事项 | 说明 |
|:------:|------|------|
| 🔴 P0 | **改主线路为千帆** | DeepSeek key 已过期，Mac Hermes 主线路需用 `qianfan-code-latest`，Tailscale 当前断了 |
| 🔴 P0 | **4TB 机械盘插上** | 用户操作 |
| 🔴 P1 | **新 DeepSeek key 验证** | 用户重生了 key，先验证是否有效（调 `/v1/chat/completions`，不要只测 `/v1/models`）|
| 🔴 P1 | **恢复 Tailscale 连接** | Mac 100.114.207.6 ping 不通，需用户检查 Mac 网络 |
| 🟡 P1 | 安装 Playwright | 需要装 |
| 🟡 P1 | 安装 OpenClaw | 需 Node 22+，用 nvm 切版本 |
| 🟡 P2 | 配 pg_jieba 中文分词 | 法条匹配前置 |
| 🟡 P2 | Skills 同步 | VPS → Mac 传输选定 skill |
| 🟠 P3 | 智能法制助手开发 | 核心应用，未开始 |