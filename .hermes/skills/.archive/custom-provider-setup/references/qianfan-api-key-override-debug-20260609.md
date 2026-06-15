# Qianfan Coding Plan: API Key Override Debug (2026-06-09)

## Symptom

Gateway returns `HTTP 401: invalid_iam_token` for `qianfan-code-latest` even though:
- `QIANFAN_API_KEY` env var is correct (77 chars, `bce-v3/...`)
- `.hermes/.env` has the key
- Curl to the same endpoint with Bearer auth works (200 OK)

## Root Cause

`model.api_key: ''` (empty string) in `config.yaml` overrides `providers.qianfan.api_key_env: QIANFAN_API_KEY`.

Gateway request dump confirmation:
```
URL: https://qianfan.baidubce.com/v2/coding/chat/completions
Auth: Bearer no-key-required     ← empty string!
Model: qianfan-code-latest
```

## Diagnostic Commands Used

### 1. Compare keys across locations
```bash
# System env
echo "System: len=${#QIANFAN_API_KEY} prefix=${QIANFAN_API_KEY:0:10}"

# .hermes/.env key
ENV_KEY=$(grep "^QIANFAN_API_KEY=*** ~/.hermes/.env | cut -d'=' -f2)
echo "  .env: len=${#ENV_KEY} prefix=${ENV_KEY:0:10}"
```

### 2. Inspect request dump (most recent)
```bash
python3 -c "
import json, glob
dumps = sorted(glob.glob('/root/.hermes/sessions/request_dump_*.json'))
with open(dumps[-1]) as f:
    d = json.load(f)
auth = d['request']['headers'].get('Authorization', 'MISSING')
print('URL:', d['request']['url'])
print('Auth:', auth[:60])
print('Model:', d['request']['body'].get('model', 'N/A'))
"
```

### 3. Curl test to compare
```bash
curl -s https://qianfan.baidubce.com/v2/coding/chat/completions \
  -H "Authorization: Bearer $QIANFAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qianfan-code-latest","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
```

## Config State at Time of Error

```yaml
model:
  api_key: ''              # ← empty string: root cause
  provider: qianfan
  default: qianfan-code-latest

providers:
  qianfan:
    api_key_env: QIANFAN_API_KEY
    base_url: https://qianfan.baidubce.com/v2/coding
    default_model: qianfan-code-latest
    models: '["qianfan-code-latest"]'
    provider: custom        # ← generates warning: "unknown config keys ignored: provider"
```

## Fix

Write key directly to `model.api_key`:
```bash
hermes config set model.api_key "$QIANFAN_API_KEY"
```

Then verify with hermes chat or check a new request dump.
