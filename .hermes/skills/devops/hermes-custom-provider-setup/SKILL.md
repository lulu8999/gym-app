---
name: hermes-custom-provider-setup
description: "Configure custom OpenAI-compatible model providers in Hermes Agent — model section quirks, api_key vs api_key_env, debugging auth errors, and provider-specific endpoint patterns."
version: 1.0.0
author: agent
platforms: [linux, macos]
metadata:
  hermes:
    tags: [hermes, configuration, model, provider, custom, openai-compatible, auth]
    related_skills: [hermes-agent, safe-api-key-write, vision-integration]
---

# Custom Provider Setup

How to configure a custom OpenAI-compatible model provider in Hermes Agent when it's not in the built-in provider list.

## Config Structure

### The `model` Section (config.yaml)

```yaml
model:
  base_url: https://your-provider.com/v1     # OpenAI-compatible base URL
  default: your-model-name                    # Default model name
  provider: custom                             # Always "custom" for non-built-in providers
  api_key: YOUR_API_KEY                       # ⚠️ LITERAL VALUE, NOT env var name
```

### ⚠️ Critical: `api_key` vs `api_key_env`

| Field | Works in `model` section? | Works in `providers.<name>` section? |
|-------|--------------------------|--------------------------------------|
| `api_key` | ✅ Takes **literal string** | ✅ Takes **literal string** |
| `api_key_env` | ❌ **Does NOT work** | ⚠️ Yes, BUT easily overridden by `model.api_key: ''` (empty string takes precedence) |

**Three traps, not one:**

**Trap 1 (env-var-as-literal):** In the `model` section, `api_key: QIANFAN_API_KEY` sends the literal string `"QIANFAN_API_KEY"` — NOT the value of the env var. You must write the actual API key value directly.

**Trap 2 (Gateway 不加载 .env):** `providers.<name>` 段的 `api_key_env` 依赖 Gateway 进程能读到环境变量，但 Gateway **不会自动加载 `.env` 文件**到进程环境。结果：provider 初始化失败，model 显示 `unknown provider`，所有请求 401。

**Trap 3 (截断显示陷阱):** 用 `grep` 或 `echo` 从 `.env` 提取 key 时，终端可能截断显示为 `sk-cpysbts6ho2iik3bf...`（带字面 `...`），但实际值是完整的。**必须用 Python 逐字符提取并验证长度**，不能直接复制终端显示的截断值写入 config.yaml：
```python
with open('/root/.hermes/.env') as f:
    for line in f:
        if 'XIAOMI_API_KEY=*** in line and not line.startswith('#'):
            key = line.split('=', 1)[1]
            print(f'长度: {len(key)}')  # 应该是 51，不是 13
```

If you need to reference an env var, use a script to read it and pipe into `hermes config set`:

```bash
python3 -c "
import os
key = os.environ.get('MY_API_KEY', '')
from subprocess import run
run(['hermes', 'config', 'set', 'model.api_key', key], check=True)
print('Key set from env var')
"
```

### URL Construction

Hermes appends `/chat/completions` to `model.base_url`.

| base_url | Actual API endpoint |
|----------|-------------------|
| `https://api.example.com/v1` | `https://api.example.com/v1/chat/completions` |
| `https://qianfan.baidubce.com/v2/coding` | `https://qianfan.baidubce.com/v2/coding/chat/completions` |

Some providers use non-standard paths (e.g., Baidu Qianfan Coding Plan uses `/v2/coding` as the base, resulting in `/v2/coding/chat/completions`). Make sure your base_url is the **prefix** before `/chat/completions`.

## Debugging Auth Errors

### ❓ 微信一直输入不回复 — 快速诊断

**症状**：微信/企微显示"对方正在输入..."但一直不出回复，网关日志有：
```
WARNING gateway.run: Primary provider auth failed: Unknown provider 'openai'. — trying fallback
```

**根因**：`model.provider` 配置的值不在 `providers:` 列表中，网关找不到该提供者。

**快速排查：**
```bash
# 1. 检查 model.provider 是什么
grep -A3 "^model:" /root/.hermes/config.yaml | grep provider

# 2. 检查有哪些可用 provider
grep -A1 "^  [a-z]" /root/.hermes/config.yaml | grep -E "^\w+:|api_key:" | head -20

# 3. 确认 model.provider 的值是否存在于 providers: 一节中
```

