---
name: windows-admin-via-wsl
title: WSL + Windows 原生 SSH 管理 Windows（远程访问/用户/配置/清理/软件）
description: 从 WSL 通过 PowerShell interop 管理 Windows 用户、清理残留目录、处理乱码文件名、远程性能监控。适用于 Lulu 的 Win + WSL 双环境。
---

## 背景

Lulu 的 Win 本通过 Tailscale (100.80.251.96) 可达，WSL (Ubuntu 26.04) 运行在其上。管理 Windows 需通过 `sshpass` 到 WSL，再通过 WSL 的 `/mnt/c/` 或 PowerShell interop 操控 Windows。

## 用户策略：直接连实际 Windows 用户，不建专用 SSH 用户

**核心经验：** 直接用 Lulu 的 Windows 本地用户（陆海天）SSH 连接，不要创建独立的 SSH-only 用户（如 `lulu`）。

### 为什么

| 方案 | 优点 | 缺点 |
|:-----|:-----|:-----|
| ✅ **连实际用户（陆海天）** | 直接管理和写入用户桌面、文件 | 需要知道 Windows 登录密码 |
| ❌ **建专用 SSH 用户（lulu）** | 密码可设简单 | ❌ 无法访问实际用户的桌面/文件 |
| | | ❌ 一删了之多一步 |

根本问题是 Windows 用户权限墙：**SSH 以谁的身份登录，就只能访问谁的桌面和用户文件。** 建一个独立的 `lulu` 用户虽然 SSH 通了，但 `lulu` 用户看不见 `陆海天` 桌面上的任何文件，反之亦然——即使两者都是 Administrators 组成员也不管用。

### 密码为空格的支持

Windows 本地用户允许以**纯空格**作为密码。SSH 同样支持空格密码，通过 `sshpass` 传递：

```bash
# 密码为6个空格
sshpass -p '      ' ssh -p 2222 陆海天@100.80.251.96 "whoami"
```

SCP 同理：
```bash
sshpass -p '      ' scp -P 2222 /tmp/file.bat '陆海天@100.80.251.96:C:\Users\陆海天\Desktop\'
```

注意：中文用户名在 SSH/SCP 命令中可以直接写全拼（如 `陆海天`），Windows OpenSSH 能正确解析。

### ⚠️ 跨用户文件访问铁律

**SSH 以 A 用户登录，不能写入 B 用户的桌面/AppData/用户目录。** 即使 A 在 Administrators 组：

```powershell
# ❌ 以 lulu 身份 SSH 连入，尝试写入陆海天桌面
Copy-Item "C:\Users\lulu\Desktop\file.bat" "C:\Users\陆海天\Desktop\file.bat"
# → PermissionDenied

# ❌ 同一用户的不同目录也可能受 UAC 限制
# Public Desktop (C:\Users\Public\Desktop\) 也拒绝非提权写入
```

解决方案：

| 方法 | 适用场景 | 备注 |
|:-----|:---------|:-----|
| **直接用目标用户 SSH** | 最推荐 | 一次性解决所有权限问题 |
| 计划任务以 SYSTEM 运行 | 需要管理员 SSH 且定时 | 跳过 UAC 但引号地狱严重 |
| 用户手动操作 | 一次性的管理员操作 | Win+X → 终端(管理员) |

### 迁移方案：删除 SSH-only 用户

如果已创建了 SSH-only 用户（如 `lulu`）想切换到实际用户：

1. ✅ 确认实际用户（陆海天）SSH 可连
2. ✅ 把文件复制到实际用户的桌面/目录
3. ➕ 删除 SSH-only 用户：`Remove-LocalUser -Name "lulu"`
4. ✅ 更新记忆中的 SSH 配置

**注意：** SSH-only 用户在 Administrators 组时，`Remove-LocalUser` 可以直接从远程 PowerShell 执行（陆海天身份），不需要提权。

## 先决条件

- WSL 已安装，`systemd=true` 在 `/etc/wsl.conf`
- `sshpass` 在 VPS 可用
- 知道 WSL 登录密码

## SSH 远程访问架构

### WSL SSH 的局限性

WSL SSH 服务器的生命周期绑定在 WSL 对话框上：

| 行为 | 后果 |
|:----|:-----|
| 关闭 WSL 对话框 | SSH 可能掉线（`Connection reset` 或 `Connection timed out during banner exchange`） |
| 重新打开 WSL | SSH 服务不一定自动重启，需 `sudo service ssh restart` |
| WSL 重启 | Tailscale 端口转发规则可能丢失 |
| **执行 `sudo passwd lulu` 改密码** | **旧的 `sshpass` 密码立刻失效，下次 SSH 报 `Permission denied`**。必须把新密码同步给 VPS 端的脚本/命令。 |

**根本原因：** WSL 端口转发到 Windows 22 端口（`100.80.251.96:22 → 172.20.212.99:22`），WSL 一重启转发就断了。

### 推荐方案：Windows 原生 OpenSSH Server + 非标准端口

长期稳定方案是在 Windows 本机安装 OpenSSH Server，让 SSH 直接连 Windows 而非走 WSL 转发。

**端口方案（避免冲突）：**
- 端口 **22** → WSL SSH（通过 netsh portproxy 转发到 WSL 内网 IP）
- 端口 **2222** → Windows 原生 SSH（避免与 WSL 抢占 22 端口）

这样 WSL 管理走 22 端口，Windows 管理走 2222 端口，互不干扰。

