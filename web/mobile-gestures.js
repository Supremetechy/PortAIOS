/**
 * Mobile & Touch Gesture Support for AIOS Dynamic UI
 * Provides swipe, pinch, and tap gestures for mobile devices
 */

class MobileGestureHandler {
  constructor(dynamicUI, options = {}) {
    this.dynamicUI = dynamicUI;
    this.options = {
      swipeThreshold: options.swipeThreshold || 50,
      pinchThreshold: options.pinchThreshold || 0.2,
      doubleTapDelay: options.doubleTapDelay || 300,
      ...options
    };
    
    this.touchStartX = 0;
    this.touchStartY = 0;
    this.touchEndX = 0;
    this.touchEndY = 0;
    this.lastTap = 0;
    this.initialPinchDistance = 0;
    this.currentScale = 1;
    
    this.gestureActive = false;
    this.touches = [];
    
    this._init();
  }

  _init() {
    // Detect if mobile device
    this.isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    this.isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    
    if (this.isTouch) {
      this._bindTouchEvents();
      this._addMobileStyles();
      console.log('[MobileGestures] Touch support enabled');
    }
  }

  _bindTouchEvents() {
    const container = this.dynamicUI.container;
    
    // Touch events
    container.addEventListener('touchstart', this._handleTouchStart.bind(this), { passive: false });
    container.addEventListener('touchmove', this._handleTouchMove.bind(this), { passive: false });
    container.addEventListener('touchend', this._handleTouchEnd.bind(this), { passive: false });
    container.addEventListener('touchcancel', this._handleTouchCancel.bind(this), { passive: false });
    
    // Prevent default context menu on long press
    container.addEventListener('contextmenu', (e) => {
      if (this.isMobile) {
        e.preventDefault();
      }
    });
  }

  _handleTouchStart(e) {
    this.touches = Array.from(e.touches);
    
    if (this.touches.length === 1) {
      // Single touch
      this.touchStartX = this.touches[0].clientX;
      this.touchStartY = this.touches[0].clientY;
      this.gestureActive = true;
      
      // Check for double tap
      const now = Date.now();
      if (now - this.lastTap < this.options.doubleTapDelay) {
        this._handleDoubleTap(this.touches[0]);
        this.lastTap = 0;
      } else {
        this.lastTap = now;
      }
    } else if (this.touches.length === 2) {
      // Pinch gesture
      this.initialPinchDistance = this._getPinchDistance(this.touches);
      e.preventDefault();
    }
  }

  _handleTouchMove(e) {
    this.touches = Array.from(e.touches);
    
    if (this.touches.length === 1 && this.gestureActive) {
      // Swipe gesture
      this.touchEndX = this.touches[0].clientX;
      this.touchEndY = this.touches[0].clientY;
      
      // Show swipe indicator
      this._showSwipeIndicator();
    } else if (this.touches.length === 2) {
      // Pinch gesture
      const currentDistance = this._getPinchDistance(this.touches);
      const scale = currentDistance / this.initialPinchDistance;
      
      if (Math.abs(scale - 1) > this.options.pinchThreshold) {
        this._handlePinch(scale);
      }
      
      e.preventDefault();
    }
  }

  _handleTouchEnd(e) {
    if (this.gestureActive && this.touches.length === 1) {
      this._handleSwipe();
    }
    
    this.gestureActive = false;
    this.touches = Array.from(e.touches);
    this._hideSwipeIndicator();
  }

  _handleTouchCancel(e) {
    this.gestureActive = false;
    this.touches = [];
    this._hideSwipeIndicator();
  }

  _handleSwipe() {
    const deltaX = this.touchEndX - this.touchStartX;
    const deltaY = this.touchEndY - this.touchStartY;
    const absDeltaX = Math.abs(deltaX);
    const absDeltaY = Math.abs(deltaY);
    
    // Determine swipe direction
    if (Math.max(absDeltaX, absDeltaY) < this.options.swipeThreshold) {
      return; // Not a swipe, just a tap
    }
    
    if (absDeltaX > absDeltaY) {
      // Horizontal swipe
      if (deltaX > 0) {
        this._onSwipeRight();
      } else {
        this._onSwipeLeft();
      }
    } else {
      // Vertical swipe
      if (deltaY > 0) {
        this._onSwipeDown();
      } else {
        this._onSwipeUp();
      }
    }
  }

