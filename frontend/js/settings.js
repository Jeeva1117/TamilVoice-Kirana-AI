/**
 * TamilVoice Kirana AI - Settings Controller
 * Handles Kirana store metadata, voice configuration, and backend API status diagnostics.
 */
import { ApiService } from './api.js';
import { Utils } from './utils.js';

export const Settings = {
  initialized: false,

  init() {
    if (this.initialized) return;
    this.cacheDOM();
    this.bindEvents();
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
  },

  async loadSettings() {
    try {
      const data = await ApiService.getStoreSettings();

      // Populate form fields
      this.setVal('set-shop-name', data.shop_name);
      this.setVal('set-shop-name-ta', data.shop_name_ta);
      this.setVal('set-owner-name', data.owner_name);
      this.setVal('set-phone', data.phone);
      this.setVal('set-address', data.address);
      this.setVal('set-gstin', data.gstin);
      this.setVal('set-voice-lang', data.voice_preferred_language);
      this.setVal('set-speech-speed', data.speech_speed);
      this.setVal('set-threshold', data.low_stock_threshold_default);

      // Status badges
      this.setStatusBadge('status-gemini', data.gemini_ready);
      this.setStatusBadge('status-gnani-stt', data.gnani_stt_ready);
      this.setStatusBadge('status-gnani-tts', data.gnani_tts_ready);
    } catch (err) {
      console.warn('Could not load settings:', err);
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
      el.textContent = 'Mock Fallback Mode';
    }
  },

  async saveSettings() {
    const payload = {
      shop_name: document.getElementById('set-shop-name')?.value,
      shop_name_ta: document.getElementById('set-shop-name-ta')?.value,
      owner_name: document.getElementById('set-owner-name')?.value,
      phone: document.getElementById('set-phone')?.value,
      address: document.getElementById('set-address')?.value,
      gstin: document.getElementById('set-gstin')?.value,
      voice_preferred_language: document.getElementById('set-voice-lang')?.value,
      speech_speed: parseFloat(document.getElementById('set-speech-speed')?.value || '1.0'),
      low_stock_threshold_default: parseFloat(document.getElementById('set-threshold')?.value || '5.0'),
    };

    try {
      await ApiService.updateStoreSettings(payload);
      Utils.showToast('success', 'Settings Saved', 'Store configuration successfully updated.');
    } catch (err) {
      Utils.showToast('danger', 'Save Failed', err.message || 'Could not update settings');
    }
  }
};

