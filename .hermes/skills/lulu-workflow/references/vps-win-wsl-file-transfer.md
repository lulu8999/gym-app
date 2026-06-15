# VPS → Windows → WSL 文件传输模式

## 背景

当需要在 WSL 环境安装工具，但 WSL 没有 sudo/pip/unzip 时，需要通过 VPS 中转。

## 正确路径

```
VPS（有代理） → 下载文件 → SCP到Windows → WSL访问/mnt/c/
```

### Step 1: VPS 下载（需要代理）

```bash
# VPS 直连 GitHub 超时，必须走代理
curl -sL --proxy http://127.0.0.1:7890 -o /tmp/file.zip https://github.com/.../releases/download/.../file.zip
```

### Step 2: SCP 到 Windows

```bash
sshpass -p '密码' scp -P 2222 /tmp/file.zip 陆海天@100.80.251.96:C:\\Temp\\
```

### Step 3: WSL 访问

```bash
sshpass -p '密码' ssh -p 2222 陆海天@100.80.251.96 'wsl -u lulu bash -c "cp /mnt/c/Temp/file.zip /tmp/ && cd /tmp && python3 -c \"import zipfile; zipfile.ZipFile(\\\"file.zip\\\").extractall()\""'
```

## 常见坑

| 坑 | 原因 | 解决 |
|----|------|------|
| VPS 下载 GitHub 超时 | 无代理直连 | `--proxy http://127.0.0.1:7890` |
| SSH 嵌套引号地狱 | `wsl -u lulu bash -c "..."` 内部引号冲突 | 分步执行，或用 `cmd /c "wsl ..."` |
| WSL 没有 unzip | Debian 最小安装 | 用 Python `zipfile` 模块 |
| WSL 没有 pip | Debian 最小安装 | 用 `python3 -m venv` 或下载预编译二进制 |
| WSL 没有 sudo 密码 | 用户 lulu 的 sudo 密码 | 从 memory 查或问用户 |
| SCP 路径格式 | Windows 路径 `C:\Temp\` 在 Linux SCP 中 | 用 `C:\\Temp\\` 或 `C:/Temp/` |

## 实战案例：安装 ncmdump（2026-06-13）

```bash
# 1. VPS 下载
curl -sL --proxy http://127.0.0.1:7890 -o /tmp/ncmdump.zip https://github.com/taurusxin/ncmdump/releases/download/1.5.1/ncmdump-1.5.1-linux-amd64.zip

# 2. 解压
cd /tmp && unzip -o ncmdump.zip && chmod +x ncmdump

# 3. SCP 到 Windows
sshpass -p '密码' scp -P 2222 /tmp/ncmdump 陆海天@100.80.251.96:C:\\Temp\\

# 4. WSL 安装
sshpass -p '密码' ssh -p 2222 陆海天@100.80.251.96 cmd /c "wsl -u lulu bash -l -c \"mkdir -p ~/bin && cp /mnt/c/Temp/ncmdump ~/bin/ && chmod +x ~/bin/ncmdump\""

# 5. 验证
sshpass -p '密码' ssh -p 2222 陆海天@100.80.251.96 cmd /c "wsl -u lulu bash -l -c \"~/bin/ncmdump --help 2>&1 | head -3\""
```

## SSH 连接方式（2026-06-14 修正）

| 目标 | 命令 | 端口 | 用户 | 状态 |
|------|------|------|------|------|
| WSL SSH（推荐） | `ssh -p 2222 陆海天@100.80.251.96` | 2222 | 陆海天 | ✅ |
| Windows→WSL | `ssh -p 2222 陆海天@IP 'wsl -u lulu bash -c "..."'` | 2222 | 陆海天 | ✅ |
| 端口 22 | `ssh -p 22 陆海天@100.80.251.96` | 22 | — | ❌ svchost.exe 占用，非 OpenSSH |

**⚠️ 重要**：端口 22 被 `svchost.exe` 占用，不是 Windows OpenSSH。`sshd -T` 显示实际 sshd 配置在 2222。Windows 本机 `ssh localhost` 会 reset。
