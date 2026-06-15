# Mac Hermes Gateway launchd 恢复流程

> 场景：Hermes Gateway 已配 launchd 服务但持续退出（exit code 78），需要排查并恢复。

## 退出码速查

| 原始值 | 退出码 | sysexits 含义 | 典型原因 |
|:------:|:------:|:-------------:|----------|
| 0 | 0 | 正常 | ✅ 运行中 |
| 19968 | 78 | EX_CONFIG | 配置错误：API Key 无效、wecom 凭证错、模型配置不对 |
| 19904 | 77 | — | 启动后立即退出 |

> launchd 的 `LastExitStatus` 是移位值：`19968 >> 8 = 78`（十进制）。

## 排查步骤

```bash
# 0. 确认 launchd 已注册但进程不在
launchctl list com.hermes.gateway
# 看 LastExitStatus — 非0表示已退出

# 1. 查错误日志（最重要）
tail -30 ~/.hermes/logs/errors.log
tail -30 ~/.hermes/logs/gateway.log
cat ~/.hermes/logs/gateway-stderr.log  # 可能为空，正常

# 2. 检查模型配置
hermes config show model

# 3. 检查平台配置（后端节点不应有 weixin/wecom）
grep -E "weixin|wecom" ~/.hermes/config.yaml
```

## 常见故障

### 1. 平台配置残留（wecom 凭证错误 或 weixin 自动发现）

**症状**（两种模式）：

**模式 A — wecom 凭证错误**：`gateway.log` 中反复报 `invalid bot_id or secret`，然后 gateway exit 78。

**模式 B — weixin 自动发现**：`gateway.log` 无报错，但 Gateway 启动后微信大量收到消息。原因是 `.env` 有 `WEIXIN_ACCOUNT_ID`/`WEIXIN_TOKEN`，Hermes 自动拉起 weixin 平台。

**模式 C — wecom enabled:false 但仍在重试**：设置了 `platforms.wecom.enabled: false`，但日志仍显示 `Starting reconnection watcher for 1 failed platform(s): wecom`。`enabled: false` 只阻止平台注册到 channel_directory，**不阻止初始连接尝试**。必须彻底删除配置段。
**原因**：从 VPS scp 的 config 带了 weixin/wecom 平台配置和 `.env` 环境变量。Mac 作为后端节点不需要这些平台。

**解决方法**：显式禁用平台（不要只删除配置段，因为 Hermes 会从 `.env` 自动发现 weixin）：

```bash
# 关闭 wecom（不删除配段，只是禁用重连）
hermes config set platforms.wecom.enabled false
```

> ⚠️ **注意**：`hermes config set` 只能修改现有字段，不能创建新的。如果 `platforms` 段下没有直接对应的 set 入口，需要手动编辑 `~/.hermes/config.yaml`。

**彻底删除 wecom 配置段（解决 enabled: false 仍重试的问题）**：

用 sed（macOS 需要 `-i ''` 而非 Linux 的 `-i`）：
```bash
# 备份
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak

# 找 wecom 段起止行号
WECOM_START=$(grep -n "^  wecom:" ~/.hermes/config.yaml | head -1 | cut -d: -f1)
WECOM_END=$(grep -n "^  wecom_callback:" ~/.hermes/config.yaml | head -1 | cut -d: -f1)
# 删除 wecom 段
sed -i '' "$WECOM_START,$((WECOM_END - 1))d" ~/.hermes/config.yaml

# 再删除 wecom_callback 段
CALLBACK_START=$(grep -n "^  wecom_callback:" ~/.hermes/config.yaml | head -1 | cut -d: -f1)
WEIXIN_START=$(grep -n "^  weixin:" ~/.hermes/config.yaml | head -1 | cut -d: -f1)
sed -i '' "$CALLBACK_START,$((WEIXIN_START - 1))d" ~/.hermes/config.yaml

# 从 gateway 段也清理
sed -i '' '/^    wecom_callback:/,/^    [a-z]/{ /^    wecom_callback:/d; /^      home_channel:/d; /^        channel:/d; /^        chat_id:/d; /^        platform:/d; }' ~/.hermes/config.yaml
```

或使用 Python（如果 PyYAML 可用）：
```python
import yaml
with open('/Users/lulu/.hermes/config.yaml', 'r') as f:
    config = yaml.safe_load(f)
config.get('platforms', {}).pop('wecom', None)
config.get('platforms', {}).pop('wecom_callback', None)
config.get('gateway', {}).get('platforms', {}).pop('wecom_callback', None)
with open('/Users/lulu/.hermes/config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
```

### 2. API Key 无效

**症状**：`errors.log` 中报 `HTTP 401: invalid_iam_token` 或 `AuthenticationError`。
**原因**：API key 过期/失效，或 provider 类型配错（`qianfan` 而非 `custom`）。

**排查**：
```bash
# 检查 provider 类型
grep -A5 "^model:" ~/.hermes/config.yaml | grep provider
# 必须为 custom（OpenAI 兼容 API 都走 custom）

# curl 直测试
KEY=$(grep "DEEPSEEK_API_KEY" ~/.hermes/.env | cut -d= -f2)
curl -s https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $KEY" | head -3
```

### 3. launchd 停止后未重新拉起

**症状**：`launchctl stop` 后进程消失，`launchctl start` 也没反应。

