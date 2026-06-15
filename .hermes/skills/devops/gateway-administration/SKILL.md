---
name: gateway-administration
description: >-
  Configure Hermes Gateway approval modes, system notification routing, restart
  handling, and notification suppression for multi-user deployments.
---

# Hermes Gateway Administration

Use when the user asks to change approval behavior, suppress system
notifications, configure who receives gateway restart/error notices, or set
up home-channel routing.

## Approval Modes

Hermes supports three approval modes for dangerous commands:

| Mode | Behavior | When to use |
|------|----------|-------------|
| `manual` | Always prompt for approval (default) | Single-user, you want maximum safety |
| `smart` | LLM auto-approves low-risk, prompts on high-risk | Multi-user, admin trusts the model |
| `off` | Skip all prompts (`--yolo`) | Dev/testing only |

```bash
hermes config set approvals.mode smart      # recommended for multi-user
hermes config set approvals.mode manual     # safest
hermes config set approvals.mode off        # dangerous
```

### `smart` mode approval triggers

Commands in `command_allowlist` (config.yaml) always require approval:

- Stop/restart system service
- Shell command via `-c`/`-lc` flag
- Delete in root path
- Overwrite project env/config file
- Script execution via heredoc
- Script execution via `-e`/`-c` flag
- Stop/restart hermes gateway
- Overwrite system config

## System Notification Routing

### Home Channel (`/sethome`)

The home channel is the **only** destination for gateway system notifications
(shutdown notices, restart alerts, error messages).

```bash
# In the chat that should receive notifications:
/sethome
```

After setting, verify:
```bash
grep WECOM_CALLBACK_HOME_CHANNEL /root/.hermes/.env
# Should show platform:chat_id — e.g. ww815119bb08398d37:KuHai
```

### How Gateway Restarts Affect Users

When the gateway is interrupted (SIGINT/SIGTERM):

1. **Shutdown notification** → sent ONLY to home channel ✅
2. **Auto-resume** → injects `[System note: Your previous turn was interrupted...]`
   into **all** active sessions — including non-admin users

This means non-admin users (圆圆, 师父, etc.) see system interruption context
in their conversations. If they then send a message (even empty `''`), the
agent responds to the interruption context — generating confusing messages.

**Fix:** Handle the interruption silently. When you see `[System note:` in a
non-admin user's session, do not mention the restart — just continue
naturally.

### Self-Improvement Review Suppression

The `display.turn_completion_explainer` setting controls post-turn summaries
like `💾 Self-improvement review: Memory updated · Skill 'X' created.`:

```bash
hermes config set display.turn_completion_explainer false
```

Disable this for multi-user deployments so system messages don't appear in
any user's chat.

## Multi-User Notification Policy

When deploying Hermes with multiple users (圆圆的 settings: trusted, 师父:
trusted, etc.), follow these rules:

| Notification type | Goes to |
|-------------------|---------|
| Gateway restart/shutdown | Home channel only |
| Permission approval requests | Admin only |
| Self-improvement review | Suppressed (disabled) |
| Cron job delivery | Configured per job deliver target |
| Balance alerts | Configured per cron job |
| Daily/weekly reports | Configured per cron job |

## Token Cost Tracking

The daily summary cron job (6:00 AM) includes precise DeepSeek cost calculation
via the **balance-difference method** — read yesterday's balance, read today's
balance, subtract. No estimation or cache-hit-rate guessing.

See `references/token-cost-calculation.md` for full design and implementation.

## Math / Cost Presentation

When reporting token costs, balances, or any numerical work for this user:
1. Show the calculation **step by step** — one line per operation
2. Use the actual balance difference as the authoritative "spent" figure
3. Always convert USD → CNY explicitly (rate: 7.3)
4. Show the unit (¥ or $) clearly — don't mix them up
5. List token counts alongside their corresponding prices

**Wrong:** "about ¥5.89"

**Right:**
```
Input cache miss: 1.58M × ¥1.02 = ¥1.61
Input cache hit:  163M × ¥0.02  = ¥3.26
Output:           0.49M × ¥2.04 = ¥1.00
Total (calc):                    ¥5.87
Actual (balance):                ¥11.63 ← authoritative
```

