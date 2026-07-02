/**
 * Avatar Controller - FIXED for Firefox/Safari TTS
 * Enhanced cross-browser compatibility for speech synthesis
 */

import { BinaryAvatarRenderer } from './binary-avatar.js';

class AvatarController {
  constructor(container, options = {}) {
    this.container = container;
    this.options = options;

    // Accept an externally-created renderer, or build one when a
    // valid container is provided.  Passing container=null without
    // a renderer is allowed — controller runs in "headless" mode
    // (TTS / WebSocket only, no rendering).
    if (options.renderer) {
      this.renderer = options.renderer;
    } else if (container) {
      this.renderer = new BinaryAvatarRenderer(container, {
        colorPalette: options.colorPalette || 'matrix',
        ...options,
      });
    } else {
      // Headless stub — every public method is a safe no-op
      this.renderer = {
        setActivity() {}, setEmotion() {}, setVolume() {},
        setColorPalette() {}, setFrequencyData() {}, setState() {},
        options: { colorPalette: 'matrix' },
        state: { emotion: 'neutral', activity: 'idle', volume: 0 },
      };
    }

    this.audioContext = null;
    this.analyser = null;
    this.frequencyData = null;
    
    this.speechQueue = [];
    this.isSpeaking = false;
    
    this.ws = null;
    this.wsReconnectAttempts = 0;
    this.maxReconnectAttempts = 5;

    this.currentEmotion = 'neutral';
    this.currentActivity = 'idle';
    
    // Browser detection
    this.browser = this.detectBrowser();
    
    // Voice loading state
    this.voicesLoaded = false;
    this.selectedVoice = null;
    
    this.init();
  }

  detectBrowser() {
    const ua = navigator.userAgent;
    if (ua.includes('Firefox')) return 'firefox';
    if (ua.includes('Safari') && !ua.includes('Chrome')) return 'safari';
    if (ua.includes('Chrome')) return 'chrome';
    if (ua.includes('Edge')) return 'edge';
    return 'other';
  }

  async init() {
    console.log(`[Avatar] Browser detected: ${this.browser}`);
    
    // Initialize audio context (requires user gesture)
    this.initAudioContext();
    
    // Preload voices with browser-specific handling
    await this.preloadVoices();
    
    // Connect to backend WebSocket
    this.connectWebSocket();
    
    // Start monitoring loop
    this.startMonitoring();
  }

  initAudioContext() {
    // Tracks whether the page has received a user activation gesture. Chrome's
    // autoplay policy blocks both AudioContext.resume() and the first call to
    // speechSynthesis.speak() until this is true; speak() reports the failure
    // as `event.error === 'not-allowed'`, which is easy to misread as a
    // microphone-permissions problem (it isn't).
    this.userActivated = false;
    this._pendingSpeechQueue = [];

    const onFirstGesture = () => {
      this.userActivated = true;

      if (!this.audioContext) {
        try {
          this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
          this.analyser = this.audioContext.createAnalyser();
          this.analyser.fftSize = 256;
          this.frequencyData = new Uint8Array(this.analyser.frequencyBinCount);
          console.log('[Avatar] Audio context initialized');
        } catch (error) {
          console.error('[Avatar] Failed to create audio context:', error);
        }
      }

      // Prime the SpeechSynthesis engine with a zero-volume empty utterance.
      // This satisfies Chrome's autoplay gate so subsequent speak() calls work
      // without firing 'not-allowed'.
      if (window.speechSynthesis) {
        try {
          const primer = new SpeechSynthesisUtterance(' ');
          primer.volume = 0;
          primer.rate = 10;
          window.speechSynthesis.speak(primer);
        } catch (e) {
          console.warn('[Avatar] TTS primer failed:', e);
        }
      }

      // Drain anything that was deferred while we waited for the gesture.
      const queued = this._pendingSpeechQueue.splice(0);
      for (const text of queued) {
        this.speakViaWebSpeech(text).catch(() => {});
      }
    };

    document.addEventListener('click', onFirstGesture, { once: true });
    document.addEventListener('keydown', onFirstGesture, { once: true });
    document.addEventListener('touchstart', onFirstGesture, { once: true });
  }

