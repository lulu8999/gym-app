# LiteLLM 代理配置参考

## 作用
将 Claude Code（Anthropic Messages API 格式）的请求翻译成 DeepSeek API（OpenAI 格式）

## 架构
```
Claude Code  ── Anthropic Messages ──→  LiteLLM (localhost:41111)  ── OpenAI ──→  DeepSeek API
```

## 配置

**配置文件：** `/root/litellm-config.yaml`
**PM2 进程名：** `litellm-proxy`
**启动脚本：** `/root/start-litellm.sh`

### 模型映射表

| Claude 模型名 | 映射到 DeepSeek | 用途 |
|---|---|---|
| `claude-sonnet-4-20250514` | `deepseek-v4-flash` | 日常快速 |
| `claude-sonnet-4-8` | `deepseek-v4-flash` | 日常快速 |
| `claude-opus-4-8` | `deepseek-v4-pro` | 复杂任务/写代码 |
| `claude-haiku-4-8` | `deepseek-chat` | 简单对话 |
| `deepseek-v4-flash` | `deepseek-v4-flash` | 直连（不经过翻译） |
| `deepseek/deepseek-v4-flash` | `deepseek-v4-flash` | 直连（不经过翻译） |

### Claude Code settings.json

**路径：** `/root/.claude/settings.json`

关键字段：
- `apiKey` — DeepSeek API Key（与 Hermes 共用 `/root/.hermes/.env` 中的 key）
- `baseUrl` — `https://api.deepseek.com`（直连 DeepSeek 用的）
- `env.ANTHROPIC_BASE_URL` — `http://localhost:41111`（走代理时的地址）
- `models` — 可用模型列表
- `modelMapping` — 别名映射（sonnet→flash, opus→pro, haiku→chat）

## 启动/重启

```bash
# 查看状态
pm2 list | grep litellm

# 重启
pm2 restart litellm-proxy

# 验证
curl -s http://localhost:41111/v1/models | python3 -c "import json,sys; d=json.load(sys.stdin); [print(m['id']) for m in d.get('data',[])]"
```

## 故障排查

| 症状 | 原因 | 修复 |
|---|---|---|
| "Claude Provider 缺少 base_url 配置" | settings.json 中 env.ANTHROPIC_BASE_URL 指向失效地址 | 更新为 `http://localhost:41111` 或删除 |
| "Invalid model name" | Claude Code 发送的模型名没有配置映射 | 在 litellm-config.yaml 中补 mapping |
| 403 Request not allowed | Claude Code 直接发给 DeepSeek（不兼容格式） | 确保通过代理转发 |
| Connection refused | 代理未运行 | `pm2 start /root/start-litellm.sh --interpreter bash --name litellm-proxy` |
