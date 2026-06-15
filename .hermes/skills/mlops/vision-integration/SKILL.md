---
name: vision-integration
description: 设置并使用视觉/图片识别能力（MiMo + Kimi），包括Hermes配置和OpenAI兼容API直接调用模式
---

# 视觉识别集成指南

## 支持视觉的模型一览

| 模型 | Provider | 视觉支持 | 备注 |
|------|----------|----------|------|
| mimo-v2.5 | xiaomi-mimo | ✅ | 主要视觉模型 |
| mimo-v2-omni | xiaomi-mimo | ✅ | 多模态 |
| moonshot-v1-8k-vision-preview | kimi | ✅ | 备选视觉模型 |
| glm-4v / glm-5.1 | qianfan | ✅ | 千帆多模态模型，支持图片输入 |

**⚠️ 重要：** 微信/Weixin 通道**能接收图片**（日志中 `media=1` 表示收到），图片会被下载到本地缓存传给网关。用户发图看不到通常是因为下游 `auxiliary.vision` 配置不完整（base_url/api_key 空导致超时），**不是通道级别限制**。详见陷阱 #15/#18/#19 的诊断路线图。

## 策略优先级

1. **主要**: `xiaomi-mimo/mimo-v2.5` — 通过 Hermes `auxiliary.vision` 配置自动接入
2. **备选**: `kimi` (moonshot-v1-8k-vision-preview) — fallback 方案

## Lulu 模型分层策略

日常对话 + 识图走 MiMo v2.5（便宜够用），视觉备选 Kimi。复杂推理/编程/数学走 DeepSeek（通过 `delegate_task` 的 `delegation.model=deepseek-v4-pro`）。

**切换型号令**: 用户说"切模型"/"切到xxx"时，自动完成两步：① `hermes config set model.default/provider` 切换模型配置 ② 开启新会话。不要问直接做。

## 方式一：Hermes 配置（推荐）

在 `config.yaml` 中设置 auxiliary vision:

```yaml
auxiliary:
  vision:
    provider: xiaomi-mimo      # 或 kimi
    model: mimo-v2.5            # 或 moonshot-v1-8k-vision-preview
```

命令行配置：
```bash
hermes config set auxiliary.vision.provider xiaomi-mimo
hermes config set auxiliary.vision.model mimo-v2.5
```

Hermes 自动处理图片加载和发送，无需手动 base64 编码。

## 方式二：直接 API 调用（测试/验证用）

### MiMo 验证
```bash
source ~/.hermes/.env
curl -s https://api.xiaomimimo.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer *** \
  -d '{"model":"mimo-v2.5","messages":[{"role":"user","content":"你好"}],"max_tokens":50}'
```

### Kimi 验证
```bash
source ~/.hermes/.env
curl -s https://api.moonshot.cn/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer *** \
  -d '{"model":"moonshot-v1-8k-vision-preview","messages":[{"role":"user","content":"你好"}],"max_tokens":50}'
```

### 图片识别（Kimi 直接 API）
图片需要 base64 编码后放在 `data:image/jpeg;base64,{b64}` 格式中传递：

```python
import base64, json, urllib.request

with open(img_path, "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

payload = {
    "model": "moonshot-v1-8k-vision-preview",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "图中是什么？详细描述一下，用中文回答"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
        ]
    }],
    "max_tokens": 500
}
```

**相关技能**: `safe-api-key-write`（Key 安全写入）、`model-watchdog`（模型可用性监控）

## 实战工作流

- `references/social-media-image-extraction.md` — 从抖音/小红书等图片轮播帖中提取文字内容的完整流程（浏览器 + JS提取图片URL + vision_analyze逐张识别）

## 添加新 Provider 的标准流程

当用户提供一个新的 API Key + base_url 时：

1. 将 Key 写入 `~/.hermes/.env`（用 echo/append 方式，**不用 write_file** 避免自动脱敏）
2. 在 `config.yaml` 的 `providers` 下添加 provider 定义：
   ⚠️ **关键**：内层 `provider` 字段是**协议类型**，不是自定义名称。OpenAI 兼容 API 用 `openai`，DeepSeek 用 `deepseek`，Kimi 用 `kimi-coding`。

   ```yaml
   providers:
     自定义provider名:            # ← 这里是自定义别名
       provider: openai            # ← 这里是协议类型！MiMo 兼容 OpenAI 所以用 openai
       api_key_env: 对应_ENV_KEY
       base_url: https://api.xxx.com/v1
       models: '["model1","model2"]'
   ```

   **常见错误**：把内层 `provider` 写成自定义名称（如 `provider: xiaomi-mimo`）。Hermes 不认识这个协议，会报错或回退到默认行为。协议类型必须是 Hermes 内置的：`openai`、`deepseek`、`anthropic`、`google`、`kimi-coding`、`groq` 等。
