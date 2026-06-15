# OpenClaw ↔ Hermes Credential Conflicts

## Problem
OpenClaw Gateway's config (`/root/.openclaw/openclaw.json`) may contain wecom channel settings that **share credentials with Hermes' wecom_callback** (same corpId, agentId, secret).

Even if the wecom plugin is "not installed" (OpenClaw can't send messages), the stale config:
1. Produces noise on every startup: `plugin not installed: wecom`
2. Risks accidental message delivery if the plugin ever gets installed

## Detection

```bash
grep -A 15 '"wecom"' /root/.openclaw/openclaw.json
```

## Cleanup

```bash
python3 -c "
import json
with open('/root/.openclaw/openclaw.json') as f:
    d = json.load(f)
d.get('channels', {}).pop('wecom', None)
d.get('channels', {}).pop('openclaw-weixin', None)
d.get('plugins', {}).get('entries', {}).pop('wecom', None)
d.get('plugins', {}).get('entries', {}).pop('openclaw-weixin', None)
with open('/root/.openclaw/openclaw.json', 'w') as f:
    json.dump(d, f, indent=2)
print('✅ Stale wecom/weixin config removed')
"
```

## Verify

```bash
openclaw doctor --fix 2>&1 | grep -iE "wecom|weixin"
# Should show no more warnings about wecom/weixin
```

## Restart Cascade (when OpenClaw ↔ Hermes share credentials)

When OpenClaw Gateway is started/restarted repeatedly (e.g. debugging with
`--bind lan` → fails → retry → different port → re-try), each attempt may
trigger Hermes Gateway restarts too. Every Hermes restart:

1. Sends `shutdown notification` **only** to the home channel (KuHai) ✅
2. Schedules `auto-resume` for **all** active sessions, injecting
   `[System note: Your previous turn was interrupted…]` into every user's
   conversation — including non-admin users (圆圆, 师父, etc.)
3. If a non-admin user then sends any message (even empty `''`), the agent
   responds to the interruption context — generating confusing duplicate
   messages that the user didn't ask for

**Lesson:** Always stabilize OpenClaw Gateway *before* deploying it. Use
`--bind loopback` + PM2 from the start. Avoid iterating on gateway config
while users are actively chatting.
