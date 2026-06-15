---
name: wecom-message-push
description: 通过企业微信（WeCom/企业微信）API 发送消息 — 从 cron 脚本或 agent 任务中集成企微通知
category: messaging
trigger: 用户需要将定时任务报告、监控告警、每日推送通过企业微信发送给指定用户
---

## 用户偏好：结果反馈风格

用户要求反馈操作结果时不要展示原始 API 返回码，直接说"成功了"或"失败了"就行。适用于所有涉企微 API 调用的场景。

---

## 企业微信消息推送

通过企业微信（WeCom）的 Corp API 发送消息到用户。适用场景：定时推送股票晨报、收盘报告、监控告警、每日天气等。

## 管理员面板与聊天记录查询

Hermes 的会话数据存储在 SQLite 数据库 `/root/.hermes/state.db` 中，可直接查询用户的聊天记录和 token 消耗。数据库结构和使用示例见 `references/hermes-state-db-schema.md`。查询本地数据库不消耗 API token，适合构建轻量 Web 管理面板（Flask）用于用户管理和聊天记录查看。

## 前置条件

在企微管理后台创建自建应用，获取以下信息：

| 参数 | 说明 | 获取位置 |
|------|------|---------|
| corpId | 企业 ID | 企微后台 → 我的企业 → 企业信息 |
| agentId | 应用 AgentID | 企微后台 → 应用管理 → 自建应用 |
| secret | 应用密钥 | 企微后台 → 应用管理 → 自建应用 → Secret |
| token / encodingAESKey | 消息回调（可选） | 仅回调需要 |

## 配置文件格式

```json
{
  "channels": {
    "wecom": {
      "enabled": true,
      "corpId": "wwxxxxxxxxxxxxx",
      "agentId": 1000002,
      "secret": "xxxxxxxxxxxxxxxxxx",
      "token": "xxxxxxxxxxxx",
      "encodingAESKey": "xxxxxxxxxxxx"
    }
  }
}
```

## 发送文件（Excel/PDF/图片等）

企业微信 API 支持发送文件（file 类型消息）。这是发送文件给企微用户的**唯一可靠方式**——Hermes 内置的 `send_message(media=...)` 工具无法成功发送文件附件（微信平台不支持，`wecom_callback` 路由有 bug 会送到错误 chat_id）。

**三步流程：** 获取 token → 上传文件 → 发送消息

```bash
# 参数
CORPID=ww815119bb08398d37
CORPSECRET=*** ~/.openclaw/openclaw.json 的 channels.wecom.secret 获取>
AGENTID=1000002
TOUSER=KuHai
FILE_PATH="/root/users-data/Lulu/约翰·列侬生平.xlsx"

# 1. 获取 access_token
TOKEN=*** -s \
  "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=${CORPID}&corpsecret=${CORPSECRET}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. 上传文件获取 media_id
MEDIA_ID=$(curl -s -F "media=@${FILE_PATH}" \
  "https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token=${TOKEN}&type=file" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['media_id'])")

# 3. 发送文件消息
curl -s -X POST \
  "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"touser\": \"${TOUSER}\",
    \"msgtype\": \"file\",
    \"agentid\": ${AGENTID},
    \"file\": { \"media_id\": \"${MEDIA_ID}\" }
  }"
```

**注意：** `media_id` 有效期 3 天，不可复用，每次发送前需重新上传。

## 发送消息脚本模板

创建一个 HTTP 调用脚本，放在 `~/.hermes/scripts/` 下供 cron 使用：

```python
#!/usr/bin/env python3
"""通过企微发送消息"""
import json, os, time, urllib.request

# ── 从配置文件读取凭据 ──
def load_config():
    path = '/root/.openclaw/openclaw.json'
    if not os.path.exists(path):
        # 回退：从环境变量或 .env 读取
        return None
    with open(path) as f:
        cfg = json.load(f)
    return cfg.get('channels', {}).get('wecom', {})

# ── 获取 access_token（带缓存）──
TOKEN_CACHE = '/tmp/wecom_token_cache.json'

def get_token(wc):
    # 尝试读缓存
    if os.path.exists(TOKEN_CACHE):
        with open(TOKEN_CACHE) as f:
            cached = json.load(f)
        if time.time() < cached.get('expires_at', 0) - 120:
            return cached['token']
    # 重新获取
    url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={wc[\"corpId\"]}&corpsecret={wc[\"secret\"]}'
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    token = data.get('access_token', '')
    if token:
        with open(TOKEN_CACHE, 'w') as f:
            json.dump({'token': token, 'expires_at': time.time() + 7200}, f)
    return token

# ── 发送文本消息 ──
def send_text(token, agent_id, user_id, text):
    body = json.dumps({
        'touser': user_id,
        'msgtype': 'text',
        'agentid': agent_id,
        'text': {'content': text}
    }).encode('utf-8')
    url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}'
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())  # 返回 {"errcode":0, "errmsg":"ok"}

# ── 封装调用 ──
def push_wecom(user_id, content, config=None):
    wc = config or load_config()
    if not wc:
        print('❌ 未找到企微配置')
        return False
    token = get_token(wc)
    if not token:
        print('❌ 获取 token 失败')
        return False
    result = send_text(token, wc['agentId'], user_id, content)
    return result.get('errcode') == 0
```