**修复**：`model.provider` 必须匹配 `providers:` 下的一个键名。例如：
```yaml
model:
  default: mimo-v2.5-pro
  provider: xiaomi-mimo    # ← 必须存在 provders.xiaomi-mimo

providers:
  xiaomi-mimo:              # ← 有这个键
    api_key: sk-...
    base_url: https://api.xiaomimimo.com/v1
```

改完重启网关：
```bash
pm2 restart hermes-gateway
# 检查日志确认不再报 Unknown provider
tail -5 /root/.pm2/logs/hermes-gateway-error.log
```

### Provider 解析链（排障必备）

Hermes 网关在运行时通过 `resolve_requested_provider()` 决定用哪个 provider：

```
1. requested 参数（显式指定）
2. ↓
   model.provider（config.yaml 的 model 段）
3. ↓
   HERMES_INFERENCE_PROVIDER 环境变量
4. ↓
   "auto"（默认）
```

得到 provider 名后，`_resolve_named_custom_runtime()` 在 `providers:` 节查找：
- `providers.<name>` 存在 → 使用其 api_key + base_url
- 不存在 → 报 `Unknown provider '<name>'`

**重要**：`providers:` 下的 provider 名和 `model.provider` 值**必须完全一致**（大小写敏感）。

### 401 Debugging Checklist

1. **Check the request dump** — When Hermes logs a 401, it writes a debug dump:
   ```bash
   cat ~/.hermes/sessions/request_dump_<timestamp>_<session>_<timestamp>.json
   ```

2. **Check the actual Authorization header sent**:
   ```bash
   python3 -c "
   import json
   with open('/root/.hermes/sessions/request_dump_<timestamp>.json') as f:
       d = json.load(f)
   print('URL:', d['request']['url'])
   print('Auth prefix:', d['request']['headers']['Authorization'][:30])
   print('Body model:', d['request']['body'].get('model','N/A'))
   "
   ```
   If the Auth header shows a **literal env var name** (e.g. `Bearer QIANFAN_..._KEY` or `Bearer no-key-required`), the `api_key` field wasn't set to the actual key value.

3. **Verify the key is in `.env`**:
   ```bash
   grep YOUR_VAR_NAME ~/.hermes/.env
   ```
   (Output may be redacted by the secret redactor — use `xxd` to verify raw bytes if needed.)

### Common 401 Error Messages

| Error Code / Signal | Meaning |
|-----------|---------|
| `invalid_iam_token` | Key format is recognized but the **endpoint doesn't match** the key type. The API key is for a different endpoint. |
| `coding_plan_api_key_not_allowed` | The key IS valid and recognized as a Coding Plan key, but the request URL is targeting the **standard chat endpoint**, not the coding endpoint. Fix: use the correct base_url. |
| `invalid_api_key` / `unauthorized` | General auth failure — key may be wrong, expired, or the account doesn't have access to the model. |
| `Bearer no-key-required` in request dump | `model.api_key` is set to an **empty string `''`**, which takes precedence over the provider-level `api_key_env`. The gateway sends a blank key. |
| WARNING: `unknown config keys ignored: provider` | The `provider: custom` field inside `providers.<name>` blocks is **not recognized** as a valid config key by the current Hermes version. It may be silently ignored. Prefer Option A (write key to `model.api_key`) over relying on a providers-section-only config. |

### The `model.api_key: ''` Pitfall ⚠️

**Problem:** When `model.api_key` is set to an empty string `''` AND a provider section has `api_key_env` correctly configured, Hermes still sends `Bearer no-key-required` because the top-level `model.api_key` (even when empty) overrides the provider-level `api_key_env`.

**Additional finding (2026-06):** The `provider: custom` field inside `providers.<name>` blocks generates a WARNING and may be ignored by the current Hermes gateway:
```
WARNING hermes_cli.config: providers.qianfan: unknown config keys ignored: provider
```
This means the `providers`-section approach as a whole has two reliability issues: the `api_key_env` can be shadowed by an empty top-level key, AND the `provider` type declaration may not be read. Prefer Option A below.