## Self-Healing Script (`hermes_self_heal.py`)

The self-heal script at `/root/scripts/hermes_self_heal.py` monitors PM2
services and auto-recovers from failures. See `references/self-heal-design.md`
for architecture, ANSI-parsing patterns, and cooldown mechanism.

### Common pitfalls

1. **ANSI color codes in PM2 output** — `pm2 show` output includes
   `\x1b[32m\x1b[1monline\x1b[22m\x1b[39m`. Strip before parsing:
   `re.sub(r'\x1b\[\d+(;\d+)*[a-zA-Z]', '', raw)`.

2. **Infinite restart loop** — If the script restarts a service but the port
   isn't ready yet, the next check restarts again. Fix with:
   - 120s cooldown between restarts of the same service
   - Skip if process is `online` but port not ready (transient state)
   - Save last-check state → detect repeated issues across checks
   - Read OLD state BEFORE writing new one (avoid self-match)

3. **State file dedup** — `.self_heal_last_state.json` holds
   `{timestamp, issues: [{service, problem}]}`. Write AFTER reading old state.

### Services monitored

- `hermes-gateway` (port 8645)
- `hermes-dashboard` (port 9119)
- `openclaw-gateway` (port 9000)
- `location-server` (port 9803)
- `litellm-proxy` (port 41111)

## OpenClaw Gateway 启动问题

### bind=lan 要求 auth mode=token

OpenClaw 配置 `bind=lan` 时，`gateway.auth.mode` 不能为 `"none"`。启动日志报：
```
Refusing to bind gateway to lan without auth.
```

**修复：** 将 `~/.openclaw/openclaw.json` 中的 `gateway.auth.mode` 从 `"none"` 改为 `"token"`（token 值本身不需要改）。

**验证：** `openclaw gateway status` → Runtime: running, Connectivity probe: ok

### 旧插件条目阻塞启动

安装新插件（如 `@wecom/wecom-openclaw-plugin@2026.5.7`）后，若 `plugins.entries` 中仍有旧插件条目（如 `"wecom": {"enabled": true}`），`systemctl restart` 可能失败（exit code 203/EXEC）。

**修复：** 编辑 `~/.openclaw/openclaw.json`，删除 `plugins.entries` 下的旧条目。

**完整流程：**
```bash
# 1. 备份
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup
# 2. 修复 auth mode（若 bind=lan）
# 3. 删除旧插件条目
# 4. 重新安装服务单元 + 启动
openclaw gateway install    # ← 重要：重写 systemd 单元文件，修复 exec 路径问题
openclaw gateway start      # ← 启动服务
# 5. 验证
openclaw gateway status     # → Runtime: running, Connectivity probe: ok
```

**参考：** `references/openclaw-startup-203-error.md` 详细排障记录。## OpenClaw Credentials Conflict

OpenClaw's config may contain wecom channel settings that **share
credentials with Hermes' wecom_callback** (same corpId/agentId/secret).
Even if the wecom plugin is \"not installed\" (can't send messages), stale
config is a hygiene issue. Check `~/.openclaw/openclaw.json` for
`channels.wecom` entries when troubleshooting duplicate notifications.

## Pairing Auto-Approve

By default, new users connecting to the gateway require manual approval
(`hermes pairing approve <platform> <code>`). For trusted multi-user
deployments where you've already vetted all users, enable auto-approve:

```bash
hermes config set pairing.auto_approve true
hermes gateway restart
```

**Security note:** `auto_approve` is all-or-nothing — it approves ALL
pairing requests, not just known users. Access control still applies via
`access.yaml` (role-based permissions), so an auto-approved attacker
gets `untrusted` role at most. But they CAN send messages. If you need
per-user approval granularity, keep `auto_approve: false` and approve
manually.

**When pairing requests appear unexpectedly:** usually caused by gateway
restart invalidating existing session tokens. Known users reconnecting
will trigger a new pairing request. This is normal — approve once and
they're back.