## 从 cron no_agent 脚本集成

在 `~/.hermes/scripts/` 下的脚本中直接调用企微 API：

```python
# stock_morning_report.py 典型结构
def main():
    # 1. 生成报告（运行股票分析、查询天气等）
    report = generate_report()
    weather = get_weather(city)
    message = f"📊 晨报\n\n{report}\n\n{weather}"
    
    # 2. 发送到企微
    for uid in ['KuHai', 'FengZaiQiShi', 'LuWeiFeng']:
        push_wecom(uid, message)
    
    # 3. stdout 输出（可选，cron no_agent 模式会投递）
    print(f"✅ 已发送: 用户列表")
```

## 企微用户管理

```python
# 列出所有用户
def list_users(wc):
    token = get_token(wc)
    url = f'https://qyapi.weixin.qq.com/cgi-bin/user/list?access_token={token}&department_id=1&fetch_child=1'
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    for u in data.get('userlist', []):
        print(f'{u["userid"]} — {u["name"]}')
```

## 已有封装脚本：send_wecom.py

该服务器已有现成的封装脚本 `/root/stock_analyzer/send_wecom.py`，自动管理 token 缓存，直接调用即可：

```bash
# 发送文本
python3 /root/stock_analyzer/send_wecom.py <user_id> <消息内容>

# 发送图片
python3 /root/stock_analyzer/send_wecom.py --image <user_id> <图片路径> [描述]

# 撤回消息
python3 /root/stock_analyzer/send_wecom.py --recall <user_id> <msgid>

# 列出所有用户
python3 /root/stock_analyzer/send_wecom.py --list-users
```

注意：该脚本**每次只支持单用户**，多发需循环调用。脚本从 `/root/.openclaw/openclaw.json` 读取配置。

## 推荐架构：报告文件 + 投递分离

推送内容丰富报告（如股市报告）时，**不要捕获被调用脚本的 stdout**。脚本的日志输出（`[WARN]`, `[OK]`, `📡 采集数据...` 等）会污染最终消息。

**正确做法：** 让被调用脚本写入报告文件，投递脚本只读文件 + 推送到企微：

```python
def get_latest_report(report_dir):
    """读取最新生成的报告文件，避免捕获含日志的 stdout"""
    import glob
    files = sorted(glob.glob(os.path.join(report_dir, 'report_*.md')), reverse=True)
    if not files:
        return None
    with open(files[0], encoding='utf-8') as f:
        return f.read().strip()

# 1. 静默运行（不抓 stdout）
subprocess.run(['python3', 'main.py', '--official'], cwd=STOCK_DIR,
    capture_output=True, timeout=120)

# 2. 读报告文件
report = get_latest_report(REPORT_DIR)

# 3. 推送到企微
for uid in RECIPIENTS:
    send_wecom(uid, f"📊 报告\n\n{report}")
```

## 消息记录与发送日志

### 为什么需要旁路日志

Hermes session DB 只记录「用户 → 助手」的交互会话，不记录助手单方面通过企微 API 推送的消息（cron 定时任务、手动发送的欢迎词等）。这些消息通过企微 API 直接发送，不会进入 Hermes 的消息系统。

### 日志系统架构

```
send_wecom() / cron no_agent 脚本
      │
      ▼
wecom_log.log(recipient, content)
      │
      ▼
~/.hermes/wecom_message_log.jsonl    ← 追加写入的 JSONL 文件
      │
      ▼
admin.lulugame.fun 面板读取显示
```

**核心文件：**

| 文件 | 作用 |
|------|------|
| `~/.hermes/scripts/wecom_log.py` | 日志模块：`log()` 记录、`get_messages()` 查询、`get_messages_grouped()` 按用户分组 |
| `~/.hermes/wecom_message_log.jsonl` | 数据文件：逐行 JSON，每行一条发送记录 |
| `~/.hermes/scripts/backfill_wecom_log.py` | 历史回填：从 cron 输出目录提取已发送消息记录 |

