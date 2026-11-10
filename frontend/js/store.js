/**
 * TamilVoice Kirana AI - Shared Data Store
 * Centralized state management for inventory, sales transactions, and stock movements.
 * Synchronizes across Dashboard, Inventory, Sales, and Voice Assistant.
 * Persists state in localStorage with live SQLite backend synchronization.
 */

import { API_CONFIG } from './api.js';

export const Store = {
  STORAGE_KEYS: {
    INVENTORY: 'tv_kirana_inventory_v1',
    SALES: 'tv_kirana_sales_v1',
    MOVEMENTS: 'tv_kirana_movements_v1'
  },

  // Clean Initial State: Real shopkeeper catalog starts empty
  defaultProducts: [],
  defaultSales: [],
  defaultMovements: [],

  init() {
    // One-time purge of legacy demo seed items from local storage
    if (!localStorage.getItem('tv_purged_shopkeeper_data_v2')) {
      localStorage.removeItem(this.STORAGE_KEYS.INVENTORY);
      localStorage.removeItem(this.STORAGE_KEYS.SALES);
      localStorage.removeItem(this.STORAGE_KEYS.MOVEMENTS);
      localStorage.removeItem('tv_voice_history');
      localStorage.setItem('tv_purged_shopkeeper_data_v2', 'true');
    }

    if (!localStorage.getItem(this.STORAGE_KEYS.INVENTORY)) {
      this.saveProducts([]);
    }
    if (!localStorage.getItem(this.STORAGE_KEYS.SALES)) {
      this.saveSales([]);
    }
    if (!localStorage.getItem(this.STORAGE_KEYS.MOVEMENTS)) {
      this.saveMovements([]);
    }
    this.syncFromBackend();
    this.syncSalesFromBackend();
  },

  async syncFromBackend() {
    try {
      const res = await fetch(`${API_CONFIG.BASE_URL}/inventory?limit=100`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.items && Array.isArray(data.items)) {
          const mapped = data.items.map(p => ({
            id: p.id,
            sku: p.sku,
            name_en: p.name,
            name_ta: p.name_ta || p.name,
            category: p.category,
            stock: p.quantity,
            min_stock: p.minimum_stock_level,
            unit: p.unit,
            purchase_price: p.purchase_price,
            selling_price: p.selling_price,
            description: p.description || '',
            is_low_stock: p.is_low_stock,
            is_out_of_stock: p.is_out_of_stock,
            status: p.stock_status === 'out_of_stock' ? 'Out of Stock' : (p.stock_status === 'low_stock' ? 'Low Stock' : 'In Stock')
          }));
          this.saveProducts(mapped);
          this.notify('inventory');
        }
      }
    } catch (e) {
      console.warn('[Store] syncFromBackend notice:', e.message);
    }
  },

  async syncSalesFromBackend() {
    try {
      const res = await fetch(`${API_CONFIG.BASE_URL}/sales?limit=100`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.items && Array.isArray(data.items)) {
          const mapped = data.items.map(s => {
            const hasItems = s.items && s.items.length > 0;
            const itemLines = hasItems ? s.items.map(it => `${it.product_name_snapshot} (${it.quantity} ${it.unit || ''})`).join(', ') : (s.notes || 'Counter Sale');
            const totalQty = hasItems ? s.items.reduce((acc, it) => acc + (it.quantity || 0), 0) : 1;
            const prodName = hasItems ? (s.items.length > 1 ? `${s.items[0].product_name_snapshot} + ${s.items.length - 1} more` : s.items[0].product_name_snapshot) : 'Sale';

            return {
              id: s.transaction_id || `TX-${s.id}`,
              date: s.created_at,
              items: s.items || [],
              items_summary: itemLines,
              total_items: hasItems ? s.items.length : 1,
              product_id: hasItems ? s.items[0].product_id : null,
              product_name: prodName,
              product_name_ta: '',
              quantity: totalQty,
              unit: hasItems && s.items.length === 1 ? s.items[0].unit : 'items',
              unit_price: hasItems && s.items.length === 1 ? s.items[0].unit_price : s.total_amount,
              total_amount: s.total_amount,
              payment_method: s.payment_method,
              customer_name: s.customer_name || 'Walk-in Counter',
              status: s.status,
              notes: s.notes || ''
            };
          });
          this.saveSales(mapped);
          this.notify('sales');
        }
      }
    } catch (e) {
      console.warn('[Store] syncSalesFromBackend notice:', e.message);
    }
  },

  /* =========================================================================
     INVENTORY METHODS
     ========================================================================= */
  getProducts() {
    try {
      const data = localStorage.getItem(this.STORAGE_KEYS.INVENTORY);
      return data ? JSON.parse(data) : [...this.defaultProducts];
    } catch (e) {
      console.error('[Store] Failed to read inventory from localStorage', e);
      return [...this.defaultProducts];
    }
  },

  getProductById(id) {
    if (id === null || id === undefined) return null;
    const products = this.getProducts();
    const idStr = String(id).trim();
    const idNum = Number(id);
    return products.find(p => 
      (!isNaN(idNum) && Number(p.id) === idNum) ||
      String(p.id) === idStr ||
      (p.sku && p.sku.toLowerCase() === idStr.toLowerCase()) ||
      (p.name_en && p.name_en.toLowerCase() === idStr.toLowerCase())
    ) || null;
  },

  saveProducts(products) {
    localStorage.setItem(this.STORAGE_KEYS.INVENTORY, JSON.stringify(products));
    this.notify('inventory');
  },

  addProduct(newProduct) {
    const products = this.getProducts();
    const nextId = products.length ? Math.max(...products.map(p => p.id || 0)) + 1 : 1;
    const product = {
      ...newProduct,
      id: nextId,
      stock: Number(newProduct.stock) || 0,
      min_stock: Number(newProduct.min_stock) || 0,
      purchase_price: Number(newProduct.purchase_price) || 0,
      selling_price: Number(newProduct.selling_price) || 0
    };
    products.unshift(product);
    this.saveProducts(products);

    // Log movement
    this.addMovement({
      product_id: product.id,
      type: 'New Product Added',
      quantity: product.stock,
      unit: product.unit,
      date: new Date().toISOString(),
      reason: 'Initial stock intake'
    });

    return product;
  },

  updateProduct(id, updatedFields) {
    const products = this.getProducts();
    const index = products.findIndex(p => Number(p.id) === Number(id));
    if (index === -1) return null;

    products[index] = {
      ...products[index],
      ...updatedFields,
      id: Number(id),
      stock: Number(updatedFields.stock !== undefined ? updatedFields.stock : products[index].stock),
      min_stock: Number(updatedFields.min_stock !== undefined ? updatedFields.min_stock : products[index].min_stock),
      purchase_price: Number(updatedFields.purchase_price !== undefined ? updatedFields.purchase_price : products[index].purchase_price),
      selling_price: Number(updatedFields.selling_price !== undefined ? updatedFields.selling_price : products[index].selling_price)
    };

    this.saveProducts(products);
    return products[index];
  },

  deleteProduct(id) {
    let products = this.getProducts();
    const target = products.find(p => Number(p.id) === Number(id));
    if (!target) return false;

    products = products.filter(p => Number(p.id) !== Number(id));
    this.saveProducts(products);
    return true;
  },

  adjustStock(id, type, qty, reason) {
    const product = this.getProductById(id);
    if (!product) return null;

    const previousStock = Number(product.stock);
    const adjustmentQty = Number(qty);
    let newStock = previousStock;

    if (type === 'Add Stock') {
      newStock = previousStock + adjustmentQty;
    } else if (type === 'Remove Stock') {
      newStock = Math.max(0, previousStock - adjustmentQty);
    } else if (type === 'Set Current Stock') {
      newStock = Math.max(0, adjustmentQty);
    }

    const updated = this.updateProduct(id, { stock: newStock });

    // Log movement
    const delta = newStock - previousStock;
    this.addMovement({
      product_id: product.id,
      type: `Stock Adjustment (${type})`,
      quantity: delta,
      unit: product.unit,
      date: new Date().toISOString(),
      reason: reason || 'Manual correction'
    });

    return { product: updated, previousStock, newStock };
  },

  /**
   * Automatically calculate dynamic stock status
   * Out of Stock: stock = 0
   * Low Stock: 0 < stock <= min_stock
   * In Stock: stock > min_stock
   */
  calculateStatus(product) {
    const stock = Number(product.stock) || 0;
    const min = Number(product.min_stock) || 0;
    if (stock <= 0) return 'Out of Stock';
    if (stock <= min) return 'Low Stock';
    return 'In Stock';
  },

  /* =========================================================================
     SALES METHODS
     ========================================================================= */
  getSales() {
    try {
      const data = localStorage.getItem(this.STORAGE_KEYS.SALES);
      return data ? JSON.parse(data) : [...this.defaultSales];
    } catch (e) {
      console.error('[Store] Failed to read sales from localStorage', e);
      return [...this.defaultSales];
    }
  },

  getSaleById(id) {
    const sales = this.getSales();
    return sales.find(s => s.id === id) || null;
  },

  saveSales(sales) {
    localStorage.setItem(this.STORAGE_KEYS.SALES, JSON.stringify(sales));
    this.notify('sales');
  },

  recordSale(saleData) {
    const product = this.getProductById(saleData.product_id);
    if (!product) {
      throw new Error('Selected product does not exist.');
    }

    const saleQty = Number(saleData.quantity);
    if (saleQty <= 0) {
      throw new Error('Quantity must be greater than zero.');
    }

    if (saleQty > Number(product.stock)) {
      throw new Error(`Insufficient stock. Only ${product.stock} ${product.unit} available.`);
    }

    // 1. Generate Next Transaction ID
    const sales = this.getSales();
    const nextNum = 1090 + sales.length;
    const invoiceId = `KB-${nextNum}`;

    const newSale = {
      id: invoiceId,
      date: new Date().toISOString(),
      product_id: product.id,
      product_name: product.name_en,
      product_name_ta: product.name_ta,
      quantity: saleQty,
      unit: product.unit,
      unit_price: Number(saleData.unit_price) || product.selling_price,
      total_amount: saleQty * (Number(saleData.unit_price) || product.selling_price),
      payment_method: saleData.payment_method || 'Cash',
      customer_name: saleData.customer_name || 'Counter Customer',
      status: 'Completed',
      notes: saleData.notes || ''
    };

    // 2. Decrement Product Stock
    const newStock = Math.max(0, Number(product.stock) - saleQty);
    this.updateProduct(product.id, { stock: newStock });

    // 3. Log Stock Movement
    this.addMovement({
      product_id: product.id,
      type: 'Sale',
      quantity: -saleQty,
      unit: product.unit,
      date: new Date().toISOString(),
      reason: `Invoice ${invoiceId}`
    });

    // 4. Save to Sales Record
    sales.unshift(newSale);
    this.saveSales(sales);

    return newSale;
  },

  /* =========================================================================
     STOCK MOVEMENTS
     ========================================================================= */
  getMovements(productId = null) {
    try {
      const data = localStorage.getItem(this.STORAGE_KEYS.MOVEMENTS);
      const all = data ? JSON.parse(data) : [...this.defaultMovements];
      if (productId) {
        return all.filter(m => Number(m.product_id) === Number(productId));
      }
      return all;
    } catch (e) {
      return [...this.defaultMovements];
    }
  },

  saveMovements(movements) {
    localStorage.setItem(this.STORAGE_KEYS.MOVEMENTS, JSON.stringify(movements));
  },

  addMovement(movement) {
    const all = this.getMovements();
    const nextId = all.length ? Math.max(...all.map(m => m.id || 0)) + 1 : 1;
    all.unshift({ ...movement, id: nextId });
    this.saveMovements(all);
  },

  /* =========================================================================
     RESET DEMO DATA
     ========================================================================= */
  resetDemoData() {
    this.saveProducts(this.defaultProducts);
    this.saveSales(this.defaultSales);
    this.saveMovements(this.defaultMovements);
    this.notify('all');
  },

  /* =========================================================================
     NOTIFICATIONS / REACTIVE EVENTS
     ========================================================================= */
  notify(type) {
    window.dispatchEvent(new CustomEvent('store-updated', { detail: { type } }));
  }
};

