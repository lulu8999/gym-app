# 回调消息收不到 — 空body/XML解析错误排障

## 症状

企微管理后台回调URL配置显示"已保存"，但在企微App中发送消息后：
- 网关日志报错：`xml.parsers.expat.ExpatError: syntax error: line 1, column 0`
- 数据库中没有收到用户消息（`sqlite3 ~/.hermes/state.db "SELECT ..."` 看不到）
- `/health` 端点正常：`{"status":"ok","platform":"wecom_callback"}`

## 可能原因（按排查顺序）

### 1. 回调URL验证通过了但没有转发消息

企微配置回调URL分两步：
1. **GET验证（URL校验）** — 发送带 `echostr`、`timestamp`、`nonce`、`msg_signature` 的GET请求
2. **POST消息推送** — 后续所有消息走POST

如果GET验证通过了（企微后台显示绿色成功），不等于POST就必然正常工作。

### 2. Token / EncodingAESKey 不匹配

配置中的 `token` 和 `encoding_aes_key` 必须与企微管理后台 **完全一致**。注意：
- Token 不含空格和特殊字符时比较隐性
- EncodingAESKey 是43字符的Base64编码字符串

验证方式：在企微管理后台重新复制 Token 和 EncodingAESKey，然后用 `hermes config set` 重新设置。

### 3. 隧道未转发POST body

Cloudflare Tunnel（cloudflared）可能正确路由了连接但没有正确转发POST body。

尝试：在VPS上监听原始请求：
```bash
# 检查隧道是否正在接收数据
pm2 logs wecom-tunnel --lines 50 --nostream | grep -i "callback\|8645"
```

### 4. 多app配置问题（_apps解析）

`_normalize_apps` 方法（wecom_callback.py:92-107）优先检查 `extra.apps` 列表。如果config.yaml中有 `apps:` 字段但格式不对，可能跳过corp_id/agent_id等字段导致配置不生效。

检查方式：
```bash
grep -A 20 "wecom_callback:" ~/.hermes/config.yaml | grep -E "apps|corp_id|agent_id|token|encoding"
```

确保结构是**扁平extra**（apps列表为空或无），而不是嵌套apps列表。

### 5. 企微IP白名单

企微API调用（获取access_token、发送消息）需要把VPS IP加入白名单。但消息回调是企微主动推送，不依赖IP白名单。

## 已尝试但未解决的问题（记录中，待排查）

- 回调URL已通过企微GET验证 ✅
- 本地 `/health` 和公网 `callback.lulugame.fun/health` 均正常 ✅
- DNS解析正确（Cloudflare IP: 104.21.33.165 / 172.67.147.96） ✅
- aiohttp/httpx/defusedxml 包已安装 ✅
- 端口8645无冲突 ✅
- 网关日志显示收到POST请求但body为空 → **根因待定**

## 攻击性排查（如果常规方法无效）

```bash
# 1. 查看原始HTTP请求日志
pm2 logs hermes-gateway --lines 200 --nostream | grep -B5 -A5 "wecom_callback"

# 2. 在回调链路上添加调试日志
# 在 _handle_callback 中加 print(f"RAW BODY: {body[:500]}")

# 3. 用 nc 监听原始请求（临时方案）
# 停止wecom_callback服务器，在8645端口用nc监听
# 然后在企微发消息，看nc收到什么原始数据

# 4. 检查云平台防火墙/SELinux
sestatus 2>/dev/null
iptables -L -n 2>/dev/null | grep 8645
```
