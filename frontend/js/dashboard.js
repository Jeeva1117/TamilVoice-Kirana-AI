/**
 * TamilVoice Kirana AI - Dashboard Module
 * Handles KPI cards, Chart.js analytics visualization, low stock alerts, & recent sales
 */

import { Utils } from './utils.js';

export const Dashboard = {
  chartInstance: null,
  currentPeriod: 'daily',

  // Mock Realistic Data
  data: {
    kpis: {
      todayRevenue: 18450,
      revenueChange: '+12.4%',
      totalSales: 142,
      salesChange: '+8.1%',
      ordersToday: 38,
      ordersChange: '+5.2%',
      lowStockCount: 6,
      totalProducts: 428
    },
    analytics: {
      daily: {
        labels: ['8 AM', '10 AM', '12 PM', '2 PM', '4 PM', '6 PM', '8 PM', '10 PM'],
        revenue: [1200, 2800, 4100, 2200, 3100, 5600, 7200, 3450],
        orders: [8, 19, 28, 14, 22, 39, 48, 24]
      },
      weekly: {
        labels: ['Mon (திங்கள்)', 'Tue (செவ்வாய்)', 'Wed (புதன்)', 'Thu (வியாழன்)', 'Fri (வெள்ளி)', 'Sat (சனி)', 'Sun (ஞாயிறு)'],
        revenue: [14200, 16800, 15300, 17900, 19400, 24800, 22100],
        orders: [95, 112, 104, 118, 134, 168, 150]
      },
      monthly: {
        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
        revenue: [98000, 112400, 105600, 126500],
        orders: [720, 840, 790, 910]
      }
    },
    lowStock: [
      { id: 'PRD-01', nameEn: 'Ponni Boiled Rice 25kg', nameTa: 'பொன்னி புழுங்கல் அரிசி 25kg', category: 'Rice', stock: 2, minStock: 8, unit: 'bags', status: 'critical' },
      { id: 'PRD-02', nameEn: 'Gold Winner Sunflower Oil 1L', nameTa: 'கோல்ட் வின்னர் எண்ணெய் 1L', category: 'Oil', stock: 4, minStock: 15, unit: 'pkts', status: 'warning' },
      { id: 'PRD-03', nameEn: 'Aachi Chilli Powder 100g', nameTa: 'ஆச்சி மிளகாய் தூள் 100g', category: 'Spices', stock: 6, minStock: 20, unit: 'pkts', status: 'warning' },
      { id: 'PRD-04', nameEn: 'Tata Iodized Salt 1kg', nameTa: 'டாடா உப்பு 1kg', category: 'Grocery', stock: 3, minStock: 12, unit: 'pkts', status: 'critical' },
      { id: 'PRD-05', nameEn: 'Premium Toor Dhal', nameTa: 'முதல் தர துவரம் பருப்பு', category: 'Dhal', stock: 5, minStock: 18, unit: 'kg', status: 'warning' }
    ],
    recentTransactions: [
      { id: 'KB-1089', itemsEn: 'Ponni Rice 25kg (1 bag)', itemsTa: 'பொன்னி அரிசி 25kg (1 மூட்டை)', amount: 1450, time: '10 mins ago', status: 'completed' },
      { id: 'KB-1088', itemsEn: 'Sunflower Oil 2L + Tata Salt 1kg', itemsTa: 'சூரியகாந்தி எண்ணெய் 2L + உப்பு 1kg', amount: 320, time: '24 mins ago', status: 'completed' },
      { id: 'KB-1087', itemsEn: 'Aachi Chilli & Coriander Powder', itemsTa: 'ஆச்சி மிளகாய் & மல்லி தூள்', amount: 95, time: '38 mins ago', status: 'completed' },
      { id: 'KB-1086', itemsEn: 'White Sugar 5kg + Toor Dhal 2kg', itemsTa: 'சீனி 5kg + துவரம் பருப்பு 2kg', amount: 460, time: '1 hour ago', status: 'completed' },
      { id: 'KB-1085', itemsEn: 'Aashirvaad Whole Wheat Atta 5kg', itemsTa: 'ஆசீர்வாத் கோதுமை மாவு 5kg', amount: 295, time: '2 hours ago', status: 'completed' }
    ],
    topProducts: [
      { rank: 1, nameEn: 'Ponni Boiled Rice 25kg', nameTa: 'பொன்னி புழுங்கல் அரிசி 25kg', sold: '34 bags', revenue: 49300 },
      { rank: 2, nameEn: 'Gold Winner Sunflower Oil 1L', nameTa: 'கோல்ட் வின்னர் எண்ணெய் 1L', sold: '62 pkts', revenue: 8680 },
      { rank: 3, nameEn: 'Tata Iodized Salt 1kg', nameTa: 'டாடா அயோடின் உப்பு 1kg', sold: '88 pkts', revenue: 2200 },
      { rank: 4, nameEn: 'Premium Toor Dhal 1kg', nameTa: 'முதல் தர துவரம் பருப்பு', sold: '45 kg', revenue: 6750 }
    ]
  },

  init() {
    this.renderKPIs();
    this.initChart();
    this.renderLowStock();
    this.renderRecentTransactions();
    this.renderTopProducts();
    this.bindChartControls();
    this.updateClockAndDate();

    // Re-render when language toggle occurs
    window.addEventListener('language-changed', () => {
      this.renderLowStock();
      this.renderRecentTransactions();
      this.renderTopProducts();
      this.updateChartData();
    });
  },

  updateClockAndDate() {
    const dateEl = document.getElementById('current-date-display');
    if (dateEl) {
      const currentLang = localStorage.getItem('tv_lang') || 'en';
      dateEl.textContent = Utils.formatDate(new Date(), currentLang);
    }
  },

  renderKPIs() {
    const revEl = document.getElementById('kpi-revenue');
    const salesEl = document.getElementById('kpi-sales');
    const ordersEl = document.getElementById('kpi-orders');
    const lowStockEl = document.getElementById('kpi-low-stock');
    const productsEl = document.getElementById('kpi-products');

    if (revEl) revEl.textContent = Utils.formatINR(this.data.kpis.todayRevenue);
    if (salesEl) salesEl.textContent = this.data.kpis.totalSales.toString();
    if (ordersEl) ordersEl.textContent = this.data.kpis.ordersToday.toString();
    if (lowStockEl) lowStockEl.textContent = this.data.kpis.lowStockCount.toString();
    if (productsEl) productsEl.textContent = this.data.kpis.totalProducts.toString();
  },

  initChart() {
    const canvas = document.getElementById('salesRevenueChart');
    if (!canvas || typeof Chart === 'undefined') {
      console.warn('Chart canvas or Chart.js not loaded yet.');
      return;
    }

    const ctx = canvas.getContext('2d');
    const periodData = this.data.analytics[this.currentPeriod];

    // Create subtle gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, 'rgba(37, 99, 235, 0.28)');
    gradient.addColorStop(1, 'rgba(37, 99, 235, 0.01)');

    this.chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: periodData.labels,
        datasets: [{
          label: 'Revenue (₹)',
          data: periodData.revenue,
          borderColor: '#2563EB',
          borderWidth: 2.5,
          backgroundColor: gradient,
          fill: true,
          tension: 0.38,
          pointBackgroundColor: '#FFFFFF',
          pointBorderColor: '#2563EB',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0F172A',
            titleColor: '#FFFFFF',
            bodyColor: '#93C5FD',
            padding: 10,
            cornerRadius: 8,
            displayColors: false,
            callbacks: {
              label: (context) => `Revenue: ${Utils.formatINR(context.raw)}`
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: '#64748B',
              font: { family: "'Inter', 'Noto Sans Tamil', sans-serif", size: 11 }
            }
          },
          y: {
            grid: { color: '#F1F5F9' },
            ticks: {
              color: '#64748B',
              font: { family: "'Inter', sans-serif", size: 11 },
              callback: (value) => `₹${value >= 1000 ? (value / 1000) + 'k' : value}`
            }
          }
        }
      }
    });
  },

  bindChartControls() {
    const buttons = document.querySelectorAll('.chart-tab-btn');
    buttons.forEach(btn => {
      btn.addEventListener('click', () => {
        buttons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const period = btn.getAttribute('data-period');
        if (period && this.data.analytics[period]) {
          this.currentPeriod = period;
          this.updateChartData();
        }
      });
    });
  },

  updateChartData() {
    if (!this.chartInstance) return;
    const periodData = this.data.analytics[this.currentPeriod];
    this.chartInstance.data.labels = periodData.labels;
    this.chartInstance.data.datasets[0].data = periodData.revenue;
    this.chartInstance.update();
  },

  renderLowStock() {
    const tbody = document.getElementById('low-stock-table-body');
    if (!tbody) return;

    const currentLang = localStorage.getItem('tv_lang') || 'en';

    tbody.innerHTML = this.data.lowStock.map(item => {
      const isCritical = item.status === 'critical';
      const badgeClass = isCritical ? 'danger' : 'warning';
      const badgeText = isCritical ? (currentLang === 'ta' ? 'அவசர இருப்பு' : 'Critical Low') : (currentLang === 'ta' ? 'குறைந்த இருப்பு' : 'Low Stock');
      const displayName = currentLang === 'ta' ? item.nameTa : item.nameEn;

      return `
        <tr>
          <td>
            <div class="product-info-cell">
              <span class="product-name-tamil">${displayName}</span>
              <span class="text-xs text-muted">ID: ${item.id}</span>
            </div>
          </td>
          <td>
            <span class="text-semibold ${isCritical ? 'text-danger' : 'text-warning'}">
              ${item.stock} ${item.unit}
            </span>
          </td>
          <td class="text-muted">${item.minStock} ${item.unit}</td>
          <td>
            <span class="badge-pill ${badgeClass}">${badgeText}</span>
          </td>
          <td style="text-align: right;">
            <button class="btn btn-xs btn-outline btn-restock" data-product-id="${item.id}" data-product-name="${displayName}">
              ${currentLang === 'ta' ? 'இருப்பு சேர்க்க' : 'Restock'}
            </button>
          </td>
        </tr>
      `;
    }).join('');

    // Attach Restock click handlers
    tbody.querySelectorAll('.btn-restock').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const prodName = btn.getAttribute('data-product-name');
        Utils.showToast('info', 'Stock Adjustment', `Opening restock modal for ${prodName}...`);
      });
    });
  },

  renderRecentTransactions() {
    const tbody = document.getElementById('recent-sales-table-body');
    if (!tbody) return;

    const currentLang = localStorage.getItem('tv_lang') || 'en';

    tbody.innerHTML = this.data.recentTransactions.map(tx => {
      const items = currentLang === 'ta' ? tx.itemsTa : tx.itemsEn;
      return `
        <tr>
          <td><span class="text-semibold text-primary">${tx.id}</span></td>
          <td>
            <div class="product-info-cell">
              <span class="product-name-tamil">${items}</span>
              <span class="text-xs text-muted">${tx.time}</span>
            </div>
          </td>
          <td class="text-semibold">${Utils.formatINR(tx.amount)}</td>
          <td>
            <span class="badge-pill success">
              <span class="status-indicator-dot completed"></span>
              ${currentLang === 'ta' ? 'முழுமை' : 'Completed'}
            </span>
          </td>
        </tr>
      `;
    }).join('');
  },

  renderTopProducts() {
    const container = document.getElementById('top-products-container');
    if (!container) return;

    const currentLang = localStorage.getItem('tv_lang') || 'en';

    container.innerHTML = this.data.topProducts.map(p => {
      const name = currentLang === 'ta' ? p.nameTa : p.nameEn;
      return `
        <div class="product-sales-item">
          <div class="product-sales-info">
            <span class="product-rank top-${p.rank}">${p.rank}</span>
            <div class="flex flex-col">
              <span class="product-name-tamil">${name}</span>
              <span class="product-sales-qty">${p.sold}</span>
            </div>
          </div>
          <div class="product-sales-stats">
            <span class="product-sales-revenue">${Utils.formatINR(p.revenue)}</span>
          </div>
        </div>
      `;
    }).join('');
  }
};
