# 微信配置 API 失败诊断指南

> 用户反复反馈"微信上配置 API 总是出错"——三个根因，按出现频率排列。

## 症状

用户在微信/企微上配置 API 后，聊天消息发不出去、一直「输入中」、或者报 401 错误。

## 根因速查表

| # | 根因 | 日志特征 | 修复 |
|---|------|---------|------|
| 1 | **`model.provider` 配错**（配成了不存在的 provider 名） | 网关日志出现 provider 报错，每条消息等一次失败再 fallback | 改为真实 provider 名（如 `xiaomi-mimo`） |
| 2 | **`api_key_env` 间接引用**（Gateway 不加载 .env） | `/model` 显示 `unknown provider`，请求头 `no-key-required` | 删掉 `api_key_env`，直接写 `api_key` 值 |
| 3 | **残留旧 key**（改了但没删干净） | 401，但新 key 明明写进去了 | `grep api_key` 全文件，确认只有一处新 key |

## 详细排查流程

### 第一步：查网关日志

```bash
tail -20 /root/.hermes/logs/gateway.log | grep -i "provider\|401\|error\|fail"
```

| 看到什么 | 判断 |
|---------|------|
| `unknown config keys ignored: provider` | `provider: custom` 在 providers 段 → 改为 `provider: openai` |
| `Provider xxx not found` / `not in provider list` | `model.provider` 名字不对 |
| `401 Unauthorized` | Key 没读到或 key 截断了 |

### 第二步：查当前 model 配置

```bash
python3 -c "
import yaml
with open('/root/.hermes/config.yaml') as f:
    c = yaml.safe_load(f)
m = c.get('model', {})
print('model.name:', m.get('name', '?'))
print('model.provider:', m.get('provider', '?'))
print('model.api_key:', '***' + str(m.get('api_key', 'none'))[-6:] if m.get('api_key') else 'NONE')
print()
print('providers:', list(c.get('providers', {}).keys()))
"
```

### 第三步：查 key 截断

```bash
python3 -c "
import re
with open('/root/.hermes/config.yaml') as f:
    content = f.read()
for m in re.finditer(r'api_key:\s*(\S+)', content):
    key = m.group(1)
    if '...' in key or len(key) < 20:
        print(f'❌ 截断: {key} (len={len(key)})')
    else:
        print(f'✅ OK: {key[:15]}... (len={len(key)})')
"
```

### 第四步：查 `.env` 是否还有旧 key

```bash
grep -E "^[A-Z_]+=" ~/.hermes/.env | grep -v "^#"
```

如果 `config.yaml` 里用了 `api_key_env`，Gateway 根本读不到 `.env` 的值。

## 为什么微信上特别容易出错

| 原因 | 说明 |
|------|------|
| 看不到原始配置 | 微信消息里只能看到格式化的文本，没法直接 cat config.yaml 确认 |
| 命令被截断 | 微信可能吃掉换行、缩进、特殊字符，配置粘贴进去就变形了 |
| 反馈延迟 | 配置错了要等消息卡住才知道，不象 CLI 能直接 curl 测试 |
| 模型名混淆 | `model` 段 vs `providers` 段 vs `model.name` 容易搞混 |

## 标准修复流程（微信场景）

当用户说"微信上配 API 又出错了"：

1. 先查网关日志确认具体报错
2. 列当前配置给用户看
3. 三个根因逐一排除（provider 名 → api_key_env → 残留 key）
4. 修复后重启网关
5. 让用户发条消息测试

## 避免再次出错

- 所有 API Key **直接写** `api_key` 字段，不用 `api_key_env`
- `provider` 统一用 `openai`，不用 `custom`
- 改完 key 后 grep 全文件确认无残留
- 配完立刻重启网关测试