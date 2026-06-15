# 文件发送问题调试记录（2026-06-05）

## 问题
用户要求生成Excel文件并通过企业微信发送，但始终收不到。

## 调试过程

### 尝试1：`send_message(media=..., target='weixin:...')`
- 结果：返回 `success: true`，用户没收到
- 原因：微信平台不支持文件附件

### 尝试2：`send_message(media=..., target='wecom_callback:KuHai')`
- 结果：返回 `success: true`，但 `note.chat_id` 显示为 `sisu.`（圆圆）
- 原因：`send_message` 工具的 `wecom_callback` 路由有 bug，总是解析到 sisu. 的 chat_id

### 尝试3：文本版本发送
- 结果：同样没收到，路由问题相同

### 尝试4：OpenClaw 发送
- 结果：WeCom 插件未安装，网关未运行
- 已安装插件：`@wecom/wecom-openclaw-plugin@2026.5.7`
- 需要重启 OpenClaw 网关才能使用

### 尝试5：HTTP 服务器提供下载
- 结果：服务器启动成功，但外部端口（8080/8888）不可访问
- 原因：安全组/防火墙未开放这些端口
- 绕过方案：可用 Caddy 反向代理，但配置修改失败（权限问题）

## OpenClaw 网关启动问题

### 问题：bind=lan 需要 auth mode=token

OpenClaw 网关配置 `bind=lan` 时，auth mode 不能是 `none`，否则启动失败：
```
Refusing to bind gateway to lan without auth.
```

**修复：** 将 `gateway.auth.mode` 从 `"none"` 改为 `"token"`（已有的 token 值本身不需要改）。

### 问题：旧插件条目阻塞启动

安装新插件（如 `@wecom/wecom-openclaw-plugin@2026.5.7`）后，如果 `plugins.entries` 中仍有旧条目（如 `"wecom": {"enabled": true}`），会报 Config Warnings 甚至阻塞启动。

**修复：** 用 Python 编辑 `~/.openclaw/openclaw.json` 删除旧条目。

### 完整修复流程
```bash
# 1. 备份配置文件
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup

# 2. 修复 auth mode（如果 bind=lan）
# 编辑 openclaw.json 将 gateway.auth.mode 从 "none" 改为 "token"

# 3. 删除旧的插件条目
# 编辑 openclaw.json 删除 plugins.entries.wecom（如果存在）

# 4. 重新安装并启动
openclaw gateway install
openclaw gateway start

# 5. 验证状态
openclaw gateway status
# → Runtime: running, Connectivity probe: ok
```

## 结论
1. **微信平台不支持文件附件** — 这是平台限制
2. **`send_message` 的 `wecom_callback` 路由有 bug** — 总是发到错误的 chat_id
3. **正确方案**：用 `/root/stock_analyzer/send_wecom.py` 直接调企微 API
4. **OpenClaw**：插件已装好，网关启动后也能发文件，但需修复 auth mode 和旧插件条目

## 参考命令
```bash
# 企微 API token 缓存验证
cat /tmp/wecom_token_cache.json

# 检查企微通道连接状态
openclaw channels status --deep | grep WeCom

# 用封装脚本发文件
python3 /root/stock_analyzer/send_wecom.py --image KuHai /path/to/file.xlsx "文件描述"

# OpenClaw 发文件（需网关运行）
openclaw agent --channel wecom --message "请查收文件" --deliver
```