### ⚠️ 关键原则：只记录可验证的数据

**永远不要猜测或伪造数据：**

1. **时间戳** — 只能从以下来源获取（按优先级）：
   - cron 输出文件名 `YYYY-MM-DD_HH-MM-SS.md` → 解析为精确 Unix 时间戳
   - Hermes session DB `messages.timestamp` → 仅限通过 gateway 发送的消息
   - 企微 API 返回的 `create_time`
   - **不要**根据「大概什么时候」估时间，**不要**用相近的其他活动时间代替
2. **收信人** — 不要通过 assistant 消息中「提到」某用户来判断发给了谁
   - 正确来源：cron job 配置的收信人列表、手动记录的实际调用
3. **内容** — 从实际发送的文本记录中提取，不要从对话推断

### 历史消息回填

`backfill_wecom_log.py` 从 cron 输出目录中提取已发送消息：

```python
# 从 cron job 配置获取收信人
CRON_RECIPIENTS = {
    "f8b0d9210422": {"name": "晨报", "recipients": ["KuHai", "FengZaiQiShi", "LuWeiFeng"]},
    "43b1251c6d99": {"name": "收盘报告", "recipients": ["KuHai"]},
}

# 遍历 cron 输出文件，解析文件名中的精确时间戳
for job_dir in CRON_OUTPUT_DIR:
    recipients = CRON_RECIPIENTS.get(job_dir, ["KuHai"])
    for fname in sorted(os.listdir(job_dir)):
        ts = datetime.strptime(fname.replace('.md',''), "%Y-%m-%d_%H-%M-%S")
```

### 新用户自动注册

当新用户通过企微发送消息时，自动发现并注册为 restricted 用户。

**脚本：** `~/.hermes/scripts/auto_register_users.py`

工作流：
```
新用户发消息到企微 Bot → state.db 记录（含 user_id）
  ↓（每10分钟 cron 扫描）
auto_register 脚本检测到不在 access.yaml 中的 user_id
  ↓
自动加入 access.yaml（role=restricted）
  ↓
admin.lulugame.fun 自动显示新用户
  ↓
cron 投递通知到管理员微信
```

**部署命令：**
```bash
hermes cron create --schedule "every 10m" \
  --script auto_register_users.py \
  --no-agent --name "🆕 新用户自动检测注册"
```

## 企微用户列表

本服务器实际用户：

| userid | 姓名 | 身份 |
|--------|------|------|
| `KuHai` | 苦海 | Lulu |
| `FengZaiQiShi` | 风再起时 | 师父（徐昕） |
| `LuWeiFeng` | 陆伟锋 | 老爹 |
| `LuHaiTian` | 陆海天 | — |

企微应用名：**超级大脑**，agentId=1000002

## 新用户注册流程

新增企微用户时，执行以下步骤：

1. **在企微添加用户**（如已有则跳过）
2. **在 `/root/users-data/` 创建用户目录**，放入 `profile.json`
   - Lulu + 陆海天 → `Lulu_LuHaiTian/`
   - 师父 → `师父_FengZaiQiShi/`
   - 老爹 → `老爹_LuWeiFeng/`
   - 其他人 → 创建以用户名为名的目录
3. **发送定位链接**：通过企微发送 `https://loc.lulugame.fun/?user=用户名`
   - 解释：点开链接授权位置，用于推送天气信息
4. **用户提交位置后**：反查城市，将城市名写入 profile.json 的 `city` 字段
5. **在定时报告脚本中引用城市字段**来获取天气

## 接收企微消息（两种方式）

Hermes 提供两种接收企微消息的方式。注意它们是**互斥**的，只能启用一个，不能同时运行。

### 方式一：AI Bot WebSocket（wecom）

使用企业微信的 **AI Bot WebSocket 网关**（`wss://openws.work.weixin.qq.com`）接收来自用户的消息。

#### ⚠️ 关键误区：Bot ID ≠ AgentId

**Bot ID 不是自建应用的 AgentId！** 典型错误就是把 AgentId（如 1000002）当作 Bot ID 配置，导致 WebSocket 连接失败（errcode=853000）。

| 概念 | 示例 | 来源 |
|------|------|------|
| AgentId | `1000002`（数字） | 应用管理 → 自建应用详情 |
| Bot ID | `a1b2c3d4-...`（字符串） | 应用管理 → AI Bot（机器人）设置 |

#### ⚠️ 关键误区：字段名必须是 `secret`，不是 `bot_secret`