## Gateway Down After Restart — Why It Stays Down

### Root cause: `systemctl stop` from inside the gateway kills itself

When a **restart command is executed from within the gateway agent** (e.g. an agent tool call runs `systemctl --user stop hermes-gateway && sleep 5 && systemctl --user start hermes-gateway`):

1. The `systemctl stop` sends SIGTERM to the gateway process — which is the **parent** of the bash child running the command
2. The gateway begins shutdown: it runs its shutdown diagnostic, waits for in-flight tool calls
3. If a tool call is still running (e.g. a 30s `terminal` timeout), the main process doesn't exit immediately
4. systemd eventually sends SIGKILL to remaining processes in the cgroup
5. The `sleep 5 && systemctl start` part never executes — the bash child was killed before it could run `start`
6. `Restart=always` does NOT kick in because `systemctl stop` was a **manual stop** — systemd respects the stop intent and won't auto-restart

**Key insight:** A restart command issued from inside the gateway is a self-destruct sequence. Never do it.

### How to restart the gateway safely

| Method | Works from | Notes |
|--------|-----------|-------|
| `systemctl --user restart hermes-gateway` | Any terminal NOT inside the gateway | Safe — separate process, not a child of the dying gateway |
| `hermes gateway restart` | Hermes CLI session | Safe — Hermes CLI manages the lifecycle externally |
| `systemctl --user stop; sleep 5; systemctl --user start` | ONLY from an external SSH/login session | Trap: don't run this from an agent tool call inside the gateway |

### ⚠️ NEVER kill the gateway process directly

**❌ Forbidden:** `kill -9 <pid>`, `kill <pid>`, or any direct process termination.

**Why:** Directly killing the gateway process triggers an ungraceful shutdown:
1. The `sigterm_handler` / `sigint_handler` can't run cleanup properly
2. WeChat/微信 connections are **hard-disconnected** (not gracefully drained)
3. The shutdown diagnostic script won't run — making debugging harder
4. Auto-resume may produce garbled system notifications to active sessions

**✅ Correct way:**
```bash
systemctl --user stop hermes-gateway     # stop first
sleep 5                                   # wait for drain
systemctl --user start hermes-gateway    # start fresh
```

If systemd user bus isn't available (e.g. in cron context or VPS):
```bash
# Stop the running process gracefully
kill -TERM $(pgrep -f "hermes gateway run" | head -1)
sleep 5
# Start a new one in background
hermes gateway run --replace
```

### ⚠️ PM2 vs systemd 双重管理陷阱

**症状**：PM2 `hermes-gateway` 反复崩溃（restart count 飙升到 77+），但微信收发正常。

**原因**：`systemctl --user` 和 PM2 都在管理 hermes-gateway：
1. `pm2 resurrect` 启动了一个网关进程
2. `systemctl --user start hermes-gateway` 也启动了一个
3. 先启动的占用了端口 8645
4. 后启动的因端口冲突反复崩溃

**修复**：
```bash
pm2 stop hermes-gateway            # 停掉 PM2 管理的那个
# 用 systemd 管理网关：
systemctl --user restart hermes-gateway
```

**预防**：
- 网关只用 systemd 管理，不要混用 PM2
- `pm2 resurrect` 后检查是否有 `hermes-gateway`，如有立即 `pm2 stop`
- systemd 的 `Restart=always` 比 PM2 的 `autorestart` 更可靠（不会因端口占用无限循环）

**Legacy note:** The old watchdog script (`gateway_watchdog.py`) also uses `systemctl --user` to restart. When that fails (no D-Bus), it's better to fix the watchdog than to fall back to killing the process directly.

**Manual start from root CLI (no systemd bus available):**

```bash
/root/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace
```

Use `terminal(background=true, notify_on_complete=true)` for this — the gateway is a long-running process.

## Gateway Down Diagnostic Sequence

When the user reports WeChat/微信 is disconnected, follow this order:

### Step 1: Is the port listening?
```bash
ss -tlnp | grep 8645
```
Nothing → gateway is dead.