  async preloadVoices() {
    if (!window.speechSynthesis) {
      console.warn('[Avatar] Speech Synthesis not available');
      return;
    }

    return new Promise((resolve) => {
      // Different browsers handle voice loading differently
      const loadVoices = () => {
        const voices = window.speechSynthesis.getVoices();
        
        if (voices.length > 0) {
          this.voicesLoaded = true;
          this.availableVoices = voices;
          
          // Categorize voices by language and quality
          this.voiceCategories = {
            'en-US': voices.filter(v => v.lang === 'en-US'),
            'en-GB': voices.filter(v => v.lang === 'en-GB'),
            'en-AU': voices.filter(v => v.lang === 'en-AU'),
            'es-ES': voices.filter(v => v.lang.startsWith('es')),
            'fr-FR': voices.filter(v => v.lang.startsWith('fr')),
            'de-DE': voices.filter(v => v.lang.startsWith('de')),
            'ja-JP': voices.filter(v => v.lang.startsWith('ja')),
            'zh-CN': voices.filter(v => v.lang.startsWith('zh')),
            'other': voices.filter(v => !v.lang.match(/^(en|es|fr|de|ja|zh)/))
          };
          
          // Select best voice based on browser with enhanced selection
          if (this.browser === 'safari') {
            // Safari: Prefer premium voices (Samantha, Alex, Victoria)
            this.selectedVoice = voices.find(v => 
              v.name.includes('Samantha') || v.name.includes('Alex') || v.name.includes('Victoria')
            ) || voices.find(v => v.lang.startsWith('en') && v.localService);
          } else if (this.browser === 'firefox') {
            // Firefox: Use default voice or look for quality voices
            this.selectedVoice = voices.find(v => v.default) || 
                                voices.find(v => v.lang === 'en-US' && v.localService) || 
                                voices[0];
          } else {
            // Chrome/Edge: Prefer local English voices first — remote Google voices fail
            // silently on localhost/app mode (onerror: 'network' / 'synthesis-failed')
            this.selectedVoice = voices.find(v => v.lang.startsWith('en') && v.localService)
              || voices.find(v => v.name.includes('Google US English') || v.name.includes('Google UK English'))
              || voices.find(v => v.name.includes('Microsoft') && v.name.includes('Natural'))
              || voices.find(v => v.lang.startsWith('en'));
          }
          
          console.log('[Avatar] Voice selected:', this.selectedVoice?.name || 'default');
          console.log(`[Avatar] ${voices.length} voices available in ${Object.keys(this.voiceCategories).length} languages`);
          
          // Populate voice selector UI if it exists
          this.populateVoiceSelector();
          resolve();
        } else {
          // Voices not loaded yet, wait for event
          if (!this._voiceLoadListener) {
            this._voiceLoadListener = true;
            window.speechSynthesis.addEventListener('voiceschanged', () => {
              loadVoices();
            }, { once: true });
            
            // Timeout for browsers that don't fire voiceschanged
            setTimeout(() => {
              if (!this.voicesLoaded) {
                console.log('[Avatar] Voice loading timeout - proceeding with system default voice');
                this.voicesLoaded = true;
                const voices = window.speechSynthesis.getVoices();
                if (voices.length > 0) {
                  this.availableVoices = voices;
                  this.selectedVoice = voices[0];
                  console.log('[Avatar] Fallback voice selected:', this.selectedVoice?.name || 'default');
                }
                resolve();
              }
            }, 3000);
          }
        }
      };

      loadVoices();
      
      // Safari-specific: Force trigger
      if (this.browser === 'safari') {
        window.speechSynthesis.getVoices();
      }
    });
  }

