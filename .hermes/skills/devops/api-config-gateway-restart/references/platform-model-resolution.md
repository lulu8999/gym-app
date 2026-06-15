# Platform ↔ Model Resolution

How gateway platforms resolve which model to use — critical for troubleshooting "platform X not responding."

## Rule: Gateway Platforms Use the Default Model

All gateway-connected platforms (weixin, telegram, discord, wecom_callback, slack, etc.) use the model configured in `config.yaml`'s `model.default` / `model.provider`:

```yaml
model:
  default: mimo-v2.5-pro
  provider: xiaomi-mimo
```

**This is the ONLY setting that controls what model gateway sessions use.**

## What `--global` Does NOT Do

Switching model via CLI flag (`--global` or `hermes chat --model X`) only affects the current CLI session. It does NOT:
- Change `config.yaml`
- Affect any gateway platform session
- Persist across sessions

## Weixin Auto-Load Behavior

Unlike Telegram/Discord/wecom_callback which need explicit `platforms:` sections in config.yaml, **Weixin (个人微信) is auto-loaded** when a user has previously logged in via QR code. The account data lives at:

```
~/.hermes/weixin/accounts/
```

No `platforms.weixin:` config block exists in config.yaml. The platform is discovered automatically by the gateway at startup.

## Diagnostic Flow for "Platform X Not Responding"

1. Check gateway status:
   ```bash
   pm2 list | grep hermes-gateway
   ```

2. Check default model in config:
   ```bash
   grep -A2 "^model:" ~/.hermes/config.yaml
   ```

3. Check gateway logs for errors:
   ```bash
   pm2 logs hermes-gateway --lines 100 --nostream 2>/dev/null | grep -i "error\|no llm provider\|unknown config"
   ```

4. **Common culprit: broken default model.** If the default provider is misconfigured (missing key, wrong base_url, unknown config keys), all gateway sessions fail with:
   ```
   RuntimeError: No LLM provider configured. Run `hermes model` to select a provider...
   ```

   The fix is NOT in the CLI — it must be in `config.yaml` + gateway restart.

## Fix: Changing Model for All Platforms

To make a new model take effect on all platforms (weixin, telegram, etc.):

1. Update `model.default` and `model.provider` in config.yaml
2. Optionally delete the `providers.<name>` section if the old provider config has issues (e.g., `provider: openai` is ignored as unknown key)
3. Restart gateway: `pm2 restart hermes-gateway` (or `pm2 resurrect` if using dump)

The CLI session model override is temporary — it will use the new default after restart anyway.

## Related

- `api-config-gateway-restart` SKILL.md — full API config + restart procedure
- `hermes-custom-provider-setup` SKILL.md — provider-specific config traps