### Step 2: Check systemd journal (most authoritative)
```bash
journalctl --user -u hermes-gateway.service --no-pager -n 30
```
Look for:
- `SIGTERM` / `SIGKILL` — was it killed?
- `Failed with result 'signal'` — systemd won't auto-restart
- `Stopping ...` — was a `systemctl stop` issued?
- `timeout` in last tool call — was a slow command blocking shutdown?

### Step 3: Check gateway logs
```bash
cat /root/.hermes/logs/gateway.log | tail -60
cat /root/.hermes/logs/gateway-shutdown-diag.log
cat /root/.hermes/logs/gateway-exit-diag.log
```

### Step 4: Check cloudflared tunnel
```bash
pm2 list | grep wecom-tunnel
```
The tunnel (wecom-tunnel) forwards `callback.lulugame.fun → localhost:8645`. If the tunnel is up but port 8645 is down, the gateway is the problem, not the tunnel.

### Step 5: Check PM2 services for collateral damage
Sometimes the gateway restart takes down other PM2 services (via `KillMode=mixed` cgroup cleanup). Check:
```bash
pm2 list
```

### Common pitfalls

1. **"gateway was running fine, then died"** → Check if a `systemctl stop` was issued from inside the gateway (see "self-restart trap" above). The shutdown diagnostic log captures the pstree — look for a `systemctl stop` as a child of the gateway process.

2. **`Restart=always` didn't kick in** → `systemctl stop` is a manual stop, so systemd respects the intent. The service stays stopped. Use `systemctl start` (not `restart`) to bring it back.

3. **wecom platform error vs wecom_callback** — The `wecom` platform (WebSocket bot) and `wecom_callback` (HTTP callback) are two completely separate platforms:
   - `wecom` platform uses `bot_id`/`bot_secret` — this has been failing with `invalid bot_id or secret` for this deployment
   - `wecom_callback` uses `corp_id`/`corp_secret`/`agent_id` — this is the working channel
   - **The wecom WebSocket failure is NOT a problem** — the callback channel works independently
   - Don't waste time debugging the wecom bot credentials; the callback channel is what Lulu uses
   - **⚠️ Pitfall: `enabled: false` may not prevent connection attempts** — If the `wecom` platform section has credentials (bot_id/bot_secret) even with `enabled: false`, the gateway may still try to connect and fail. The repeated failure + SIGTERM combo can kill the gateway process. If the bot platform isn't needed, remove the credentials or the entire `wecom` platform section from config.yaml.
   - **errcode 853000** = `invalid bot_id or secret` — the wecom bot credentials are wrong/expired. This comes from the wecom WebSocket bot platform, NOT from wecom_callback

## Provider Switching State Confusion

After switching providers (e.g. DeepSeek → MiMo → DeepSeek), the gateway
may enter a confused state where API calls fail with **"Missing
Authentication header"** — meaning no Authorization header was sent at all.

**Root cause:** The gateway process hasn't fully reloaded env vars or
provider config after the switch. The running process still has stale
credentials from the previous provider.

**Fix:** Always restart the gateway after provider switches:

```bash
hermes gateway restart
```

**Diagnostic clue:** If you see "Missing Authentication header" (not
"Invalid API Key"), it's a gateway state issue, not a key issue. The
key itself is fine — the gateway just isn't sending it. One restart
solves it.

**Prevention:** When switching models, always do it in this order:
1. Update config: `hermes config set model.default <model>`
2. Restart gateway: `hermes gateway restart`
3. Start a new session (or send the first message in the existing one)

## Related

- `openclaw-gateway` skill — for OpenClaw-specific gateway setup
- `hermes-session-recovery` skill — gateway interruption handling per session
- `references/wecom-853000-gateway-cascade.md` — errcode 853000 failure pattern + fix
- `references/suppress-system-notifications.md` — full notification routing rules
- `references/token-cost-calculation.md` — precise DeepSeek cost tracking via balance difference
- `references/self-heal-design.md` — self-heal architecture, ANSI parsing, cooldown details
- `~/.hermes/access.yaml` → user role mapping
