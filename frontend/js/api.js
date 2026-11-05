/**
 * TamilVoice Kirana AI - Centralized API Service Layer
 * Prepared for future FastAPI backend integration.
 * Gracefully falls back to client-side demo data when backend is not running.
 */

export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000/api',
  TIMEOUT_MS: 5000,
  IS_DEMO_MODE: true, // Auto-detected or forced when backend is unreachable
};

export class ApiService {
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

      API_CONFIG.IS_DEMO_MODE = false;
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      // Mark as demo mode if backend is unreachable
      API_CONFIG.IS_DEMO_MODE = true;
      console.warn(`[API] Notice: Backend is not reachable at ${url} (${error.message}). Running in Demo Mode.`);
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
     Sales & Orders Endpoints
     ========================================================================= */
  static async getSales(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const endpoint = queryString ? `/sales?${queryString}` : '/sales';
    return this.request(endpoint, { method: 'GET' });
  }

  static async createSale(saleData) {
    return this.request('/sales', {
      method: 'POST',
      body: JSON.stringify(saleData),
    });
  }

  /* =========================================================================
     Voice Processing Endpoint (Gnani & Gemini)
     ========================================================================= */
  static async processVoice(audioBlob, langCode = 'ta-IN') {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    formData.append('language', langCode);

    const url = `${API_CONFIG.BASE_URL}/voice/process`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Voice API error: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  /* =========================================================================
     Reports & Analytics Endpoints
     ========================================================================= */
  static async getDailyReport(date) {
    return this.request(`/reports/daily?date=${encodeURIComponent(date)}`, { method: 'GET' });
  }

  static async getWeeklyReport(startDate) {
    return this.request(`/reports/weekly?start_date=${encodeURIComponent(startDate)}`, { method: 'GET' });
  }

  static async getMonthlyReport(year, month) {
    return this.request(`/reports/monthly?year=${year}&month=${month}`, { method: 'GET' });
  }
}
