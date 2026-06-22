// 训炼 - 健身训练记录应用
// 完整功能版本

// API 基础地址
const API_BASE = '/api';

// 应用状态
const state = {
  user: null,
  trainings: [],
  exercises: [],
  plans: [],
  currentTraining: null,
  currentPage: 'home',
  isLoading: false
};

// ==================== 工具函数 ====================
const utils = {
  formatDate(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return '今天';
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return `${diffDays}天前`;
    
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  },
  
  formatDuration(seconds) {
    if (!seconds) return '0分钟';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 0) {
      return `${hours}小时${minutes > 0 ? minutes + '分钟' : ''}`;
    }
    return `${minutes}分钟`;
  },
  
  formatWeight(kg) {
    if (!kg) return '0kg';
    if (kg >= 1000) {
      return `${(kg / 1000).toFixed(1)}t`;
    }
    return `${Math.round(kg)}kg`;
  },
  
  formatNumber(num) {
    if (!num) return '0';
    if (num >= 10000) {
      return `${(num / 10000).toFixed(1)}w`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}k`;
    }
    return num.toString();
  },
  
  calcVolume(sets) {
    if (!sets || sets.length === 0) return 0;
    return sets.reduce((sum, set) => sum + (set.weight || 0) * (set.reps || 0), 0);
  },
  
  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 2000);
  },
  
  showModal(title, content) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').innerHTML = content;
    document.getElementById('modalOverlay').classList.add('show');
  },
  
  hideModal() {
    document.getElementById('modalOverlay').classList.remove('show');
  },
  
  showLoading() {
    state.isLoading = true;
    const loading = document.createElement('div');
    loading.className = 'loading-overlay';
    loading.innerHTML = '<div class="loading"></div>';
    document.body.appendChild(loading);
  },
  
  hideLoading() {
    state.isLoading = false;
    const loading = document.querySelector('.loading-overlay');
    if (loading) loading.remove();
  }
};

// ==================== API 请求封装 ====================
const api = {
  async get(url) {
    try {
      const response = await fetch(`${API_BASE}${url}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('API GET Error:', error);
      throw error;
    }
  },
  
  async post(url, data) {
    try {
      const response = await fetch(`${API_BASE}${url}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('API POST Error:', error);
      throw error;
    }
  },
  
  async put(url, data) {
    try {
      const response = await fetch(`${API_BASE}${url}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('API PUT Error:', error);
      throw error;
    }
  },
  
  async delete(url) {
    try {
      const response = await fetch(`${API_BASE}${url}`, { method: 'DELETE' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('API DELETE Error:', error);
      throw error;
    }
  }
};

// ==================== 路由系统 ====================
const router = {
  routes: {
    '/': 'home',
    '/training': 'training',
    '/training/new': 'trainingNew',
    '/exercises': 'exercises',
    '/stats': 'stats',
    '/profile': 'profile',
    '/plans': 'plans'
  },
  
  init() {
    window.addEventListener('popstate', () => this.handleRoute());
    
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a[href]');
      if (link && link.href.startsWith(window.location.origin)) {
        e.preventDefault();
        this.navigate(link.getAttribute('href'));
      }
    });
    
    this.handleRoute();
  },
  
  navigate(path) {
    window.history.pushState({}, '', path);
    this.handleRoute();
  },
  
  handleRoute() {
    const path = window.location.pathname;
    const page = this.routes[path] || 'home';
    
    state.currentPage = page;
    this.updateNav(page);
    this.renderPage(page);
  },
  
  updateNav(page) {
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.remove('active');
      if (item.dataset.page === page || 
          (page === 'trainingNew' && item.dataset.page === 'training')) {
        item.classList.add('active');
      }
    });
  },
  
  async renderPage(page) {
    const app = document.getElementById('app');
    
    switch (page) {
      case 'home':
        await this.renderHome(app);
        break;
      case 'training':
        await this.renderTraining(app);
        break;
      case 'trainingNew':
        await this.renderTrainingNew(app);
        break;
      case 'exercises':
        await this.renderExercises(app);
        break;
      case 'stats':
        await this.renderStats(app);
        break;
      case 'profile':
        await this.renderProfile(app);
        break;
      case 'plans':
        await this.renderPlans(app);
        break;
      default:
        await this.renderHome(app);
    }
  },
  
  // ==================== 首页 ====================
  async renderHome(app) {
    try {
      const [stats, trainings] = await Promise.all([
        api.get('/stats/weekly'),
        api.get('/trainings?limit=5')
      ]);
      
      const hasTraining = (stats.trainings || 0) > 0;
      
      app.innerHTML = `
        <!-- 开始训练按钮 -->
        <section class="hero-start">
          <button class="btn-start-hero" id="startTraining">
            <i class="fas fa-play"></i>
            <span>开始训练</span>
          </button>
        </section>

        <!-- 本周统计 -->
        <section class="stats-section">
          <h3 class="section-title">本周统计</h3>
          <div class="stats-row">
            <div class="stat-chip">
              <span class="stat-num">${stats.trainings || 0}</span>
              <span class="stat-unit">次</span>
            </div>
            <div class="stat-chip">
              <span class="stat-num">${stats.sets || 0}</span>
              <span class="stat-unit">组</span>
            </div>
            <div class="stat-chip">
              <span class="stat-num">${utils.formatDuration(stats.duration).replace('分钟','').replace('小时','h')}</span>
              <span class="stat-unit">时长</span>
            </div>
            <div class="stat-chip">
              <span class="stat-num">${utils.formatWeight(stats.volume)}</span>
              <span class="stat-unit">容量</span>
            </div>
          </div>
          ${!hasTraining ? '<p class="empty-hint">完成第一次训练，这里将展示你的数据 💪</p>' : ''}
        </section>

        <!-- 最近训练 -->
        <section class="recent-section">
          <div class="section-header">
            <h3 class="section-title">最近训练</h3>
            <a href="/training" class="link-more">查看全部 <i class="fas fa-chevron-right"></i></a>
          </div>
          <div class="training-list" id="trainingList">
            ${this.renderTrainingList(trainings)}
          </div>
        </section>

        <!-- 快捷入口 -->
        <section class="quick-actions">
          <h3 class="section-title">快捷入口</h3>
          <div class="action-grid">
            <a href="/exercises" class="action-item">
              <div class="action-icon"><i class="fas fa-dumbbell"></i></div>
              <span>动作库</span>
            </a>
            <a href="/plans" class="action-item">
              <div class="action-icon"><i class="fas fa-calendar-alt"></i></div>
              <span>训练计划</span>
            </a>
            <a href="/stats" class="action-item">
              <div class="action-icon"><i class="fas fa-chart-line"></i></div>
              <span>数据统计</span>
            </a>
            <a href="/profile" class="action-item">
              <div class="action-icon"><i class="fas fa-user"></i></div>
              <span>个人中心</span>
            </a>
          </div>
        </section>
      `;
      
      // 绑定开始训练按钮
      document.getElementById('startTraining')?.addEventListener('click', () => {
        router.navigate('/training/new');
      });
      
    } catch (error) {
      console.error('Load home error:', error);
      app.innerHTML = '<div class="error-state">加载失败，请刷新重试</div>';
    }
  },
  
  renderTrainingList(trainings) {
    if (!trainings || trainings.length === 0) {
      return `
        <div class="empty-state">
          <i class="fas fa-clipboard-list"></i>
          <p>还没有训练记录</p>
          <p class="sub">开始你的第一次训练吧！</p>
        </div>
      `;
    }
    
    return trainings.map(t => `
      <div class="training-item" data-id="${t.id}">
        <div class="training-header">
          <div class="training-type">
            <span class="type-badge">${t.training_type || '训练'}</span>
          </div>
          <div class="training-date">${utils.formatDate(t.start_time)}</div>
        </div>
        <div class="training-stats">
          <span><i class="fas fa-dumbbell"></i> ${t.exercise_count || 0}动作</span>
          <span><i class="fas fa-layer-group"></i> ${t.total_sets || 0}组</span>
          <span><i class="fas fa-clock"></i> ${utils.formatDuration(t.duration)}</span>
          <span><i class="fas fa-weight-hanging"></i> ${utils.formatWeight(t.total_volume)}</span>
        </div>
      </div>
    `).join('');
  },
  
  // ==================== 训练记录页面 ====================
  async renderTraining(app) {
    try {
      const trainings = await api.get('/trainings?limit=20');
      
      app.innerHTML = `
        <section class="page-header">
          <h2>训练记录</h2>
          <button class="btn-primary" id="newTraining">
            <i class="fas fa-plus"></i> 新建训练
          </button>
        </section>
        
        <section class="training-history">
          <div class="training-list" id="trainingListFull">
            ${this.renderTrainingList(trainings)}
          </div>
        </section>
      `;
      
      document.getElementById('newTraining')?.addEventListener('click', () => {
        router.navigate('/training/new');
      });
      
      // 绑定训练项点击事件
      document.querySelectorAll('.training-item').forEach(item => {
        item.addEventListener('click', async () => {
          const id = item.dataset.id;
          await this.showTrainingDetail(id);
        });
      });
      
    } catch (error) {
      console.error('Load training error:', error);
      app.innerHTML = '<div class="error-state">加载失败</div>';
    }
  },
  
  async showTrainingDetail(id) {
    try {
      const training = await api.get(`/trainings/${id}`);
      
      const setsHtml = training.sets?.map(set => `
        <tr>
          <td>${set.exercise_name}</td>
          <td>${set.set_order}</td>
          <td>${set.weight}kg</td>
          <td>${set.reps}</td>
          <td>${set.rpe || '-'}</td>
        </tr>
      `).join('') || '';
      
      utils.showModal('训练详情', `
        <div class="training-detail">
          <div class="detail-info">
            <p><strong>类型：</strong>${training.training_type || '训练'}</p>
            <p><strong>时长：</strong>${utils.formatDuration(training.duration)}</p>
            <p><strong>总容量：</strong>${utils.formatWeight(training.total_volume)}</p>
          </div>
          <table class="detail-table">
            <thead>
              <tr>
                <th>动作</th>
                <th>组</th>
                <th>重量</th>
                <th>次数</th>
                <th>RPE</th>
              </tr>
            </thead>
            <tbody>${setsHtml}</tbody>
          </table>
        </div>
      `);
    } catch (error) {
      utils.showToast('加载训练详情失败', 'error');
    }
  },
  
  // ==================== 新建训练页面 ====================
  async renderTrainingNew(app) {
    try {
      const exercises = await api.get('/exercises');
      
      // 按类别分组
      const grouped = {};
      exercises.forEach(ex => {
        if (!grouped[ex.category]) grouped[ex.category] = [];
        grouped[ex.category].push(ex);
      });
      
      app.innerHTML = `
        <section class="page-header">
          <button class="btn-back" onclick="router.navigate('/training')">
            <i class="fas fa-arrow-left"></i>
          </button>
          <h2>新建训练</h2>
          <button class="btn-primary" id="saveTraining">保存</button>
        </section>
        
        <section class="timer-section">
          <div class="timer-display">
            <i class="fas fa-stopwatch"></i>
            <span id="trainingTimer">00:00:00</span>
            <button id="timerToggle" class="btn-timer">
              <i class="fas fa-pause"></i>
            </button>
          </div>
        </section>
        
        <section class="new-training">
          <div class="form-group">
            <label>训练类型</label>
            <select id="trainingType" class="form-control">
              <option value="胸">胸</option>
              <option value="背">背</option>
              <option value="腿">腿</option>
              <option value="肩">肩</option>
              <option value="手臂">手臂</option>
              <option value="核心">核心</option>
              <option value="有氧">有氧</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>添加动作</label>
            <div class="exercise-selector">
              ${Object.keys(grouped).map(category => `
                <div class="exercise-category">
                  <h4 class="category-title">${category}</h4>
                  <div class="exercise-list">
                    ${grouped[category].map(ex => `
                      <button class="exercise-btn" data-id="${ex.id}" data-name="${ex.name}">
                        ${ex.name}
                      </button>
                    `).join('')}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
          
          <div class="form-group">
            <label>训练记录</label>
            <div id="trainingSets" class="training-sets">
              <div class="empty-state small">
                <p>选择动作后开始记录</p>
              </div>
            </div>
          </div>
        </section>
      `;
      
      // 绑定动作选择事件
      let selectedExercises = [];
      let currentSets = [];
      
      document.querySelectorAll('.exercise-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const id = btn.dataset.id;
          const name = btn.dataset.name;
          
          if (!selectedExercises.find(ex => ex.id === id)) {
            selectedExercises.push({ id, name });
            btn.classList.add('selected');
            this.updateSetsUI(selectedExercises, currentSets);
          }
        });
      });
      
      // 计时器逻辑
      let timerInterval = null;
      let timerSeconds = 0;
      let timerRunning = true;
      
      const timerDisplay = document.getElementById('trainingTimer');
      const timerToggle = document.getElementById('timerToggle');
      
      function updateTimerDisplay() {
        const hours = Math.floor(timerSeconds / 3600);
        const minutes = Math.floor((timerSeconds % 3600) / 60);
        const seconds = timerSeconds % 60;
        timerDisplay.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
      }
      
      function startTimer() {
        timerInterval = setInterval(() => {
          timerSeconds++;
          updateTimerDisplay();
        }, 1000);
        timerRunning = true;
        timerToggle.innerHTML = '<i class="fas fa-pause"></i>';
      }
      
      function pauseTimer() {
        clearInterval(timerInterval);
        timerRunning = false;
        timerToggle.innerHTML = '<i class="fas fa-play"></i>';
      }
      
      // 启动计时器
      startTimer();
      
      // 暂停/继续按钮
      timerToggle?.addEventListener('click', () => {
        if (timerRunning) {
          pauseTimer();
        } else {
          startTimer();
        }
      });
      
      // 绑定保存按钮
      document.getElementById('saveTraining')?.addEventListener('click', async () => {
        if (selectedExercises.length === 0) {
          utils.showToast('请至少选择一个动作', 'error');
          return;
        }
        
        try {
          utils.showLoading();
          
          // 创建训练记录
          const training = await api.post('/trainings', {
            training_type: document.getElementById('trainingType').value,
            duration: Math.floor(timerSeconds / 60)  // 转换为分钟
          });
          
          // 添加训练组
          for (const set of currentSets) {
            await api.post(`/trainings/${training.id}/sets`, set);
          }
          
          // 完成训练
          await api.post(`/trainings/${training.id}/complete`);
          
          utils.hideLoading();
          utils.showToast('训练已保存', 'success');
          router.navigate('/training');
          
        } catch (error) {
          utils.hideLoading();
          utils.showToast('保存失败', 'error');
        }
      });
      
    } catch (error) {
      console.error('Load new training error:', error);
      app.innerHTML = '<div class="error-state">加载失败</div>';
    }
  },
  
  updateSetsUI(exercises, sets) {
    const container = document.getElementById('trainingSets');
    if (!container) return;
    
    container.innerHTML = exercises.map(ex => {
      const exSets = sets.filter(s => s.exercise_id === ex.id);
      
      return `
        <div class="exercise-sets" data-exercise-id="${ex.id}">
          <div class="exercise-name">${ex.name}</div>
          ${exSets.map((set, idx) => `
            <div class="set-row">
              <span class="set-num">${idx + 1}</span>
              <input type="number" class="set-input" placeholder="重量" value="${set.weight || ''}" data-field="weight">
              <span class="set-unit">kg</span>
              <input type="number" class="set-input" placeholder="次数" value="${set.reps || ''}" data-field="reps">
              <input type="number" class="set-input small" placeholder="RPE" value="${set.rpe || ''}" data-field="rpe" step="0.5" min="1" max="10">
            </div>
          `).join('')}
          <button class="btn-add-set" data-exercise-id="${ex.id}">
            <i class="fas fa-plus"></i> 添加一组
          </button>
        </div>
      `;
    }).join('');
    
    // 绑定添加组按钮
    container.querySelectorAll('.btn-add-set').forEach(btn => {
      btn.addEventListener('click', () => {
        const exerciseId = btn.dataset.exerciseId;
        sets.push({
          exercise_id: exerciseId,
          set_order: sets.filter(s => s.exercise_id === exerciseId).length + 1,
          weight: 0,
          reps: 0,
          rpe: null
        });
        this.updateSetsUI(exercises, sets);
      });
    });
    
    // 绑定输入事件
    container.querySelectorAll('.set-input').forEach(input => {
      input.addEventListener('change', (e) => {
        const row = e.target.closest('.set-row');
        const exerciseId = row.closest('.exercise-sets').dataset.exerciseId;
        const setIndex = Array.from(row.parentElement.querySelectorAll('.set-row')).indexOf(row);
        const field = e.target.dataset.field;
        
        const matchingSets = sets.filter(s => s.exercise_id === exerciseId);
        if (matchingSets[setIndex]) {
          matchingSets[setIndex][field] = parseFloat(e.target.value) || 0;
        }
      });
    });
  },
  
  // ==================== 动作库页面 ====================
  async renderExercises(app) {
    try {
      const exercises = await api.get('/exercises');
      
      const grouped = {};
      exercises.forEach(ex => {
        if (!grouped[ex.category]) grouped[ex.category] = [];
        grouped[ex.category].push(ex);
      });
      
      app.innerHTML = `
        <section class="page-header">
          <h2>动作库</h2>
          <button class="btn-primary" id="addExercise">
            <i class="fas fa-plus"></i> 添加动作
          </button>
        </section>
        
        <section class="exercises-page">
          <div class="search-box">
            <i class="fas fa-search"></i>
            <input type="text" id="exerciseSearch" placeholder="搜索动作...">
          </div>
          
          <div class="exercise-categories" id="exerciseList">
            ${Object.keys(grouped).map(category => `
              <div class="category-section">
                <h3 class="category-header">${category}</h3>
                <div class="exercise-grid">
                  ${grouped[category].map(ex => `
                    <div class="exercise-card" data-id="${ex.id}">
                      <div class="exercise-icon">
                        <i class="fas fa-dumbbell"></i>
                      </div>
                      <div class="exercise-info">
                        <div class="exercise-name">${ex.name}</div>
                        <div class="exercise-muscle">${ex.muscle_group}</div>
                      </div>
                    </div>
                  `).join('')}
                </div>
              </div>
            `).join('')}
          </div>
        </section>
      `;
      
      // 搜索功能
      document.getElementById('exerciseSearch')?.addEventListener('input', (e) => {
        const keyword = e.target.value.toLowerCase();
        document.querySelectorAll('.exercise-card').forEach(card => {
          const name = card.querySelector('.exercise-name').textContent.toLowerCase();
          card.style.display = name.includes(keyword) ? '' : 'none';
        });
      });
      
      // 添加动作
      document.getElementById('addExercise')?.addEventListener('click', () => {
        this.showAddExerciseModal();
      });
      
      // 动作详情
      document.querySelectorAll('.exercise-card').forEach(card => {
        card.addEventListener('click', async () => {
          await this.showExerciseDetail(card.dataset.id);
        });
      });
      
    } catch (error) {
      console.error('Load exercises error:', error);
      app.innerHTML = '<div class="error-state">加载失败</div>';
    }
  },
  
  showAddExerciseModal() {
    utils.showModal('添加自定义动作', `
      <div class="form-group">
        <label>动作名称</label>
        <input type="text" id="newExerciseName" class="form-control" placeholder="如：杠铃弯举">
      </div>
      <div class="form-group">
        <label>部位分类</label>
        <select id="newExerciseCategory" class="form-control">
          <option value="胸">胸</option>
          <option value="背">背</option>
          <option value="腿">腿</option>
          <option value="肩">肩</option>
          <option value="手臂">手臂</option>
          <option value="核心">核心</option>
          <option value="有氧">有氧</option>
        </select>
      </div>
      <div class="form-group">
        <label>主要肌群</label>
        <input type="text" id="newExerciseMuscle" class="form-control" placeholder="如：肱二头肌">
      </div>
      <div class="form-group">
        <label>器械类型</label>
        <input type="text" id="newExerciseEquipment" class="form-control" placeholder="如：杠铃">
      </div>
      <button class="btn-primary full" id="saveExercise">保存动作</button>
    `);
    
    document.getElementById('saveExercise')?.addEventListener('click', async () => {
      const name = document.getElementById('newExerciseName').value;
      const category = document.getElementById('newExerciseCategory').value;
      const muscle_group = document.getElementById('newExerciseMuscle').value;
      const equipment = document.getElementById('newExerciseEquipment').value;
      
      if (!name) {
        utils.showToast('请输入动作名称', 'error');
        return;
      }
      
      try {
        await api.post('/exercises', { name, category, muscle_group, equipment });
        utils.hideModal();
        utils.showToast('动作已添加', 'success');
        router.renderPage('exercises');
      } catch (error) {
        utils.showToast('添加失败', 'error');
      }
    });
  },
  
  // 肌肉图解 - 使用 BodyMap 专业医学人体图
  getMuscleSVG(exercise) {
    return `<div id="bodyMapContainer" class="body-map-container"></div>`;
  },

  async showExerciseDetail(id) {
    try {
      const [exercise, records] = await Promise.all([
        api.get(`/exercises/${id}`),
        api.get(`/exercises/${id}/records?limit=10`)
      ]);
      
      const recordsHtml = records.map(r => `
        <tr>
          <td>${utils.formatDate(r.created_at)}</td>
          <td>${r.weight}kg</td>
          <td>${r.reps}</td>
          <td>${utils.formatWeight(r.volume)}</td>
        </tr>
      `).join('') || '<tr><td colspan="4">暂无记录</td></tr>';
      
      utils.showModal(exercise.name, `
        <div class="exercise-detail">
          <div class="exercise-illustration">
            ${this.getMuscleSVG(exercise)}
          </div>
          <div class="detail-info">
            <p><strong>部位：</strong>${exercise.category}</p>
            <p><strong>肌群：</strong>${exercise.muscle_group}</p>
            <p><strong>器械：</strong>${exercise.equipment}</p>
          </div>
          <h4>最近记录</h4>
          <table class="detail-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>重量</th>
                <th>次数</th>
                <th>容量</th>
              </tr>
            </thead>
            <tbody>${recordsHtml}</tbody>
          </table>
        </div>
      `);
      
      // 初始化 BodyMap 专业医学人体图
      setTimeout(() => {
        const container = document.getElementById('bodyMapContainer');
        if (container && typeof BodyMap !== 'undefined') {
          new BodyMap(container, {
            view: 'front',
            highlightCategory: exercise.category,
            highlightMuscle: exercise.muscle_group
          });
        }
      }, 50);
    } catch (error) {
      utils.showToast('加载详情失败', 'error');
    }
  },
  
  // ==================== 数据统计页面 ====================
  async renderStats(app) {
    try {
      const [stats, prs] = await Promise.all([
        api.get('/stats/weekly'),
        api.get('/stats/pr')
      ]);
      
      const prsHtml = prs.map(pr => `
        <tr>
          <td>${pr.name}</td>
          <td>${pr.max_weight}kg</td>
          <td>${utils.formatWeight(pr.max_volume)}</td>
        </tr>
      `).join('') || '<tr><td colspan="3">暂无记录</td></tr>';
      
      app.innerHTML = `
        <section class="page-header">
          <h2>数据统计</h2>
        </section>
        
        <section class="stats-page">
          <div class="stats-overview">
            <div class="stat-card">
              <div class="stat-icon large"><i class="fas fa-calendar-check"></i></div>
              <div class="stat-content">
                <div class="stat-value large">${stats.trainings || 0}</div>
                <div class="stat-label">本周训练</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon large"><i class="fas fa-layer-group"></i></div>
              <div class="stat-content">
                <div class="stat-value large">${stats.sets || 0}</div>
                <div class="stat-label">总组数</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon large"><i class="fas fa-clock"></i></div>
              <div class="stat-content">
                <div class="stat-value large">${utils.formatDuration(stats.duration)}</div>
                <div class="stat-label">训练时长</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon large"><i class="fas fa-weight-hanging"></i></div>
              <div class="stat-content">
                <div class="stat-value large">${utils.formatWeight(stats.volume)}</div>
                <div class="stat-label">总容量</div>
              </div>
            </div>
          </div>
          
          <div class="pr-section">
            <h3 class="section-title">个人记录 (PR)</h3>
            <table class="pr-table">
              <thead>
                <tr>
                  <th>动作</th>
                  <th>最大重量</th>
                  <th>最大容量</th>
                </tr>
              </thead>
              <tbody>${prsHtml}</tbody>
            </table>
          </div>
        </section>
      `;
      
    } catch (error) {
      console.error('Load stats error:', error);
      app.innerHTML = '<div class="error-state">加载失败</div>';
    }
  },
  
  // ==================== 个人中心页面 ====================
  async renderProfile(app) {
    app.innerHTML = `
      <section class="page-header">
        <h2>个人中心</h2>
      </section>
      
      <section class="profile-page">
        <div class="profile-card">
          <div class="avatar">
            <i class="fas fa-user"></i>
          </div>
          <div class="profile-info">
            <h3>健身爱好者</h3>
            <p>坚持训练，见证进步</p>
          </div>
        </div>
        
        <div class="menu-list">
          <div class="menu-item" id="bodyData">
            <i class="fas fa-weight"></i>
            <span>记录身体数据</span>
            <i class="fas fa-chevron-right"></i>
          </div>
          <div class="menu-item" id="bodyHistory">
            <i class="fas fa-chart-line"></i>
            <span>身体数据趋势</span>
            <i class="fas fa-chevron-right"></i>
          </div>
          <div class="menu-item" id="exportData">
            <i class="fas fa-file-export"></i>
            <span>导出数据</span>
            <i class="fas fa-chevron-right"></i>
          </div>
          <div class="menu-item" id="settings">
            <i class="fas fa-cog"></i>
            <span>设置</span>
            <i class="fas fa-chevron-right"></i>
          </div>
        </div>
      </section>
    `;
    
    // 绑定菜单事件
    document.getElementById('bodyData')?.addEventListener('click', () => {
      this.showBodyDataModal();
    });
    
    document.getElementById('bodyHistory')?.addEventListener('click', () => {
      this.showBodyHistory();
    });
    
    document.getElementById('exportData')?.addEventListener('click', () => {
      this.exportData();
    });
    
    document.getElementById('settings')?.addEventListener('click', () => {
      utils.showModal('设置', `
        <div class="form-group">
          <label>用户名</label>
          <input type="text" class="form-control" value="健身爱好者" id="settingsName">
        </div>
        <div class="form-group">
          <label>休息计时（秒）</label>
          <input type="number" class="form-control" value="90" id="settingsRest" min="30" max="300">
        </div>
        <button class="btn-primary full" id="saveSettings">保存设置</button>
      `);
      document.getElementById('saveSettings')?.addEventListener('click', () => {
        utils.hideModal();
        utils.showToast('设置已保存', 'success');
      });
    });
  },
  
  showBodyDataModal() {
    utils.showModal('记录身体数据', `
      <div class="form-group">
        <label>体重 (kg)</label>
        <input type="number" id="bodyWeight" class="form-control" step="0.1" placeholder="如：70.5">
      </div>
      <div class="form-group">
        <label>体脂率 (%)</label>
        <input type="number" id="bodyFat" class="form-control" step="0.1" placeholder="如：15.0">
      </div>
      <button class="btn-primary full" id="saveBodyData">保存</button>
    `);
    
    document.getElementById('saveBodyData')?.addEventListener('click', async () => {
      const weight = parseFloat(document.getElementById('bodyWeight').value);
      const body_fat = parseFloat(document.getElementById('bodyFat').value);
      
      if (!weight) {
        utils.showToast('请输入体重', 'error');
        return;
      }
      
      try {
        await api.post('/body', { weight, body_fat });
        utils.hideModal();
        utils.showToast('身体数据已记录', 'success');
      } catch (error) {
        utils.showToast('保存失败', 'error');
      }
    });
  },
  
  async exportData() {
    try {
      utils.showLoading();
      const trainings = await api.get('/trainings?limit=1000');
      
      // 生成 CSV
      let csv = '日期,类型,时长(秒),总组数,总容量(kg)\n';
      trainings.forEach(t => {
        csv += `${t.start_time},${t.training_type || ''},${t.duration || 0},${t.total_sets || 0},${t.total_volume || 0}\n`;
      });
      
      // 下载
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `训炼_训练记录_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      
      utils.hideLoading();
      utils.showToast('数据已导出', 'success');
    } catch (error) {
      utils.hideLoading();
      utils.showToast('导出失败', 'error');
    }
  },
  
  async showBodyHistory() {
    try {
      utils.showLoading();
      const records = await api.get('/body?limit=30');
      utils.hideLoading();
      
      if (records.length === 0) {
        utils.showToast('暂无身体数据记录', 'info');
        return;
      }
      
      // 生成表格 HTML
      let tableHtml = `
        <div class="body-history">
          <table class="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>体重 (kg)</th>
                <th>体脂率 (%)</th>
              </tr>
            </thead>
            <tbody>
      `;
      
      records.forEach(r => {
        const dateStr = r.record_date ? new Date(r.record_date).toLocaleDateString('zh-CN') : '-';
        tableHtml += `
          <tr>
            <td>${dateStr}</td>
            <td>${r.weight || '-'}</td>
            <td>${r.body_fat || '-'}</td>
          </tr>
        `;
      });
      
      tableHtml += `
            </tbody>
          </table>
        </div>
      `;
      
      utils.showModal('身体数据趋势', tableHtml);
    } catch (error) {
      utils.hideLoading();
      utils.showToast('获取数据失败', 'error');
    }
  },
  
  // ==================== 训练计划页面 ====================
  async renderPlans(app) {
    try {
      const plans = await api.get('/plans');
      
      app.innerHTML = `
        <section class="page-header">
          <h2>训练计划</h2>
          <button class="btn-primary" id="addPlan">
            <i class="fas fa-plus"></i> 创建计划
          </button>
        </section>
        
        <section class="plans-page">
          <div class="plans-list">
            ${plans.length > 0 ? plans.map(plan => `
              <div class="plan-card" data-id="${plan.id}">
                <div class="plan-icon">
                  <i class="fas fa-calendar-alt"></i>
                </div>
                <div class="plan-info">
                  <h3>${plan.name}</h3>
                  <p>${plan.description || '自定义计划'}</p>
                </div>
                <i class="fas fa-chevron-right"></i>
              </div>
            `).join('') : `
              <div class="empty-state">
                <i class="fas fa-calendar-alt"></i>
                <p>还没有训练计划</p>
                <p class="sub">创建一个计划，让训练更有规律</p>
              </div>
            `}
          </div>
          
          <div class="template-section">
            <h3 class="section-title">预设模板</h3>
            <div class="template-grid">
              <div class="template-card" data-template="ppl">
                <h4>PPL 推拉腿</h4>
                <p>推日/拉日/腿日</p>
              </div>
              <div class="template-card" data-template="upper-lower">
                <h4>上下肢分化</h4>
                <p>上肢A/下肢A/上肢B/下肢B</p>
              </div>
              <div class="template-card" data-template="5day">
                <h4>五分化</h4>
                <p>胸/背/肩/腿/手臂</p>
              </div>
            </div>
          </div>
        </section>
      `;
      
      // 创建计划
      document.getElementById('addPlan')?.addEventListener('click', () => {
        this.showCreatePlanModal();
      });
      
      // 使用模板
      document.querySelectorAll('.template-card').forEach(card => {
        card.addEventListener('click', () => {
          this.useTemplate(card.dataset.template);
        });
      });
      
    } catch (error) {
      console.error('Load plans error:', error);
      app.innerHTML = '<div class="error-state">加载失败</div>';
    }
  },
  
  showCreatePlanModal() {
    utils.showModal('创建训练计划', `
      <div class="form-group">
        <label>计划名称</label>
        <input type="text" id="planName" class="form-control" placeholder="如：我的PPL计划">
      </div>
      <div class="form-group">
        <label>计划描述</label>
        <textarea id="planDesc" class="form-control" placeholder="描述一下这个计划..."></textarea>
      </div>
      <button class="btn-primary full" id="savePlan">创建计划</button>
    `);
    
    document.getElementById('savePlan')?.addEventListener('click', async () => {
      const name = document.getElementById('planName').value;
      const description = document.getElementById('planDesc').value;
      
      if (!name) {
        utils.showToast('请输入计划名称', 'error');
        return;
      }
      
      try {
        await api.post('/plans', { name, description });
        utils.hideModal();
        utils.showToast('计划已创建', 'success');
        router.renderPage('plans');
      } catch (error) {
        utils.showToast('创建失败', 'error');
      }
    });
  },
  
  async useTemplate(template) {
    const templates = {
      'ppl': {
        name: 'PPL 推拉腿',
        description: '经典推拉腿分化训练',
        days: [
          { name: '推日', exercises: ['平板卧推', '上斜卧推', '哑铃推举', '侧平举', '三头绳索下压'] },
          { name: '拉日', exercises: ['引体向上', '杠铃划船', '高位下拉', '面拉', '杠铃弯举'] },
          { name: '腿日', exercises: ['深蹲', '腿举', '腿屈伸', '腿弯举', '小腿提踵'] }
        ]
      },
      'upper-lower': {
        name: '上下肢分化',
        description: '上下肢交替训练',
        days: [
          { name: '上肢A', exercises: ['平板卧推', '杠铃划船', '哑铃推举', '引体向上'] },
          { name: '下肢A', exercises: ['深蹲', '罗马尼亚硬拉', '腿举', '小腿提踵'] },
          { name: '上肢B', exercises: ['上斜卧推', '坐姿划船', '侧平举', '杠铃弯举'] },
          { name: '下肢B', exercises: ['前蹲', '硬拉', '腿屈伸', '腿弯举'] }
        ]
      },
      '5day': {
        name: '五分化',
        description: '胸背肩腿手臂五天分化',
        days: [
          { name: '胸日', exercises: ['平板卧推', '上斜卧推', '哑铃飞鸟', '龙门架夹胸'] },
          { name: '背日', exercises: ['引体向上', '杠铃划船', '高位下拉', '坐姿划船'] },
          { name: '肩日', exercises: ['哑铃推举', '侧平举', '面拉', '俯身飞鸟'] },
          { name: '腿日', exercises: ['深蹲', '腿举', '腿屈伸', '罗马尼亚硬拉'] },
          { name: '手臂日', exercises: ['杠铃弯举', '锤式弯举', '三头绳索下压', '碎颅者'] }
        ]
      }
    };
    
    const t = templates[template];
    if (!t) return;
    
    try {
      utils.showLoading();
      
      const plan = await api.post('/plans', {
        name: t.name,
        description: t.description
      });
      
      // 获取动作库
      const exercises = await api.get('/exercises');
      
      // 添加计划动作
      for (let day = 0; day < t.days.length; day++) {
        for (let order = 0; order < t.days[day].exercises.length; order++) {
          const exName = t.days[day].exercises[order];
          const ex = exercises.find(e => e.name === exName);
          
          if (ex) {
            await api.post(`/plans/${plan.id}/exercises`, {
              exercise_id: ex.id,
              day_order: day + 1,
              exercise_order: order + 1
            });
          }
        }
      }
      
      utils.hideLoading();
      utils.showToast('计划已创建', 'success');
      router.renderPage('plans');
      
    } catch (error) {
      utils.hideLoading();
      utils.showToast('创建失败', 'error');
    }
  }
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
  // 初始化路由
  router.init();
  
  // 主题切换
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      document.body.classList.toggle('light-theme');
      const icon = themeToggle.querySelector('i');
      icon.classList.toggle('fa-moon');
      icon.classList.toggle('fa-sun');
    });
  }
  
  // 模态框关闭
  document.getElementById('modalClose')?.addEventListener('click', () => {
    utils.hideModal();
  });
  
  document.getElementById('modalOverlay')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
      utils.hideModal();
    }
  });
});
