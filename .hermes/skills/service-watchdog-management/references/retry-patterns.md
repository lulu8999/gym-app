# Retry Patterns for Watchdog Scripts

## Problem

Watchdog scripts that automatically restart services can enter infinite loops if the service fails immediately after restart. This wastes resources and floods logs.

## Basic Retry Pattern

```python
import time, json, os

MAX_RETRIES = 3
COOLDOWN = 1800  # 30 minutes in seconds

def get_retry_file(service_name):
    return f'/tmp/{service_name}_watchdog_retries'

def get_retry_count(service_name):
    """Get current retry count, reset if older than 1 hour"""
    retry_file = get_retry_file(service_name)
    if not os.path.exists(retry_file):
        return 0
    
    try:
        with open(retry_file) as f:
            data = json.load(f)
        
        # Reset count if older than 1 hour
        if time.time() - data.get('ts', 0) > 3600:
            return 0
        
        return data.get('count', 0)
    except:
        return 0

def increment_retry(service_name):
    """Increment retry count"""
    retry_file = get_retry_file(service_name)
    count = get_retry_count(service_name) + 1
    with open(retry_file, 'w') as f:
        json.dump({'count': count, 'ts': time.time()}, f)
    return count

def reset_retries(service_name):
    """Reset retry count on successful run"""
    retry_file = get_retry_file(service_name)
    if os.path.exists(retry_file):
        os.remove(retry_file)
```

## Cooldown Pattern

```python
import time, os

COOLDOWN = 1800  # 30 minutes

def check_cooldown(service_name):
    """Check if we're in cooldown period"""
    cooldown_file = f'/tmp/{service_name}_cooldown'
    if not os.path.exists(cooldown_file):
        return False
    
    try:
        with open(cooldown_file) as f:
            last_restart = float(f.read().strip())
        return time.time() - last_restart < COOLDOWN
    except:
        return False

def set_cooldown(service_name):
    """Set cooldown timestamp"""
    cooldown_file = f'/tmp/{service_name}_cooldown'
    with open(cooldown_file, 'w') as f:
        f.write(str(time.time()))
```

## Complete Watchdog with Retry Logic

```python
#!/usr/bin/env python3
"""Watchdog with retry limits and cooldown"""
import subprocess, time, json, os, sys

MAX_RETRIES = 3
COOLDOWN = 1800  # 30 minutes

def log(msg):
    from datetime import datetime
    t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{t}] {msg}')

def get_retry_count(service):
    retry_file = f'/tmp/{service}_retries'
    if not os.path.exists(retry_file):
        return 0
    try:
        with open(retry_file) as f:
            data = json.load(f)
        if time.time() - data.get('ts', 0) > 3600:
            return 0
        return data.get('count', 0)
    except:
        return 0

def increment_retry(service):
    retry_file = f'/tmp/{service}_retries'
    count = get_retry_count(service) + 1
    with open(retry_file, 'w') as f:
        json.dump({'count': count, 'ts': time.time()}, f)
    return count

def reset_retries(service):
    retry_file = f'/tmp/{service}_retries'
    if os.path.exists(retry_file):
        os.remove(retry_file)

def check_cooldown(service):
    cooldown_file = f'/tmp/{service}_cooldown'
    if not os.path.exists(cooldown_file):
        return False
    try:
        with open(cooldown_file) as f:
            last = float(f.read().strip())
        return time.time() - last < COOLDOWN
    except:
        return False

def set_cooldown(service):
    cooldown_file = f'/tmp/{service}_cooldown'
    with open(cooldown_file, 'w') as f:
        f.write(str(time.time()))

def check_service(service):
    """Check if service is running (systemd example)"""
    try:
        r = subprocess.run(
            ['systemctl', '--user', 'is-active', service],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip() == 'active'
    except:
        return False

def restart_service(service):
    """Restart service (systemd example)"""
    try:
        subprocess.run(['systemctl', '--user', 'restart', service], 
                      timeout=30, capture_output=True)
        time.sleep(5)
        return check_service(service)
    except:
        return False

def main(service):
    # Check if in cooldown
    if check_cooldown(service):
        log(f'⏳ {service} in cooldown, skipping')
        return
    
    # Check if service is running
    if check_service(service):
        reset_retries(service)  # Success - reset retries
        return  # Silent exit when healthy
    
    # Service is down
    retries = get_retry_count(service)
    if retries >= MAX_RETRIES:
        log(f'❌ {service} failed {retries} times, giving up')
        return
    
    # Try to restart
    log(f'⚠️ {service} not running, attempt {retries + 1}/{MAX_RETRIES}')
    increment_retry(service)
    
    if restart_service(service):
        log(f'✅ {service} restarted successfully')
        reset_retries(service)
    else:
        log(f'❌ {service} restart failed')
    
    set_cooldown(service)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print('Usage: watchdog.py <service_name>')
```

## Best Practices

1. **Reset on success:** Always reset retry count when service runs stably
2. **Time-based reset:** Reset retries after 1 hour to allow fresh attempts
3. **Long cooldowns:** Use 30+ minute cooldowns to avoid spam
4. **Logging:** Log retry attempts and final give-up messages
5. **User notification:** When giving up, notify that manual intervention is needed

## Common Mistakes

1. **No retry limit:** Infinite loops waste resources
2. **Too short cooldown:** Rapid restart attempts spam logs
3. **Not resetting on success:** Permanent backoff after transient failures
4. **Hardcoded paths:** Use service-specific temp files to avoid conflicts