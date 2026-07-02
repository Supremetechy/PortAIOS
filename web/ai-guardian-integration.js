/**
 * AI Guardian Integration Layer
 * Connects the 3D avatar with voice, visemes, and gesture systems
 */

import { AIGuardian3D } from './ai-guardian-3d.js';

export class AIGuardianController {
    constructor(container, options = {}) {
        this.container = container;
        this.options = options;
        
        this.guardian = null;
        this.websocket = null;
        this.audioContext = null;
        this.currentAudio = null;
        
        // Viseme queue for smooth playback
        this.visemeQueue = [];
        this.visemeTimeline = [];
        this.playbackStartTime = 0;
        
        // Gesture mapping
        this.gestureKeywords = {
            'stop': ['stop', 'halt', 'wait', 'pause'],
            'wave': ['hello', 'hi', 'greet', 'welcome'],
            'point': ['look', 'see', 'there', 'this', 'that'],
            'thinking': ['think', 'consider', 'analyze', 'process', 'hmm']
        };
        
        // Emotion mapping
        this.emotionKeywords = {
            'happy': ['great', 'excellent', 'perfect', 'wonderful', 'success'],
            'thinking': ['analyzing', 'processing', 'calculating', 'considering'],
            'surprised': ['wow', 'amazing', 'incredible', 'unexpected']
        };
    }
    
    async init() {
        console.log('[AIGuardianController] Initializing...');
        
        // Initialize 3D avatar
        this.guardian = new AIGuardian3D(this.container, this.options);
        await this.guardian.init();
        
        // Setup audio context
        this._setupAudioContext();
        
        // Connect to viseme websocket
        this._connectVisemeWebSocket();
        
        // Register global viseme listener if available
        if (typeof eel !== 'undefined') {
            this._registerEelIntegration();
        }
        
        console.log('[AIGuardianController] ✓ Ready');
        return this;
    }
    
