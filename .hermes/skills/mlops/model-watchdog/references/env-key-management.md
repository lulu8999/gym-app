# .env API Key 管理技巧

## write_file 会掩码 sk-xxx 格式的 Key

Hermes 的 `write_file` 工具会自动将 `sk-xxx` 格式的 API Key 替换为 `***`，导致写出的 key 无效。

**不要用 write_file 更新 .env 的 API Key。**

正确的做法：

```python
# Python 方式（推荐）
import os
env_path = os.path.expanduser('~/.hermes/.env')
with open(env_path) as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if line.startswith('XIAOMI_API_KEY='):
        lines[i] = f'XIAOMI_API_KEY={new_key}\n'
        break
with open(env_path, 'w') as f:
    f.writelines(lines)
```

```bash
# sed 方式
sed -i 's|^XIAOMI_API_KEY=.*|XIAOMI_API_KEY='"$NEW_KEY"'|' ~/.hermes/.env
```

## 验证 Key 写入成功

写入后用 Python 测试 API 是否接受新的 Key：

```python
import urllib.request, json
req = urllib.request.Request('https://api.xiaomimimo.com/v1/models')
req.add_header('Authorization', f'Bearer {key}')
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read())
models = [m['id'] for m in data['data']]
print(f'OK - {len(models)} models available')
```

## self_heal 备份可能覆盖新的 Key

`hermes_self_heal.py` 的 `BACKUP_PATHS` 包含 `.env`。如果执行 `restore`：

```
python3 hermes_self_heal.py restore
```

它会从最新备份（tar.gz）中解压 `.env` 覆盖当前文件，**旧 Key 会覆盖新写入的 Key**。

**预防措施：**
- 每次更新 Key 后手动重新备份：`python3 hermes_self_heal.py backup`
- 删除旧的含过期 Key 的备份：`rm ~/.hermes/backups/hermes_backup_*.tar.gz`
- 或者不要在 BACKUP_PATHS 中包括 .env（如非必要）
