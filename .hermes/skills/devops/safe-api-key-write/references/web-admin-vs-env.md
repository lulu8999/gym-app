# Hermes Web Admin vs .env: What Goes Where

## The Confusion (from a real case)

User tries to fix an API key on the Hermes web admin panel → key still returns 401 → user reports "I fixed it on the web but it still won't work".

**Root cause:** The web admin panel edits `config.yaml`, but API keys are stored in `.env` and read as environment variables at process start.

## What the Web Admin Controls

| Config file | What goes there |
|---|---|
| `~/.hermes/config.yaml` | Model names, provider definitions, base URLs, UI preferences, plugin config |
| `~/.hermes/.env` | **API Keys, tokens, secrets** — loaded as env vars |

## Example: MiMo Provider config

```yaml
# config.yaml — doesn't store the key
providers:
  custom:
    xiaomi-mimo:
      env_var: XIAOMI_API_KEY  # ← just references the env var
      base_url: https://api.xiaomimimo.com/v1
```

```bash
# .env — stores the actual key
XIAOMI_API_KEY=sk-xxxxxxxxxxxxx
```

## What to Do

- **Provider setup / model list / base URL changes** → web admin or `hermes config set`
- **API key changes** → `python3 /root/scripts/set_env_key.py KEY_NAME value` with atomic write to `.env`, then restart gateway