3. **清除残留 base_url**：旧 provider 可能在 `model.base_url` 留有过期地址，会覆盖新 provider 的 base_url。
   ```bash
   # 先检查是否有残留
   grep '^\s*base_url:' ~/.hermes/config.yaml | head -3
   # 如果有旧地址，清空它（让 provider 配置继承正确地址）
   hermes config set model.base_url ""
   ```
4. 设为主模型：`hermes config set model.default <模型名>` + `hermes config set model.provider <provider名>`
5. （如需）修改 `auxiliary.vision.provider/model`
6. 用 curl 直接测 API 确认可用：
   ```bash
   source ~/.hermes/.env
   curl -s --connect-timeout 10 --max-time 20 {base_url}/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer ${对应_KEY}" \
     -d '{"model":"<模型名>","messages":[{"role":"user","content":"你好"}],"max_tokens":50}'
   ```
7. **重启网关**使新配置生效：`hermes gateway restart`
8. 更新 memory 中的模型策略和可用模型列表
9. 关键：**含 API Key 的文件不要用 write_file**，用 `sed` / `grep` / echo 拼接字符串避免自动脱敏

## 切换模型（换 provider/模型名）

用户说"切模型"/"切到xxx"时，自动完成：
1. 修改配置：`hermes config set model.default <模型名>` + `hermes config set model.provider <provider名>` + 清除残留 `model.base_url`
2. `hermes gateway restart` 使配置生效
3. 开启新会话

不要问直接做。

## 已知陷阱

### 1. Kimi 没有余额查询接口
`/v1/user/balance` 返回 404。无法通过 API 查询余额。
估值：`moonshot-v1-8k-vision-preview` 约 0.012 元/千 token，一次识别约 0.01 元。

### 2. WeCom 回调通道不收图片
`wecom_callback.py` 第 348 行只处理 `text` 和 `event` 类型消息：
```python
if msg_type not in {"text", "event"}:
    return None
```
图片消息（`MsgType=image`）被静默丢弃。如需支持图片需要修改此代码。

### 3. Weixin 通道收图但下游配置不全会导致超时
Weixin/微信通道确实能接收图片（日志中 `media=1` 表示收到图片），下载到本地缓存后通过 `media_urls` 传给网关。**问题通常在后端**：

- 如果 `auxiliary.vision` 的 `base_url` 或 `api_key` 为空，`vision_analyze` 会因连不上后端而**超时**
- 日志特征：`[Weixin] inbound from=xxx type=dm media=1` → `Image routing: text (mode=text). Pre-analyzing 1 image(s) via vision_analyze.` → 然后无后续结果
- 用户端表现：发图后 agent 沉默或超时，回复说看不到图

**排查路线：** 微信收图（media=1）→ 路由判定（text/native）→ vision_analyze 调用 → 超时 → 问题定位到 auxiliary.vision 配置。

不要一上来就说"微信不收图"——先看日志里 `media=` 的值是 0 还是 1。

### 4. 回复时不回传图片
用户发图片给你识别时，**不要**在回复中包含 `MEDIA:/path/to/image` 标记，否则图片会被重新发送给用户。只描述内容即可。

### 5. Key 显示遮盖 ≠ 文件损坏（2026-06-06 修正）
`write_file` **不会**损坏磁盘文件。所有输出渠道（`read_file` 回读、`terminal` 的 `cat`/`grep`、`execute_code` 的 `print`）都会经过 `redact_sensitive_text()` 将 `sk-xxx` 显示为 `***`，但磁盘上的文件是正确的。

**验证方法（唯一可靠）：** 用 hex 查看绕过遮盖：
```bash
xxd /root/.hermes/.env | grep XIAOMI
# 输出 73 6b 2d = sk- 说明文件正确
```

**推荐写入方式：** `set_env_key.py` 脚本避免输出混淆：
```bash
python3 /root/scripts/set_env_key.py XIAOMI_API_KEY sk-xxx
```

