/**
 * TamilVoice Kirana AI - Sales & Orders Controller
 * Phase 3: Sales Register, Multi-filter, New Sale Workflow, Confirmation, Receipt Preview & Printing.
 */

import { Utils } from './utils.js';
import { Store } from './store.js';
import { ApiService } from './api.js';
import { Settings } from './settings.js';

export const Sales = {
  searchQuery: '',
  dateFilter: 'all',
  paymentFilter: 'all',
  statusFilter: 'all',
  sortBy: 'date-desc',
  pendingSaleData: null,
  activeReceiptSale: null,
  currentCart: [],
  billRef: '',

  init() {
    this.billRef = 'BILL-' + new Date().toISOString().slice(0, 10).replace(/-/g, '') + '-' + Math.floor(100 + Math.random() * 900);
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
    // Current Bill Panel Elements
    this.currentBillPanel = document.getElementById('current-bill-panel');
    this.currentBillRef = document.getElementById('current-bill-ref');
    this.currentBillStatus = document.getElementById('current-bill-status-badge');
    this.currentBillTbody = document.getElementById('current-bill-tbody');
    this.currentBillEmpty = document.getElementById('current-bill-empty');
    this.currentBillSubtotal = document.getElementById('current-bill-subtotal');
    this.currentBillGrandTotal = document.getElementById('current-bill-grand-total');
    this.currentBillPayment = document.getElementById('current-bill-payment-method');
    this.btnBillAddProduct = document.getElementById('btn-bill-add-product');
    this.btnBillCancelAll = document.getElementById('btn-bill-cancel-all');
    this.btnBillCancelCart = document.getElementById('btn-bill-cancel-cart');
    this.btnBillConfirmPay = document.getElementById('btn-bill-confirm-and-pay');

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

    // Back to Edit button in Confirm Sale Modal
    const btnBackToEdit = document.getElementById('btn-back-to-edit-sale');
    if (btnBackToEdit) {
      btnBackToEdit.addEventListener('click', () => {
        if (this.modalConfirmSale) this.modalConfirmSale.classList.remove('open');
        if (this.modalNewSale) this.modalNewSale.classList.add('open');
      });
    }

    // Print Receipt button click
    if (this.btnPrintReceiptNow) {
      this.btnPrintReceiptNow.addEventListener('click', () => {
        window.print();
      });
    }

    // Current Bill Panel Actions
    if (this.btnBillAddProduct) {
      this.btnBillAddProduct.addEventListener('click', () => this.openNewSaleModal());
    }
    if (this.btnBillCancelAll) {
      this.btnBillCancelAll.addEventListener('click', () => this.clearCurrentBill());
    }
    if (this.btnBillCancelCart) {
      this.btnBillCancelCart.addEventListener('click', () => this.clearCurrentBill());
    }
    if (this.btnBillConfirmPay) {
      this.btnBillConfirmPay.addEventListener('click', () => this.confirmAndCheckoutCurrentBill());
    }

    // Voice Cart Synchronization Event
    window.addEventListener('voice-cart-updated', (e) => {
      if (e.detail) this.handleVoiceCartUpdate(e.detail);
    });
  },

  render() {
    this.renderKPIs();
    this.renderTable();
    this.renderCurrentBill();
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
      const allSales = Store.getSales();
      const isEmptySales = allSales.length === 0;
      this.tableBody.innerHTML = `
        <tr>
          <td colspan="9">
            <div class="table-empty-state">
              <svg class="table-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="11" cy="11" r="8"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/>
              </svg>
              <h4 style="font-size: 1rem; color: var(--color-text-primary); margin-top: 4px;">
                ${isEmptySales ? 'No bills recorded yet' : 'No sales records found'}
              </h4>
              <p style="font-size: 0.8125rem; color: var(--color-text-secondary); max-width: 320px;">
                ${isEmptySales ? 'Record your first sale or use voice commands to bill items.' : 'No invoices match your search or filter selection.'}
              </p>
              ${isEmptySales
                ? '<button class="btn btn-sm btn-primary" style="margin-top: 8px;" onclick="document.getElementById(\'sales-btn-open-new\').click();">+ Record First Sale</button>'
                : '<button class="btn btn-sm btn-outline" style="margin-top: 8px;" onclick="document.getElementById(\'sales-btn-reset-filters\').click();">Reset All Filters</button>'
              }
            </div>
          </td>
        </tr>
      `;
      return;
    }

    const currentLang = localStorage.getItem('tv_lang') || 'en';

    this.tableBody.innerHTML = filtered.map(s => {
      const pmClass = (s.payment_method || 'Cash').toLowerCase();
      const payStatus = (s.payment_status || (s.payment_method === 'CREDIT' ? 'PENDING' : 'PAID')).toUpperCase();
      const statusClass = (payStatus === 'PAID') ? 'success' : (payStatus === 'PENDING' ? 'warning' : 'neutral');
      const hasMultiItems = s.items && s.items.length > 1;
      const isSingleItem = s.items && s.items.length === 1;

      let displayProduct = s.product_name;
      let displayQty = `${s.quantity} ${s.unit || ''}`;
      let displayRate = Utils.formatINR(s.unit_price);

      if (hasMultiItems) {
        displayProduct = `<span class="badge-pill neutral" style="font-size: 11px; margin-right: 4px;">${s.items.length} Items</span> ${s.items_summary || s.product_name}`;
        displayQty = `${s.items.length} items`;
        displayRate = '—';
      } else if (isSingleItem) {
        const single = s.items[0];
        displayProduct = single.product_name_snapshot || s.product_name;
        displayQty = `${single.quantity} ${single.unit || ''}`;
        displayRate = Utils.formatINR(single.unit_price);
      } else if (currentLang === 'ta' && s.product_name_ta) {
        displayProduct = s.product_name_ta;
      }

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
              <span class="text-semibold" style="max-width: 260px; display: inline-block; white-space: normal;">${displayProduct}</span>
              ${s.customer_name ? `<span class="text-2xs text-muted">${s.customer_name}</span>` : ''}
            </div>
          </td>
          <td>
            <span class="text-semibold">${displayQty}</span>
          </td>
          <td>
            <span class="text-muted text-xs">${displayRate}</span>
          </td>
          <td>
            <span class="text-semibold text-primary">${Utils.formatINR(s.total_amount)}</span>
          </td>
          <td>
            <span class="payment-badge ${pmClass}">${s.payment_method || 'Cash'}</span>
          </td>
          <td>
            <span class="badge-pill ${statusClass}">
              <span class="status-indicator-dot ${statusClass}"></span>
              ${payStatus}
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

  async executeSale() {
    if (!this.pendingSaleData) return;

    try {
      const saleData = { ...this.pendingSaleData };
      let createdInvoice = null;

      try {
        const res = await ApiService.createSale({
          items: [{
            product_id: Number(saleData.product_id),
            quantity: Number(saleData.quantity)
          }],
          payment_method: saleData.payment_method || 'CASH',
          notes: saleData.notes || `Sold to ${saleData.customer_name}`
        });
        if (res && (res.id || res.transaction_id)) {
          createdInvoice = res.transaction_id || `TX-${res.id}`;
        }
        await Store.syncFromBackend();
        await Store.syncSalesFromBackend();
      } catch (apiErr) {
        console.warn('Backend createSale unavailable, falling back to local Store:', apiErr);
      }

      let invoiceId = createdInvoice;
      if (!invoiceId) {
        const newSale = Store.recordSale(saleData);
        invoiceId = newSale.id;
      }
      this.pendingSaleData = null;

      if (this.modalConfirmSale) this.modalConfirmSale.classList.remove('open');

      Utils.showToast('success', 'Bill Recorded', `Invoice ${invoiceId} created. Inventory deducted.`);

      // Prompt Receipt preview
      setTimeout(() => {
        this.openReceiptModal(invoiceId);
      }, 400);

    } catch (err) {
      Utils.showToast('error', 'Sale Failed', err.message);
    }
  },

  /* =========================================================================
     TRANSACTION DETAILS MODAL
     ========================================================================= */
  openDetailsModal(id) {
    const sale = (typeof id === 'object' && id !== null) ? id : Store.getSaleById(id);
    if (!sale || !this.modalDetails || !this.detailsContent) return;

    this.activeReceiptSale = sale;
    const hasItems = sale.items && sale.items.length > 0;

    let itemsHtml = '';
    if (hasItems) {
      itemsHtml = `
        <table class="receipt-items-table" style="width: 100%; margin: 8px 0; font-size: 0.85rem;">
          <thead>
            <tr style="border-bottom: 1px solid var(--color-border); text-align: left;">
              <th style="padding: 6px 4px;">Item</th>
              <th style="text-align: center; padding: 6px 4px;">Qty</th>
              <th style="text-align: right; padding: 6px 4px;">Rate</th>
              <th style="text-align: right; padding: 6px 4px;">Line Total</th>
            </tr>
          </thead>
          <tbody>
            ${sale.items.map(it => `
              <tr style="border-bottom: 1px dashed var(--color-border);">
                <td style="padding: 6px 4px;"><strong>${it.product_name_snapshot || it.name || it.product_name}</strong></td>
                <td style="text-align: center; padding: 6px 4px;">${it.quantity} ${it.unit || ''}</td>
                <td style="text-align: right; padding: 6px 4px;">${Utils.formatINR(it.unit_price)}</td>
                <td style="text-align: right; padding: 6px 4px; font-weight: 600;">${Utils.formatINR(it.line_total || (it.quantity * it.unit_price))}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } else {
      itemsHtml = `
        <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
          <span class="text-muted">Item Billed:</span>
          <strong>${sale.product_name}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
          <span class="text-muted">Quantity Sold:</span>
          <span>${sale.quantity} ${sale.unit || ''}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
          <span class="text-muted">Unit Rate:</span>
          <span>${Utils.formatINR(sale.unit_price)}</span>
        </div>
      `;
    }

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
            <span class="text-muted">Customer Name:</span>
            <span>${sale.customer_name || 'Counter Walk-in'}</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
            <span class="text-muted">Payment Method:</span>
            <span class="payment-badge ${sale.payment_method ? sale.payment_method.toLowerCase() : 'cash'}">${sale.payment_method || 'CASH'}</span>
          </div>
          
          <div style="margin-top: 6px;">
            <div style="font-weight: 600; font-size: 0.8rem; color: var(--color-text-secondary); margin-bottom: 4px;">Itemized Products:</div>
            ${itemsHtml}
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
  openReceiptModal(saleOrId) {
    let sale = null;
    if (typeof saleOrId === 'object' && saleOrId !== null) {
      sale = saleOrId;
    } else {
      sale = Store.getSaleById(saleOrId);
    }
    if (!sale || !this.modalReceipt || !this.receiptContainer) return;

    this.activeReceiptSale = sale;
    const store = (Settings && typeof Settings.getStoreDetails === 'function')
      ? Settings.getStoreDetails()
      : {
          shop_name: 'Arjun Grocery Store',
          shop_name_ta: 'அர்ஜுன் மளிகைக் கடை',
          owner_name: 'Jeevan',
          phone: '+91 98401 23456',
          address: '42, North Mada Street, Mylapore, Chennai, Tamil Nadu - 600004',
          gstin: '33ABCDE1234F1Z5',
          receipt_footer: 'நன்றி! மீண்டும் வருக! / Thank you, visit again!'
        };

    // Build Receipt HTML
    this.receiptContainer.innerHTML = `
      <div class="receipt-wrapper">
        <div class="receipt-header">
          <div style="font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 1px; margin-bottom: 2px;">TAMILVOICE KIRANA AI</div>
          <div class="receipt-shop-title">${(store.shop_name || 'ARJUN GROCERY STORE').toUpperCase()}</div>
          ${store.shop_name_ta ? `<div class="receipt-shop-tamil">${store.shop_name_ta}</div>` : ''}
          <div class="receipt-shop-meta">${store.address || ''} • Ph: ${store.phone}</div>
          ${store.gstin ? `<div style="font-size: 11px; color: #475569; font-weight: 600; margin-top: 2px;">GSTIN: ${store.gstin}</div>` : ''}
          <div class="receipt-watermark">RETAIL INVOICE / வாடிக்கையாளர் ரசீது</div>
        </div>

        <div class="receipt-info-row">
          <span>Invoice No: <strong>${sale.id}</strong></span>
          <span>Date: ${Utils.formatDate(sale.date)}</span>
        </div>
        <div class="receipt-info-row">
          <span>Time: ${Utils.formatTime(sale.date)}</span>
          <span>Cashier: ${store.owner_name}</span>
        </div>
        <div class="receipt-info-row">
          <span>Customer: ${sale.customer_name || 'Walk-in Counter'}</span>
          <span>Payment: <strong>${sale.payment_method || 'CASH'}</strong> (${(sale.payment_status || (sale.payment_method === 'CREDIT' ? 'PENDING' : 'PAID')).toUpperCase()})</span>
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
            ${(sale.items && sale.items.length > 0)
              ? sale.items.map(it => `
                <tr>
                  <td><strong>${it.product_name_snapshot || it.name || it.product_name}</strong></td>
                  <td style="text-align: center;">${it.quantity} ${it.unit || ''}</td>
                  <td style="text-align: right;">${Utils.formatINR(it.unit_price)}</td>
                  <td style="text-align: right; font-weight: 600;">${Utils.formatINR(it.line_total || (it.quantity * it.unit_price))}</td>
                </tr>
              `).join('')
              : `
                <tr>
                  <td>
                    <strong>${sale.product_name}</strong>
                    ${sale.product_name_ta ? `<div style="font-size: 10px; color: #64748B;">${sale.product_name_ta}</div>` : ''}
                  </td>
                  <td style="text-align: center;">${sale.quantity} ${sale.unit || ''}</td>
                  <td style="text-align: right;">${Utils.formatINR(sale.unit_price)}</td>
                  <td style="text-align: right; font-weight: 600;">${Utils.formatINR(sale.total_amount)}</td>
                </tr>
              `
            }
          </tbody>
        </table>

        <div class="receipt-total-row">
          <span>GRAND TOTAL AMOUNT:</span>
          <span>${Utils.formatINR(sale.total_amount)}</span>
        </div>

        <div class="receipt-footer">
          <div>Goods once sold can be exchanged within 2 days with bill.</div>
          <div class="receipt-thankyou-tamil">${store.receipt_footer || 'நன்றி! மீண்டும் வருக!'}</div>
          <div style="font-size: 11px; margin-top: 2px;">Thank you for shopping with us!</div>
        </div>
      </div>
    `;

    // Close any previous detail modal and open receipt modal
    if (this.modalDetails) this.modalDetails.classList.remove('open');
    this.modalReceipt.classList.add('open');
  },

  /* =========================================================================
     CURRENT BILL (தற்போதைய பில்) METHODS
     ========================================================================= */

  handleVoiceCartUpdate(data) {
    if (!data) return;
    if (data.ref) {
      this.billRef = `BILL-${data.ref.slice(0, 8).toUpperCase()}`;
    }
    if (data.items && Array.isArray(data.items)) {
      this.currentCart = data.items.map(it => ({
        product_id: it.product_id,
        name: it.product_name,
        quantity: it.quantity,
        unit: it.unit || 'unit',
        unit_price: it.unit_price,
        line_total: it.line_total || (it.quantity * it.unit_price),
        current_stock: it.current_stock,
        projected_stock: it.projected_stock
      }));
    } else if (data.cleared) {
      this.currentCart = [];
      this.billRef = 'BILL-' + new Date().toISOString().slice(0, 10).replace(/-/g, '') + '-' + Math.floor(100 + Math.random() * 900);
    }
    this.renderCurrentBill();
  },

  renderCurrentBill() {
    if (!this.currentBillTbody) return;

    if (this.currentBillRef) {
      this.currentBillRef.textContent = this.billRef;
    }

    if (!this.currentCart || this.currentCart.length === 0) {
      this.currentBillTbody.innerHTML = '';
      if (this.currentBillEmpty) this.currentBillEmpty.style.display = 'block';
      if (this.currentBillSubtotal) this.currentBillSubtotal.textContent = '₹0.00';
      if (this.currentBillGrandTotal) this.currentBillGrandTotal.textContent = '₹0.00';
      if (this.currentBillStatus) {
        this.currentBillStatus.textContent = 'Cart Empty';
        this.currentBillStatus.className = 'badge-pill neutral';
      }
      return;
    }

    if (this.currentBillEmpty) this.currentBillEmpty.style.display = 'none';

    const grandTotal = this.currentCart.reduce((sum, it) => sum + (Number(it.line_total) || (it.quantity * it.unit_price)), 0);
    const totalQty = this.currentCart.reduce((sum, it) => sum + Number(it.quantity), 0);

    if (this.currentBillSubtotal) this.currentBillSubtotal.textContent = Utils.formatCurrency(grandTotal);
    if (this.currentBillGrandTotal) this.currentBillGrandTotal.textContent = Utils.formatCurrency(grandTotal);
    if (this.currentBillStatus) {
      this.currentBillStatus.textContent = `${this.currentCart.length} products (${totalQty} units)`;
      this.currentBillStatus.className = 'badge-pill warning';
    }

    this.currentBillTbody.innerHTML = this.currentCart.map((item, idx) => {
      const lineAmt = item.line_total || (item.quantity * item.unit_price);
      return `
        <tr>
          <td><strong style="color: #94A3B8;">${idx + 1}</strong></td>
          <td>
            <strong>${item.name}</strong>
            ${item.current_stock !== undefined ? `<div style="font-size: 0.75rem; color: #94A3B8;">Stock: ${item.current_stock} &rarr; <span class="text-primary">${item.projected_stock !== undefined ? item.projected_stock : (item.current_stock - item.quantity)} ${item.unit}</span></div>` : ''}
          </td>
          <td>
            <div style="display: flex; align-items: center; gap: 0.35rem;">
              <button class="btn btn-outline btn-xs btn-cart-dec" data-idx="${idx}" style="padding: 2px 6px;">-</button>
              <input type="number" min="0.1" step="any" class="form-input cart-qty-input" data-idx="${idx}" value="${item.quantity}" style="width: 55px; text-align: center; padding: 2px 4px; font-size: 0.85rem;">
              <button class="btn btn-outline btn-xs btn-cart-inc" data-idx="${idx}" style="padding: 2px 6px;">+</button>
              <span style="font-size: 0.8rem; color: #94A3B8; margin-left: 2px;">${item.unit}</span>
            </div>
          </td>
          <td style="font-size: 0.9rem;">₹${Number(item.unit_price).toFixed(2)}</td>
          <td><strong class="text-success" style="font-size: 0.95rem;">₹${Number(lineAmt).toFixed(2)}</strong></td>
          <td style="text-align: center;">
            <button class="btn btn-ghost btn-xs text-danger btn-cart-remove" data-idx="${idx}" title="Remove Item" style="color: #EF4444; font-size: 1rem; line-height: 1;">&times;</button>
          </td>
        </tr>
      `;
    }).join('');

    // Bind item buttons
    this.currentBillTbody.querySelectorAll('.btn-cart-dec').forEach(btn => {
      btn.addEventListener('click', () => {
        const i = parseInt(btn.getAttribute('data-idx'), 10);
        if (this.currentCart[i].quantity > 1) {
          this.currentCart[i].quantity -= 1;
          this.currentCart[i].line_total = this.currentCart[i].quantity * this.currentCart[i].unit_price;
          this.renderCurrentBill();
        } else {
          this.removeFromCurrentBill(i);
        }
      });
    });

    this.currentBillTbody.querySelectorAll('.btn-cart-inc').forEach(btn => {
      btn.addEventListener('click', () => {
        const i = parseInt(btn.getAttribute('data-idx'), 10);
        this.currentCart[i].quantity += 1;
        this.currentCart[i].line_total = this.currentCart[i].quantity * this.currentCart[i].unit_price;
        this.renderCurrentBill();
      });
    });

    this.currentBillTbody.querySelectorAll('.cart-qty-input').forEach(input => {
      input.addEventListener('change', (e) => {
        const i = parseInt(input.getAttribute('data-idx'), 10);
        const val = parseFloat(e.target.value);
        if (!isNaN(val) && val > 0) {
          this.currentCart[i].quantity = val;
          this.currentCart[i].line_total = val * this.currentCart[i].unit_price;
          this.renderCurrentBill();
        } else {
          this.renderCurrentBill();
        }
      });
    });

    this.currentBillTbody.querySelectorAll('.btn-cart-remove').forEach(btn => {
      btn.addEventListener('click', () => {
        const i = parseInt(btn.getAttribute('data-idx'), 10);
        this.removeFromCurrentBill(i);
      });
    });
  },

  removeFromCurrentBill(index) {
    if (this.currentCart[index]) {
      const removed = this.currentCart.splice(index, 1);
      Utils.showToast('info', 'Item Removed', `${removed[0]?.name} removed from current bill.`);
      this.renderCurrentBill();
    }
  },

  clearCurrentBill() {
    this.currentCart = [];
    this.billRef = 'BILL-' + new Date().toISOString().slice(0, 10).replace(/-/g, '') + '-' + Math.floor(100 + Math.random() * 900);
    this.renderCurrentBill();
    Utils.showToast('info', 'Bill Cleared', 'Current bill cart has been cleared.');
  },

  async confirmAndCheckoutCurrentBill() {
    if (!this.currentCart || this.currentCart.length === 0) {
      Utils.showToast('warning', 'Empty Cart', 'Please add products to the bill before confirming.');
      return;
    }

    const paymentMethod = this.currentBillPayment ? this.currentBillPayment.value : 'CASH';
    const saleItems = this.currentCart.map(it => ({
      product_id: it.product_id,
      quantity: Number(it.quantity)
    }));

    try {
      if (this.btnBillConfirmPay) {
        this.btnBillConfirmPay.disabled = true;
        this.btnBillConfirmPay.innerHTML = '<span>Processing Bill...</span>';
      }

      const res = await ApiService.createSale({
        items: saleItems,
        payment_method: paymentMethod,
        notes: `Counter Checkout (${this.billRef})`
      });

      if (res && (res.transaction_id || res.id)) {
        Utils.showToast('success', 'Bill Completed', `Invoice ${res.transaction_id} created successfully! Total: ₹${res.total_amount}`);
        
        // Refresh store
        if (Store && typeof Store.syncFromBackend === 'function') {
          await Store.syncFromBackend();
        }
        if (Store && typeof Store.syncSalesFromBackend === 'function') {
          await Store.syncSalesFromBackend();
        }

        const completedSale = {
          id: res.transaction_id,
          date: res.created_at || new Date().toISOString(),
          customer_name: res.customer_name || 'Walk-in Counter',
          payment_method: res.payment_method || paymentMethod,
          total_amount: res.total_amount,
          items: res.items || this.currentCart.map(c => ({
            product_name_snapshot: c.name,
            quantity: c.quantity,
            unit: c.unit,
            unit_price: c.unit_price,
            line_total: c.line_total || (c.quantity * c.unit_price)
          }))
        };

        this.clearCurrentBill();

        // Open Printable Receipt Preview Modal
        this.openReceiptModal(completedSale);
      } else {
        throw new Error(res?.detail || 'Failed to complete sale');
      }
    } catch (err) {
      console.error('[Sales] Checkout error:', err);
      Utils.showToast('error', 'Checkout Error', err.message || 'Could not complete bill transaction.');
    } finally {
      if (this.btnBillConfirmPay) {
        this.btnBillConfirmPay.disabled = false;
        this.btnBillConfirmPay.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          <span>Confirm & Generate Bill</span>
        `;
      }
    }
  }
};

// Make accessible globally
if (typeof window !== 'undefined') {
  window.Sales = Sales;
}

