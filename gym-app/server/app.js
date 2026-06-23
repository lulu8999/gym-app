const express = require('express');
const cors = require('cors');
const path = require('path');
const mysql = require('mysql2/promise');

const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public'), {
  maxAge: 0,
  etag: false,
  lastModified: false,
  setHeaders: (res) => {
    res.set('Cache-Control', 'no-store, no-cache, must-revalidate');
    res.set('Pragma', 'no-cache');
    res.set('Expires', '0');
  }
}));
// 额外静态文件目录（根级别 public）
app.use(express.static(path.join(__dirname, '..', 'public'), {
  maxAge: 0,
  etag: false,
  lastModified: false,
  setHeaders: (res) => {
    res.set('Cache-Control', 'no-store, no-cache, must-revalidate');
    res.set('Pragma', 'no-cache');
    res.set('Expires', '0');
  }
}));

// 数据库连接池
const pool = mysql.createPool({
  host: process.env.DB_HOST || 'localhost',
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME || 'gym_app',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

// 测试数据库连接
app.get('/api/health', async (req, res) => {
  try {
    const [rows] = await pool.query('SELECT 1');
    res.json({ status: 'ok', database: 'connected' });
  } catch (error) {
    res.status(500).json({ status: 'error', message: error.message });
  }
});

// 用户相关 API
app.post('/api/auth/login', async (req, res) => {
  // 微信登录逻辑（后续实现）
  res.json({ message: '登录功能待实现' });
});

app.get('/api/user/profile', async (req, res) => {
  // 获取用户信息（后续实现）
  res.json({ message: '用户信息待实现' });
});

// 训练相关 API
app.get('/api/trainings', async (req, res) => {
  try {
    const { limit = 10, offset = 0 } = req.query;
    const [trainings] = await pool.query(
      `SELECT t.*, 
              COUNT(DISTINCT ts.exercise_id) as exercise_count,
              COUNT(ts.id) as total_sets
       FROM trainings t
       LEFT JOIN training_sets ts ON t.id = ts.training_id
       GROUP BY t.id
       ORDER BY t.start_time DESC
       LIMIT ? OFFSET ?`,
      [parseInt(limit), parseInt(offset)]
    );
    res.json(trainings);
  } catch (error) {
    console.error('Get trainings error:', error);
    res.status(500).json({ error: '获取训练记录失败' });
  }
});

app.get('/api/trainings/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    // 获取训练基本信息
    const [trainings] = await pool.query(
      'SELECT * FROM trainings WHERE id = ?',
      [id]
    );
    
    if (trainings.length === 0) {
      return res.status(404).json({ error: '训练记录不存在' });
    }
    
    const training = trainings[0];
    
    // 获取训练组详情
    const [sets] = await pool.query(
      `SELECT ts.*, e.name as exercise_name, e.category
       FROM training_sets ts
       JOIN exercises e ON ts.exercise_id = e.id
       WHERE ts.training_id = ?
       ORDER BY ts.exercise_id, ts.set_order`,
      [id]
    );
    
    training.sets = sets;
    res.json(training);
  } catch (error) {
    console.error('Get training detail error:', error);
    res.status(500).json({ error: '获取训练详情失败' });
  }
});

app.post('/api/trainings', async (req, res) => {
  try {
    const { training_type, note } = req.body;
    
    const [result] = await pool.query(
      `INSERT INTO trainings (user_id, training_type, start_time, note)
       VALUES (1, ?, NOW(), ?)`,
      [training_type, note]
    );
    
    res.json({ id: result.insertId, message: '训练已创建' });
  } catch (error) {
    console.error('Create training error:', error);
    res.status(500).json({ error: '创建训练失败' });
  }
});

app.post('/api/trainings/:id/complete', async (req, res) => {
  try {
    const { id } = req.params;
    
    // 计算总容量和总组数
    const [stats] = await pool.query(
      `SELECT 
         COUNT(*) as total_sets,
         COALESCE(SUM(weight * reps), 0) as total_volume
       FROM training_sets
       WHERE training_id = ?`,
      [id]
    );
    
    // 更新训练记录
    await pool.query(
      `UPDATE trainings 
       SET end_time = NOW(),
           duration = TIMESTAMPDIFF(SECOND, start_time, NOW()),
           total_sets = ?,
           total_volume = ?
       WHERE id = ?`,
      [stats[0].total_sets, stats[0].total_volume, id]
    );
    
    res.json({ message: '训练已完成' });
  } catch (error) {
    console.error('Complete training error:', error);
    res.status(500).json({ error: '完成训练失败' });
  }
});

