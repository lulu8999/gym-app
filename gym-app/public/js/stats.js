// 数据统计页面逻辑
const statsPage = {
  // 图表实例
  frequencyChart: null,
  volumeChart: null,
  bodyPartsChart: null,

  // 当前时间范围
  currentPeriod: 30,

  init() {
    this.bindEvents();
    this.loadAllData();
  },

  bindEvents() {
    // 时间范围切换
    document.querySelectorAll('.period-tabs .tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.period-tabs .tab-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        this.currentPeriod = parseInt(e.target.dataset.period);
        this.loadAllData();
      });
    });
  },

  async loadAllData() {
    try {
      await Promise.all([
        this.loadOverview(),
        this.loadCalendar(),
        this.loadFrequency(),
        this.loadVolumeTrend(),
        this.loadBodyParts(),
        this.loadPRs()
      ]);
    } catch (error) {
      console.error('Load stats error:', error);
      utils.showToast('加载统计数据失败', 'error');
    }
  },

  // ==================== 总览统计 ====================
  async loadOverview() {
    try {
      const data = await api.get(`/stats/overview?period=${this.currentPeriod}`);

      document.getElementById('totalTrainings').textContent = data.total_trainings || 0;
      document.getElementById('totalDuration').textContent = utils.formatDuration(data.total_duration || 0);
      document.getElementById('totalVolume').textContent = utils.formatWeight(data.total_volume || 0);
      document.getElementById('streakDays').textContent = (data.streak_days || 0) + '天';
    } catch (error) {
      console.error('Load overview error:', error);
    }
  },

  // ==================== 训练日历热力图 ====================
  async loadCalendar() {
    try {
      const data = await api.get('/stats/calendar?days=90');
      const grid = document.getElementById('calendarGrid');
      const empty = document.getElementById('calendarEmpty');

      if (!data || !data.dates || data.dates.length === 0) {
        grid.innerHTML = '';
        grid.appendChild(empty);
        empty.style.display = 'flex';
        return;
      }

      // 构建日期映射
      const dateMap = {};
      data.dates.forEach(d => {
        dateMap[d.date] = d.count;
      });

      // 找出最大训练次数用于颜色分级
      const maxCount = Math.max(...Object.values(dateMap), 1);

      // 生成最近90天的日历
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const weeks = [];
      let currentWeek = [];

      // 从90天前开始，对齐到周日
      const startDate = new Date(today);
      startDate.setDate(startDate.getDate() - 89);
      // 回退到周日
      const dayOfWeek = startDate.getDay();
      startDate.setDate(startDate.getDate() - dayOfWeek);

      // 生成所有日期
      const allDates = [];
      const endDate = new Date(today);
      for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
        allDates.push(new Date(d));
      }

      // 按周分组
      allDates.forEach(d => {
        if (d.getDay() === 0 && currentWeek.length > 0) {
          weeks.push([...currentWeek]);
          currentWeek = [];
        }
        currentWeek.push(new Date(d));
      });
      if (currentWeek.length > 0) {
        weeks.push(currentWeek);
      }

      // 渲染日历
      let html = '<div class="calendar-wrapper">';
      html += '<div class="calendar-months">';

      // 月份标签
      const months = [];
      weeks.forEach(week => {
        week.forEach(d => {
          const mKey = `${d.getFullYear()}-${d.getMonth()}`;
          if (!months.includes(mKey)) {
            months.push(mKey);
          }
        });
      });

      html += '<div class="month-labels">';
      let lastMonth = -1;
      let lastYear = -1;
      allDates.forEach((d, i) => {
        if (d.getMonth() !== lastMonth || d.getFullYear() !== lastYear) {
          lastMonth = d.getMonth();
          lastYear = d.getFullYear();
          const monthNames = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
          html += `<span class="month-label" style="grid-column: ${Math.floor(i / 7) + 2}">${monthNames[lastMonth]}</span>`;
        }
      });
      html += '</div>';

      html += '<div class="calendar-cells">';
      // 星期标签
      const dayLabels = ['', '一', '', '三', '', '五', ''];
      for (let row = 0; row < 7; row++) {
        html += `<span class="day-label">${dayLabels[row]}</span>`;
        for (let col = 0; col < weeks.length; col++) {
          const day = weeks[col] && weeks[col][row];
          if (day && day <= today) {
            const dateStr = day.toISOString().split('T')[0];
            const count = dateMap[dateStr] || 0;
            let level = 0;
            if (count > 0) {
              level = Math.ceil((count / maxCount) * 3);
            }
            const title = `${dateStr}: ${count}次训练`;
            html += `<div class="cal-cell level-${level}" title="${title}" data-date="${dateStr}" data-count="${count}"></div>`;
          } else {
            html += '<div class="cal-cell empty-cell"></div>';
          }
        }
      }
      html += '</div>';

      html += '</div></div>';

      grid.innerHTML = html;
      empty.style.display = 'none';

    } catch (error) {
      console.error('Load calendar error:', error);
    }
  },

  // ==================== 训练频率趋势 ====================
  async loadFrequency() {
    try {
      const granularity = this.currentPeriod <= 30 ? 'day' : 'week';
      const data = await api.get(`/stats/frequency?period=${this.currentPeriod}&granularity=${granularity}`);

      const emptyEl = document.getElementById('frequencyEmpty');
      const canvas = document.getElementById('frequencyChart');

      if (!data || !data.labels || data.labels.length === 0) {
        emptyEl.style.display = 'flex';
        if (this.frequencyChart) { this.frequencyChart.destroy(); this.frequencyChart = null; }
        return;
      }

      emptyEl.style.display = 'none';

      if (this.frequencyChart) {
        this.frequencyChart.data.labels = data.labels;
        this.frequencyChart.data.datasets[0].data = data.values;
        this.frequencyChart.update();
        return;
      }

      const ctx = canvas.getContext('2d');
      this.frequencyChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [{
            label: '训练次数',
            data: data.values,
            borderColor: '#FF6B35',
            backgroundColor: 'rgba(255, 107, 53, 0.1)',
            borderWidth: 2.5,
            pointRadius: 4,
            pointBackgroundColor: '#FF6B35',
            pointBorderColor: '#1A1A2E',
            pointBorderWidth: 2,
            fill: true,
            tension: 0.3
          }]
        },
        options: this.getChartOptions('次')
      });
    } catch (error) {
      console.error('Load frequency error:', error);
    }
  },

  // ==================== 训练量趋势 ====================
  async loadVolumeTrend() {
    try {
      const granularity = this.currentPeriod <= 30 ? 'day' : 'week';
      const data = await api.get(`/stats/volume-trend?period=${this.currentPeriod}&granularity=${granularity}`);

      const emptyEl = document.getElementById('volumeEmpty');
      const canvas = document.getElementById('volumeChart');

      if (!data || !data.labels || data.labels.length === 0) {
        emptyEl.style.display = 'flex';
        if (this.volumeChart) { this.volumeChart.destroy(); this.volumeChart = null; }
        return;
      }

      emptyEl.style.display = 'none';

      if (this.volumeChart) {
        this.volumeChart.data.labels = data.labels;
        this.volumeChart.data.datasets[0].data = data.values;
        this.volumeChart.update();
        return;
      }

      const ctx = canvas.getContext('2d');
      this.volumeChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [{
            label: '训练量 (kg)',
            data: data.values,
            borderColor: '#4ECDC4',
            backgroundColor: 'rgba(78, 205, 196, 0.1)',
            borderWidth: 2.5,
            pointRadius: 4,
            pointBackgroundColor: '#4ECDC4',
            pointBorderColor: '#1A1A2E',
            pointBorderWidth: 2,
            fill: true,
            tension: 0.3
          }]
        },
        options: this.getChartOptions('kg')
      });
    } catch (error) {
      console.error('Load volume trend error:', error);
    }
  },

  // ==================== 部位统计 ====================
  async loadBodyParts() {
    try {
      const data = await api.get(`/stats/body-parts?period=${this.currentPeriod}`);

      const emptyEl = document.getElementById('bodyPartsEmpty');
      const canvas = document.getElementById('bodyPartsChart');

      if (!data || !data.labels || data.labels.length === 0) {
        emptyEl.style.display = 'flex';
        if (this.bodyPartsChart) { this.bodyPartsChart.destroy(); this.bodyPartsChart = null; }
        return;
      }

      emptyEl.style.display = 'none';

      // 部位颜色
      const partColors = {
        '胸': 'rgba(255, 107, 53, 0.85)',
        '背': 'rgba(78, 205, 196, 0.85)',
        '腿': 'rgba(155, 89, 182, 0.85)',
        '肩': 'rgba(46, 204, 113, 0.85)',
        '手臂': 'rgba(241, 196, 15, 0.85)',
        '核心': 'rgba(52, 152, 219, 0.85)'
      };

      const colors = data.labels.map(l => partColors[l] || 'rgba(255, 107, 53, 0.85)');
      const borderColors = data.labels.map(l => (partColors[l] || 'rgba(255, 107, 53, 1)').replace('0.85', '1'));

      if (this.bodyPartsChart) {
        this.bodyPartsChart.data.labels = data.labels;
        this.bodyPartsChart.data.datasets[0].data = data.values;
        this.bodyPartsChart.data.datasets[0].backgroundColor = colors;
        this.bodyPartsChart.data.datasets[0].borderColor = borderColors;
        this.bodyPartsChart.update();
        return;
      }

      const ctx = canvas.getContext('2d');
      this.bodyPartsChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: data.labels,
          datasets: [{
            label: '训练次数',
            data: data.values,
            backgroundColor: colors,
            borderColor: borderColors,
            borderWidth: 1.5,
            borderRadius: 6,
            borderSkipped: false
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          layout: { padding: { top: 10, right: 10, bottom: 0, left: 5 } },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: '#1A1A2E',
              titleColor: '#fff',
              bodyColor: '#FF6B35',
              borderColor: '#FF6B35',
              borderWidth: 1,
              cornerRadius: 8,
              callbacks: {
                label: (ctx) => `${ctx.parsed.y} 次训练`
              }
            }
          },
          scales: {
            x: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#888', font: { size: 13 } }
            },
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: {
                color: '#888',
                stepSize: 1,
                callback: v => v + '次'
              }
            }
          }
        }
      });
    } catch (error) {
      console.error('Load body parts error:', error);
    }
  },

  // ==================== 个人记录 ====================
  async loadPRs() {
    try {
      const data = await api.get('/stats/pr');
      const listEl = document.getElementById('prList');

      if (!data || data.length === 0) {
        listEl.innerHTML = `
          <div class="empty-state">
            <img src="/icons/trophy.svg" width="32" height="32" class="icon" alt="">
            <p>还没有个人记录</p>
            <p class="sub">完成训练后将显示你的最佳成绩</p>
          </div>
        `;
        return;
      }

      // 部位分组
      const grouped = {};
      data.forEach(item => {
        const cat = item.category || '其他';
        if (!grouped[cat]) grouped[cat] = [];
        grouped[cat].push(item);
      });

      let html = '';
      for (const [cat, items] of Object.entries(grouped)) {
        html += `<div class="pr-group">
          <div class="pr-group-title">${cat}</div>`;
        items.forEach(item => {
          html += `
          <div class="pr-item">
            <span class="pr-name">${item.name}</span>
            <span class="pr-value">${item.max_weight || 0} kg</span>
          </div>`;
        });
        html += '</div>';
      }

      listEl.innerHTML = html;
    } catch (error) {
      console.error('Load PRs error:', error);
    }
  },

  // 通用图表配置
  getChartOptions(unit) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 10, right: 10, bottom: 0, left: 5 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1A1A2E',
          titleColor: '#fff',
          borderColor: '#FF6B35',
          borderWidth: 1,
          cornerRadius: 8,
          callbacks: {
            label: (ctx) => `${ctx.parsed.y} ${unit}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#888', maxRotation: 45, font: { size: 11 } }
        },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: {
            color: '#888',
            callback: v => utils.formatNumber(v) + (v > 0 ? unit : '')
          }
        }
      }
    };
  }
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  statsPage.init();
});
