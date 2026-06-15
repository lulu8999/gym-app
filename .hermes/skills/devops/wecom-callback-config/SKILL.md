---
name: wecom-callback-config
category: devops
description: 配置企业微信（WeCom）应用回调模式，让 Hermes 能接收企业微信用户发来的消息。涉及 Hermes 配置、Cloudflare 隧道、企微后台三方联动。
---

# WeCom 回调模式配置

## 背景

Hermes 有两种方式接入企业微信：

1. **wecom（AI Bot WebSocket）** — 直连企微 WebSocket，长链接收消息，支持图片/文件。需要创建 AI 机器人获取 Bot ID + Secret。
2. **wecom_callback（HTTP 回调）** — 启动 HTTP 服务器接收企微推送的消息回调。无需创建机器人，使用已有应用的 corpId + agentId + secret + token + encodingAESKey。

本技能覆盖 wecom_callback 方式。

## 前置条件

- Hermes 网关运行中
- Cloudflare Tunnel（cloudflared）已配置
- 企业微信管理后台可访问
- 已有的应用（如"超级大脑"）的配置信息：
  - corp_id（企业ID）
  - agent_id（应用ID/AgentId）
  - corp_secret（应用Secret）
  - token（用于签名验证的Token）
  - encoding_aes_key（消息加解密密钥）

## 配置步骤

### 1. 启用 wecom_callback 并填入凭证

```yaml
# ~/.hermes/config.yaml
platforms:
  wecom:                      # 停用AI Bot模式
    enabled: false
  wecom_callback:             # 启用回调模式
    enabled: true
    extra:
      corp_id: "wwxxxxxxxxxxxxx"
      corp_secret: "xxxxxxxx"
      agent_id: "1000002"
      token: "xxxxxxxx"
      encoding_aes_key: "xxxxxxxx"
      host: "0.0.0.0"
      port: 8645              # 默认端口
      # path: "/wecom/callback"  # 默认路径，可不配
```

用 hermes config set 写入：
```bash
hermes config set platforms.wecom_callback.enabled true
hermes config set platforms.wecom_callback.extra.corp_id "ww..."
hermes config set platforms.wecom_callback.extra.corp_secret "..."
# ... 以此类推
```

注意：hermes config set 不支持写嵌套 dict，可以逐项 set 或直接编辑 config.yaml

### 2. 添加 Cloudflare 隧道

```yaml
# ~/.cloudflared/config.yml
ingress:
  - hostname: callback.lulugame.fun
    service: http://localhost:8645
```

重启 tunnel：`pm2 restart wecom-tunnel`

验证：
```bash
curl http://localhost:8645/health
# → {"status":"ok","platform":"wecom_callback"}

curl https://callback.lulugame.fun/health
# → {"status":"ok","platform":"wecom_callback"}
```

### 3. 企微后台配置回调URL

登录 https://work.weixin.qq.com/wework_admin/loginpage_wx

→ 应用管理 → 选择你的应用 → 接收消息 → 设置回调URL

填写：
- **URL：** `https://callback.lulugame.fun/wecom/callback`
- **Token：** 和配置中 `token` 一致
- **EncodingAESKey：** 和配置中 `encoding_aes_key` 一致

点击保存，企微会发送 GET 请求验证 URL 有效性。验证通过即生效。

### 4. 重启网关

```bash
hermes gateway restart
```

验证状态：
```bash
hermes gateway status
```

### 5. 设置家目录（Home Channel）

首次回调连接成功后，系统会提示：
```
📬 No home channel is set for Wecom_Callback. A home channel is where Hermes delivers cron job results and cross-platform messages.
Type /sethome to make this chat your home channel, or ignore to skip.
```

**在企微 App 中和超级大脑的聊天框里输入 `/sethome`** 并发送（不是在终端里），系统会自动将当前会话设为家目录。

家目录的作用：所有 cron 任务输出、系统通知、跨平台消息都推送到这个会话。

注意：这是平台通道级别的设置，和用户权限系统（access.yaml 中的 admin/trusted/restricted）是两回事。设了家目录不代表其他用户能用——权限控制走的是 access.yaml。

### 6. 验证

在企业微信 App 中向该应用发送一条消息，查看网关日志：
```bash
journalctl --user -u hermes-gateway -n 30 --no-pager | grep -i "wecom"
```

## 依赖检查

回调模式需要以下 Python 包：
- `aiohttp`（HTTP 服务器）
- `httpx`（调用企微 API）
- `defusedxml`（安全解析 XML）

这些包通常在 Hermes 的 venv 中已安装。验证：
```bash
cd ~/.hermes/hermes-agent && source venv/bin/activate && \
python3 -c "import aiohttp,httpx,defusedxml; print('OK')"
```

## 常见问题

### 网关启动失败：`TypeError: string indices must be integers`

**症状**：`journalctl --user -u hermes-gateway` 报 `TypeError` 或 `KeyError: 'chat_id'`

**原因**：`home_channel` 配置格式错误。如果写成字符串 `home_channel: wecom_callback:sisu.`，解析器会报 `string indices must be integers`。如果只写了 `platform` 和 `channel` 没写 `chat_id`，会报 `KeyError: 'chat_id'`。

**正确格式**（在 `config.yaml` 的 `platforms.wecom_callback` 下）：
```yaml
home_channel:
  platform: wecom_callback
  channel: sisu.
  chat_id: sisu.
```

**修复命令**：
```bash
hermes config set gateway.platforms.wecom_callback.home_channel.platform wecom_callback
hermes config set gateway.platforms.wecom_callback.home_channel.channel sisu.
hermes config set gateway.platforms.wecom_callback.home_channel.chat_id sisu.
# 删除旧的字符串格式行（如果有）
sed -i '/home_channel: wecom_callback:sisu./d' ~/.hermes/config.yaml
hermes gateway restart
```

