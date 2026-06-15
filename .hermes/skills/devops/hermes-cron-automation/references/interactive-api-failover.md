# 交互式 API 故障切换（可执行 Cron 看门狗）

针对 AI Agent 后端 API 不可用时，通过企微发选项让用户选择切换模型，全程不依赖故障 API。

## 模式

```
cron (每 5 分钟)
  └─ watchdog.py ── curl 测当前模型 API ── 通？→ 静默
                                             │ 不通？
                                             ▼
                                       企微告警：
                                        ⚠️ 当前模型 [X] 异常
                                         1. 模型A
                                         2. 模型B
                                             │
                                             ▼
                                       用户在 Hermes 对话回复"选1"
                                        → 执行 apply_choice.sh
                                        → 更新 config.yaml → 下次请求生效
```

## 核心实现

### 1. 健康检测（Python，用 urllib.request，不用 requests）

```python
import urllib.request

def test_api(provider, base_url, api_key):
    url = f"{base_url}/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        resp = urllib.request.urlopen(req, timeout=8)
        return resp.status == 200
    except Exception:
        return False
```

**⚠️ 坑：不要用 `__import__('urllib.request')`**
- `__import__('urllib.request')` 返回的是顶层 `urllib` 模块，不是 `urllib.request`
- `urllib.request.Request` 存在，但 `__import__('urllib.request').Request` 不存在
- 直接用 `import urllib.request` 在文件顶部导入

### 2. 互斥锁（fcntl，比 JSON 锁文件可靠）

```python
import fcntl, os

LOCK_FILE = "/tmp/model_watchdog/watchdog.lock"
os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
try:
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except (IOError, OSError):
    print("SKIP: 另一实例正在运行")
    sys.exit(0)
```

注意：`fcntl.LOCK_EX | fcntl.LOCK_NB` 组合用按位或，不是加法。

### 3. 从 .env 加载密钥

```python
def load_env():
    env = {}
    with open(os.path.expanduser("~/.hermes/.env")) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k and k.isupper():
                env[k] = v
    return env
```

### 4. 读取 Hermes 当前模型配置

```python
def get_config():
    config_path = os.path.expanduser("~/.hermes/config.yaml")
    model = provider = base_url = None
    in_model = False
    with open(config_path) as f:
        for line in f:
            if line.startswith("model:"):
                in_model = True; continue
            if in_model:
                if line.startswith("  default:"):
                    model = line.split(":", 1)[1].strip()
                elif line.startswith("  provider:"):
                    provider = line.split(":", 1)[1].strip()
                elif line.startswith("  base_url:"):
                    base_url = line.split(":", 1)[1].strip()
                elif not line.startswith("  ") or line.startswith("provider"):
                    break
    return {"model": model, "provider": provider, "base_url": base_url}
```

### 5. 防刷屏：30 分钟冷却

```python
ALERT_SENT_FILE = "/tmp/model_watchdog/alert_sent"
if os.path.exists(ALERT_SENT_FILE):
    last_alert = int(open(ALERT_SENT_FILE).read().strip())
    if time.time() - last_alert < 1800:
        print("SKIP: 30分钟内已发过告警")
        sys.exit(0)
open(ALERT_SENT_FILE, "w").write(str(int(time.time())))
```

### 6. 发送企微选择消息

调用 `/root/stock_analyzer/send_wecom.py`：

```python
import subprocess
subprocess.run(["python3", SEND_WECOM, user_id, message], capture_output=True, timeout=10)
```

消息格式：

```
⚠️ 模型异常通知
━━━━━━━━━━━━━━━━━━
当前模型 [deepseek-v4-flash] 检测失败
时间：06-03 19:08

请回复编号选择备用模型：

  1. deepseek-v4-flash
  2. deepseek-v4-pro

（回复对应数字即可）
```

### 7. 状态文件

```json
{
  "failed_model": "deepseek-v4-flash",
  "failed_provider": "deepseek",
  "timestamp": 1780485285,
  "alerted": true,
  "model_count": 2
}
```

文件位置：`/tmp/model_watchdog/status.json`

### 8. 切换脚本（apply_choice.sh）

用 `sed` 修改 `~/.hermes/config.yaml` 的前几行：

```bash
sed -i "s|^  default:.*|  default: $NEW_MODEL|" "$HERMES_CONFIG"
sed -i "s|^  provider:.*|  provider: $NEW_PROVIDER|" "$HERMES_CONFIG"
sed -i "s|^  base_url:.*|  base_url: $NEW_BASE|" "$HERMES_CONFIG"
```

切换后发企微确认消息。

## cron 设置

```bash
*/5 * * * * python3 /root/scripts/model_watchdog.py >> /tmp/model_watchdog/watchdog.log 2>&1
```

## 故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| 脚本检测失败但 API 正常 | `.env` 密钥加载错误 | 改用 `source` 或修复 `load_env` |
| 脚本检测总返回 False | `__import__('urllib.request')` bug | 改成顶部 `import urllib.request` |
| 企微通知重复刷屏 | 冷却文件未写入 | 检查 `/tmp/` 写权限或 cooldown 逻辑 |
| sed 改出了两个 `model:` 块 | config.yaml 有多个匹配行 | 确认 `grep '^model:' config.yaml` 只返回一行 |

## 脚本位置

- 看门狗：`/root/scripts/model_watchdog.py`
- 切换脚本：`/tmp/model_watchdog/apply_choice.sh`（由 watchdog 自动创建）
- 日志：`/tmp/model_watchdog/watchdog.log`
