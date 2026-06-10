#!/usr/bin/env python3
import json
import sys

config_path = '/root/.openclaw/openclaw.json'

with open(config_path, 'r') as f:
    config = json.load(f)

# 修改认证模式为token
if 'gateway' in config and 'auth' in config['gateway']:
    config['gateway']['auth']['mode'] = 'token'
    print("Changed auth mode to 'token'")

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"Config updated: {config_path}")