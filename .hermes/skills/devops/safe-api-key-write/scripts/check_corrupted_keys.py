#!/usr/bin/env python3
"""检查 .env 文件中 API Key 是否被 write_file 的 sk-xxx bug 损坏为 ***。

用法: python3 /root/.hermes/skills/devops/safe-api-key-write/scripts/check_corrupted_keys.py
"""

import os
import re
import sys

def check_env_file(path):
    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        return []

    corrupted = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # 匹配 KEY=VALUE 格式（不含 export 前缀）
            m = re.match(r'^(export\s+)?([A-Z_]+)=(.*)', line)
            if m:
                key_name = m.group(2)
                key_value = m.group(3).strip().strip('"').strip("'")
                # 检测是否包含 API Key 相关关键词
                if any(kw in key_name for kw in ['API_KEY', 'TOKEN', 'SECRET', 'PASSWORD']):
                    if key_value == '***' or len(key_value) < 5:
                        corrupted.append((i, key_name, key_value))
    return corrupted

def main():
    env_path = os.path.expanduser('~/.hermes/.env')
    if len(sys.argv) > 1:
        env_path = sys.argv[1]

    print(f"检查: {env_path}")
    corrupted = check_env_file(env_path)

    if corrupted:
        print(f"\n❌ 发现 {len(corrupted)} 个损坏的 Key:")
        for line_no, name, value in corrupted:
            print(f"  第 {line_no} 行: {name}={value}")
        print("\n修复方法:")
        print(f"  python3 /root/scripts/set_env_key.py <KEY_NAME> <真实KEY值>")
        sys.exit(1)
    else:
        print("✅ 所有 Key 正常，未发现损坏。")
        sys.exit(0)

if __name__ == "__main__":
    main()
