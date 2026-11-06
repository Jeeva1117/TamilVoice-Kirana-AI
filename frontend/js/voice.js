/**
 * TamilVoice Kirana AI - Voice Assistant Controller
 * Phase 2: MediaRecorder API, 7 UI States, Demo Commands, Intent Extraction,
 * Confirmation Workflow, SpeechSynthesis TTS, and Conversation History.
 */

import { Utils } from './utils.js';

export const VoiceAssistant = {
  // 7 Voice States
  STATES: {
    IDLE: 'idle',
    LISTENING: 'listening',
    PROCESSING: 'processing',
    CONFIRMATION: 'confirmation',
    EXECUTING: 'executing',
    SUCCESS: 'success',
    ERROR: 'error'
  },

  currentState: 'idle',
  mediaRecorder: null,
  mediaStream: null,
  audioChunks: [],
  recordingInterval: null,
  recordingStartTime: 0,
  activeLanguage: 'ta', // 'ta' | 'tanglish' | 'en'

  // Current Pending Action for Confirmation
  currentAction: null,

  // Demo Commands Library
  demoCommands: [
    {
      id: 'cmd-1',
      category: 'Inventory',
      command: 'Innaiku 5 kilo rice stock add pannunga.',
      commandTa: 'இன்று 5 கிலோ அரிசி சரக்கு சேர்க்கவும்.',
      action: 'Add Stock',
      actionTa: 'சரக்கு சேர்க்க',
      product: 'Ponni Boiled Rice',
      productTa: 'பொன்னி அரிசி',
      quantity: 5,
      unit: 'kg',
      requiresConfirmation: true,
      responseTa: 'சரி! 5 கிலோ பொன்னி அரிசி stock சேர்க்கப்பட்டது (Demo).',
      responseTanglish: 'Seri! 5 kilo Ponni rice stock add panna confirmation aachu (Demo).',
      responseEn: 'Confirmed! 5 kg of Ponni Rice has been added to stock (Demo).'
    },
    {
      id: 'cmd-2',
      category: 'Sales',
      command: 'Innaiku 2 litre oil sell panniten.',
      commandTa: 'இன்று 2 லிட்டர் எண்ணெய் விற்பனை ஆனது.',
      action: 'Record Sale',
      actionTa: 'விற்பனை பதிவு',
      product: 'Gold Winner Sunflower Oil',
      productTa: 'சூரியகாந்தி எண்ணெய்',
      quantity: 2,
      unit: 'litre',
      requiresConfirmation: true,
      responseTa: 'சரி! 2 லிட்டர் சூரியகாந்தி எண்ணெய் விற்பனை பதிவு செய்யப்பட்டது (Demo).',
      responseTanglish: 'Seri! 2 litre oil sale record panniyachu (Demo).',
      responseEn: 'Sale recorded: 2 litres of Sunflower Oil (Demo).'
    },
    {
      id: 'cmd-3',
      category: 'Stock Query',
      command: 'Rice stock evlo irukku?',
      commandTa: 'அரிசி இருப்பு எவ்வளவு உள்ளது?',
      action: 'Check Inventory',
      actionTa: 'இருப்பு சோதனை',
      product: 'Ponni Boiled Rice',
      productTa: 'பொன்னி அரிசி',
      quantity: 24,
      unit: 'bags',
      requiresConfirmation: false,
      responseTa: 'பொன்னி அரிசி தற்போது 24 மூட்டைகள் இருப்பில் உள்ளது.',
      responseTanglish: 'Ponni rice stock kitta thatta 24 bags irukku.',
      responseEn: 'Current stock of Ponni Boiled Rice is 24 bags.'
    },
    {
      id: 'cmd-4',
      category: 'Low Stock',
      command: 'Low stock products sollunga.',
      commandTa: 'குறைந்த இருப்பு பொருட்களை சொல்லவும்.',
      action: 'List Low Stock',
      actionTa: 'குறைந்த இருப்பு பட்டியல்',
      product: '6 items needing re-order',
      productTa: '6 பொருட்கள் தேவை',
      quantity: 6,
      unit: 'items',
      requiresConfirmation: false,
      responseTa: 'கவனிக்கவும்! 6 பொருட்கள் குறைந்த இருப்பில் உள்ளன. எண்ணெய் மற்றும் உப்பு உடனே ஆர்டர் செய்ய வேண்டும்.',
      responseTanglish: '6 products low stock-la irukku. Oil and salt udane re-order pannanum.',
      responseEn: 'Attention: 6 items are low on stock, including sunflower oil and iodized salt.'
    },
    {
      id: 'cmd-5',
      category: 'Sales Query',
      command: 'Innaiku sales evlo?',
      commandTa: 'இன்றைய விற்பனை எவ்வளவு?',
      action: 'Get Daily Sales',
      actionTa: 'இன்றைய விற்பனை தகவல்',
      product: 'Daily Total Revenue',
      productTa: 'இன்றைய மொத்த வரவு',
      quantity: 18450,
      unit: 'INR (₹)',
      requiresConfirmation: false,
      responseTa: 'இன்று இதுவரை ₹18,450 விற்பனை ஆகியுள்ளது. மொத்தம் 142 பில்கள் போடப்பட்டுள்ளன.',
      responseTanglish: 'Innaiku idhuvaraikkum ₹18,450 sales aagi irukku. Total 142 bills.',
      responseEn: "Today's sales total ₹18,450 across 142 completed bills."
    }
  ],

  init() {
    this.cacheDOM();
    this.bindEvents();
    this.loadHistory();
    this.setState(this.STATES.IDLE);
  },

  cacheDOM() {
    this.stageCard = document.getElementById('voice-stage-card');
    this.micBtn = document.getElementById('btn-main-mic');
    this.stopRecBtn = document.getElementById('btn-stop-recording');
    this.recTimer = document.getElementById('voice-rec-timer');
    this.statusPill = document.getElementById('voice-status-pill');
    this.statusPillText = document.getElementById('voice-status-pill-text');
    this.promptText = document.getElementById('voice-prompt-text');
    this.transcriptTextarea = document.getElementById('voice-transcript-input');
    this.editTranscriptBtn = document.getElementById('btn-edit-transcript');
    
    // AI Interpretation elements
    this.actionVal = document.getElementById('entity-action');
    this.productVal = document.getElementById('entity-product');
    this.qtyVal = document.getElementById('entity-qty');
    this.confidenceVal = document.getElementById('entity-confidence');

    // Confirmation elements
    this.confirmationCard = document.getElementById('voice-confirmation-card');
    this.confirmationSummary = document.getElementById('confirmation-summary-text');
    this.btnConfirmAction = document.getElementById('btn-confirm-action');
    this.btnEditAction = document.getElementById('btn-edit-action');
    this.btnCancelAction = document.getElementById('btn-cancel-action');
    this.inlineEditForm = document.getElementById('inline-edit-form');
    this.editActionType = document.getElementById('edit-action-type');
    this.editProduct = document.getElementById('edit-product-name');
    this.editQuantity = document.getElementById('edit-quantity');
    this.editUnit = document.getElementById('edit-unit');
    this.btnApplyEdit = document.getElementById('btn-apply-edit');

    // Assistant Response elements
    this.responseBubble = document.getElementById('assistant-response-bubble');
    this.responseTabs = document.querySelectorAll('.response-tab-btn');
    this.btnSpeak = document.getElementById('btn-speak-response');
    this.btnStopSpeak = document.getElementById('btn-stop-speak');
    this.ttsNotice = document.getElementById('tts-voice-notice');

    // Demo commands container
    this.demoCommandsGrid = document.getElementById('demo-commands-grid');

    // History elements
    this.historyList = document.getElementById('voice-history-list');
    this.btnClearHistory = document.getElementById('btn-clear-history');

    // Language chips in header
    this.langChips = document.querySelectorAll('.lang-chip[data-voice-lang]');
  },

  bindEvents() {
    // Microphone Click Handler
    if (this.micBtn) {
      this.micBtn.addEventListener('click', () => {
        if (this.currentState === this.STATES.LISTENING) {
          this.stopRecording();
        } else if (this.currentState === this.STATES.IDLE || this.currentState === this.STATES.SUCCESS || this.currentState === this.STATES.ERROR) {
          this.startRecording();
        }
      });
    }

    // Stop Recording Button
    if (this.stopRecBtn) {
      this.stopRecBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.stopRecording();
      });
    }

    // Language Selector Chips (Tamil / Tanglish / English)
    this.langChips.forEach(chip => {
      chip.addEventListener('click', () => {
        this.langChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        this.activeLanguage = chip.getAttribute('data-voice-lang') || 'ta';
        this.updateResponseLanguage(this.activeLanguage);
      });
    });

    // Demo Command Chips Click
    if (this.demoCommandsGrid) {
      this.renderDemoCommandChips();
    }

    // Editable Transcript
    if (this.editTranscriptBtn && this.transcriptTextarea) {
      this.editTranscriptBtn.addEventListener('click', () => {
        const isReadonly = this.transcriptTextarea.hasAttribute('readonly');
        if (isReadonly) {
          this.transcriptTextarea.removeAttribute('readonly');
          this.transcriptTextarea.focus();
          this.editTranscriptBtn.textContent = 'Save';
          this.editTranscriptBtn.classList.add('btn-primary');
          this.editTranscriptBtn.classList.remove('btn-outline');
        } else {
          this.transcriptTextarea.setAttribute('readonly', 'true');
          this.editTranscriptBtn.textContent = 'Edit';
          this.editTranscriptBtn.classList.remove('btn-primary');
          this.editTranscriptBtn.classList.add('btn-outline');
          Utils.showToast('info', 'Transcript Updated', 'AI entity interpretation refreshed.');
        }
      });
    }

    // Confirmation Action Buttons
    if (this.btnConfirmAction) {
      this.btnConfirmAction.addEventListener('click', () => this.confirmPendingAction());
    }

    if (this.btnEditAction) {
      this.btnEditAction.addEventListener('click', () => this.toggleInlineEdit());
    }

    if (this.btnApplyEdit) {
      this.btnApplyEdit.addEventListener('click', () => this.applyEditedDetails());
    }

    if (this.btnCancelAction) {
      this.btnCancelAction.addEventListener('click', () => this.cancelPendingAction());
    }

    // Response Language Tabs
    this.responseTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        this.responseTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const lang = tab.getAttribute('data-lang');
        this.updateResponseLanguage(lang);
      });
    });

    // TTS Speak & Stop Speak
    if (this.btnSpeak) {
      this.btnSpeak.addEventListener('click', () => this.speakResponse());
    }
    if (this.btnStopSpeak) {
      this.btnStopSpeak.addEventListener('click', () => this.stopSpeaking());
    }

    // Clear History Button
    if (this.btnClearHistory) {
      this.btnClearHistory.addEventListener('click', () => this.clearHistory());
    }
  },

  /**
   * Set one of the 7 voice interaction states
   * @param {string} state - idle | listening | processing | confirmation | executing | success | error
   * @param {string} customMsg
   */
  setState(state, customMsg = '') {
    this.currentState = state;

    // Reset classes on stage card
    if (this.stageCard) {
      this.stageCard.className = `voice-stage-card state-${state}`;
    }

    // Reset status pill
    if (this.statusPill) {
      this.statusPill.className = `voice-status-pill ${state}`;
    }

    const stateLabels = {
      idle: 'Idle — Ready',
      listening: 'Listening...',
      processing: 'Processing AI Intent...',
      confirmation: 'Confirmation Required',
      executing: 'Executing Action...',
      success: 'Demo Action Completed',
      error: 'Error Occurred'
    };

    const promptMessages = {
      idle: '“வணக்கம்! உங்கள் கடைக்கு இன்று என்ன செய்ய வேண்டும்?”',
      listening: '“Listening... Speak in colloquial Tamil or Tanglish.”',
      processing: '“Understanding your request through AI reasoning...”',
      confirmation: '“Always review and confirm details before executing.”',
      executing: '“Simulating business record update in demo mode...”',
      success: '“சரி! உங்கள் செயல்பாடு வெற்றிகரமாக முடிந்தது (Demo).”',
      error: '“Microphone permission denied or recognition error.”'
    };

    if (this.statusPillText) {
      this.statusPillText.textContent = stateLabels[state] || state;
    }

    if (this.promptText) {
      this.promptText.textContent = customMsg || promptMessages[state] || '';
    }

    // Toggle mic button accessibility state
    if (this.micBtn) {
      this.micBtn.disabled = (state === this.STATES.PROCESSING || state === this.STATES.EXECUTING);
    }

    // Hide or show confirmation card
    if (this.confirmationCard) {
      if (state === this.STATES.CONFIRMATION) {
        this.confirmationCard.classList.add('active');
      } else {
        this.confirmationCard.classList.remove('active');
        if (this.inlineEditForm) this.inlineEditForm.classList.remove('active');
      }
    }
  },

  /**
   * Browser MediaRecorder Audio Capture
   */
  async startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.setState(this.STATES.ERROR, 'Browser does not support MediaRecorder or microphone access.');
      Utils.showToast('error', 'Microphone Unsupported', 'Your browser does not support audio recording.');
      return;
    }

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioChunks = [];

      this.mediaRecorder = new MediaRecorder(this.mediaStream);
      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.audioChunks.push(e.data);
      };

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        console.log('[MediaRecorder] Audio captured locally:', audioBlob.size, 'bytes');
        // Release tracks
        if (this.mediaStream) {
          this.mediaStream.getTracks().forEach(track => track.stop());
          this.mediaStream = null;
        }
      };

      this.mediaRecorder.start();
      this.setState(this.STATES.LISTENING);
      this.startTimer();
      Utils.showToast('info', 'Listening', 'Microphone active. Speak your command in Tamil.');

    } catch (err) {
      console.error('[MediaRecorder Error]', err);
      let errorDesc = 'Microphone access failed.';
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        errorDesc = 'Microphone permission denied. Please allow microphone in browser site settings.';
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        errorDesc = 'No microphone device found on this system.';
      }
      this.setState(this.STATES.ERROR, errorDesc);
      Utils.showToast('error', 'Microphone Permission', errorDesc, 6000);
    }
  },

  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
    this.stopTimer();

    // Transition to Processing state
    this.setState(this.STATES.PROCESSING);

    // Simulate intent analysis (since backend is demo mode)
    setTimeout(() => {
      // Pick a sample demo command to demonstrate workflow
      const sample = this.demoCommands[0]; // Rice stock addition
      this.executeCommandWorkflow(sample, true);
    }, 1400);
  },

  startTimer() {
    this.recordingStartTime = Date.now();
    if (this.recTimer) this.recTimer.textContent = '00:00';

    this.recordingInterval = setInterval(() => {
      const elapsedSeconds = Math.floor((Date.now() - this.recordingStartTime) / 1000);
      const mins = String(Math.floor(elapsedSeconds / 60)).padStart(2, '0');
      const secs = String(elapsedSeconds % 60).padStart(2, '0');
      if (this.recTimer) this.recTimer.textContent = `${mins}:${secs}`;

      // Auto-stop after 15 seconds to prevent accidental runaway recording
      if (elapsedSeconds >= 15) {
        this.stopRecording();
      }
    }, 1000);
  },

  stopTimer() {
    if (this.recordingInterval) {
      clearInterval(this.recordingInterval);
      this.recordingInterval = null;
    }
  },

  /**
   * Render Demo Voice Command Chips
   */
  renderDemoCommandChips() {
    this.demoCommandsGrid.innerHTML = this.demoCommands.map(cmd => `
      <button class="demo-command-btn" data-cmd-id="${cmd.id}">
        <span class="demo-btn-category">${cmd.category}</span>
        <span class="demo-btn-text">"${cmd.command}"</span>
        <span class="demo-btn-sub">${cmd.commandTa}</span>
      </button>
    `).join('');

    this.demoCommandsGrid.querySelectorAll('.demo-command-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const cmdId = btn.getAttribute('data-cmd-id');
        const cmd = this.demoCommands.find(c => c.id === cmdId);
        if (cmd) {
          this.executeCommandWorkflow(cmd, false);
        }
      });
    });
  },

  /**
   * Execute Command Workflow with Transcript & Intent Extraction
   */
  executeCommandWorkflow(cmd, fromMic = false) {
    this.setState(this.STATES.PROCESSING);

    setTimeout(() => {
      // Populate Transcript
      if (this.transcriptTextarea) {
        this.transcriptTextarea.value = cmd.command;
      }

      // Populate Extracted AI Entities
      if (this.actionVal) this.actionVal.textContent = cmd.action;
      if (this.productVal) this.productVal.textContent = cmd.product;
      if (this.qtyVal) this.qtyVal.textContent = cmd.quantity ? `${cmd.quantity} ${cmd.unit}` : 'N/A';
      if (this.confidenceVal) this.confidenceVal.textContent = '98.5% (High)';

      this.currentAction = { ...cmd };

      // Populate Responses
      this.updateResponseText(cmd);

      // Check Confirmation Rule: NEVER auto-execute stock or sales
      if (cmd.requiresConfirmation) {
        this.setState(this.STATES.CONFIRMATION);
        if (this.confirmationSummary) {
          this.confirmationSummary.textContent = `Action: ${cmd.action} | Product: ${cmd.product} | Quantity: ${cmd.quantity} ${cmd.unit}`;
        }
        Utils.showToast('warning', 'Confirmation Required', `Please confirm before performing "${cmd.action}".`);
      } else {
        // Direct Query response
        this.setState(this.STATES.SUCCESS, `Done! ${cmd.action} query answered.`);
        this.addToHistory(cmd.command, cmd.action, 'Completed');
      }

      if (fromMic) {
        Utils.showToast('info', 'Demo Notice', 'Audio processed in demo mode. Voice AI backend integration in next phase.');
      }
    }, 900);
  },

  /**
   * User Confirms the Action
   */
  confirmPendingAction() {
    if (!this.currentAction) return;

    this.setState(this.STATES.EXECUTING);

    setTimeout(() => {
      this.setState(this.STATES.SUCCESS, `Success! ${this.currentAction.action} for ${this.currentAction.product} confirmed (Demo).`);
      this.addToHistory(this.currentAction.command, this.currentAction.action, 'Confirmed');
      Utils.showToast('success', 'Action Confirmed', `${this.currentAction.action} completed successfully in demo mode.`);
      
      // Auto-speak confirmation in Tamil if TTS is enabled
      this.speakResponse();
    }, 1100);
  },

  /**
   * User Toggles Inline Form to Edit Intent Details
   */
  toggleInlineEdit() {
    if (!this.inlineEditForm) return;
    const isActive = this.inlineEditForm.classList.toggle('active');
    
    if (isActive && this.currentAction) {
      if (this.editProduct) this.editProduct.value = this.currentAction.product;
      if (this.editQuantity) this.editQuantity.value = this.currentAction.quantity || 1;
      if (this.editUnit) this.editUnit.value = this.currentAction.unit || 'kg';
      if (this.editActionType) this.editActionType.value = this.currentAction.action;
    }
  },

  /**
   * Apply edited details
   */
  applyEditedDetails() {
    if (!this.currentAction) return;

    const newProd = this.editProduct ? this.editProduct.value.trim() : this.currentAction.product;
    const newQty = this.editQuantity ? parseFloat(this.editQuantity.value) : this.currentAction.quantity;
    const newUnit = this.editUnit ? this.editUnit.value : this.currentAction.unit;
    const newAct = this.editActionType ? this.editActionType.value : this.currentAction.action;

    this.currentAction.product = newProd;
    this.currentAction.quantity = newQty;
    this.currentAction.unit = newUnit;
    this.currentAction.action = newAct;

    // Refresh UI
    if (this.actionVal) this.actionVal.textContent = newAct;
    if (this.productVal) this.productVal.textContent = newProd;
    if (this.qtyVal) this.qtyVal.textContent = `${newQty} ${newUnit}`;
    if (this.confirmationSummary) {
      this.confirmationSummary.textContent = `Action: ${newAct} | Product: ${newProd} | Quantity: ${newQty} ${newUnit}`;
    }

    if (this.inlineEditForm) this.inlineEditForm.classList.remove('active');
    Utils.showToast('info', 'Details Updated', 'Pending action details updated.');
  },

  /**
   * User Cancels Action
   */
  cancelPendingAction() {
    this.currentAction = null;
    this.setState(this.STATES.IDLE, 'Action was cancelled by user. Returning to ready state.');
    Utils.showToast('info', 'Cancelled', 'Pending action was cancelled.');
  },

  /**
   * Update Assistant Response Text
   */
  updateResponseText(cmd) {
    if (!this.responseBubble) return;
    const textMap = {
      ta: cmd.responseTa,
      tanglish: cmd.responseTanglish,
      en: cmd.responseEn
    };
    this.responseBubble.textContent = textMap[this.activeLanguage] || cmd.responseTa;
  },

  updateResponseLanguage(lang) {
    this.activeLanguage = lang;
    if (this.currentAction) {
      this.updateResponseText(this.currentAction);
    }
  },

  /**
   * Text-to-Speech (TTS) using Browser SpeechSynthesis API
   */
  speakResponse() {
    if (!('speechSynthesis' in window)) {
      Utils.showToast('error', 'TTS Unsupported', 'Browser does not support SpeechSynthesis.');
      return;
    }

    const textToSpeak = this.responseBubble ? this.responseBubble.textContent : '';
    if (!textToSpeak) return;

    window.speechSynthesis.cancel(); // Stop any active speech

    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.rate = 0.95; // Slightly slower for crisp retail clarity
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    // Prefer Tamil voice (ta-IN or ta)
    const tamilVoice = voices.find(v => v.lang.includes('ta') || v.name.toLowerCase().includes('tamil'));
    
    if (tamilVoice) {
      utterance.voice = tamilVoice;
      if (this.ttsNotice) {
        this.ttsNotice.textContent = `Speaking with voice: ${tamilVoice.name} (ta-IN)`;
      }
    } else {
      if (this.ttsNotice) {
        this.ttsNotice.textContent = 'Browser voice demo — Native Tamil voice not found on device. Gnani Timbre integration pending.';
      }
    }

    utterance.onstart = () => {
      if (this.btnSpeak) this.btnSpeak.disabled = true;
      if (this.btnStopSpeak) this.btnStopSpeak.disabled = false;
    };

    utterance.onend = () => {
      if (this.btnSpeak) this.btnSpeak.disabled = false;
      if (this.btnStopSpeak) this.btnStopSpeak.disabled = true;
    };

    utterance.onerror = (e) => {
      console.warn('[SpeechSynthesis Error]', e);
      if (this.btnSpeak) this.btnSpeak.disabled = false;
      if (this.btnStopSpeak) this.btnStopSpeak.disabled = true;
    };

    window.speechSynthesis.speak(utterance);
  },

  stopSpeaking() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      if (this.btnSpeak) this.btnSpeak.disabled = false;
      if (this.btnStopSpeak) this.btnStopSpeak.disabled = true;
    }
  },

  /**
   * Conversation History Management
   */
  loadHistory() {
    const saved = localStorage.getItem('tv_voice_history');
    let history = [];
    if (saved) {
      try {
        history = JSON.parse(saved);
      } catch (e) {
        history = [];
      }
    }

    if (!history.length) {
      // Seed with initial realistic demo entries
      history = [
        { command: 'Innaiku 5 kilo rice stock add pannunga.', action: 'Add Stock', time: '10 mins ago', status: 'Demo' },
        { command: 'Sugar stock evlo irukku?', action: 'Check Inventory', time: '25 mins ago', status: 'Demo' }
      ];
      localStorage.setItem('tv_voice_history', JSON.stringify(history));
    }

    this.renderHistory(history);
  },

  renderHistory(history) {
    if (!this.historyList) return;

    if (!history.length) {
      this.historyList.innerHTML = `
        <div style="padding: 1.5rem; text-align: center; color: var(--color-text-muted); font-size: var(--font-size-xs);">
          No recent voice commands. Speak or select a demo command above.
        </div>
      `;
      return;
    }

    this.historyList.innerHTML = history.map(item => `
      <div class="history-item">
        <div class="history-left">
          <span class="history-cmd-text">"${item.command}"</span>
          <span class="history-meta">${item.action} • ${item.time}</span>
        </div>
        <span class="badge-pill info">${item.status || 'Demo'}</span>
      </div>
    `).join('');
  },

  addToHistory(command, action, status = 'Demo') {
    const saved = localStorage.getItem('tv_voice_history');
    let history = [];
    if (saved) {
      try { history = JSON.parse(saved); } catch (e) { history = []; }
    }

    const newItem = {
      command,
      action,
      time: Utils.formatTime(new Date()),
      status
    };

    history.unshift(newItem);
    if (history.length > 10) history.pop(); // keep last 10
    localStorage.setItem('tv_voice_history', JSON.stringify(history));
    this.renderHistory(history);
  },

  clearHistory() {
    localStorage.removeItem('tv_voice_history');
    this.renderHistory([]);
    Utils.showToast('info', 'History Cleared', 'Voice command history cleared.');
  }
};

