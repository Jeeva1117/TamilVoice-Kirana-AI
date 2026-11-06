/**
 * TamilVoice Kirana AI - Inventory Management Controller
 * Phase 3: Product Inventory, Filtering, Sorting, Add/Edit/Delete, Stock Adjustments & CSV Export.
 */

import { Utils } from './utils.js';
import { Store } from './store.js';

export const Inventory = {
  searchQuery: '',
  categoryFilter: 'all',
  statusFilter: 'all',
  sortBy: 'name-asc',
  selectedProductId: null,
  deleteTargetId: null,

  init() {
    this.cacheDOM();
    this.bindEvents();
    this.render();

    // Listen for reactive store updates (e.g. from Sales, Voice, or Reset)
    window.addEventListener('store-updated', () => {
      this.render();
    });

    // Re-render when language toggle occurs
    window.addEventListener('language-changed', () => {
      this.render();
    });
  },

  cacheDOM() {
    // KPI elements
    this.kpiTotalProducts = document.getElementById('inv-kpi-total-products');
    this.kpiStockValue = document.getElementById('inv-kpi-stock-value');
    this.kpiLowStock = document.getElementById('inv-kpi-low-stock');
    this.kpiOutOfStock = document.getElementById('inv-kpi-out-of-stock');

    // Filter elements
    this.searchInput = document.getElementById('inv-search-input');
    this.categorySelect = document.getElementById('inv-category-filter');
    this.statusSelect = document.getElementById('inv-status-filter');
    this.sortSelect = document.getElementById('inv-sort-filter');
    this.btnResetFilters = document.getElementById('inv-btn-reset-filters');
    this.btnExportCSV = document.getElementById('inv-btn-export-csv');
    this.btnOpenAddModal = document.getElementById('inv-btn-open-add');
    this.btnResetDemoData = document.getElementById('inv-btn-reset-demo');

    // Table elements
    this.tableBody = document.getElementById('inventory-table-body');
    this.tableCountBadge = document.getElementById('inv-table-count-badge');

    // Modals
    this.modalAdd = document.getElementById('modal-add-product');
    this.formAdd = document.getElementById('form-add-product');
    this.modalEdit = document.getElementById('modal-edit-product');
    this.formEdit = document.getElementById('form-edit-product');
    this.modalDelete = document.getElementById('modal-delete-product');
    this.deleteProductName = document.getElementById('delete-product-name-display');
    this.btnConfirmDelete = document.getElementById('btn-confirm-delete-product');
    this.modalAdjust = document.getElementById('modal-adjust-stock');
    this.formAdjust = document.getElementById('form-adjust-stock');
    this.adjustProdName = document.getElementById('adjust-product-name');
    this.adjustCurrentStock = document.getElementById('adjust-current-stock');
    this.adjustProjectedStock = document.getElementById('adjust-projected-stock');
    this.adjustType = document.getElementById('adjust-type-select');
    this.adjustQtyInput = document.getElementById('adjust-quantity-input');
    this.modalDetails = document.getElementById('modal-product-details');
    this.detailsBody = document.getElementById('product-details-content');
  },

  bindEvents() {
    // Search input (debounced)
    if (this.searchInput) {
      this.searchInput.addEventListener('input', Utils.debounce((e) => {
        this.searchQuery = e.target.value.trim().toLowerCase();
        this.renderTable();
      }, 250));
    }

    // Category filter
    if (this.categorySelect) {
      this.categorySelect.addEventListener('change', (e) => {
        this.categoryFilter = e.target.value;
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

    // Export CSV
    if (this.btnExportCSV) {
      this.btnExportCSV.addEventListener('click', () => this.exportCSV());
    }

    // Open Add Product Modal
    if (this.btnOpenAddModal) {
      this.btnOpenAddModal.addEventListener('click', () => this.openAddModal());
    }

    // Reset Demo Data
    if (this.btnResetDemoData) {
      this.btnResetDemoData.addEventListener('click', () => {
        if (confirm('Reset all demo inventory and sales to default initial values?')) {
          Store.resetDemoData();
          Utils.showToast('info', 'Reset Complete', 'Demo inventory and sales restored to initial records.');
        }
      });
    }

    // Form Add Product
    if (this.formAdd) {
      this.formAdd.addEventListener('submit', (e) => this.handleAddSubmit(e));
    }

    // Form Edit Product
    if (this.formEdit) {
      this.formEdit.addEventListener('submit', (e) => this.handleEditSubmit(e));
    }

    // Confirm Delete
    if (this.btnConfirmDelete) {
      this.btnConfirmDelete.addEventListener('click', () => this.handleDeleteConfirm());
    }

    // Stock Adjustment Form and Live Projection
    if (this.adjustType && this.adjustQtyInput) {
      const updateProjection = () => this.updateAdjustProjection();
      this.adjustType.addEventListener('change', updateProjection);
      this.adjustQtyInput.addEventListener('input', updateProjection);
    }

    if (this.formAdjust) {
      this.formAdjust.addEventListener('submit', (e) => this.handleAdjustSubmit(e));
    }

    // Generic Modal Close Buttons
    document.querySelectorAll('[data-close-modal]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const modal = e.target.closest('.modal-backdrop');
        if (modal) modal.classList.remove('open');
      });
    });

    // Close on backdrop click
    document.querySelectorAll('.modal-backdrop').forEach(modal => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('open');
      });
    });
  },

  render() {
    this.renderKPIs();
    this.renderTable();
  },

  renderKPIs() {
    const products = Store.getProducts();

    const totalProducts = products.length;
    let totalStockValue = 0;
    let lowStockCount = 0;
    let outOfStockCount = 0;

    products.forEach(p => {
      const stock = Number(p.stock) || 0;
      const price = Number(p.purchase_price) || 0;
      totalStockValue += stock * price;

      const status = Store.calculateStatus(p);
      if (status === 'Low Stock') lowStockCount++;
      if (status === 'Out of Stock') outOfStockCount++;
    });

    if (this.kpiTotalProducts) this.kpiTotalProducts.textContent = totalProducts.toString();
    if (this.kpiStockValue) this.kpiStockValue.textContent = Utils.formatINR(totalStockValue);
    if (this.kpiLowStock) this.kpiLowStock.textContent = lowStockCount.toString();
    if (this.kpiOutOfStock) this.kpiOutOfStock.textContent = outOfStockCount.toString();
  },

  getFilteredProducts() {
    let products = Store.getProducts();

    // 1. Text Search (Name or SKU)
    if (this.searchQuery) {
      products = products.filter(p => {
        const nameEn = (p.name_en || '').toLowerCase();
        const nameTa = (p.name_ta || '').toLowerCase();
        const sku = (p.sku || '').toLowerCase();
        return nameEn.includes(this.searchQuery) || nameTa.includes(this.searchQuery) || sku.includes(this.searchQuery);
      });
    }

    // 2. Category Filter
    if (this.categoryFilter && this.categoryFilter !== 'all') {
      products = products.filter(p => (p.category || '').toLowerCase() === this.categoryFilter.toLowerCase());
    }

    // 3. Stock Status Filter
    if (this.statusFilter && this.statusFilter !== 'all') {
      products = products.filter(p => {
        const status = Store.calculateStatus(p).toLowerCase().replace(/\s+/g, '-');
        return status === this.statusFilter.toLowerCase();
      });
    }

    // 4. Sorting
    products.sort((a, b) => {
      switch (this.sortBy) {
        case 'name-asc':
          return (a.name_en || '').localeCompare(b.name_en || '');
        case 'name-desc':
          return (b.name_en || '').localeCompare(a.name_en || '');
        case 'qty-asc':
          return (Number(a.stock) || 0) - (Number(b.stock) || 0);
        case 'qty-desc':
          return (Number(b.stock) || 0) - (Number(a.stock) || 0);
        case 'price-asc':
          return (Number(a.selling_price) || 0) - (Number(b.selling_price) || 0);
        case 'price-desc':
          return (Number(b.selling_price) || 0) - (Number(a.selling_price) || 0);
        default:
          return 0;
      }
    });

    return products;
  },

  renderTable() {
    if (!this.tableBody) return;

    const filtered = this.getFilteredProducts();

    if (this.tableCountBadge) {
      this.tableCountBadge.textContent = `${filtered.length} items`;
    }

    if (!filtered.length) {
      this.tableBody.innerHTML = `
        <tr>
          <td colspan="9">
            <div class="table-empty-state">
              <svg class="table-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><line x1="8" x2="14" y1="11" y2="11"/>
              </svg>
              <h4 style="font-size: 1rem; color: var(--color-text-primary); margin-top: 4px;">No products found</h4>
              <p style="font-size: 0.8125rem; color: var(--color-text-secondary); max-width: 320px;">
                No inventory records match your search or filter criteria.
              </p>
              <button class="btn btn-sm btn-outline" style="margin-top: 8px;" onclick="document.getElementById('inv-btn-reset-filters').click();">
                Reset All Filters
              </button>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    const currentLang = localStorage.getItem('tv_lang') || 'en';

    this.tableBody.innerHTML = filtered.map(p => {
      const status = Store.calculateStatus(p);
      const statusClass = status === 'In Stock' ? 'in-stock' : (status === 'Low Stock' ? 'low-stock' : 'out-of-stock');
      const statusText = currentLang === 'ta'
        ? (status === 'In Stock' ? 'இருப்பில் உள்ளது' : (status === 'Low Stock' ? 'குறைந்த இருப்பு' : 'இருப்பு இல்லை'))
        : status;

      return `
        <tr data-product-id="${p.id}">
          <td>
            <div class="product-cell-name" onclick="window.Inventory.openDetailModal(${p.id})">
              <span class="product-cell-primary">${p.name_en}</span>
              <span class="product-cell-tamil">${p.name_ta || ''}</span>
            </div>
          </td>
          <td>
            <span class="sku-badge">${p.sku || 'N/A'}</span>
          </td>
          <td>
            <span class="category-tag">${p.category || 'Grocery'}</span>
          </td>
          <td>
            <span class="text-semibold ${status === 'Out of Stock' ? 'text-danger' : (status === 'Low Stock' ? 'text-warning' : '')}">
              ${p.stock} <span class="text-xs text-muted">${p.unit}</span>
            </span>
          </td>
          <td>
            <span class="text-xs text-muted">${p.unit}</span>
          </td>
          <td>
            <span class="text-muted">${Utils.formatINR(p.purchase_price)}</span>
          </td>
          <td>
            <span class="text-semibold text-primary">${Utils.formatINR(p.selling_price)}</span>
          </td>
          <td>
            <span class="status-pill ${statusClass}">
              <span class="status-indicator-dot ${statusClass}"></span>
              ${statusText}
            </span>
          </td>
          <td>
            <div class="table-actions-cell">
              <button class="btn-table-action" title="View Details" onclick="window.Inventory.openDetailModal(${p.id})">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
              </button>
              <button class="btn-table-action adjust-action" title="Stock Adjustment" onclick="window.Inventory.openAdjustModal(${p.id})">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12H3M12 3v18"/></svg>
              </button>
              <button class="btn-table-action" title="Edit Product" onclick="window.Inventory.openEditModal(${p.id})">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
              </button>
              <button class="btn-table-action delete-action" title="Delete Product" onclick="window.Inventory.openDeleteModal(${p.id})">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  resetFilters() {
    this.searchQuery = '';
    this.categoryFilter = 'all';
    this.statusFilter = 'all';
    this.sortBy = 'name-asc';

    if (this.searchInput) this.searchInput.value = '';
    if (this.categorySelect) this.categorySelect.value = 'all';
    if (this.statusSelect) this.statusSelect.value = 'all';
    if (this.sortSelect) this.sortSelect.value = 'name-asc';

    this.renderTable();
    Utils.showToast('info', 'Filters Reset', 'All inventory search filters have been cleared.');
  },

  /* =========================================================================
     ADD PRODUCT MODAL & VALIDATION
     ========================================================================= */
  openAddModal() {
    if (!this.modalAdd || !this.formAdd) return;
    this.formAdd.reset();

    // Auto-generate suggested SKU
    const skuInput = document.getElementById('add-product-sku');
    if (skuInput) {
      const count = Store.getProducts().length + 1;
      skuInput.value = `SKU-GRO-${String(count).padStart(3, '0')}`;
    }

    this.modalAdd.classList.add('open');
  },

  handleAddSubmit(e) {
    e.preventDefault();

    const nameEn = document.getElementById('add-product-name-en').value.trim();
    const nameTa = document.getElementById('add-product-name-ta').value.trim();
    const sku = document.getElementById('add-product-sku').value.trim();
    const category = document.getElementById('add-product-category').value;
    const stock = parseFloat(document.getElementById('add-product-stock').value);
    const minStock = parseFloat(document.getElementById('add-product-min-stock').value);
    const unit = document.getElementById('add-product-unit').value;
    const purchasePrice = parseFloat(document.getElementById('add-product-purchase-price').value);
    const sellingPrice = parseFloat(document.getElementById('add-product-selling-price').value);
    const description = document.getElementById('add-product-desc').value.trim();

    // Validations
    if (!nameEn) {
      Utils.showToast('error', 'Validation Error', 'English product name is required.');
      return;
    }

    if (isNaN(stock) || stock < 0) {
      Utils.showToast('error', 'Validation Error', 'Stock quantity must be a non-negative number.');
      return;
    }

    if (isNaN(purchasePrice) || purchasePrice < 0 || isNaN(sellingPrice) || sellingPrice < 0) {
      Utils.showToast('error', 'Validation Error', 'Purchase and selling prices must be valid non-negative numbers.');
      return;
    }

    // SKU uniqueness check
    if (sku) {
      const existing = Store.getProducts().find(p => (p.sku || '').toLowerCase() === sku.toLowerCase());
      if (existing) {
        Utils.showToast('error', 'SKU Exists', `SKU "${sku}" is already assigned to ${existing.name_en}.`);
        return;
      }
    }

    const newProduct = Store.addProduct({
      name_en: nameEn,
      name_ta: nameTa || nameEn,
      sku: sku || `SKU-${category.slice(0, 3).toUpperCase()}-${Date.now().toString().slice(-4)}`,
      category,
      stock,
      min_stock: isNaN(minStock) ? 5 : minStock,
      unit,
      purchase_price: purchasePrice,
      selling_price: sellingPrice,
      description
    });

    this.modalAdd.classList.remove('open');
    Utils.showToast('success', 'Product Added', `${newProduct.name_en} successfully added to inventory.`);
  },

  /* =========================================================================
     EDIT PRODUCT MODAL
     ========================================================================= */
  openEditModal(id) {
    const product = Store.getProductById(id);
    if (!product || !this.modalEdit) return;

    this.selectedProductId = id;

    document.getElementById('edit-prod-id').value = product.id;
    document.getElementById('edit-prod-name-en').value = product.name_en;
    document.getElementById('edit-prod-name-ta').value = product.name_ta || '';
    document.getElementById('edit-prod-sku').value = product.sku || '';
    document.getElementById('edit-prod-category').value = product.category || 'Grocery';
    document.getElementById('edit-prod-stock').value = product.stock;
    document.getElementById('edit-prod-min-stock').value = product.min_stock;
    document.getElementById('edit-prod-unit').value = product.unit || 'kg';
    document.getElementById('edit-prod-purchase-price').value = product.purchase_price;
    document.getElementById('edit-prod-selling-price').value = product.selling_price;
    document.getElementById('edit-prod-desc').value = product.description || '';

    this.modalEdit.classList.add('open');
  },

  handleEditSubmit(e) {
    e.preventDefault();
    if (!this.selectedProductId) return;

    const nameEn = document.getElementById('edit-prod-name-en').value.trim();
    const nameTa = document.getElementById('edit-prod-name-ta').value.trim();
    const sku = document.getElementById('edit-prod-sku').value.trim();
    const category = document.getElementById('edit-prod-category').value;
    const stock = parseFloat(document.getElementById('edit-prod-stock').value);
    const minStock = parseFloat(document.getElementById('edit-prod-min-stock').value);
    const unit = document.getElementById('edit-prod-unit').value;
    const purchasePrice = parseFloat(document.getElementById('edit-prod-purchase-price').value);
    const sellingPrice = parseFloat(document.getElementById('edit-prod-selling-price').value);
    const description = document.getElementById('edit-prod-desc').value.trim();

    if (!nameEn) {
      Utils.showToast('error', 'Validation Error', 'Product name cannot be empty.');
      return;
    }

    // SKU uniqueness check against other products
    if (sku) {
      const existing = Store.getProducts().find(p => p.id !== this.selectedProductId && (p.sku || '').toLowerCase() === sku.toLowerCase());
      if (existing) {
        Utils.showToast('error', 'SKU Conflict', `SKU "${sku}" is already in use by ${existing.name_en}.`);
        return;
      }
    }

    const updated = Store.updateProduct(this.selectedProductId, {
      name_en: nameEn,
      name_ta: nameTa,
      sku,
      category,
      stock,
      min_stock: minStock,
      unit,
      purchase_price: purchasePrice,
      selling_price: sellingPrice,
      description
    });

    this.modalEdit.classList.remove('open');
    Utils.showToast('success', 'Product Updated', `${updated.name_en} details saved.`);
  },

  /* =========================================================================
     DELETE PRODUCT MODAL
     ========================================================================= */
  openDeleteModal(id) {
    const product = Store.getProductById(id);
    if (!product || !this.modalDelete) return;

    this.deleteTargetId = id;
    if (this.deleteProductName) {
      this.deleteProductName.textContent = `${product.name_en} (${product.sku || 'No SKU'})`;
    }

    this.modalDelete.classList.add('open');
  },

  handleDeleteConfirm() {
    if (!this.deleteTargetId) return;

    const product = Store.getProductById(this.deleteTargetId);
    const name = product ? product.name_en : 'Product';

    Store.deleteProduct(this.deleteTargetId);
    this.deleteTargetId = null;
    this.modalDelete.classList.remove('open');

    Utils.showToast('warning', 'Product Removed', `"${name}" was deleted from inventory.`);
  },

  /* =========================================================================
     STOCK ADJUSTMENT MODAL
     ========================================================================= */
  openAdjustModal(id) {
    const product = Store.getProductById(id);
    if (!product || !this.modalAdjust) return;

    this.selectedProductId = id;

    if (this.adjustProdName) {
      this.adjustProdName.textContent = `${product.name_en} (${product.sku || ''})`;
    }

    if (this.adjustCurrentStock) {
      this.adjustCurrentStock.textContent = `${product.stock} ${product.unit}`;
    }

    if (this.adjustQtyInput) {
      this.adjustQtyInput.value = 5;
    }

    if (this.adjustType) {
      this.adjustType.value = 'Add Stock';
    }

    this.updateAdjustProjection();
    this.modalAdjust.classList.add('open');
  },

  updateAdjustProjection() {
    if (!this.selectedProductId) return;
    const product = Store.getProductById(this.selectedProductId);
    if (!product) return;

    const curr = Number(product.stock) || 0;
    const qty = parseFloat(this.adjustQtyInput.value) || 0;
    const type = this.adjustType.value;

    let projected = curr;
    if (type === 'Add Stock') projected = curr + qty;
    if (type === 'Remove Stock') projected = Math.max(0, curr - qty);
    if (type === 'Set Current Stock') projected = Math.max(0, qty);

    if (this.adjustProjectedStock) {
      this.adjustProjectedStock.textContent = `${projected} ${product.unit}`;
      this.adjustProjectedStock.className = `projection-val ${projected <= 0 ? 'text-danger' : (projected <= product.min_stock ? 'text-warning' : 'text-success')}`;
    }
  },

  handleAdjustSubmit(e) {
    e.preventDefault();
    if (!this.selectedProductId) return;

    const product = Store.getProductById(this.selectedProductId);
    if (!product) return;

    const type = this.adjustType.value;
    const qty = parseFloat(this.adjustQtyInput.value);
    const reason = document.getElementById('adjust-reason-select').value;
    const notes = document.getElementById('adjust-notes-input').value.trim();

    if (isNaN(qty) || qty < 0) {
      Utils.showToast('error', 'Invalid Quantity', 'Please enter a valid non-negative quantity.');
      return;
    }

    const fullReason = notes ? `${reason}: ${notes}` : reason;
    const res = Store.adjustStock(this.selectedProductId, type, qty, fullReason);

    this.modalAdjust.classList.remove('open');
    Utils.showToast('success', 'Stock Adjusted', `${product.name_en} stock updated from ${res.previousStock} to ${res.newStock} ${product.unit}.`);
  },

  /* =========================================================================
     PRODUCT DETAILS & MOVEMENT TIMELINE
     ========================================================================= */
  openDetailModal(id) {
    const product = Store.getProductById(id);
    if (!product || !this.modalDetails || !this.detailsBody) return;

    const status = Store.calculateStatus(product);
    const movements = Store.getMovements(id);

    this.detailsBody.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: var(--space-4);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <h3 style="font-size: 1.125rem; font-weight: 700; color: var(--color-text-primary);">${product.name_en}</h3>
            <span style="font-family: var(--font-family-tamil); color: var(--color-text-muted); font-size: 0.875rem;">${product.name_ta || ''}</span>
            <div style="margin-top: 4px;"><span class="sku-badge">${product.sku || 'N/A'}</span> <span class="category-tag">${product.category}</span></div>
          </div>
          <span class="status-pill ${status === 'In Stock' ? 'in-stock' : (status === 'Low Stock' ? 'low-stock' : 'out-of-stock')}">
            ${status}
          </span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-3); background: var(--color-bg); padding: var(--space-3); border-radius: var(--radius-lg); border: 1px solid var(--color-border); text-align: center;">
          <div>
            <div class="projection-label">Current Stock</div>
            <div style="font-size: 1.125rem; font-weight: 700; color: var(--color-text-primary);">${product.stock} ${product.unit}</div>
          </div>
          <div>
            <div class="projection-label">Min Stock Threshold</div>
            <div style="font-size: 1.125rem; font-weight: 700; color: var(--color-text-secondary);">${product.min_stock} ${product.unit}</div>
          </div>
          <div>
            <div class="projection-label">Selling Margin</div>
            <div style="font-size: 1.125rem; font-weight: 700; color: var(--color-success);">${Utils.formatINR(product.selling_price - product.purchase_price)}</div>
          </div>
        </div>

        <p style="font-size: 0.8125rem; color: var(--color-text-secondary); line-height: 1.5;">
          ${product.description || 'No description provided for this catalog item.'}
        </p>

        <div>
          <h4 style="font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); margin-bottom: var(--space-2);">
            Stock Movement History (சரக்கு இருப்பு பதிவு)
          </h4>
          <div class="timeline-list">
            ${movements.length ? movements.map(m => `
              <div class="timeline-item">
                <span class="timeline-dot ${m.quantity >= 0 ? 'positive' : 'negative'}"></span>
                <div style="flex: 1;">
                  <div style="display: flex; justify-content: space-between;">
                    <strong>${m.type}</strong>
                    <span style="font-weight: 700; color: ${m.quantity >= 0 ? 'var(--color-success)' : 'var(--color-danger)'};">
                      ${m.quantity >= 0 ? `+${m.quantity}` : m.quantity} ${m.unit}
                    </span>
                  </div>
                  <div style="color: var(--color-text-muted); font-size: 0.6875rem; margin-top: 2px;">
                    ${m.reason || 'Movement logged'} • ${Utils.formatDate(m.date)} ${Utils.formatTime(m.date)}
                  </div>
                </div>
              </div>
            `).join('') : '<div style="color: var(--color-text-muted); font-size: 0.75rem; text-align: center; padding: 1rem;">No movement logs recorded yet.</div>'}
          </div>
        </div>
      </div>
    `;

    this.modalDetails.classList.add('open');
  },

  /* =========================================================================
     CSV EXPORT
     ========================================================================= */
  exportCSV() {
    const products = this.getFilteredProducts();
    if (!products.length) {
      Utils.showToast('warning', 'Export Empty', 'No products available in the current filter to export.');
      return;
    }

    const headers = ['Product Name', 'Tamil Name', 'SKU', 'Category', 'Quantity', 'Unit', 'Purchase Price (INR)', 'Selling Price (INR)', 'Stock Status'];
    const rows = products.map(p => [
      `"${(p.name_en || '').replace(/"/g, '""')}"`,
      `"${(p.name_ta || '').replace(/"/g, '""')}"`,
      `"${(p.sku || '').replace(/"/g, '""')}"`,
      `"${(p.category || '').replace(/"/g, '""')}"`,
      p.stock,
      `"${p.unit || ''}"`,
      p.purchase_price,
      p.selling_price,
      `"${Store.calculateStatus(p)}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    const dateStamp = new Date().toISOString().slice(0, 10);
    link.setAttribute('download', `TamilVoice_Kirana_Inventory_${dateStamp}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    Utils.showToast('success', 'Export Complete', `Exported ${products.length} inventory records to CSV.`);
  }
};

// Make accessible globally for inline HTML event triggers
if (typeof window !== 'undefined') {
  window.Inventory = Inventory;
}

