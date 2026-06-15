# MiMo api_key_env 失败案例（2026-06-13）

## 问题

`providers.xiaomi-mimo` 配置了 `api_key_env: XIAOMI_API_KEY`，但 Gateway 进程不加载 `.env` 到环境变量，导致：

1. provider 初始化失败
2. `/model` 显示 `unknown provider`
3. 所有请求 401

## 原始配置（有问题）

```yaml
providers:
  xiaomi-mimo:
    api_key_env: XIAOMI_API_KEY      # ← Gateway 不加载 .env
    base_url: https://api.xiaomimimo.com/v1
    default_model: mimo-v2.5-pro
    provider: openai
    key_env: XIAOMI_API_KEY           # ← 同样无效
```

## 修复后配置

```yaml
providers:
  xiaomi-mimo:
    api_key: sk-cpy...lfby            # ← 直接写入完整 key
    base_url: https://api.xiaomimimo.com/v1
    default_model: mimo-v2.5-pro
    provider: openai
```

## 额外发现：Key 截断显示陷阱

从 `.env` 提取 key 时，终端 `grep` / `echo` 可能截断显示：
```
$ grep XIAOMI_API_KEY .env
XIAOMI_API_KEY=sk-cpy...lfby        # 字面显示 13 字符
```

但实际值是 51 位：`sk-cpysbts6ho2iik3bflbuxoxgu5ugkvgp94w3vww4br0lfby`

**正确做法**：用 Python 逐字符提取并验证长度：
```python
with open('.env') as f:
    for line in f:
        if 'XIAOMI_API_KEY=*** in line and not line.startswith('#'):
            key = line.split('=', 1)[1]
            print(f'长度: {len(key)}')  # 应该是 51，不是 13
```
