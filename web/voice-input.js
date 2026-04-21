/**
 * Voice Input System for AIOS Onboarding
 * Handles speech recognition, wake words, and voice commands
 * Integrates with binary avatar for visual feedback
 */

class VoiceInputController {
  constructor(options = {}) {
    this.options = {
      wakeWords: options.wakeWords || ['hey aios', 'aios', 'computer'],
      continuous: options.continuous !== false,
      language: options.language || 'en-US',
      interimResults: options.interimResults !== false,
      maxAlternatives: options.maxAlternatives || 1,
      autoStart: options.autoStart || false,
      ...options
    };

    // State
    this.isListening = false;
    this.isAwake = false;
    this.currentTranscript = '';
    this.finalTranscript = '';
    
    // Recognition instance
    this.recognition = null;
    this.recognitionSupported = false;

    // Callbacks
    this.onTranscript = options.onTranscript || (() => {});
    this.onCommand = options.onCommand || (() => {});
    this.onWakeWord = options.onWakeWord || (() => {});
    this.onError = options.onError || ((error) => console.error('[Voice]', error));
    this.onStateChange = options.onStateChange || (() => {});

    // Avatar reference (will be set externally)
    this.avatar = null;

    this.init();
  }

  init() {
    // Check for Web Speech API support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.warn('[Voice] Web Speech API not supported in this browser');
      this.recognitionSupported = false;
      this.onError({ 
        type: 'not_supported', 
        message: 'Speech recognition not supported' 
      });
      return;
    }

    this.recognitionSupported = true;
    
    // Initialize recognition
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = this.options.continuous;
    this.recognition.interimResults = this.options.interimResults;
    this.recognition.maxAlternatives = this.options.maxAlternatives;
    this.recognition.lang = this.options.language;

    // Set up event handlers
    this.setupEventHandlers();

    console.log('[Voice] Voice input system initialized');

