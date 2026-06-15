---
name: proxy-setup
description: 在Linux/Mac上安装和配置mihomo代理客户端，支持VLESS+Reality、Clash订阅转换。涵盖中国大陆VPS环境下的安装技巧和常见坑。
category: devops
tags: [proxy, mihomo, vless, reality, network]
---

# 代理客户端配置（mihomo）

## 适用场景
- VPS/Mac在大陆，需要访问外网（GitHub、Google等）
- 用户提供订阅链接或VLESS节点信息
- 需要HTTP/SOCKS5代理给终端/浏览器/Hermes用

## 安装流程

### 1. 下载mihomo（大陆VPS）

GitHub被墙，不能直接下载。用镜像站：

```bash
# 方式一：ghfast.top 代理（推荐）
curl -L -o mihomo.gz "https://ghfast.top/https://github.com/MetaCubeX/mihomo/releases/download/v1.19.8/mihomo-linux-amd64-v1.19.8.gz"

# 方式二：其他镜像
curl -L -o mihomo.gz "https://mirror.ghproxy.com/https://github.com/MetaCubeX/mihomo/releases/download/v1.19.8/mihomo-linux-amd64-v1.19.8.gz"
```

### 2. 安装
```bash
gunzip -f mihomo.gz && chmod +x mihomo && mv mihomo /usr/local/bin/
mihomo -v  # 验证
```

### 3. 下载GeoIP数据库（同样需要代理）

mihomo启动时会自动下载，但大陆VPS可能失败。手动下载：

```bash
curl -L -o /root/.config/mihomo/country.mmdb \
  "https://ghfast.top/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/country.mmdb"
```

## 配置文件模板

见 `templates/mihomo-config.yaml`

## ⚠️ 常见坑

### DNS解析失败
**症状**：日志报 `dns resolve failed: couldn't find ip`，代理返回502
**原因**：mihomo默认DNS用了Google（8.8.8.8），大陆访问不稳定
**修复**：nameserver用国内DNS，fallback用国外DNS
```yaml
dns:
  nameserver:
    - 223.5.5.5      # 阿里DNS
    - 119.29.29.29   # 腾讯DNS
    - 114.114.114.114 # 电信DNS
  fallback:
    - 8.8.8.8
    - 1.1.1.1
```

### GeoIP数据库下载失败
**症状**：日志报 `MMDB invalid, remove and download`，端口不启动
**修复**：手动下载country.mmdb（见上方）

### 订阅链接格式
- 传统机场：返回Clash YAML配置（直接导入）
- VLESS节点：返回base64编码的vless://链接（需要转换成mihomo YAML）
- 解码方法：`curl -s "订阅URL" | base64 -d`

### 端口不监听
**检查顺序**：
1. `ps aux | grep mihomo` — 进程在吗？
2. `ss -tlnp | grep 7890` — 端口起了吗？
3. `tail -20 /tmp/mihomo.log` — 日志有啥错？

### 节点切换与健康检查

**动态切换节点**（两种方式）：

方式一：API切换（针对已存在的代理组）
```bash
# 查询当前代理状态
curl -s http://127.0.0.1:9090/proxies | python3 -c "
import sys,json
d = json.load(sys.stdin)
proxies = d.get('proxies', {})
for k,v in proxies.items():
    if v.get('type') in ['Selector', 'URLTest']:
        print(f'{k}: now={v.get(\"now\",\"?\")}')"

# 切换代理组指向的节点（通过修改配置并重载）
curl -s http://127.0.0.1:9090/configs -X PUT -H "Content-Type: application/json" -d '{}'
```

方式二：直接修改配置（推荐）
```bash
# 1. 编辑 config.yaml 中的 proxy-groups
# 2. 设置 default: 节点名 强制使用指定节点
# 3. 调用 API 重载配置
curl -s http://127.0.0.1:9090/configs -X PUT -H "Content-Type: application/json" -d '{}'
```

**检查节点健康状态**：
```bash
curl -s http://127.0.0.1:9090/proxies | python3 -c "
import sys,json
d = json.load(sys.stdin)
proxies = d.get('proxies', {})
for name in ['首尔-标准套餐·01', '首尔-标准套餐·02']:
    p = proxies.get(name, {})
    print(f'{name}: alive={p.get(\"alive\")}')"
```

⚠️ **重要坑点**：
1. **代理组引用问题**：在 proxy-groups 里写 `🇰🇷 首尔` 会引用另一个组，而不是具体节点。如果该组默认指向的节点已死（alive=False），代理会失败。
2. **节点可能宕机**：同一个地区的多个节点（如首尔-01/02/03）不一定全活着，切节点前必须先查 `alive` 状态。
3. **API路径问题**：mihomo API 对 emoji/中文URL支持不稳定，用 config 修改+重载更可靠。

## 使用方式

### 终端走代理
```bash
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
```

### curl走代理
```bash
curl -x http://127.0.0.1:7890 https://github.com
```

### Hermes .env配置
```
HTTPS_PROXY=http://127.0.0.1:7890
HTTP_PROXY=http://127.0.0.1:7890
```

### 测试连通性
```bash
# 测试外网
curl -x http://127.0.0.1:7890 -s --max-time 10 "http://ipinfo.io/ip"

# 测试国内直连
curl -x http://127.0.0.1:7890 -s --max-time 10 "http://baidu.com"
```

## 后台运行

### 推荐：systemd 服务（独立于 hermes-gateway）

**不要用 nohup 或作为网关子进程运行** — 网关重启时会把 mihomo 一起杀掉。

```bash
# 创建 systemd 服务
cat > /etc/systemd/system/mihomo.service << 'EOF'
[Unit]
Description=mihomo proxy
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/mihomo -d /root/.config/mihomo
Restart=always
RestartSec=3
KillMode=process
KillSignal=SIGTERM
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动 + 开机自启
systemctl daemon-reload
systemctl enable mihomo
systemctl start mihomo

# 查看状态
systemctl status mihomo
```

**关键：** mihomo 必须作为独立 systemd 服务运行（`/system.slice/mihomo.service`），与 hermes-gateway 完全隔离。之前用 nohup 启动时，重启网关会连带杀掉 mihomo（因为它们在同一进程组）。

### 不推荐：nohup（会被网关重启误杀）

```bash
# 前台测试
mihomo -d /root/.config/mihomo

# 后台运行（不推荐，网关重启会杀掉）
nohup mihomo -d /root/.config/mihomo > /tmp/mihomo.log 2>&1 &

# 停止
pkill mihomo
# 或
systemctl stop mihomo
```