### ⚠️ 从 WSL 的权限铁壁：所有 Windows 管理员操作必须让用户手动跑

这是一个反复踩坑的核心规律。**从 WSL 没有任何方式可以绕过 Windows UAC**：

| 想做的事 | 从 WSL 尝试 | 结果 |
|:---------|:------------|:-----|
| `Start-Service sshd` | `powershell.exe -Command "..."` | ❌ 拒绝访问 |
| `sc.exe start sshd` | WSL 内直接跑 | ❌ `OpenService 失败 5: 拒绝访问` |
| `Set-Service -StartupType` | 同上 | ❌ 拒绝访问 |
| `New-NetFirewallRule` | 同上 | ❌ 拒绝访问 |
| `Add-WindowsCapability` | 同上 | ❌ 需要提升 |
| `netsh portproxy delete` | 同上 | ❌ 需要提升 |
| `schtasks /Create /RU SYSTEM` | 从 WSL 调 schtasks.exe | ❌ 同样报"拒绝访问"（无解） |
| 编辑 `C:\\ProgramData\\ssh\\sshd_config` | `sudo sed` 或 `powershell Set-Content` | ❌ 拒绝访问 / 无终端 |
| 编辑 `C:\ProgramData\ssh\sshd_config` | `sudo sed` 或 `powershell Set-Content` | ❌ 拒绝访问 / 无终端 |

**唯一正确的做法：**
1. 在 WSL 里准备好脚本写到 `C:\tmp\` 共享目录
2. **让用户在 Windows 本机以管理员身份开 PowerShell**（Win+X → 终端(管理员)），粘贴运行
3. 然后从 WSL 验证结果

```bash
# 在 WSL 里写好脚本
cat > /mnt/c/tmp/install_ssh.ps1 << "EOF"
Add-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0"
Start-Service sshd
Set-Service -Name sshd -StartupType "Automatic"
New-NetFirewallRule -DisplayName "OpenSSH Server (sshd)" -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow
EOF

# 然后让用户自己在管理员 PowerShell 执行：
# C:\tmp\install_ssh.ps1
```

⚠️ **手写这条经验：** 没有捷径，别浪费时间试 `schtasks /Create /RU SYSTEM`、`Start-Process -Verb RunAs`、`runas` 等提权方案——从 WSL 调 `powershell.exe` 统统没管理员权限。

**不要浪费时间寻找 WSL 内的提权捷径**——不存在。直接让用户跑管理员 PowerShell 是最快的路。

### WSL 内 PowerShell.exe 路径问题

WSL 默认 PATH 不包含 Windows 的 System32 目录（`powershell.exe` 会报 `command not found`）。

**必须用完整路径：**
```bash
# ❌ 错误（command not found）
powershell.exe -Command "..."

# ✅ 正确（完整路径）
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "..."
```

### 第一步：先检查是否已预装（Win 10/11 自带）

很多 Windows 10/11 已经预装了 OpenSSH Server，只是服务没启动。**别急着下载安装，先检查：**

```bash
# 方法 A：查服务是否存在
/mnt/c/Windows/System32/sc.exe query sshd

# 方法 B：查二进制文件
ls /mnt/c/Windows/System32/OpenSSH/

# 方法 C：Powershell 查可选功能
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
  "Get-WindowsCapability -Online -Name 'OpenSSH.Server*' | Select-Object Name,State"
```

**判断结果：**

| `sc query sshd` 返回 | `ls OpenSSH/` | 结论 |
|:---------------------|:--------------|:------|
| `STOPPED` | 有文件 | ✅ 已装，直接 `Start-Service sshd` |
| 服务不存在 (`error 1060`)  | 有文件 | ❌ ZIP 解压到了正确位置但没跑 install-sshd.ps1，服务未注册 |
| 服务不存在 (`error 1060`) | 无文件 | ❌ 完全没装 |
| `START_PENDING` | 有文件 | 正在启动中，等一下再试 |

⚠️ 从 WSL 内 `powershell.exe` 查状态也可能报\"需要提升\"（COMException），但 `sc.exe query` 和 `ls` 不需要管理员权限，足够判断。

### 安装 Windows OpenSSH Server

**方法 A — 设置里装（最稳）：**
`Win+I` → 应用 → 可选功能 → 添加功能 → 搜索 "OpenSSH 服务器" → 勾上安装

**方法 B — 管理员 PowerShell（Add-WindowsCapability）：**
```powershell
Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0'
```
⚠️ **下载可能看起来卡住不动**，实际上后台在跑。等 1-2 分钟，如果实在等不了就 `Ctrl+C` 关掉，然后检查是否"看似卡住实则已装好"：

```bash
/mnt/c/Windows/System32/sc.exe query sshd
```

如果发现 `sshd` 服务已存在（`STOPPED` 或 `START_PENDING`），说明下载/安装**实际上成功了**，只是进度条卡了。

**方法 C — DISM（离线安装）：**
```powershell
dism /online /Add-Capability /CapabilityName:OpenSSH.Server~~~~0.0.1.0 /LimitAccess /Source:C:\Windows\WinSxS
```

**方法 D — winget（最快，但不一定找得到）：**
```powershell
winget install Microsoft.OpenSSH.Beta --source winget
```
⚠️ 实测 `winget` 可能返回 `No package found matching input criteria`，备选其他方法。

**方法 E — GitHub Releases 下载 .zip（含 install-sshd.ps1）：**
从 GitHub Releases 下载 OpenSSH-Win64.zip：[https://github.com/PowerShell/Win32-OpenSSH/releases](https://github.com/PowerShell/Win32-OpenSSH/releases)

**方法 F — 阿里云镜像/离线包：**
用户可能去阿里云镜像站找离线包。确认文件名（.msi 或 .zip）。

**⚠️ 常见坑：误下签名文件（.asc）。** GitHub 下载页也提供 `OpenSSH-Win64-vX.X.X.X.tar.gz.asc` 文件——这是 **GPG 签名验证文件**，只有几百字节，不是安装包。用户下载后解压会得到无意义的签名数据。认准后缀 `.msi` 或 `.zip`。

**⚠️ 常见坑：Add-WindowsCapability 看起来卡住不动。** PowerShell 的 `Add-WindowsCapability -Online` 命令下载时可能没有进度反馈，看起来像卡死了。实际上后台在下载安装。判断方法：另开一个窗口或之后用以下命令检查：
```bash
/mnt/c/Windows/System32/sc.exe query sshd
```
如果返回 `STATE: STOPPED` 或 `STATE: START_PENDING`，说明安装**实际上成功了**，只是进度条没刷新。直接接着启动服务即可。

**⚠️ 常见坑：误下签名文件。** GitHub 下载页也提供 `.tar.gz.asc`（GPG 签名验证文件，只有几百字节）**不是安装包**。认准 `.msi` 或 `.zip`。

**方法 F — 阿里云镜像/离线包：**
用户可能去阿里云镜像站找离线包。确认文件名（.msi 或 .zip）。

### 🧩 ZIP 包安装流程（重点！）

如果用户下载的是 .zip 包，解压后必须运行 `install-sshd.ps1` 注册服务，**仅解压到 `C:\Windows\System32\OpenSSH\` 不会注册服务**：

```powershell
# 1. 解压到某个目录，比如 D:\download\OpenSSH-Win64\
# 2. 管理员 PowerShell 运行安装脚本
D:\download\OpenSSH-Win64\OpenSSH-Win64\install-sshd.ps1

