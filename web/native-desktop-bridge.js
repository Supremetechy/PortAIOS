/**
 * Native Desktop Bridge for AIOS
 * Provides integration between the avatar display and native desktop features
 * Allows voice-controlled access to files, apps, browser, and system functions
 */

class NativeDesktopBridge {
  constructor(options = {}) {
    this.options = {
      enableFileSystem: true,
      enableBrowser: true,
      enableApps: true,
      enableDesktop: true,
      ...options
    };

    this.isEelAvailable = typeof eel !== 'undefined';
    this.currentView = 'avatar'; // avatar, desktop, browser, files, app
    this.viewHistory = [];
    
    // Callbacks
    this.onViewChange = options.onViewChange || (() => {});
    this.onFileOpen = options.onFileOpen || (() => {});
    this.onError = options.onError || ((error) => console.error('[Desktop]', error));
  }

  /**
   * Initialize the bridge and verify backend connection
   */
  async initialize() {
    console.log('[Desktop] Initializing native desktop bridge...');
    
    if (!this.isEelAvailable) {
      console.warn('[Desktop] Eel not available - running in web-only mode');
      return false;
    }

    try {
      // Test connection to backend
      const connected = await this.testBackendConnection();
      if (connected) {
        console.log('[Desktop] Backend connection established');
        return true;
      }
    } catch (error) {
      console.error('[Desktop] Failed to connect to backend:', error);
      this.onError({ type: 'connection_failed', message: error.message });
    }

    return false;
  }

  /**
   * Test if backend is available
   */
  async testBackendConnection() {
    if (!this.isEelAvailable) return false;
    
    try {
      // Try to call a simple backend function
      const response = await eel.get_system_info()();
      return !!response;
    } catch (error) {
      console.warn('[Desktop] Backend test failed:', error);
      return false;
    }
  }

  /**
   * Switch to desktop view showing files and folders
   */
  async showDesktop(path = null) {
    console.log('[Desktop] Showing desktop view:', path || 'default');
    
    try {
      const files = await this.listDirectory(path);
      this.currentView = 'desktop';
      this.viewHistory.push({ view: 'desktop', path });
      
      this.onViewChange({
        view: 'desktop',
        data: { files, path }
      });
      
      return files;
    } catch (error) {
      console.error('[Desktop] Failed to show desktop:', error);
      this.onError({ type: 'desktop_load_failed', message: error.message });
      return [];
    }
  }

  /**
   * List directory contents
   */
  async listDirectory(path = null) {
    if (!this.isEelAvailable) {
      // Return mock data for web-only mode
      return this.getMockFiles();
    }

    try {
      const result = await eel.list_directory(path || '')();
      return result.files || [];
    } catch (error) {
      console.error('[Desktop] Failed to list directory:', error);
      throw error;
    }
  }

  /**
   * Open a file or folder
   */
  async openPath(path) {
    console.log('[Desktop] Opening path:', path);
    
    if (!this.isEelAvailable) {
      console.warn('[Desktop] Cannot open path - backend not available');
      return false;
    }

    try {
      const result = await eel.open_file_or_folder(path)();
      this.onFileOpen({ path, success: result.success });
      return result.success;
    } catch (error) {
      console.error('[Desktop] Failed to open path:', error);
      this.onError({ type: 'file_open_failed', message: error.message, path });
      return false;
    }
  }

  /**
   * Show browser with URL
   */
  async showBrowser(url = 'about:blank') {
    console.log('[Desktop] Showing browser:', url);
    
    this.currentView = 'browser';
    this.viewHistory.push({ view: 'browser', url });
    
    this.onViewChange({
      view: 'browser',
      data: { url }
    });
  }

  /**
   * Launch an application
   */
  async launchApp(appName) {
    console.log('[Desktop] Launching app:', appName);
    
    if (!this.isEelAvailable) {
      console.warn('[Desktop] Cannot launch app - backend not available');
      return false;
    }

    try {
      const result = await eel.launch_application(appName)();
      return result.success;
    } catch (error) {
      console.error('[Desktop] Failed to launch app:', error);
      this.onError({ type: 'app_launch_failed', message: error.message, appName });
      return false;
    }
  }

  /**
   * Return to avatar view
   */
  returnToAvatar() {
    console.log('[Desktop] Returning to avatar view');
    
    this.currentView = 'avatar';
    this.onViewChange({
      view: 'avatar',
      data: {}
    });
  }

  /**
   * Go back to previous view
   */
  goBack() {
    if (this.viewHistory.length > 0) {
      const previousView = this.viewHistory.pop();
      console.log('[Desktop] Going back to:', previousView.view);
      
      switch (previousView.view) {
        case 'desktop':
          this.showDesktop(previousView.path);
          break;
        case 'browser':
          this.showBrowser(previousView.url);
          break;
        default:
          this.returnToAvatar();
      }
    } else {
      this.returnToAvatar();
    }
  }

  /**
   * Get current view state
   */
  getCurrentView() {
    return {
      view: this.currentView,
      history: this.viewHistory.length
    };
  }

  /**
   * Mock file data for web-only mode
   */
  getMockFiles() {
    return [
      { name: 'Documents', type: 'folder', path: '/home/user/Documents' },
      { name: 'Downloads', type: 'folder', path: '/home/user/Downloads' },
      { name: 'Pictures', type: 'folder', path: '/home/user/Pictures' },
      { name: 'example.txt', type: 'file', path: '/home/user/example.txt', size: 1024 },
      { name: 'notes.md', type: 'file', path: '/home/user/notes.md', size: 2048 }
    ];
  }

  /**
   * Voice command handlers
   */
  handleVoiceCommand(command) {
    const cmd = command.toLowerCase().trim();
    
    // Desktop navigation
    if (cmd.includes('show desktop') || cmd.includes('open desktop')) {
      return this.showDesktop();
    }
    
    if (cmd.includes('show files') || cmd.includes('open files')) {
      return this.showDesktop();
    }
    
    // Browser
    if (cmd.includes('open browser')) {
      const urlMatch = cmd.match(/open browser (.+)/);
      const url = urlMatch ? urlMatch[1] : 'about:blank';
      return this.showBrowser(url);
    }
    
    // App launching
    if (cmd.includes('launch') || cmd.includes('open app')) {
      const appMatch = cmd.match(/(?:launch|open app) (.+)/);
      if (appMatch) {
        return this.launchApp(appMatch[1]);
      }
    }
    
    // Navigation
    if (cmd === 'go back' || cmd === 'back') {
      return this.goBack();
    }
    
    if (cmd === 'return to avatar' || cmd === 'show avatar') {
      return this.returnToAvatar();
    }
    
    return false;
  }
}

// ES6 Export for module imports
export { NativeDesktopBridge };
