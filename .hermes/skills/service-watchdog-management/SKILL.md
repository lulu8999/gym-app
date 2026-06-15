---
name: service-watchdog-management
description: "Managing watchdog scripts for system services - health checks, restart logic, retry limits, and common pitfalls"
category: devops
---

# Service Watchdog Management

## Overview

Watchdog scripts monitor critical services and automatically restart them when they fail. This skill covers patterns for creating and maintaining effective watchdogs, based on real-world debugging of hermes-gateway monitoring.

## Key Patterns

### Service Health Checks

**systemd services:**
```bash
# Check if active
systemctl --user is-active <service>

# Get main PID
systemctl --user show <service> --property=MainPID

# Check status
systemctl --user status <service>
```

**PM2 processes:**
```bash
# List all processes as JSON
pm2 jlist

# Check specific process
pm2 describe <name>
```

**Critical:** Always verify which service manager is actually in use before writing watchdog logic.

### Retry Limits

Always implement maximum retry counts to prevent infinite restart loops:

```python
MAX_RETRIES = 3
COOLDOWN = 1800  # 30 minutes

def check_cooldown():
    """Check if we're in cooldown period"""
    cf = '/tmp/watchdog_last_restart'
    if os.path.exists(cf):
        with open(cf) as f:
            last = float(f.read().strip())
        if time.time() - last < COOLDOWN:
            return True
    return False
```

- Reset retry count when service runs stably for a period
- Log when giving up and requiring manual intervention
- Use longer cooldown periods (30+ minutes) to avoid spam

### Silent Dependency Failures

Scripts may fail silently if dependencies are missing:

```python
# BAD: Script fails, falls back to stale data
try:
    subprocess.run(['python3', 'main.py'], check=True)
except:
    pass  # Silently continues with old data

# GOOD: Check for actual output files
files = sorted(glob.glob('report_*.md'), reverse=True)
if files:
    mtime = os.path.getmtime(files[0])
    if time.time() - mtime > 86400:  # Older than 24h
        print("⚠️ Report data is stale!")
```

## Common Pitfalls

### D-Bus Dependency (systemctl --user in cron)

**Problem:** `systemctl --user` silently fails in cron/non-login environments without a D-Bus session bus.

**Symptoms:**
- Watchdog shows "⚠️ 网关未运行" and attempts restart every cycle (OR shows "✅ 网关正常" for the wrong service)
- `systemctl --user is-active <service>` returns `Failed to connect to bus: No medium found`
- The cron job log is full of restart attempts that all fail
- But the service is actually running fine

**Root cause:** `systemctl --user` needs `XDG_RUNTIME_DIR` to find the D-Bus socket. Cron often lacks this, but if set (e.g. `XDG_RUNTIME_DIR=/run/user/0`), `systemctl --user` works even in cron:

```bash
# Without XDG_RUNTIME_DIR — fails
$ env -i HOME=$HOME systemctl --user is-active my-service
Failed to connect to bus: No medium found

# With XDG_RUNTIME_DIR — works
$ XDG_RUNTIME_DIR=/run/user/0 systemctl --user is-active my-service
active
```

**Recommended fix — PID-based check, no D-Bus needed:**
```python
def check_systemd(service_name):
    """Try systemctl --user, fallback to pgrep if no D-Bus."""
    try:
        r = subprocess.run(
            ['systemctl', '--user', 'is-active', service_name],
            capture_output=True, text=True, timeout=10
        )
        if r.stdout.strip() == 'active':
            return True
        if 'No medium found' in r.stderr or 'could not connect' in r.stderr.lower():
            r2 = subprocess.run(
                ['pgrep', '-f', service_name.replace('.service', '')],
                capture_output=True, text=True, timeout=5
            )
            return r2.returncode == 0
        return False
    except:
        return False
```

### Wrong Service Name (stale references)

**Problem:** Watchdog checks for a renamed or never-existent service.

**Symptoms:**
- Service named `hermes-gateway` but watchdog checks `openclaw-gateway.service`
- `systemctl --user is-active old-name` always returns "not-found"
- Watchdog perpetually reports "not active" while real service is fine

