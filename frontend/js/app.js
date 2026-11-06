/**
 * TamilVoice Kirana AI - Main Application Controller
 * Bootstraps modules, coordinates state, handles localization and global events
 */

import { Utils } from './utils.js';
import { Store } from './store.js';
import { Navigation } from './navigation.js';
import { Dashboard } from './dashboard.js';
import { VoiceAssistant } from './voice.js';
import { Inventory } from './inventory.js';
import { Sales } from './sales.js';

export const App = {
  currentLang: 'en',

  init() {
    Store.init();
    this.initLanguage();
    Navigation.init();
    Dashboard.init();
    VoiceAssistant.init();
    Inventory.init();
    Sales.init();
    this.bindGlobalEvents();

    // Check if initial hash is set (e.g. #voice)
    const initialHash = window.location.hash.replace('#', '');
    if (initialHash && ['dashboard', 'voice', 'inventory', 'sales', 'reports', 'customers', 'settings'].includes(initialHash)) {
      Navigation.switchView(initialHash, false);
    }

    console.log('%c TamilVoice Kirana AI %c Ready ', 'background: #2563EB; color: #fff; font-weight: bold; padding: 4px 8px; border-radius: 4px 0 0 4px;', 'background: #0F172A; color: #93C5FD; padding: 4px 8px; border-radius: 0 4px 4px 0;');
  },

  initLanguage() {
    this.currentLang = localStorage.getItem('tv_lang') || 'en';
    this.updateLanguageUI(this.currentLang);

    const langButtons = document.querySelectorAll('.lang-btn');
    langButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const selectedLang = btn.getAttribute('data-lang');
        if (selectedLang && selectedLang !== this.currentLang) {
          this.setLanguage(selectedLang);
        }
      });
    });
  },

  setLanguage(lang) {
    this.currentLang = lang;
    localStorage.setItem('tv_lang', lang);
    this.updateLanguageUI(lang);
    Navigation.updateHeaderMeta(Navigation.activeView);
    Dashboard.updateClockAndDate();
    window.dispatchEvent(new CustomEvent('language-changed', { detail: { lang } }));

    const toastMsg = lang === 'ta' ? 'மொழி தமிழுக்கு மாற்றப்பட்டது' : 'Language switched to English';
    Utils.showToast('info', 'Language Updated', toastMsg, 2500);
  },

  updateLanguageUI(lang) {
    document.querySelectorAll('.lang-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-lang') === lang);
    });

    // Update data-i18n elements
    const i18nElements = document.querySelectorAll('[data-i18n]');
    i18nElements.forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (Utils.translations[lang] && Utils.translations[lang][key]) {
        el.textContent = Utils.translations[lang][key];
      }
    });

    // Toggle html lang attribute
    document.documentElement.setAttribute('lang', lang);
  },

  bindGlobalEvents() {
    // Quick Voice Action Hero Button Click
    const heroVoiceBtn = document.getElementById('btn-hero-voice');
    if (heroVoiceBtn) {
      heroVoiceBtn.addEventListener('click', () => {
        Navigation.switchView('voice');
        Utils.showToast('info', 'Voice Assistant', 'Tamil Voice Assistant activated. Click microphone to speak.');
      });
    }

    // Voice Teaser Banner Button Click
    const bannerVoiceBtn = document.getElementById('btn-banner-voice');
    if (bannerVoiceBtn) {
      bannerVoiceBtn.addEventListener('click', () => {
        Navigation.switchView('voice');
      });
    }

    // Quick New Sale Button Click
    const newSaleBtn = document.getElementById('btn-quick-new-sale');
    if (newSaleBtn) {
      newSaleBtn.addEventListener('click', () => {
        Navigation.switchView('sales');
        Utils.showToast('info', 'New Sale', 'Navigating to billing and sales management.');
      });
    }

    // Notifications Button Click
    const notifBtn = document.getElementById('btn-notifications');
    if (notifBtn) {
      notifBtn.addEventListener('click', () => {
        Utils.showToast('info', 'Notifications', 'You have 6 low-stock alerts and 1 daily backup notice.');
      });
    }

    // Global Search Input with debounce
    const searchInput = document.querySelector('.global-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', Utils.debounce((e) => {
        const query = e.target.value.trim();
        if (query.length > 1) {
          Utils.showToast('info', 'Search', `Searching for "${query}" across inventory & bills...`, 2000);
        }
      }, 400));
    }
  }
};

// Auto-run when DOM is fully loaded in browser
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      App.init();
    });
  } else {
    App.init();
  }
}
