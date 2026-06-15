# Mac 作为后端推理节点（Backend Inference Node）模式

> 最后更新：2026-06-09
> 更新内容：🚨 平台禁用三步走（enabled:false 不够）、.env 变量自动发现陷阱、WECOM_HOME_CHANNEL 清理

> 适用场景：Mac 不直接面向用户/微信，仅作为 VPS 的**后端处理节点**，接收加密任务、调用模型推理、返回结果。

## 架构对比

### 标准模式（已有文档覆盖）
```
用户微信 → Mac Hermes（Gateway+平台）→ 模型 API
```

### 后端节点模式（本文档）
```
用户微信 → VPS Hermes（Gateway+平台）
                ├─ 简单任务 → VPS 自行处理
                └─ 核心任务 → Tailscale加密 → 
                   Mac Hermes（纯推理，无平台）→ VPS LiteLLM → 模型 API
                                                  → 结果返VPS → 回用户
```

## 核心特征

### 1. 🚨 平台禁用：三步走（enabled:false 不够）

如果从 VPS 同步了 config.yaml（含 weixin/wecom 配置）和 .env（含 WEIXIN_/WECOM_ 变量），Mac Hermes 启动后会**自动发现凭据并连接微信/企微**，导致给用户发消息（实测教训 2026-06-09）。

**`enabled: false` 无效的原因：** Hermes 平台自动发现会扫描 .env 中的 `WEIXIN_ACCOUNT_ID`、`WEIXIN_TOKEN`、`WECOM_BOT_ID`、`WECOM_SECRET` 等变量。只要这些变量存在，平台就会启动，`enabled: false` 配置项被忽略。

**正确禁用流程：**

**第一步：配置中禁用平台**
```bash
hermes config set platforms.weixin.enabled false
hermes config set platforms.wecom.enabled false
hermes config set platforms.wecom_callback.enabled false
```

**第二步：注释 .env 中的凭据变量（关键！）**
```bash
# 禁用微信自动发现
sed -i '' 's/^WEIXIN_/#WEIXIN_/' ~/.hermes/.env
# 禁用企微自动发现
sed -i '' 's/^WECOM_/#WECOM_/' ~/.hermes/.env
```

**第三步：删除 config.yaml 中的 WECOM 引用**
```bash
# 删除 WECOM_HOME_CHANNEL 等残留行
sed -i '' '/^WECOM_/d' ~/.hermes/config.yaml 2>/dev/null || true
```

**验证：** 启动 Hermes 后检查日志：
```bash
tail -5 ~/.hermes/logs/gateway-stderr.log
# ✅ 期望：No messaging platforms enabled.
# ❌ 不要看到：wecom failed to connect 或 weixin inbound
```

如果还有 wecom 重试，说明还有残留 WECOM_ 配置或 env 变量没清干净。

### 2. Mac Hermes API Key 策略

**主线路（依赖 VPS）：不存 Key**

模型调用指向 VPS 的 LiteLLM（通过 Tailscale 内网）：

```yaml
model:
  default: qianfan-code-latest     # 或 deepseek-v4-flash
  provider: custom
  base_url: http://100.80.33.29:41111/v1
  api_key: sk-no-key-required      # VPS LiteLLM 不需要认证
```

原理：VPS LiteLLM 监听 `:41111`，Mac 通过 Tailscale IP `100.80.33.29:41111` 访问。
LiteLLM 对内部请求不做认证，Mac 无需携带 API key。

> ⚠️ **实测 2026-06-09：DeepSeek key 全局失效** — VPS 和 Mac 使用同一 key 都无法调通 `/v1/chat/completions`（都返回 401），但 `/v1/models` 仍返回模型列表（这只是配置缓存）。结论：**永远用 `/v1/chat/completions` 验证 key 有效性，不要信 `/v1/models`。**
>
> 解决方案：主线路改为千帆（`qianfan.baidubce.com/v2/coding`），等 DeepSeek 新 key 再配备用。

**备用线路（VPS 离线时）：Mac 本地存 Key 直连**

在 Mac 的 `~/.hermes/.env` 中存一份有效的 API key，配置独立 provider：

```bash
hermes config set providers.deepseek-backup.provider custom
hermes config set providers.deepseek-backup.api_key_env DEEPSEEK_API_KEY
hermes config set providers.deepseek-backup.base_url https://api.deepseek.com/v1
hermes config set providers.deepseek-backup.default_model deepseek-chat
hermes config set providers.deepseek-backup.models '["deepseek-chat","deepseek-v4-flash"]'
```