# 3. 启动服务
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
```

**判断是否已注册服务：**
```bash
# 如果 sc query sshd 返回 "服务未安装"（error 1060），就是没跑 install-sshd.ps1
/mnt/c/Windows/System32/sc.exe query sshd
# 输出：STATE: STOPPED → 已装好，直接启动
# 输出：error 1060 → 未注册，需跑 install-sshd.ps1
```

### 安装后验证 + 设置非标准端口（避免与 WSL 冲突）

Windows SSH 装好后，WSL 可能已经通过 `netsh portproxy` 占用了 22 端口。检测方法：

```bash
/mnt/c/Windows/System32/netsh.exe interface portproxy show all
```

如果输出 `0.0.0.0:22 → 172.20.212.99:22`，说明 22 端口转给了 WSL。

**解决方案：Windows SSH 走 2222 端口，WSL 继续用 22 端口。**

在**管理员 PowerShell** 依次执行：

```powershell
# 1. 改 sshd_config 端口（Port 22 → Port 2222）
(Get-Content "C:\ProgramData\ssh\sshd_config") -replace "#Port 22","Port 2222" | Set-Content "C:\ProgramData\ssh\sshd_config"

# 2. 防火墙放行 2222
New-NetFirewallRule -DisplayName "OpenSSH 2222" -Direction Inbound -Protocol TCP -LocalPort 2222 -Action Allow

# 3. 重启 sshd
Restart-Service sshd
```

⚠️ `C:\\ProgramData\\ssh\\sshd_config` 是受保护目录，从 WSL 无法编辑（`sudo` 也无效，因为文件在 Windows 文件系统上），**必须让用户手动执行**。

#### Match Group administrators 块（禁用管理员密码登录）

Windows OpenSSH 默认配置包含：
```
Match Group administrators
       AuthorizedKeysFile __PROGRAMDATA__/ssh/administrators_authorized_keys
```

这个 Match 块导致**所有管理员用户只能用密钥登录，密码登录直接被忽略**，即使全局设置了 `PasswordAuthentication yes`。解决方案：删掉/注释掉这个 Match 块。

**管理员 PowerShell：**
```powershell
(Get-Content "C:\ProgramData\ssh\sshd_config") -notmatch "Match Group administrators|AuthorizedKeysFile __PROGRAMDATA__" | Set-Content "C:\ProgramData\ssh\sshd_config"
Restart-Service sshd
```

#### Copy-Item（不是 copy /Y）

PowerShell 中没有 `copy /Y` 语法，用户从 cmd 习惯来的会报错。PowerShell 用 `Copy-Item` + `-Force`：
```powershell
# ❌ 错误
copy "C:\tmp\keys" "C:\ProgramData\ssh\" /Y

# ✅ 正确
Copy-Item "C:\tmp\keys" "C:\ProgramData\ssh\administrators_authorized_keys" -Force
```

#### 用户交互模式

让用户执行管理员命令时，**必须给出可以直接复制粘贴的完整命令**。标准的交互模式：

1. 在 WSL 里写好脚本到 `C:\tmp\`（如果命令短则不需要写文件）
2. **明确告知用户按什么键**：`Win+X → 选「终端(管理员)」`
3. 给出**一行或几行完整命令**，直接复制粘贴就能跑
4. 用户跑完后告诉我结果，我来验证

### 验证连通性

```bash
从 VPS 测试 Windows SSH（2222 端口）
sshpass -p '密码' ssh -p 2222 -o StrictHostKeyChecking=no lulu@100.80.251.96 "whoami && ver"

