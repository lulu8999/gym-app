#!/usr/bin/env python3
"""安全地写入 API Key 到 .env 文件，避开 Hermes write_file 的 sk-xxx 自动替换 bug。

用法:
    python3 /root/scripts/set_env_key.py KEY_NAME KEY_VALUE
    python3 /root/scripts/set_env_key.py XIAOMI_API_KEY sk-xxxxx
    python3 /root/scripts/set_env_key.py XIAOMI_API_KEY sk-xxxxx --env /path/to/.env

不传 --env 时默认写入 /root/.hermes/.env（Hermes 主配置）
"""

import os
import sys
import re
import shutil
import tempfile

def main():
    if len(sys.argv) < 3:
        print("用法: set_env_key.py KEY_NAME KEY_VALUE [--env PATH]")
        sys.exit(1)

    key_name = sys.argv[1]
    key_value = sys.argv[2]

    # 检测 --env 参数
    env_path = os.path.expanduser("~/.hermes/.env")
    if "--env" in sys.argv:
        idx = sys.argv.index("--env")
        if idx + 1 < len(sys.argv):
            env_path = os.path.expanduser(sys.argv[idx + 1])

    if not os.path.exists(env_path):
        print(f"❌ 文件不存在: {env_path}")
        sys.exit(1)

    # 读取原始文件
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    replaced = False
    new_lines = []

    # 正则：匹配 KEY_NAME=xxx 或 export KEY_NAME=xxx
    pattern = re.compile(r'^(export\s+)?' + re.escape(key_name) + r'=.*')

    for line in lines:
        if pattern.match(line):
            if line.startswith("export "):
                new_lines.append(f"export {key_name}={key_value}")
            else:
                new_lines.append(f"{key_name}={key_value}")
            replaced = True
        else:
            new_lines.append(line)

    # 没找到现有行，追加
    if not replaced:
        new_lines.append(f"{key_name}={key_value}")

    new_content = "\n".join(new_lines) + "\n"

    # 用临时文件 + 移动的方式安全写入（避免 write_file 截断/替换）
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(env_path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_content)
        shutil.copymode(env_path, tmp_path)
        shutil.move(tmp_path, env_path)
    except:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    action = "更新" if replaced else "新增"
    # 验证写入成功
    with open(env_path, "r", encoding="utf-8") as f:
        verify_lines = f.readlines()
    for vl in verify_lines:
        if vl.startswith(key_name + "=") or vl.startswith("export " + key_name + "="):
            val = vl.split("=", 1)[1].strip()
            if val == key_value:
                print(f"✅ {action}成功: {key_name}={val[:8]}...{val[-4:]}")
            else:
                print(f"❌ 值不匹配！期望={key_value[:8]}... 实际={val[:8]}...")
                sys.exit(1)
            break

if __name__ == "__main__":
    main()
