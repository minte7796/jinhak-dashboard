// Dashboard JavaScript logic for 2027 수시모집 스마트 경쟁률

let ratioChart = null;
let autoRefreshTimer = null;
let isUpdating = false;

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initial data fetch on app start
  initDashboard();

  // 2. Set up auto-refresh listener
  const autoSelect = document.getElementById('autoRefreshSelect');
  if (autoSelect) {
    autoSelect.addEventListener('change', handleAutoRefreshChange);
    setupAutoRefresh(parseInt(autoSelect.value, 10));
  }
});

/**
 * Initializes the dashboard on startup.
 */
async function initDashboard() {
  await loadData(false);
}

/**
 * Loads competition data from the backend API.
 * @param {boolean} force - Whether to force a live scrape
 */
async function loadData(force = false) {
  setLoadingState(true);
  try {
    const url = force ? '/api/update' : '/api/ratios';
    const method = force ? 'POST' : 'GET';
    const resp = await fetch(url, { method });

    if (!resp.ok) {
      if (resp.status === 502 || resp.status === 503 || resp.status === 504) {
        showToast('클라우드 서버가 절전 모드에서 깨어나는 중입니다. 약 20~30초 후 다시 시도해 주세요.', 'info');
        return;
      }
      throw new Error(`HTTP ${resp.status}`);
    }

    const json = await resp.json();

    if (json.success && json.data) {
      renderDashboard(json.data);
      if (force) {
        showToast(json.message || '최신 경쟁률 데이터가 성공적으로 갱신되었습니다.', 'success');
      }
    } else {
      showToast(json.message || '데이터를 불러오지 못했습니다.', 'error');
    }
  } catch (err) {
    console.error('Data load error:', err);
    if (err.message && (err.message.includes('Failed to fetch') || err.message.includes('NetworkError'))) {
      showToast('서버 기동 중이거나 연결이 불안정합니다. 잠시 후 다시 시도해 주세요.', 'info');
    } else {
      showToast('데이터 갱신 중 일시적인 지연이 발생했습니다.', 'error');
    }
  } finally {
    setLoadingState(false);
  }
}

/**
 * Triggered when the user clicks "지금 업데이트"
 */
async function handleManualUpdate() {
  if (isUpdating) return;
  await loadData(true);
}

/**
 * Renders all components of the dashboard.
 */
function renderDashboard(data) {
  // Update Timestamp
  const lastSyncEl = document.getElementById('lastSyncedTime');
  if (lastSyncEl) {
    lastSyncEl.textContent = data.updated_at || new Date().toLocaleString();
  }

  // 1. Render Table (Now at Top)
  renderTable(data.items || []);

  // 2. Render Chart
  renderChart(data.items || []);

  // 3. Render University Cards Grid
  renderCardsGrid(data.items || []);
}

/**
 * Renders the 6 university cards.
 */