从 VPS 测试 WSL SSH（22 端口，走 portproxy）
sshpass -p '密码' ssh -o StrictHostKeyChecking=no lulu@100.80.251.96 "uname -a"

### 🔑 配置 SSH 密钥认证（Windows SSH）

Windows OpenSSH 对**管理员用户**强制走密钥认证（`Match Group administrators` 块），密码登录直接拒绝。必须配置密钥。

#### 第一步：生成密钥对

```bash
# 在 VPS/Mac 端生成，不要设密码（-N ""）
ssh-keygen -t ed25519 -f ~/.ssh/windows_key -N ""
```

#### 第二步：添加公钥到 Windows

公钥必须写入 `C:\ProgramData\ssh\administrators_authorized_keys`（注意不是 `~/.ssh/authorized_keys`！）。**写这个文件有三个陷阱：**

**陷阱 1 — 路径不对：** 管理员用户的 authorized_keys 在 `%ProgramData%\ssh\administrators_authorized_keys`，不是 `%USERPROFILE%\.ssh\`。

**陷阱 2 — 编码不对（最坑）：** PowerShell 的 `Out-File` **默认用 UTF-16 LE 编码**，每个字符之间塞入 `\u0000` 空字节。OpenSSH 只认 ASCII/UTF-8，UTF-16 内容会被当成无效密钥直接拒绝。

```
# ❌ Out-File 默认行为（UTF-16 LE — 每个字符间有空字节，SSH 不认）
s\u0000s\u0000h\u0000-\u0000e\u0000d\u00002\u00005\u00005\u00001\u00009\u0000...

# ✅ 必须指定 ASCII 或无 BOM UTF-8
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...
```

**陷阱 3 — 权限不对：** 文件必须只允许 SYSTEM 和 Administrators 访问，否则 OpenSSH 忽略此文件（安全策略）。`icacls` 必须设：

```powershell
icacls "C:\ProgramData\ssh\administrators_authorized_keys" /inheritance:r /grant "SYSTEM:(R)" /grant "BUILTIN\Administrators:(R)"
```

#### 完整安装流程（用户在管理员 PowerShell 执行）

```powershell
# 1. 写公钥（⚠️ 必须指定 -Encoding ascii！）
"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA..." | Out-File -Encoding ascii -FilePath "C:\ProgramData\ssh\administrators_authorized_keys" -Force

# 2. 修权限
icacls "C:\ProgramData\ssh\administrators_authorized_keys" /inheritance:r /grant "SYSTEM:(R)" /grant "BUILTIN\Administrators:(R)"

# 3. 重启 sshd
Restart-Service sshd
```

**注意：** `C:\ProgramData\` 是受保护目录，从 WSL 的 `powershell.exe` 也无法写入（拒绝访问），必须用户在 Windows 本机以管理员身份跑 PowerShell。

#### 测试连接

```bash
ssh -p 2222 -i ~/.ssh/windows_key -o StrictHostKeyChecking=no lulu@100.80.251.96 "whoami && ver"
```

> 如果 `Permission denied (publickey)` 且密钥没错，99% 是文件编码问题——去 WSL 里 `cat "/mnt/c/ProgramData/ssh/administrators_authorized_keys"` 看有没有 `\u0000` 空字节。有的话就是编码错了，重写。
```

### ⚠️ 从 WSL 装 Windows 软件的权限铁壁

WSL 内的 `powershell.exe` **没有管理员权限**，以下所有命令都会报"拒绝访问"：

```powershell
# 全部失败 ❌
Add-WindowsCapability ...              # COMException / 需要提升
Start-Service sshd                      # 无法打开服务 / 拒绝访问
Set-Service -Name sshd ...              # 拒绝访问
New-NetFirewallRule ...                 # 拒绝访问
schtasks.exe /Create /RU SYSTEM ...     # 拒绝访问（连创建计划任务都不行）
```

**没有任何取巧方式能从 WSL 绕过 Windows UAC。** 所有需要管理员权限的操作，唯一可靠方案是：

1. 在 WSL 里写好脚本到 `C:\tmp\` 共享目录
2. 让用户在 **Windows 本机以管理员身份开 PowerShell**（Win+X → 终端(管理员)），粘贴运行

```bash
# 在 WSL 里写脚本
cat > /mnt/c/tmp/install_ssh.ps1 << "EOF"
Add-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0"
Start-Service sshd
Set-Service -Name sshd -StartupType "Automatic"
New-NetFirewallRule -DisplayName "OpenSSH Server (sshd)" -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow
EOF

# 用户自己在管理员 PowerShell 执行：
# C:\tmp\install_ssh.ps1
```

### 启动服务 & 防火墙

安装完成后，在**管理员 PowerShell** 执行：

```powershell
# 启动 SSH 服务并设为自动
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# 防火墙放行 22 端口
New-NetFirewallRule -DisplayName 'OpenSSH Server (sshd)' -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow

# 确认安装成功
Get-Service sshd
```

### 验证连通性

```bash
# 用密码连接 Windows
ssh lulu@100.80.251.96
```

### 检查是否已安装

```powershell
Get-WindowsCapability -Online -Name 'OpenSSH.Server*' | Select-Object Name,State
```

如果显示 `Installed`，直接 `Start-Service sshd` 即可。

## Windows 用户管理

### 列出用户

```bash
sshpass -p '密码' ssh lulu@100.80.251.96 \
  "/mnt/c/.../powershell.exe -NoProfile -ExecutionPolicy Bypass \
  -Command 'Get-LocalUser | Select-Object Name, Enabled, LastLogon'"
