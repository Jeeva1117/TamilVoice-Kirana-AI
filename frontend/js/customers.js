/**
 * TamilVoice Kirana AI - Customers & Udhaar Khata Controller
 * Manages regular store customers, credit balances, payment logging and purchase history.
 */
import { ApiService } from './api.js';
import { Utils } from './utils.js';

export const Customers = {
  initialized: false,
  activeCustomerId: null,

  init() {
    if (this.initialized) return;
    this.cacheDOM();
    this.bindEvents();
    this.initialized = true;

    window.addEventListener('view-changed', (e) => {
      if (e.detail && e.detail.view === 'customers') {
        this.loadCustomers();
      }
    });
  },

  cacheDOM() {
    this.container = document.getElementById('view-customers');
  },

  bindEvents() {
    if (!this.container) return;

    this.container.addEventListener('click', (e) => {
      const payBtn = e.target.closest('[data-pay-customer-id]');
      if (payBtn) {
        const custId = parseInt(payBtn.getAttribute('data-pay-customer-id'), 10);
        const name = payBtn.getAttribute('data-customer-name');
        const bal = parseFloat(payBtn.getAttribute('data-customer-balance')) || 0;
        this.openPaymentModal(custId, name, bal);
      }

      if (e.target.closest('#btn-add-customer-modal')) {
        this.openAddCustomerModal();
      }

      if (e.target.closest('#btn-refresh-customers')) {
        this.loadCustomers();
      }
    });

    const searchInput = document.getElementById('customer-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', Utils.debounce((e) => {
        this.loadCustomers(e.target.value.trim());
      }, 300));
    }
  },

  async loadCustomers(search = '') {
    const tbody = document.getElementById('customers-tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:2rem; color:var(--color-text-secondary);">Loading customer ledger...</td></tr>`;

    try {
      const params = search ? { search } : {};
      const res = await ApiService.getCustomers(params);
      const items = res.items || [];

      if (items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:2rem; color:var(--color-text-secondary);">No customer records found.</td></tr>`;
        return;
      }

      tbody.innerHTML = items.map(c => `
        <tr>
          <td>
            <div style="font-weight:600; color:var(--color-text-primary); font-size:0.95rem;">${c.name}</div>
            <div style="font-size:0.75rem; color:var(--color-text-muted);">Joined ${new Date(c.created_at).toLocaleDateString('en-IN')}</div>
          </td>
          <td>
            <span style="font-family:var(--font-mono); font-size:0.875rem;">${c.phone || '—'}</span>
          </td>
          <td style="color:var(--color-text-secondary); font-size:0.85rem; max-width:200px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">
            ${c.address || '—'}
          </td>
          <td>
            <span class="badge ${c.credit_balance > 0 ? 'badge-danger' : 'badge-success'}" style="font-size:0.875rem; font-weight:600;">
              ₹${(c.credit_balance || 0).toLocaleString('en-IN')}
            </span>
          </td>
          <td style="text-align:right;">
            <button class="btn btn-secondary btn-sm"
              data-pay-customer-id="${c.id}"
              data-customer-name="${c.name}"
              data-customer-balance="${c.credit_balance}">
              Settle Payment
            </button>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--color-danger); padding:1rem;">Failed to load customers from backend.</td></tr>`;
    }
  },

  openAddCustomerModal() {
    const name = prompt('Enter Customer Full Name:');
    if (!name || !name.trim()) return;
    const phone = prompt('Enter Phone Number (+91...):') || '';
    const address = prompt('Enter Address / Area:') || '';

    ApiService.createCustomer({ name: name.trim(), phone: phone.trim(), address: address.trim(), credit_balance: 0.0 })
      .then(() => {
        Utils.showToast('success', 'Customer Added', `Customer ${name} registered in Khata.`);
        this.loadCustomers();
      })
      .catch(err => {
        Utils.showToast('danger', 'Error', err.message || 'Failed to add customer');
      });
  },

  openPaymentModal(customerId, name, currentBalance) {
    const amountStr = prompt(`Settle Udhaar for ${name}\nCurrent Balance: ₹${currentBalance}\nEnter payment amount (₹):`);
    if (!amountStr) return;
    const amount = parseFloat(amountStr);
    if (isNaN(amount) || amount <= 0) {
      Utils.showToast('danger', 'Invalid Amount', 'Please enter a valid positive payment number.');
      return;
    }

    ApiService.recordCustomerPayment(customerId, { amount, payment_method: 'CASH', notes: 'Manual payment settlement' })
      .then(res => {
        Utils.showToast('success', 'Payment Settled', `Logged ₹${amount} payment for ${name}. Remaining balance: ₹${res.remaining_balance}`);
        this.loadCustomers();
      })
      .catch(err => {
        Utils.showToast('danger', 'Payment Error', err.message || 'Failed to process payment');
      });
  }
};
