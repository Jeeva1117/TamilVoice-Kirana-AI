/**
 * TamilVoice Kirana AI - Settings Controller
 * Handles persistent Kirana store metadata, contact details, voice settings, and backend sync.
 */
import { ApiService, API_CONFIG } from './api.js';
import { Utils } from './utils.js';

export const Settings = {
  initialized: false,
  activeSettings: null,

  init() {
    if (this.initialized) return;
    this.cacheDOM();
    this.bindEvents();
    this.loadSettings();
    this.initialized = true;

    window.addEventListener('view-changed', (e) => {
      if (e.detail && e.detail.view === 'settings') {
        this.loadSettings();
      }
    });
  },

  cacheDOM() {
    this.container = document.getElementById('view-settings');
    this.form = document.getElementById('settings-store-form');
    this.backendUrlInput = document.getElementById('set-backend-api-url');
    this.btnSaveBackendUrl = document.getElementById('btn-save-backend-url');
  },

  bindEvents() {
    if (this.form) {
      this.form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.saveSettings();
      });
    }

    const refreshBtn = document.getElementById('btn-refresh-settings');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadSettings());
    }

    if (this.btnSaveBackendUrl) {
      this.btnSaveBackendUrl.addEventListener('click', async () => {
        const rawUrl = this.backendUrlInput?.value;
        if (!rawUrl || !rawUrl.trim()) {
          localStorage.removeItem('tamilvoice_backend_url');
          Utils.showToast('info', 'Backend Reset', 'Reverted to default auto-detected API URL.');
          this.loadSettings();
          return;
        }
        const cleaned = ApiService.setBackendUrl(rawUrl);
        Utils.showToast('info', 'Connecting...', `Testing backend at ${cleaned}`);
        try {
          const health = await ApiService.checkHealth();
          if (health && health.status === 'healthy') {
            Utils.showToast('success', 'Backend Connected', `Successfully reached FastAPI backend!`);
            this.loadSettings();
          } else {
            Utils.showToast('warning', 'Connection Warning', 'Backend URL saved, but /health did not return healthy.');
          }
        } catch (err) {
          Utils.showToast('error', 'Connection Failed', 'Could not reach specified backend URL.');
        }
      });
    }
  },

  getStoreDetails() {
    if (this.activeSettings) return this.activeSettings;
    try {
      const saved = localStorage.getItem('tv_store_settings');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return {
      shop_name: 'Arjun Grocery Store',
      shop_name_ta: 'அர்ஜுன் மளிகைக் கடை',
      owner_name: 'Jeevan',
      phone: '+91 98401 23456',
      whatsapp_number: '+91 98401 23456',
      address: '42, North Mada Street, Mylapore, Chennai, Tamil Nadu - 600004',
      email: 'contact@arjungrocery.in',
      gstin: '33ABCDE1234F1Z5',
      currency: 'INR',
      currency_symbol: '₹',
      receipt_footer: 'நன்றி! மீண்டும் வருக! / Thank you, visit again!'
    };
  },

  updateDOMShopIdentity(data) {
    if (!data) return;
    this.activeSettings = data;
    try {
      localStorage.setItem('tv_store_settings', JSON.stringify(data));
    } catch (e) {}

    // Topbar & Profile
    const topShop = document.getElementById('top-shop-name');
    if (topShop) topShop.textContent = data.shop_name;
    const topOwner = document.getElementById('top-proprietor-name');
    if (topOwner) topOwner.textContent = data.owner_name;
    const topAvatar = document.getElementById('top-profile-avatar');
    if (topAvatar && data.owner_name) {
      const initials = data.owner_name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
      topAvatar.textContent = initials || 'AG';
    }

    // Sidebar & Branding
    document.querySelectorAll('.brand-title, .sidebar-shop-name').forEach(el => {
      el.textContent = data.shop_name;
    });

    window.dispatchEvent(new CustomEvent('store-settings-updated', { detail: data }));
  },

  async loadSettings() {
    if (this.backendUrlInput) {
      this.backendUrlInput.value = localStorage.getItem('tamilvoice_backend_url') || (typeof API_CONFIG !== 'undefined' ? API_CONFIG.BASE_URL : '');
    }
    try {
      const data = await ApiService.getStoreSettings();
      this.updateDOMShopIdentity(data);

      // Populate form fields
      this.setVal('set-shop-name', data.shop_name);
      this.setVal('set-shop-name-ta', data.shop_name_ta);
      this.setVal('set-owner-name', data.owner_name);
      this.setVal('set-phone', data.phone);
      this.setVal('set-whatsapp', data.whatsapp_number);
      this.setVal('set-email', data.email);
      this.setVal('set-address', data.address);
      this.setVal('set-gstin', data.gstin);
      this.setVal('set-currency', data.currency || 'INR');
      this.setVal('set-pref-lang', data.preferred_language || 'ta');
      this.setVal('set-voice-lang', data.voice_preferred_language || 'ta');
      this.setVal('set-speech-speed', data.speech_speed || 1.0);
      this.setVal('set-threshold', data.low_stock_threshold_default || 5.0);

      // Status badges
      this.setStatusBadge('status-gemini', data.gemini_ready);
      this.setStatusBadge('status-gnani-stt', data.gnani_stt_ready);
      this.setStatusBadge('status-gnani-tts', data.gnani_tts_ready);
    } catch (err) {
      console.warn('Could not load settings from backend, using cached settings:', err);
      const cached = this.getStoreDetails();
      this.updateDOMShopIdentity(cached);
    }
  },

  setVal(id, val) {
    const el = document.getElementById(id);
    if (el && val !== undefined && val !== null) el.value = val;
  },

  setStatusBadge(id, isReady) {
    const el = document.getElementById(id);
    if (!el) return;
    if (isReady) {
      el.className = 'badge badge-success';
      el.textContent = 'Active / Ready';
    } else {
      el.className = 'badge badge-warning';
      el.textContent = 'Active / Local Engine';
    }
  },

  async saveSettings() {
    const shopName = document.getElementById('set-shop-name')?.value?.trim();
    const ownerName = document.getElementById('set-owner-name')?.value?.trim();
    const phone = document.getElementById('set-phone')?.value?.trim();
    const whatsapp = document.getElementById('set-whatsapp')?.value?.trim();
    const email = document.getElementById('set-email')?.value?.trim();

    if (!shopName) {
      Utils.showToast('error', 'Validation Error', 'Shop Name is required.');
      return;
    }
    if (!ownerName) {
      Utils.showToast('error', 'Validation Error', 'Proprietor Name is required.');
      return;
    }
    if (!phone || phone.replace(/\D/g, '').length < 10) {
      Utils.showToast('error', 'Validation Error', 'Please enter a valid 10-digit phone number.');
      return;
    }
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      Utils.showToast('error', 'Validation Error', 'Please enter a valid email address.');
      return;
    }

    const payload = {
      shop_name: shopName,
      shop_name_ta: document.getElementById('set-shop-name-ta')?.value?.trim() || null,
      owner_name: ownerName,
      phone: phone,
      whatsapp_number: whatsapp || null,
      email: email || null,
      address: document.getElementById('set-address')?.value?.trim() || null,
      gstin: document.getElementById('set-gstin')?.value?.trim() || null,
      currency: document.getElementById('set-currency')?.value || 'INR',
      preferred_language: document.getElementById('set-pref-lang')?.value || 'ta',
      voice_preferred_language: document.getElementById('set-voice-lang')?.value || 'ta',
      speech_speed: parseFloat(document.getElementById('set-speech-speed')?.value || '1.0'),
      low_stock_threshold_default: parseFloat(document.getElementById('set-threshold')?.value || '5.0'),
    };

    try {
      const res = await ApiService.updateStoreSettings(payload);
      this.updateDOMShopIdentity(res);
      Utils.showToast('success', 'Settings Saved', 'Shop details and preferences updated successfully.');
    } catch (err) {
      Utils.showToast('error', 'Save Failed', err.message || 'Could not update settings. Please try again.');
    }
  }
};
