/**
 * TamilVoice Kirana AI - Sales & Orders Controller
 * Phase 3: Sales Register, Multi-filter, New Sale Workflow, Confirmation, Receipt Preview & Printing.
 */

import { Utils } from './utils.js';
import { Store } from './store.js';

export const Sales = {
  searchQuery: '',
  dateFilter: 'all',
  paymentFilter: 'all',
  statusFilter: 'all',
  sortBy: 'date-desc',
  pendingSaleData: null,
  activeReceiptSale: null,

  init() {
    this.cacheDOM();
    this.bindEvents();
    this.render();

    // Listen for reactive store updates
    window.addEventListener('store-updated', () => {
      this.render();
    });

    window.addEventListener('language-changed', () => {
      this.render();
    });
  },

  cacheDOM() {
    // KPI elements
    this.kpiTodaySales = document.getElementById('sales-kpi-today');
    this.kpiTotalRevenue = document.getElementById('sales-kpi-total-revenue');
    this.kpiTotalTransactions = document.getElementById('sales-kpi-total-tx');
    this.kpiAvgOrderValue = document.getElementById('sales-kpi-aov');

    // Filter elements
    this.searchInput = document.getElementById('sales-search-input');
    this.dateSelect = document.getElementById('sales-date-filter');
    this.paymentSelect = document.getElementById('sales-payment-filter');
    this.statusSelect = document.getElementById('sales-status-filter');
    this.sortSelect = document.getElementById('sales-sort-filter');
    this.btnResetFilters = document.getElementById('sales-btn-reset-filters');
    this.btnOpenNewSale = document.getElementById('sales-btn-open-new');

    // Table elements
    this.tableBody = document.getElementById('sales-table-body');
    this.tableCountBadge = document.getElementById('sales-table-count-badge');

    // New Sale Modal Elements
    this.modalNewSale = document.getElementById('modal-new-sale');
    this.formNewSale = document.getElementById('form-new-sale');
    this.productSelect = document.getElementById('sale-product-select');
    this.qtyInput = document.getElementById('sale-quantity-input');
    this.priceInput = document.getElementById('sale-price-input');
    this.paymentMethodSelect = document.getElementById('sale-payment-method');
    this.customerInput = document.getElementById('sale-customer-input');
    this.notesInput = document.getElementById('sale-notes-input');
    this.stockHint = document.getElementById('sale-stock-hint');
    this.totalAmountDisplay = document.getElementById('sale-total-display');

    // Sale Confirmation Modal Elements
    this.modalConfirmSale = document.getElementById('modal-confirm-sale');
    this.confirmSummaryText = document.getElementById('confirm-sale-summary');
    this.confirmStockBefore = document.getElementById('confirm-stock-before');
    this.confirmStockAfter = document.getElementById('confirm-stock-after');
    this.btnFinalConfirmSale = document.getElementById('btn-final-confirm-sale');

    // Transaction Details Modal Elements
    this.modalDetails = document.getElementById('modal-sale-details');
    this.detailsContent = document.getElementById('sale-details-content');

    // Receipt Modal & Printable Template
    this.modalReceipt = document.getElementById('modal-receipt-preview');
    this.receiptContainer = document.getElementById('printable-receipt-area');
    this.btnPrintReceiptNow = document.getElementById('btn-print-receipt-now');
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

    // Status filter
    if (this.statusSelect) {
      this.statusSelect.addEventListener('change', (e) => {
        this.statusFilter = e.target.value;
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

    // Reset Filters
    if (this.btnResetFilters) {
      this.btnResetFilters.addEventListener('click', () => this.resetFilters());
    }

    // Open New Sale Modal
    if (this.btnOpenNewSale) {
      this.btnOpenNewSale.addEventListener('click', () => this.openNewSaleModal());
    }

    // Product change in New Sale Modal
    if (this.productSelect) {
      this.productSelect.addEventListener('change', () => this.onProductSelected());
    }

    // Quantity / Price change in New Sale Modal
    if (this.qtyInput) {
      this.qtyInput.addEventListener('input', () => this.calculateSaleTotal());
    }
    if (this.priceInput) {
      this.priceInput.addEventListener('input', () => this.calculateSaleTotal());
    }

    // Form Submit -> opens confirmation dialog
    if (this.formNewSale) {
      this.formNewSale.addEventListener('submit', (e) => this.handleNewSalePreConfirm(e));
    }

    // Final Confirm Sale
    if (this.btnFinalConfirmSale) {
      this.btnFinalConfirmSale.addEventListener('click', () => this.executeSale());
    }

    // Print Receipt button click
    if (this.btnPrintReceiptNow) {
      this.btnPrintReceiptNow.addEventListener('click', () => {
        window.print();
      });
    }
  },

  render() {
    this.renderKPIs();
    this.renderTable();
  },

  renderKPIs() {
    const sales = Store.getSales();
    const todayStr = new Date().toISOString().slice(0, 10);

    let todayRevenue = 0;
    let totalRevenue = 0;
    const totalTx = sales.length;

    sales.forEach(s => {
      const amt = Number(s.total_amount) || 0;
      totalRevenue += amt;
      if (s.date && s.date.slice(0, 10) === todayStr) {
        todayRevenue += amt;
      }
    });

    const aov = totalTx ? Math.round(totalRevenue / totalTx) : 0;

    if (this.kpiTodaySales) this.kpiTodaySales.textContent = Utils.formatINR(todayRevenue);
    if (this.kpiTotalRevenue) this.kpiTotalRevenue.textContent = Utils.formatINR(totalRevenue);
    if (this.kpiTotalTransactions) this.kpiTotalTransactions.textContent = totalTx.toString();
    if (this.kpiAvgOrderValue) this.kpiAvgOrderValue.textContent = Utils.formatINR(aov);
  },

  getFilteredSales() {
    let sales = Store.getSales();
    const now = Date.now();
    const todayStr = new Date().toISOString().slice(0, 10);
    const yesterdayStr = new Date(now - 86400000).toISOString().slice(0, 10);

    // 1. Text Search
    if (this.searchQuery) {
      sales = sales.filter(s => {
        const id = (s.id || '').toLowerCase();
        const prod = (s.product_name || '').toLowerCase();
        const prodTa = (s.product_name_ta || '').toLowerCase();
        const cust = (s.customer_name || '').toLowerCase();
        return id.includes(this.searchQuery) || prod.includes(this.searchQuery) || prodTa.includes(this.searchQuery) || cust.includes(this.searchQuery);
      });
    }

    // 2. Date Filter
    if (this.dateFilter && this.dateFilter !== 'all') {
      sales = sales.filter(s => {
        if (!s.date) return false;
        const sDate = s.date.slice(0, 10);
        if (this.dateFilter === 'today') return sDate === todayStr;
        if (this.dateFilter === 'yesterday') return sDate === yesterdayStr;
        if (this.dateFilter === 'week') {
          return (now - new Date(s.date).getTime()) <= 7 * 86400000;
        }
        return true;
      });
    }

    // 3. Payment Filter
    if (this.paymentFilter && this.paymentFilter !== 'all') {
      sales = sales.filter(s => (s.payment_method || '').toLowerCase() === this.paymentFilter.toLowerCase());
    }

    // 4. Status Filter
    if (this.statusFilter && this.statusFilter !== 'all') {
      sales = sales.filter(s => (s.status || '').toLowerCase() === this.statusFilter.toLowerCase());
    }

    // 5. Sorting
    sales.sort((a, b) => {
      switch (this.sortBy) {
        case 'date-desc':
          return new Date(b.date).getTime() - new Date(a.date).getTime();
        case 'date-asc':
          return new Date(a.date).getTime() - new Date(b.date).getTime();
        case 'amount-desc':
          return (Number(b.total_amount) || 0) - (Number(a.total_amount) || 0);
        case 'amount-asc':
          return (Number(a.total_amount) || 0) - (Number(b.total_amount) || 0);
        default:
          return 0;
      }
    });

    return sales;
  },

  renderTable() {
    if (!this.tableBody) return;

    const filtered = this.getFilteredSales();

    if (this.tableCountBadge) {
      this.tableCountBadge.textContent = `${filtered.length} bills`;
    }

    if (!filtered.length) {
      this.tableBody.innerHTML = `
        <tr>
          <td colspan="9">
            <div class="table-empty-state">
              <svg class="table-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/>
              </svg>
              <h4 style="font-size: 1rem; color: var(--color-text-primary); margin-top: 4px;">No sales records found</h4>
              <p style="font-size: 0.8125rem; color: var(--color-text-secondary); max-width: 320px;">
                No invoices match your search or filter selection.
              </p>
              <button class="btn btn-sm btn-outline" style="margin-top: 8px;" onclick="document.getElementById('sales-btn-reset-filters').click();">
                Reset All Filters
              </button>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    const currentLang = localStorage.getItem('tv_lang') || 'en';

    this.tableBody.innerHTML = filtered.map(s => {
      const pmClass = (s.payment_method || 'Cash').toLowerCase();
      const statusClass = (s.status || 'Completed').toLowerCase() === 'completed' ? 'success' : 'warning';
      const prodDisplay = currentLang === 'ta' && s.product_name_ta ? s.product_name_ta : s.product_name;

      return `
        <tr>
          <td>
            <span class="text-semibold text-primary" style="cursor: pointer;" onclick="window.Sales.openDetailsModal('${s.id}')">${s.id}</span>
          </td>
          <td>
            <div class="flex flex-col">
              <span class="text-xs text-semibold">${Utils.formatDate(s.date, currentLang)}</span>
              <span class="text-2xs text-muted">${Utils.formatTime(s.date)}</span>
            </div>
          </td>
          <td>
            <div class="product-cell-name">
              <span class="text-semibold">${prodDisplay}</span>
              ${s.customer_name ? `<span class="text-2xs text-muted">${s.customer_name}</span>` : ''}
            </div>
          </td>
          <td>
            <span class="text-semibold">${s.quantity}</span> <span class="text-2xs text-muted">${s.unit || ''}</span>
          </td>
          <td>
            <span class="text-muted text-xs">${Utils.formatINR(s.unit_price)}</span>
          </td>
          <td>
            <span class="text-semibold text-primary">${Utils.formatINR(s.total_amount)}</span>
          </td>
          <td>
            <span class="payment-badge ${pmClass}">${s.payment_method || 'Cash'}</span>
          </td>
          <td>
            <span class="badge-pill ${statusClass}">
              <span class="status-indicator-dot completed"></span>
              ${s.status || 'Completed'}
            </span>
          </td>
          <td>
            <div class="table-actions-cell">
              <button class="btn-table-action" title="View Details" onclick="window.Sales.openDetailsModal('${s.id}')">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
              </button>
              <button class="btn-table-action" title="Print Receipt" onclick="window.Sales.openReceiptModal('${s.id}')">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect width="12" height="8" x="6" y="14"/></svg>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  resetFilters() {
    this.searchQuery = '';
    this.dateFilter = 'all';
    this.paymentFilter = 'all';
    this.statusFilter = 'all';
    this.sortBy = 'date-desc';

    if (this.searchInput) this.searchInput.value = '';
    if (this.dateSelect) this.dateSelect.value = 'all';
    if (this.paymentSelect) this.paymentSelect.value = 'all';
    if (this.statusSelect) this.statusSelect.value = 'all';
    if (this.sortSelect) this.sortSelect.value = 'date-desc';

    this.renderTable();
    Utils.showToast('info', 'Filters Reset', 'Sales history filters have been reset.');
  },

  /* =========================================================================
     RECORD NEW SALE MODAL & WORKFLOW
     ========================================================================= */
  openNewSaleModal() {
    if (!this.modalNewSale || !this.formNewSale) return;
    this.formNewSale.reset();

    // Populate products dropdown
    const products = Store.getProducts();
    if (this.productSelect) {
      this.productSelect.innerHTML = `
        <option value="">-- Choose Product to Bill --</option>
        ${products.map(p => `
          <option value="${p.id}" ${p.stock <= 0 ? 'disabled' : ''}>
            ${p.name_en} (${p.stock} ${p.unit} in stock) — ${Utils.formatINR(p.selling_price)}/${p.unit}
          </option>
        `).join('')}
      `;
    }

    if (this.stockHint) this.stockHint.textContent = 'Select a product to view available inventory.';
    if (this.totalAmountDisplay) this.totalAmountDisplay.textContent = '₹0';

    this.modalNewSale.classList.add('open');
  },

  onProductSelected() {
    const prodId = this.productSelect.value;
    if (!prodId) {
      if (this.stockHint) this.stockHint.textContent = '';
      if (this.priceInput) this.priceInput.value = '';
      this.calculateSaleTotal();
      return;
    }

    const product = Store.getProductById(prodId);
    if (!product) return;

    if (this.priceInput) this.priceInput.value = product.selling_price;
    if (this.qtyInput) {
      this.qtyInput.max = product.stock;
      this.qtyInput.value = product.stock > 0 ? 1 : 0;
    }

    if (this.stockHint) {
      if (product.stock <= 0) {
        this.stockHint.className = 'product-stock-hint insufficient';
        this.stockHint.textContent = `Out of stock! (0 ${product.unit} available)`;
      } else {
        this.stockHint.className = 'product-stock-hint sufficient';
        this.stockHint.textContent = `Available: ${product.stock} ${product.unit} in store.`;
      }
    }

    this.calculateSaleTotal();
  },

  calculateSaleTotal() {
    const qty = parseFloat(this.qtyInput.value) || 0;
    const price = parseFloat(this.priceInput.value) || 0;
    const total = qty * price;

    if (this.totalAmountDisplay) {
      this.totalAmountDisplay.textContent = Utils.formatINR(total);
    }
  },

  handleNewSalePreConfirm(e) {
    e.preventDefault();

    const prodId = this.productSelect.value;
    const qty = parseFloat(this.qtyInput.value);
    const price = parseFloat(this.priceInput.value);
    const paymentMethod = this.paymentMethodSelect.value;
    const customer = this.customerInput.value.trim();
    const notes = this.notesInput.value.trim();

    if (!prodId) {
      Utils.showToast('error', 'Select Product', 'Please select a product from the list.');
      return;
    }

    const product = Store.getProductById(prodId);
    if (!product) return;

    if (isNaN(qty) || qty <= 0) {
      Utils.showToast('error', 'Invalid Quantity', 'Quantity must be greater than zero.');
      return;
    }

    if (qty > Number(product.stock)) {
      Utils.showToast('error', 'Insufficient Stock', `Cannot sell ${qty} ${product.unit}. Only ${product.stock} ${product.unit} available.`);
      return;
    }

    // Prepare pending sale object
    this.pendingSaleData = {
      product_id: product.id,
      quantity: qty,
      unit_price: price,
      payment_method: paymentMethod,
      customer_name: customer || 'Counter Customer',
      notes
    };

    // Populate confirmation step
    if (this.confirmSummaryText) {
      this.confirmSummaryText.textContent = `${product.name_en} • ${qty} ${product.unit} @ ${Utils.formatINR(price)} = ${Utils.formatINR(qty * price)} (${paymentMethod})`;
    }

    if (this.confirmStockBefore) {
      this.confirmStockBefore.textContent = `${product.stock} ${product.unit}`;
    }

    if (this.confirmStockAfter) {
      const remaining = Number(product.stock) - qty;
      this.confirmStockAfter.textContent = `${remaining} ${product.unit}`;
      this.confirmStockAfter.className = remaining <= product.min_stock ? 'text-warning text-semibold' : 'text-success text-semibold';
    }

    // Close form modal, open confirmation dialog
    this.modalNewSale.classList.remove('open');
    if (this.modalConfirmSale) this.modalConfirmSale.classList.add('open');
  },

  executeSale() {
    if (!this.pendingSaleData) return;

    try {
      const newSale = Store.recordSale(this.pendingSaleData);
      this.pendingSaleData = null;

      if (this.modalConfirmSale) this.modalConfirmSale.classList.remove('open');

      Utils.showToast('success', 'Bill Recorded (Demo)', `Invoice ${newSale.id} created. Inventory deducted.`);

      // Prompt Receipt preview
      setTimeout(() => {
        this.openReceiptModal(newSale.id);
      }, 400);

    } catch (err) {
      Utils.showToast('error', 'Sale Failed', err.message);
    }
  },

  /* =========================================================================
     TRANSACTION DETAILS MODAL
     ========================================================================= */
  openDetailsModal(id) {
    const sale = Store.getSaleById(id);
    if (!sale || !this.modalDetails || !this.detailsContent) return;

    this.activeReceiptSale = sale;

    this.detailsContent.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: var(--space-4);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <h3 style="font-size: 1.125rem; font-weight: 700; color: var(--color-primary);">${sale.id}</h3>
            <span style="font-size: 0.8125rem; color: var(--color-text-muted);">${Utils.formatDate(sale.date)} • ${Utils.formatTime(sale.date)}</span>
          </div>
          <span class="badge-pill success">Completed</span>
        </div>

        <div style="background: var(--color-bg); padding: var(--space-4); border-radius: var(--radius-lg); border: 1px solid var(--color-border); display: flex; flex-direction: column; gap: 8px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
            <span class="text-muted">Item Billed:</span>
            <strong>${sale.product_name} (${sale.product_name_ta || ''})</strong>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
            <span class="text-muted">Quantity Sold:</span>
            <span>${sale.quantity} ${sale.unit || ''}</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
            <span class="text-muted">Unit Rate:</span>
            <span>${Utils.formatINR(sale.unit_price)}</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
            <span class="text-muted">Payment Method:</span>
            <span class="payment-badge ${sale.payment_method.toLowerCase()}">${sale.payment_method}</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
            <span class="text-muted">Customer Name:</span>
            <span>${sale.customer_name || 'Counter Walk-in'}</span>
          </div>
          ${sale.notes ? `
            <div style="border-top: 1px dashed var(--color-border); padding-top: 6px; font-size: 0.75rem; color: var(--color-text-muted);">
              Note: ${sale.notes}
            </div>
          ` : ''}
          <div style="border-top: 2px dashed #CBD5E1; padding-top: 8px; display: flex; justify-content: space-between; font-size: 1.125rem; font-weight: 700; color: var(--color-text-primary);">
            <span>Total Paid:</span>
            <span class="text-primary">${Utils.formatINR(sale.total_amount)}</span>
          </div>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: var(--space-3);">
          <button class="btn btn-outline" data-close-modal>Close</button>
          <button class="btn btn-primary" onclick="window.Sales.openReceiptModal('${sale.id}')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect width="12" height="8" x="6" y="14"/></svg>
            <span>Print Receipt</span>
          </button>
        </div>
      </div>
    `;

    this.modalDetails.classList.add('open');
  },

  /* =========================================================================
     PRINTABLE RECEIPT MODAL
     ========================================================================= */
  openReceiptModal(id) {
    const sale = Store.getSaleById(id);
    if (!sale || !this.modalReceipt || !this.receiptContainer) return;

    this.activeReceiptSale = sale;

    // Build Receipt HTML
    this.receiptContainer.innerHTML = `
      <div class="receipt-wrapper">
        <div class="receipt-header">
          <div class="receipt-shop-title">KARTHIK KIRANA STORE</div>
          <div class="receipt-shop-tamil">கார்த்திக் மளிகைக் கடை</div>
          <div class="receipt-shop-meta">12, Bazaar Street, Madurai, Tamil Nadu • Ph: 98765 43210</div>
          <div class="receipt-demo-watermark">DEMO RECEIPT — NOT A FISCAL TAX INVOICE</div>
        </div>

        <div class="receipt-info-row">
          <span>Bill No: <strong>${sale.id}</strong></span>
          <span>Date: ${Utils.formatDate(sale.date)}</span>
        </div>
        <div class="receipt-info-row">
          <span>Time: ${Utils.formatTime(sale.date)}</span>
          <span>Cashier: Karthik R.</span>
        </div>
        <div class="receipt-info-row">
          <span>Customer: ${sale.customer_name || 'Walk-in'}</span>
          <span>Mode: ${sale.payment_method}</span>
        </div>

        <table class="receipt-items-table">
          <thead>
            <tr>
              <th>Item Description</th>
              <th style="text-align: center;">Qty</th>
              <th style="text-align: right;">Rate</th>
              <th style="text-align: right;">Amount</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <strong>${sale.product_name}</strong>
                ${sale.product_name_ta ? `<div style="font-size: 10px; color: #64748B;">${sale.product_name_ta}</div>` : ''}
              </td>
              <td style="text-align: center;">${sale.quantity} ${sale.unit}</td>
              <td style="text-align: right;">${Utils.formatINR(sale.unit_price)}</td>
              <td style="text-align: right; font-weight: 600;">${Utils.formatINR(sale.total_amount)}</td>
            </tr>
          </tbody>
        </table>

        <div class="receipt-total-row">
          <span>TOTAL AMOUNT PAID:</span>
          <span>${Utils.formatINR(sale.total_amount)}</span>
        </div>

        <div class="receipt-footer">
          <div>Goods once sold can be exchanged within 2 days with bill.</div>
          <div class="receipt-thankyou-tamil">நன்றி! மீண்டும் வருக!</div>
          <div style="font-size: 11px; margin-top: 2px;">Thank you for shopping with us!</div>
        </div>
      </div>
    `;

    // Close any previous detail modal and open receipt modal
    if (this.modalDetails) this.modalDetails.classList.remove('open');
    this.modalReceipt.classList.add('open');
  }
};

// Make accessible globally
if (typeof window !== 'undefined') {
  window.Sales = Sales;
}