**Fix:** Always verify the actual service name:
```bash
systemctl --user list-units --type=service --all | grep -iE 'gateway|hermes|openclaw'
```

### Monitoring the Wrong Process (False All-Clear)

**Problem:** Two different gateways coexist on the same machine. Watchdog monitors the old/inactive one while the real production gateway runs independently.

**Typical scenario — OpenClaw vs Hermes coexistence:**
| Service | Manager | PID | Port | Purpose |
|---------|---------|-----|------|---------|
| `openclaw-gateway.service` | systemd user | 239727 | 18789 | Legacy Node.js gateway |
| Hermes gateway (via script) | shell/script | 1624792 | 8645 | Current Python gateway |

**Symptoms:**
- Watchdog log shows continuous `✅ 网关正常` for days
- But it's checking `openclaw-gateway.service`, not the actual Hermes gateway
- The old OpenClaw gateway happens to be running stably, giving false confidence
- If Hermes gateway dies, the watchdog **will not detect it** because the old OpenClaw is still up

**Detection:**
```bash
# 1. Check what the watchdog actually monitors
grep 'SERVICE\|service_name\|check_gateway' /path/to/watchdog.py

# 2. List ALL gateway processes, not just the ones the watchdog checks
ps aux | grep -iE 'gateway|hermes|openclaw' | grep -v grep

# 3. Check what ports they listen on
ss -tlnp | grep -E '8645|18789'

# 4. Cross-reference systemd services
systemctl --user list-units --type=service --all 2>/dev/null | grep -iE 'gateway|hermes'
```

**Root cause:** During migration from OpenClaw to Hermes, the old service unit (`openclaw-gateway.service`) was left running. The watchdog was never updated to check the new process.

**Fix:**
1. Decide which gateway is the active production one
2. Update the watchdog's `SERVICE` variable to the correct service name
3. If the real gateway doesn't use systemd, switch to PID-based or port-based checking:
   ```python
   def check_hermes_gateway():
       \"\"\"Check Hermes gateway by port (8645) — no systemd needed\"\"\"
       try:
           r = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True, timeout=5)
           return ':8645' in r.stdout
       except:
           return False
   ```
4. Consider stopping the old inactive gateway to avoid confusion:
   ```bash
   systemctl --user stop openclaw-gateway.service
   systemctl --user disable openclaw-gateway.service
   ```

### Stale Log Path (dead code from software migration)

**Problem:** Watchdog checks for keywords in a log directory that no longer receives writes.

**Symptoms:**
- Script checks `/tmp/openclaw/` for "stalled session" — but that's old OpenClaw, not Hermes
- No "stalled session" ever appears in Hermes logs
- The check is dead code that always returns False

**Fix:** Remove or update log path references when the monitored software changes:
```bash
ls -lt /root/.hermes/logs/  # Find current log locations
```
### ❌ Gateway Not a systemd Service (2026-06-09 Debug Case)

**Problem:** Watchdog checks for `hermes-gateway` as a systemd user service, but Hermes gateway actually runs as a regular bash script process on VPS.

**Symptoms:**
- Watchdog reports "⚠️ Gateway(hermes-gateway) 未运行" every cycle
- Attempted restart fails: "❌ Gateway 重启失败"
- But gateway is actually running fine (PID 1624792)
- Service shows "not found" because it was never a systemd service

**Root Cause:**
```bash
# Actual gateway running as:
/root/run-hermes-gateway.sh  # bash script
hermes gateway run           # Python process (PID 1624792)

# NOT as systemd:
systemctl --user list-units --type=service | grep hermes
# (empty - no such service exists)
```

**Fix (2026-06-09 applied):**
```python
# In watchdog script, REMOVE gateway from services list:
services = [
    # ('hermes-gateway', 'Gateway'),  # ❌ 错误 - 不是 systemd 服务
]

# Gateway 自己有健康检查，不需要看门狗监控
```

**Key Insight:** Hermes gateway self-manages its health. The watchdog should NOT try to monitor it as a systemd service. If gateway dies, the gateway's own restart logic or cron will handle it.

---

### Wrong Service Manager