```

### 查看 Administrators 组

```bash
sshpass -p '密码' ssh lulu@100.80.251.96 \
  "/mnt/c/.../powershell.exe ... \
  -Command 'Get-LocalGroupMember -Group Administrators | Select-Object Name'"
```

### 创建新 Windows 用户

从远程通过 WSL 创建 Windows 本地用户：

```powershell
# ❌ net user 会失败（密码太简单报错 1317）
net user lulu 111111 /add
# 报错：指定的账户不存在 / 用户名与计算机名可以不同

# ✅ New-LocalUser 成功
$pw = ConvertTo-SecureString "111111" -AsPlainText -Force
New-LocalUser "lulu" -Password $pw -FullName "lulu"
Add-LocalGroupMember -Group "Administrators" -Member "lulu"
```

**注意：** `net user` 对简单密码（纯数字、过短）可能拒绝创建，而 `New-LocalUser` 没有此限制。

### 删除用户 + 用户目录

```powershell
Remove-LocalUser -Name "用户名"
Remove-Item -Recurse -Force "C:\Users\用户名"
```

**顺序重要：** 先 `Remove-LocalUser` 删用户，再删目录（目录可能被进程锁住）。

## 处理乱码文件名（中文编码问题）

PowerShell 显示中文用户名时可能乱码（如 `½`、`½����`），用 WSL 原生文件系统命令绕过：

### 查真实文件名

```bash
ls -la /mnt/c/Users/
find /mnt/c/Users/ -maxdepth 1 -type d | sort
```

### 通配符模糊删除

```bash
find /mnt/c/Users/ -maxdepth 1 -type d -name "½*" -exec rm -rf {} \;
```

### 验证清理

```bash
ls /mnt/c/Users/ | grep -v 'Default\|Public\|AppData'
```

## 检查 Win 系统综合状态

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, LastBootUpTime, OSArchitecture
Get-ChildItem "C:\Users" | Select-Object Name, LastWriteTime
Get-Process | Where-Object { $_.ProcessName -match "node|openclaw" }
```

## 从 WSL 安装软件（无 sudo）

当 GitHub 不可用时，从 nodejs.org 下载 Node.js 二进制包：

```bash
curl -L 'https://nodejs.org/dist/v24.9.0/node-v24.9.0-linux-x64.tar.xz' -o /tmp/node.tar.xz
tar -xf /tmp/node.tar.xz
cp -r node-v24.9.0-linux-x64/* ~/.local/
export PATH=$HOME/.local/bin:$PATH
```

## PM2 管理 OpenClaw（绕过 launcher 问题）

OpenClaw 的 `openclaw.mjs` launcher 会 spawn 子进程做 compile cache 优化，PM2 会跟踪到父进程而非实际网关。**必须用 entry.js 直接启动：**

```bash
pm2 start node --name openclaw-gateway -- \
  /home/lulu/.local/lib/node_modules/openclaw/dist/entry.js \
  gateway --port 18789
```

### PM2 开机自启（WSL systemd）

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/pm2-lulu.service << 'EOF'
[Unit]
Description=PM2 process manager
After=network.target

[Service]
Type=forking
Environment=PATH=/home/lulu/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PM2_HOME=/home/lulu/.pm2
ExecStart=/home/lulu/.local/bin/pm2 resurrect
ExecReload=/home/lulu/.local/bin/pm2 reload all
ExecStop=/home/lulu/.local/bin/pm2 kill

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable pm2-lulu
loginctl enable-linger lulu
```

## 卸载 Windows 应用

### 获取卸载命令

从注册表读 UninstallString 和 QuietUninstallString：

```python
ps_cmd = r'Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" | Select DisplayName, Publisher, UninstallString, QuietUninstallString | ConvertTo-Json -Compress'
```

**同时查 32 位注册表：** `HKLM:\Software\WOW6432Node\...` 路径。

### 静默卸载

优先尝试带 `/S` 或 `/SILENT` 参数的卸载命令（来自 `QuietUninstallString`）：

```bash
# MSI 应用（用 /quiet）
"/mnt/c/Windows/System32/msiexec.exe" /x {GUID} /quiet /norestart

# Inno Setup（有 /SILENT）
"D:\\lm\\unins000.exe" /SILENT

