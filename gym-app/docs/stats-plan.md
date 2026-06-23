# 📊 健身应用 - 统计数据功能设计

## 一、功能概述

### 目标
为健身应用提供全面的数据统计和可视化功能，帮助用户：
- 追踪训练进度和趋势
- 发现训练规律和问题
- 激励持续训练

### 页面位置
新增 `stats.html` 页面，底部导航增加"统计"入口

---

## 二、数据维度设计

### 1. 总览统计（顶部卡片）
| 指标 | 说明 | 数据源 |
|------|------|--------|
| 总训练次数 | 所有训练记录数 | trainings |
| 总训练时长 | 累计训练时间 | trainings.duration |
| 总训练量 | 累计重量（kg） | trainings.total_volume |
| 平均每次时长 | 总时长/次数 | 计算值 |

### 2. 时间维度统计（图表）

#### 2.1 训练频率趋势（折线图）
- **X轴**: 最近30天/12周/12个月
- **Y轴**: 训练次数
- **切换**: 日/周/月视图
```sql
-- 按天统计
SELECT DATE(start_time) as date, COUNT(*) as count
FROM trainings
WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY DATE(start_time)
ORDER BY date;

-- 按周统计
SELECT YEAR(start_time) as year, WEEK(start_time) as week, COUNT(*) as count
FROM trainings
WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 12 WEEK)
GROUP BY YEAR(start_time), WEEK(start_time);

-- 按月统计
SELECT DATE_FORMAT(start_time, '%Y-%m') as month, COUNT(*) as count
FROM trainings
WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
GROUP BY DATE_FORMAT(start_time, '%Y-%m');
```

#### 2.2 训练量趋势（折线图）
- **X轴**: 时间
- **Y轴**: 总重量（kg）
- **切换**: 日/周/月视图

#### 2.3 训练时长趋势（折线图）
- **X轴**: 时间
- **Y轴**: 时长（分钟）

### 3. 部位/动作统计（柱状图/饼图）

#### 3.1 各部位训练次数（柱状图）
- **X轴**: 部位（胸/背/腿/肩/手臂/核心）
- **Y轴**: 训练次数
```sql
SELECT e.category, COUNT(DISTINCT ts.training_id) as count
FROM training_sets ts
JOIN exercises e ON ts.exercise_id = e.id
WHERE ts.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY e.category
ORDER BY count DESC;
```

#### 3.2 各部位训练量分布（饼图）
- 显示各部位训练量占比

#### 3.3 动作训练量排名（列表）
- Top 10 训练量最大的动作
```sql
SELECT e.name, e.category,
       SUM(ts.weight * ts.reps) as total_volume,
       COUNT(*) as total_sets
FROM training_sets ts
JOIN exercises e ON ts.exercise_id = e.id
GROUP BY e.id, e.name, e.category
ORDER BY total_volume DESC
LIMIT 10;
```

### 4. 身体数据趋势（折线图）

#### 4.1 体重变化
- **X轴**: 日期
- **Y轴**: 体重（kg）
- 支持选择时间范围：1个月/3个月/6个月/1年

#### 4.2 体脂率变化
- **X轴**: 日期
- **Y轴**: 体脂率（%）

### 5. 训练强度分析

#### 5.1 RPE 趋势（折线图）
- **X轴**: 时间
- **Y轴**: 平均 RPE
```sql
SELECT DATE(ts.created_at) as date,
       AVG(ts.rpe) as avg_rpe
FROM training_sets ts
WHERE ts.rpe IS NOT NULL
  AND ts.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY DATE(ts.created_at)
ORDER BY date;
```

#### 5.2 训练量强度分布（柱状图）
- 显示不同强度区间的训练量分布

### 6. 训练日历（热力图）
- 类似 GitHub 贡献日历
- 显示哪些天有训练，颜色深浅表示训练量
```sql
SELECT DATE(start_time) as date,
       COUNT(*) as count,
       SUM(total_volume) as volume
FROM trainings
WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
GROUP BY DATE(start_time);
```

### 7. 个人记录（PR）
- 各动作最大重量
- 各动作最大训练量（重量×次数）
- 历史 PR 变化

### 8. 对比分析

#### 8.1 周对比
- 本周 vs 上周：训练次数、训练量、时长

#### 8.2 月对比
- 本月 vs 上月：训练次数、训练量、时长

### 9. 训练计划执行统计
- 各计划使用次数
- 计划完成率

---

## 三、页面布局设计