    // Auto-start if requested
    if (this.options.autoStart) {
      this.start();
    }
  }

  setupEventHandlers() {
    if (!this.recognition) return;

    // Speech recognition started
    this.recognition.onstart = () => {
      console.log('[Voice] Recognition started');
      this.isListening = true;
      this.updateState('listening');
      this.updateAvatarState('listening');
    };

    // Speech recognition ended
    this.recognition.onend = () => {
      console.log('[Voice] Recognition ended');
      this.isListening = false;
      
      // Restart if continuous mode and we're still awake
      if (this.options.continuous && this.isAwake) {
        setTimeout(() => {
          if (this.isAwake && !this.isListening) {
            this.start();
          }
        }, 100);
      } else {
        this.updateState('idle');
        this.updateAvatarState('idle');
      }
    };

    // Results received
    this.recognition.onresult = (event) => {
      this.handleResults(event);
    };

    // Errors
    this.recognition.onerror = (event) => {
      console.error('[Voice] Recognition error:', event.error);
      
      // Handle specific errors
      if (event.error === 'no-speech') {
        console.log('[Voice] No speech detected, continuing...');
        return;
      }
      
      if (event.error === 'aborted') {
        console.log('[Voice] Recognition aborted');
        return;
      }

      this.onError({
        type: event.error,
        message: `Speech recognition error: ${event.error}`
      });

      // Update avatar to show error
      this.updateAvatarState('error');
      
      // Return to listening after a delay
      setTimeout(() => {
        if (this.isAwake) {
          this.updateAvatarState('listening');
        }
      }, 2000);
    };

    // Audio start (user started speaking)
    this.recognition.onaudiostart = () => {
      console.log('[Voice] Audio capture started');
      this.updateAvatarState('receiving');
    };

    // Audio end (user stopped speaking)
    this.recognition.onaudioend = () => {
      console.log('[Voice] Audio capture ended');
    };

    // Speech start
    this.recognition.onspeechstart = () => {
      console.log('[Voice] Speech detected');
      this.updateAvatarState('processing');
    };

    // Speech end
    this.recognition.onspeechend = () => {
      console.log('[Voice] Speech ended');
    };
  }

  handleResults(event) {
    let interim = '';
    let final = '';

    // Process all results
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      
      if (event.results[i].isFinal) {
        final += transcript + ' ';
      } else {
        interim += transcript;
      }
    }

    // Update transcripts
    this.currentTranscript = interim.trim();
    
    if (final) {
      this.finalTranscript = final.trim();
      console.log('[Voice] Final transcript:', this.finalTranscript);
      
      // Process the final transcript
      this.processTranscript(this.finalTranscript);
    }

    // Notify listeners
    this.onTranscript({
      interim: this.currentTranscript,
      final: this.finalTranscript,
      isFinal: final.length > 0
    });
  }

  processTranscript(transcript) {
    const lowerTranscript = transcript.toLowerCase();

    // Check for wake words if not already awake
    if (!this.isAwake) {
      for (const wakeWord of this.options.wakeWords) {
        if (lowerTranscript.includes(wakeWord.toLowerCase())) {
          console.log('[Voice] Wake word detected:', wakeWord);
          this.wake();
          
          // Extract command after wake word
          const commandStart = lowerTranscript.indexOf(wakeWord.toLowerCase()) + wakeWord.length;
          const command = transcript.substring(commandStart).trim();
          
          if (command) {
            this.processCommand(command);
          }
          
          return;
        }
      }
      
      // Not awake and no wake word, ignore
      return;
    }

    // Already awake, process as command
    this.processCommand(transcript);
  }

  processCommand(command) {
    console.log('[Voice] Processing command:', command);
    
    // Update avatar to show processing
    this.updateAvatarState('thinking');

    // Notify command handler
    this.onCommand({
      command: command,
      timestamp: Date.now()
    });

    // Reset after processing
    setTimeout(() => {
      this.updateAvatarState('listening');
    }, 500);
  }

  wake() {
    if (this.isAwake) return;
    
    console.log('[Voice] System awake');
    this.isAwake = true;
    this.updateState('awake');
    this.updateAvatarState('active');
    
    // Notify wake word handler
    this.onWakeWord();

    // Auto-sleep after 30 seconds of no commands
    this.resetSleepTimer();
  }

  sleep() {
    if (!this.isAwake) return;
    
    console.log('[Voice] System sleeping');
    this.isAwake = false;
    this.updateState('sleeping');
    this.updateAvatarState('idle');
    
    if (this.sleepTimer) {
      clearTimeout(this.sleepTimer);
      this.sleepTimer = null;
    }
  }

  resetSleepTimer() {
    if (this.sleepTimer) {
      clearTimeout(this.sleepTimer);
    }

    // Auto-sleep after 30 seconds
    this.sleepTimer = setTimeout(() => {
      this.sleep();
    }, 30000);
  }

  start() {
    if (!this.recognitionSupported) {
      console.warn('[Voice] Cannot start - not supported');
      return false;
    }

    if (this.isListening) {
      console.log('[Voice] Already listening');
      return false;
    }

    try {
      console.log('[Voice] Starting recognition...');
      this.recognition.start();
      return true;
    } catch (error) {
      console.error('[Voice] Failed to start:', error);
      this.onError({
        type: 'start_failed',
        message: error.message
      });
      return false;
    }
  }

  stop() {
    if (!this.recognition || !this.isListening) {
      return;
    }

    try {
      console.log('[Voice] Stopping recognition...');
      this.recognition.stop();
      this.isListening = false;
      this.updateState('stopped');
    } catch (error) {
      console.error('[Voice] Failed to stop:', error);
    }
  }

  toggle() {
    if (this.isListening) {
      this.stop();
    } else {
      this.start();
    }
  }

  updateState(state) {
    console.log('[Voice] State:', state);
    this.onStateChange(state);
  }

  updateAvatarState(state) {
    if (!this.avatar) return;

    const stateMap = {
      'listening': { activity: 'idle', emotion: 'neutral' },
      'receiving': { activity: 'idle', emotion: 'neutral' },
      'processing': { activity: 'thinking', emotion: 'thinking' },
      'thinking': { activity: 'thinking', emotion: 'thinking' },
      'active': { activity: 'idle', emotion: 'happy' },
      'error': { activity: 'error', emotion: 'error' },
      'idle': { activity: 'idle', emotion: 'neutral' }
    };

    const avatarState = stateMap[state] || stateMap['idle'];
    
    if (this.avatar.renderer) {
      this.avatar.renderer.setActivity(avatarState.activity);
    }
    
    this.avatar.setEmotion(avatarState.emotion);

    // Visual indicator: pulse effect when listening
    if (state === 'listening' || state === 'receiving') {
      // Could add visual pulsing effect here
      if (this.avatar.renderer && this.avatar.renderer.digitMesh) {
        this.avatar.renderer.digitMesh.material.uniforms.uGlitchIntensity.value = 0.1;
      }
    } else {
      if (this.avatar.renderer && this.avatar.renderer.digitMesh) {
        this.avatar.renderer.digitMesh.material.uniforms.uGlitchIntensity.value = 0;
      }
    }
  }

  setAvatar(avatar) {
    this.avatar = avatar;
    console.log('[Voice] Avatar reference set');
  }

  // Utility: Check if browser supports speech recognition
  static isSupported() {
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  // Utility: Request microphone permission
  static async requestPermission() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(track => track.stop());
      return true;
    } catch (error) {
      console.error('[Voice] Microphone permission denied:', error);
      return false;
    }
  }

  destroy() {
    console.log('[Voice] Destroying voice input controller...');
    
    if (this.sleepTimer) {
      clearTimeout(this.sleepTimer);
    }

    if (this.recognition) {
      this.stop();
      this.recognition = null;
    }

    this.avatar = null;
  }
}

// Command parser helper
class VoiceCommandParser {
  static parse(command) {
    const lowerCommand = command.toLowerCase().trim();
    
    // Common patterns
    const patterns = {
      // Navigation
      next: /^(next|continue|proceed|go on|move forward)/i,
      back: /^(back|previous|go back|return)/i,
      skip: /^(skip|skip this|pass)/i,
      
      // Confirmation
      yes: /^(yes|yeah|yep|sure|okay|ok|affirmative|correct)/i,
      no: /^(no|nope|nah|negative|not really)/i,
      
      // Help
      help: /^(help|what|how|explain|info|information)/i,
      
      // Input
      input: /^(type|enter|input|set)\s+(.+)/i,
      
      // Control
      pause: /^(pause|wait|hold on|stop)/i,
      resume: /^(resume|start|go|begin)/i,
      cancel: /^(cancel|abort|quit|exit)/i,
      
      // Repeat
      repeat: /^(repeat|say again|what|pardon)/i
    };

    // Check each pattern
    for (const [type, pattern] of Object.entries(patterns)) {
      const match = lowerCommand.match(pattern);
      if (match) {
        return {
          type: type,
          command: command,
          match: match,
          params: match.length > 1 ? match.slice(1) : []
        };
      }
    }

    // If no pattern matches, return as custom command
    return {
      type: 'custom',
      command: command,
      match: null,
      params: []
    };
  }
}

// Export
export { VoiceInputController, VoiceCommandParser };

// Global API for non-module usage
if (typeof window !== 'undefined') {
  window.AIOS = window.AIOS || {};
  window.AIOS.VoiceInputController = VoiceInputController;
  window.AIOS.VoiceCommandParser = VoiceCommandParser;
}
