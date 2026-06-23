// 身体数据页面逻辑

const bodyPage = {
  weightChart: null,
  bodyFatChart: null,
  currentDays: 7,

  init() {
    this.bindEvents();
    this.loadData();
  },

  bindEvents() {
    // 保存按钮
    document.getElementById('saveBodyBtn').addEventListener('click', () => this.saveRecord());

    // 天数切换
    document.querySelectorAll('.chart-tabs .tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.chart-tabs .tab-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        this.currentDays = parseInt(e.target.dataset.days);
        this.loadChart();
      });
    });

    // 回车保存
    document.getElementById('noteInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.saveRecord();
    });
  },

  async loadData() {
    await Promise.all([this.loadChart(), this.loadHistory()]);
  },

  async saveRecord() {
    const weight = parseFloat(document.getElementById('weightInput').value);
    const bodyFat = parseFloat(document.getElementById('bodyFatInput').value) || null;
    const note = document.getElementById('noteInput').value.trim() || null;

    if (!weight || weight < 20 || weight > 300) {
      utils.showToast('请输入有效体重（20-300kg）', 'error');
      return;
    }

    try {
      const btn = document.getElementById('saveBodyBtn');
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';

      await api.post('/body', { weight, body_fat: bodyFat, note });

      utils.showToast('记录已保存 ✅', 'success');
      
      // 清空输入
      document.getElementById('weightInput').value = '';
      document.getElementById('bodyFatInput').value = '';
      document.getElementById('noteInput').value = '';

      // 刷新数据
      await this.loadData();
    } catch (error) {
      utils.showToast('保存失败：' + (error.message || '未知错误'), 'error');
    } finally {
      const btn = document.getElementById('saveBodyBtn');
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-check"></i> 保存记录';
    }
  },

  async loadChart() {
    try {
      const records = await api.get(`/body?limit=${this.currentDays}`);
      
      if (!records || records.length === 0) {
        document.getElementById('chartEmpty').style.display = 'flex';
        document.getElementById('bodyFatChartEmpty').style.display = 'flex';
        if (this.weightChart) { this.weightChart.destroy(); this.weightChart = null; }
        if (this.bodyFatChart) { this.bodyFatChart.destroy(); this.bodyFatChart = null; }
        return;
      }

      // 按日期升序排列
      const sorted = [...records].reverse();
      const labels = sorted.map(r => {
        const d = new Date(r.record_date);
        return `${d.getMonth() + 1}/${d.getDate()}`;
      });
      const weights = sorted.map(r => parseFloat(r.weight));
      const bodyFats = sorted.map(r => r.body_fat ? parseFloat(r.body_fat) : null);

      // 体重图
      this.renderWeightChart(labels, weights);
      
      // 体脂图
      const hasBodyFat = bodyFats.some(v => v !== null);
      if (hasBodyFat) {
        document.getElementById('bodyFatChartEmpty').style.display = 'none';
        this.renderBodyFatChart(labels, bodyFats);
      } else {
        document.getElementById('bodyFatChartEmpty').style.display = 'flex';
      }

    } catch (error) {
      console.error('Load chart error:', error);
    }
  },

  renderWeightChart(labels, data) {
    document.getElementById('chartEmpty').style.display = 'none';

    if (this.weightChart) {
      this.weightChart.data.labels = labels;
      this.weightChart.data.datasets[0].data = data;
      this.weightChart.update();
      return;
    }

    const ctx = document.getElementById('weightChart').getContext('2d');
    this.weightChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '体重 (kg)',
          data,
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
              label: (ctx) => `${ctx.parsed.y} kg`
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#888' }
          },
          y: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#888', callback: v => v.toFixed(1) + ' kg' },
            suggestedMin: Math.min(...data) - 1,
            suggestedMax: Math.max(...data) + 1
          }
        }
      }
    });
  },

  renderBodyFatChart(labels, data) {
    if (this.bodyFatChart) {
      this.bodyFatChart.data.labels = labels;
      this.bodyFatChart.data.datasets[0].data = data;
      this.bodyFatChart.update();
      return;
    }

    const ctx = document.getElementById('bodyFatChart').getContext('2d');
    this.bodyFatChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '体脂率 (%)',
          data,
          borderColor: '#4ECDC4',
          backgroundColor: 'rgba(78, 205, 196, 0.1)',
          borderWidth: 2.5,
          pointRadius: 4,
          pointBackgroundColor: '#4ECDC4',
          pointBorderColor: '#1A1A2E',
          pointBorderWidth: 2,
          fill: true,
          tension: 0.3,
          spanGaps: true
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
            bodyColor: '#4ECDC4',
            borderColor: '#4ECDC4',
            borderWidth: 1,
            cornerRadius: 8,
            callbacks: {
              label: (ctx) => ctx.parsed.y !== null ? `${ctx.parsed.y} %` : '未记录'
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#888' }
          },
          y: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#888', callback: v => v.toFixed(1) + '%' },
            suggestedMin: Math.min(...data.filter(v => v !== null)) - 1,
            suggestedMax: Math.max(...data.filter(v => v !== null)) + 1
          }
        }
      }
    });
  },

  async loadHistory() {
    try {
      const records = await api.get('/body?limit=50');
      const listEl = document.getElementById('historyList');

      if (!records || records.length === 0) {
        listEl.innerHTML = `
          <div class="empty-state">
            <i class="fas fa-weight"></i>
            <p>还没有记录</p>
            <p class="sub">每天记录一次，见证变化</p>
          </div>
        `;
        return;
      }

      listEl.innerHTML = records.map((r, i) => {
        const date = new Date(r.record_date);
        const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
        const prev = records[i + 1];
        let weightDiff = '';
        let diffClass = '';
        if (prev && r.weight && prev.weight) {
          const diff = (r.weight - prev.weight).toFixed(1);
          if (diff > 0) { weightDiff = `+${diff}`; diffClass = 'up'; }
          else if (diff < 0) { weightDiff = diff; diffClass = 'down'; }
          else { weightDiff = '0'; diffClass = 'same'; }
        }

        return `
          <div class="history-item">
            <div class="history-date">${dateStr}</div>
            <div class="history-data">
              <span class="weight-value">${r.weight ? r.weight + ' kg' : '-'}</span>
              ${weightDiff ? `<span class="weight-diff ${diffClass}">${weightDiff}</span>` : ''}
              ${r.body_fat ? `<span class="bodyfat-value">体脂 ${r.body_fat}%</span>` : ''}
            </div>
            ${r.note ? `<div class="history-note">${r.note}</div>` : ''}
          </div>
        `;
      }).join('');

    } catch (error) {
      console.error('Load history error:', error);
    }
  }
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  bodyPage.init();
});
