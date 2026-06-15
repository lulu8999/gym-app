# 第7-10课：权限/进程/网络/包管理

**日期：** 2026-06-13

## 第7课：权限管理（chmod/chown/sudo）

### 核心命令
```bash
chmod 755 文件名    # 改权限
chmod +x 文件名     # 加执行权限
chown 用户名 文件名  # 改主人
sudo 命令           # 用校长权限执行
```

### 权限数字速记
7=rwx 6=rw- 5=r-x 4=r-- 0=---

### 用户测验结果
**第一轮：2.5/5**
- ❌ 混淆 chmod 和 sudo（用 `sudo +x` 代替 `chmod +x`）
- ❌ 权限数字5算错（写成-wx，应为r-x）

**巩固轮：4.5/5**
- ✅ 全部正确（sudo解释不够精确但可接受）

### 核心混淆点（已攻克）
- `chmod` 改权限 vs `sudo` 提权执行 → 他俩不是一回事
- 权限数字计算：r=4, w=2, x=1，相加得数字

### 教学发现
- 用户对"主人vs同组"概念有疑问，需要大楼比喻解释（房主vs同宿舍同学）
- 类比教学效果好：房间换锁=chmod，校长钥匙=sudo

---

## 第8课：进程管理（ps/top/kill）

### 核心命令
```bash
ps aux              # 看所有进程
ps aux | grep xxx   # 找特定进程
top                 # 实时监控（q退出）
kill PID            # 温和退出
kill -9 PID         # 强制杀
```

### 用户测验结果：5/5 🎉 首测全对
- 管道符 `ps aux | grep` 用得很熟练
- top退出（按q）知道
- kill -9 强制杀理解到位

---

## 第9课：网络工具（curl/ping/ss）

### 核心命令
```bash
ping -c 4 域名           # 测连通
curl -I 网址             # 只看响应头
curl -o 文件名 网址      # 下载
ss -tlnp                 # 看监听端口
ss -tlnp | grep :80      # 过滤端口
```

### ss -tlnp 参数含义
-t=TCP -l=LISTEN -n=数字端口 -p=显示进程

### 用户测验结果
**第一轮：2/5**
- ❌ `ping -3` 代替 `ping -c 3`
- ❌ `ss -tlnp 80` 代替 `ss -tlnp | grep 80`
- ❌ `curl -o URL` 缺文件名

**巩固轮：4.5/5**
- ❌ `curl -i` vs `curl -I` 大小写问题

### 核心坑
1. ping参数是 `-c 次数`，不是 `-次数`
2. ss不支持直接跟端口过滤，必须管道 `| grep`
3. `curl -o` 后面跟**文件名 URL**（两个参数），不是直接跟URL
4. `curl -I`(大写)只看头，`curl -i`(小写)头+内容都输出

---

## 第10课：包管理（apt/pip）

### 核心命令
```bash
sudo apt update              # 刷新软件列表
sudo apt install 包名        # 装系统软件
sudo apt remove 包名         # 卸载
pip install 包名              # 装Python包
pip list                      # 看已装的包
```

### 用户测验结果：3.5/5
- ❌ `sudo apt htop` 缺了 `install`（apt必须跟动作）
- ❌ `sudo apt nginx` 同样缺 install

### 核心坑
- apt后面必须跟动作（install/remove），不能直接跟包名
- apt装系统工具（需要sudo），pip装Python包（一般不需要sudo）

### 教学发现
- 用户追问 nginx vs flask 的区别 → 用前台接待(nginx) vs 后厨(flask) 类比解释效果好
- 用户对"系统工具vs Python包"有疑问 → 用大楼基础设施 vs 房间内家具 类比