详见 `safe-api-key-write` 技能的完整调查记录。

### 6. model.base_url 残留导致 401 误报
切换 provider 后，`model.base_url` 可能残留上一家 provider 的地址（如 `https://api.deepseek.com/v1`）。
新 provider 的 API key 会被发到错误的地址，返回 **401 Invalid API Key**——症状像 key 无效，
实际上是请求地址错了。调试步骤：
```bash
# 1. 检查 model.base_url 是否有残留
hermes config show | grep "base_url" | head -1
# 2. 如果有旧地址，清空之
hermes config set model.base_url ""
# 3. 清空后 model.base_url 从 provider 配置继承正确地址
# 4. 重启网关
hermes gateway restart
```
直接 curl 调 API 能通但 Hermes 报 401 → 基本就是 base_url 残留。不一上来就怀疑 key 坏了。

### 7. MiMo API 特性

- **config.yaml 中 `provider` 字段会产生警告**：`providers.xiaomi-mimo: unknown config keys ignored: provider`。这是 Hermes 解析 config 时的 warning，不影响功能，可以忽略。
- **无 billing/usage 查询端点**：`/v1/dashboard/billing/usage` 返回 404，无法通过 API 查账户消费。只能去小米 MiMo 开放平台后台看。
- **chat completions 返回 usage 数据**：response 中有 `usage.prompt_tokens` / `usage.completion_tokens` / `usage.total_tokens`，但 **Hermes 本地不存储**（messages 表 token_count 始终为 NULL）。想追踪用量需要自己在 watchdog 或其他脚本里记录。
- **可用模型列表**：mimo-v2-flash、mimo-v2-pro、mimo-v2.5、mimo-v2.5-pro、mimo-v2-omni、mimo-v2.5-asr、mimo-v2.5-tts、mimo-v2.5-tts-voiceclone、mimo-v2.5-tts-voicedesign（2025-06 实测）。

### 8. 切换模型必须重启网关
`hermes config set` 只改配置文件，新模型在网关重启后才生效。
用户说"切模型"时流程：修改配置 → `hermes gateway restart` → 新会话走新模型。

### 9. 输出遮盖陷阱：`***` 不一定是 key 损坏

当用户反馈 "MiMo key 用一会就过期 / 网站显示正常但 API 报 401" 时，**最可能的原因是 `.env` 里的 key 被替换成了 `***`**。但关键区分：

**两种"被替换"的含义完全不同：**

| 类型 | 症状 | 原因 |
|------|------|------|
| 🟡 输出遮盖（无害） | `cat .env` 显示 `***`，但 `xxd` 看到真实 key | redact.py 对所有输出渠道的显示遮盖 |
| 🔴 文件损坏（有害） | `xxd .env` 也显示 `***` | 文件被错误地写了 `***` 到磁盘 |

**诊断步骤：**

```bash
# 1. 用 hex 验证文件是否真的损坏（终极方法）
xxd ~/.hermes/.env | grep -A1 XIAOMI
# 如果看到 73 6b 2d (= sk-) + 真实key → 文件完好，只是显示被遮盖
# 如果看到 * * * (= 3 asterisks) → 文件真的损坏了

# 2. 或用字节数判断
grep '^XIAOMI_API_KEY=' ~/.hermes/.env | wc -c
# 22 bytes = "XIAOMI_API_KEY=***\\n" → 损坏
# 47+ bytes = 含真实 key → 完好

# 3. 修复（仅需在文件损坏时执行）
python3 /root/scripts/set_env_key.py XIAOMI_API_KEY sk-真实key
pm2 restart hermes-gateway
```

**重要纪律：** 当用户报告 key 问题时（"切到 mimo 报错过期"），优先解决这个问题，不要先去做其他事（重跑 cron、查余额等）。先问 key → 写 key → 重启 → 让用户验证。用户问题解决后，再问"还有别的事需要处理吗？"。

### 10. 非视觉模型下收到图片：主动切换或说明

当前模型为 deepseek-v4-flash（纯文本模型）时，**无法处理任何图片消息**。如果此时通过企业微信/微信收到用户发来的图片（如圆圆回图），系统不会报错但也不会回复——用户会觉得被忽视了。

**正确做法：**
- 如果只是需要看图回复，切换到支持视觉的模型（mimo-v2.5 或 kimi）
- 或者在回复中说明"我现在用的是纯文本模型看不了图，切到视觉模型就能看了"
- **不要沉默** —— 用户发了图没回应会困惑

