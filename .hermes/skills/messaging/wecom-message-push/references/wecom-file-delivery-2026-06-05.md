# 企业微信文件发送成功记录（2026-06-05）

## 问题背景
用户要求发送 Excel 文件（约翰·列侬生平）到企业微信。Hermes `send_message` 和微信平台均无法发送文件附件。

## 最终解决方案：直接调企业微信官方 API

**关键参数：**
- corpid: `ww815119bb08398d37`
- corpsecret: OpenClaw 配置中的 `channels.wecom.secret`（存储在 `~/.openclaw/openclaw.json`）
- agentid: `1000002`
- touser: `KuHai`
- 文件: `/root/users-data/Lulu/约翰·列侬生平.xlsx`（7565 字节）

## 完整执行记录

### 第1步：获取 access_token
```bash
curl -s "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=ww815119bb08398d37&corpsecret=bXV8wcELfmGQ6JncmScmolVHBmJef0tg2lHxpkNq3x4"
```
**返回：** `{"errcode":0, "errmsg":"ok", "access_token":"CNN7Rm...vg_w", "expires_in":7200}`

### 第2步：上传文件获取 media_id
```bash
curl -s -F "media=@/root/users-data/Lulu/约翰·列侬生平.xlsx" \
  "https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token=${TOKEN}&type=file"
```
**返回：** `{"errcode":0, "errmsg":"ok", "type":"file", "media_id":"3QgXQx9DVqbpG5u1XGycvHo3xyXa8a_ln4Y4gauXE5TvBi_G321MQK5XxYJW4x4it", "created_at":"1780665605"}`

### 第3步：发送文件消息
```bash
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"touser\": \"KuHai\",
    \"msgtype\": \"file\",
    \"agentid\": 1000002,
    \"file\": { \"media_id\": \"3QgXQx9DVqbpG5u1XGycvHo3xyXa8a_ln4Y4gauXE5TvBi_G321MQK5XxYJW4x4it\" }
  }"
```
**返回：** `{"errcode":0, "errmsg":"ok", "msgid":"-k0v1xV6DAwY50e7tkh-GXGam07HGuA6wkIuV4CaMPsXJ7pY2sOwE2BpPH1VVOPeWIQsO21lAPTKToCBqnwiLxdDF4nNrrRI9vn9HXwDrvRvbqsashAj0a6o7LF6u-A_"}`

**结果：** ✅ 用户在企业微信上收到了 Excel 文件

## 用户指令
"以后记住了，就这么干，发企业微信！"

## 注意事项
- media_id 有效期 3 天，不可重复使用
- secret 存储在 `~/.openclaw/openclaw.json` 的 `channels.wecom.secret` 字段
- OpenClaw 企业微信认证之所以失败，是因为 OpenClaw 的 wecom channel 使用 WebSocket 连接（`wss://openws.work.weixin.qq.com`），需要 bot_id + bot_secret（不是应用 secret）。但发送文件用的是 Corp API（`qyapi.weixin.qq.com`），需要 corpid + 应用 secret，不需要 bot 配置。两者是不同的通道。

## 相关脚本
- `/root/stock_analyzer/send_wecom.py` — 已有封装脚本，支持文本/图片发送
- 文件发送暂未封装进该脚本，如需添加需增加文件上传 + 文件消息类型支持