  populateVoiceSelector() {
    const selector = document.getElementById('voice-select');
    if (!selector || !this.availableVoices) return;

    // Clear existing options
    selector.innerHTML = '';

    // Group voices by language
    const languageGroups = {
      'English (US)': this.voiceCategories['en-US'] || [],
      'English (UK)': this.voiceCategories['en-GB'] || [],
      'English (AU)': this.voiceCategories['en-AU'] || [],
      'Spanish': this.voiceCategories['es-ES'] || [],
      'French': this.voiceCategories['fr-FR'] || [],
      'German': this.voiceCategories['de-DE'] || [],
      'Japanese': this.voiceCategories['ja-JP'] || [],
      'Chinese': this.voiceCategories['zh-CN'] || [],
      'Other Languages': this.voiceCategories['other'] || []
    };

    for (const [label, voices] of Object.entries(languageGroups)) {
      if (voices.length === 0) continue;

      const optgroup = document.createElement('optgroup');
      optgroup.label = label;

      voices.forEach(voice => {
        const option = document.createElement('option');
        option.value = voice.name;
        option.textContent = `${voice.name} ${voice.localService ? '📱' : '☁️'}`;
        if (voice === this.selectedVoice) {
          option.selected = true;
        }
        optgroup.appendChild(option);
      });

      selector.appendChild(optgroup);
    }

    // Add change listener
    selector.addEventListener('change', (e) => {
      const voiceName = e.target.value;
      this.selectedVoice = this.availableVoices.find(v => v.name === voiceName);
      console.log('[Avatar] Voice changed to:', this.selectedVoice?.name);
      this.updateTTSIndicator('browser');
    });
  }

  setVoice(voiceName) {
    if (!this.availableVoices) return false;
    const voice = this.availableVoices.find(v => v.name === voiceName);
    if (voice) {
      this.selectedVoice = voice;
      console.log('[Avatar] Voice manually set to:', voice.name);
      return true;
    }
    return false;
  }

  getAvailableVoices() {
    return this.voiceCategories || {};
  }

