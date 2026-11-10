/**
 * TamilVoice Kirana AI - Navigation Controller
 * Handles sidebar toggling, desktop collapse, mobile drawer & view switching
 */

export const Navigation = {
  activeView: 'dashboard',

  init() {
    this.cacheDOM();
    this.bindEvents();
    this.restoreSidebarState();
  },

  cacheDOM() {
    this.sidebar = document.querySelector('.app-sidebar');
    this.mainWrapper = document.querySelector('.main-wrapper');
    this.collapseBtn = document.querySelector('.collapse-btn');
    this.mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    this.sidebarOverlay = document.querySelector('.sidebar-overlay');
    this.navLinks = document.querySelectorAll('.nav-link[data-view]');
    this.viewPanes = document.querySelectorAll('.view-pane');
    this.pageTitle = document.querySelector('.page-title');
    this.breadcrumbCurrent = document.querySelector('.breadcrumb-current');
    this.mobileNavItems = document.querySelectorAll('.mobile-nav-item[data-view]');
  },

  bindEvents() {
    // Desktop Sidebar Collapse Toggle
    if (this.collapseBtn) {
      this.collapseBtn.addEventListener('click', () => this.toggleDesktopSidebar());
    }

    // Mobile Hamburger Menu Button
    if (this.mobileMenuBtn) {
      this.mobileMenuBtn.addEventListener('click', () => this.openMobileSidebar());
    }

    // Mobile Drawer Overlay Click
    if (this.sidebarOverlay) {
      this.sidebarOverlay.addEventListener('click', () => this.closeMobileSidebar());
    }

    // Navigation Links & Elements with [data-view] Click Handling
    document.querySelectorAll('[data-view]').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const targetView = link.getAttribute('data-view');
        if (targetView) {
          this.switchView(targetView);
          this.closeMobileSidebar();
        }
      });
    });

    // Mobile Bottom Nav Items
    this.mobileNavItems.forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const targetView = item.getAttribute('data-view');
        if (targetView) {
          this.switchView(targetView);
        }
      });
    });

    // Listen for hash change if user uses browser back/forward
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.replace('#', '');
      if (hash && hash !== this.activeView) {
        this.switchView(hash, false);
      }
    });

    // Keyboard shortcut '/' to focus global search
    window.addEventListener('keydown', (e) => {
      if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
        e.preventDefault();
        const searchInput = document.querySelector('.global-search-input');
        if (searchInput) searchInput.focus();
      }
      // Esc closes mobile sidebar
      if (e.key === 'Escape' && this.sidebar.classList.contains('mobile-open')) {
        this.closeMobileSidebar();
      }
    });
  },

  toggleDesktopSidebar() {
    if (!this.sidebar || !this.mainWrapper) return;
    const isCollapsed = this.sidebar.classList.toggle('collapsed');
    this.mainWrapper.classList.toggle('sidebar-collapsed', isCollapsed);
    localStorage.setItem('tv_sidebar_collapsed', isCollapsed ? 'true' : 'false');
  },

  restoreSidebarState() {
    const saved = localStorage.getItem('tv_sidebar_collapsed');
    if (saved === 'true' && window.innerWidth > 992) {
      this.sidebar.classList.add('collapsed');
      this.mainWrapper.classList.add('sidebar-collapsed');
    }
  },

  openMobileSidebar() {
    if (this.sidebar) this.sidebar.classList.add('mobile-open');
    if (this.sidebarOverlay) this.sidebarOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  },

  closeMobileSidebar() {
    if (this.sidebar) this.sidebar.classList.remove('mobile-open');
    if (this.sidebarOverlay) this.sidebarOverlay.classList.remove('active');
    document.body.style.overflow = '';
  },

  /**
   * Switch the active view
   * @param {string} viewId
   * @param {boolean} updateHash
   */
  switchView(viewId, updateHash = true) {
    const targetPane = document.getElementById(`view-${viewId}`);
    if (!targetPane) {
      console.warn(`View #view-${viewId} not found.`);
      return;
    }

    // Hide all panes, show active
    this.viewPanes.forEach(pane => pane.classList.remove('active'));
    targetPane.classList.add('active');

    // Update desktop sidebar links
    this.navLinks.forEach(link => {
      const isTarget = link.getAttribute('data-view') === viewId;
      link.classList.toggle('active', isTarget);
      if (isTarget) {
        link.setAttribute('aria-current', 'page');
      } else {
        link.removeAttribute('aria-current');
      }
    });

    // Update mobile bottom nav links
    this.mobileNavItems.forEach(item => {
      item.classList.toggle('active', item.getAttribute('data-view') === viewId);
    });

    // Update Header Title & Breadcrumb
    this.updateHeaderMeta(viewId);

    this.activeView = viewId;
    if (updateHash) {
      window.location.hash = viewId;
    }

    // Dispatch custom event for view modules to refresh if needed
    window.dispatchEvent(new CustomEvent('view-changed', { detail: { view: viewId } }));
  },

  updateHeaderMeta(viewId) {
    const titles = {
      dashboard: { en: 'Dashboard Overview', ta: 'கடையின் சுருக்கம்' },
      voice: { en: 'Tamil Voice Assistant', ta: 'தமிழ் வாய்ஸ் அசிஸ்டண்ட்' },
      inventory: { en: 'Inventory Management', ta: 'சரக்கு இருப்பு மேலாண்மை' },
      sales: { en: 'Billing Counter', ta: 'பில்லிங் கவுண்டர்' },
      bills: { en: 'Bill History & Invoices', ta: 'பில் வரலாறு மற்றும் ரசீதுகள்' },
      reports: { en: 'Reports & Analytics', ta: 'வணிக அறிக்கைகள்' },
      customers: { en: 'Customer Khata Ledger', ta: 'வாடிக்கையாளர் கணக்கு' },
      settings: { en: 'Store Settings', ta: 'கடை அமைப்புகள்' },
      testing: { en: 'System Validation & Test Lab', ta: 'கணினி சோதனை அரங்கம்' }
    };

    const currentLang = localStorage.getItem('tv_lang') || 'en';
    const info = titles[viewId] || { en: 'Dashboard', ta: 'முகப்பு' };
    
    if (this.pageTitle) {
      this.pageTitle.textContent = currentLang === 'ta' ? info.ta : info.en;
    }
    if (this.breadcrumbCurrent) {
      this.breadcrumbCurrent.textContent = currentLang === 'ta' ? info.ta : info.en;
    }
  }
};

