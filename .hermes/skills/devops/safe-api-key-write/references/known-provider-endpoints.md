# Known OpenAI-Compatible Provider Endpoints

Reference for configuring providers in Hermes `config.yaml`. All use `provider: openai`.

## Confirmed Working

| Provider | base_url | Auth Format | Notes |
|----------|----------|-------------|-------|
| Xiaomi MiMo | `https://api.xiaomimimo.com/v1` | Bearer `sk-xxx` | Models: mimo-v2-flash, mimo-v2-pro, mimo-v2.5, mimo-v2.5-pro |
| 百度千帆 (标准) | `https://qianfan.baidubce.com/v2` | Bearer token | OpenAI-compatible chat completions |
| 百度千帆 (Coding Plan) | `https://qianfan.baidubce.com/v2/coding` | Bearer `bce-v3/...` | Coding Plan 专用端点，仅支持 Coding Plan 内的模型 |
| 百度千帆 (老版) | `https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop` | Bearer token | 文心一言原生接口 |

## 百度千帆 Coding Plan 特殊要求

- API Key 格式：`bce-v3/ALTAKSP-...`（以 `bce-v3/` 开头）
- base_url **必须**加 `/coding` 后缀，否则报 `coding_plan_api_key_not_allowed`
- 模型名由千帆控制台决定，标准模型（ernie-4.5-turbo 等）不支持 Coding Plan
- 如果报 `coding_plan_model_not_supported`，需去千帆控制台查看支持的模型列表

## How to Test a New Provider

Before adding to Hermes config, verify the endpoint works:

```bash
# Read key from .env (avoid write_file corruption)
KEY=$(grep 'MY_API_KEY=' ~/.hermes/.env | cut -d= -f2-)

curl -s -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"model-name","messages":[{"role":"user","content":"hi"}],"max_tokens":5}' \
     https://api.example.com/v1/chat/completions
```

If HTTP 200 → provider endpoint is correct → add to config.yaml with `provider: openai`.
If HTTP 401 → key issue (check .env corruption, not provider type).
If connection refused → wrong base_url or network issue.

## Hermes Provider Config Template

```yaml
providers:
  friendly-name:
    provider: openai           # ← ALWAYS 'openai' for compatible APIs
    api_key_env: MY_API_KEY    # ← env var name in .env
    base_url: https://...      # ← from provider docs
    models: '["model-a","model-b"]'
```

Then set as default:
```bash
hermes config set model.default friendly-name
hermes config set model.provider friendly-name
```