function renderCardsGrid(items) {
  const container = document.getElementById('cardsGrid');
  if (!container) return;

  if (items.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-8 text-center text-slate-400">
        조회된 대학 경쟁률 데이터가 없습니다.
      </div>
    `;
    return;
  }

  container.innerHTML = items.map((item, idx) => {
    const diffBadge = item.diff_applicants > 0
      ? `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 ml-1.5">▲ +${item.diff_applicants}</span>`
      : '';

    const ratioNum = item.ratio_num || 0;
    // Highlight colors based on ratio
    let ratioColor = 'text-slate-900';
    if (ratioNum >= 2.5) ratioColor = 'text-purple-700';
    else if (ratioNum >= 1.5) ratioColor = 'text-blue-700';

    return `
      <div class="univ-card bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm flex flex-col justify-between">
        <!-- Card Header -->
        <div class="p-4 border-b border-slate-100 bg-slate-50/50">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${item.color || '#4f46e5'}"></span>
              <h3 class="font-bold text-slate-900 text-base">${item.univ}</h3>
              ${item.campus ? `<span class="text-[11px] px-1.5 py-0.5 rounded bg-slate-200/70 text-slate-600 font-medium">${item.campus}</span>` : ''}
            </div>
            <span class="text-[11px] px-2 py-0.5 rounded-full font-medium ${item.badge_color || 'bg-slate-100 text-slate-700'}">
              ${item.system || '원서접수'}
            </span>
          </div>
          <div class="mt-2 text-xs font-semibold text-slate-600 flex items-center">
            <i class="fa-solid fa-graduation-cap mr-1.5 text-slate-400"></i>
            <span>${item.admission_type}</span>
          </div>
        </div>

        <!-- Card Body -->
        <div class="p-5 flex-1 flex flex-col justify-between space-y-4">
          <div>
            <div class="text-xs text-slate-500 mb-1">모집단위 / 학과</div>
            <div class="text-base font-bold text-slate-900 truncate" title="${item.major}">
              ${item.major}
            </div>
          </div>

          <!-- Highlighted Competition Ratio -->
          <div class="bg-slate-50 rounded-xl p-3.5 border border-slate-100 flex items-center justify-between">
            <div>
              <span class="text-xs font-medium text-slate-500">실시간 경쟁률</span>
              <div class="text-2xl font-black ${ratioColor} tracking-tight">
                ${item.ratio}
              </div>
            </div>
            <div class="text-right">
              <div class="text-xs font-medium text-slate-500">모집 / 지원</div>
              <div class="text-sm font-bold text-slate-800 mt-0.5">
                <span class="text-slate-500">${item.quota}명</span>
                <span class="text-slate-300 mx-1">/</span>
                <span class="text-indigo-600 font-bold">${item.applicants}명</span>
                ${diffBadge}
              </div>
            </div>
          </div>

          <!-- Official Last Update Time Badge -->
          <div class="${item.status === '정상' ? 'bg-amber-50/70 border-amber-200/80 text-amber-900' : 'bg-red-50/80 border-red-200 text-red-900'} border rounded-lg p-2.5 text-xs flex items-start space-x-2">
            <i class="fa-solid ${item.status === '정상' ? 'fa-clock text-amber-600' : 'fa-triangle-exclamation text-red-600'} mt-0.5"></i>
            <div class="flex-1 leading-tight">
              <span class="text-[11px] font-semibold block">${item.status === '정상' ? '대학별 최종 업데이트 시간' : '수집 상태'}</span>
              <span class="font-bold text-slate-900 font-mono text-[12px]">${item.update_time || '확인 중'}</span>
              ${item.status !== '정상' ? `<span class="block text-[10px] text-red-600 mt-0.5 font-sans">${item.status}</span>` : ''}
            </div>
          </div>
        </div>

        <!-- Card Footer / Redirect Link -->
        <div class="p-3 bg-slate-50 border-t border-slate-100">
          <a href="${item.ratio_url}" target="_blank" rel="noopener noreferrer" 
             class="w-full inline-flex items-center justify-center px-3.5 py-2 text-xs font-semibold rounded-lg text-slate-700 bg-white hover:bg-indigo-50 hover:text-indigo-600 border border-slate-200 hover:border-indigo-200 shadow-sm transition-all duration-150 group">
            <i class="fa-solid fa-arrow-up-right-from-square mr-1.5 text-slate-400 group-hover:text-indigo-500 transition-colors"></i>
            해당학교 경쟁률 바로가기
          </a>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Renders the tabular breakdown.
 */
function renderTable(items) {
  const tbody = document.getElementById('tableBody');
  if (!tbody) return;

  tbody.innerHTML = items.map(item => `
    <tr class="hover:bg-slate-50/80 transition-colors">
      <td class="py-3 px-4 font-bold text-slate-900 whitespace-nowrap">
        <div class="flex items-center space-x-2">
          <span class="w-2 h-2 rounded-full" style="background-color: ${item.color || '#6366f1'}"></span>
          <span>${item.univ}</span>
        </div>
      </td>
      <td class="py-3 px-4 text-slate-700 font-medium whitespace-nowrap">${item.admission_type}</td>
      <td class="py-3 px-4 font-semibold text-slate-900 whitespace-nowrap">${item.major}</td>
      <td class="py-3 px-3 text-right font-medium text-slate-600">${item.quota}명</td>
      <td class="py-3 px-3 text-right font-bold text-indigo-600">${item.applicants}명</td>
      <td class="py-3 px-4 text-right">
        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-900 border border-slate-200 font-mono">
          ${item.ratio}
        </span>
      </td>
      <td class="py-3 px-4 text-xs font-mono whitespace-nowrap">
        <span class="inline-flex items-center ${item.status === '정상' ? 'text-amber-900 bg-amber-50 border-amber-200' : 'text-red-900 bg-red-50 border-red-200'} px-2 py-1 rounded border">
          <i class="fa-regular ${item.status === '정상' ? 'fa-clock text-amber-600' : 'fa-triangle-exclamation text-red-600'} mr-1"></i>${item.update_time}
        </span>
      </td>
      <td class="py-3 px-4 text-center whitespace-nowrap">
        <a href="${item.ratio_url}" target="_blank" rel="noopener noreferrer" 
           class="inline-flex items-center px-2.5 py-1 text-xs font-semibold rounded text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 transition-colors">
          경쟁률 링크 <i class="fa-solid fa-arrow-up-right-from-square ml-1 text-[10px]"></i>
        </a>
      </td>
    </tr>
  `).join('');
}

/**
 * Renders or updates the Chart.js bar chart.
 */
function renderChart(items) {
  const canvas = document.getElementById('ratioComparisonChart');
  if (!canvas) return;

  const labels = items.map(it => `${it.univ} (${it.major})`);
  const ratioValues = items.map(it => it.ratio_num || 0);
  const colors = items.map(it => it.color || '#4f46e5');

  if (ratioChart) {
    ratioChart.data.labels = labels;
    ratioChart.data.datasets[0].data = ratioValues;
    ratioChart.data.datasets[0].backgroundColor = colors.map(c => c + 'cc');
    ratioChart.data.datasets[0].borderColor = colors;
    ratioChart.update();
    return;
  }

  const ctx = canvas.getContext('2d');
  ratioChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '경쟁률 ( : 1)',
        data: ratioValues,
        backgroundColor: colors.map(c => c + 'cc'),
        borderColor: colors,
        borderWidth: 1.5,
        borderRadius: 6,
        maxBarThickness: 45
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const item = items[context.dataIndex];
              return [
                `경쟁률: ${item.ratio}`,
                `모집인원: ${item.quota}명 | 지원인원: ${item.applicants}명`,
                `최종 업데이트: ${item.update_time}`
              ];
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: '경쟁률 ( : 1)',
            font: { size: 11, weight: 'bold' }
          },
          grid: {
            color: '#f1f5f9'
          }
        },
        x: {
          grid: {
            display: false
          },
          ticks: {
            font: { size: 11, weight: 'bold' }
          }
        }
      }
    }
  });
}

/**
 * Handles auto-refresh selection change.
 */
function handleAutoRefreshChange(e) {
  const seconds = parseInt(e.target.value, 10);
  setupAutoRefresh(seconds);
}

/**
 * Sets or clears the auto-refresh interval.
 */
function setupAutoRefresh(seconds) {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
  if (seconds > 0) {
    autoRefreshTimer = setInterval(() => {
      console.log(`[AutoRefresh] Updating data (${seconds}s interval)...`);
      loadData(true);
    }, seconds * 1000);
  }
}

/**
 * Controls loading states in UI.
 */
function setLoadingState(loading) {
  isUpdating = loading;
  const btn = document.getElementById('btnManualUpdate');
  const icon = document.getElementById('btnUpdateIcon');
  const text = document.getElementById('btnUpdateText');

  if (loading) {
    if (btn) btn.disabled = true;
    if (icon) icon.className = 'fa-solid fa-arrows-rotate fa-spin mr-1.5';
    if (text) text.textContent = '업데이트 중...';
  } else {
    if (btn) btn.disabled = false;
    if (icon) icon.className = 'fa-solid fa-arrows-rotate mr-1.5';
    if (text) text.textContent = '지금 업데이트';
  }
}

/**
 * Displays floating toast message.
 */
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  const bgClass = type === 'success' ? 'bg-emerald-600 text-white' : (type === 'error' ? 'bg-red-600 text-white' : 'bg-slate-800 text-white');
  const iconClass = type === 'success' ? 'fa-circle-check' : (type === 'error' ? 'fa-triangle-exclamation' : 'fa-circle-info');

  toast.className = `${bgClass} toast-slide-in pointer-events-auto px-4 py-3 rounded-lg shadow-lg flex items-center space-x-2 text-xs font-medium max-w-sm`;
  toast.innerHTML = `
    <i class="fa-solid ${iconClass} text-sm"></i>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