  _onSwipeRight() {
    console.log('[Gesture] Swipe right');
    const currentMode = this.dynamicUI.getCurrentMode();
    
    if (currentMode !== 'avatar') {
      // Go back to avatar on swipe right
      this.dynamicUI.backToAvatar();
      this._showGestureFeedback('← Back to Avatar');
    }
  }

  _onSwipeLeft() {
    console.log('[Gesture] Swipe left');
    // Cycle through modes on swipe left
    const modes = ['avatar', 'desktop', 'terminal', 'browser'];
    const currentMode = this.dynamicUI.getCurrentMode();
    const currentIndex = modes.indexOf(currentMode);
    const nextMode = modes[(currentIndex + 1) % modes.length];
    
    this._cycleModes(nextMode);
  }

  _onSwipeUp() {
    console.log('[Gesture] Swipe up');
    // Show recent files or search
    if (this.dynamicUI.getCurrentMode() === 'avatar') {
      this.dynamicUI.showDesktop([], '/home');
      this._showGestureFeedback('↑ Opening Files');
    }
  }

  _onSwipeDown() {
    console.log('[Gesture] Swipe down');
    // Return to avatar or close current view
    if (this.dynamicUI.getCurrentMode() !== 'avatar') {
      this.dynamicUI.backToAvatar();
      this._showGestureFeedback('↓ Closing View');
    }
  }

  _handleDoubleTap(touch) {
    console.log('[Gesture] Double tap');
    
    const currentMode = this.dynamicUI.getCurrentMode();
    
    if (currentMode === 'avatar') {
      // Double tap on avatar opens terminal
      this.dynamicUI.showTerminal('Terminal opened via double-tap');
      this._showGestureFeedback('Terminal Activated');
    } else {
      // Double tap in other modes returns to avatar
      this.dynamicUI.backToAvatar();
      this._showGestureFeedback('Back to Avatar');
    }
  }

  _handlePinch(scale) {
    console.log('[Gesture] Pinch', scale);
    
    if (scale > 1.2) {
      // Pinch out - zoom in or expand
      this._showGestureFeedback('Zoom In');
      this._emitGesture('pinchOut', { scale });
    } else if (scale < 0.8) {
      // Pinch in - zoom out or minimize
      this._showGestureFeedback('Zoom Out');
      this._emitGesture('pinchIn', { scale });
    }
  }

  _cycleModes(targetMode) {
    const modeNames = {
      'avatar': 'Avatar',
      'desktop': 'Files',
      'terminal': 'Terminal',
      'browser': 'Browser'
    };
    
    if (targetMode === 'desktop') {
      this.dynamicUI.showDesktop([], '/home');
    } else if (targetMode === 'terminal') {
      this.dynamicUI.showTerminal();
    } else if (targetMode === 'browser') {
      this.dynamicUI.showBrowser('about:blank');
    } else {
      this.dynamicUI.backToAvatar();
    }
    
    this._showGestureFeedback(`→ ${modeNames[targetMode]}`);
  }

