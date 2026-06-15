# Systemd vs PM2 Detection Patterns

## Problem

Many systems use both systemd and PM2 for service management. Watchdog scripts must detect which manager is actually in use before checking service status.

## Detection Algorithm

```python
import subprocess, json

def detect_service_manager(service_name):
    """Detect whether a service is managed by systemd or PM2"""
    
    # Try systemd first (more common for system services)
    try:
        r = subprocess.run(
            ['systemctl', '--user', 'is-active', service_name],
            capture_output=True, text=True, timeout=10
        )
        if r.stdout.strip() in ('active', 'inactive', 'failed'):
            return 'systemd'
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Try PM2 (common for Node.js apps)
    try:
        r = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True, timeout=10)
        processes = json.loads(r.stdout)
        for p in processes:
            if p.get('name') == service_name:
                return 'pm2'
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    
    return None

def check_service_status(service_name):
    """Check service status using the appropriate manager"""
    manager = detect_service_manager(service_name)
    
    if manager == 'systemd':
        r = subprocess.run(
            ['systemctl', '--user', 'is-active', service_name],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip() == 'active'
    
    elif manager == 'pm2':
        r = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True, timeout=10)
        processes = json.loads(r.stdout)
        for p in processes:
            if p.get('name') == service_name:
                return p.get('pm2_env', {}).get('status') == 'online'
    
    return False
```

## Common Scenarios

| Service | Typical Manager | Detection Command |
|---------|-----------------|-------------------|
| hermes-gateway | systemd | `systemctl --user is-active hermes-gateway` |
| hermes-dashboard | PM2 | `pm2 list \| grep dashboard` |
| nginx | systemd (system) | `systemctl is-active nginx` |
| docker | systemd (system) | `systemctl is-active docker` |

## Pitfalls

1. **Assuming wrong manager:** Always detect first, don't hardcode
2. **Timeout issues:** Set reasonable timeouts (10s) for detection commands
3. **Permission issues:** System services may need `sudo`, user services don't
4. **Mixed environments:** Some services might be managed by both (rare but possible)

## Verification

After implementing detection, test with:
```bash
# Manually verify what the script detects
systemctl --user is-active hermes-gateway
pm2 list | grep hermes
```