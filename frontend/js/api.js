/**
 * TamilVoice Kirana AI - Centralized API Service Layer
 * Connects to FastAPI backend on http://127.0.0.1:8000/api (or same-origin)
 * Provides 8-stage error tracing across:
 * 1. Microphone capture
 * 2. Frontend-to-backend connection
 * 3. Audio upload
 * 4. Gnani STT
 * 5. Gemini processing
 * 6. Database operation
 * 7. Gnani TTS
 * 8. Audio playback
 */

function getInitialBaseUrl() {
  if (typeof window === 'undefined') return '/api';

  // 1. Explicit user override in Settings takes highest priority
  const savedUrl = localStorage.getItem('tamilvoice_backend_url') || localStorage.getItem('API_BASE_URL');
  if (savedUrl && savedUrl.trim()) {
    let clean = savedUrl.trim().replace(/\/+$/, '');
    if (!clean.endsWith('/api') && !clean.includes('/api/')) clean = `${clean}/api`;
    return clean;
  }

  // 2. Local development on localhost/127.0.0.1 defaults to local FastAPI on port 8000
  const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  if (isLocalHost) {
    if (window.location.port === '8000') {
      return `${window.location.origin}/api`;
    }
    return `${window.location.protocol}//127.0.0.1:8000/api`;
  }

  // 3. Injected build-time or runtime environment URL (e.g. Vercel build via build.js / env.js)
  if (window.__API_BASE_URL__ && window.__API_BASE_URL__.trim()) {
    let clean = window.__API_BASE_URL__.trim().replace(/\/+$/, '');
    if (!clean.endsWith('/api') && !clean.includes('/api/')) clean = `${clean}/api`;
    return clean;
  }

  // 4. HTML meta tag override: <meta name="backend-api-url" content="...">
  const metaUrl = document.querySelector('meta[name="backend-api-url"]')?.content;
  if (metaUrl && metaUrl.trim()) {
    let clean = metaUrl.trim().replace(/\/+$/, '');
    if (!clean.endsWith('/api') && !clean.includes('/api/')) clean = `${clean}/api`;
    return clean;
  }

  // 5. Fallback same-origin /api
  return '/api';
}

function getBackendHint() {
  const isLocal = typeof window !== 'undefined' && 
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  return isLocal
    ? 'Ensure FastAPI backend is running locally on port 8000 (run start-dev.bat).'
    : `Ensure deployed backend at ${API_CONFIG.BASE_URL} is live, or configure your Render backend URL in UI Settings.`;
}

export const API_CONFIG = {
  BASE_URL: getInitialBaseUrl(),
  TIMEOUT_MS: 30000,
  IS_BACKEND_AVAILABLE: false,
};

export class ApiService {
  /**
   * Configure and save custom deployed backend URL (for Vercel production deployment)
   */
  static setBackendUrl(url) {
    if (!url || typeof url !== 'string') return API_CONFIG.BASE_URL;
    let clean = url.trim().replace(/\/+$/, '');
    if (!clean.endsWith('/api') && !clean.includes('/api/')) {
      clean = `${clean}/api`;
    }
    localStorage.setItem('tamilvoice_backend_url', clean);
    API_CONFIG.BASE_URL = clean;
    return clean;
  }