切换命令：
```bash
# 切到 mimo（支持视觉）
hermes config set model.default mimo-v2.5 && hermes config set model.provider xiaomi-mimo && systemctl --user restart hermes-gateway
```

### 11. MiMo 视觉 API 调用注意事项

#### 11a. 只有 mimo-v2.5 支持 vision，mimo-v2-flash 和 mimo-v2.5-pro 都不支持

**mimo-v2-flash 和 mimo-v2.5-pro 都不支持图片输入（vision）。** 调用时报错：
```
# mimo-v2.5-pro
No endpoints found that support image input

# mimo-v2-flash
No endpoints found that support image input
```

**正确做法：** 视觉任务必须用 `mimo-v2.5`（或 `mimo-v2-omni`），不要用 `mimo-v2.5-pro` 或 `mimo-v2-flash`。

```python
# ✅ 正确
model = "mimo-v2.5"

# ❌ 错误 — mimo-v2-flash 不支持图片
model = "mimo-v2-flash"
```

#### 11b. `thinking` 参数必须在请求顶层，不能在 `extra_body` 内

MiMo API 要求 `thinking` 参数直接放在 JSON 请求的顶层，而不是像 OpenAI 那样放在 `extra_body` 内部：

```python
# ✅ 正确：thinking 在顶层
requests.post(api_url, json={
    "model": "mimo-v2.5",
    "messages": [...],
    "max_tokens": 500,
    "thinking": {"type": "disabled"}   # ← 顶层 key
})

# ❌ 错误：thinking 在 extra_body 内
requests.post(api_url, json={
    "model": "mimo-v2.5",
    "messages": [...],
    "extra_body": {"thinking": {"type": "disabled"}}  # ← MiMo 不识别 extra_body
})
```

**`extra_body` 是 OpenAI SDK 客户端传参的约定，不是 API 协议标准。** 直接用 `requests` 发 RAW JSON 时，`thinking` 必须在 JSON 根层级。

**验证方法：** 如果请求返回了 `reasoning_content`（思考过程 tokens），说明 `thinking: {"type": "disabled"}` 没有生效，需要检查参数位置。

#### 11c. MiMo 视觉 API 返回的 JSON 内容可能包裹在 ```json 标记中

MiMo 视觉 API 返回的内容有时不是纯 JSON，而是 Markdown 代码块格式包裹的 JSON：

```
```json
{
  "ocr_text": "...",
  "emotion": {...},
  ...
}
```
```

**解析时需要先剥离 Markdown 标记：**
```python
import re, json

content = data["choices"][0]["message"]["content"]
# 去掉 ```json ... ``` 包裹
cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', content, flags=re.MULTILINE)
result = json.loads(cleaned)
```

**不处理的后果：** `json.loads()` 直接报错 `Expecting value: line 1 column 1 (char 0)`，因为第一个字符是反引号，不是 JSON 合法起始字符。

### 12. MiMo 429 Too Many Requests — 并发过多触发限流

MiMo API 对短时间内的并发请求有限流策略，返回 HTTP 429。常见触发场景：
- 多个 agent 同时调用 MiMo（如 Hermes + OpenClaw 各跑一个会话）
- 看门狗/cron 脚本与活跃会话同时请求

**策略：** 遇到 429 时等待 1-2 秒重试，或错开不同服务的请求时间。这不是 key 失效，是 API 侧的速率控制。

### 13. vision_analyze 双重失败：模型不支持 + fallback key 损坏

当当前模型是纯文本模型（如 deepseek-v4-flash）时，`vision_analyze` 会尝试 fallback 到辅助视觉模型。但如果**所有视觉 provider 的 API key 都被损坏**（`.env` 中 `***`），fallback 也会失败：

```
Error code: 400 - unknown variant `image_url`, expected `text`
```

这个错误信息很误导人——看起来是格式问题，实际上是**视觉模型根本没被调用到**。

**诊断步骤：**
1. 检查当前模型是否支持视觉（deepseek 系列不支持）
2. 检查 `.env` 中的视觉 provider key 是否被损坏（`grep XIAOMI_API_KEY /root/.hermes/.env | wc -c` — 如果只有 22 字节就是损坏了）
3. 用 `safe-api-key-write` 技能修复 key 后重试

