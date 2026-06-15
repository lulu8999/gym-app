# LiteLLM Proxy Setup — Claude Code ↔ DeepSeek

## System Overview

Claude Code connects via LiteLLM proxy to DeepSeek API:

```
Claude Code → LiteLLM (localhost:41111) → DeepSeek API
```

`settings.json` has `env.ANTHROPIC_BASE_URL: http://localhost:41111` so all Anthropic-format requests go through the proxy, which translates to OpenAI format for DeepSeek.

## File Locations (current)

| File | Purpose |
|------|---------|
| `/root/.claude-code-litellm/config.yaml` | LiteLLM config (PM2-managed) |
| `/root/.claude-code-litellm/.env` | API Key (`DEEPSEEK_API_KEY=sk-...`) |
| `/root/.claude-code-litellm/start.sh` | PM2 startup script (sources env var) |
| `/root/.claude-code-litellm/ecosystem.config.js` | PM2 ecosystem config |
| `/root/.claude/settings.json` | Claude Code config (apiKey, baseUrl, models, env.ANTHROPIC_BASE_URL) |
| `/usr/local/bin/claude-code-ds` | Shortcut: `claude --bare --model "deepseek-v4-flash" "$@"` |

## Model Mappings

settings.json modelMapping:
- `sonnet` → `deepseek-v4-flash` (日常编码)
- `opus` → `deepseek-v4-pro` (复杂推理)
- `haiku` → `deepseek-chat` (轻量)

LiteLLM config (`/root/.claude-code-litellm/config.yaml`):
```yaml
model_list:
  - model_name: claude-sonnet-4-20250514
    litellm_params:
      model: openai/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY
      api_base: https://api.deepseek.com/v1
```

> LiteLLM 会自动路由未在 model_list 中的模型名（如 `deepseek-v4-flash`）到 DeepSeek，前提是 `DEEPSEEK_API_KEY` 环境变量已设。

## 🔑 DeepSeek API Key 轮换 (ROTATION)

**关键：必须同时更新 2 个文件，然后用 `--update-env` 重启 PM2。**

### 步骤

```bash
# 1. 更新 LiteLLM 代理的 Key
echo 'DEEPSEEK_API_KEY=sk-新Key' > /root/.claude-code-litellm/.env

# 2. 更新 Claude Code 的 Key（settings.json 中的 apiKey）
python3 -c "
import json
c = json.load(open('/root/.claude/settings.json'))
c['apiKey'] = 'sk-新Key'
json.dump(c, open('/root/.claude/settings.json','w'), indent=4)
"

# 3. 重启 LiteLLM（⚠️ 必须带 --update-env）
pm2 restart litellm-proxy --update-env

# 4. 验证
sleep 3 && curl -s http://localhost:41111/health
```

### ⚠️ 常见陷阱

| 陷阱 | 后果 | 原因 |
|:---|:---|:---|
| 只更新一个文件 | 401 Authentication Fails | `.env` + `settings.json` 两个 Key 都要一致 |
| 用 `sed` 通过 terminal 工具改 | 文件被写入字面 `***` | Hermes tool output masking 会截断 Key |
| `pm2 restart` 不带 `--update-env` | 新 Key 不生效 | PM2 默认复用旧环境变量 |
| `start.sh` 读环境变量而非 .env | Key 丢了 | `start.sh` 做 `export DEEPSEEK_API_KEY="${DEEP...Y:-}"`，需 PM2 传 env |

### 验证 Key 是否生效

```bash
# 健康检查（看 healthy_count > 0）
curl -s http://localhost:41111/health | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'healthy={d[\"healthy_count\"]}')"

# Claude Code 实际调用测试
cd /root/.hermes && claude-code-ds --print "say hello in Chinese" 2>&1 | head -5
```

## PM2 Management

```bash
pm2 list | grep litellm                      # 查看进程状态
pm2 restart litellm-proxy --update-env       # 重启代理（必须带 --update-env）
pm2 logs litellm-proxy --lines 10 --nostream  # 看最近日志
```

## Model Verification

```bash
# 查看代理暴露的模型
curl -s http://localhost:41111/v1/models

# 验证 API Key 连通性
source /root/.hermes/.env && curl -s "https://api.deepseek.com/v1/models" -H "Authorization: Bearer $DEEPSEEK_API_KEY"

# 验证 Anthropic Messages 格式代理
curl -s -w "\nHTTP %{http_code}" http://localhost:41111/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk-test" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-sonnet-4-8","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
```

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Claude Provider 缺少 base_url 配置" | settings.json 中 env.ANTHROPIC_BASE_URL 指向死地址（如 15721） | 更新为 localhost:41111 或删除 env.ANTHROPIC_BASE_URL |
| "403 Request not allowed" | DeepSeek API 收到 Anthropic 格式消息（直接连接时不在代理中） | 设置 env.ANTHROPIC_BASE_URL 走 LiteLLM 代理 |
| "Invalid model name" | 代理配置中无对应模型映射 | 在 litellm-config.yaml 添加映射后重启 |
| 401 authentication | API Key 无效 | 用 .hermes/.env 中的有效 Key 替换 |
| Connection refused | LiteLLM 代理未运行 | pm2 start start-litellm.sh |