  /**
   * Test connection to FastAPI backend with auto-discovery fallback
   */
  static async checkHealth() {
    const isLocalHost = typeof window !== 'undefined' && 
      (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

    const saved = typeof window !== 'undefined' ? localStorage.getItem('tamilvoice_backend_url') : null;
    
    // Remote environments (Vercel) should NEVER probe 127.0.0.1 or localhost (causes mixed-content/connection refused)
    const localCandidates = isLocalHost
      ? [`${window.location.protocol}//127.0.0.1:8000/api`, `${window.location.protocol}//localhost:8000/api`]
      : [];

    const candidates = [
      API_CONFIG.BASE_URL,
      saved,
      typeof window !== 'undefined' ? window.__API_BASE_URL__ : null,
      ...localCandidates,
      '/api'
    ].filter(Boolean);
    const uniqueCandidates = [...new Set(candidates.map(u => (typeof u === 'string' ? u.trim().replace(/\/+$/, '') : '')))].filter(Boolean);

    for (const cand of uniqueCandidates) {
      try {
        const response = await fetch(`${cand}/health`, {
          method: 'GET',
          headers: { Accept: 'application/json' },
          signal: AbortSignal.timeout(4000),
        });
        if (response.ok) {
          const data = await response.json();
          API_CONFIG.BASE_URL = cand;
          API_CONFIG.IS_BACKEND_AVAILABLE = data.status === 'healthy';
          return data;
        }
      } catch {
        // try next candidate
      }
    }

    API_CONFIG.IS_BACKEND_AVAILABLE = false;
    return { status: 'offline', database: 'disconnected' };
  }

  /**
   * Generic request wrapper with stage-aware error handling
   * @param {string} endpoint
   * @param {RequestInit} options
   */
  static async request(endpoint, options = {}) {
    const url = `${API_CONFIG.BASE_URL}${endpoint}`;
    const isFormData = options.body instanceof FormData;
    const headers = {
      Accept: 'application/json',
      ...(!isFormData ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    };
    if (isFormData && headers['Content-Type']) {
      delete headers['Content-Type'];
    }

    const controller = new AbortController();
    const timeoutMs = options.timeoutMs || API_CONFIG.TIMEOUT_MS;
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const stagePrefix = errorData.stage ? `[Stage: ${errorData.stage}] ` : '';
        throw new Error(`${stagePrefix}${errorData.detail || `HTTP Error ${response.status}: ${response.statusText}`}`);
      }

      API_CONFIG.IS_BACKEND_AVAILABLE = true;
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error(`[Stage 2: Backend Connection] Request to ${endpoint} timed out after ${timeoutMs / 1000}s. Check backend server.`);
      }
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error(`[Stage 2: Backend Connection] Could not connect to FastAPI at ${API_CONFIG.BASE_URL}. ${getBackendHint()}`);
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

  static async updateSaleStatus(saleId, statusData) {
    return this.request(`/sales/${saleId}/status`, {
      method: 'PATCH',
      body: JSON.stringify(statusData),
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

  static async recordCustomerPayment(customerId, paymentData) {
    return this.request(`/customers/${customerId}/payment`, {
      method: 'POST',
      body: JSON.stringify(paymentData),
    });
  }

  static async getCustomerSales(customerId, limit = 50) {
    return this.request(`/customers/${customerId}/sales?limit=${limit}`, {
      method: 'GET',
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

  static getExportCsvUrl(reportType, startDate = null, endDate = null) {
    const params = new URLSearchParams({ report_type: reportType });
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    return `${API_CONFIG.BASE_URL}/reports/export/csv?${params.toString()}`;
  }

  /* =========================================================================
     Settings Endpoints
     ========================================================================= */
  static async getStoreSettings() {
    return this.request('/settings', { method: 'GET' });
  }

  static async updateStoreSettings(settingsData) {
    return this.request('/settings', {
      method: 'PUT',
      body: JSON.stringify(settingsData),
    });
  }

  /* =========================================================================
     System Validation & Testing Endpoints
     ========================================================================= */
  static async getTestStatus() {
    return this.request('/test/status', { method: 'GET' });
  }

  static async runSystemTest(testPayload) {
    return this.request('/test/run', {
      method: 'POST',
      body: JSON.stringify(testPayload),
    });
  }

  /* =========================================================================
     Phase 5: Gemini AI Intelligence Endpoints
     ========================================================================= */
  static async getAIStatus() {
    return this.request('/ai/status', { method: 'GET' });
  }

  static normalizeLang(lang) {
    if (!lang) return 'ta-IN';
    const l = String(lang).toLowerCase().trim();
    if (l === 'en' || l === 'english' || l === 'en-in') return 'en-IN';
    return 'ta-IN';
  }

  static async interpretCommand(text, sessionId = null, context = null) {
    return this.request('/ai/interpret', {
      method: 'POST',
      body: JSON.stringify({
        text,
        allow_mock: false,
        session_id: sessionId,
        context: context,
      }),
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

  /* =========================================================================
     Phase 6: Gnani Prisma STT & Gnani Timbre TTS Endpoints
     ========================================================================= */
  static async getVoiceStatus() {
    return this.request('/voice/status', { method: 'GET' });
  }

  static async transcribeAudio(audioBlob, language = 'ta-IN') {
    const normLang = this.normalizeLang(language);
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.wav');
    formData.append('language', normLang);

    const url = `${API_CONFIG.BASE_URL}/voice/transcribe`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 35000);

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `[Stage 4: Gnani STT] Transcription failed: ${response.statusText}`);
      }
      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        throw new Error('[Stage 4: Gnani STT] STT transcription timed out after 35s.');
      }
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error(`[Stage 2: Backend Connection] Could not reach ${API_CONFIG.BASE_URL}/voice/transcribe. ${getBackendHint()}`);
      }
      throw err;
    }
  }

  static async processVoiceCommand(audioBlob = null, transcriptText = null, language = 'ta-IN', sessionId = null, context = null) {
    const normLang = this.normalizeLang(language);
    const formData = new FormData();
    if (audioBlob) {
      formData.append('audio', audioBlob, 'recording.wav');
    }
    if (transcriptText) {
      formData.append('transcript', transcriptText);
    }
    formData.append('language', normLang);
    if (sessionId) {
      formData.append('session_id', sessionId);
    }
    if (context) {
      formData.append('context_json', JSON.stringify(context));
    }

    const url = `${API_CONFIG.BASE_URL}/voice/command`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        const stagePrefix = err.stage ? `[Stage: ${err.stage}] ` : '';
        throw new Error(`${stagePrefix}${err.detail || `Voice command error: ${response.statusText}`}`);
      }
      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        throw new Error('[Stage 3: Audio Upload / Pipeline Timeout] Voice command request timed out. Please check network and server.');
      }
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error(`[Stage 2: Backend Connection] Network error connecting to ${API_CONFIG.BASE_URL}/voice/command. ${getBackendHint()}`);
      }
      throw err;
    }
  }

  static async synthesizeSpeech(text, language = 'ta-IN', speed = 1.0) {
    const normLang = this.normalizeLang(language);
    const url = `${API_CONFIG.BASE_URL}/voice/speak`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 25000);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'audio/wav, audio/*, */*'
        },
        body: JSON.stringify({ text, language: normLang, speed }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `[Stage 7: Gnani TTS] TTS synthesis failed: ${response.statusText}`);
      }
      return await response.blob();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        throw new Error('[Stage 7: Gnani TTS] TTS synthesis timed out after 25s.');
      }
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error(`[Stage 2: Backend Connection] Could not reach TTS service at ${API_CONFIG.BASE_URL}/voice/speak. ${getBackendHint()}`);
      }
      throw err;
    }
  }
}
