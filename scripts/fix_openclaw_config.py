#!/usr/bin/env python3
import json
import sys

config_path = '/root/.openclaw/openclaw.json'
backup_path = '/root/.openclaw/openclaw.json.backup'

with open(config_path, 'r') as f:
    config = json.load(f)

# 删除旧的wecom插件条目
if 'plugins' in config and 'entries' in config['plugins']:
    if 'wecom' in config['plugins']['entries']:
        del config['plugins']['entries']['wecom']
        print("Removed old 'wecom' plugin entry")
    # 确保新的wecom-openclaw-plugin存在
    if 'wecom-openclaw-plugin' not in config['plugins']['entries']:
        config['plugins']['entries']['wecom-openclaw-plugin'] = {'enabled': True}
        print("Added 'wecom-openclaw-plugin' entry")

# 同样删除channels中的wecom条目，如果插件未安装
if 'channels' in config and 'wecom' in config['channels']:
    # 暂时保留，因为可能还需要配置
    pass

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"Config updated: {config_path}")