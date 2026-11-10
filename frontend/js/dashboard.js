/**
 * TamilVoice Kirana AI - Dashboard Module
 * Handles KPI cards, Chart.js analytics visualization, low stock alerts, & recent sales
 */

import { Utils } from './utils.js';
import { ApiService } from './api.js';
import { Store } from './store.js';

export const Dashboard = {
  chartInstance: null,
  currentPeriod: 'daily',

  // Live Store Data (Zero-based initialization)
  data: {
    kpis: {
      todayRevenue: 0,
      revenueChange: '0.0%',
      totalSales: 0,
      salesChange: '0.0%',
      ordersToday: 0,
      ordersChange: '0.0%',
      lowStockCount: 0,
      totalProducts: 0
    },
    analytics: {
      daily: {
        labels: ['8 AM', '10 AM', '12 PM', '2 PM', '4 PM', '6 PM', '8 PM', '10 PM'],
        revenue: [0, 0, 0, 0, 0, 0, 0, 0],
        orders: [0, 0, 0, 0, 0, 0, 0, 0]
      },
      weekly: {
        labels: ['Mon (திங்கள்)', 'Tue (செவ்வாய்)', 'Wed (புதன்)', 'Thu (வியாழன்)', 'Fri (வெள்ளி)', 'Sat (சனி)', 'Sun (ஞாயிறு)'],
        revenue: [0, 0, 0, 0, 0, 0, 0],
        orders: [0, 0, 0, 0, 0, 0, 0]
      },
      monthly: {
        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
        revenue: [0, 0, 0, 0],
        orders: [0, 0, 0, 0]
      }
    },
    lowStock: [],
    recentTransactions: [],
    topProducts: []
  },

  init() {
    this.syncFromLocalStore();
    this.initChart();
    this.bindChartControls();
    this.updateClockAndDate();
    this.fetchLiveDashboardData();

    // Re-render when shared store changes (from inventory or sales actions)
    window.addEventListener('store-updated', () => {
      this.syncFromLocalStore();
    });

    // Re-render when language toggle occurs
    window.addEventListener('language-changed', () => {
      this.renderLowStock();
      this.renderRecentTransactions();
      this.renderTopProducts();
      this.updateChartData();
    });
  },

  syncFromLocalStore() {
    const products = Store.getProducts();
    const sales = Store.getSales();
    const todayStr = new Date().toISOString().slice(0, 10);

    let todayRev = 0;
    let todayOrdersCount = 0;
    sales.forEach(s => {
      if (s.date && s.date.slice(0, 10) === todayStr) {
        todayRev += Number(s.total_amount) || 0;
        todayOrdersCount++;
      }
    });

    const lowStockList = [];
    products.forEach(p => {
      const status = Store.calculateStatus(p);
      if (status === 'Low Stock' || status === 'Out of Stock') {
        lowStockList.push({
          id: p.sku || `PRD-${p.id}`,
          rawId: p.id,
          nameEn: p.name_en,
          nameTa: p.name_ta || p.name_en,
          category: p.category,
          stock: p.stock,
          minStock: p.min_stock,
          unit: p.unit,
          status: status === 'Out of Stock' ? 'critical' : 'warning'
        });
      }
    });

    this.data.kpis.todayRevenue = todayRev;
    this.data.kpis.totalSales = sales.length;
    this.data.kpis.ordersToday = todayOrdersCount;
    this.data.kpis.lowStockCount = lowStockList.length;
    this.data.kpis.totalProducts = products.length;

    this.data.lowStock = lowStockList;

    this.data.recentTransactions = sales.slice(0, 5).map(s => ({
      id: s.id,
      itemsEn: `${s.product_name || 'Sale'} (${s.quantity || 1} ${s.unit || ''})`,
      itemsTa: `${s.product_name_ta || s.product_name || 'விற்பனை'} (${s.quantity || 1} ${s.unit || ''})`,
      amount: s.total_amount,
      time: Utils.formatTime(s.date),
      status: (s.status || 'completed').toLowerCase()
    }));

    // Derive top products from real sales
    const productSalesMap = {};
    sales.forEach(s => {
      const key = s.product_name || 'Item';
      if (!productSalesMap[key]) {
        productSalesMap[key] = {
          nameEn: s.product_name,
          nameTa: s.product_name_ta || s.product_name,
          soldCount: 0,
          revenue: 0,
          unit: s.unit || ''
        };
      }
      productSalesMap[key].soldCount += Number(s.quantity) || 1;
      productSalesMap[key].revenue += Number(s.total_amount) || 0;
    });

    this.data.topProducts = Object.values(productSalesMap)
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 5)
      .map((item, idx) => ({
        rank: idx + 1,
        nameEn: item.nameEn,
        nameTa: item.nameTa,
        sold: `${item.soldCount} ${item.unit}`.trim(),
        revenue: item.revenue
      }));

    this.renderKPIs();
    this.renderLowStock();
    this.renderRecentTransactions();
    this.renderTopProducts();
  },

  async fetchLiveDashboardData() {
    try {
      const liveData = await ApiService.getDashboard();
      if (liveData && liveData.kpis) {
        this.data.kpis = {
          todayRevenue: liveData.kpis.today_sales ?? 0,
          revenueChange: `${(liveData.kpis.today_sales_change_pct || 0) >= 0 ? '+' : ''}${liveData.kpis.today_sales_change_pct || 0}%`,
          totalSales: liveData.kpis.today_orders ?? 0,
          salesChange: '0.0%',
          ordersToday: liveData.kpis.today_orders ?? 0,
          ordersChange: '0.0%',
          lowStockCount: liveData.kpis.low_stock_count ?? 0,
          totalProducts: liveData.kpis.total_products ?? 0
        };

        if (liveData.top_products && liveData.top_products.length > 0) {
          this.data.topProducts = liveData.top_products.map((p, idx) => ({
            rank: idx + 1,
            nameEn: p.name,
            nameTa: p.name_ta || p.name,
            sold: `${p.units_sold} units`,
            revenue: p.revenue
          }));
        }

        if (liveData.hourly_sales && liveData.hourly_sales.length > 0) {
          this.data.analytics.daily = {
            labels: liveData.hourly_sales.map(h => h.hour),
            revenue: liveData.hourly_sales.map(h => h.amount),
            orders: liveData.hourly_sales.map(() => 0)
          };
        }

        this.renderKPIs();
        this.updateChartData();
        this.renderLowStock();
        this.renderRecentTransactions();
        this.renderTopProducts();

        // Live backend status indicator
        const statusBanner = document.querySelector('.system-status-alert');
        if (statusBanner) {
          statusBanner.innerHTML = `
            <div class="system-status-content">
              <span class="badge-pill success" style="font-weight: 700;">BACKEND LIVE</span>
              <span class="system-status-text">
                <strong>Connected:</strong> FastAPI + SQLite Database active at <a href="http://127.0.0.1:8000/docs" target="_blank" style="text-decoration: underline; color: #166534;">http://127.0.0.1:8000</a>.
              </span>
            </div>
          `;
          statusBanner.style.backgroundColor = '#F0FDF4';
          statusBanner.style.borderColor = '#BBF7D0';
          statusBanner.style.color = '#166534';
        }
      }
    } catch (err) {
      console.log('[Dashboard] Backend offline or loading, using local store data.');
    }
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
    const navBadge = document.getElementById('nav-inventory-badge');

    if (revEl) revEl.textContent = Utils.formatINR(this.data.kpis.todayRevenue);
    if (salesEl) salesEl.textContent = this.data.kpis.totalSales.toString();
    if (ordersEl) ordersEl.textContent = this.data.kpis.ordersToday.toString();
    if (lowStockEl) lowStockEl.textContent = this.data.kpis.lowStockCount.toString();
    if (productsEl) productsEl.textContent = this.data.kpis.totalProducts.toString();
    if (navBadge) navBadge.textContent = this.data.kpis.totalProducts.toString();
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

    if (!this.data.lowStock || !this.data.lowStock.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 2rem; color: var(--color-text-muted);">
            <div style="font-size: 0.875rem;">${currentLang === 'ta' ? 'அனைத்து பொருட்களும் போதிய இருப்பில் உள்ளன.' : 'All products are adequately stocked.'}</div>
            <div style="font-size: 0.75rem; margin-top: 4px;">${currentLang === 'ta' ? 'குறைந்த இருப்பு எச்சரிக்கைகள் இல்லை.' : 'No low stock alerts at this time.'}</div>
          </td>
        </tr>
      `;
      return;
    }

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
            <button class="btn btn-xs btn-outline btn-restock" data-product-id="${item.rawId || item.id}" data-product-name="${displayName}">
              ${currentLang === 'ta' ? 'இருப்பு சேர்க்க' : 'Restock'}
            </button>
          </td>
        </tr>
      `;
    }).join('');

    // Attach Restock click handlers
    tbody.querySelectorAll('.btn-restock').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const prodId = btn.getAttribute('data-product-id');
        const prodName = btn.getAttribute('data-product-name');
        Utils.showToast('info', 'Stock Adjustment', `Opening restock modal for ${prodName}...`);
        
        // Navigate to inventory view and open adjust stock modal
        window.location.hash = 'inventory';
        if (window.Inventory && typeof window.Inventory.openAdjustModal === 'function') {
          setTimeout(() => {
            window.Inventory.openAdjustModal(prodId);
          }, 150);
        }
      });
    });
  },

  renderRecentTransactions() {
    const tbody = document.getElementById('recent-sales-table-body');
    if (!tbody) return;

    const currentLang = localStorage.getItem('tv_lang') || 'en';

    if (!this.data.recentTransactions || !this.data.recentTransactions.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align: center; padding: 2rem; color: var(--color-text-muted);">
            <div style="font-size: 0.875rem;">${currentLang === 'ta' ? 'இன்றைய விற்பனை பதிவுகள் ஏதுமில்லை.' : 'No transactions recorded yet today.'}</div>
            <div style="font-size: 0.75rem; margin-top: 4px;">${currentLang === 'ta' ? 'விற்பனை பதிவு செய்ய வாய்ஸ் அல்லது Sales Tab பயன்படுத்தவும்.' : 'Use voice commands or the Sales tab to record sales.'}</div>
          </td>
        </tr>
      `;
      return;
    }

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

    if (!this.data.topProducts || !this.data.topProducts.length) {
      container.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--color-text-muted); font-size: 0.875rem;">
          ${currentLang === 'ta' ? 'விற்பனை தரவு எதுவும் கிடைக்கவில்லை.' : 'No sales data recorded yet.'}
        </div>
      `;
      return;
    }

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