代码读取 `extra.get("secret")`（见 `wecom.py` 第 156 行）。如果你写了 `bot_secret: xxx`，代码会跳过它（`extra.get("secret")` 返回 None），然后回退到环境变量。

```yaml
# ❌ 错误 — bot_secret 不会被读取
extra:
  bot_id: "xxx"
  bot_secret: "xxx"

# ✅ 正确 — 字段名必须是 secret
extra:
  bot_id: "xxx"
  secret: "xxx"
```

#### 用户操作步骤

1. 打开 [企微管理后台](https://work.weixin.qq.com/wework_admin) → **应用管理** → 选择应用（如"超级大脑"）
2. 在应用详情页找 **「AI Bot 配置」**（也叫智能助手/机器人设置），如果找不到直接在搜索框搜「AI Bot」
3. 开启 AI Bot 后获得：
   - **Bot ID**（bot_id）
   - **Bot Secret**（bot_secret）
4. 将 Bot ID 和 Bot Secret 发给 Hermes 配置

### Hermes 配置

在 `~/.hermes/config.yaml` 中添加：

```yaml
platforms:
  wecom:
    enabled: true
    extra:
      bot_id: "your-bot-id"
      secret: "your-bot-secret"
      # websocket_url: "wss://openws.work.weixin.qq.com"  # 默认值，无需填写
      dm_policy: "open"
      group_policy: "open"
```

环境变量替代：
| 变量 | 对应字段 |
|------|---------|
| `WECOM_BOT_ID` | `bot_id` |
| `WECOM_BOT_SECRET` | `secret` |

配置后重启网关：`pm2 restart hermes-gateway`（或 `hermes gateway restart`）

### 权限控制

用户被 Hermes 接收后，权限由 `access.yaml` 控制：
- 不在 `access.yaml` 中的用户 → `restricted` 角色（仅可对话，不能调用工具）
- 管理员可在 `access.yaml` 中设置 `trusted` 或 `admin` 角色

注意：企微接收和发送使用**不同的通道**。发送走 Corp API（`qyapi.weixin.qq.com`），接收走 AI Bot WebSocket（`openws.work.weixin.qq.com`），两个通道需要独立的配置。

### 方式二：HTTP 回调（wecom_callback）

适用于自建应用的**标准回调方式**。企微 POST 加密的 XML 到 HTTP 端点，适配器解密后处理消息，用 `message/send` API 回复。这也是旧版 OpenClaw 用的方式。

#### 配置示例

```yaml
platforms:
  wecom_callback:
    enabled: true
    extra:
      corp_id: "wwxxxxxxxxxxxxx"      # 企业 ID
      corp_secret: "xxxxxxxxxxxx"      # 应用 Secret（同发送用）
      agent_id: 1000002               # 应用 AgentId
      token: "xxxxxxxxxxxxxxxx"       # 回调 URL 验证 Token
      encoding_aes_key: "xxxxxxxxxxxx"  # 消息加解密密钥
      host: "0.0.0.0"                # 监听地址
      port: 8645                     # 监听端口（默认 8645）
      path: "/wecom/callback"        # 回调路径
```

#### 前置条件

1. 在企微后台 → 应用管理 → 自建应用 → 设置 **「接收消息」**，配置回调 URL
2. 回调 URL 必须是公网可达的（通过域名+隧道暴露端口）
3. 配置时企微会发送 GET 验证请求，`wecom_callback` 适配器会自动处理验证

#### 与 AI Bot WebSocket 的区别

| 维度 | WebSocket (wecom) | HTTP 回调 (wecom_callback) |
|------|-------------------|---------------------------|
| 连接方式 | 主动 WebSocket 长连 | 被动 HTTP 服务器 |
| 认证凭据 | bot_id + bot_secret | corp_id + agentId + secret + token + encodingAESKey |
| 消息格式 | JSON（明文） | XML（AES 加密） |
| 媒体消息（图片/文件） | ✅ 支持（_extract_media 自动下载） | ❌ 仅文本（WeCom 回调会发送图片通知，但适配器丢弃非 text/event 类型） |
| 公网需求 | 不需要 | 需要 |
| 腾讯端配置 | 开启 AI Bot 即可 | 需配置「接收消息」回调 URL |

#### 快速启用

1. 停止 AI Bot 模式（从 config.yaml 中移除或禁用 `platforms.wecom`）
2. 添加 `platforms.wecom_callback` 配置（见上方示例）
3. Cloudflare Tunnel 添加域名指向回调端口，或使用已有域名路径转发
4. 重启网关：`pm2 restart hermes-gateway`
5. 在企微后台配置回调 URL，使用 Token + EncodingAESKey 验证

#### 已知配置（本服务器）

从 OpenClaw 迁移过来的企微回调配置：
- corpId: `ww815119bb08398d37`
- agentId: 1000002
- token 和 encodingAESKey 存于旧版 `~/.openclaw/openclaw.json`
- 原 OpenClaw 监听端口：18800

## 注意事项

### 文件发送：必须用企微官方 API，不用 send_message

Hermes 内置 `send_message(media=...)` **发不了文件**：
- **微信（weixin）**：平台不支持文件附件，返回 `success: true` 但用户收不到
- **`wecom_callback`**：chat_id 路由有 bug（总是解析到 `sisu.` 而非 `KuHai`），用户收不到

**唯一可靠方式：** 直接调企微 Corp API 三步走（获取 token → 上传文件 → 发送消息），见上方「发送文件」章节。

### API Key  관리

**关键风险：`write_file` 工具会损坏 API key！**

Hermes 内置的 `write_file` 在写入后会调用 `redact_sensitive_text()`（`file_tools.py` 第823行），用正则 `r"sk-[A-Za-z0-9_-]{10,}"`（`agent/redact.py` 第71行）匹配所有以 `sk-` 开头的字符串并替换成 `***`。这会导致 `.env` 和 `openclaw.json` 中的 API key 全部变成 `***`，且不可恢复。

**防范措施：**
1. **永远不要用 `write_file` 写入 API key**——使用专门的 `set_env_key.py` 脚本，或用终端 `sed` 命令
2. **不要用 Hermes 的 `write_file` 修改 `.env`、`config.yaml`、`openclaw.json`** 等含 key 的文件
3. 如果发现 key 被损坏，需用户从原始来源重新提供，或从备份恢复

**哪里存着有效 key（未损坏时）：**
| 位置 | 用途 |
|------|------|
| `~/.hermes/.env` | Hermes 的 API Key 配置（易被 write_file 损坏） |
| `~/.openclaw/openclaw.json` | OpenClaw 的 API Key + 企微配置（也可能被损坏） |

### 其他注意事项

- **access_token 有 7200 秒有效期** — 必须缓存避免频繁调用
- **频率限制** — 每应用每分钟 1500 次，足够日常推送
- **agentId 是整数** — 不是字符串，别引号包错
- **touser 支持多用户** — 用 `|` 分隔：`'KuHai|FengZaiQiShi'`（send_wecom.py 不支持此格式，需循环）
- **IP 白名单** — 企微 API 要求源 IP 加入企业微信后台（应用管理 → 超级大脑 → 企业可信IP），否则返回 `errcode: 60020`
- **消息长度** — 企微文本消息约 4096 字节限制，过长需截断或分段
- 旧版 OpenClaw 的企微配置在 `~/.openclaw/openclaw.json`，迁移时可复用
- 企微和微信是两个不同的平台，企微消息不能发到个人微信
- **`wecom_callback` 的 `send_message` chat_id 路由可能有 bug** — 调用 `send_message(target='wecom_callback:KuHai')` 时，返回的 `note` 中 `chat_id` 总是 `sisu.`（圆圆）而不是 `KuHai`。消息实际也没到用户手里。这是 Hermes 内置 `send_message` 工具的路由问题，不是配置问题。**解决方案**：用封装脚本 `/root/stock_analyzer/send_wecom.py` 直接调企微 API，绕过 `send_message` 工具。
- **OpenClaw WeCom 插件**：`@wecom/wecom-openclaw-plugin@2026.5.7`，安装后需重启 OpenClaw 网关。OpenClaw 之前能正常发送文件到企微。
- 相关技能：`hermes-cron-automation` — Hermes cron 定时任务 + no_agent 脚本模式

## 用户文件图书馆式管理

与不同企微用户交互时收到的文件，必须按用户分开存储，不能混入 Lulu 的系统目录。

**文件目录结构：**

```
/root/users-data/
├── Lulu_LuHaiTian/          ← Lulu + 陆海天 共享空间
├── 师父_FengZaiQiShi/       ← 师父专属
└── 老爹_LuWeiFeng/          ← 老爹专属
```

**规则：**
- 企微上其他用户发来的文件、聊天记录、媒体文件，存入对应目录
- Lulu + 陆海天的文件放在 `Lulu_LuHaiTian/`
- 师父的文件放 `师父_FengZaiQiShi/`
- 老爹的文件放 `老爹_LuWeiFeng/`
- 任何时候不把别人的文件存进 Lulu 的私人目录