```yaml
# ❌ BROKEN — empty model.api_key blocks providers.qianfan.api_key_env
model:
  api_key: ''              # ← empty string takes precedence!
  provider: qianfan

providers:
  qianfan:
    api_key_env: QIANFAN_API_KEY   # ← correctly configured but ignored
    base_url: https://qianfan.baidubce.com/v2/coding
    provider: custom
```

**Fix (choose one — Option A is the belt-and-suspenders winner):**

**Option A (🥇 Recommended — "dual approach"):** Write the actual key value to `model.api_key` AND keep `api_key_env` in the providers section. This way either path works:

```bash
# Read key from .env and write to model.api_key
hermes config set model.api_key "$QIANFAN_API_KEY"
```

```yaml
# Keep both in config.yaml — the key in model.api_key wins if present,
# and api_key_env is a backup if model.api_key is ever removed.
model:
  api_key: bce-v3/...        # ← actual key value (A path)
  provider: qianfan

providers:
  qianfan:
    api_key_env: QIANFAN_API_KEY    # ← env var reference (B path)
    base_url: https://qianfan.baidubce.com/v2/coding
    provider: custom
```

**Option B (Clean approach):** Remove the empty `api_key` from the `model` section entirely:
```yaml
model:
  # api_key: ''   ← delete this line
  provider: qianfan
```

**Verification:** After the fix, inspect a new request dump — the Auth header should show the actual key (`Bearer bce-v3/...`) instead of `Bearer no-key-required`.

## After Changing Config

Always restart the gateway for config changes to take effect in gateway sessions:

```bash
systemctl --user restart hermes-gateway
```

For CLI sessions (like `hermes chat -q "..."`), config changes take effect immediately — no restart needed.

## Testing

```bash
hermes chat -q "你好"
# Or with specific provider:
hermes chat -q "你好" --provider custom
```

## Critical: `providers.<name>` Section MUST Have `provider: custom`... BUT Gateway Ignores It

When adding a provider under the `providers` section (not the top-level `model` section), the `provider: custom` field is **required**. Without it, Hermes cannot determine the authentication method and will send malformed requests, resulting in **401 errors** even though the API key is valid.

**BUT** — the current Hermes gateway version (2026-06) **silently ignores** `provider: custom` inside `providers.<name>` sections with warning: `unknown config keys ignored: provider`. This means:

- For `provider: openai` type providers (MiMo, OpenAI native): **safe to use `providers` section** — no `provider: custom` needed
- For `provider: custom` type providers (Qianfan, relay/中转站): **must use `model` section** — `providers` section will fail silently

