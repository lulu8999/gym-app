---
name: expose-hermes-dashboard
description: 通过域名+反向代理（Caddy/Nginx）将 Hermes Agent Dashboard 暴露到公网，配合 Cloudflare 代理
category: devops
trigger: 用户想通过浏览器（电脑/手机）直接访问 Hermes Agent 的 Web 界面
---

# Expose Hermes Dashboard via Reverse Proxy + Cloudflare

将 Hermes Dashboard（端口 9119）通过域名暴露到公网，让用户在浏览器中直接访问。

## 架构

```
浏览器 → Cloudflare（Proxy）→ 服务器（Caddy/Nginx）→ Hermes Dashboard（:9119）
```

## Caddy 配置

### 关键坑：Cloudflare Flexible SSL + Caddy 自动 HTTPS 跳转

- Caddy 默认行为：站点块 `lulugame.fun { ... }` 会在 80 端口返回 **308 永久重定向**到 HTTPS
- Cloudflare 在 **Flexible** SSL 模式下，通过 HTTP（80 端口）连接源服务器
- 两者冲突：Caddy 返回 308 → Cloudflare 处理异常 → 用户看到奇怪的内容

### 正确配置：显式指定 80 端口

```caddy
lulugame.fun:80 {
	reverse_proxy 127.0.0.1:9119
}
```

这样 Caddy 只在 80 端口提供服务，不做 HTTPS 跳转。

### Caddy 相关命令

```bash
# 查看 Caddyfile
cat /etc/caddy/Caddyfile

# 重载配置
sudo caddy reload --config /etc/caddy/Caddyfile

# 重启
sudo systemctl restart caddy

# 查看日志
journalctl -u caddy --no-pager -n 50

# 验证监听端口
ss -tlnp | grep caddy
```

## Hermes Dashboard 启动

```bash
# Dashboard 通常在端口 9119 运行
hermes dashboard --port 9119 --host 0.0.0.0
```

确认运行：
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:9119/
# 应返回 200
```

## Cloudflare 排查

如果域名访问返回的不是 Dashboard 内容，排查方向：

1. **Cloudflare Workers/Pages** — 可能部署了 Worker 代码在边缘层拦截请求
2. **Cloudflare 页面规则** — 可能有转发规则
3. **SSL/TLS 模式** — Flexible / Full / Strict 影响源服务器连接方式
4. **Cloudflare Tunnel（cloudflared）** — 隧道连接绕过 Caddy/Nginx，直接将域名路由到本地端口

### Cloudflare Tunnel 排查步骤

```bash
# 检查 cloudflared 是否在运行
ps aux | grep cloudflared | grep -v grep

# 查看隧道入口规则（关键文件）
cat /root/.cloudflared/config.yml
# 示例输出：
# tunnel: wecom
# ingress:
#   - hostname: lulugame.fun
#     service: http://localhost:9800    # ← 检查这个端口！
#   - hostname: sub.lulugame.fun
#     service: http://localhost:18888
#   - service: http_status:404

# 查看 cloudflared 监听的本地端口
ss -tlnp | grep cloudflared
```

**关键发现：** 隧道入口规则的优先级高于 Caddy/Nginx。如果域名在隧道配置里指向了其他端口，改 Caddy 是没用的——隧道把请求截走了。

**修复方法：** 编辑 `/root/.cloudflared/config.yml`，把对应域名的 `service` 改成 Dashboard 端口：

```yaml
ingress:
  - hostname: lulugame.fun
    service: http://localhost:9119    # ← Hermes Dashboard
```

然后重启 cloudflared：
```bash
sudo systemctl restart cloudflared
```

**另外检查 DNS 记录：** 在 Cloudflare 仪表板里，域名的 A 记录可能是指向 Tunnel CNAME（如 `lulugame.fun.cdn.cloudflare.net`）而不是服务器真实 IP，这同样说明隧道在使用中。

查看位置：Cloudflare 控制面板 → 域名 → 左侧菜单

## 验证

```bash
# 服务器本地验证
curl -s http://localhost:9119/ | head -5
# 应返回 <title>Hermes Agent - Dashboard</title>

# 模拟 Cloudflare 访问（通过 Caddy 80 端口）
curl -s -H "Host: lulugame.fun" http://localhost:80/ | head -5

# 通过公网访问
curl -s https://lulugame.fun/ | head -5
```

## 注意事项

- 旧的 Caddyfile 更改后必须重载/重启 Caddy 才能生效
- Caddyfile 是系统文件（`/etc/caddy/`），需要 sudo 权限
- Cloudflare 的缓存可能导致旧内容残留，添加 `Cache-Control: no-cache` 请求头可绕过
- 如果 Dashboard 需要认证，可在 Caddy 层配置 basic auth（参考 `.htpasswd` 文件）