### 页面结构
```
┌─────────────────────────────────┐
│           统计数据              │
├─────────────────────────────────┤
│  [总览卡片]                      │
│  ┌─────┬─────┬─────┬─────┐     │
│  │次数 │时长 │训练量│平均 │     │
│  └─────┴─────┴─────┴─────┘     │
├─────────────────────────────────┤
│  [时间范围选择]                  │
│  [7天] [30天] [90天] [1年]      │
├─────────────────────────────────┤
│  [图表区域]                      │
│  ┌─────────────────────────┐   │
│  │                         │   │
│  │    折线图/柱状图/饼图    │   │
│  │                         │   │
│  └─────────────────────────┘   │
├─────────────────────────────────┤
│  [训练日历]                      │
│  ┌─────────────────────────┐   │
│  │  热力图（90天）          │   │
│  └─────────────────────────┘   │
├─────────────────────────────────┤
│  [部位统计]                      │
│  ┌─────┬─────┐                 │
│  │柱状图│饼图 │                 │
│  └─────┴─────┘                 │
├─────────────────────────────────┤
│  [个人记录]                      │
│  ┌─────────────────────────┐   │
│  │  动作列表 + PR           │   │
│  └─────────────────────────┘   │
└─────────────────────────────────┘
│  首页  训练  动作  统计  身体  │
└─────────────────────────────────┘
```

### 图表库选择
推荐使用 **Chart.js**（已使用）：
- 折线图：训练频率、训练量趋势、身体数据
- 柱状图：部位统计、动作排名
- 饼图：部位分布

### 交互设计
1. **时间范围切换**：点击按钮切换 7天/30天/90天/1年
2. **图表类型切换**：点击 tab 切换不同统计维度
3. **下钻查看**：点击柱状图某项可查看详细数据

---

## 四、API 设计

### 4.1 总览统计
```
GET /api/stats/overview?period=30
```
**参数**：
- `period`: 天数（7/30/90/365）

**返回**：
```json
{
  "total_trainings": 45,
  "total_duration": 4050,
  "total_volume": 125000,
  "avg_duration": 90,
  "trainings_change": 20,
  "volume_change": 15
}
```

### 4.2 训练频率趋势
```
GET /api/stats/frequency?period=30&granularity=day
```
**参数**：
- `period`: 天数
- `granularity`: day/week/month

**返回**：
```json
[
  {"date": "2026-06-01", "count": 2},
  {"date": "2026-06-02", "count": 1},
  ...
]
```

### 4.3 训练量趋势
```
GET /api/stats/volume-trend?period=30&granularity=day
```

### 4.4 部位统计
```
GET /api/stats/body-parts?period=30
```
**返回**：
```json
[
  {"category": "胸", "count": 12, "volume": 35000},
  {"category": "背", "count": 10, "volume": 30000},
  ...
]
```

### 4.5 动作排名
```
GET /api/stats/exercise-ranking?period=30&limit=10
```

### 4.6 训练日历
```
GET /api/stats/calendar?days=90
```
**返回**：
```json
[
  {"date": "2026-06-01", "count": 2, "volume": 5000},
  ...
]
```

### 4.7 周/月对比
```
GET /api/stats/comparison?type=week
```

---

## 五、数据库优化（可选）

### 索引优化
```sql
-- 训练记录时间索引
CREATE INDEX idx_trainings_start_time ON trainings(start_time);

-- 训练组记录时间索引
CREATE INDEX idx_training_sets_created_at ON training_sets(created_at);
```

### 统计汇总表（可选，提升性能）
```sql
CREATE TABLE daily_stats (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT,
  stat_date DATE,
  training_count INT,
  total_duration INT,
  total_volume DECIMAL(10,2),
  total_sets INT,
  UNIQUE KEY (user_id, stat_date)
);
```

---

## 六、实现优先级

### P0（核心功能）
1. ✅ 总览统计卡片
2. ✅ 训练频率趋势图（折线图）
3. ✅ 训练量趋势图（折线图）
4. ✅ 部位统计（柱状图）
5. ✅ 个人记录列表

### P1（增强功能）
6. 训练日历热力图
7. 动作训练量排名
8. 身体数据趋势
9. 周/月对比

### P2（高级功能）
10. RPE 趋势分析
11. 训练计划执行统计
12. 训练强度分布

---

## 七、技术栈

### 前端
- **HTML/CSS/JS**（与现有项目一致）
- **Chart.js**（图表库，已使用）
- **暗夜科技风**配色（与身体数据页面一致）

### 后端
- **Express.js**（已有）
- **MySQL**（已有）

---

## 八、预计工作量

| 功能 | 工作量 | 说明 |
|------|--------|------|
| API 开发 | 3小时 | 5个核心 API |
| 页面布局 | 2小时 | HTML/CSS |
| 图表渲染 | 3小时 | Chart.js 配置 |
| 交互逻辑 | 2小时 | 时间切换、数据刷新 |
| 测试优化 | 1小时 | 边界情况处理 |
| **总计** | **11小时** | |

---

## 九、验收标准

1. ✅ 总览统计卡片显示正确数据
2. ✅ 时间范围切换正常（7天/30天/90天/1年）
3. ✅ 图表正确显示训练频率和训练量趋势
4. ✅ 部位统计图表正确
5. ✅ 个人记录列表正确
6. ✅ 页面在移动端正常显示
7. ✅ 无数据时显示空状态提示
8. ✅ 与现有设计风格一致（暗夜科技风）