  _getPinchDistance(touches) {
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  _showSwipeIndicator() {
    // Visual feedback during swipe
    const deltaX = this.touchEndX - this.touchStartX;
    const deltaY = this.touchEndY - this.touchStartY;
    
    // You could add a visual line or arrow here
    // For now, just emit event
    this._emitGesture('swipeProgress', { deltaX, deltaY });
  }

  _hideSwipeIndicator() {
    this._emitGesture('swipeEnd', {});
  }

  _showGestureFeedback(message) {
    // Create or update feedback element
    let feedback = document.getElementById('gesture-feedback');
    if (!feedback) {
      feedback = document.createElement('div');
      feedback.id = 'gesture-feedback';
      feedback.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0, 255, 255, 0.9);
        color: #000;
        padding: 20px 40px;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        font-size: 1.2em;
        font-weight: bold;
        z-index: 10000;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.3s ease;
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.6);
      `;
      document.body.appendChild(feedback);
    }
    
    feedback.textContent = message;
    feedback.style.opacity = '1';
    
    setTimeout(() => {
      feedback.style.opacity = '0';
    }, 1500);
  }

  _addMobileStyles() {
    const style = document.createElement('style');
    style.textContent = `
      /* Mobile-specific styles */
      @media (max-width: 768px) {
        .ui-mode-container {
          font-size: 14px !important;
        }
        
        .file-item {
          min-width: 80px !important;
        }
        
        .ui-btn, .doc-btn, button {
          padding: 12px 20px !important;
          font-size: 1em !important;
          min-height: 44px !important;
        }
        
        .mode-badge {
          font-size: 0.75em !important;
          padding: 6px 12px !important;
        }
        
        .voice-indicator {
          width: 50px !important;
          height: 50px !important;
          bottom: 20px !important;
          right: 20px !important;
        }
        
        /* Make scrollable areas easier to use on mobile */
        .ui-mode-container {
          -webkit-overflow-scrolling: touch;
        }
        
        /* Larger touch targets */
        .file-item {
          padding: 20px !important;
        }
        
        /* Prevent text selection during gestures */
        .ui-mode-container {
          -webkit-user-select: none;
          user-select: none;
        }
      }
      
      /* Landscape mode adjustments */
      @media (max-width: 896px) and (orientation: landscape) {
        .avatar-section {
          height: 400px !important;
        }
        
        .mode-badge {
          top: 10px !important;
          right: 10px !important;
        }
      }
      
      /* Extra small devices */
      @media (max-width: 375px) {
        .ui-mode-container {
          font-size: 12px !important;
        }
        
        .file-grid {
          grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)) !important;
          gap: 10px !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  _emitGesture(name, data) {
    const event = new CustomEvent(`gesture:${name}`, { detail: data });
    window.dispatchEvent(event);
  }

  // Public methods for programmatic gesture triggering
  
  enableGestures() {
    this.gesturesEnabled = true;
    console.log('[MobileGestures] Gestures enabled');
  }

  disableGestures() {
    this.gesturesEnabled = false;
    console.log('[MobileGestures] Gestures disabled');
  }

  isGesturesEnabled() {
    return this.gesturesEnabled;
  }

  isMobileDevice() {
    return this.isMobile;
  }

  isTouchDevice() {
    return this.isTouch;
  }

  // Create gesture help overlay
  showGestureHelp() {
    const help = document.createElement('div');
    help.id = 'gesture-help';
    help.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.95);
      z-index: 10001;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      padding: 20px;
      color: #00ffff;
      font-family: 'Courier New', monospace;
    `;
    
    help.innerHTML = `
      <h2 style="margin-bottom: 30px; font-size: 1.8em;">Gesture Controls</h2>
      
      <div style="max-width: 400px; line-height: 2;">
        <div style="margin-bottom: 20px;">
          <strong>← Swipe Right:</strong> Back to Avatar
        </div>
        <div style="margin-bottom: 20px;">
          <strong>→ Swipe Left:</strong> Next Mode
        </div>
        <div style="margin-bottom: 20px;">
          <strong>↑ Swipe Up:</strong> Open Files
        </div>
        <div style="margin-bottom: 20px;">
          <strong>↓ Swipe Down:</strong> Close View
        </div>
        <div style="margin-bottom: 20px;">
          <strong>👆👆 Double Tap:</strong> Toggle Terminal
        </div>
        <div style="margin-bottom: 20px;">
          <strong>🤏 Pinch Out:</strong> Zoom In
        </div>
        <div style="margin-bottom: 20px;">
          <strong>🤏 Pinch In:</strong> Zoom Out
        </div>
      </div>
      
      <button id="close-gesture-help" style="
        margin-top: 40px;
        padding: 15px 40px;
        background: rgba(0, 255, 255, 0.2);
        border: 2px solid #00ffff;
        color: #00ffff;
        font-family: 'Courier New', monospace;
        font-size: 1.1em;
        cursor: pointer;
        border-radius: 8px;
      ">Got it!</button>
    `;
    
    document.body.appendChild(help);
    
    document.getElementById('close-gesture-help').addEventListener('click', () => {
      help.remove();
    });
  }
}

// Make available globally
if (typeof window !== 'undefined') {
  window.MobileGestureHandler = MobileGestureHandler;
}

export { MobileGestureHandler };