切换命令（Hermes TUI 中）：
```
/model default                 ← 主线路（VPS LiteLLM，默认）
/model deepseek-backup         ← 备用（Mac 直连 DeepSeek）
/model qianfan-backup          ← 备用2（Mac 直连千帆）
```

### 3. 网络依赖：Tailscale 必须稳定

Mac 必须保持 Tailscale 在线，否则：
- ❌ 无法调用 VPS LiteLLM（模型推理全挂）
- ❌ VPS 无法转发任务到 Mac（处理节点失联）

**保持 Mac 不睡眠**：
```bash
sudo pmset -a sleep 0 networkoversleep 1 disksleep 0
```

**Tailscale 断开时的应急诊断**：
```bash
# 从 VPS 测连通性
ping -c 3 100.114.207.6
# 如果 ping 不通，检查：
# 1. Mac 是否睡眠（按键盘/鼠标唤醒）
# 2. Tailscale 是否在线（菜单栏图标）
# 3. Wi-Fi/网络是否正常
```

### 4. Hermes Gateway 配置示例（无平台版）

```yaml
gateway:
  port: 8645
  # 没有 platforms 段 — 不接任何聊天渠道

model:
  default: qianfan-code-latest
  provider: custom
  base_url: http://100.80.33.29:41111/v1
  api_key: sk-no-key-required

# 平台配置（weixin/wecom/telegram）全部删除
# .env 中 WEIXIN_/WECOM_ 变量全部注释掉
```

### 5. 启动验证

```bash
# 检查 Hermes 运行状态
ps aux | grep "hermes gateway" | grep -v grep
tail -5 ~/.hermes/logs/gateway-stderr.log

# 检查是否有平台连接
grep -E "platform|weixin|wecom" ~/.hermes/logs/gateway.log | tail -5
```

## 诊断清单（Hermes 启动失败排查）

```bash
# 1. 检查 Mac Hermes 进程
ps aux | grep "hermes gateway" | grep -v grep

# 2. 查最近日志
tail -20 ~/.hermes/logs/gateway.log

# 3. 查错误日志
tail -20 ~/.hermes/logs/errors.log

# 4. 检查模型配置
grep -A5 "^model:" ~/.hermes/config.yaml

# 5. 检查 .env 中是否有微信/企微变量残留
grep "^WEIXIN\|^WECOM" ~/.hermes/.env

# 6. 检查 config.yaml 中平台引用
grep -n "wecom\|weixin" ~/.hermes/config.yaml

# 7. 平台禁用后的预期日志
# Gateway started with no connected platforms
# No messaging platforms enabled.
# Gateway will continue running for cron job execution.
```

## 已知陷阱（2026-06 实测）

- **🚨 `enabled: false` 不能完全禁用平台** — Hermes 平台自动发现会扫描 .env 中的 `WEIXIN_*` 和 `WECOM_*` 变量。只要变量存在，平台就会启动。必须也注释掉 .env 中的对应变量。
- **🚨 `wecom` 即使删了配置也会重试** — 如果 .env 中有 `WECOM_BOT_ID`/`WECOM_SECRET`，config.yaml 中删了 `wecom:` 段也没用。必须同时删除 .env 中的变量 AND config.yaml 中的 `WECOM_HOME_CHANNEL` 行。
- **Mac Hermes 启动后微信收到一堆消息** — 从 VPS scp 的 config.yaml 和 .env 中有微信凭据。先执行上面"三步走"再启动。
- **不要 scp VPS 的 config.yaml 直接到 Mac 然后启动** — VPS config 有 weixin/wecom 平台配置和 API Key，直接复制会导致 Mac 尝试连接企微（用无效凭证），导致 gateway 反复退出。
- **DeepSeek 的 `/v1/models` 返回 ≠ key 有效** — 这是 LiteLLM 的配置缓存。用 `/v1/chat/completions` 发一条真实请求验证。
- **`eval $(brew shellenv bash)` 必须前缀** — SSH bash 不加载 zsh profile，每次远程执行需要手动添加。
- **Tailscale 断开后 SSH 超时** — Mac 睡眠或网络切换（Wi-Fi ↔ 有线）可能导致 Tailscale 掉线。ping 不通时先让用户检查 Mac 网络状态。