# NSIS（有 /S）
"D:\\path\\Uninstall.exe" /S
```

### 无静默参数时

直接运行 UninstallString（会弹出卸载向导，SSH 下无法交互，但应用仍会注册卸载）：
```bash
"/mnt/e/txhuiyi/WeMeet/3.40.2.407/WeMeetUninstall.exe"
```

**注意：** MSI /S 卸载可能超时，也试试不加 /quiet 的裸命令。

### MSI 卸载失败排查

1. 先 kill 目标进程：`taskkill /F /IM "EpicGamesLauncher.exe" /T`
2. GUID 可能不对，从注册表 `Get-ChildItem` 查 DisplayName 对应 GUID
3. 备选：`wmic product where "name like '%Epic%'" call uninstall`

### ⚠️ 重要陷阱

| 陷阱 | 示例 | 解决 |
|:----|:----|:-----|
| MSI 卸载疑似成功但实际失败 | exit 0 + 乱码输出 | 检查目录是否还在 |
| 注册表大小 ≠ C 盘占用 | QQ 显示 1GB 但实际在 D 盘 | 读 UninstallString 确认路径 |
| 完美世界等游戏平台可能在 D:\新建文件夹 下 | 卸载命令路径含中文 | 用 `/mnt/d/` 绝对路径 |
| 卸载超时 | MSI 默认 120s+ | 设 timeout=120 |

## 清理 Windows 缓存

C 盘常见缓存位置及清理命令：

```bash
# Windows 临时文件（安全清理）
rm -rf /mnt/c/Windows/Temp/*

# 用户临时文件（安全清理，锁文件保留）
rm -rf /mnt/c/Users/*/AppData/Local/Temp/*

# Windows Update 缓存（安全清理）
rm -rf /mnt/c/Windows/SoftwareDistribution/Download/*
```

**注意事项：**
- Temp 目录被锁的文件会跳过，不影响系统
- Windows Update 缓存可以清，下次更新会重新下载

## 验证实际安装位置（注册表 vs 磁盘）

注册表 UninstallString 暴露真实安装路径，用来区分"注册表认为在 C 盘 vs 实际在 D/E 盘"：

```bash
# 从 UninstallString 提取路径（如 D:\\腾讯qq\\Uninstall.exe）
# 然后用 du 验证
du -sh /mnt/d/腾讯qq/
```

**常见模式：** QQ、迅雷、网易云、小黑盒加速器等国产软件常默认装到 D 盘，但注册表仍显示在 C 盘（占空间统计），实际不占 C 盘空间。

## 批量卸载工作流

```
1. 扫全部注册表 → 按需建立目标列表
2. 读 UninstallString + QuietUninstallString
3. 分类：有静默参数 → 直接卸载；无静默参数 → 裸跑
4. 查实际安装路径释放空间（注册表虚标 vs 真实）
5. 验证：再次扫注册表确认条目消失
6. 收尾：清理残留目录 + Temp
```

## Windows 软件清单扫描

从 WSL 远程扫描 Windows 所有安装程序（注册表 + 游戏库 + 便携应用）。详见 `references/software-inventory.md`。

### 核心思路（三层互补）

| 层 | 覆盖 | 获取方式 |
|:---|:-----|:---------|
| 注册表 64位 | Add/Remove Programs | `Get-ItemProperty HKLM:\Software\...\Uninstall\*` |
| 注册表 32位 | 32位程序 | `HKLM:\Software\WOW6432Node\...\Uninstall\*` |
| 文件系统 | Steam/Epic/WeGame 游戏库 + 便携应用 | `ls /mnt/d/*/` + 游戏库子目录 |

### PowerShell 命令要点

- **stdin 管道模式**避开引号地狱：`echo 'PS脚本' | powershell -NoProfile -Command -`
- `$_` 在 bash 里转义为 `\\$_.DisplayName`
- 中文输出用 GBK 解码
- 查 32 位注册表时同样管道模式，单引号包裹

### Base64 管道传复杂脚本

当需要 Python 后处理（JSON 解析、合并数据源、格式化输出）时，用 base64 编码传脚本：

```bash
# 写脚本到 VPS → base64 → SSH 管道 → 流式执行
base64 < /tmp/script.py | sshpass -p '密码' ssh lulu@100.80.251.96 \
  'base64 -d | python3'
```

**注意：** 不要中间再写文件再执行（`cat > /tmp/s.py && python3 /tmp/s.py`），中文编码会被破坏。直接 `base64 -d | python3` 最稳。

## WeGame/Delta Force 游戏缓存清理

WeGame 游戏（如三角洲行动）缓存路径和清理模式：

```bash
# 三角洲行动缓存目录（在 WeGameApps 下）
# 注意路径含括号，bash 需要转义
DF_BASE="/mnt/d/WeGameApps/rail_apps/DeltaForce(2001918)"

# tiny_cache（根目录）
rm -rf "$DF_BASE/tiny_cache/"*

# icreate/tiny_cache  
rm -rf "$DF_BASE/icreate/tiny_cache/"*

# Saved 目录下的 webcache 和 pixuicache
rm -rf "$DF_BASE/DeltaForce/Saved/webcache_"*
rm -rf "$DF_BASE/DeltaForce/Saved/pixuicache"

# PipelineCacheData
rm -rf "$DF_BASE/DeltaForce/Content/PipelineCacheData/"*
```

**缓存释放预估：** 三角洲行动可释放 ~1.3GB 缓存。游戏本体（149GB）不受影响。

常见 WeGame 缓存位置模式：
- `tiny_cache/` （根目录或子目录）
- `Saved/webcache_*`
- `Saved/pixuicache`
- `Content/PipelineCacheData/`
- `Intermediate/AssetRegistryCache/`

## 开机启动项排查

当用户反馈有未知程序开机弹出时，用七层排查法从浅到深定位。详见 `references/startup-investigation.md`。

**核心命令：** `Get-CimInstance Win32_StartupCommand` — 一份命令覆盖所有启动来源。

## 检测并清除隐藏/流氓软件

当用户反馈右下角弹出未知通知但在已安装程序列表找不到时，使用以下工作流。

### 第0步：进程级定位（最快找到藏身处）

很多流氓软件会注入系统托盘，被识别为 `SystrayComponent`：

```powershell
# 找进程 -> 看 ExecutablePath -> 定位真实目录
Get-Process | Where-Object { $_.ProcessName -match "SystrayComponent" }
Get-CimInstance Win32_Process -Filter "Name = 'winToolBoxSrv.exe'" |
  Select-Object ProcessId, ExecutablePath, CommandLine