**不要**反复试 vision_analyze——每次失败都在浪费 token。先确认 key 完好再试。

### 14. 用户发图不响应：非视觉模型的沉默问题

当前模型为纯文本模型（如 deepseek-v4-flash）时，**无法处理任何图片消息**。如果此时收到用户发来的图片，系统不会报错也不会回复——用户会觉得被忽视了。

**正确做法：**
- 如果只是需要看图回复，切换到支持视觉的模型（mimo-v2.5 或 kimi）
- 在回复中说明\"我的模型现在不支持看图\"，而不是沉默
- 如果需要调用视觉 API 但 key 损坏，告知用户并提供修复步骤

切换命令：
```bash
hermes config set model.default mimo-v2.5 && hermes config set model.provider xiaomi-mimo && systemctl --user restart hermes-gateway
```

### 15. `vision_analyze` fallback 因 auxiliary.vision 配置不全而失败（超时版）

当 `config.yaml` 中的 `auxiliary.vision` 配置不完整——**`base_url` 和 `api_key_env` 为空**——时，`vision_analyze` 会因连不上视觉后端导致**超时**，而不是立刻报 400。

**具体机制：** `auxiliary.vision.provider` 只要非空（如 `openai`），`_explicit_aux_vision_override` 就会返回 True，强制走 "text" 模式。但 `base_url` 和 `api_key_env` 为空时，`vision_analyze` 连不到任何后端，最终超时：

```
INFO gateway.run: Image routing: text (mode=text). Pre-analyzing 1 image(s) via vision_analyze.
...
INFO agent.auxiliary_client: Auxiliary vision (async): transient transport error; retrying once...
Request timed out.
```

**诊断步骤：**
```bash
grep -A 5 "auxiliary" ~/.hermes/config.yaml
# 检查 base_url 和 api_key_env 是否有值
```

**修复（必须设两个字段，缺一不可）：**\n```bash\n# api_key_env 给网关进程用（启动时自动加载 .env）\nhermes config set auxiliary.vision.api_key_env XIAOMI_API_KEY\n# api_key 给 agent 进程用（不依赖 .env）\nhermes config set auxiliary.vision.api_key \"sk-真实key值\"\nsystemctl --user restart hermes-gateway\n```\n\n**关键：** 只设 `api_key_env` 只覆盖了网关通道（用户发图）。agent 主动调用 `vision_analyze`（浏览器截图、URL 图等）会因拿不到 key 而失败。**必须 `api_key` + `api_key_env` 双设**。详见陷阱 #18。

### 16. 不要禁用 MiMo 的 thinking 功能

**用户明确纠正：** 禁用 MiMo (mimo-v2.5) 的 thinking 功能会导致严重的质量下降（用户描述为"降智"）。

- **错误做法：** 通过 `extra_body.thinking={"type":"disabled"}` 或插件控制来关闭思考
- **正确做法：** 保持 MiMo 默认配置，让模型自主使用思考功能
- **性能问题：** 如果 MiMo 响应慢，通常是因为上下文过长（8-9万 tokens），而不是思考功能本身。此时应优化上下文（开新会话、压缩历史）而非禁用思考

**决策原则：** 对于 MiMo v2.5，永远不要主动禁用 thinking。如果用户抱怨慢，诊断上下文长度，而不是关闭思考。

### 17. auxiliary.vision 已配置仍报 401 → key 文件损坏（而非 base_url 问题）

**场景：** 修复了 `auxiliary.vision.base_url` 和 `api_key_env` 后，`vision_analyze` 仍然报错：
```
Error code: 401 - {'error': {'message': 'Invalid API Key', 'param': 'Please provide valid API Key', 'code': '401', 'type': 'invalid_key'}}
```

**与 pitfall #6（base_url 残留导致 401）的区别：**

| pitfall #6 | pitfall #17（新增） |
|------------|-------------------|
| `model.base_url` 有旧地址残留 | `model.base_url` 已清空 |
| API key 本身是好的 | API key 在 `.env` 中被写成了 `***` |
| curl 调 API 能通，只有 Hermes 报 401 | curl + Hermes 都报 401 |

**诊断路径：**
```
auxiliary.vision 已配 → 401 → 不是 base_url 残留 → 检查 key 是否损坏
```

**检查方法：**
```bash
xxd ~/.hermes/.env | grep XIAOMI
# 看到 * * * → key 损坏，需要重新写 key
# 看到 73 6b 2d (=sk-) → key 完好，排查其他原因
```

