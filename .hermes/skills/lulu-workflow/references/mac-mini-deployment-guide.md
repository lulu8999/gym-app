# Mac Mini M4 Hermes 部署指南

本文档记录 Mac Mini M4 作为 Hermes 服务器部署的完整流程，包括无 IPv4 环境下的远程连接、SSH 配置排错、以及 Cloudflare DNS 管理。

## 网络架构

```
[Internet] → [Cloudflare Tunnel] → [Tailscale 虚拟网] → [Mac Mini]
                ↓
         [VPS 当前主力]
```

## 一、初始远程连接（无 IPv4 场景）

### 1.1 安装 Tailscale

Mac 终端执行：
```bash
# 命令行安装
brew install tailscale
sudo tailscaled install
sudo tailscale up

# 或者直接从 App Store 搜索 "Tailscale" 安装
```

获取 Tailscale IP：
```bash
tailscale ip -4
# 输出示例：100.114.207.6
```

### 1.2 VPS 连接 Mac

VPS 也需要安装 Tailscale 并加入同一网络：
```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
```

## 二、SSH 配置与排错

### 2.1 开启 SSH 服务

Mac 终端：
```bash
# 方法1：命令行（需要完全磁盘访问权限）
sudo systemsetup -setremotelogin on

# 方法2：图形界面
# 系统设置 → 通用 → 共享 → 打开"远程登录"
```

**授权步骤：**
1. 系统设置 → 隐私与安全性 → 完全磁盘访问权限
2. 点 + 号，添加"终端"(Terminal) App
3. 打开开关，重新打开终端

### 2.2 密钥登录配置（推荐）

Mac 终端执行：
```bash
# 创建 .ssh 目录
mkdir -p ~/.ssh && chmod 700 ~/.ssh

# 添加 VPS 的 SSH 公钥
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDIhz2GK/XCUj4i6Q5yQJNL1MW1l0bYQkIYG7g4VSc1t root@HermesGateway" >> ~/.ssh/authorized_keys

# 设置权限（关键！）
chmod 600 ~/.ssh/authorized_keys
chmod 755 ~
```

**权限检查清单：**
| 路径 | 权限 | 作用 |
|--------|-------|-------|
| `~` | 755 | 主目录可扫描 |
| `~/.ssh` | 700 | 仅所有者可访问 |
| `~/.ssh/authorized_keys` | 600 | 仅所有者可读写 |

### 2.3 排错指南

**问题1：** `ssh_exchange_identification: Connection closed by remote host`
- 检查 SSH 服务状态：`sudo launchctl list | grep ssh`
- 检查防火墙：`sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off`

**问题2：** `认证失败（密钥登录无效）`
- 检查公钥是否正确写入 authorized_keys
- 检查权限：`ls -la ~/.ssh/`
- 检查 SSH 配置：`cat /etc/ssh/sshd_config | grep -i "pubkeyauthentication"`
  - 应显示 `PubkeyAuthentication yes`

**问题3：** `Host key verification failed`
- VPS 第一次连接时需要确认 host key
- 添加参数绕过：`-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null`

## 三、Cloudflare DNS 管理

### 3.1 API Token 创建

权限要求：
| 权限 | 值 | 说明 |
|------|-----|-------|
| Zone | Read | 查看 Zone ID |
| DNS | Edit | 管理 DNS 记录 |

Zone Resources: Include - Specific zone - `lulugame.fun`

### 3.2 获取 DNS 记录列表

```bash
# 1. 获取 Zone ID
ZONE_ID=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=lulugame.fun" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq -r '.result[0].id')

# 2. 获取所有 DNS 记录
curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?per_page=100" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.result[] | {name, type, content, proxied}'
```

### 3.3 清理无用记录

常见可删除的测试记录：
- 指向 `192.0.2.1` 的记录（RFC 5737 测试地址）
- 旧的 Tunnel 指向（不再使用的 CF Tunnel ID）

## 四、存储规划

### 三层存储架构

```
256G SSD (系统盘)
├── macOS 系统
├── Hermes 程序
└── 配置文件

1TB SSD (数据盘)
├── Hermes 数据库
├── 日志文件
└── 用户数据

4TB 机械 (冷数据)
├── 智能法制助手数据
├── 案件资料（敏感数据）
└── 备份存档
```

**数据分类原则：**
| 类型 | 位置 | 备份策略 |
|------|-------|----------|
| 程序/配置 | 256G | 可快速重建，无需单独备份 |
| 用户数据 | 1TB SSD | 定期备份到 4TB |
| 案件资料 | 4TB 机械 | 本地主备份，不上云 |

## 五、切换策略

### 准备期（当前）
- VPS 继续运行主力
- Mac 安装基础环境，不处理敏感数据
- 测试稳定性

### 并行期
- 两台机器同时运行
- 逐步切换非敏感流量
- 验证 Mac 稳定性

### 切换期
- VPS 处理：论文、企微资料（非敏感）
- Mac 处理：案件资料、法制助手（敏感）

## 参考

- skill: `lulu-workflow` - 部署工作流程
- memory: 用户偏好 - 规划优先于执行
