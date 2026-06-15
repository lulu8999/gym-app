# BLE 门锁全品牌协议数据库（2026-06-13 更新）

> 本文件是 `ble_lock_加密方式调研报告.pdf` 的数据精华版，供 ESP32 探测程序开发时快速查阅。

## 一、品牌速查总表

| 品牌 | 协议 | 加密 | 安全 | ESP32接入难度 | 公开 API | 典型 Service UUID |
|:----|:-----|:-----|:---:|:-----------:|:--------:|:-----------------|
| 廉价公模锁 | BLE | 明文/XOR | 极低 | 低 | 不需要 | `0xFFE0` |
| TTLock v1-v2 | BLE | XOR 混淆 | 极低 | 低 | SDK | `0xFFF0` |
| TTLock v3 | BLE | AES-128-CBC | 中 | 中 | SDK | `0xFFF0` |
| 涂鸦 Tuya | BLE/WiFi | AES-256/128 | 中 | 中 | 开放平台 | 自定义128-bit |
| 小米米家 | BLE | Mi Service+芯片 | 高 | 高 | 部分 | `0xFE95` |
| August | BLE+WiFi | AES+TLS双层 | 高 | 高 | 付费API | 自定义128-bit |
| Yale | BLE+Z-Wave | AES+TLS | 高 | 高 | 付费API | 自定义 |
| 德施曼 | BLE+WiFi | AES(自研) | 中 | 高 | 封闭 | 自定义 |
| 凯迪仕 | BLE+WiFi | AES(自研) | 中 | 高 | 封闭 | 自定义 |
| 鹿客 Loock | BLE+NB-IoT | Mi Service | 中 | 高 | 米家平台 | `0xFE95` |
| Lockly | BLE+WiFi | AES-128 | 中 | 中 | 封闭 | 自定义 |
| Ultraloq | BLE+WiFi | MD5有CVE | 低 | 中 | 部分 | 自定义 |

## 二、Service UUID 速查表

| Service UUID | Char UUID | 品牌/类型 | 用途 | 安全 |
|:------------|:----------|:---------|:-----|:---:|
| `0xFFE0` | `0xFFE1` | 廉价公模 | 密码写入 | 明文 |
| `0xFFF0` | `0xFFF1` 或自定义 | TTLock | 加密指令 | AES |
| `0xFE95` | `0x0001-0x0016` | 米家/鹿客 | Mi Service认证 | 安全芯片 |
| 自定义128-bit | 自定义 | Tuya | DP数据 | AES-256 |
| 自定义128-bit | 自定义 | August/Yale | 指令 | AES+TLS |
| 自定义128-bit | 自定义 | 德施曼/凯迪仕 | 自研指令 | AES |
| `0x180F` | `0x2A19` | 所有锁 | 电池电量 | 只读 |

## 三、TTLock 深度分析

**加密版本**：
- v1-v2：XOR+单字节混淆（实际就是明文）
- v3：AES-128-CBC（正式加密）

**配对方式**：JustWorks（无配对交互）

**API**：open.ttlock.com 提供全平台 SDK

**已知漏洞**：
- 协议降级攻击（Aleph Security 2024）：修改协商包协议版本号到 v2 即可切回 XOR
- AES 空解密攻击：设密文末字节为 0x01 让 AES 解密返回非零值
- MQTT Token 泄漏：部分网关 MQTT 无用户隔离

**开锁指令**：GATT Write to Char，指令体 AES-128-CBC 加密（v3+）

**钥匙机制**：每锁唯一 eKey，App 配对时生成下发到手机

**逆向关键点**：
- TTLock app 的 processCommandResponse 方法采用消息头的协议版本号而非信任本地存储的版本
- eKey 存在手机本地，逆向 App 可提取

## 四、米家 Mi Service 深度分析

**Service UUID**: `0xFE95`

**特征值表**：
| UUID | 大小 | 属性 | 说明 |
|:----|:---:|:----|:-----|
| `0x0001` | 12B | Write/Notify | Token |
| `0x0002` | 2B | Read | Product ID |
| `0x0004` | 10B | Read | Version |
| `0x0005` | 20B | Write/Notify | WiFi Config |
| `0x0010` | 4B | Write | Authentication |
| `0x0013` | 20B | Read/Write | Device ID |
| `0x0014` | 12B | Read | Beacon Key |
| `0x0016` | 20B | Write/Notify | Security Auth |

**加密安全**：
- v1.x：混淆算法（私有，不公开）
- v2.x：加密算法套件（部分开源）
- 每颗安全芯片有唯一私钥和证书

**已知漏洞/社区利用**：
- Char 0x0014 保存 Beacon Key，绑定后可提取
- Service Data(0xFE95)明文，Manufacturer Data(0x038F)加密
- 通过 xiaomi_ble 组件+beacon_key 可解密广播数据实现本地监控
- 新锁适配只需添加 PID 到设备列表

## 五、涂鸦 Tuya 加密详情

**加密方式**：AES-256-ECB + AES-128-ECB 双层

**流程**：
1. ticket_key 用 AES-256-ECB 解密（密钥=Access Secret）
2. 临时密码用 AES-128-ECB 加密（密钥=解密后的 ticket_key）

**开锁指令**：DP 协议，DP_ID 2 = 远程开锁

**常见芯片**：BK3633（博通）、FR801x（炬芯）

## 六、ESP32 通用扫描策略

```
1. 扫描所有 BLE 设备
2. 匹配 UUID 库 (0xFFE0/0xFFF0/0xFE95/自定义)
3. 设备名含 "Lock"/"Door"/"TTL"/"Mi" 辅助识别
4. 连接 -> Service Discovery -> 获取所有 UUID
5. 查协议数据库 -> 匹配解锁 Handler
```

## 七、开放项目参考

- ttlock-esp32-ble-gateway — TTLock ESP32 网关
- ESPHome Bluetooth Proxy — BLE 广播捕获（支持米家解密）
- ESP-IDF GATT Client — 官方 BLE 客户端例程
- Hackaday ESP32 Smart Lock — DIY 自制锁方案

## 八、信息来源

- open.ttlock.com
- alephsecurity.com/2024/03/07/kontrol-lux-lock-2
- bookstack.cn/read/miio_open/ble-Mi-Service.md
- developer.tuya.com
- bbs.hassbian.com/thread-25590-1-1.html
- secrss.com/articles/24972
- app.opencve.io/cve?vendor=ttlock
