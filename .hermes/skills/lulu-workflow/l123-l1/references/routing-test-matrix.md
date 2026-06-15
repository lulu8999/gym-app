# L1 路由测试矩阵

修改 `routing.yaml` 或 `router.py` 后，用此矩阵验证未回归。

## 快速验证（一键全跑）

```bash
cd /root/l123 && python3 -c "
from agent.router import router
suite = [
    # (msg, 'intent'|'count'|'not_complex', expected)
    ('查天气','intent','simple'),('写篇文章','intent','creative'),
    ('写个Python脚本','intent','coding'),('爬豆瓣','intent','scraping'),
    ('部署网站','intent','deployment'),('做个方案','intent','creative'),
    ('查天气并写报告','count',2),('爬数据然后存数据库','count',2),
    ('部署网站再配置域名','count',2),('爬数据然后分析再写报告','count',3),
    ('查天气写报告','count',2),('查天气写报告部署网站','count',3),
    ('部署网站爬数据','not_complex',None),('然后呢','not_complex',None),
    ('并存方案','not_complex',None),('最后呢','not_complex',None),
    ('最后一步','not_complex',None),('啊','not_complex',None),
    ('部署名','not_complex',None),('安装饰','not_complex',None),
]
ok = 0
for msg, mode, exp in suite:
    r = router.route(msg)
    if mode == 'intent': c = r['intent'] == exp
    elif mode == 'count': c = r['type'] == 'complex' and r['count'] == exp
    else: c = r['type'] != 'complex'
    if c: ok += 1
    else: print(f'FAIL: \"{msg}\"')
print(f'{ok}/{len(suite)} 通过')
"
```

## 分类

### 1. 常规意图分类（20条）

| 消息 | 期望 | 注意 |
|:---|:---:|:---|
| 查天气 | simple | |
| 显示进程 | simple | |
| 打开文件 | simple | |
| 写篇文章 | creative | |
| 翻译 | creative | |
| 总结 | creative | |
| 润色 | creative | |
| 分析数据 | creative | |
| 做个方案 | creative | 方案→creative（关键修复） |
| 写个Python脚本 | coding | 之前误归creative，靠"写个脚本"修复 |
| 重构函数 | coding | |
| 加个登录功能 | coding | 之前归simple，靠"登录功能"修复 |
| 写代码 | coding | 之前没词，靠"写代码"修复 |
| 测试接口 | coding | |
| 爬豆瓣 | scraping | |
| 下载文件 | scraping | |
| 采集数据 | scraping | |
| 部署网站 | deployment | "网站"在scraping，但"部署"(len=2)同分优先 |
| 安装Nginx | deployment | |
| 配置数据库 | deployment | |

### 2. 连接词拆分（5条）

| 消息 | 步数 | 拆分 |
|:---|:---:|:---|
| 查天气并写报告 | 2 | 查天气 + 写报告 |
| 爬数据然后存数据库 | 2 | 爬数据 + 存数据库 |
| 部署网站再配置域名 | 2 | 部署网站 + 配置域名 |
| 部署最后写文档 | 2 | 部署 + 写文档 |
| 爬数据然后分析再写报告 | 3 | 爬数据 + 分析 + 写报告 |

### 3. 连写拆分（4条）

| 消息 | 步数 | 拆分 |
|:---|:---:|:---|
| 查天气写报告 | 2 | 查天气 + 写报告 |
| 查天气写报告部署网站 | 3 | 查天气 + 写报告 + 部署网站 |
| 查天气写报告部署网站爬数据 | 4 | 查天气 + 写报告 + 部署 + 网站爬数据 |
| 写报告部署网站爬数据 | 3 | 写报告 + 部署 + 网站爬数据 |

### 4. 短消息不误拆（4条）

| 消息 | 期望 | 原因 |
|:---|:---:|:---|
| 部署网站爬数据 | `<10字, 单任务` | 短消息不启用意图切换 |
| 爬数据存数据库 | `<10字, 单任务` | 同上 |
| 部署网站 | `<10字, 单任务` | 同上 |
| 写文章部署网站 | `>=10字, 按意图拆` | 10字边界, creative→deployment |

### 5. 连接词不误拆（5条）

| 消息 | 原因 | 关键逻辑 |
|:---|:---|---:|
| 然后呢 | "然后"是连接词但拆完1步→降级 | `_split_subtasks` 长度检测 |
| 最后呢 | "最后"同上 | 同上 |
| 最后一步 | "最后"同上 | 同上 |
| 并存方案 | "并"触发→但拆完1步 | 降级为creative（"方案"匹配） |
| 并发问题 | "并"触发→拆完1步 | 降级为simple |

### 6. 模糊/边缘（7条）

| 消息 | 期望 |
|:---|:---:|
| (空串) | simple |
| x | simple |
| 啊 | simple |
| 好 | simple |
| 做吧 | simple |
| hello | simple |
| 今天心情不错 | simple |

## 调试命令

```bash
# 查看路由结果
python3 -c "from agent.router import router; print(router.route('你的话'))"

# 查看路由的人类可读版
python3 -c "from agent.router import router; print(router.describe('你的话'))"

# 查看意图切换检测
python3 -c "from agent.router import router; print(router._detect_intent_shifts('你的话'))"

# 查看子任务拆分
python3 -c "from agent.router import router; print(router._split_subtasks('你的话'))"

# 查看关键词预处理
python3 -c "from agent.router import router; [print(f'{k}: {v[\"_prepared_keywords\"][:3]}...') for k,v in router.config['intent_types'].items() if v.get('keywords')]"
```