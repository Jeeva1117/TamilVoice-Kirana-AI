/**
 * TamilVoice Kirana AI - Utilities & Helpers
 * Reusable helper functions for UI, formatting, notifications & localization
 */

export const Utils = {
  /**
   * Format number as Indian Rupee (INR)
   * @param {number} amount
   * @param {boolean} includeDecimals
   * @returns {string}
   */
  formatINR(amount, includeDecimals = false) {
    if (isNaN(amount)) return '₹0';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: includeDecimals ? 2 : 0,
      maximumFractionDigits: includeDecimals ? 2 : 0,
    }).format(amount);
  },

  /**
   * Format date into user-friendly string
   * @param {Date|string} date
   * @param {string} lang - 'en' | 'ta'
   * @returns {string}
   */
  formatDate(date, lang = 'en') {
    const d = new Date(date);
    if (isNaN(d.getTime())) return '';
    
    if (lang === 'ta') {
      const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
      return d.toLocaleDateString('ta-IN', options);
    }
    
    return d.toLocaleDateString('en-IN', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  },

  /**
   * Format time in 12-hour format with AM/PM
   * @param {Date|string} date
   * @returns {string}
   */
  formatTime(date) {
    const d = new Date(date);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  },

  /**
   * Debounce helper for search and input handlers
   */
  debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  /**
   * Display a clean toast notification
   * @param {'success'|'warning'|'error'|'info'} type
   * @param {string} title
   * @param {string} message
   * @param {number} duration
   */
  showToast(type = 'info', title = '', message = '', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');

    const icons = {
      success: `<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>`,
      warning: `<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>`,
      error: `<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>`,
      info: `<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>`
    };

    toast.innerHTML = `
      ${icons[type] || icons.info}
      <div class="toast-content">
        ${title ? `<div class="toast-title">${title}</div>` : ''}
        <div class="toast-message">${message}</div>
      </div>
      <button class="toast-close" aria-label="Close Notification">&times;</button>
    `;

    // Close button click
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
      dismissToast(toast);
    });

    container.appendChild(toast);

    // Auto dismiss
    const autoDismissTimer = setTimeout(() => {
      dismissToast(toast);
    }, duration);

    function dismissToast(el) {
      clearTimeout(autoDismissTimer);
      el.classList.add('removing');
      setTimeout(() => {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 250);
    }
  },

  /**
   * Translations for bilingual Tamil & English UI
   */
  translations: {
    en: {
      appName: 'TamilVoice Kirana AI',
      welcome: 'Vanakkam! Welcome back.',
      welcomeSub: "Today's store performance and live overview.",
      shopName: 'Karthik Kirana Store',
      aiStatus: 'TamilVoice AI Ready',
      todaysRevenue: "Today's Revenue",
      totalSales: 'Total Sales',
      ordersToday: 'Orders Today',
      lowStockItems: 'Low Stock Items',
      totalProducts: 'Total Products',
      salesAnalytics: 'Sales & Revenue Analytics',
      topProducts: 'Top Selling Products',
      inventoryAlerts: 'Low Stock Alerts',
      recentTransactions: 'Recent Transactions',
      viewAll: 'View All',
      restockNow: 'Restock',
      speakVoice: 'Speak in Tamil',
      searchPlaceholder: 'Search products, bills...',
    },
    ta: {
      appName: 'தமிழ் வாய்ஸ் கிரானா AI',
      welcome: 'வணக்கம்! மீண்டும் வருக.',
      welcomeSub: 'உங்கள் கடையின் இன்றைய நிலவரம் மற்றும் நேரடி தகவல்.',
      shopName: 'கார்த்திக் மளிகைக் கடை',
      aiStatus: 'தமிழ் வாய்ஸ் AI தயார்',
      todaysRevenue: 'இன்றைய வருமானம்',
      totalSales: 'மொத்த விற்பனை',
      ordersToday: 'இன்றைய பில்கள்',
      lowStockItems: 'குறைந்த இருப்பு பொருட்கள்',
      totalProducts: 'மொத்த பொருட்கள்',
      salesAnalytics: 'விற்பனை மற்றும் வருமான அறிக்கை',
      topProducts: 'அதிகம் விற்பனையானவை',
      inventoryAlerts: 'இருப்பு குறைவு எச்சரிக்கைகள்',
      recentTransactions: 'சமீபத்திய பரிவர்த்தனைகள்',
      viewAll: 'அனைத்தையும் காண்க',
      restockNow: 'இருப்பு சேர்க்க',
      speakVoice: 'தமிழில் பேசவும்',
      searchPlaceholder: 'பொருட்கள், பில்களை தேட...',
    }
  }
};