```

**典型进程名：** winToolBoxSrv, WinTray, cssdk, softmgrsvr, pdfReaderSrv, winInterceptSer

### 第1步：查启动机制（三重排查）

```powershell
# 服务（最常见藏身点）
Get-CimInstance Win32_Service | Where-Object { $_.PathName -match "可疑名字" }
# 任务计划
Get-ScheduledTask | Where-Object { $_.TaskName -match "可疑" }
# 启动项
Get-CimInstance Win32_StartupCommand | Where-Object { $_.Command -match "可疑" }
```

### 第2步：停止 + 删除服务

```powershell
Stop-Service 服务名 -Force
sc.exe delete 服务名
```

**注意：** 一个流氓可能注册多个服务，以 Update Event Notification Service 为伪装。winToolBox 注册了 3 个。

### 第3步：杀进程 + 删文件

```bash
taskkill /F /IM winToolBoxSrv.exe
taskkill /F /IM softmgrsvr.exe  # 子进程
rm -rf /mnt/c/Users/陆海天/AppData/Local/winToolBox/
```

### 第4步：处理权限保护的文件

如果 rm 报 Input/output error 或 访问被拒绝：

```powershell
takeown /f "目录路径" /r /d y
icacls "目录路径" /grant "用户名:(OI)(CI)F" /T /Q
Remove-Item "目录路径" -Recurse -Force
```

**注意：** 必须是全部进程已 kill -> 再删文件。进程以不同身份(SYSTEM)运行时 takeown 也会失败。

### 验证

```powershell
Get-CimInstance Win32_Service -Filter "Name like '%winTool%'"
Test-Path "C:\Users\陆海天\AppData\Local\winToolBox"
```

## Windows 远程性能监控（游戏/应用诊断）

从 Linux 通过 SSH 在 Windows 部署 PowerShell 监控脚本，采集 CPU/GPU/内存数据，用于帧率卡顿诊断。

详见 `references/windows-performance-monitoring.md`。

核心工作流：
1. 写 PowerShell 监控脚本 → SCP 到 `C:\tmp\`
2. 写 .bat 快捷方式 → SCP 到桌面
3. 用户双击 .bat 启动监控 → 开玩 → 停 → 发 CSV 回来分析

## WSL 环境复制（技能/脚本/记忆迁移）

当需要把 VPS 上的 Hermes 技能、脚本、配置记忆复制到 WSL 环境时，用「本地打包 → SCP → 远程解压」模式：

```bash
# 1. 本地打包技能
cd ~/.hermes/skills && tar czf /tmp/skills.tar.gz target-skill/

# 2. SCP 到 WSL
sshpass -p '密码' scp /tmp/skills.tar.gz lulu@100.80.251.96:~/.hermes/skills/

# 3. 远程解压
sshpass -p '密码' ssh lulu@100.80.251.96 "cd ~/.hermes/skills && tar xzf skills.tar.gz && rm skills.tar.gz"
```

**记忆文件**：在 WSL 创建 `~/MEMORY.md` 记录所有配置（SSH信息、已安装软件、脚本位置、待办事项），方便未来会话快速恢复上下文。详见 `references/environment-replication.md`。

**桌面快捷方式**：用 WSL 的 `/mnt/c/Users/<用户>/Desktop/` 路径复制 .bat 到 Windows 桌面。

### Hermes Agent 完整安装

如果需要在 WSL 上完整安装 Hermes Agent（不仅仅是复制技能），见 `references/hermes-install-wsl.md`。

### Hermes Desktop ↔ WSL SSH Tunnel 连接

当需要在 Windows 的 Hermes Desktop 中连到 WSL 的 Hermes 后端（全功能：Chat + Sessions + Skills + Memory + Gateway + Logs），见 `references/hermes-desktop-ssh-tunnel.md`。

核心流程：WSL 启动 `hermes gateway run`（默认端口 8642）→ Desktop 选 SSH Tunnel 模式 → 填 `127.0.0.1:22` + 用户密码 + remote port `8642`。

核心注意事项：
- `install.sh` 在慢网络下 git clone 可能超时（已安装的 Python/Node 不会重装）
- 超时后仓库为空（`No commits yet`），需要清空重试或分段安装
- 兜底方案：VPS 下载后 scp 到目标机器

## 常见陷阱

### ⚡ SSH 连接超时时必须快速失败

**用户明确偏好：当 SSH 连不上时，不要反复重试。** 一次「为什么半天不回复」的教训。

```bash
# ❌ 错误做法 — 5+ 次重试，用户干等 1 分钟
sshpass ... "echo OK"     # timeout
sshpass ... "command"     # timeout  
ping 100.80.251.96        # timeout
ssh via WSL ...           # timeout
ssh via port 2222 ...     # timeout
→ 用户：\"为什么半天不回复\"