**解决方法**：
```bash
# 完整重启流程
launchctl stop com.hermes.gateway
sleep 3
# 确认进程已停
ps aux | grep hermes | grep -v grep
# 如果还在，等一会儿
sleep 2
# 重新启动
launchctl start com.hermes.gateway
sleep 3
# 确认进程在跑
ps aux | grep hermes | grep -v grep
# 或看 launchd 状态
launchctl list com.hermes.gateway
```

如果还是不行，尝试直接在前台运行看实时报错：
```bash
hermes gateway
```

（在 Mac 终端前台运行，报错会直接显示）

### 4. plist 中 bash 路径不存在（/opt/homebrew/bin/bash）

**症状**：`launchctl list` 显示 `exit code 78: EX_CONFIG`，`launchctl print` 显示 `runs = 1, last exit code = 78: EX_CONFIG, properties = keepalive | runatload | penalty box`，但手动运行 `hermes gateway` 正常。

**原因**：plist 中 `ProgramArguments` 的第一个参数指向了 `/opt/homebrew/bin/bash`，但 **Homebrew 并未安装 bash**（macOS 自带 bash 在 `/bin/bash`）。launchd 找不到可执行文件 → EX_CONFIG → 进 penalty box（禁止重试）。

**排查**：
```bash
# 验证 bash 路径是否存在
ls -la /opt/homebrew/bin/bash
# 若报 No such file or directory → 路径错误

# 系统自带 bash 在
/bin/bash --version
# GNU bash, version 3.2.57(1)-release (arm64-apple-darwin...)
```

**修复**：
```bash
# 修改 plist 中的 bash 路径
sed -i '' 's|/opt/homebrew/bin/bash|/bin/bash|' \
  ~/Library/LaunchAgents/com.hermes.gateway.plist

# 重新加载
launchctl bootout gui/501 ~/Library/LaunchAgents/com.hermes.gateway.plist 2>/dev/null
sleep 1
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.hermes.gateway.plist
sleep 8

# 验证
ps aux | grep 'hermes gateway' | grep -v grep
launchctl list com.hermes.gateway  # 应显示 PID 0（正常运行）
```

> ⚠️ **为什么之前手动跑正常？** SSH 会话默认用 `/bin/bash`（路径存在），launchd 用 plist 指定的路径（`/opt/homebrew/bin/bash` 不存在），所以一个能跑一个不能。

> ⚠️ **Homebrew 的 bash vs 系统 bash**：`brew install bash` 会安装新版 bash 到 `/opt/homebrew/bin/bash`（GNU bash 5.x），而 macOS 系统自带的是 `/bin/bash`（3.2.x，因 GPL 原因停留在旧版本）。如果 plist 创建时假设了 Homebrew bash 已安装，实际却没有，就会触发此问题。两种修复方向：
> 1. 改 plist 为 `/bin/bash`（快速修复）
> 2. `brew install bash` 安装 Homebrew bash（如需新版 bash 特性）

### 5. launchd bootout/bootstrap 失败（Error 5: Input/output error）

**症状**：`launchctl bootout` 和 `launchctl bootstrap` 都报 `Input/output error`，`launchctl list` 一直显示 `exit 78`。

**原因**：launchd 缓存了服务的退出状态并进入节流（throttle）模式，拒绝重试。从 SSH 远程操作时，`bootout` 无法正确清除 gui-domain 的缓存状态。

**解决方法 A — nohup 手动启动（SSH 远程时第一选择）**：

```bash
# 1. 直接前台测试配置是否有效
eval "$(/opt/homebrew/bin/brew shellenv bash)"
export PATH=$PATH:/Users/lulu/.local/bin
hermes gateway
# → 看到 "No messaging platforms enabled." 即配置正确
# Ctrl+C 停止

# 2. 后台运行（替代 launchd）
eval "$(/opt/homebrew/bin/brew shellenv bash)"
export PATH=$PATH:/Users/lulu/.local/bin
cd /Users/lulu
nohup hermes gateway > ~/.hermes/logs/gateway-stdout.log 2> ~/.hermes/logs/gateway-stderr.log &
```

**后续修复 launchd**：等用户在 Mac 本地终端时执行：
```bash
launchctl bootout gui/501 ~/Library/LaunchAgents/com.hermes.gateway.plist
sleep 3
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.hermes.gateway.plist
```
从本地执行通常能成功，因为 gui 域绑定的是当前桌面会话。

**解决方法 B — 本地 terminal 执行（Mac 前）**：直接开 Mac 终端执行：
```bash
# 杀掉旧进程
kill $(ps aux | grep 'hermes gateway' | grep -v grep | awk '{print $2}')
sleep 3

# 完整重启流程（本地可连 gui 域）
launchctl bootout gui/501 ~/Library/LaunchAgents/com.hermes.gateway.plist
sleep 3
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.hermes.gateway.plist
sleep 5

# 验证
ps aux | grep 'hermes gateway' | grep -v grep
launchctl list com.hermes.gateway  # 应无 exit code（正常运行）
```

> **原理**：launchd 的 gui 域只能从属于该用户的 GUI 会话内操作。SSH 属于非 GUI 会话，`bootout` 可能无法正确清理服务状态。`nohup` 绕过 launchd，让 Hermes 直接在后台运行，配置变更仍即时生效。

## 诊断技巧

- `gateway-stderr.log` 和 `gateway-stdout.log` 经常为空 — 这是正常的，核心日志在 `gateway.log` 和 `errors.log`
- exit 78 不一定是配置语法错，也可能是运行时平台连接失败后主动退出
- 如果 `launchctl start` 后马上又 exit 78，说明 lauchd 的 KeepAlive 触发了但进程即刻崩溃