  connectWebSocket() {
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
      
      this.ws.onerror = (error) => {
        console.error('[Avatar] WebSocket error:', error);
      };
      
      this.ws.onclose = () => {
        console.log('[Avatar] WebSocket closed');
        this.attemptReconnect();
      };
    } catch (error) {
      console.warn('[Avatar] WebSocket not available, using fallback mode');
      this.useFallbackMode();
    }
  }

  attemptReconnect() {
    if (this.wsReconnectAttempts < this.maxReconnectAttempts) {
      this.wsReconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.wsReconnectAttempts), 30000);
      console.log(`[Avatar] Reconnecting in ${delay}ms...`);
      setTimeout(() => this.connectWebSocket(), delay);
    } else {
      console.warn('[Avatar] Max reconnection attempts, using fallback');
      this.useFallbackMode();
    }
  }

  useFallbackMode() {
    this.usingFallback = true;
    console.log('[Avatar] Using Web Speech API fallback');
  }

  handleWebSocketMessage(data) {
    try {
      const message = JSON.parse(data);
      
      switch (message.type) {
        case 'audio_data':
          this.playFullAudio(message.data);
          break;

        case 'audio_chunk':
          // Legacy chunked path — accumulate and decode on tts_complete
          if (!this._audioChunks) this._audioChunks = [];
          this._audioChunks.push(message.data);
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

        case 'agent_result':
          if (this.onAgentResult) {
            this.onAgentResult(message);
          }
          break;

        case 'tts_complete':
          // If legacy chunks were accumulated, decode them now
          if (this._audioChunks && this._audioChunks.length > 0) {
            const combined = this._audioChunks.join('');
            this._audioChunks = [];
            this.playFullAudio(combined);
          } else {
            this.stopSpeakingAnimation();
          }
          break;
      }
    } catch (error) {
      console.error('[Avatar] Error parsing message:', error);
    }
  }

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
    const { text, emotion, options } = this.speechQueue.shift();
    
    this.setEmotion(emotion);
    this.renderer.setActivity('speaking');

    try {
      // Always use Web Speech API for Firefox/Safari
      if (this.browser === 'firefox' || this.browser === 'safari') {
        await this.speakViaWebSpeech(text);
      } else if (this.ws && this.ws.readyState === WebSocket.OPEN && !this.usingFallback) {
        // Try backend first, but fallback to Web Speech if it fails
        try {
          await this.speakViaBackend(text, emotion);
        } catch (backendError) {
          console.log('[Avatar] Backend TTS failed, using Web Speech API fallback');
          await this.speakViaWebSpeech(text);
        }
      } else {
        await this.speakViaWebSpeech(text);
      }
    } catch (error) {
      console.warn('[Avatar] Speech error:', error.message || error);
      // Continue processing queue even if speech fails
    }

    await this.processSpeechQueue();
  }

  async speakViaBackend(text, emotion) {
    this.updateTTSIndicator('backend');
    return new Promise((resolve, reject) => {
      // Shorter timeout for faster fallback
      const timeout = setTimeout(() => {
        this.ws.removeEventListener('message', completionHandler);
        console.log('[Avatar] Backend TTS timeout after 10s, will fallback to Web Speech');
        reject(new Error('Backend TTS timeout'));
      }, 10000);

      const completionHandler = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'tts_complete') {
            clearTimeout(timeout);
            this.ws.removeEventListener('message', completionHandler);
            resolve();
          }
        } catch (e) {
          // Ignore malformed messages
        }
      };

      this.ws.addEventListener('message', completionHandler);

      try {
        this.ws.send(JSON.stringify({
          type: 'tts_request',
          text: text,
          emotion: emotion
        }));
      } catch (sendError) {
        clearTimeout(timeout);
        this.ws.removeEventListener('message', completionHandler);
        reject(new Error('Failed to send TTS request'));
      }
    });
  }

  async speakViaWebSpeech(text) {
    if (!window.speechSynthesis) {
      console.warn('[Avatar] Speech synthesis not supported');
      return;
    }

    // Chrome / Safari refuse the very first speak() call until the page has
    // received a user activation gesture (click/keydown/touch). Defer this
    // utterance until that happens; initAudioContext() will replay the queue.
    if (!this.userActivated) {
      console.log('[Avatar] Deferring TTS until first user gesture (autoplay policy)');
      this._pendingSpeechQueue.push(text);
      return;
    }

    this.updateTTSIndicator('browser');

    return new Promise((resolve, reject) => {
      // CRITICAL FIX: Cancel any ongoing speech first
      try {
        window.speechSynthesis.cancel();
      } catch(e) {
        console.warn('[Avatar] Error canceling speech:', e);
      }
      
      // Wait a tick for cancellation to process (especially important for Safari)
      setTimeout(() => {
        const utterance = new SpeechSynthesisUtterance(text);
        
        // Configure voice
        if (this.selectedVoice) {
          utterance.voice = this.selectedVoice;
        } else {
          // Fallback voice selection
          const voices = window.speechSynthesis.getVoices();
          const enVoice = voices.find(v => v.lang.startsWith('en'));
          if (enVoice) utterance.voice = enVoice;
        }
        
        // Browser-specific settings
        if (this.browser === 'firefox') {
          utterance.rate = 0.9;  // Firefox tends to speak faster
          utterance.pitch = 1.0;
          utterance.volume = 1.0;
        } else if (this.browser === 'safari') {
          utterance.rate = 1.0;
          utterance.pitch = 1.0;
          utterance.volume = 1.0;
        } else {
          utterance.rate = 1.0;
          utterance.pitch = 1.0;
          utterance.volume = 1.0;
        }

        let hasStarted = false;
        let hasEnded = false;

        utterance.onstart = () => {
          hasStarted = true;
          console.log('[Avatar] Speech started');
          this.renderer.setActivity('speaking');
          this.startSpeechVolumeSimulation();
        };

        utterance.onend = () => {
          if (hasEnded) return; // Prevent double-firing
          hasEnded = true;
          console.log('[Avatar] Speech ended');
          this.stopSpeechVolumeSimulation();
          resolve();
        };

        utterance.onerror = (event) => {
          if (hasEnded) return; // Already handled
          hasEnded = true;
          this.stopSpeechVolumeSimulation();

          // Common non-critical errors that should not break the flow
          const nonCriticalErrors = ['interrupted', 'canceled', 'network', 'synthesis-failed', 'synthesis-unavailable'];

          if (nonCriticalErrors.includes(event.error)) {
            // 'network' / 'synthesis-failed' usually means a remote voice (e.g. Google US
            // English) was selected and failed on localhost. Retry with a local voice.
            if (event.error === 'network' || event.error === 'synthesis-failed') {
              const localVoice = window.speechSynthesis.getVoices()
                .find(v => v.lang.startsWith('en') && v.localService);
              if (localVoice && utterance.voice !== localVoice) {
                console.warn('[Avatar] Remote voice failed, retrying with local voice:', localVoice.name);
                this.selectedVoice = localVoice;
                // Re-attempt via the public speak() path so queue/state are managed correctly
                this.speakViaWebSpeech(text).then(resolve).catch(() => resolve());
                return;
              }
            }
            console.log('[Avatar] Speech error (non-critical):', event.error);
            resolve(); // Resolve instead of reject for graceful degradation
          } else if (event.error === 'not-allowed') {
            // NB: this is the SpeechSynthesisUtterance API (TTS / output),
            // not microphone access. 'not-allowed' here means the browser
            // refused to play synthesized audio. The most common causes are:
            //   1. No user activation yet (autoplay policy) — handled by the
            //      gesture-priming in initAudioContext(). If we still hit it
            //      after a click, the priming didn't take.
            //   2. The TTS engine is disabled in chrome://settings.
            //   3. The selected voice is a remote/Google voice and the page
            //      origin is `file://` (Chrome blocks remote TTS there).
            // Resolve so the agent loop continues; falling back to the
            // backend Piper bridge or a local voice is the user's recourse.
            console.warn(
              '[Avatar] TTS rejected as "not-allowed". This is the speech-synthesis ' +
              '(output) API, NOT microphone access. Likely causes: autoplay policy ' +
              '(needs a click before the first speak()), TTS engine disabled in ' +
              'browser settings, or remote voice blocked on file:// origins.'
            );
            resolve();
          } else {
            console.warn('[Avatar] Speech error:', event.error, '- continuing anyway');
            resolve(); // Always resolve to prevent blocking
          }
        };

        // CRITICAL FIX for Chrome/Safari hanging issue
        // Resume after 14 seconds if still speaking
        const resumeInterval = setInterval(() => {
          if (window.speechSynthesis.speaking && !hasEnded) {
            console.log('[Avatar] Resuming speech (browser workaround)');
            window.speechSynthesis.pause();
            window.speechSynthesis.resume();
          } else {
            clearInterval(resumeInterval);
          }
        }, 14000);

        // Safety timeout
        const timeout = setTimeout(() => {
          if (!hasEnded) {
            console.warn('[Avatar] Speech timeout, forcing end');
            clearInterval(resumeInterval);
            window.speechSynthesis.cancel();
            this.stopSpeechVolumeSimulation();
            resolve();
          }
        }, 30000);

        utterance.onend = () => {
          if (hasEnded) return;
          hasEnded = true;
          clearInterval(resumeInterval);
          clearTimeout(timeout);
          this.stopSpeechVolumeSimulation();
          resolve();
        };

        // FIREFOX FIX: Small delay before speaking
        if (this.browser === 'firefox') {
          setTimeout(() => {
            window.speechSynthesis.speak(utterance);
          }, 50);
        } else {
          window.speechSynthesis.speak(utterance);
        }

        // SAFARI FIX: Ensure speech starts within 1 second
        if (this.browser === 'safari') {
          setTimeout(() => {
            if (!hasStarted && !hasEnded) {
              console.warn('[Avatar] Safari speech failed to start, retrying...');
              window.speechSynthesis.cancel();
              window.speechSynthesis.speak(utterance);
            }
          }, 1000);
        }
      }, 50); // Small delay after cancel
    });
  }

  startSpeechVolumeSimulation() {
    let phase = 0;
    this.volumeSimInterval = setInterval(() => {
      phase += 0.1;
      const volume = (Math.sin(phase) + 1) * 0.3 + 0.2;
      this.renderer.setVolume(volume);
    }, 50);
  }

  stopSpeechVolumeSimulation() {
    if (this.volumeSimInterval) {
      clearInterval(this.volumeSimInterval);
      this.volumeSimInterval = null;
    }
    this.renderer.setVolume(0);
  }

  stopSpeakingAnimation() {
    this.isAnalyzing = false;
    this.isSpeaking = false;
    this.renderer.setActivity('idle');
    this.renderer.setVolume(0);
    this.stopSpeechVolumeSimulation();
  }

  playFullAudio(base64Data) {
    if (!this.audioContext) return;
    if (!base64Data) { this.stopSpeakingAnimation(); return; }

    const arrayBuf = this.base64ToArrayBuffer(base64Data);

    this.audioContext.decodeAudioData(arrayBuf.slice(0))
      .then((buffer) => {
        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;

        source.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);

        this.renderer.setActivity('speaking');
        if (!this.isAnalyzing) this.startAudioAnalysis();

        source.onended = () => this.stopSpeakingAnimation();
        source.start(0);
      })
      .catch((err) => {
        console.warn('[Avatar] decodeAudioData failed, falling back to browser TTS:', err.message);
        this.stopSpeakingAnimation();
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

  setEmotion(emotion) {
    this.currentEmotion = emotion;
    this.renderer.setEmotion(emotion);

    const emotionPalettes = {
      'happy': 'cyan',
      'neutral': 'matrix',
      'thinking': 'amber',
      'error': 'red',
      'excited': 'cyber-magenta',
      'groovy': 'ice',
    };

    const palette = emotionPalettes[emotion];
    if (palette && typeof this.renderer.setColorPalette === 'function') {
      this.renderer.setColorPalette(palette);
    }
  }

  updateState(state) {
    if (state.activity) {
      this.renderer.setActivity(state.activity);
    }
    if (state.emotion) {
      this.setEmotion(state.emotion);
    }
    if (state.cpuLoad !== undefined) {
      this.renderer.setState({ cpuLoad: state.cpuLoad });
    }
  }

  updateSystemStatus(status) {
    if (status.cpu_usage > 80) {
      this.renderer.setActivity('thinking');
    }
  }

  startMonitoring() {
    setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          type: 'request_status'
        }));
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

  updateTTSIndicator(method) {
    // Update visual indicator for TTS method
    const indicator = document.getElementById('tts-indicator');
    if (!indicator) return;

    const methodInfo = {
      'backend': {
        text: '🔊 Backend TTS',
        color: '#00ff00',
        tooltip: 'Using Piper neural TTS backend'
      },
      'browser': {
        text: '🔊 Browser TTS',
        color: '#00ccff',
        tooltip: `Using ${this.selectedVoice?.name || 'system'} voice`
      }
    };

    const info = methodInfo[method];
    if (info) {
      indicator.textContent = info.text;
      indicator.style.color = info.color;
      indicator.title = info.tooltip;
      indicator.style.animation = 'pulse-glow 0.3s ease-in-out';
      
      // Dispatch custom event for other UI components
      window.dispatchEvent(new CustomEvent('avatar:ttsMethodChanged', {
        detail: { method, voice: this.selectedVoice?.name }
      }));
    }
  }

  destroy() {
    this.stop();
    
    if (this.ws) {
      this.ws.close();
    }
    
    if (this.audioContext) {
      this.audioContext.close();
    }
    
    this.renderer.destroy();
  }
}

export { AvatarController };

if (typeof window !== 'undefined') {
  window.AIOS = window.AIOS || {};
  window.AIOS.AvatarController = AvatarController;
}
