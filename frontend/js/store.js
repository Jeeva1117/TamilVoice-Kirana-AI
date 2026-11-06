/**
 * TamilVoice Kirana AI - Shared Data Store
 * Centralized state management for inventory, sales transactions, and stock movements.
 * Synchronizes across Dashboard, Inventory, Sales, and Voice Assistant.
 * Persists demo state in localStorage with safe initialization and reset capabilities.
 */

export const Store = {
  STORAGE_KEYS: {
    INVENTORY: 'tv_kirana_inventory_v1',
    SALES: 'tv_kirana_sales_v1',
    MOVEMENTS: 'tv_kirana_movements_v1'
  },

  // Initial Seed Data (Realistic Tamil Nadu Kirana Store)
  defaultProducts: [
    {
      id: 1,
      sku: 'SKU-GRN-001',
      name_en: 'Ponni Boiled Rice',
      name_ta: 'பொன்னி புழுங்கல் அரிசி',
      category: 'Grains',
      stock: 45,
      min_stock: 15,
      unit: 'kg',
      purchase_price: 48,
      selling_price: 58,
      description: 'First quality Thanjavur Ponni boiled rice.'
    },
    {
      id: 2,
      sku: 'SKU-GRN-002',
      name_en: 'Wheat Flour (Atta)',
      name_ta: 'கோதுமை மாவு (ஆட்டா)',
      category: 'Grains',
      stock: 20,
      min_stock: 10,
      unit: 'kg',
      purchase_price: 42,
      selling_price: 52,
      description: '100% whole wheat stone-ground chakki fresh atta.'
    },
    {
      id: 3,
      sku: 'SKU-OIL-001',
      name_en: 'Sunflower Oil (Gold Winner)',
      name_ta: 'சூரியகாந்தி எண்ணெய்',
      category: 'Oils',
      stock: 12,
      min_stock: 15,
      unit: 'litre',
      purchase_price: 120,
      selling_price: 140,
      description: 'Refined sunflower cooking oil pouch.'
    },
    {
      id: 4,
      sku: 'SKU-GRO-001',
      name_en: 'White Crystal Sugar',
      name_ta: 'வெள்ளை சீனி',
      category: 'Grocery',
      stock: 30,
      min_stock: 15,
      unit: 'kg',
      purchase_price: 38,
      selling_price: 44,
      description: 'Pure refined sulphurless white sugar.'
    },
    {
      id: 5,
      sku: 'SKU-PUL-001',
      name_en: 'Premium Toor Dal',
      name_ta: 'முதல் தர துவரம் பருப்பு',
      category: 'Pulses',
      stock: 8,
      min_stock: 12,
      unit: 'kg',
      purchase_price: 135,
      selling_price: 155,
      description: 'Polished desi toor dal for sambar and dal.'
    },
    {
      id: 6,
      sku: 'SKU-DAI-001',
      name_en: 'Fresh Toned Milk',
      name_ta: 'பசும்பால்',
      category: 'Dairy',
      stock: 5,
      min_stock: 10,
      unit: 'litre',
      purchase_price: 24,
      selling_price: 30,
      description: 'Pasteurized homogenized toned pouch milk.'
    },
    {
      id: 7,
      sku: 'SKU-BEV-001',
      name_en: '3 Roses Tea Powder',
      name_ta: '3 ரோஸஸ் டீ தூள்',
      category: 'Beverages',
      stock: 15,
      min_stock: 8,
      unit: 'packet',
      purchase_price: 65,
      selling_price: 78,
      description: '250g strong blend CTC black tea packet.'
    },
    {
      id: 8,
      sku: 'SKU-GRO-002',
      name_en: 'Tata Iodized Salt',
      name_ta: 'டாடா அயோடின் உப்பு',
      category: 'Grocery',
      stock: 25,
      min_stock: 10,
      unit: 'kg',
      purchase_price: 20,
      selling_price: 26,
      description: 'Vacuum evaporated iodized crystal salt.'
    },
    {
      id: 9,
      sku: 'SKU-SPI-001',
      name_en: 'Aachi Chilli Powder 100g',
      name_ta: 'ஆச்சி மிளகாய் தூள்',
      category: 'Spices',
      stock: 6,
      min_stock: 15,
      unit: 'packet',
      purchase_price: 38,
      selling_price: 48,
      description: '100g hot red chilli powder packet.'
    },
    {
      id: 10,
      sku: 'SKU-PUL-002',
      name_en: 'Urad Dal (White Whole)',
      name_ta: 'உளுந்தம் பருப்பு (முழு)',
      category: 'Pulses',
      stock: 0,
      min_stock: 10,
      unit: 'kg',
      purchase_price: 125,
      selling_price: 145,
      description: 'Guntur premium urad dal for idli/dosa batter.'
    }
  ],

  defaultSales: [
    {
      id: 'KB-1089',
      date: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      product_id: 1,
      product_name: 'Ponni Boiled Rice',
      product_name_ta: 'பொன்னி புழுங்கல் அரிசி',
      quantity: 25,
      unit: 'kg',
      unit_price: 58,
      total_amount: 1450,
      payment_method: 'UPI',
      customer_name: 'Murugan Pandian',
      status: 'Completed',
      notes: 'Monthly grocery purchase'
    },
    {
      id: 'KB-1088',
      date: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
      product_id: 3,
      product_name: 'Sunflower Oil (Gold Winner)',
      product_name_ta: 'சூரியகாந்தி எண்ணெய்',
      quantity: 2,
      unit: 'litre',
      unit_price: 140,
      total_amount: 280,
      payment_method: 'Cash',
      customer_name: 'Lakshmi Ammal',
      status: 'Completed',
      notes: 'Counter sale'
    },
    {
      id: 'KB-1087',
      date: new Date(Date.now() - 75 * 60 * 1000).toISOString(),
      product_id: 9,
      product_name: 'Aachi Chilli Powder 100g',
      product_name_ta: 'ஆச்சி மிளகாய் தூள்',
      quantity: 2,
      unit: 'packet',
      unit_price: 48,
      total_amount: 96,
      payment_method: 'Cash',
      customer_name: 'Walk-in Customer',
      status: 'Completed',
      notes: ''
    },
    {
      id: 'KB-1086',
      date: new Date(Date.now() - 130 * 60 * 1000).toISOString(),
      product_id: 4,
      product_name: 'White Crystal Sugar',
      product_name_ta: 'வெள்ளை சீனி',
      quantity: 5,
      unit: 'kg',
      unit_price: 44,
      total_amount: 220,
      payment_method: 'UPI',
      customer_name: 'Senthil Kumar',
      status: 'Completed',
      notes: 'Festival sweets preparation'
    },
    {
      id: 'KB-1085',
      date: new Date(Date.now() - 210 * 60 * 1000).toISOString(),
      product_id: 2,
      product_name: 'Wheat Flour (Atta)',
      product_name_ta: 'கோதுமை மாவு (ஆட்டா)',
      quantity: 5,
      unit: 'kg',
      unit_price: 52,
      total_amount: 260,
      payment_method: 'Card',
      customer_name: 'Anitha Ramesh',
      status: 'Completed',
      notes: ''
    }
  ],

  defaultMovements: [
    { id: 1, product_id: 1, type: 'Initial Stock', quantity: 70, unit: 'kg', date: new Date(Date.now() - 86400000 * 2).toISOString(), reason: 'Distributor delivery' },
    { id: 2, product_id: 1, type: 'Sale', quantity: -25, unit: 'kg', date: new Date(Date.now() - 10 * 60 * 1000).toISOString(), reason: 'Invoice KB-1089' },
    { id: 3, product_id: 3, type: 'Initial Stock', quantity: 14, unit: 'litre', date: new Date(Date.now() - 86400000 * 2).toISOString(), reason: 'Stock intake' },
    { id: 4, product_id: 3, type: 'Sale', quantity: -2, unit: 'litre', date: new Date(Date.now() - 35 * 60 * 1000).toISOString(), reason: 'Invoice KB-1088' }
  ],

  init() {
    if (!localStorage.getItem(this.STORAGE_KEYS.INVENTORY)) {
      this.saveProducts(this.defaultProducts);
    }
    if (!localStorage.getItem(this.STORAGE_KEYS.SALES)) {
      this.saveSales(this.defaultSales);
    }
    if (!localStorage.getItem(this.STORAGE_KEYS.MOVEMENTS)) {
      this.saveMovements(this.defaultMovements);
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
    const products = this.getProducts();
    return products.find(p => Number(p.id) === Number(id)) || null;
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

