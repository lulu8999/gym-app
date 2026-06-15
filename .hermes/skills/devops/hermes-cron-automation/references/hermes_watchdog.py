#!/usr/bin/env python3
"""
Hermes 网关看门狗 — no_agent cron 脚本示例（监控型/静默模式）
正常时无输出，异常时打印消息（投递到微信）。
"""
import json, os, subprocess, time, sys
from datetime import datetime

LOCK = '/tmp/hermes_watchdog.lock'
COOLDOWN = 600  # 重启后冷却期（秒）

def log(msg):
    t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{t}] {msg}')

def get_lock():
    now = time.time()
    if os.path.exists(LOCK):
        try:
            with open(LOCK) as f:
                data = json.load(f)
            if now - data.get('ts', 0) > 1800:
                os.remove(LOCK)
            else:
                return False
        except:
            os.remove(LOCK)
    with open(LOCK, 'w') as f:
        json.dump({'pid': os.getpid(), 'ts': now}, f)
    return True

def release_lock():
    try:
        if os.path.exists(LOCK): os.remove(LOCK)
    except: pass

def pm2_status(name):
    r = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True, timeout=10)
    processes = json.loads(r.stdout)
    for p in processes:
        if p.get('name') == name:
            status = p.get('pm2_env', {}).get('status', '')
            return status == 'online', p.get('pid', '')
    return False, ''

def pm2_restart(name):
    log(f'重启 {name}...')
    subprocess.run(['pm2', 'restart', name], timeout=30, capture_output=True)
    time.sleep(5)
    return pm2_status(name)[0]

def check_cooldown():
    cf = '/tmp/hermes_watchdog_last_restart'
    if os.path.exists(cf):
        with open(cf) as f:
            last = float(f.read().strip())
        if time.time() - last < COOLDOWN:
            return True
    return False

def set_cooldown():
    with open('/tmp/hermes_watchdog_last_restart', 'w') as f:
        f.write(str(time.time()))

def main():
    if not get_lock():
        return

    try:
        services = [
            ('hermes-gateway', 'Gateway'),
            ('hermes-dashboard', 'Dashboard'),
        ]

        any_issue = False
        for proc_name, label in services:
            ok, pid = pm2_status(proc_name)
            if not ok:
                any_issue = True
                log(f'⚠️  {label}({proc_name}) 未运行')

        if not any_issue:
            return  # 一切正常，静默退出

        if check_cooldown():
            log(f'⏳ 冷却期内，跳过自动重启')
            return

        log('🔄 开始自动恢复...')
        for proc_name, label in services:
            ok, pid = pm2_status(proc_name)
            if not ok:
                if pm2_restart(proc_name):
                    log(f'✅ {label} 重启成功')
                else:
                    log(f'❌ {label} 重启失败')

        set_cooldown()

        all_ok = True
        for proc_name, label in services:
            ok, pid = pm2_status(proc_name)
            if not ok:
                all_ok = False
                log(f'❌ {label} 仍未恢复，需要人工介入')

        if all_ok:
            log('✅ 所有服务已恢复')

    finally:
        release_lock()

if __name__ == '__main__':
    main()
