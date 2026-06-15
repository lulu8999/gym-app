# Cloudflare Tunnel 暴露新应用流程

## 背景

在 VPS 上开发了新应用（如 Flask app 在 localhost:5000），需要让用户通过公网域名访问。VPS 已有 `cloudflared` systemd 服务在运行。

## 标准流程

### 步骤 1：确认 cloudflared 管理方式

```bash
systemctl status cloudflared  # 如果是 systemd 管理
pm2 list | grep cloudflared   # 如果是 PM2 管理
```

**教训**：直接 `kill` 进程会被 systemd `Restart=always` 自动拉起来，浪费精力。正确做法是用 `systemctl restart`。

### 步骤 2：修改隧道 ingress 配置

编辑 `/root/.cloudflared/config.yml`，新增域名映射：

```yaml
  - hostname: gym.lulugame.fun
    service: http://localhost:5000
```

### 步骤 3：添加 DNS CNAME 记录（⚠️ 关键步骤）

**如果 Cloudflare zone 没有通配符 DNS，必须手动添加 CNAME 记录！**

测试是否有通配符：
```bash
curl -s -o /dev/null -w "%{http_code}" https://random-test.lulugame.fun
# 000 → 无通配符，需手动加 DNS
```

**需要用户操作**：登录 Cloudflare → `lulugame.fun` → DNS → 添加：
| 类型 | 名称 | 目标 |
|---|---|---|
| CNAME | `gym` | 隧道域名（如 `wecom.cfargotunnel.com`） |

**无法自动化的原因**：Cloudflare API 需要 zone API Token，VPS 上没有。

### 步骤 4：重启 cloudflared（加载新 ingress）

```bash
systemctl restart cloudflared
```

### 步骤 5：验证

```bash
curl -s -o /dev/null -w "%{http_code}" https://gym.lulugame.fun
# 200 → 成功
# 000 → DNS 未生效，等几秒重试
```

## 失败尝试记录

### Quick Tunnel（不可靠）
```bash
cloudflared tunnel --url http://localhost:5000
```
**问题**：2026-06-12 测试时停留在 health check，从未输出 `trycloudflare.com` URL。不可靠，不推荐。

### Nginx 反向代理（复杂且有冲突）
- 装 nginx → 端口 80 被 Caddy 占用
- 改 nginx 用 9080 → 仍需 DNS
- 总体比直接加 DNS 记录更复杂

### Caddy 扩展（不适用）
- Caddy 只代理 `lulugame.fun:80 → localhost:9119`
- 新域名需要 DNS + Caddy config，本质没简化

## 结论

**最快路径**：加 CNAME 记录到 Cloudflare DNS → 改 cloudflared ingress → `systemctl restart cloudflared`。Nginx/Caddy 等反向代理方案只会增加复杂度，不推荐用于简单场景。

## 本次实例（2026-06-12）

- 应用：健身追踪器 Flask app，`localhost:5000`
- 域名：`gym.lulugame.fun`
- 状态：ingress 已配，等待 DNS CNAME 记录
