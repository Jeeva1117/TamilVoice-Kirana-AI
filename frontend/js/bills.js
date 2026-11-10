/**
 * TamilVoice Kirana AI - Bill History & Invoices Controller
 * Section 6: Persistent Bill History, Multi-Filter, Itemized Invoice Details & Receipt Printing.
 */

import { Utils } from './utils.js';
import { Store } from './store.js';
import { Navigation } from './navigation.js';
import { Sales } from './sales.js';

export const Bills = {
  searchQuery: '',
  dateFilter: 'all',
  paymentFilter: 'all',
  sortBy: 'date-desc',

  init() {
    this.cacheDOM();
    this.bindEvents();
    this.render();

    // Listen for reactive store updates
    window.addEventListener('store-updated', () => {
      this.render();
    });

    window.addEventListener('view-changed', (e) => {
      if (e.detail && e.detail.view === 'bills') {
        if (Store && typeof Store.syncSalesFromBackend === 'function') {
          Store.syncSalesFromBackend();
        }
        this.render();
      }
    });

    window.addEventListener('language-changed', () => {
      this.render();
    });
  },

  cacheDOM() {
    // KPI elements
    this.kpiTodayCount = document.getElementById('bills-kpi-today-count');
    this.kpiTodayRevenue = document.getElementById('bills-kpi-today-revenue');
    this.kpiTotalBills = document.getElementById('bills-kpi-total-bills');
    this.kpiAvgAmount = document.getElementById('bills-kpi-avg-amount');

    // Filter elements
    this.searchInput = document.getElementById('bills-search-input');
    this.dateSelect = document.getElementById('bills-date-filter');
    this.paymentSelect = document.getElementById('bills-payment-filter');
    this.sortSelect = document.getElementById('bills-sort-filter');
    this.btnResetFilters = document.getElementById('bills-btn-reset-filters');
    this.btnCreateBill = document.getElementById('bills-btn-create-bill');

    // Table elements
    this.tableBody = document.getElementById('bills-table-body');
    this.tableCountBadge = document.getElementById('bills-table-count-badge');
    this.navBadge = document.getElementById('nav-bills-badge');
  },

  bindEvents() {
    // Search input
    if (this.searchInput) {
      this.searchInput.addEventListener('input', Utils.debounce((e) => {
        this.searchQuery = e.target.value.trim().toLowerCase();
        this.renderTable();
      }, 250));
    }

    // Date filter
    if (this.dateSelect) {
      this.dateSelect.addEventListener('change', (e) => {
        this.dateFilter = e.target.value;
        this.renderTable();
      });
    }

    // Payment method filter
    if (this.paymentSelect) {
      this.paymentSelect.addEventListener('change', (e) => {
        this.paymentFilter = e.target.value;
        this.renderTable();
      });
    }

    // Sort filter
    if (this.sortSelect) {
      this.sortSelect.addEventListener('change', (e) => {
        this.sortBy = e.target.value;
        this.renderTable();
      });
    }

    // Reset filters
    if (this.btnResetFilters) {
      this.btnResetFilters.addEventListener('click', () => {
        this.searchQuery = '';
        this.dateFilter = 'all';
        this.paymentFilter = 'all';
        this.sortBy = 'date-desc';

        if (this.searchInput) this.searchInput.value = '';
        if (this.dateSelect) this.dateSelect.value = 'all';
        if (this.paymentSelect) this.paymentSelect.value = 'all';
        if (this.sortSelect) this.sortSelect.value = 'date-desc';

        this.renderTable();
        Utils.showToast('info', 'Filters Reset', 'Showing all bills.');
      });
    }

    // New Customer Bill button navigates to Sales / Billing counter
    if (this.btnCreateBill) {
      this.btnCreateBill.addEventListener('click', () => {
        Navigation.switchView('sales');
      });
    }
  },

  render() {
    this.renderKPIs();
    this.renderTable();
  },

  renderKPIs() {
    const allSales = Store.getSales() || [];
    const now = new Date();
    const todayStr = now.toISOString().split('T')[0];

    let todayCount = 0;
    let todayRevenue = 0;
    let totalRevenue = 0;

    allSales.forEach(s => {
      const amt = Number(s.total_amount) || 0;
      totalRevenue += amt;
      const sDate = (s.date || '').split('T')[0];
      if (sDate === todayStr) {
        todayCount++;
        todayRevenue += amt;
      }
    });

    const totalBills = allSales.length;
    const avgAmount = totalBills > 0 ? (totalRevenue / totalBills) : 0;

    if (this.kpiTodayCount) this.kpiTodayCount.textContent = todayCount;
    if (this.kpiTodayRevenue) this.kpiTodayRevenue.textContent = Utils.formatCurrency(todayRevenue);
    if (this.kpiTotalBills) this.kpiTotalBills.textContent = totalBills;
    if (this.kpiAvgAmount) this.kpiAvgAmount.textContent = Utils.formatCurrency(avgAmount);

    if (this.navBadge) {
      this.navBadge.textContent = totalBills;
      this.navBadge.style.display = totalBills > 0 ? 'inline-flex' : 'none';
    }
  },

  renderTable() {
    if (!this.tableBody) return;

    let filtered = [...(Store.getSales() || [])];

    // Filter by search query
    if (this.searchQuery) {
      const q = this.searchQuery;
      filtered = filtered.filter(s =>
        (s.id && s.id.toLowerCase().includes(q)) ||
        (s.customer_name && s.customer_name.toLowerCase().includes(q)) ||
        (s.product_name && s.product_name.toLowerCase().includes(q)) ||
        (s.items_summary && s.items_summary.toLowerCase().includes(q)) ||
        (s.notes && s.notes.toLowerCase().includes(q))
      );
    }

    // Filter by date
    if (this.dateFilter !== 'all') {
      const now = new Date();
      filtered = filtered.filter(s => {
        if (!s.date) return false;
        const sDate = new Date(s.date);
        if (this.dateFilter === 'today') {
          return sDate.toDateString() === now.toDateString();
        } else if (this.dateFilter === 'yesterday') {
          const y = new Date();
          y.setDate(now.getDate() - 1);
          return sDate.toDateString() === y.toDateString();
        } else if (this.dateFilter === 'week') {
          const w = new Date();
          w.setDate(now.getDate() - 7);
          return sDate >= w;
        }
        return true;
      });
    }

    // Filter by payment method
    if (this.paymentFilter !== 'all') {
      filtered = filtered.filter(s =>
        s.payment_method && s.payment_method.toUpperCase() === this.paymentFilter.toUpperCase()
      );
    }

    // Sorting
    filtered.sort((a, b) => {
      const dateA = new Date(a.date || 0);
      const dateB = new Date(b.date || 0);
      const amtA = Number(a.total_amount) || 0;
      const amtB = Number(b.total_amount) || 0;

      if (this.sortBy === 'date-desc') return dateB - dateA;
      if (this.sortBy === 'date-asc') return dateA - dateB;
      if (this.sortBy === 'amount-desc') return amtB - amtA;
      if (this.sortBy === 'amount-asc') return amtA - amtB;
      return 0;
    });

    if (this.tableCountBadge) {
      this.tableCountBadge.textContent = `${filtered.length} bills`;
    }

    if (filtered.length === 0) {
      this.tableBody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align: center; padding: 3rem 1rem; color: #94A3B8;">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity: 0.5; margin-bottom: 0.75rem;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            <div style="font-weight: 600; font-size: 1rem; margin-bottom: 0.25rem;">No Bill Records Found</div>
            <div style="font-size: 0.85rem;">Adjust search filters or generate customer bills via Voice Assistant or Billing Counter.</div>
          </td>
        </tr>
      `;
      return;
    }

    this.tableBody.innerHTML = filtered.map(s => {
      const dateFmt = Utils.formatDate(s.date);
      const amtFmt = Utils.formatCurrency(s.total_amount);
      const itemsText = s.items_summary || (s.product_name ? `${s.product_name} (${s.quantity} ${s.unit})` : 'Counter Sale');
      const totalItems = s.total_items || (s.items ? s.items.length : 1);
      const payClass = (s.payment_method === 'UPI') ? 'blue' : (s.payment_method === 'CASH' ? 'green' : (s.payment_method === 'CARD' ? 'purple' : 'amber'));

      return `
        <tr>
          <td><strong style="color: #60A5FA; font-family: monospace;">${s.id}</strong></td>
          <td style="color: #94A3B8; font-size: 0.85rem;">${dateFmt}</td>
          <td><strong>${s.customer_name || 'Walk-in Counter'}</strong></td>
          <td style="max-width: 280px; white-space: normal;" title="${itemsText}">
            <span style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; font-size: 0.85rem;">
              ${itemsText}
            </span>
          </td>
          <td><span class="badge-pill neutral" style="font-size: 0.75rem;">${totalItems} ${totalItems === 1 ? 'item' : 'items'}</span></td>
          <td><strong class="text-success" style="font-size: 1rem;">${amtFmt}</strong></td>
          <td><span class="badge-pill ${payClass}" style="font-size: 0.75rem;">${s.payment_method || 'CASH'}</span></td>
          <td><span class="badge-pill success" style="font-size: 0.75rem;">Completed</span></td>
          <td style="text-align: right; white-space: nowrap;">
            <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
              <button class="btn btn-outline btn-xs btn-bill-view" data-bill-id="${s.id}" title="View Complete Itemized Bill">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
                <span>View</span>
              </button>
              <button class="btn btn-outline btn-xs btn-bill-print" data-bill-id="${s.id}" title="Print Receipt">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect width="12" height="8" x="6" y="14"/></svg>
                <span>Print</span>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Bind action buttons
    this.tableBody.querySelectorAll('.btn-bill-view').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-bill-id');
        this.openBillDetails(id);
      });
    });

    this.tableBody.querySelectorAll('.btn-bill-print').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-bill-id');
        this.printBillReceipt(id);
      });
    });
  },

  openBillDetails(billId) {
    const sale = (Store.getSales() || []).find(s => s.id === billId);
    if (!sale) return;

    if (Sales && typeof Sales.openDetailsModal === 'function') {
      Sales.openDetailsModal(billId);
    }
  },

  printBillReceipt(billId) {
    const sale = (Store.getSales() || []).find(s => s.id === billId);
    if (!sale) return;

    if (Sales && typeof Sales.openReceiptModal === 'function') {
      Sales.openReceiptModal(sale);
    }
  }
};