**诊断**：看网关日志定位具体错误：
```bash
journalctl --user -u hermes-gateway -n 30 --no-pager
```

### 消息不回复：用户被拒绝（Unauthorized）

**症状**：网关运行正常，但发消息没反应。日志有 `No user allowlists configured. All unauthorized users will be denied.`

**原因**：`.env` 中 `GATEWAY_ALLOW_ALL_USERS` 未设为 `true`，且没有配置用户白名单。

**修复**：
```bash
sed -i 's/# GATEWAY_ALLOW_ALL_USERS=false/GATEWAY_ALLOW_ALL_USERS=true/' ~/.hermes/.env
hermes gateway restart
```

**注意**：这是开放访问模式，任何人都能发消息。生产环境建议通过 `access.yaml` 配置用户白名单。

### `/sethome` 消息在 session DB 中看不到

`/sethome` 是网关内置命令，由 `_handle_set_home_command`（gateway/run.py）直接处理，**不会存储为普通用户消息**。所以用 `sqlite3 ~/.hermes/state.db "SELECT * FROM messages ..."` 查不到。

家目录信息存储在 `.env` 文件中：
```bash
grep WECOM_CALLBACK_HOME ~/.hermes/.env
# → WECOM_CALLBACK_HOME_CHANNEL=ww815119bb08398d37:KuHai
# → WECOM_CALLBACK_HOME_CHANNEL_THREAD_ID=
```

验证家目录是否已设置，检查 `.env` 中有没有对应的 `WECOM_CALLBACK_HOME_CHANNEL`。

### 自动注册不覆盖 wecom_callback 用户

现有的 `auto_register_users.py` 只查询 `source = 'weixin' OR source = 'wecom'` 的会话，**不包括 `source = 'wecom_callback'`**。所以通过企微回调模式发消息的用户不会被自动检测注册到 `access.yaml` 中。

要人工添加 wecom_callback 用户：
```bash
hermes access add <user_id> restricted wecom_callback
# 或直接编辑 ~/.hermes/access.yaml
```

### 查询回调模式下的用户消息

由于 wecom_callback 和 weixin 是**独立的会话源**，查询时需指定源：
```bash
# 查 weixin 的消息
sqlite3 ~/.hermes/state.db "SELECT * FROM messages m JOIN sessions s ... WHERE s.source='weixin'"

# 查 wecom_callback 的消息
sqlite3 ~/.hermes/state.db "SELECT * FROM messages m JOIN sessions s ... WHERE s.source='wecom_callback'"
```

两个平台的会话 ID、user_id、消息 ID 可能重合，注意区分。

### "aiohttp/httpx/defusedxml not installed"

虽然 `which python3` 能找到包，但网关进程可能找不到。检查 venv 是否正确：
```bash
ls -la /root/.local/bin/hermes  # 看链接指向哪个 venv
/root/.hermes/hermes-agent/venv/bin/python3 -c "import aiohttp,httpx,defusedxml; print('OK')"
```

### URL 验证失败

企微验证 URL 时发送 GET 请求带 `echostr`、`timestamp`、`nonce`、`msg_signature` 参数。服务器需解密返回明文 echostr。

- 检查隧道是否可达：`curl https://callback.lulugame.fun/wecom/callback`
- 返回 `signature verification failed` 是正常的（GET 不带企微参数时必然失败）
- 如果返回 404/502，检查隧道和端口配置

### 图片/文件支持（已实现）

wecom_callback 适配器已支持 image 类型的消息，在 `_build_event` 方法中提取 `PicUrl` 和 `MediaId`，以 `[图片] PicUrl=xxx MediaId=xxx` 格式传入 agent。

Agent 收到后下载图片（通过 `urllib` 或 `curl` 获取 `PicUrl`），然后调用 **Kimi 视觉 API**（`moonshot-v1-8k-vision-preview`）进行识别，返回中文描述。

如需查看实现细节：
- `references/wecom-callback-image-support.md` — 回调端提取图片的逻辑
- `references/kimi-vision-api.md` — Kimi 视觉 API 配置和调用方式

如需支持文件/语音等其他类型，同样在 `_build_event` 中增加对应 MsgType 的处理即可。

### 文件发送失败（send_message 发文件收不到）

**症状：** `send_message` 返回 success，但用户实际收不到 Excel/图片等文件附件。返回的 note 中 `chat_id` 显示为 `sisu.` 而非 `KuHai`。

**原因：** wecom_callback 平台的用户映射存在已知问题——KuHai 用户的文件投递目标被错误解析为 sisu.。微信（weixin）平台也不支持文件附件发送。

**替代方案：**
- 将文件内容转为 Markdown/文本格式直接发送（文本消息是通的）
- 通过 OpenClaw 网关的企业微信 AI Bot 模式发送
- 生成下载链接发送给用户

完整排障记录见 `references/file-sending-limitations.md`。

## 相关技能

- `wecom-message-push` — 从 cron 脚本发送企微消息
- `domain-routing` — Cloudflare 隧道配置
- `hermes-session-recovery` — 网关重启后的会话恢复

## 参考文件

- `references/callback-empty-body-debug.md` — 回调消息收不到（空body/XML解析错误）的排障记录
- `references/wecom-callback-image-support.md` — 图片消息的提取处理逻辑
- `references/kimi-vision-api.md` — Kimi 视觉 API 集成：配置、调用方式、费用估算、注意事项
- `references/home-channel-config-format.md` — home_channel 配置格式问题：字符串vs对象、修复步骤
