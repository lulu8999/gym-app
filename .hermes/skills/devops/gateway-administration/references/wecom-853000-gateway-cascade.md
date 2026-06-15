# WeCom errcode 853000 → Gateway Killed Cascade

## Pattern

When `wecom` bot platform has credentials but `enabled: false`, gateway still
attempts connection → fails with errcode 853000 → repeated failures → systemd
SIGTERM kills entire gateway process → WeChat(weixin) and wecom_callback go
down too.

## Log Signature

```
INFO gateway.run: Connecting to wecom_callback...
INFO gateway.platforms.wecom_callback: [WecomCallback] HTTP server listening on 0.0.0.0:8645
INFO gateway.platforms.wecom_callback: [WecomCallback] Token refreshed ... expires in 7200s
INFO gateway.run: ✓ wecom_callback connected
INFO gateway.run: Connecting to wecom...
ERROR gateway.platforms.wecom: [Wecom] Failed to connect: invalid bot_id or secret, hint: [...], errcode=853000
WARNING gateway.run: ✗ wecom failed to connect
INFO gateway.run: Connecting to weixin...
INFO gateway.run: ✓ weixin connected
INFO gateway.run: Gateway running with 2 platform(s)
INFO gateway.run: Starting reconnection watcher for 1 failed platform(s): wecom
INFO gateway.run: Reconnecting wecom (attempt 2)...
ERROR gateway.platforms.wecom: [Wecom] Failed to connect: ... errcode=853000
INFO gateway.run: Received SIGTERM — initiating shutdown
```

Key indicators:
- wecom_callback and weixin connect fine
- wecom bot fails with errcode 853000
- Gateway gets SIGTERM shortly after (minutes)
- wecom-tunnel (cloudflared) errors: "connection refused" to localhost:8645 (expected, gateway dead)

## Root Cause

The `wecom` platform section in config.yaml has `bot_id` and `bot_secret` from
an old/external app. Even with `enabled: false`, the gateway tries to connect
because the platform config section exists with credentials. The errcode 853000
("invalid bot_id or secret") fires repeatedly, and systemd eventually kills the
gateway process.

## Fix Options

### Option A: Remove wecom platform section (recommended if bot not needed)
Delete the entire `platforms.wecom` block from config.yaml. Lulu uses
`wecom_callback` (HTTP callback), not the `wecom` bot WebSocket.

### Option B: Remove just the credentials
Set `bot_id: ''` and `bot_secret: ''` in the wecom section so the gateway
won't attempt to authenticate.

### Option C: Update credentials
If the bot platform IS needed, get fresh bot_id and bot_secret from the
企业微信 admin panel.

## Verification After Fix

```bash
# Start gateway
hermes gateway run --replace &

# Check logs — should NOT see "Connecting to wecom..."
tail -f /root/.hermes/logs/gateway.log | grep -E "wecom|connected|platform"
```

Expected output (no wecom bot attempt):
```
✓ wecom_callback connected
✓ weixin connected
Gateway running with 2 platform(s)
```