**修复方法：**
```bash
python3 /root/scripts/set_env_key.py XIAOMI_API_KEY sk-真实key
## 或手动用 echo 写入（不要用 write_file，会触发遮盖）
echo 'XIAOMI_API_KEY=sk-真实key' >> ~/.hermes/.env
systemctl --user restart hermes-gateway
```

**避免顺序错误的排查路线：**
1. ✅ auxiliary.vision 配置完整？（base_url + api_key_env 有值）
2. ✅ model.base_url 已清空？
3. ✅ `.env` 中的 key 不是 `***`？
4. ❌ → 写回正确 key → 重启网关 → 再试

不要在第一步就怀疑 key 损坏，也不要跳过第二步直奔 key。**按顺序排查，避免浪费时间。**

### 18. 进程上下文差异：`api_key` vs `api_key_env` 必须双设

**问题场景：** `auxiliary.vision` 配置了 `api_key_env: XIAOMI_API_KEY` 后，**通过微信发图**（走网关进程）能正常识别，但**在对话中 agent 主动调用 `vision_analyze`** 报 401。

**根因：** Hermes 有两个执行上下文：

| 上下文 | 是否读取 .env | 能否用 `api_key_env` |
|--------|-------------|-------------------|
| 网关进程（gateway） | ✅ 启动时自动加载 .env | ✅ `os.getenv("XIAOMI_API_KEY")` 有值 |
| agent 会话（当前对话） | ❌ 不加载 .env | ❌ `os.getenv("XIAOMI_API_KEY")` 为 None |

**这意味着：** 只设 `api_key_env` 只覆盖了网关通道（用户发图）。agent 主动调用 `vision_analyze`（如浏览器截图分析、URL 图片分析）会因拿不到 key 而失败。

**修复方法（双设）：**
```bash
# api_key_env 给网关进程用
hermes config set auxiliary.vision.api_key_env XIAOMI_API_KEY
# api_key 给 agent 进程用（直接从 config 读取，不依赖 .env）
hermes config set auxiliary.vision.api_key "sk-真实key值"
```

**验证方法：** 同时设完两个字段后，在对话中直接调用 `vision_analyze` 测 agent 路径，再发张图测网关路径。两条链路都通才算修好。

**补充：`_resolve_task_provider_model` 的代码缺陷**

`agent/auxiliary_client.py` 中的 `_resolve_task_provider_model` 只读取任务的 `api_key` 字段，不读取 `api_key_env`：

```python
# 第 4698 行 — 只读 api_key，不读 api_key_env
cfg_api_key = str(task_config.get("api_key", "")).strip() or None
```

修复补丁（已在 Lulu 环境中应用）：
```python
cfg_api_key = str(task_config.get("api_key", "")).strip() or None
if not cfg_api_key:
    cfg_api_key_env = str(task_config.get("api_key_env", "")).strip() or None
    if cfg_api_key_env:
        cfg_api_key = os.getenv(cfg_api_key_env, "").strip() or None
```

这个补丁在更新 Hermes 版本后可能被覆盖，需重新应用。

### 19. 微信收图诊断路线图（完整排查链路）

当用户说"收不到图/识别不了图片"时，按此路线排查：

```
用户发图 → 检查 gateway.log
                │
         media=0？ → 微信通道根本没传图过来，通道级别问题
         media=1？ → 图片已到达 ✅ 继续
                │
         Image routing: text/native？
                │
         text → 走 vision_analyze pre-analyze 路径
         native → 模型原生看图（GLM 等）
                │
         vision_analyze 是否超时/报错？
                │
         超时（6分钟无结果）→ 
           │                   
           检查 auxiliary.vision.base_url 和 api_key_env 是否为空
           空 → 补全配置
           有值 → 跳 key 检查
                │
         401 Invalid API Key →
           检查 key 是否损坏（xxd .env | grep XIAOMI）
           检查 base_url 是否残留（model.base_url）
           检查进程上下文（gateway agent 双设问题）
```

**关键日志标记：**
- `media=1` = 微信收到了图片 ✅
- `Image routing: text` = 走 text 模式（非 native）
- `Pre-analyzing 1 image(s) via vision_analyze` = 正在分析
- `transient transport error...Request timed out` = 后端连不上
- `Invalid API Key` = key 问题
