/**
 * TamilVoice Kirana AI - Reports & Analytics Controller
 * Handles daily revenue reports, product performance, inventory valuation and CSV exports.
 */
import { ApiService } from './api.js';
import { Utils } from './utils.js';

export const Reports = {
  initialized: false,

  init() {
    if (this.initialized) return;
    this.cacheDOM();
    this.bindEvents();
    this.initialized = true;

    // Listen for view-changed event to load data when view is opened
    window.addEventListener('view-changed', (e) => {
      if (e.detail && e.detail.view === 'reports') {
        this.loadAllReports();
      }
    });
  },

  cacheDOM() {
    this.container = document.getElementById('view-reports');
  },

  bindEvents() {
    if (!this.container) return;

    this.container.addEventListener('click', (e) => {
      const exportBtn = e.target.closest('[data-export-type]');
      if (exportBtn) {
        const type = exportBtn.getAttribute('data-export-type');
        this.exportCsv(type);
      }

      if (e.target.closest('#btn-refresh-reports')) {
        this.loadAllReports();
      }
    });
  },

  async loadAllReports() {
    try {
      await Promise.all([
        this.loadInventoryValuation(),
        this.loadDailySalesReport(),
        this.loadProductSalesReport(),
      ]);
    } catch (err) {
      console.warn('Reports load issue:', err);
    }
  },

  async loadInventoryValuation() {
    const el = document.getElementById('report-valuation-cards');
    if (!el) return;
    try {
      const data = await ApiService.getInventoryValuationReport();
      document.getElementById('val-total-items').textContent = data.total_items || 0;
      document.getElementById('val-total-cost').textContent = `₹${(data.total_cost_value || 0).toLocaleString('en-IN')}`;
      document.getElementById('val-total-retail').textContent = `₹${(data.total_retail_value || 0).toLocaleString('en-IN')}`;
      document.getElementById('val-potential-profit').textContent = `₹${(data.potential_profit || 0).toLocaleString('en-IN')}`;
    } catch (err) {
      console.warn('Failed to load valuation:', err);
    }
  },

  async loadDailySalesReport() {
    const tbody = document.getElementById('reports-daily-tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:1.5rem; color:var(--color-text-secondary);">Loading daily sales breakdown...</td></tr>`;

    try {
      const data = await ApiService.getDailyReport();
      if (!data.daily_breakdown || data.daily_breakdown.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:1.5rem; color:var(--color-text-secondary);">No sales data recorded in this period.</td></tr>`;
        return;
      }

      tbody.innerHTML = data.daily_breakdown.map(row => `
        <tr>
          <td><strong style="color:var(--color-text-primary);">${row.date}</strong></td>
          <td style="font-weight:600; color:var(--color-success);">₹${row.total_sales.toLocaleString('en-IN')}</td>
          <td>${row.order_count} bills</td>
          <td>₹${row.average_order_value.toLocaleString('en-IN')}</td>
        </tr>
      `).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--color-danger); padding:1rem;">Failed to fetch daily sales report.</td></tr>`;
    }
  },

  async loadProductSalesReport() {
    const tbody = document.getElementById('reports-products-tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:1.5rem; color:var(--color-text-secondary);">Loading product performance...</td></tr>`;

    try {
      const items = await ApiService.getProductsReport();
      if (!items || items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:1.5rem; color:var(--color-text-secondary);">No products registered.</td></tr>`;
        return;
      }

      tbody.innerHTML = items.slice(0, 15).map((item, idx) => `
        <tr>
          <td>
            <div style="font-weight:600; color:var(--color-text-primary);">${item.name}</div>
            <div style="font-size:0.75rem; color:var(--color-text-muted);">${item.sku}</div>
          </td>
          <td><span class="badge" style="background:var(--color-bg-secondary); font-size:0.75rem;">${item.category || 'General'}</span></td>
          <td><strong>${item.units_sold}</strong> units</td>
          <td style="font-weight:600; color:var(--color-primary);">₹${item.revenue.toLocaleString('en-IN')}</td>
          <td>
            <span class="badge ${item.current_stock <= 5 ? 'badge-danger' : 'badge-success'}">
              ${item.current_stock}
            </span>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--color-danger); padding:1rem;">Failed to fetch product rankings.</td></tr>`;
    }
  },

  exportCsv(type) {
    const url = ApiService.getExportCsvUrl(type);
    window.open(url, '_blank');
    Utils.showToast('success', 'Report Export', `Generating ${type} CSV spreadsheet download...`);
  }
};