**Problem:** Checking PM2 for a systemd-managed service, OR checking systemd for a script-based service

**Symptoms:**
- Watchdog reports service "not running" when it actually is
- Restart attempts fail silently
- Logs show repeated "service not found" errors

**Common case - hermes-gateway runs as script, NOT systemd:**

The Hermes gateway on Lulu's VPS runs via:
```bash
/root/run-hermes-gateway.sh  # bash 启动脚本
hermes gateway run            # 实际 Python 进程
```

It is NOT a systemd user service. The watchdog should NOT check:
```python
# ❌ 错误 - hermes-gateway 根本不是 systemd 服务
services = [
    ('hermes-gateway', 'Gateway'),
]
```

Instead, either don't monitor it (let the gateway manage itself), or monitor via port:
```python
# ✅ 正确 - 不监控 gateway（它有自己的健康检查）
services = []

# 或者如果要监控，用端口检查
def check_gateway_port():
    try:
        r = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
        return ':18789' in r.stdout  # gateway 端口
    except:
        return False
```

**Solution:**
```python
def check_service_status(name):
    # First try systemd
    try:
        r = subprocess.run(['systemctl', '--user', 'is-active', name],
                          capture_output=True, text=True, timeout=10)
        if r.stdout.strip() == 'active':
            return True, 'systemd'
    except:
        pass
    
    # Then try PM2
    try:
        r = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True, timeout=10)
        processes = json.loads(r.stdout)
        for p in processes:
            if p.get('name') == name and p 
                return True, 'pm2'
    except:
        pass
    
    return False, None
```

### Infinite Restart Loops

**Problem:** Watchdog keeps restarting a service that fails immediately

**Solution:** Implement retry limits and cooldown periods

```python
retry_file = f'/tmp/{service_name}_retries'
def get_retry_count():
    if os.path.exists(retry_file):
        with open(retry_file) as f:
            data = json.load(f)
        if time.time() - data.get('ts', 0) > 3600:  # Reset after 1h
            return 0
        return data.get('count', 0)
    return 0

def increment_retry():
    count = get_retry_count() + 1
    with open(retry_file, 'w') as f:
        json.dump({'count': count, 'ts': time.time()}, f)
    return count
```

### Claiming Credit for User Fixes

**Problem:** Reporting "I fixed X" when the user actually fixed it manually

**Symptoms:**
- User says "你修了个屁，是我去终端上把你修好的"
- Trust erodes when agent claims work it didn't do

**Solution:**
- Accurately report what was done
- If user fixed it, say "You fixed X" not "I fixed X"
- When in doubt, ask: "Did you fix this manually, or should I investigate?"

## Debugging Steps

1. **Identify service manager:** Is it systemd, PM2, or something else?
   ```bash
   systemctl --user status <service>  # Check if systemd-managed
   pm2 list                           # Check if PM2-managed
   ```

2. **Check dependencies:** Are all required modules/packages installed?
   ```bash
   python3 -c "import akshare"  # Test specific import
   ```

3. **Verify data flow:** Is the script actually generating new data or reading stale files?
   ```bash
   ls -lt /path/to/reports/ | head -5  # Check file timestamps
   ```

4. **Test watchdog logic:** Run the watchdog manually and observe output
   ```bash
   python3 /path/to/watchdog.py 2>&1
   ```

## Example: hermes-gateway Watchdog

```python
#!/usr/bin/env python3
"""Hermes gateway watchdog - checks systemd service"""
import subprocess, time, json, os

def check_gateway():
    """Check if hermes-gateway is running via systemd"""
    try:
        r = subprocess.run(
            ['systemctl', '--user', 'is-active', 'hermes-gateway'],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip() == 'active'
    except:
        return False

def main():
    if check_gateway():
        return  # Silent exit when healthy
    
    print("⚠️ Gateway not running")
    # ... restart logic with retry limits ...

if __name__ == '__main__':
    main()
```

## References

- See `references/systemd-vs-pm2.md` for service manager detection patterns
- See `references/retry-patterns.md` for retry limit implementations
- See `references/silent-failures.md` for debugging missing dependencies