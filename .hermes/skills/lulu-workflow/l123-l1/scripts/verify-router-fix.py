#!/usr/bin/env python3
"""Verify the conceptual QA fix in router.py"""
import sys
sys.path.insert(0, '/root/l123')
from agent.router import router

tests = [
    # Should be simple (conceptual QA)
    ('高端款能否模拟双向芯片认证信号', 'simple', '概念性QA'),
    ('高端锁物理方案怎么搞', 'simple', '概念性QA'),
    ('能不能把模型切换一下', 'simple', '概念性QA'),
    ('为什么高端锁不能逆向', 'simple', '概念性QA'),
    # Should remain complex (genuine multi-step)
    ('查天气并写报告', 'complex', '真正多步'),
    ('爬数据然后存数据库', 'complex', '真正多步'),
    # Should dispatch normally
    ('写个Python脚本', 'single_dispatch', '编码任务'),
    ('部署个网站', 'single_dispatch', '部署任务'),
]

all_ok = True
for msg, expected_type, reason in tests:
    r = router.route(msg)
    actual = r['type']
    ok = actual == expected_type or (expected_type == 'simple' and actual == 'simple')
    if not ok:
        # simple/creative both count
        ok = expected_type == 'simple' and actual in ('simple',)
    status = '✅' if ok else '❌'
    if not ok:
        all_ok = False
    print(f'{status} [{actual:>15}] \"{msg}\" (期望: {expected_type}, {reason})')

print(f'\n{"全部通过!" if all_ok else "有失败!"}')
sys.exit(0 if all_ok else 1)
