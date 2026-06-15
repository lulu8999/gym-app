# BLE 智能门锁品牌数据库

## 品牌速查表

| 品牌 | 协议 | 加密 | Service UUID | 安全评级 | 破解友好 | API |
|:----|:----|:----|:----|:----:|:----:|:----|
| 廉价公模 | BLE | 明文/XOR | 0xFFE0 | ⭐ | ⭐⭐⭐⭐⭐ | 无 |
| TTLock v1-2 | BLE | XOR混淆 | 0xFFF0 | ⭐ | ⭐⭐⭐⭐ | 开放SDK |
| TTLock v3 | BLE | AES-128-CBC | 0xFFF0 | ⭐⭐⭐ | ⭐⭐⭐ | 开放SDK |
| 涂鸦Tuya | BLE/WiFi | AES-256+128 | 自定义128-bit | ⭐⭐⭐ | ⭐⭐⭐ | 开放平台 |
| 小米米家 | BLE | Mi Service+安全芯片 | 0xFE95 | ⭐⭐⭐⭐ | ⭐⭐ | 部分开放 |
| August | BLE+WiFi | AES+TLS双层 | 自定义128-bit | ⭐⭐⭐⭐ | ⭐⭐ | 付费API |
| Yale | BLE+Z-Wave | AES+TLS | 自定义128-bit | ⭐⭐⭐⭐ | ⭐⭐ | 付费API |
| Schlage | BLE+WiFi | AES+安全芯片 | 自定义 | ⭐⭐⭐ | ⭐⭐ | Seam API |
| 德施曼 | BLE+WiFi | AES(自研) | 自定义 | ⭐⭐⭐ | ⭐⭐ | 封闭 |
| 凯迪仕 | BLE+WiFi | AES(自研) | 自定义 | ⭐⭐⭐ | ⭐⭐ | 封闭 |
| 鹿客Loock | BLE+NB-IoT | Mi Service | 0xFE95 | ⭐⭐⭐ | ⭐⭐ | 米家平台 |
| Lockly | BLE+WiFi | AES-128 | 自定义 | ⭐⭐⭐ | ⭐⭐ | 封闭 |
| Ultraloq | BLE+WiFi | MD5(有CVE) | 自定义 | ⭐⭐ | ⭐⭐⭐ | 部分开放 |

## 常见 BLE Service UUID

| UUID | 品牌 | 用途 | 安全 |
|:----|:----|:----|:----:|
| 0xFFE0 → 0xFFE1 | 廉价公模 | 密码/指令写入 | 明文 |
| 0xFFF0 → 0xFFF1 | TTLock | 加密指令写入 | AES |
| 0xFE95 | 小米/鹿客 | Mi Service认证通道 | AES+安全芯片 |
| 自定义128-bit | Tuya | DP数据通道 | AES-256 |
| 自定义128-bit | August/Yale | 加密指令通道 | AES+TLS |
| 0x180F → 0x2A19 | 几乎所有 | 电池电量 | 安全 |
| 0x180A | 几乎所有 | 设备信息 | 安全 |

## 安全评分标准

| 等级 | 特征 | 典型品牌 |
|:----:|:----|:----|
| 1 | 明文/XOR传输 | 廉价公模 |
| 2 | 加密但有已知漏洞/可降级 | TTLock v1-2, Ultraloq |
| 3 | AES+密钥管理 | TTLock v3, Tuya, Schlage |
| 4 | 安全芯片+证书 | 米家, August/Yale |
| 5 | 硬件SE+端到端加密 | Salto, ASSA ABLOY |

## 逆向可行性

### 容易入手的目标（按难度递增）
1. 廉价公模锁 — 直接扫直接写
2. TTLock v1-2 — XOR可本地实现，有开源项目
3. TTLock v3 — 需eKey（从配对过的手机提）或利用协议降级攻击
4. 涂鸦Tuya — 需Access Secret（从涂鸦云获取），离线密码可行

### 高难度目标（仅可监控，难攻击）
5. 米家 — 安全芯片+双向认证，仅可读广播数据
6. August/Yale — 封闭生态+双层加密
7. 德施曼/凯迪仕 — 封闭协议，需逆向App

## 高端锁逆向为何无公开方法（三层次分析）

1. **技术层**: 密钥存于安全元件(SE)，物理防拆+侧信道防护，破解单个锁的成本>100把锁价格
2. **法律层**: DMCA第1201条禁止发布破解工具和方法，安全研究员发文章需隐去关键算法
3. **经济层**: 高端锁投入产出比极低，锁商一个OTA就能废掉已知攻击路径

## 信息来源
- TTLock开放平台: open.ttlock.com
- Aleph Security: Kontrol Lux Lock漏洞分析
- 小米IoT BLE接入文档
- 涂鸦开发者平台
- August安全技术说明
- HA xiaomi_ble组件分析（瀚思彼岸论坛）
- OpenCVE TTLock漏洞库