# ✅ 正确做法 — 快速诊断 + 直接问用户
ping -c 1 100.80.251.96         # 1 次 ping
如果 timeout → ssh 任意方法 1 次  # 1 次 SSH 尝试
如果全 failed → 直接告诉用户：\"笔记本网络连不上，Tailscale 可能掉了，检查一下？\"
```

**铁律：** 最多 1 次 ping + 1 次 SSH 尝试（选一种方法）。两次都失败 → 立即报告给用户，不要换端口再试。用户连上后会告诉你，你再继续。

### SSH 连接超时的网络诊断

当 `sshpass` 到 Windows/WSL 超时，先确认笔记本是否可达：

```bash
# 快速 ping 测试（1 秒超时）
ping -c 1 -W 1 100.80.251.96 2>&1 | head -3
```

如果 ping 都超时，说明 Tailscale 网络断了或笔记本休眠了——告诉用户检查网络，不要继续尝试。

### 通过 SSH 安装 GUI 软件

`Start-Process` 在 SSH 会话中**无法启动交互式 GUI 程序**（如 Hermes Desktop 安装程序），因为 SSH 没有桌面会话（Session 0 隔离）。

```powershell
# ❌ 全部失败：SSH 下 Start-Process 无法启动 GUI
Start-Process C:\path\to\setup.exe          # 报错：无法访问
Start-Process C:\path\to\setup.exe -Wait    # 一样失败
Start-Process C:\path\to\setup.exe /S       # 静默安装也失败（GUI 框架需要桌面）
```

**规律：** 静默安装参数（`/S`, `/verysilent`, `/quiet`）只在安装程序本身支持无头运行时才有效，而大多数 Electron/NSIS/Inno Setup 安装器需要桌面会话。**能成功安装 GUI 软件的唯一方式：用户在本地双击运行。**

### .bat 文件双击一闪而过

.bat 文件双击后 cmd.exe 执行完自动关闭，窗口消失。**解决：在 .bat 末尾加 `pause`**，让用户看到输出。

### SSH 交互式命令需要 `-t` 伪终端

通过 SSH 远程执行交互式命令（如 `passwd`、`security set-keychain-password`）时，不加 `-t` 会报错：

```bash
# ❌ 报 passwd: authentication token failure / conversation failure
ssh user@host 'passwd'

# ❌ 报 security: couldn't open keychain
ssh user@host 'security set-keychain-password'

# ✅ 加 -t 强制分配伪终端
ssh -t user@host passwd
ssh -t user@host 'security set-keychain-password'
```

**为什么**：`passwd` 等交互式命令需要读写终端（TTY）来接收键盘输入。不加 `-t` 时 SSH 只分配管道（pipe），命令拿不到终端句柄就直接失败。

**应用场景**：

| 命令 | 需要 `-t` | 说明 |
|:-----|:---------:|:-----|
| `passwd` | ✅ | 交互式密码输入 |
| `security set-keychain-password` | ✅ | 钥匙串密码交互 |
| `sudo`（无 NOPASSWD） | ✅ | 需要终端输入密码 |
| `htop/top` | ✅ | 交互式进程查看 |
| `nano/vim` | ✅ | 终端编辑器 |
| 非交互式命令 | ❌ | 如 `whoami`, `ls`, `df -h` |

### NVM 安装后 node 命令找不到

WSL 里用 NVM 安装 Node.js 后，非交互式 SSH 会话（`ssh ... "node --version"`）会报 `command not found`，因为 `.bashrc` 没被 source。

```bash
# ❌ 直接用
sshpass -p '密码' ssh lulu@host "node --version"  # command not found

# ✅ 先 source nvm
sshpass -p '密码' ssh lulu@host "source ~/.nvm/nvm.sh && node --version"
```

**永久解决**：确保 `.bashrc` 里有 NVM 加载代码（`nvm install` 脚本会自动添加），新开终端即可。

### SSH heredoc 里的变量被 bash 解释

通过 SSH 远程创建文件时，heredoc 里的 `$` 会被本地 bash 解释，导致内容被篡改：

```bash
# ❌ $HOME、$USER 等被本地 bash 展开
sshpass -p '密码' ssh lulu@host "cat > ~/file.md << 'EOF'
Home: $HOME
EOF"

# ✅ 方案1：本地创建再 SCP（最稳）
cat > /tmp/file.md << 'EOF'
Home: $HOME
EOF
sshpass -p '密码' scp /tmp/file.md lulu@host:~/file.md
```

**铁律：复杂文件（含变量、特殊字符、多行代码）一律本地创建 + SCP，不要用 SSH heredoc。**

## 文件操作：ncm → mp3 转换

网易云音乐 ncm 文件批量转 mp3 的完整流程见 `references/ncm-conversion.md`。核心命令：

```bash
sshpass -p '密码' ssh lulu@100.80.251.96 "
  /home/lulu/bin/ncmdump -d '/mnt/c/Users/陆海天/Desktop/wyy' -o '/mnt/c/Users/陆海天/Desktop/mp3'
"
```

用户偏好：输出到独立文件夹，不删源文件，ncmdump 直接出 mp3 无需 ffmpeg。

## 远程文件整理（复制/去重/分类）

把 Windows 文件整理到 U 盘时，**用 Python 脚本代替 PowerShell** 避免跨 SSH 引号地狱。详见 `references/remote-file-organization.md`。

## 验证清单

| 检查项 | 命令 |
|:------|:----|
| 用户已删除 | `Get-LocalUser` — 确认目标用户消失 |
| 目录已清 | `Get-ChildItem C:\Users` — 确认目录消失 |
| 端口在听 | `ss -tlnp \| grep 18789` |
| 网关 http 响应 | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:18789/` |
| PM2 状态 | `pm2 status` — online |
| 服务自动启动 | `systemctl --user status pm2-lulu` — enabled |
