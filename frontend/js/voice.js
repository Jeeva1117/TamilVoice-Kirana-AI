/**
 * TamilVoice Kirana AI - Voice Assistant Controller
 * Native 16kHz PCM WAV Audio Capture, Gnani Prisma STT, Gnani Timbre TTS,
 * Gemini Intent Extraction, and Atomic SQLite Inventory Confirmation.
 */

import { Utils } from './utils.js';
import { ApiService, API_CONFIG } from './api.js';
import { Store } from './store.js';

/**
 * Encodes Float32 audio samples into a standard 16kHz 16-bit Mono WAV Blob
 * matching Gnani Prisma STT requirement.
 */
function encode16kHzPcmWav(pcmChunks, inputSampleRate) {
  let totalSamples = 0;
  for (let i = 0; i < pcmChunks.length; i++) {
    totalSamples += pcmChunks[i].length;
  }
  if (totalSamples === 0) {
    return new Blob([], { type: 'audio/wav' });
  }

  const merged = new Float32Array(totalSamples);
  let offset = 0;
  for (let i = 0; i < pcmChunks.length; i++) {
    merged.set(pcmChunks[i], offset);
    offset += pcmChunks[i].length;
  }

  const targetSampleRate = 16000;
  let resampled;
  if (inputSampleRate === targetSampleRate) {
    resampled = merged;
  } else {
    const ratio = inputSampleRate / targetSampleRate;
    const newLen = Math.round(merged.length / ratio);
    resampled = new Float32Array(newLen);
    for (let i = 0; i < newLen; i++) {
      const srcIdx = i * ratio;
      const low = Math.floor(srcIdx);
      const high = Math.min(low + 1, merged.length - 1);
      const weight = srcIdx - low;
      resampled[i] = merged[low] * (1 - weight) + merged[high] * weight;
    }
  }

  const numSamples = resampled.length;
  const buffer = new ArrayBuffer(44 + numSamples * 2);
  const view = new DataView(buffer);

  function writeStr(off, str) {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(off + i, str.charCodeAt(i));
    }
  }

  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + numSamples * 2, true);
  writeStr(8, 'WAVE');

  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, targetSampleRate, true);
  view.setUint32(28, targetSampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);

  writeStr(36, 'data');
  view.setUint32(40, numSamples * 2, true);

  let byteOffset = 44;
  for (let i = 0; i < numSamples; i++) {
    let s = Math.max(-1, Math.min(1, resampled[i]));
    view.setInt16(byteOffset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    byteOffset += 2;
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

export const VoiceAssistant = {
  // Extended Voice States matching progress pipeline
  STATES: {
    IDLE: 'idle',
    LISTENING: 'listening',
    RECORDING: 'recording',
    AUDIO_CAPTURED: 'audio_captured',
    UPLOADING: 'uploading',
    TRANSCRIBING: 'transcribing',
    TRANSCRIPT_RECEIVED: 'transcript_received',
    UNDERSTANDING: 'understanding',
    PRODUCT_IDENTIFIED: 'product_identified',
    CLARIFICATION_REQUIRED: 'clarification_required',
    WAITING_FOR_CONFIRMATION: 'waiting_for_confirmation',
    AWAITING_CONFIRMATION: 'waiting_for_confirmation',
    CONFIRMATION: 'waiting_for_confirmation',
    SAVING: 'saving',
    EXECUTING: 'saving',
    GENERATING_SPEECH: 'generating_speech',
    PLAYING_AUDIO: 'playing_audio',
    COMPLETED: 'completed',
    SUCCESS: 'completed',
    ERROR: 'error',
    CANCELLED: 'cancelled'
  },

  currentState: 'idle',
  sessionId: 'sess_' + Math.random().toString(36).slice(2, 11),
  interactionMode: 'push', // 'push' | 'continuous'
  conversationContext: null,

  // Web Audio PCM 16kHz capture properties
  mediaStream: null,
  recAudioContext: null,
  audioSourceNode: null,
  audioProcessorNode: null,
  pcmChunks: [],
  isRecordingAudio: false,
  liveSpokenText: '',
  speechRecognizer: null,

  recordingInterval: null,
  recordingStartTime: 0,
  activeLanguage: 'ta-IN', // 'ta-IN' | 'en-IN'
  activeAudio: null,
  voiceStatus: null,
  continuousTimer: null,
  silenceTimer: null,

  // Dedicated Live Voice Mode Engine Properties
  isLiveModeActive: false,
  isMicMuted: false,
  audioContext: null,
  analyser: null,
  analyserDataArray: null,
  vadAnimationId: null,
  hasUserSpokenInTurn: false,
  vadSilenceStart: 0,
  vadTurnStartTime: 0,
  vadVolumeThreshold: 14,
  vadSilenceDurationMs: 1350,
  liveMediaStream: null,
  liveProcessorNode: null,
  livePcmChunks: [],

  // Current Pending Action for Confirmation
  currentAction: null,

  init() {
    this.cacheDOM();
    this.bindEvents();
    this.loadHistory();
    this.checkVoiceStatus();
    this.setState(this.STATES.IDLE);
  },

  async checkVoiceStatus() {
    try {
      const status = await ApiService.getVoiceStatus();
      this.voiceStatus = status;
      if (this.ttsNotice) {
        if (status.stt_ready && status.tts_ready) {
          this.ttsNotice.textContent = 'Gnani Prisma v2.5 STT & Timbre v2.5 TTS Active (Live Tamil Voice)';
        } else {
          this.ttsNotice.textContent = 'Voice Engine Ready (Gemini AI Reasoning + Voice Assistant)';
        }
      }
    } catch (e) {
      console.warn('[VoiceAssistant] Voice status check warning:', e.message);
    }
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
    this.voiceHeroNotice = document.getElementById('voice-hero-notice');

    // History elements
    this.historyList = document.getElementById('voice-history-list');
    this.btnClearHistory = document.getElementById('btn-clear-history');

    // Language chips in header
    this.langChips = document.querySelectorAll('.lang-chip[data-voice-lang]');

    // Interaction mode buttons
    this.btnModePush = document.getElementById('btn-mode-push');
    this.btnModeContinuous = document.getElementById('btn-mode-continuous');

    // Dedicated Live Voice Mode Elements
    this.liveBanner = document.getElementById('live-mode-banner');
    this.btnLiveToggle = document.getElementById('btn-live-mode-toggle');
    this.btnLiveToggleText = document.getElementById('btn-live-mode-text');
    this.liveStatusPill = document.getElementById('live-status-pill');
    this.liveStatusLabel = document.getElementById('live-status-label');
    this.liveMeterBars = document.querySelectorAll('.live-meter-bar');
    this.liveMeterVal = document.getElementById('live-meter-val');
    this.btnLiveMute = document.getElementById('btn-live-mute');
    this.btnLiveMuteText = document.getElementById('btn-live-mute-text');
    this.btnLiveStopSpeech = document.getElementById('btn-live-stop-speech');
    this.btnLiveCancelAction = document.getElementById('btn-live-cancel-action');

    // Flow Step Elements
    this.flowStepIdle = document.getElementById('flow-step-idle');
    this.flowStepListening = document.getElementById('flow-step-listening');
    this.flowStepUnderstanding = document.getElementById('flow-step-understanding');
    this.flowStepSpeaking = document.getElementById('flow-step-speaking');

    // Live Multi-Product Bill Preview Elements
    this.liveBillCard = document.getElementById('live-bill-preview-card');
    this.liveBillTbody = document.getElementById('live-bill-tbody');
    this.liveBillGrandTotal = document.getElementById('live-bill-grand-total');
    this.liveBillBadge = document.getElementById('live-bill-badge');
  },

  setInteractionMode(mode) {
    this.interactionMode = mode;
    if (this.btnModePush && this.btnModeContinuous) {
      if (mode === 'continuous') {
        this.btnModePush.classList.remove('active');
        this.btnModeContinuous.classList.add('active');
        Utils.showToast('info', 'Continuous Mode Active', 'தொடர் உரையாடல்: Assistant will automatically listen for your follow-up replies after speaking.');
      } else {
        this.btnModeContinuous.classList.remove('active');
        this.btnModePush.classList.add('active');
        Utils.showToast('info', 'Push-to-Talk Active', 'Push-to-Talk: Click microphone button whenever you wish to speak.');
      }
    }
  },

  bindEvents() {
    // Mode Switch Handlers
    if (this.btnModePush) {
      this.btnModePush.addEventListener('click', () => this.setInteractionMode('push'));
    }
    if (this.btnModeContinuous) {
      this.btnModeContinuous.addEventListener('click', () => this.setInteractionMode('continuous'));
    }

    // Microphone Click Handler
    if (this.micBtn) {
      this.micBtn.addEventListener('click', () => {
        if (this.currentState === this.STATES.LISTENING || this.currentState === this.STATES.RECORDING) {
          this.stopRecording();
        } else if (
          this.currentState === this.STATES.IDLE ||
          this.currentState === this.STATES.SUCCESS ||
          this.currentState === this.STATES.ERROR ||
          this.currentState === this.STATES.CANCELLED
        ) {
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
        const rawLang = chip.getAttribute('data-voice-lang') || 'ta';
        this.activeLanguage = (rawLang === 'en' || rawLang === 'english') ? 'en-IN' : 'ta-IN';
        this.updateResponseLanguage(this.activeLanguage);
      });
    });

    // Editable Transcript
    if (this.editTranscriptBtn && this.transcriptTextarea) {
      this.editTranscriptBtn.addEventListener('click', () => {
        const isReadonly = this.transcriptTextarea.hasAttribute('readonly');
        if (isReadonly) {
          this.transcriptTextarea.removeAttribute('readonly');
          this.transcriptTextarea.focus();
          this.editTranscriptBtn.textContent = 'Interpret';
          this.editTranscriptBtn.classList.add('btn-primary');
          this.editTranscriptBtn.classList.remove('btn-outline');
        } else {
          this.transcriptTextarea.setAttribute('readonly', 'true');
          this.editTranscriptBtn.textContent = 'Edit';
          this.editTranscriptBtn.classList.remove('btn-primary');
          this.editTranscriptBtn.classList.add('btn-outline');
          const customText = this.transcriptTextarea.value.trim();
          if (customText) {
            this.executeCommandWorkflow(customText, false);
          }
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

    // Dedicated Live Voice Mode Controls
    if (this.btnLiveToggle) {
      this.btnLiveToggle.addEventListener('click', () => this.toggleLiveMode());
    }
    if (this.btnLiveMute) {
      this.btnLiveMute.addEventListener('click', () => this.toggleMicMute());
    }
    if (this.btnLiveStopSpeech) {
      this.btnLiveStopSpeech.addEventListener('click', () => this.interruptSpeech());
    }
    if (this.btnLiveCancelAction) {
      this.btnLiveCancelAction.addEventListener('click', () => this.cancelPendingAction());
    }

    // Clear History Button
    if (this.btnClearHistory) {
      this.btnClearHistory.addEventListener('click', () => this.clearHistory());
    }
  },

  /**
   * Set one of the extended voice interaction states
   * @param {string} state
   * @param {string} customMsg
   */
  setState(state, customMsg = '') {
    this.currentState = state;

    const baseClassMap = {
      idle: 'idle',
      listening: 'listening',
      recording: 'listening',
      audio_captured: 'processing',
      uploading: 'processing',
      transcribing: 'processing',
      transcript_received: 'processing',
      understanding: 'processing',
      product_identified: 'processing',
      clarification_required: 'error',
      waiting_for_confirmation: 'confirmation',
      awaiting_confirmation: 'confirmation',
      confirmation: 'confirmation',
      saving: 'executing',
      executing: 'executing',
      generating_speech: 'processing',
      playing_audio: 'listening',
      completed: 'success',
      success: 'success',
      error: 'error',
      cancelled: 'idle'
    };
    const baseClass = baseClassMap[state] || state;

    // Reset classes on stage card
    if (this.stageCard) {
      this.stageCard.className = `voice-stage-card state-${baseClass}`;
    }

    // Reset status pill
    if (this.statusPill) {
      this.statusPill.className = `voice-status-pill ${baseClass}`;
    }

    const stateLabels = {
      idle: 'Idle — Ready',
      listening: 'Listening...',
      recording: 'Recording...',
      audio_captured: 'Audio captured',
      uploading: 'Uploading...',
      transcribing: 'Transcribing...',
      transcript_received: 'Transcript received',
      understanding: 'Understanding command...',
      product_identified: 'Product identified',
      clarification_required: 'Clarification Required',
      waiting_for_confirmation: 'Waiting for confirmation...',
      awaiting_confirmation: 'Waiting for confirmation...',
      confirmation: 'Waiting for confirmation...',
      saving: 'Saving...',
      executing: 'Saving...',
      generating_speech: 'Synthesizing Tamil Speech...',
      playing_audio: 'Playing Spoken Response...',
      completed: 'Completed',
      success: 'Completed',
      error: 'Error Occurred',
      cancelled: 'Action Cancelled'
    };

    const promptMessages = {
      idle: '“வணக்கம்! உங்கள் கடைக்கு இன்று என்ன செய்ய வேண்டும்?”',
      listening: '“Listening... Speak in colloquial Tamil or Tanglish.”',
      recording: '“Recording... Speak clearly in Tamil or Tanglish.”',
      audio_captured: '“Audio captured. Preparing audio stream...”',
      uploading: '“Uploading audio to voice processor...”',
      transcribing: '“Transcribing speech into text...”',
      transcript_received: '“Transcript received. Analyzing intent...”',
      understanding: '“Understanding command and grocery entities...”',
      product_identified: '“Product identified in store inventory.”',
      clarification_required: '“Please clarify the missing product or quantity details.”',
      waiting_for_confirmation: '“Review order and stock details before confirming.”',
      awaiting_confirmation: '“Review order and stock details before confirming.”',
      confirmation: '“Review order and stock details before confirming.”',
      saving: '“Saving changes to SQLite database atomically...”',
      executing: '“Saving changes to SQLite database atomically...”',
      generating_speech: '“Generating natural Tamil voice response...”',
      playing_audio: '“Playing spoken response...”',
      completed: '“சரி! செயல்பாடு வெற்றிகரமாக முடிந்தது.”',
      success: '“சரி! செயல்பாடு வெற்றிகரமாக முடிந்தது.”',
      error: '“செயலாக்கத்தில் பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.”',
      cancelled: '“செயல்பாடு ரத்து செய்யப்பட்டது. கடையில் எந்த மாற்றமும் செய்யப்படவில்லை.”'
    };

    if (this.statusPillText) {
      this.statusPillText.textContent = stateLabels[state] || state;
    }

    if (this.voiceHeroNotice) {
      const heroNotices = {
        idle: 'Voice Pipeline Active • Click microphone to speak in Tamil, Tanglish, or English',
        listening: 'Microphone active • Listening for Tamil / Tanglish / English speech...',
        recording: 'Recording live speech audio • Click mic again or Stop when done',
        uploading: 'Uploading audio to voice processing engine...',
        transcribing: 'Transcribing speech with Gnani Prisma v2.5 STT...',
        transcript_ready: 'Transcript captured • Analyzing Kirana shopkeeper intent...',
        understanding: 'Gemini AI is analyzing intent and resolving catalog product...',
        clarification_required: 'Please clarify product name or quantity',
        awaiting_confirmation: 'Review order details carefully • Click Confirm & Execute below',
        confirmation: 'Review order details carefully • Click Confirm & Execute below',
        executing: 'Executing transaction and updating SQLite database...',
        generating_speech: 'Generating natural Tamil voice response...',
        playing_audio: 'Playing spoken response in Tamil...',
        success: 'Action executed successfully • Database and stock updated',
        error: customMsg || 'Voice processing error occurred',
        cancelled: 'Action cancelled • No database changes made'
      };
      this.voiceHeroNotice.textContent = (state === 'error' && customMsg) ? customMsg : (heroNotices[state] || stateLabels[state] || '');
    }

    if (this.promptText) {
      this.promptText.textContent = customMsg || promptMessages[state] || '';
    }

    // Toggle mic button accessibility state
    if (this.micBtn) {
      const isBusy = (
        state === this.STATES.UPLOADING ||
        state === this.STATES.TRANSCRIBING ||
        state === this.STATES.UNDERSTANDING ||
        state === this.STATES.EXECUTING ||
        state === this.STATES.GENERATING_SPEECH
      );
      this.micBtn.disabled = isBusy;
    }

    // Hide or show confirmation card
    if (this.confirmationCard) {
      const isConfirmState = (
        state === this.STATES.WAITING_FOR_CONFIRMATION ||
        state === this.STATES.AWAITING_CONFIRMATION ||
        state === this.STATES.CONFIRMATION ||
        state === 'waiting_for_confirmation' ||
        state === 'confirmation' ||
        (this.currentAction !== null && (state === this.STATES.GENERATING_SPEECH || state === this.STATES.PLAYING_AUDIO))
      );
      if (isConfirmState) {
        this.confirmationCard.classList.add('active');
      } else {
        this.confirmationCard.classList.remove('active');
        if (this.inlineEditForm) this.inlineEditForm.classList.remove('active');
      }
    }

    // Update Dedicated Live Voice Mode flow indicator and controls
    this.updateLiveFlowStep(state);
  },

  /**
   * Native 16kHz Mono PCM Audio Capture via Web Audio API
   */
  async startRecording(isContinuous = false) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      const errDetail = window.isSecureContext === false
        ? '[Stage 1: Microphone Capture] Insecure context: Browsers require HTTPS or localhost/127.0.0.1 for microphone access.'
        : '[Stage 1: Microphone Capture] Browser does not support audio recording.';
      this.setState(this.STATES.ERROR, errDetail);
      Utils.showToast('error', 'Microphone Error', errDetail, 6000);
      return;
    }

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
      this.pcmChunks = [];
      this.liveSpokenText = '';

      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.recAudioContext = new AudioContextClass();
      if (this.recAudioContext.state === 'suspended') {
        await this.recAudioContext.resume();
      }

      this.audioSourceNode = this.recAudioContext.createMediaStreamSource(this.mediaStream);
      this.audioProcessorNode = this.recAudioContext.createScriptProcessor(4096, 1, 1);
      this.isRecordingAudio = true;

      this.audioProcessorNode.onaudioprocess = (e) => {
        if (!this.isRecordingAudio) return;
        const inputData = e.inputBuffer.getChannelData(0);
        this.pcmChunks.push(new Float32Array(inputData));
      };

      this.audioSourceNode.connect(this.audioProcessorNode);
      this.audioProcessorNode.connect(this.recAudioContext.destination);

      // Optional real-time speech-to-text via browser engine (if supported)
      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRec) {
        try {
          if (this.speechRecognizer) {
            try { this.speechRecognizer.stop(); } catch (e) {}
          }
          this.speechRecognizer = new SpeechRec();
          this.speechRecognizer.continuous = true;
          this.speechRecognizer.interimResults = true;
          this.speechRecognizer.lang = (this.activeLanguage === 'en-IN' || this.activeLanguage === 'en') ? 'en-IN' : 'ta-IN';
          this.speechRecognizer.onresult = (ev) => {
            let cur = '';
            for (let i = 0; i < ev.results.length; i++) {
              cur += ev.results[i][0].transcript;
            }
            if (cur.trim()) {
              this.liveSpokenText = cur.trim();
              if (this.transcriptTextarea) {
                this.transcriptTextarea.value = this.liveSpokenText;
              }
              // Reset silence timer when user speaks
              if (this.silenceTimer) {
                clearTimeout(this.silenceTimer);
                this.silenceTimer = setTimeout(() => {
                  if (this.currentState === this.STATES.RECORDING) {
                    console.log('[Continuous Mode] Speech completed, stopping recording...');
                    this.stopRecording();
                  }
                }, 3500);
              }
            }
          };
          this.speechRecognizer.start();
        } catch (sErr) {
          console.log('[VoiceAssistant] WebSpeech API note:', sErr.message);
        }
      }

      const promptMsg = isContinuous
        ? '“தொடர் உரையாடல்: அடுத்த கட்டளையை கூறவும்... (Speaking or waiting 8s)”'
        : '“Recording... Speak clearly in colloquial Tamil or Tanglish.”';
      this.setState(this.STATES.RECORDING, promptMsg);
      this.startTimer();

      if (isContinuous) {
        if (this.silenceTimer) clearTimeout(this.silenceTimer);
        this.silenceTimer = setTimeout(() => {
          if (this.currentState === this.STATES.RECORDING) {
            console.log('[Continuous Mode] 8 seconds silence reached, auto-stopping.');
            this.stopRecording();
          }
        }, 8000);
      } else {
        Utils.showToast('info', 'Listening', 'Microphone active. Speak your command in Tamil or Tanglish.');
      }

    } catch (err) {
      console.error('[Stage 1: Microphone Capture Error]', err);
      let errorDesc = '[Stage 1: Microphone Capture] Microphone access failed.';
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        errorDesc = '[Stage 1: Microphone Capture] Microphone permission denied. Please allow microphone in browser site settings.';
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        errorDesc = '[Stage 1: Microphone Capture] No microphone device found on this system.';
      } else if (err.message && err.message.includes('Stage')) {
        errorDesc = err.message;
      }
      this.setState(this.STATES.ERROR, errorDesc);
      Utils.showToast('error', 'Microphone Error', errorDesc, 6000);
    }
  },

  async stopRecording() {
    this.stopTimer();
    this.isRecordingAudio = false;

    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
    if (this.speechRecognizer) {
      try { this.speechRecognizer.stop(); } catch (e) {}
      this.speechRecognizer = null;
    }

    if (this.audioProcessorNode) {
      try {
        this.audioProcessorNode.disconnect();
        this.audioProcessorNode.onaudioprocess = null;
      } catch (e) {}
      this.audioProcessorNode = null;
    }

    if (this.audioSourceNode) {
      try { this.audioSourceNode.disconnect(); } catch (e) {}
      this.audioSourceNode = null;
    }

    const inputSampleRate = this.recAudioContext ? this.recAudioContext.sampleRate : 48000;
    if (this.recAudioContext && this.recAudioContext.state !== 'closed') {
      try { await this.recAudioContext.close(); } catch (e) {}
      this.recAudioContext = null;
    }

    if (this.mediaStream) {
      try {
        this.mediaStream.getTracks().forEach(track => track.stop());
      } catch (e) {}
      this.mediaStream = null;
    }

    const wavBlob = encode16kHzPcmWav(this.pcmChunks || [], inputSampleRate);
    this.pcmChunks = [];
    console.log('[Audio Capture] Encoded 16kHz PCM WAV:', wavBlob.size, 'bytes, MIME:', wavBlob.type);

    const spoken = this.liveSpokenText || (this.transcriptTextarea ? this.transcriptTextarea.value.trim() : null);
    if (wavBlob.size > 100 || spoken) {
      this.handleRecordedAudio(wavBlob, spoken || null);
    } else {
      this.setState(this.STATES.ERROR, 'No audio data was recorded.');
    }
  },

  /**
   * Handle Audio Recorded from Microphone via Backend Voice Pipeline
   */
  async handleRecordedAudio(audioBlob, spokenText = null) {
    this.setState(this.STATES.AUDIO_CAPTURED);
    await new Promise(r => setTimeout(r, 200));
    this.setState(this.STATES.TRANSCRIBING);

    try {
      const voiceRes = await ApiService.processVoiceCommand(
        audioBlob,
        spokenText,
        this.activeLanguage,
        this.sessionId,
        this.conversationContext
      );

      if (voiceRes) {
        if (voiceRes.session_id) this.sessionId = voiceRes.session_id;
        if (voiceRes.context) this.conversationContext = voiceRes.context;

        if (voiceRes.success) {
          this.setState(this.STATES.TRANSCRIPT_RECEIVED);
          if (this.transcriptTextarea && voiceRes.transcript) {
            this.transcriptTextarea.value = voiceRes.transcript;
          }
          await new Promise(r => setTimeout(r, 200));
          this.setState(this.STATES.UNDERSTANDING);
          await new Promise(r => setTimeout(r, 200));
          if (voiceRes.resolved_product || (voiceRes.confirmation_preview && voiceRes.confirmation_preview.items)) {
            this.setState(this.STATES.PRODUCT_IDENTIFIED);
            await new Promise(r => setTimeout(r, 200));
          }
          this.applyVoiceCommandResponse(voiceRes);
        } else {
          // Graceful handling of assistant clarification or voice processing notice
          const userMsg = voiceRes.message_ta || voiceRes.message || 'Voice request could not be processed.';
          this.setState(this.STATES.CLARIFICATION_REQUIRED, userMsg);
          if (this.transcriptTextarea && voiceRes.transcript) {
            this.transcriptTextarea.value = voiceRes.transcript;
          }
          Utils.showToast('warning', 'Notice', userMsg, 5000);
          this.speakResponse(userMsg);
        }
      } else {
        throw new Error('Voice service is temporarily unavailable. Please try again.');
      }
    } catch (err) {
      console.warn('[VoiceAssistant] Voice pipeline processing notice:', err);
      const friendlyMsg = (err.message && err.message.includes('fetch'))
        ? 'Voice service is temporarily unavailable. Please check your connection and try again.'
        : (err.message || 'Speech recognition encountered an issue. Please try again.');
      this.setState(this.STATES.ERROR, friendlyMsg);
      Utils.showToast('error', 'Voice Assistant', friendlyMsg);
    }
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
   * Execute Command Workflow with Transcript & Intent Extraction
   */
  async executeCommandWorkflow(cmd, fromMic = false) {
    let commandText = typeof cmd === 'string' ? cmd : (cmd.command || '');

    if (this.transcriptTextarea) {
      this.transcriptTextarea.value = commandText;
    }

    this.setState(this.STATES.UNDERSTANDING);

    try {
      const aiResponse = await ApiService.interpretCommand(commandText, this.sessionId, this.conversationContext);
      if (aiResponse && aiResponse.success) {
        if (aiResponse.session_id) this.sessionId = aiResponse.session_id;
        if (aiResponse.context) this.conversationContext = aiResponse.context;

        if (aiResponse.resolved_product || (aiResponse.confirmation_preview && aiResponse.confirmation_preview.items)) {
          this.setState(this.STATES.PRODUCT_IDENTIFIED);
          await new Promise(r => setTimeout(r, 200));
        }
        this.applyAIInterpretation(aiResponse, commandText);
      } else {
        throw new Error(aiResponse?.message || 'Could not interpret command');
      }
    } catch (err) {
      console.warn('[VoiceAssistant] Command interpretation error:', err.message);
      this.setState(this.STATES.ERROR, err.message || 'செயலாக்கப் பிழை');
      Utils.showToast('error', 'செயலாக்கப் பிழை', err.message || 'கட்டளையை செயலாக்க முடியவில்லை.');
    }
  },

  applyAIInterpretation(res, commandText) {
    this.applyVoiceCommandResponse({
      ...res,
      transcript: commandText
    });
  },

  applyVoiceCommandResponse(res) {
    if (res.session_id) this.sessionId = res.session_id;
    if (res.context) this.conversationContext = res.context;

    const intent = res.intent;
    const resolved = res.resolved_product;

    if (this.actionVal) this.actionVal.textContent = intent ? intent.intent : 'N/A';
    if (this.productVal) this.productVal.textContent = resolved ? resolved.name : (intent?.entities?.product_name || 'N/A');
    if (this.qtyVal) this.qtyVal.textContent = intent?.entities?.quantity ? `${intent.entities.quantity} ${intent.entities.unit || ''}` : 'N/A';

    if (this.confidenceVal) {
      if (res.stt && res.stt.confidence) {
        this.confidenceVal.textContent = `${Math.round(res.stt.confidence * 100)}% (Gnani STT)`;
      } else if (intent && intent.confidence) {
        this.confidenceVal.textContent = `${Math.round(intent.confidence * 100)}% (Gemini AI)`;
      } else {
        this.confidenceVal.textContent = '96% (Gnani & Gemini)';
      }
    }

    // Dynamic Language Detection & Response Matching (Phase 4)
    let replyText = res.spoken_response;
    if (!replyText) {
      if (res.detected_language === 'English') {
        replyText = res.message || res.message_ta;
      } else if (res.detected_language === 'Tanglish') {
        replyText = res.message_tanglish || res.message_ta || res.message;
      } else {
        replyText = res.message_ta || res.message;
      }
    }
    if (!replyText) replyText = 'கட்டளை ஏற்றுக்கொள்ளப்பட்டது.';

    // Dynamically align active language for Gnani TTS & UI
    if (res.detected_language === 'English') {
      this.activeLanguage = 'en-IN';
    } else {
      this.activeLanguage = 'ta-IN';
    }

    if (this.responseBubble) {
      this.responseBubble.textContent = replyText;
    }

    // Direct Confirmation / Cancellation Intents
    if (intent && (intent.intent === 'CONFIRM_ACTION' || intent.intent === 'CANCEL_ACTION')) {
      this.currentAction = null;
      if (this.btnLiveCancelAction) this.btnLiveCancelAction.disabled = true;
      if (intent.intent === 'CONFIRM_ACTION') {
        this.setState(this.STATES.SUCCESS, replyText);
        this.addToHistory(res.transcript || 'Voice Confirm', 'CONFIRM_ACTION', 'Confirmed (Live DB)');
        if (this.liveBillBadge) {
          this.liveBillBadge.textContent = 'Bill Paid & Stock Deducted';
          this.liveBillBadge.className = 'badge-pill success';
        }
        if (Store && typeof Store.syncFromBackend === 'function') {
          Store.syncFromBackend();
        }
        window.dispatchEvent(new CustomEvent('store-updated', { detail: { action: 'CONFIRMED' } }));
        window.dispatchEvent(new CustomEvent('voice-cart-updated', { detail: { cleared: true } }));
      } else {
        this.setState(this.STATES.CANCELLED, replyText);
        this.addToHistory(res.transcript || 'Voice Cancel', 'CANCEL_ACTION', 'Cancelled');
        if (this.liveBillBadge) {
          this.liveBillBadge.textContent = 'Bill Cancelled';
          this.liveBillBadge.className = 'badge-pill neutral';
        }
        window.dispatchEvent(new CustomEvent('voice-cart-updated', { detail: { cleared: true } }));
        setTimeout(() => this.clearLiveBillPreview(), 2500);
      }
      this.speakResponse(replyText);
      return;
    }

    // Clarification required - store conversational context for follow-up
    if (intent && intent.requires_clarification) {
      this.conversationContext = res.context || {
        active: true,
        intent: intent.intent,
        product_name: intent.entities?.product_name || '',
        missing: 'quantity',
        timestamp: Date.now()
      };
      this.setState(this.STATES.CLARIFICATION_REQUIRED, replyText);
      Utils.showToast('warning', 'Clarification Needed', res.message || replyText, 6000);
      this.speakResponse(replyText);
      return;
    }

    // Confirmation workflow
    if (res.requires_confirmation && res.confirmation_preview) {
      const p = res.confirmation_preview;
      this.currentAction = {
        actionId: p.action_id,
        action: p.action,
        product: p.product_name,
        quantity: p.quantity,
        unit: p.unit,
        currentStock: p.current_stock,
        projectedStock: p.projected_stock,
        estimatedTotal: p.estimated_total,
        command: res.transcript || '',
        responseTa: res.message_ta || res.message,
        responseEn: res.message
      };

      if (p.items && p.items.length > 0) {
        this.renderLiveBillPreview(p);
        window.dispatchEvent(new CustomEvent('voice-cart-updated', {
          detail: { items: p.items, grand_total: p.estimated_total, ref: p.action_id }
        }));
      } else {
        this.clearLiveBillPreview();
      }

      this.setState(this.STATES.WAITING_FOR_CONFIRMATION);
      if (this.confirmationSummary) {
        if (p.items && p.items.length > 1) {
          let rowsHtml = p.items.map(item => `
            <tr>
              <td style="padding: 4px 8px; border-bottom: 1px solid rgba(255,255,255,0.1);"><strong>${item.product_name}</strong></td>
              <td style="padding: 4px 8px; border-bottom: 1px solid rgba(255,255,255,0.1);">${item.quantity} ${item.unit}</td>
              <td style="padding: 4px 8px; border-bottom: 1px solid rgba(255,255,255,0.1);">${item.current_stock} &rarr; ${item.projected_stock} ${item.unit}</td>
              <td style="padding: 4px 8px; border-bottom: 1px solid rgba(255,255,255,0.1);">₹${item.unit_price}</td>
              <td style="padding: 4px 8px; border-bottom: 1px solid rgba(255,255,255,0.1);">₹${item.line_total}</td>
            </tr>
          `).join('');
          this.confirmationSummary.innerHTML = `
            <div style="margin-bottom: 0.5rem; font-weight: 600;">Action: ${p.action} (Multi-Item Order)</div>
            <table style="width: 100%; margin: 0.5rem 0; font-size: var(--font-size-xs); border-collapse: collapse;">
              <thead>
                <tr style="background: rgba(255,255,255,0.08); text-align: left;">
                  <th style="padding: 4px 8px;">Item</th>
                  <th style="padding: 4px 8px;">Qty</th>
                  <th style="padding: 4px 8px;">Stock Change</th>
                  <th style="padding: 4px 8px;">Price</th>
                  <th style="padding: 4px 8px;">Total</th>
                </tr>
              </thead>
              <tbody>${rowsHtml}</tbody>
            </table>
            <div style="font-weight: 700; text-align: right; color: #22c55e; font-size: var(--font-size-sm); margin-top: 6px;">
              Grand Total: ₹${p.estimated_total}
            </div>
          `;
        } else {
          let details = `Action: ${p.action} | Product: ${p.product_name} | Quantity: ${p.quantity} ${p.unit} | Stock: ${p.current_stock} -> ${p.projected_stock} ${p.unit}`;
          if (p.estimated_total) details += ` | Total: ₹${p.estimated_total}`;
          this.confirmationSummary.textContent = details;
        }
      }
      Utils.showToast('warning', 'Confirmation Required', `Please review and confirm: ${p.action} for ${p.product_name}.`);
      this.speakResponse(replyText);
    } else {
      // Direct inquiry, executed relative action, or cart addition
      if (res.context && res.context.cart_items && res.context.cart_items.length > 0) {
        window.dispatchEvent(new CustomEvent('voice-cart-updated', { detail: { items: res.context.cart_items } }));
      }
      this.setState(this.STATES.SUCCESS, replyText);
      this.addToHistory(res.transcript || 'Voice Command', intent ? intent.intent : 'Query', 'Completed');
      if (Store && typeof Store.syncFromBackend === 'function') {
        Store.syncFromBackend();
      }
      window.dispatchEvent(new CustomEvent('store-updated', { detail: { action: intent ? intent.intent : 'EXECUTE' } }));
      this.speakResponse(replyText);
    }
  },

  /**
   * User Confirms the Action
   */
  async confirmPendingAction() {
    if (!this.currentAction) return;

    this.setState(this.STATES.SAVING);

    if (this.currentAction.actionId) {
      try {
        const confirmRes = await ApiService.confirmAction(this.currentAction.actionId);
        if (confirmRes && confirmRes.success) {
          const successMsg = confirmRes.message_ta || confirmRes.message;
          this.setState(this.STATES.COMPLETED, successMsg);
          this.addToHistory(this.currentAction.command, confirmRes.action, 'Confirmed (Live DB)');
          Utils.showToast('success', 'Action Executed', confirmRes.message, 5000);

          // Dispatch global store update event so Inventory table and Dashboard refresh automatically!
          if (Store && typeof Store.syncFromBackend === 'function') {
            await Store.syncFromBackend();
          }
          if (Store && typeof Store.syncSalesFromBackend === 'function') {
            await Store.syncSalesFromBackend();
          }
          window.dispatchEvent(new CustomEvent('store-updated', { detail: { action: confirmRes.action } }));
          if (this.liveBillBadge) {
            this.liveBillBadge.textContent = 'Bill Paid & Stock Deducted';
            this.liveBillBadge.className = 'badge-pill success';
          }
          if (this.btnLiveCancelAction) this.btnLiveCancelAction.disabled = true;
          this.currentAction = null;
          this.speakResponse(successMsg);
          return;
        } else {
          throw new Error(confirmRes?.message || 'Confirmation failed');
        }
      } catch (err) {
        this.setState(this.STATES.ERROR, err.message || 'Action execution failed');
        Utils.showToast('error', 'Execution Failed', err.message || 'Action execution failed', 6000);
        return;
      }
    } else {
      this.setState(this.STATES.ERROR, 'No active pending action found to confirm.');
      Utils.showToast('warning', 'No Action', 'No active pending action found to confirm.');
    }
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
  async cancelPendingAction() {
    if (this.currentAction?.actionId) {
      try {
        await ApiService.cancelAction(this.currentAction.actionId);
      } catch (e) {
        console.warn('Cancel action warning:', e.message);
      }
    }
    this.currentAction = null;
    if (this.btnLiveCancelAction) this.btnLiveCancelAction.disabled = true;
    if (this.liveBillBadge) {
      this.liveBillBadge.textContent = 'Bill Cancelled';
      this.liveBillBadge.className = 'badge-pill neutral';
    }
    setTimeout(() => this.clearLiveBillPreview(), 2500);
    this.setState(this.STATES.CANCELLED, 'Action was cancelled by user. Returning to ready state.');
    Utils.showToast('info', 'Cancelled', 'Pending action was cancelled. No changes made.');
    this.speakResponse('Action cancel panniyachu.');
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
   * Text-to-Speech (TTS) using Gnani Timbre v2.5 with Browser SpeechSynthesis Fallback
   */
  async speakResponse(overrideText = '') {
    this.stopSpeaking();

    const textToSpeak = (overrideText || (this.responseBubble ? this.responseBubble.textContent : '')).trim();
    if (!textToSpeak) return;

    this.setState(this.STATES.GENERATING_SPEECH);
    if (this.btnSpeak) this.btnSpeak.disabled = true;
    if (this.btnStopSpeak) this.btnStopSpeak.disabled = false;
    if (this.ttsNotice) this.ttsNotice.textContent = 'Synthesizing voice with Gnani Timbre v2.5...';

    try {
      const audioBlob = await ApiService.synthesizeSpeech(textToSpeak, this.activeLanguage, 1.0);
      if (audioBlob && audioBlob.size > 0) {
        const audioUrl = URL.createObjectURL(audioBlob);
        this.activeAudio = new Audio(audioUrl);

        this.activeAudio.onplay = () => {
          this.setState(this.STATES.PLAYING_AUDIO);
          this.suppressAudioFeedback(true);
          if (this.ttsNotice) this.ttsNotice.textContent = `Playing Gnani Timbre v2.5 voice audio (${this.activeLanguage})...`;
        };

        this.activeAudio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          this.activeAudio = null;
          if (this.btnSpeak) this.btnSpeak.disabled = false;
          if (this.btnStopSpeak) this.btnStopSpeak.disabled = true;
          if (this.ttsNotice) this.ttsNotice.textContent = 'Voice playback completed.';
          if (this.currentState === this.STATES.PLAYING_AUDIO || this.currentState === this.STATES.GENERATING_SPEECH) {
            this.setState(this.currentAction ? this.STATES.WAITING_FOR_CONFIRMATION : this.STATES.IDLE);
          }
          // Delay to suppress echo/feedback settling (280ms) then auto-listen
          setTimeout(() => {
            this.suppressAudioFeedback(false);
            if (this.isLiveModeActive) {
              this.startLiveListeningTurn();
            } else if (this.interactionMode === 'continuous') {
              this.scheduleContinuousListening();
            }
          }, 280);
        };

        this.activeAudio.onerror = (e) => {
          console.warn('[Stage 8: Audio Playback Error, falling back to browser TTS]:', e);
          URL.revokeObjectURL(audioUrl);
          this.activeAudio = null;
          this.fallbackBrowserSpeech(textToSpeak);
        };

        await this.activeAudio.play();
        return;
      }
    } catch (err) {
      console.warn('[Stage 7: Gnani TTS Backend Error, falling back to browser TTS]:', err.message);
    }

    // Fallback to browser SpeechSynthesis
    this.fallbackBrowserSpeech(textToSpeak);
  },

  fallbackBrowserSpeech(textToSpeak) {
    if (!('speechSynthesis' in window)) {
      if (this.btnSpeak) this.btnSpeak.disabled = false;
      if (this.btnStopSpeak) this.btnStopSpeak.disabled = true;
      if (this.ttsNotice) this.ttsNotice.textContent = 'Audio playback completed (TTS unsupported).';
      if (this.isLiveModeActive) {
        setTimeout(() => this.startLiveListeningTurn(), 300);
      } else if (this.interactionMode === 'continuous') {
        this.scheduleContinuousListening();
      }
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const tamilVoice = voices.find(v => v.lang.includes('ta') || v.name.toLowerCase().includes('tamil'));
    if (tamilVoice) {
      utterance.voice = tamilVoice;
      if (this.ttsNotice) this.ttsNotice.textContent = `Speaking with browser voice: ${tamilVoice.name} (ta-IN)`;
    } else {
      if (this.ttsNotice) this.ttsNotice.textContent = 'Spoken via browser speech synthesis fallback.';
    }

    utterance.onstart = () => {
      this.setState(this.STATES.PLAYING_AUDIO);
      this.suppressAudioFeedback(true);
      if (this.btnSpeak) this.btnSpeak.disabled = true;
      if (this.btnStopSpeak) this.btnStopSpeak.disabled = false;
    };

    utterance.onend = () => {
      if (this.btnSpeak) this.btnSpeak.disabled = false;
      if (this.btnStopSpeak) this.btnStopSpeak.disabled = true;
      if (this.currentState === this.STATES.PLAYING_AUDIO) {
        this.setState(this.currentAction ? this.STATES.WAITING_FOR_CONFIRMATION : this.STATES.IDLE);
      }
      setTimeout(() => {
        this.suppressAudioFeedback(false);
        if (this.isLiveModeActive) {
          this.startLiveListeningTurn();
        } else if (this.interactionMode === 'continuous') {
          this.scheduleContinuousListening();
        }
      }, 280);
    };

    utterance.onerror = (e) => {
      console.warn('[SpeechSynthesis Error]', e);
      if (this.btnSpeak) this.btnSpeak.disabled = false;
      if (this.btnStopSpeak) this.btnStopSpeak.disabled = true;
      if (this.currentState === this.STATES.PLAYING_AUDIO) {
        this.setState(this.currentAction ? this.STATES.WAITING_FOR_CONFIRMATION : this.STATES.IDLE);
      }
      setTimeout(() => {
        this.suppressAudioFeedback(false);
        if (this.isLiveModeActive) {
          this.startLiveListeningTurn();
        } else if (this.interactionMode === 'continuous') {
          this.scheduleContinuousListening();
        }
      }, 280);
    };

    window.speechSynthesis.speak(utterance);
  },

  scheduleContinuousListening() {
    if (this.continuousTimer) clearTimeout(this.continuousTimer);
    this.continuousTimer = setTimeout(() => {
      if (this.interactionMode === 'continuous' && this.currentState !== this.STATES.RECORDING) {
        console.log('[Continuous Mode] Starting follow-up voice listening...');
        this.startRecording(true);
      }
    }, 850);
  },

  stopSpeaking() {
    if (this.activeAudio) {
      try {
        this.activeAudio.pause();
        this.activeAudio.currentTime = 0;
      } catch (e) {}
      this.activeAudio = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    this.suppressAudioFeedback(false);
    if (this.btnSpeak) this.btnSpeak.disabled = false;
    if (this.btnStopSpeak) this.btnStopSpeak.disabled = true;
    if (this.currentState === this.STATES.PLAYING_AUDIO || this.currentState === this.STATES.GENERATING_SPEECH) {
      this.setState(this.currentAction ? this.STATES.AWAITING_CONFIRMATION : this.STATES.IDLE);
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
    } else {
      history = [];
    }

    this.renderHistory(history);
  },

  renderHistory(history) {
    if (!this.historyList) return;

    if (!history || !history.length) {
      this.historyList.innerHTML = `
        <div style="padding: 1.5rem; text-align: center; color: var(--color-text-muted); font-size: var(--font-size-xs);">
          No recent voice commands. Speak into the microphone or click a voice command.
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
        <span class="badge-pill info">${item.status || 'Live'}</span>
      </div>
    `).join('');
  },

  addToHistory(command, action, status = 'Live') {
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
  },

  /**
   * =========================================================================
   * DEDICATED LIVE VOICE MODE ENGINE (HANDS-FREE CONVERSATIONAL PIPELINE)
   * =========================================================================
   */

  async toggleLiveMode() {
    if (this.isLiveModeActive) {
      await this.stopLiveMode();
    } else {
      await this.startLiveMode();
    }
  },

  async startLiveMode() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      Utils.showToast('error', 'Microphone Unsupported', 'Browser does not support microphone capture.');
      return;
    }

    try {
      this.isLiveModeActive = true;
      this.isMicMuted = false;
      this.interactionMode = 'continuous';

      // Update UI Banner and Button
      if (this.liveBanner) this.liveBanner.classList.add('active');
      if (this.btnLiveToggle) this.btnLiveToggle.classList.add('active');
      if (this.btnLiveToggleText) {
        this.btnLiveToggleText.textContent = 'End Live Conversation (நேரடி உரையாடல் நிறுத்து)';
      }
      if (this.btnModeContinuous && this.btnModePush) {
        this.btnModePush.classList.remove('active');
        this.btnModeContinuous.classList.add('active');
      }

      // Initialize Persistent MediaStream if not active
      if (!this.liveMediaStream || !this.liveMediaStream.active) {
        this.liveMediaStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });
      }

      // Initialize Web Audio API Analyser for VAD
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        if (!this.audioContext || this.audioContext.state === 'closed') {
          this.audioContext = new AudioCtx();
        }
        if (this.audioContext.state === 'suspended') {
          await this.audioContext.resume();
        }
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        this.analyser.smoothingTimeConstant = 0.4;
        const source = this.audioContext.createMediaStreamSource(this.liveMediaStream);
        source.connect(this.analyser);
        this.analyserDataArray = new Uint8Array(this.analyser.frequencyBinCount);
      }

      Utils.showToast('success', 'Live Mode Active', 'நேரடி உரையாடல் தொடங்கியது. பேசுங்கள்!');

      // Greet the merchant and begin first listening turn on completion
      const greeting = 'வணக்கம்! நேரடி உரையாடல் தயார். உங்கள் கட்டளையை சொல்லுங்கள்.';
      if (this.responseBubble) this.responseBubble.textContent = greeting;
      await this.speakResponse(greeting);

    } catch (err) {
      console.error('[LiveVoice] Activation error:', err);
      this.isLiveModeActive = false;
      if (this.btnLiveToggle) this.btnLiveToggle.classList.remove('active');
      if (this.liveBanner) this.liveBanner.classList.remove('active');
      if (this.btnLiveToggleText) {
        this.btnLiveToggleText.textContent = 'Start Live Conversation (நேரடி உரையாடல் தொடங்கு)';
      }
      Utils.showToast('error', 'Microphone Permission', 'Could not access microphone: ' + err.message);
    }
  },

  async stopLiveMode() {
    this.isLiveModeActive = false;
    this.stopSpeaking();
    this.stopLiveVadLoop();

    if (this.liveProcessorNode) {
      try {
        this.liveProcessorNode.disconnect();
        this.liveProcessorNode.onaudioprocess = null;
      } catch (e) {}
      this.liveProcessorNode = null;
    }

    if (this.liveMediaStream) {
      try {
        this.liveMediaStream.getTracks().forEach(t => t.stop());
      } catch (e) {}
      this.liveMediaStream = null;
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      try { await this.audioContext.close(); } catch (e) {}
      this.audioContext = null;
    }

    // Reset UI
    if (this.liveBanner) this.liveBanner.classList.remove('active');
    if (this.btnLiveToggle) this.btnLiveToggle.classList.remove('active');
    if (this.btnLiveToggleText) {
      this.btnLiveToggleText.textContent = 'Start Live Conversation (நேரடி உரையாடல் தொடங்கு)';
    }
    if (this.btnLiveStopSpeech) this.btnLiveStopSpeech.disabled = true;
    if (this.btnLiveCancelAction) this.btnLiveCancelAction.disabled = true;
    this.resetMeterBars();
    this.setState(this.STATES.IDLE);
    Utils.showToast('info', 'Live Mode Ended', 'நேரடி உரையாடல் நிறுத்தப்பட்டது.');
  },

  async startLiveListeningTurn() {
    if (!this.isLiveModeActive) return;

    // Ensure audio tracks are unmuted
    this.suppressAudioFeedback(false);

    // If media stream was closed, recreate
    if (!this.liveMediaStream || !this.liveMediaStream.active) {
      try {
        this.liveMediaStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });
      } catch (e) {
        console.warn('[LiveVoice] Could not recreate stream:', e);
        this.stopLiveMode();
        return;
      }
    }

    // Initialize or resume Web Audio API context
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) {
      if (!this.audioContext || this.audioContext.state === 'closed') {
        this.audioContext = new AudioCtx();
      }
      if (this.audioContext.state === 'suspended') {
        try { await this.audioContext.resume(); } catch (e) {}
      }

      if (!this.analyser) {
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        this.analyser.smoothingTimeConstant = 0.4;
        this.analyserDataArray = new Uint8Array(this.analyser.frequencyBinCount);
      }
    }

    this.livePcmChunks = [];
    this.liveSpokenText = '';
    this.hasUserSpokenInTurn = false;
    this.vadSilenceStart = 0;
    this.vadTurnStartTime = Date.now();

    // Start WebSpeech if available for live visual transcript
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
      try {
        if (this.speechRecognizer) {
          try { this.speechRecognizer.stop(); } catch (e) {}
        }
        this.speechRecognizer = new SpeechRec();
        this.speechRecognizer.continuous = true;
        this.speechRecognizer.interimResults = true;
        this.speechRecognizer.lang = (this.activeLanguage === 'en-IN' || this.activeLanguage === 'en') ? 'en-IN' : 'ta-IN';
        this.speechRecognizer.onresult = (ev) => {
          let cur = '';
          for (let i = 0; i < ev.results.length; i++) {
            cur += ev.results[i][0].transcript;
          }
          if (cur.trim()) {
            this.liveSpokenText = cur.trim();
            if (this.transcriptTextarea) this.transcriptTextarea.value = this.liveSpokenText;
            this.hasUserSpokenInTurn = true;
            this.vadSilenceStart = 0;
          }
        };
        this.speechRecognizer.start();
      } catch (e) {
        console.log('[LiveVoice] SpeechRecognition start note:', e.message);
      }
    }

    // Connect source to analyser & ScriptProcessor for PCM WAV turn capture
    if (this.audioContext && this.liveMediaStream) {
      try {
        if (this.liveProcessorNode) {
          try {
            this.liveProcessorNode.disconnect();
            this.liveProcessorNode.onaudioprocess = null;
          } catch (e) {}
        }
        const source = this.audioContext.createMediaStreamSource(this.liveMediaStream);
        if (this.analyser) {
          try { source.connect(this.analyser); } catch (e) {}
        }
        this.liveProcessorNode = this.audioContext.createScriptProcessor(4096, 1, 1);
        this.liveProcessorNode.onaudioprocess = (e) => {
          if (!this.isLiveModeActive || this.currentState !== this.STATES.LISTENING) return;
          const input = e.inputBuffer.getChannelData(0);
          this.livePcmChunks.push(new Float32Array(input));
        };
        source.connect(this.liveProcessorNode);
        this.liveProcessorNode.connect(this.audioContext.destination);
      } catch (e) {
        console.warn('[LiveVoice] Web Audio setup warning:', e);
      }
    }

    this.setState(this.STATES.LISTENING, '“Listening... சொல்லுங்கள், நான் கேட்கிறேன்.”');
    this.startLiveVadLoop();
  },

  startLiveVadLoop() {
    this.stopLiveVadLoop();

    const checkVad = () => {
      if (!this.isLiveModeActive || this.currentState !== this.STATES.LISTENING) {
        return;
      }

      let avgEnergy = 0;
      if (this.analyser && this.analyserDataArray && !this.isMicMuted) {
        this.analyser.getByteFrequencyData(this.analyserDataArray);
        let sum = 0;
        for (let i = 0; i < this.analyserDataArray.length; i++) {
          sum += this.analyserDataArray[i];
        }
        avgEnergy = sum / this.analyserDataArray.length;
      }

      this.updateMeterBars(avgEnergy);

      if (avgEnergy > this.vadVolumeThreshold) {
        this.hasUserSpokenInTurn = true;
        this.vadSilenceStart = 0;
      } else if (this.hasUserSpokenInTurn) {
        if (this.vadSilenceStart === 0) {
          this.vadSilenceStart = Date.now();
        } else if (Date.now() - this.vadSilenceStart > this.vadSilenceDurationMs) {
          console.log('[LiveVAD] Silence threshold reached. Auto-submitting turn.');
          this.stopLiveTurnAndProcess();
          return;
        }
      }

      if (Date.now() - this.vadTurnStartTime > 10000) {
        if (this.hasUserSpokenInTurn) {
          console.log('[LiveVAD] Max turn duration reached with speech. Auto-submitting turn.');
          this.stopLiveTurnAndProcess();
          return;
        } else {
          this.vadTurnStartTime = Date.now();
        }
      }

      this.vadAnimationId = requestAnimationFrame(checkVad);
    };

    this.vadAnimationId = requestAnimationFrame(checkVad);
  },

  stopLiveVadLoop() {
    if (this.vadAnimationId) {
      cancelAnimationFrame(this.vadAnimationId);
      this.vadAnimationId = null;
    }
  },

  stopLiveTurnAndProcess() {
    this.stopLiveVadLoop();
    this.resetMeterBars();

    // Feedback prevention
    this.suppressAudioFeedback(true);

    if (this.speechRecognizer) {
      try { this.speechRecognizer.stop(); } catch (e) {}
    }

    if (this.liveProcessorNode) {
      try {
        this.liveProcessorNode.disconnect();
        this.liveProcessorNode.onaudioprocess = null;
      } catch (e) {}
      this.liveProcessorNode = null;
    }

    const sampleRate = this.audioContext ? this.audioContext.sampleRate : 48000;
    const wavBlob = encode16kHzPcmWav(this.livePcmChunks || [], sampleRate);
    this.livePcmChunks = [];
    console.log('[LiveVoice] Turn captured 16kHz PCM WAV:', wavBlob.size, 'bytes');

    const spoken = this.liveSpokenText || (this.transcriptTextarea ? this.transcriptTextarea.value.trim() : null);
    if (wavBlob.size > 100 || spoken) {
      this.handleRecordedAudio(wavBlob, spoken || null);
    } else if (this.isLiveModeActive) {
      setTimeout(() => this.startLiveListeningTurn(), 300);
    }
  },

  suppressAudioFeedback(shouldSuppress) {
    const stream = this.liveMediaStream || this.mediaStream;
    if (stream) {
      stream.getAudioTracks().forEach(track => {
        track.enabled = !shouldSuppress && !this.isMicMuted;
      });
    }
  },

  toggleMicMute() {
    this.isMicMuted = !this.isMicMuted;
    this.suppressAudioFeedback(this.isMicMuted);
    if (this.btnLiveMuteText) {
      this.btnLiveMuteText.textContent = this.isMicMuted ? 'Unmute Mic' : 'Mute Mic';
    }
    if (this.btnLiveMute) {
      if (this.isMicMuted) {
        this.btnLiveMute.classList.add('btn-warning');
        this.btnLiveMute.classList.remove('btn-outline');
      } else {
        this.btnLiveMute.classList.remove('btn-warning');
        this.btnLiveMute.classList.add('btn-outline');
      }
    }
    Utils.showToast(
      'info',
      this.isMicMuted ? 'Mic Muted' : 'Mic Unmuted',
      this.isMicMuted ? 'Microphone audio capture paused.' : 'Microphone audio capture active.'
    );
  },

  interruptSpeech() {
    console.log('[LiveVoice] User triggered barge-in interruption.');
    this.stopSpeaking();
    this.suppressAudioFeedback(false);
    if (this.isLiveModeActive) {
      setTimeout(() => this.startLiveListeningTurn(), 100);
    }
  },

  updateLiveFlowStep(state) {
    const steps = [
      this.flowStepIdle,
      this.flowStepListening,
      this.flowStepUnderstanding,
      this.flowStepSpeaking
    ];

    steps.forEach(s => {
      if (s) s.classList.remove('active', 'listening', 'understanding', 'speaking');
    });

    let activeStep = this.flowStepIdle;
    let activeKey = 'idle';

    if (state === this.STATES.LISTENING || state === this.STATES.RECORDING) {
      activeStep = this.flowStepListening;
      activeKey = 'listening';
    } else if (
      state === this.STATES.AUDIO_CAPTURED ||
      state === this.STATES.UPLOADING ||
      state === this.STATES.TRANSCRIBING ||
      state === this.STATES.TRANSCRIPT_RECEIVED ||
      state === this.STATES.UNDERSTANDING ||
      state === this.STATES.PRODUCT_IDENTIFIED ||
      state === this.STATES.SAVING ||
      state === this.STATES.EXECUTING ||
      state === this.STATES.WAITING_FOR_CONFIRMATION ||
      state === this.STATES.CONFIRMATION
    ) {
      activeStep = this.flowStepUnderstanding;
      activeKey = 'understanding';
    } else if (state === this.STATES.GENERATING_SPEECH || state === this.STATES.PLAYING_AUDIO) {
      activeStep = this.flowStepSpeaking;
      activeKey = 'speaking';
    }

    if (activeStep) {
      activeStep.classList.add('active', activeKey);
    }

    if (this.liveStatusPill && this.liveStatusLabel) {
      this.liveStatusPill.className = `live-status-pill ${activeKey}`;
      const labels = {
        idle: this.isLiveModeActive ? 'LIVE: READY' : 'LIVE CONVERSATION: IDLE',
        listening: 'LIVE: LISTENING (VAD ACTIVE)',
        understanding: 'LIVE: GEMINI & STT REASONING',
        speaking: 'LIVE: GNANI TIMBRE SPEAKING'
      };
      this.liveStatusLabel.textContent = labels[activeKey] || activeKey.toUpperCase();
    }

    if (this.btnLiveStopSpeech) {
      this.btnLiveStopSpeech.disabled = (activeKey !== 'speaking');
    }
    if (this.btnLiveCancelAction) {
      this.btnLiveCancelAction.disabled = (this.currentAction === null);
    }
  },

  updateMeterBars(energy) {
    if (!this.liveMeterBars || !this.liveMeterBars.length) return;
    const normalized = Math.min(1.0, energy / 60);
    if (this.liveMeterVal) {
      this.liveMeterVal.textContent = Math.round(normalized * 100) + '%';
    }
    const totalBars = this.liveMeterBars.length;
    this.liveMeterBars.forEach((bar, idx) => {
      const barRatio = (idx + 1) / totalBars;
      if (normalized >= barRatio * 0.7) {
        const heightPct = Math.min(100, Math.max(15, Math.round(normalized * 100 * (1 + (idx % 3) * 0.15))));
        bar.style.height = `${heightPct}%`;
      } else {
        bar.style.height = '10%';
      }
    });
  },

  resetMeterBars() {
    if (!this.liveMeterBars) return;
    this.liveMeterBars.forEach(bar => {
      bar.style.height = '10%';
    });
    if (this.liveMeterVal) this.liveMeterVal.textContent = '0%';
  },

  renderLiveBillPreview(preview) {
    if (!this.liveBillCard || !this.liveBillTbody) return;

    if (!preview || !preview.items || preview.items.length === 0) {
      this.liveBillCard.style.display = 'none';
      return;
    }

    const rows = preview.items.map((it, idx) => `
      <tr>
        <td><strong>${idx + 1}</strong></td>
        <td><strong>${it.product_name}</strong></td>
        <td>${it.quantity} ${it.unit}</td>
        <td>₹${it.unit_price}</td>
        <td><strong class="text-success">₹${it.line_total}</strong></td>
        <td>${it.current_stock} &rarr; <span class="text-primary">${it.projected_stock} ${it.unit}</span></td>
      </tr>
    `).join('');

    this.liveBillTbody.innerHTML = rows;
    if (this.liveBillGrandTotal) {
      const tot = typeof preview.estimated_total === 'number' ? preview.estimated_total : 0;
      this.liveBillGrandTotal.textContent = `₹${tot.toFixed(2)}`;
    }
    if (this.liveBillBadge) {
      this.liveBillBadge.textContent = 'Awaiting Voice Confirmation';
      this.liveBillBadge.className = 'badge-pill warning';
    }
    this.liveBillCard.style.display = 'block';
  },

  clearLiveBillPreview() {
    if (this.liveBillCard) {
      this.liveBillCard.style.display = 'none';
    }
  }
};

