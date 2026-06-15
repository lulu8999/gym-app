# 案例：model.api_key: '' 阻塞 providers 段 api_key_env 读取

**日期：** 2026-06-09  
**用户：** Lulu  
**问题：** 千帆 Coding Plan 配置后报 401 `invalid_iam_token`

---

## 现象

curl 直测千帆 API 正常（200），但 Hermes 网关发请求报 401。  
查 request dump 发现 Authorization header 是 `Bearer no-key-required`。

---

## 配置对比

### 失败时（修前）
```yaml
model:
  api_key: ''                      # 空字符串！
  api_key_env: ''
  base_url: ''
  default: qianfan-code-latest
  provider: qianfan                # 指向 providers 段

providers:
  qianfan:
    api_key_env: QIANFAN_API_KEY   # 配了但没生效
    base_url: https://qianfan.baidubce.com/v2/coding
    provider: custom
```

### 成功时（修后）
```yaml
model:
  api_key: 'bce-v3/ALTAKSP-...'    # 实际 key 值
  api_key_env: ''
  base_url: 'https://qianfan.baidubce.com/v2/coding'
  default: qianfan-code-latest
  provider: custom                 # 改为 custom，不指向 providers
```

---

## 诊断过程

1. **检查 request dump**
   ```bash
   python3 -c "
   import json, glob
   dumps = sorted(glob.glob('/root/.hermes/sessions/request_dump_*.json'))
   with open(dumps[-1]) as f:
       d = json.load(f)
   auth = d['request']['headers'].get('Authorization', 'MISSING')
   print('URL:', d['request']['url'])
   print('Auth:', auth[:60])
   print('Model:', d['request']['body'].get('model', 'N/A'))
   "
   ```
   发现 Auth 是 `Bearer no-key-required`。

2. **检查网关日志**
   ```
   WARNING hermes_cli.config: providers.qianfan: unknown config keys ignored: provider
   ```
   说明 `providers` 段的 `provider` 字段可能被忽略。

3. **检查 model.api_key**
   空字符串 `''` 被 Hermes 认为"已设置"，优先于 `providers` 段的 `api_key_env`。

---

## 解决方案

**策略：把 key 直接写入 model.api_key**

```bash
export KEY=$(grep '^QIANFAN_API_KEY=*** ~/.hermes/.env | cut -d'=' -f2-)
hermes config set model.api_key "$KEY"
hermes config set model.provider custom
hermes config set model.base_url "https://qianfan.baidubce.com/v2/coding"
```

---

## 教训

- `model.api_key: ''` 比不写更糟糕 —— 它会覆盖 `providers` 段的配置
- `providers` 段的 `provider: custom` 可能被忽略
- 最稳妥的方式是把所有关键参数都放在 `model` 段
