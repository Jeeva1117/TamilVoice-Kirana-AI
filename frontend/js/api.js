/**
 * TamilVoice Kirana AI - Centralized API Service Layer
 * Connects to FastAPI backend on http://localhost:8000/api
 * Gracefully falls back to client-side store when backend is unreachable.
 */

export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000/api',
  TIMEOUT_MS: 6000,
  IS_BACKEND_AVAILABLE: false,
};

export class ApiService {
  /**
   * Test connection to FastAPI backend
   */
  static async checkHealth() {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/health`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(3000),
      });
      if (response.ok) {
        const data = await response.json();
        API_CONFIG.IS_BACKEND_AVAILABLE = data.status === 'healthy';
        return data;
      }
    } catch {
      API_CONFIG.IS_BACKEND_AVAILABLE = false;
    }
    return { status: 'offline', database: 'disconnected' };
  }

  /**
   * Generic request wrapper with timeout and error handling
   * @param {string} endpoint
   * @param {RequestInit} options
   */
  static async request(endpoint, options = {}) {
    const url = `${API_CONFIG.BASE_URL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options.headers,
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP Error ${response.status}: ${response.statusText}`);
      }

      API_CONFIG.IS_BACKEND_AVAILABLE = true;
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('API Request timed out.');
      }
      throw error;
    }
  }

  /* =========================================================================
     Dashboard Endpoints
     ========================================================================= */
  static async getDashboard() {
    return this.request('/dashboard', { method: 'GET' });
  }

  /* =========================================================================
     Inventory Endpoints
     ========================================================================= */
  static async getInventory(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const endpoint = queryString ? `/inventory?${queryString}` : '/inventory';
    return this.request(endpoint, { method: 'GET' });
  }

  static async getCategories() {
    return this.request('/inventory/categories', { method: 'GET' });
  }

  static async getProduct(id) {
    return this.request(`/inventory/${id}`, { method: 'GET' });
  }

  static async createProduct(productData) {
    return this.request('/inventory', {
      method: 'POST',
      body: JSON.stringify(productData),
    });
  }

  static async updateProduct(id, productData) {
    return this.request(`/inventory/${id}`, {
      method: 'PUT',
      body: JSON.stringify(productData),
    });
  }

  static async deleteProduct(id) {
    return this.request(`/inventory/${id}`, {
      method: 'DELETE',
    });
  }

  /* =========================================================================
     Stock Adjustment Endpoints
     ========================================================================= */
  static async adjustStock(productId, adjustmentData) {
    return this.request(`/inventory/${productId}/adjust`, {
      method: 'POST',
      body: JSON.stringify(adjustmentData),
    });
  }

  static async getStockMovements(productId, limit = 50) {
    return this.request(`/inventory/${productId}/movements?limit=${limit}`, {
      method: 'GET',
    });
  }

  static async getAllStockMovements(limit = 50) {
    return this.request(`/inventory/movements/all?limit=${limit}`, {
      method: 'GET',
    });
  }

  /* =========================================================================
     Sales & Orders Endpoints
     ========================================================================= */
  static async getSales(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const endpoint = queryString ? `/sales?${queryString}` : '/sales';
    return this.request(endpoint, { method: 'GET' });
  }

  static async getSale(id) {
    return this.request(`/sales/${id}`, { method: 'GET' });
  }

  static async getSaleByTxId(txnId) {
    return this.request(`/sales/transaction/${encodeURIComponent(txnId)}`, { method: 'GET' });
  }

  static async createSale(saleData) {
    return this.request('/sales', {
      method: 'POST',
      body: JSON.stringify(saleData),
    });
  }

  /* =========================================================================
     Customers Endpoints
     ========================================================================= */
  static async getCustomers(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const endpoint = queryString ? `/customers?${queryString}` : '/customers';
    return this.request(endpoint, { method: 'GET' });
  }

  static async createCustomer(customerData) {
    return this.request('/customers', {
      method: 'POST',
      body: JSON.stringify(customerData),
    });
  }

  /* =========================================================================
     Reports & Analytics Endpoints
     ========================================================================= */
  static async getDailyReport(startDate, endDate) {
    const params = new URLSearchParams();
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    const qs = params.toString();
    return this.request(qs ? `/reports/daily?${qs}` : '/reports/daily', { method: 'GET' });
  }

  static async getProductsReport() {
    return this.request('/reports/products', { method: 'GET' });
  }

  static async getInventoryValuationReport() {
    return this.request('/reports/inventory', { method: 'GET' });
  }

  /* =========================================================================
     Phase 5: Gemini AI Intelligence Endpoints
     ========================================================================= */
  static async getAIStatus() {
    return this.request('/ai/status', { method: 'GET' });
  }

  static async interpretCommand(text) {
    return this.request('/ai/interpret', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  }

  static async confirmAction(actionId) {
    return this.request('/ai/confirm', {
      method: 'POST',
      body: JSON.stringify({ action_id: actionId }),
    });
  }

  static async cancelAction(actionId) {
    return this.request('/ai/cancel', {
      method: 'POST',
      body: JSON.stringify({ action_id: actionId }),
    });
  }
}