    _setupAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            console.log('[AIGuardianController] Audio context initialized');
        } catch (error) {
            console.warn('[AIGuardianController] AudioContext not available:', error);
        }
    }
    
    _connectVisemeWebSocket() {
        const wsUrl = this.options.visemeWebSocket || 'ws://localhost:8766';
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('[AIGuardianController] Connected to viseme server');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this._handleVisemeData(data);
                } catch (error) {
                    console.error('[AIGuardianController] Error parsing viseme data:', error);
                }
            };
            
            this.websocket.onerror = (error) => {
                console.warn('[AIGuardianController] WebSocket error:', error);
            };
            
            this.websocket.onclose = () => {
                console.log('[AIGuardianController] Viseme WebSocket closed');
                // Attempt reconnect after 3 seconds
                setTimeout(() => this._connectVisemeWebSocket(), 3000);
            };
        } catch (error) {
            console.warn('[AIGuardianController] Could not connect to viseme server:', error);
        }
    }
    
    _registerEelIntegration() {
        // Listen for viseme data from Python backend
        window.addEventListener('viseme_data', (event) => {
            this._handleVisemeData(event.detail);
        });
        
        console.log('[AIGuardianController] Eel integration registered');
    }
    
    _handleVisemeData(data) {
        if (data.phonemes && data.audio) {
            this.visemeTimeline = data.phonemes;
            this._playAudioWithVisemes(data.audio);
        }
    }
    
    async _playAudioWithVisemes(audioBase64) {
        if (!this.audioContext) {
            console.warn('[AIGuardianController] No audio context available');
            return;
        }
        
        try {
            // Decode base64 audio
            const audioData = atob(audioBase64);
            const audioArray = new Uint8Array(audioData.length);
            for (let i = 0; i < audioData.length; i++) {
                audioArray[i] = audioData.charCodeAt(i);
            }
            
            // Decode audio buffer
            const audioBuffer = await this.audioContext.decodeAudioData(audioArray.buffer);
            
            // Create and play audio source
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            
            // Setup audio analysis for volume-reactive effects
            const analyser = this.audioContext.createAnalyser();
            analyser.fftSize = 256;
            source.connect(analyser);
            
            const frequencyData = new Uint8Array(analyser.frequencyBinCount);
            
            // Start playback
            this.playbackStartTime = this.audioContext.currentTime;
            source.start(0);
            this.currentAudio = source;
            
            // Start viseme animation
            this._animateVisemes(analyser, frequencyData);
            
            // Cleanup on end
            source.onended = () => {
                this.guardian.stopSpeaking();
                this.currentAudio = null;
            };
            
        } catch (error) {
            console.error('[AIGuardianController] Error playing audio:', error);
        }
    }
    
    _animateVisemes(analyser, frequencyData) {
        const animate = () => {
            if (!this.currentAudio) return;
            
            // Get current time in playback
            const currentTime = this.audioContext.currentTime - this.playbackStartTime;
            
            // Find current viseme from timeline
            const currentViseme = this.visemeTimeline.find(v => 
                v.start <= currentTime && currentTime < v.end
            );
            
            if (currentViseme) {
                const visemeName = this._phonemeToViseme(currentViseme.phoneme);
                this.guardian.setViseme(visemeName, 1.0);
            }
            
            // Update volume for reactive effects
            analyser.getByteFrequencyData(frequencyData);
            const volume = frequencyData.reduce((a, b) => a + b) / (frequencyData.length * 255);
            this.guardian.setVolume(volume);
            
            requestAnimationFrame(animate);
        };
        
        animate();
    }
    
    _phonemeToViseme(phoneme) {
        // Map phonemes to viseme morph targets
        const mapping = {
            'p': 'viseme_m', 'b': 'viseme_m', 'm': 'viseme_m',
            'f': 'viseme_f', 'v': 'viseme_f',
            'aa': 'viseme_aa', 'ah': 'viseme_aa', 'a': 'viseme_aa',
            'o': 'viseme_o', 'oh': 'viseme_o', 'ow': 'viseme_o',
            'e': 'viseme_e', 'eh': 'viseme_e', 'ey': 'viseme_e',
            'i': 'viseme_i', 'ih': 'viseme_i', 'iy': 'viseme_i',
            'u': 'viseme_u', 'uh': 'viseme_u', 'uw': 'viseme_u'
        };
        
        return mapping[phoneme.toLowerCase()] || 'viseme_aa';
    }
    
    _detectGestureFromText(text) {
        const lowerText = text.toLowerCase();
        
        for (const [gesture, keywords] of Object.entries(this.gestureKeywords)) {
            if (keywords.some(keyword => lowerText.includes(keyword))) {
                return gesture;
            }
        }
        
        return 'none';
    }
    
    _detectEmotionFromText(text) {
        const lowerText = text.toLowerCase();
        
        for (const [emotion, keywords] of Object.entries(this.emotionKeywords)) {
            if (keywords.some(keyword => lowerText.includes(keyword))) {
                return emotion;
            }
        }
        
        return 'neutral';
    }
    
    // Public API
    
    async speak(text, options = {}) {
        console.log('[AIGuardianController] Speaking:', text);
        
        // Auto-detect emotion and gesture if not provided
        const emotion = options.emotion || this._detectEmotionFromText(text);
        const gesture = options.gesture || this._detectGestureFromText(text);
        
        this.guardian.setEmotion(emotion);
        this.guardian.setGesture(gesture);
        this.guardian.setActivity('speaking');
        
        // Send to backend for TTS + visemes if available
        if (typeof eel !== 'undefined' && eel.speak_with_visemes) {
            try {
                await eel.speak_with_visemes(text, emotion)();
            } catch (error) {
                console.error('[AIGuardianController] Backend speech error:', error);
                this._fallbackSpeak(text);
            }
        } else {
            this._fallbackSpeak(text);
        }
        
        return this;
    }
    
    _fallbackSpeak(text) {
        // Use Web Speech API as fallback
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            utterance.pitch = 1.0;
            
            // Simulate visemes based on speech progress
            utterance.onboundary = (event) => {
                if (event.name === 'word') {
                    // Simple animation: cycle through visemes
                    const visemes = ['viseme_aa', 'viseme_e', 'viseme_o', 'viseme_i'];
                    const randomViseme = visemes[Math.floor(Math.random() * visemes.length)];
                    this.guardian.setViseme(randomViseme, 1.0);
                }
            };
            
            utterance.onend = () => {
                this.guardian.stopSpeaking();
            };
            
            speechSynthesis.speak(utterance);
        }
    }
    
    stop() {
        if (this.currentAudio) {
            this.currentAudio.stop();
            this.currentAudio = null;
        }
        
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
        }
        
        this.guardian.stopSpeaking();
        return this;
    }
    
    setActivity(activity) {
        this.guardian.setActivity(activity);
        return this;
    }
    
    setEmotion(emotion) {
        this.guardian.setEmotion(emotion);
        return this;
    }
    
    setGesture(gesture) {
        this.guardian.setGesture(gesture);
        return this;
    }
    
    destroy() {
        if (this.websocket) {
            this.websocket.close();
        }
        
        if (this.guardian) {
            this.guardian.destroy();
        }
        
        if (this.audioContext) {
            this.audioContext.close();
        }
        
        console.log('[AIGuardianController] Destroyed');
    }
}

// Make available globally for backward compatibility
window.AIGuardianController = AIGuardianController;

export default AIGuardianController;
