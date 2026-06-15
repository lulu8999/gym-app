# 敏感数据场景部署模式（公安/法律助手系统）

适用于案件资料、个人隐私数据等敏感信息的部署架构。

## 核心原则

| 原则 | 说明 |
|------|------|
| 本地主存 | 敏感数据仅存储在 Mac 本地，绝不上云 |
| VPS 轻量化 | VPS 仅作为消息入口，无敏感数据 |
| 加密存储 | 数据库级加密（PostgreSQL + pgcrypto）|
| 双活灾备 | Mac 离线时 VPS 优雅降级，恢复后自动切回 |

## 架构图

```
用户访问
    ↓
VPS (公网入口)
├── 轻量 Gateway
├── 基础应答能力
├── 案件索引（仅元数据，无内容）
└── 健康检查/降级逻辑
    ↓ Tailscale 加密隧道
Mac Mini (内网核心)
├── PostgreSQL (案件数据库，加密)
├── 文档处理引擎 (Tika/LibreOffice)
├── 智能助手 (RAG/文书生成)
└── Hermes Gateway (主)
```

## 数据分类存储

| 数据类型 | Mac 本地 | VPS 备份 | 说明 |
|----------|:--------:|:----------:|------|
| 案件全文资料 | ✅ 主存储 | ❌ 不存储 | 绝对隔离 |
| 案件索引/元数据 | ✅ | ✅ 只传索引 | 应急时知道有什么，但看不到内容 |
| 助手配置/技能 | ✅ | ✅ 双向同步 | 保证灾备时助手可用 |
| 审计日志 | ✅ 主 | ✅ 备 | 操作追溯必要 |
| 非敏感数据 | 可选 | ✅ | 论文、企微备份等 |

## UPS 断电保护流程

```
UPS 电量 < 15%
    ↓
Mac 安全关机脚本：
  1. 锁定案件数据库
  2. 完成最后一次索引同步到 VPS
  3. 向 VPS 发送"进入降级模式"信号
  4. 安全关机

VPS 收到信号后：
  - 标记案件系统"不可用"
  - 进入降级模式（通用应答，无案件查询）

Mac 恢复后自动切回正常模式
```

## 数据库选型决策（PostgreSQL vs SQLite）

| 场景 | 推荐 | 原因 |
|------|------|------|
| 1 人使用 | SQLite | 单文件、备份简单 |
| 20 人并发 | PostgreSQL | 并发控制、用户权限、事务安全 |
| 中文全文检索 | PostgreSQL + pg_jieba | SQLite 中文分词弱 |
| 需要审计日志 | PostgreSQL | 原生支持 |
| 一步到位 | PostgreSQL | 避免日后迁移 |

## 中文文档处理方案

### 文件类型支持

| 类型 | 处理方式 | 用途 |
|------|----------|------|
| PDF | Apache Tika + OCR | 笔录、通知书 |
| Word (.docx) | python-docx | 起诉意见书、报告 |
| Excel (.xlsx) | openpyxl | 涉案财物清单 |
| 图片 | PaddleOCR/百度OCR | 现场照片、证件照 |

### 全文检索配置（PostgreSQL）

```sql
-- 安装中文分词插件
CREATE EXTENSION pg_jieba;

-- 创建全文检索索引（中文支持）
CREATE INDEX idx_case_content_fts ON cases 
USING GIN (to_tsvector('jiebacfg', content));

-- 查询示例：找涉及"盗窃"的案件
SELECT * FROM cases 
WHERE to_tsvector('jiebacfg', content) @@ to_tsquery('jiebacfg', '盗窃');
```

## 权限分级设计

| 角色 | 权限范围 | 适用场景 |
|:----:|----------|----------|
| 管理员 | 所有案件 + 用户管理 | 系统管理员 |
| 侦查员 | 自己经手案件 + 协查授权 | 主办民警 |
| 文职 | 文书录入 + 查询自己录入的案件 | 内勤、辅警 |
| 只读 | 查看指定案件，不能修改 | 领导、督查 |

### 案例隔离实现

```sql
-- 查询时自动过滤（行级安全）
CREATE POLICY case_access_policy ON cases
FOR SELECT
USING (
  -- 管理员看所有
  current_user_role = 'admin'
  OR
  -- 侦查员看自己的
  (current_user_role = 'investigator' AND handler_id = current_user_id())
  OR
  -- 协查授权
  EXISTS (SELECT 1 FROM case_shares WHERE case_id = id AND user_id = current_user_id())
);
```

## 推广策略建议

```
阶段1（0-3个月）：1人验证
  ├── 验证核心功能：文书生成、案件查询
  ├── 积累测试数据：20-50 个案件
  └── 打磨查询语法：如何描述需求最准确

阶段2（3-6个月）：+ 小范围
  ├── 1-2 名同事试用
  ├── 权限分级上线
  ├── 收集反馈优化中文分词
  └── 完善文书模板

阶段3（6-12个月）：5-10 人试点
  ├── Tailscale 组网
  ├── 并发压力测试
  └── 审计、备份机制完善

阶段4（12个月后）：正式推广 20 人
  ├── 部署指南 + 培训
  ├── 运维监控
  └── 持续迭代
```

## 安全检查清单

- [ ] PostgreSQL 启用 SSL 连接
- [ ] 数据库密码复杂度策略（Bitwarden 管理）
- [ ] 行级安全策略（RLS）配置
- [ ] 审计日志自动归档
- [ ] 定期备份脚本（加密备份）
- [ ] Tailscale ACL 策略（只允许授权设备访问）
- [ ] VPS 无敏感数据验证（定期扫描）
