# Hermes Agent 安装到 WSL/远程 Linux

通过官方 `install.sh` 脚本在 WSL（或任何远程 Linux）上部署 Hermes Agent 的完整流程、常见故障及恢复方案。

## 标准安装

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

脚本自动完成：Python 3.11 安装（通过 uv）、Node.js 22 LTS、git clone 仓库、venv 创建、pip 依赖安装。

**注意**：`ripgrep` 和 `ffmpeg` 需要手动安装（root 权限，非交互模式跳过）：
```bash
sudo apt install -y ripgrep ffmpeg
```

## 🔴 常见故障：git clone 超时（最典型）

### 症状

```
→ Installing to /home/lulu/.hermes/hermes-agent...
→ Trying SSH clone...
→ SSH failed, trying HTTPS...
Cloning into '/home/lulu/.hermes/hermes-agent'...
[Command timed out after 300s]  ← 超时
```

### 结果特征

```bash
ls -la ~/.hermes/hermes-agent/
```
- 目录存在但有 `.git/`（空仓库，`No commits yet`）
- 没有实际文件被 checkout

### 诊断

```bash
cd ~/.hermes/hermes-agent && git status
# → "No commits yet"  = 克隆没完成，仓库是空的
```

### 恢复方案

#### 方案 A：重新运行 install.sh（推荐，幂等）

```bash
rm -rf ~/.hermes/hermes-agent
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

`install.sh` 设计为幂等的：已安装的 Python/Node 不会重装，只有 git clone 重做。清空失败的目录后再跑，避免残留冲突。

#### 方案 B：手动 clone + 补全安装脚本

如果 install.sh 的网络仍不稳定，分段执行：

```bash
# 1. 手动 clone（带 --depth 1 减少数据量）
git clone --depth 1 https://github.com/NousResearch/hermes-agent.git ~/.hermes/hermes-agent

# 2. 手动创建 venv + 安装依赖
cd ~/.hermes/hermes-agent
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. 创建 hermes 命令行 symlink
ln -sf ~/.hermes/hermes-agent/.venv/bin/hermes ~/.local/bin/hermes
```

#### 方案 C：VPS 下载后 scp（网络最差时的兜底）

```bash
# 在 VPS（网络好的机器）上 clone
git clone --depth 1 https://github.com/NousResearch/hermes-agent.git /tmp/hermes-agent

# 打包
tar czf /tmp/hermes-agent.tar.gz -C /tmp hermes-agent/

# scp 到目标机器
sshpass -p '密码' scp /tmp/hermes-agent.tar.gz lulu@目标IP:~/.hermes/

# 在目标机器解压
sshpass -p '密码' ssh lulu@目标IP "cd ~/.hermes && tar xzf hermes-agent.tar.gz && rm hermes-agent.tar.gz"
```

### 网络探测

安装前先测一下网络连通性，避免白等 300s：

```bash
# 测 GitHub 连通性（快速探测）
curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 https://github.com 2>/dev/null || echo "FAILED"

# 测 DNS
nslookup github.com 2>/dev/null | head -5 || echo "DNS FAILED"
```

如果 GitHub 不通但有代理/镜像，可在 install.sh 前设环境变量：
```bash
# 设置 git 代理
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
```

## 安装后验证

```bash
# 1. 验证 hermes 命令
source ~/.bashrc
hermes --version

# 2. 验证 Python 版本
python3 --version  # 应显示 3.11.x

# 3. 验证依赖
pip list 2>/dev/null | grep -i hermes

# 4. 验证目录结构
ls ~/.hermes/hermes-agent/
ls ~/.hermes/hermes-agent/.venv/
```

## 已知注意事项

| 问题 | 说明 | 解决 |
|------|------|------|
| NVM 版本的 Node 不被 install.sh 识别 | install.sh 自己装了一份 Node 22 到 `~/.hermes/node/` | 不影响原有 Node，两者共存 |
| `pip install -e .` 在慢网络可能超时 | install.sh 会在 clone 后安装 pip 依赖 | 手动 `cd ~/.hermes/hermes-agent && source .venv/bin/activate && pip install -e .` |
| 非交互式 SSH 不加载 .bashrc | `hermes` 命令可能找不到 | `source ~/.bashrc` 或直接写完整路径 `~/.hermes/hermes-agent/.venv/bin/hermes` |