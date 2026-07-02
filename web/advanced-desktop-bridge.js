/**
 * Advanced Desktop Features Bridge
 * Provides clipboard, screenshot, and notification access via voice commands
 */

class AdvancedDesktopBridge {
  constructor(options = {}) {
    this.options = {
      enableClipboard: true,
      enableScreenshots: true,
      enableNotifications: true,
      ...options
    };

    this.isEelAvailable = typeof eel !== 'undefined';
  }

  // ============ CLIPBOARD OPERATIONS ============

  async getClipboard() {
    if (!this.isEelAvailable) {
      console.warn('[AdvancedDesktop] Backend not available - clipboard access disabled');
      return { success: false, error: 'Backend not available' };
    }

    try {
      const result = await eel.get_clipboard()();
      return result;
    } catch (error) {
      console.error('[AdvancedDesktop] Error getting clipboard:', error);
      return { success: false, error: error.message };
    }
  }

  async setClipboard(text) {
    if (!this.isEelAvailable) {
      console.warn('[AdvancedDesktop] Backend not available - clipboard access disabled');
      return { success: false, error: 'Backend not available' };
    }

    try {
      const result = await eel.set_clipboard(text)();
      return result;
    } catch (error) {
      console.error('[AdvancedDesktop] Error setting clipboard:', error);
      return { success: false, error: error.message };
    }
  }

  async copyToClipboard(text) {
    return await this.setClipboard(text);
  }

  async pasteFromClipboard() {
    const result = await this.getClipboard();
    return result.success ? result.text : '';
  }

  // ============ SCREENSHOT OPERATIONS ============

  async takeScreenshot(savePath = null) {
    if (!this.isEelAvailable) {
      console.warn('[AdvancedDesktop] Backend not available - screenshot disabled');
      return { success: false, error: 'Backend not available' };
    }

    try {
      const result = await eel.take_screenshot(savePath)();
      return result;
    } catch (error) {
      console.error('[AdvancedDesktop] Error taking screenshot:', error);
      return { success: false, error: error.message };
    }
  }

  async takeWindowScreenshot(windowTitle = null) {
    if (!this.isEelAvailable) {
      console.warn('[AdvancedDesktop] Backend not available - screenshot disabled');
      return { success: false, error: 'Backend not available' };
    }

    try {
      const result = await eel.take_window_screenshot(windowTitle)();
      return result;
    } catch (error) {
      console.error('[AdvancedDesktop] Error taking window screenshot:', error);
      return { success: false, error: error.message };
    }
  }

  // ============ NOTIFICATION OPERATIONS ============

  async sendNotification(title, message, timeout = 5000) {
    if (!this.isEelAvailable) {
      // Fallback to browser notifications
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, { body: message });
        return { success: true, fallback: 'browser' };
      }
      return { success: false, error: 'No notification backend available' };
    }

    try {
      const result = await eel.send_notification(title, message, timeout)();
      return result;
    } catch (error) {
      console.error('[AdvancedDesktop] Error sending notification:', error);
      return { success: false, error: error.message };
    }
  }

  async requestNotificationPermission() {
    if ('Notification' in window && Notification.permission !== 'granted') {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }
    return Notification.permission === 'granted';
  }

  // ============ WINDOW OPERATIONS ============

  async getActiveWindow() {
    if (!this.isEelAvailable) {
      console.warn('[AdvancedDesktop] Backend not available - window info disabled');
      return { success: false, error: 'Backend not available' };
    }

    try {
      const result = await eel.get_active_window()();
      return result;
    } catch (error) {
      console.error('[AdvancedDesktop] Error getting active window:', error);
      return { success: false, error: error.message };
    }
  }

  // ============ VOICE COMMAND HANDLERS ============

  async handleVoiceCommand(command) {
    const cmd = command.toLowerCase().trim();

    // Clipboard commands
    if (cmd.includes('copy') || cmd.includes('clipboard')) {
      if (cmd.includes('get') || cmd.includes('paste') || cmd.includes('what')) {
        const result = await this.getClipboard();
        if (result.success) {
          await this.sendNotification('Clipboard', `Content: ${result.text.substring(0, 100)}...`);
          return true;
        }
      } else if (cmd.includes('set') || cmd.includes('copy')) {
        // Extract text to copy
        const match = cmd.match(/copy (.+)/);
        if (match) {
          const result = await this.setClipboard(match[1]);
          if (result.success) {
            await this.sendNotification('Clipboard', 'Text copied successfully');
            return true;
          }
        }
      }
    }

    // Screenshot commands
    if (cmd.includes('screenshot') || cmd.includes('capture screen')) {
      if (cmd.includes('window')) {
        const result = await this.takeWindowScreenshot();
        if (result.success) {
          await this.sendNotification('Screenshot', `Saved to: ${result.path}`);
          return true;
        }
      } else {
        const result = await this.takeScreenshot();
        if (result.success) {
          await this.sendNotification('Screenshot', `Saved to: ${result.path}`);
          return true;
        }
      }
    }

    // Notification test
    if (cmd.includes('test notification') || cmd === 'notify me') {
      await this.sendNotification('AIOS', 'Voice command notification test');
      return true;
    }

    // Window info
    if (cmd.includes('active window') || cmd.includes('current window')) {
      const result = await this.getActiveWindow();
      if (result.success) {
        const info = result.window || result.app || 'Unknown';
        await this.sendNotification('Active Window', info);
        return true;
      }
    }

    return false;
  }
}

// ES6 Export for module imports
export { AdvancedDesktopBridge };

// Global API for non-module scripts
if (typeof window !== 'undefined') {
  window.AIOS = window.AIOS || {};
  window.AIOS.AdvancedDesktopBridge = AdvancedDesktopBridge;
}
