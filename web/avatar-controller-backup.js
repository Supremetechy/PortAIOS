/**
 * Avatar Controller - Integrates Binary Avatar with TTS and Audio Analysis
 * Handles speech synthesis, audio analysis, and state management
 */

import { BinaryAvatarRenderer } from './binary-avatar.js';

class AvatarController {
  constructor(container, options = {}) {
    this.container = container;
    this.options = options;

    this.renderer = new BinaryAvatarRenderer(container, {
      colorPalette: options.colorPalette || 'matrix',
      ...options
    });

    this.audioContext = null;
    this.analyser = null;
    this.frequencyData = null;

    this.speechQueue = [];
    this.isSpeaking = false;

    this.ws = null;
    this.wsReconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.usingFallback = false;

    this.currentEmotion = 'neutral';
    this.currentActivity = 'idle';

    this._voicesLoaded = false;

    this.init();
  }

  async init() {
    this.initAudioContext();
    this.preloadVoices();
    this.connectWebSocket();
    this.startMonitoring();
  }

  initAudioContext() {
    document.addEventListener('click', () => {
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        this.frequencyData = new Uint8Array(this.analyser.frequencyBinCount);
        console.log('[Avatar] Audio context initialized');
      }
    }, { once: true });
  }

  preloadVoices() {
    if (!window.speechSynthesis) return;
    const voices = window.speechSynthesis.getVoices();
    if (voices.length > 0) {
      this._voicesLoaded = true;
      return;
    }
    window.speechSynthesis.addEventListener('voiceschanged', () => {
      this._voicesLoaded = true;
    }, { once: true });
  }

  // ── WebSocket ──────────────────────────────────────────────────────

  connectWebSocket() {
    if (this.usingFallback) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.hostname}:8765`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[Avatar] WebSocket connected to TTS backend');
        this.wsReconnectAttempts = 0;
        this.renderer.setActivity('idle');
      };

      this.ws.onmessage = (event) => {
        this.handleWebSocketMessage(event.data);
      };

      this.ws.onerror = () => {
        // onclose handles retry/fallback
      };

      this.ws.onclose = () => {
        this.ws = null;
        this.attemptReconnect();
      };
    } catch (error) {
      this.attemptReconnect();
    }
  }

  attemptReconnect() {
    if (this.usingFallback) return;
    if (this.wsReconnectAttempts < this.maxReconnectAttempts) {
      this.wsReconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.wsReconnectAttempts), 10000);
      console.log(`[Avatar] WS reconnect attempt ${this.wsReconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
      setTimeout(() => this.connectWebSocket(), delay);
    } else {
      this.useFallbackMode();
    }
  }

  useFallbackMode() {
    if (this.usingFallback) return;
    this.usingFallback = true;
    this.ws = null;
    console.log('[Avatar] Using Web Speech API for voice output');
  }

  handleWebSocketMessage(data) {
    try {
      const message = JSON.parse(data);

      switch (message.type) {
        case 'audio_chunk':
          this.playAudioChunk(message.data);
          break;
        case 'state_update':
          this.updateState(message.state);
          break;
        case 'emotion':
          this.setEmotion(message.emotion);
          break;
        case 'system_status':
          this.updateSystemStatus(message.status);
          break;
        default:
          break;
      }
    } catch (error) {
      console.error('[Avatar] Error parsing WebSocket message:', error);
    }
  }

  // ── Speech ─────────────────────────────────────────────────────────

  async speak(text, options = {}) {
    const emotion = options.emotion || 'neutral';
    this.speechQueue.push({ text, emotion, options });
    if (!this.isSpeaking) {
      await this.processSpeechQueue();
    }
  }

  async processSpeechQueue() {
    if (this.speechQueue.length === 0) {
      this.isSpeaking = false;
      this.renderer.setActivity('idle');
      return;
    }

    this.isSpeaking = true;
    const { text, emotion } = this.speechQueue.shift();

    this.setEmotion(emotion);
    this.renderer.setActivity('speaking');

    try {
      if (this.ws && this.ws.readyState === WebSocket.OPEN && !this.usingFallback) {
        await this.speakViaBackend(text, emotion);
      } else {
        await this.speakViaWebSpeech(text);
      }
    } catch (error) {
      console.warn('[Avatar] Speech error, trying fallback:', error.message);
      try {
        await this.speakViaWebSpeech(text);
      } catch (e) {
        console.error('[Avatar] All speech methods failed:', e);
      }
    }

    await this.processSpeechQueue();
  }

  async speakViaBackend(text, emotion) {
    return new Promise((resolve, reject) => {
      const requestId = Date.now() + '_' + Math.random().toString(36).slice(2);

      this.ws.send(JSON.stringify({
        type: 'tts_request',
        text: text,
        emotion: emotion,
        request_id: requestId
      }));

      const completionHandler = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'tts_complete') {
            this.ws.removeEventListener('message', completionHandler);
            resolve();
          }
        } catch (e) {}
      };

      this.ws.addEventListener('message', completionHandler);

      setTimeout(() => {
        this.ws.removeEventListener('message', completionHandler);
        reject(new Error('TTS timeout'));
      }, 30000);
    });
  }

  async speakViaWebSpeech(text) {
    return new Promise((resolve, reject) => {
      if (!window.speechSynthesis) {
        reject(new Error('Speech synthesis not supported'));
        return;
      }

      // Cancel any stuck utterances
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);

      // Select voice — voices may load asynchronously
      const voices = window.speechSynthesis.getVoices();
      if (voices.length > 0) {
        const preferred = voices.find(v =>
          v.lang === 'en-US' && v.localService
        ) || voices.find(v =>
          v.lang.startsWith('en')
        );
        if (preferred) utterance.voice = preferred;
      }

      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      utterance.onstart = () => {
        this.renderer.setActivity('speaking');
        this.startSpeechVolumeSimulation();
      };

      utterance.onend = () => {
        this.stopSpeechVolumeSimulation();
        resolve();
      };

      utterance.onerror = (event) => {
        this.stopSpeechVolumeSimulation();
        if (event.error === 'canceled' || event.error === 'interrupted') {
          resolve();
        } else {
          reject(new Error(event.error || 'speech error'));
        }
      };

      // Chrome bug: speechSynthesis can hang after ~15s. Resume it.
      this._speechResumeInterval = setInterval(() => {
        if (window.speechSynthesis.speaking) {
          window.speechSynthesis.pause();
          window.speechSynthesis.resume();
        }
      }, 10000);

      window.speechSynthesis.speak(utterance);
    });
  }

  // Simulate volume from speech (Web Speech API doesn't expose audio data)
  startSpeechVolumeSimulation() {
    this._simVolume = true;
    const simulate = () => {
      if (!this._simVolume) return;
      const vol = 0.3 + Math.random() * 0.5;
      this.renderer.setVolume(vol);
      setTimeout(simulate, 80 + Math.random() * 60);
    };
    simulate();
  }

  stopSpeechVolumeSimulation() {
    this._simVolume = false;
    this.renderer.setVolume(0);
    if (this._speechResumeInterval) {
      clearInterval(this._speechResumeInterval);
      this._speechResumeInterval = null;
    }
  }

  playAudioChunk(audioData) {
    if (!this.audioContext) return;

    const audioBuffer = this.base64ToArrayBuffer(audioData);

    this.audioContext.decodeAudioData(audioBuffer, (buffer) => {
      const source = this.audioContext.createBufferSource();
      source.buffer = buffer;
      source.connect(this.analyser);
      this.analyser.connect(this.audioContext.destination);
      source.start(0);

      if (!this.isAnalyzing) {
        this.startAudioAnalysis();
      }
    }).catch(err => {
      console.warn('[Avatar] Audio decode error:', err.message);
    });
  }

  startAudioAnalysis() {
    if (this.isAnalyzing || !this.analyser) return;

    this.isAnalyzing = true;

    const analyze = () => {
      if (!this.isAnalyzing) return;

      this.analyser.getByteFrequencyData(this.frequencyData);

      let sum = 0;
      for (let i = 0; i < this.frequencyData.length; i++) {
        sum += this.frequencyData[i];
      }
      const avgVolume = sum / this.frequencyData.length / 255;

      this.renderer.setVolume(avgVolume);
      this.renderer.setFrequencyData(this.frequencyData);

      requestAnimationFrame(analyze);
    };

    analyze();
  }

  stopAudioAnalysis() {
    this.isAnalyzing = false;
    this.renderer.setVolume(0);
  }

  // ── State ──────────────────────────────────────────────────────────

  setEmotion(emotion) {
    this.currentEmotion = emotion;
    this.renderer.setEmotion(emotion);

    const emotionPalettes = {
      'happy': 'cyan',
      'neutral': 'matrix',
      'thinking': 'amber',
      'error': 'red',
      'excited': 'cyber-magenta'
    };

    const palette = emotionPalettes[emotion];
    if (palette && this.renderer.digitMesh) {
      this.renderer.options.colorPalette = palette;
      this.renderer.digitMesh.material.uniforms.uColorPalette.value = this.renderer.getColorPalette();
      if (this.renderer.rainPoints) {
        this.renderer.rainPoints.material.uniforms.uColor.value = this.renderer.getColorPalette();
      }
    }
  }

  updateState(state) {
    if (state.activity) this.renderer.setActivity(state.activity);
    if (state.emotion) this.setEmotion(state.emotion);
    if (state.cpuLoad !== undefined) this.renderer.setState({ cpuLoad: state.cpuLoad });
  }

  updateSystemStatus(status) {
    if (status.cpu_usage > 80) {
      this.renderer.setActivity('thinking');
    }
  }

  startMonitoring() {
    setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'request_status' }));
      }
    }, 5000);
  }

  stop() {
    this.speechQueue = [];
    this.isSpeaking = false;
    this.stopAudioAnalysis();
    this.stopSpeechVolumeSimulation();

    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    this.renderer.setActivity('idle');
  }

  base64ToArrayBuffer(base64) {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }

  destroy() {
    this.stop();
    if (this.ws) this.ws.close();
    if (this.audioContext) this.audioContext.close();
    this.renderer.destroy();
  }
}

export { AvatarController };

if (typeof window !== 'undefined') {
  window.AIOS = window.AIOS || {};
  window.AIOS.AvatarController = AvatarController;
}
