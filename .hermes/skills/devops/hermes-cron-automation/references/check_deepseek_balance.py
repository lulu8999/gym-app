#!/usr/bin/env python3
"""DeepSeek 余额检查 — no_agent cron 脚本示例（报告型）
输出直接投递到用户微信。
"""
import json, os, sys
from urllib.request import Request, urlopen

# 从 .env 加载 API Key
env_path = '/root/.hermes/.env'
api_key = ''
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith('DEEPSEEK_API_KEY=***                api_key = line.strip().split('=', 1)[1]
                break

if not api_key:
    print("⚠️ 无法获取 DeepSeek API Key")
    sys.exit(1)

try:
    req = Request(
        'https://api.deepseek.com/user/balance',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    )
    with urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    infos = data.get('balance_infos', [])
    if not infos:
        print("⚠️ 未能获取余额信息")
        sys.exit(1)

    for info in infos:
        currency = info.get('currency', '?')
        total = float(info.get('total_balance', 0))
        granted = float(info.get('granted_balance', 0))
        topped_up = float(info.get('topped_up_balance', 0))
        symbol = '¥' if currency == 'CNY' else '$'

        print(f"💰 DeepSeek 余额日报")
        print(f"━━━━━━━━━━━━━━━━━")
        print(f"总余额：{symbol}{total:.2f}")
        if topped_up > 0:
            print(f"充值余额：{symbol}{topped_up:.2f}")
        if granted > 0:
            print(f"赠送余额：{symbol}{granted:.2f}")

        if total < 1.0:
            print(f"\n⚠️  余额不足 ¥1，建议及时充值！")
        elif total < 5.0:
            print(f"\n📌 余额偏低，注意关注用量")

except Exception as e:
    print(f"❌ 查询余额失败：{e}")
    sys.exit(1)