**2026-06-13 real-world failure:** `providers.xiaomi-mimo` had `api_key_env: XIAOMI_API_KEY` (Gateway doesn't load `.env` into process env) → provider initialized as `unknown` → `/model` showed `unknown provider` → all requests failed with 401. **Fix:** direct `api_key` value in `providers.xiaomi-mimo`, OR move everything to `model` section.

```yaml
# ❌ WRONG — missing provider field → 401
providers:
  my-relay:
    api_key_env: MY_RELAY_KEY
    base_url: https://relay.example.com/v1
    default_model: gpt-4o
    api_mode: chat_completions

# ✅ CORRECT — includes provider: custom
providers:
  my-relay:
    api_key_env: MY_RELAY_KEY
    base_url: https://relay.example.com/v1
    default_model: gpt-4o
    api_mode: chat_completions
    provider: custom        # ← REQUIRED for non-built-in providers
```

**Debugging path:** If curl to the API succeeds but Hermes returns 401, check whether `provider: custom` is present in the `providers.<name>` section.

## ⚠️ Never Use sed to Edit YAML Config

`sed` string replacement on YAML files is unreliable and can cause:
- Duplicate entries (if pattern matches multiple locations)
- Broken YAML structure (indentation, nesting)
- Lost fields (if yaml.dump reorders keys)

**Always use Python yaml module** for config modifications:

```python
import yaml
with open('/root/.hermes/config.yaml') as f:
    config = yaml.safe_load(f)
config['providers']['my-provider']['provider'] = 'custom'
with open('/root/.hermes/config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
```

## OpenAI-Compatible Relay / 中转站 Configuration

Chinese users often use relay/proxy stations (中转站) that expose an OpenAI-compatible API. Configuration pattern:

```yaml
providers:
  codex-gpt:
    api_key_env: CODEX_API_KEY
    base_url: https://relay.example.com/v1    # 中转站 base URL
    default_model: gpt-5.4-xhigh               # 中转站支持的模型名
    api_mode: chat_completions
    provider: custom                            # ← MUST have this
```

The model name in the relay's response may differ from what you send (e.g., you send `gpt-5.4-xhigh` but the response shows `gpt-5.4`). This is normal — the relay maps model names internally.

## References

- 📕 `references/qianfan-coding-plan.md` — Baidu Qianfan Coding Plan specific config
- 📕 `references/chinese-provider-companies.md` — Chinese AI provider company map (avoid deleting wrong provider)
- 📕 `references/mimo-api-key-env-trap.md` — MiMo api_key_env failure case + key truncation pitfall (2026-06-13)

---

## Chinese Provider Configuration (百度千帆等)

> This section consolidates guidance from `custom-model-provider-config` and `custom-provider-setup` skills.

### ⚠️ Red Line Rule: Confirm Before Configuring

**All API configuration must follow this process, never execute unilaterally:**

```
1. List complete parameters → provider, model, api_key, base_url, special notes
2. Send to user for confirmation → wait for user to say "add" or "go"
3. Then execute configuration → update .env + config.yaml
```

**❌ Forbidden:** Start configuring directly, decide parameters yourself, configure first without asking
**✅ Required:** List all parameters clearly, wait for user approval before acting

This rule applies to any provider (Qianfan, DeepSeek, Kimi, Xiaomi, self-hosted, etc.), whether new or modifying existing config.

### Qianfan Specific Configuration

#### Account Types and Endpoints

| Account Type | Base URL | Use Case |
|-------------|----------| P3 |
| General Inference | `https://qianfan.baidubce.com/v2` | Standard models (ernie-4.5-turbo, etc.) |
| **Coding Plan** | `https://qianfan.baidubce.com/v2/coding` | Code generation models (qianfan-code-latest) |

**Critical Warning:** Coding Plan keys MUST use `/v2/coding` endpoint, otherwise error:
```
Error: coding_plan_api_key_not_allowed
```

#### IAM Token Expiration Handling ⚠️

**Critical Warning:** Baidu Qianfan's `bce-v3/...` format Key is an **IAM temporary token** with validity period (typically days to weeks), **cannot be renewed** — must regenerate when expired.

**Symptoms:**
- Previously working Key suddenly reports `invalid_iam_token`
- No config changes made, curl test also returns 401

**Resolution Process:**
1. Go to Baidu Intelligent Cloud Console → Qianfan Platform → API Key Management, regenerate IAM Token
2. Update `.env`:
   ```bash
   sed -i 's|^QIANFAN_API_KEY=.*|QIANFAN_API_KEY=<newKey>|' ~/.hermes/.env
   ```
3. Test with curl:
   ```bash
   source ~/.hermes/.env
   curl -s https://qianfan.baidubce.com/v2/coding/chat/completions \
     -H "Authorization: Bearer $QIANFAN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"glm-5.1","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'
   ```
4. If using `providers.<name>` section referencing `api_key_env`, **no need to modify config.yaml** — update `.env` and restart gateway
5. If using `model.api_key` with literal value, need to re-write:
   ```bash
   python3 - P4 "
   import os
   key = os.environ.get('QIANFAN_API_KEY', '')
   from subprocess import run
   run(['hermes', 'config', 'set', 'model.api_key', key], check=True)
   print('Key updated')
   "
   ```

**Debugging Mnemonic:** Switch to a coding model on the same provider (e.g., `deepseek-v4-flash`) for testing → if it works, the issue is model incompatibility, not Key expiration. Still 401 → Key expired.

### Qianfan Configuration Complete Example

```yaml
# ~/.hermes/config.yaml
model:
  provider: custom
  base_url: https://qianfan.baidubce.com/v2/coding
  default: qianfan-code-latest
  api_key: bce-v3/ALTAKSP-xxx/xxx...  # Read from .env and filled in

# ~/.hermes/.env
QIANFAN_API_KEY=bce-v3/ALTAKSP-xxx/xxx...
```

**Notes:**
- Qianfan provides multiple authentication methods, above is **IAM Key** method
- Using `/v2/coding` endpoint requires **Coding Plan**
- If using regular API Key, endpoint may differ