// 训练组相关 API
app.post('/api/trainings/:id/sets', async (req, res) => {
  try {
    const { id } = req.params;
    const { exercise_id, set_order, weight, reps, rpe, note } = req.body;
    
    const [result] = await pool.query(
      `INSERT INTO training_sets (training_id, exercise_id, set_order, weight, reps, rpe, note)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [id, exercise_id, set_order, weight, reps, rpe, note]
    );
    
    res.json({ id: result.insertId, message: '训练组已添加' });
  } catch (error) {
    console.error('Add set error:', error);
    res.status(500).json({ error: '添加训练组失败' });
  }
});

app.put('/api/sets/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { weight, reps, rpe, note } = req.body;
    
    await pool.query(
      `UPDATE training_sets 
       SET weight = ?, reps = ?, rpe = ?, note = ?
       WHERE id = ?`,
      [weight, reps, rpe, note, id]
    );
    
    res.json({ message: '训练组已更新' });
  } catch (error) {
    console.error('Update set error:', error);
    res.status(500).json({ error: '更新训练组失败' });
  }
});

app.delete('/api/sets/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    await pool.query('DELETE FROM training_sets WHERE id = ?', [id]);
    
    res.json({ message: '训练组已删除' });
  } catch (error) {
    console.error('Delete set error:', error);
    res.status(500).json({ error: '删除训练组失败' });
  }
});

// 动作相关 API
app.get('/api/exercises', async (req, res) => {
  try {
    const { category, search } = req.query;
    
    let query = 'SELECT * FROM exercises WHERE 1=1';
    const params = [];
    
    if (category) {
      query += ' AND category = ?';
      params.push(category);
    }
    
    if (search) {
      query += ' AND name LIKE ?';
      params.push(`%${search}%`);
    }
    
    query += ' ORDER BY category, name';
    
    const [exercises] = await pool.query(query, params);
    res.json(exercises);
  } catch (error) {
    console.error('Get exercises error:', error);
    res.status(500).json({ error: '获取动作列表失败' });
  }
});

app.get('/api/exercises/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    const [exercises] = await pool.query(
      'SELECT * FROM exercises WHERE id = ?',
      [id]
    );
    
    if (exercises.length === 0) {
      return res.status(404).json({ error: '动作不存在' });
    }
    
    res.json(exercises[0]);
  } catch (error) {
    console.error('Get exercise error:', error);
    res.status(500).json({ error: '获取动作详情失败' });
  }
});

app.get('/api/exercises/:id/records', async (req, res) => {
  try {
    const { id } = req.params;
    const { limit = 10 } = req.query;
    
    const [records] = await pool.query(
      `SELECT ts.weight, ts.reps, ts.created_at,
              (ts.weight * ts.reps) as volume
       FROM training_sets ts
       WHERE ts.exercise_id = ?
       ORDER BY ts.created_at DESC
       LIMIT ?`,
      [id, parseInt(limit)]
    );
    
    res.json(records);
  } catch (error) {
    console.error('Get exercise records error:', error);
    res.status(500).json({ error: '获取动作记录失败' });
  }
});

app.post('/api/exercises', async (req, res) => {
  try {
    const { name, category, muscle_group, equipment, is_compound } = req.body;
    
    const [result] = await pool.query(
      `INSERT INTO exercises (user_id, name, category, muscle_group, equipment, is_compound)
       VALUES (1, ?, ?, ?, ?, ?)`,
      [name, category, muscle_group, equipment, is_compound || false]
    );
    
    res.json({ id: result.insertId, message: '动作已添加' });
  } catch (error) {
    console.error('Add exercise error:', error);
    res.status(500).json({ error: '添加动作失败' });
  }
});

// 统计相关 API
app.get('/api/stats/weekly', async (req, res) => {
  try {
    const [stats] = await pool.query(
      `SELECT 
         COUNT(DISTINCT t.id) as trainings,
         COALESCE(SUM(t.total_sets), 0) as sets,
         COALESCE(SUM(t.duration), 0) as duration,
         COALESCE(SUM(t.total_volume), 0) as volume
       FROM trainings t
       WHERE t.start_time >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)`
    );
    
    res.json(stats[0]);
  } catch (error) {
    console.error('Get weekly stats error:', error);
    res.status(500).json({ error: '获取周统计失败' });
  }
});

// 总览统计
app.get('/api/stats/overview', async (req, res) => {
  try {
    const { period = 30 } = req.query;
    const days = parseInt(period);

    const [result] = await pool.query(
      `SELECT 
         COUNT(DISTINCT t.id) as total_trainings,
         COALESCE(SUM(t.duration), 0) as total_duration,
         COALESCE(SUM(t.total_volume), 0) as total_volume,
         COUNT(DISTINCT DATE(t.start_time)) as active_days
       FROM trainings t
       WHERE t.start_time >= DATE_SUB(CURDATE(), INTERVAL ? DAY)`,
      [days]
    );

    // 计算连续训练天数
    const [streakResult] = await pool.query(
      `SELECT DISTINCT DATE(start_time) as train_date
       FROM trainings
       WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
       ORDER BY train_date DESC`
    );

    let streakDays = 0;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const checkDate = new Date(today);

    // 如果今天还没训练，从昨天开始算
    const hasToday = streakResult.some(r => {
      const d = new Date(r.train_date);
      return d.toDateString() === today.toDateString();
    });

    if (!hasToday) {
      checkDate.setDate(checkDate.getDate() - 1);
    }

    const dateSet = new Set(streakResult.map(r => {
      const d = new Date(r.train_date);
      return d.toDateString();
    }));

    for (let i = 0; i < 90; i++) {
      if (dateSet.has(checkDate.toDateString())) {
        streakDays++;
        checkDate.setDate(checkDate.getDate() - 1);
      } else {
        break;
      }
    }

    res.json({
      ...result[0],
      streak_days: streakDays
    });
  } catch (error) {
    console.error('Get overview error:', error);
    res.status(500).json({ error: '获取总览统计失败' });
  }
});

// 训练日历
app.get('/api/stats/calendar', async (req, res) => {
  try {
    const { days = 90 } = req.query;
    const limit = parseInt(days);

    const [rows] = await pool.query(
      `SELECT DATE(start_time) as date, COUNT(*) as count
       FROM trainings
       WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL ? DAY)
       GROUP BY DATE(start_time)
       ORDER BY date ASC`,
      [limit]
    );

    res.json({ dates: rows });
  } catch (error) {
    console.error('Get calendar error:', error);
    res.status(500).json({ error: '获取训练日历失败' });
  }
});

// 训练频率趋势
app.get('/api/stats/frequency', async (req, res) => {
  try {
    const { period = 30, granularity = 'day' } = req.query;
    const days = parseInt(period);

    let dateFormat, labelFormat;
    if (granularity === 'week') {
      dateFormat = '%Y-%u';  // year-week
      labelFormat = 'DATE_FORMAT(DATE(start_time), "%Y年第%u周")';
    } else {
      dateFormat = '%Y-%m-%d';
      labelFormat = "DATE_FORMAT(DATE(start_time), '%m/%d')";
    }

    const [rows] = await pool.query(
      `SELECT ${labelFormat} as label, COUNT(*) as count, MIN(DATE(start_time)) as sort_date
       FROM trainings
       WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL ? DAY)
       GROUP BY label
       ORDER BY sort_date ASC`,
      [days]
    );

    res.json({
      labels: rows.map(r => r.label),
      values: rows.map(r => r.count)
    });
  } catch (error) {
    console.error('Get frequency error:', error);
    res.status(500).json({ error: '获取训练频率失败' });
  }
});

// 训练量趋势
app.get('/api/stats/volume-trend', async (req, res) => {
  try {
    const { period = 30, granularity = 'day' } = req.query;
    const days = parseInt(period);

    let dateFormat, labelFormat;
    if (granularity === 'week') {
      labelFormat = "DATE_FORMAT(DATE(start_time), '%Y年第%u周')";
    } else {
      labelFormat = "DATE_FORMAT(DATE(start_time), '%m/%d')";
    }

    const [rows] = await pool.query(
      `SELECT ${labelFormat} as label, 
              COALESCE(SUM(total_volume), 0) as volume,
              MIN(DATE(start_time)) as sort_date
       FROM trainings
       WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL ? DAY)
       GROUP BY label
       ORDER BY sort_date ASC`,
      [days]
    );

    res.json({
      labels: rows.map(r => r.label),
      values: rows.map(r => Math.round(r.volume))
    });
  } catch (error) {
    console.error('Get volume trend error:', error);
    res.status(500).json({ error: '获取训练量趋势失败' });
  }
});

// 部位统计
app.get('/api/stats/body-parts', async (req, res) => {
  try {
    const { period = 30 } = req.query;
    const days = parseInt(period);

    // 部位映射：training_type -> muscle group
    const [rows] = await pool.query(
      `SELECT 
         CASE 
           WHEN t.training_type IN ('chest', '胸', 'chest_triceps', 'push') THEN '胸'
           WHEN t.training_type IN ('back', '背', 'back_biceps', 'pull') THEN '背'
           WHEN t.training_type IN ('leg', '腿', 'legs', 'lower') THEN '腿'
           WHEN t.training_type IN ('shoulder', '肩', 'shoulders', 'shoulders_arms', 'upper') THEN '肩'
           WHEN t.training_type IN ('arm', '手臂', 'arms') THEN '手臂'
           WHEN t.training_type IN ('core', '核心', 'abs') THEN '核心'
           ELSE '其他'
         END as body_part,
         COUNT(*) as count
       FROM trainings t
       WHERE t.start_time >= DATE_SUB(CURDATE(), INTERVAL ? DAY)
       GROUP BY body_part
       HAVING body_part != '其他'
       ORDER BY count DESC`,
      [days]
    );

    // 确保所有部位都有（即使为0）
    const allParts = ['胸', '背', '腿', '肩', '手臂', '核心'];
    const countMap = {};
    rows.forEach(r => { countMap[r.body_part] = r.count; });

    const labels = allParts;
    const values = allParts.map(p => countMap[p] || 0);

    // 也统计训练组中的部位（更精确）
    const [setRows] = await pool.query(
      `SELECT e.category, COUNT(DISTINCT ts.training_id) as count
       FROM training_sets ts
       JOIN exercises e ON ts.exercise_id = e.id
       JOIN trainings t ON ts.training_id = t.id
       WHERE t.start_time >= DATE_SUB(CURDATE(), INTERVAL ? DAY)
         AND e.category IN ('胸', '背', '腿', '肩', '手臂', '核心')
       GROUP BY e.category`,
      [days]
    );

    // 如果训练组数据更丰富，优先使用
    if (setRows.length > 0) {
      const setMap = {};
      setRows.forEach(r => { setMap[r.category] = r.count; });
      // 合并两种数据源
      allParts.forEach((p, i) => {
        if (setMap[p]) {
          values[i] = Math.max(values[i], setMap[p]);
        }
      });
    }

    res.json({ labels, values });
  } catch (error) {
    console.error('Get body parts error:', error);
    res.status(500).json({ error: '获取部位统计失败' });
  }
});

app.get('/api/stats/pr', async (req, res) => {
  try {
    const [prs] = await pool.query(
      `SELECT e.name, e.category,
              MAX(ts.weight) as max_weight,
              MAX(ts.weight * ts.reps) as max_volume
       FROM training_sets ts
       JOIN exercises e ON ts.exercise_id = e.id
       GROUP BY e.id, e.name, e.category
       HAVING max_weight > 0
       ORDER BY e.category, e.name`
    );
    
    res.json(prs);
  } catch (error) {
    console.error('Get PR error:', error);
    res.status(500).json({ error: '获取个人记录失败' });
  }
});

// 计划相关 API
app.get('/api/plans', async (req, res) => {
  try {
    const [plans] = await pool.query(
      'SELECT * FROM plans ORDER BY created_at DESC'
    );
    res.json(plans);
  } catch (error) {
    console.error('Get plans error:', error);
    res.status(500).json({ error: '获取计划列表失败' });
  }
});

app.post('/api/plans', async (req, res) => {
  try {
    const { name, description } = req.body;
    const user_id = 1; // 默认用户
    const [result] = await pool.query(
      'INSERT INTO plans (user_id, name, description) VALUES (?, ?, ?)',
      [user_id, name, description]
    );
    res.json({ id: result.insertId, name, description });
  } catch (error) {
    console.error('Create plan error:', error);
    res.status(500).json({ error: '创建计划失败' });
  }
});

app.post('/api/plans/:id/exercises', async (req, res) => {
  try {
    const { id } = req.params;
    const { exercise_id, day_order, exercise_order } = req.body;
    const [result] = await pool.query(
      'INSERT INTO plan_exercises (plan_id, exercise_id, day_order, exercise_order) VALUES (?, ?, ?, ?)',
      [id, exercise_id, day_order, exercise_order]
    );
    res.json({ id: result.insertId });
  } catch (error) {
    console.error('Add plan exercise error:', error);
    res.status(500).json({ error: '添加计划动作失败' });
  }
});

// 身体数据 API
app.post('/api/body', async (req, res) => {
  try {
    const { weight, body_fat, note } = req.body;
    const user_id = 1; // 默认用户
    const record_date = new Date().toISOString().split('T')[0]; // 今天日期
    const [result] = await pool.query(
      'INSERT INTO body_records (user_id, record_date, weight, body_fat, note) VALUES (?, ?, ?, ?, ?)',
      [user_id, record_date, weight, body_fat, note || null]
    );
    res.json({ id: result.insertId, weight, body_fat, record_date });
  } catch (error) {
    console.error('Save body data error:', error);
    res.status(500).json({ error: '保存身体数据失败' });
  }
});

app.get('/api/body', async (req, res) => {
  try {
    const { limit = 30 } = req.query;
    const [records] = await pool.query(
      'SELECT * FROM body_records ORDER BY record_date DESC LIMIT ?',
      [parseInt(limit)]
    );
    res.json(records);
  } catch (error) {
    console.error('Get body data error:', error);
    res.status(500).json({ error: '获取身体数据失败' });
  }
});

// 数据导出 API
app.get('/api/export/trainings', async (req, res) => {
  try {
    const { format = 'csv', days = 30 } = req.query;
    
    // 获取训练记录
    const [trainings] = await pool.query(
      `SELECT t.*, 
              COUNT(DISTINCT ts.exercise_id) as exercise_count,
              COUNT(ts.id) as total_sets,
              SUM(ts.weight * ts.reps) as total_volume
       FROM trainings t
       LEFT JOIN training_sets ts ON t.id = ts.training_id
       WHERE t.start_time >= DATE_SUB(NOW(), INTERVAL ? DAY)
       GROUP BY t.id
       ORDER BY t.start_time DESC`,
      [parseInt(days)]
    );
    
    // 获取每组详情
    const trainingIds = trainings.map(t => t.id);
    let sets = [];
    
    if (trainingIds.length > 0) {
      [sets] = await pool.query(
        `SELECT ts.*, e.name as exercise_name, e.category
         FROM training_sets ts
         JOIN exercises e ON ts.exercise_id = e.id
         WHERE ts.training_id IN (?)
         ORDER BY ts.training_id, ts.exercise_id, ts.set_order`,
        [trainingIds]
      );
    }
    
    // 按训练ID分组
    const setsByTraining = {};
    sets.forEach(s => {
      if (!setsByTraining[s.training_id]) {
        setsByTraining[s.training_id] = [];
      }
      setsByTraining[s.training_id].push(s);
    });
    
    if (format === 'json') {
      // JSON 格式
      const data = trainings.map(t => ({
        ...t,
        sets: setsByTraining[t.id] || []
      }));
      res.setHeader('Content-Type', 'application/json');
      res.setHeader('Content-Disposition', `attachment; filename=trainings_${days}d.json`);
      res.json(data);
    } else {
      // CSV 格式
      let csv = '训练ID,训练类型,开始时间,结束时间,时长(分钟),动作数,总组数,总容量(kg)\n';
      trainings.forEach(t => {
        const duration = t.end_time ? 
          Math.round((new Date(t.end_time) - new Date(t.start_time)) / 60000) : 0;
        csv += `${t.id},${t.type || '未分类'},${t.start_time},${t.end_time || ''},${duration},${t.exercise_count},${t.total_sets},${t.total_volume || 0}\n`;
      });
      
      csv += '\n详细记录:\n';
      csv += '训练ID,动作名称,类别,组数,重量(kg),次数,RPE\n';
      sets.forEach(s => {
        csv += `${s.training_id},${s.exercise_name},${s.category},${s.set_order},${s.weight},${s.reps},${s.rpe || ''}\n`;
      });
      
      res.setHeader('Content-Type', 'text/csv; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename=trainings_${days}d.csv`);
      res.send('\uFEFF' + csv); // 添加 BOM 支持中文
    }
  } catch (error) {
    console.error('Export trainings error:', error);
    res.status(500).json({ error: '导出训练记录失败' });
  }
});

// 前端路由支持（SPA）
// 显式路由映射
app.get('/stats', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'stats.html'));
});

app.get('/body', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'body.html'));
});

app.get('/exercises', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'exercises.html'));
});

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`🏋️ 训记服务器运行在 http://localhost:${PORT}`);
});

module.exports = app;
