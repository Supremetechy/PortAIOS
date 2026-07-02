/**
 * PortAIOS Integration Loader
 * ============================
 * Loads and initializes all OS integration components
 */

(function() {
  'use strict';
  
  console.log('[PortAIOS] Loading OS Integration...');
  
  // Wait for Eel to be available
  function waitForEel(callback, timeout = 10000) {
    const startTime = Date.now();
    
    function check() {
      if (typeof eel !== 'undefined' && !window.__eelMissing) {
        callback();
      } else if (Date.now() - startTime > timeout) {
        console.warn('[PortAIOS] Eel not available, running in limited mode');
        callback();
      } else {
        setTimeout(check, 100);
      }
    }
    
    check();
  }
  
  // Initialize OS components
  waitForEel(async function() {
    console.log('[PortAIOS] Eel ready, initializing OS components...');
    
    // System Tray is auto-initialized
    if (window.osSystemTray) {
      console.log('[PortAIOS] ✓ System Tray initialized');
      
      // Show welcome notification
      setTimeout(() => {
        window.osSystemTray.addNotification(
          'PortAIOS Ready',
          'Vertically integrated operating system is now active',
          'success'
        );
      }, 1000);
    }
    
    // Setup custom events for OS integration
    window.addEventListener('os-switch-mode', (e) => {
      const mode = e.detail;
      if (window.dynamicUI) {
        window.dynamicUI.switchMode(mode);
      } else {
        // Fallback to dock buttons
        const btn = document.getElementById(`btn-${mode}`);
        if (btn) btn.click();
      }
    });
    
    window.addEventListener('os-open-process-manager', () => {
      // Switch to dashboard and show process manager
      if (window.dynamicUI) {
        window.dynamicUI.showDashboard();
      }
      // TODO: Open process manager in app launcher
    });
    
    // Enhanced dock button behavior
    function enhanceDockButtons() {
      const dockButtons = {
        'btn-avatar': { mode: 'avatar', label: 'Avatar' },
        'btn-dashboard': { mode: 'dashboard', label: 'Dashboard' },
        'btn-desktop': { mode: 'desktop', label: 'Files' },
        'btn-browser': { mode: 'browser', label: 'Browser' },
        'btn-terminal': { mode: 'terminal', label: 'Terminal' },
        'btn-document': { mode: 'document', label: 'Documents' }
      };
      
      Object.entries(dockButtons).forEach(([id, config]) => {
        const btn = document.getElementById(id);
        if (btn) {
          // Add tooltip
          btn.title = config.label;
          
          // Add keyboard shortcut hints
          const shortcuts = {
            'dashboard': 'Ctrl+D',
            'desktop': 'Ctrl+F',
            'browser': 'Ctrl+B',
            'terminal': 'Ctrl+T'
          };
          
          if (shortcuts[config.mode]) {
            btn.title += ` (${shortcuts[config.mode]})`;
          }
        }
      });
    }
    
    enhanceDockButtons();
    
    // Global keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey || e.metaKey) {
        const shortcuts = {
          'd': 'dashboard',
          'f': 'desktop',
          'b': 'browser',
          't': 'terminal'
        };
        
        const mode = shortcuts[e.key.toLowerCase()];
        if (mode) {
          e.preventDefault();
          window.dispatchEvent(new CustomEvent('os-switch-mode', { detail: mode }));
        }
      }
      
      // Escape to return to avatar
      if (e.key === 'Escape') {
        window.dispatchEvent(new CustomEvent('os-switch-mode', { detail: 'avatar' }));
      }
    });
    
    // Enhanced file operations
    window.portAIOS = window.portAIOS || {};
    
    window.portAIOS.openFile = async function(path) {
      try {
        const result = await eel.os_open_file(path)();
        if (result.success) {
          window.osSystemTray?.addNotification(
            'File Opened',
            `Opened ${path.split('/').pop()}`,
            'success'
          );
        } else {
          window.osSystemTray?.addNotification(
            'Error',
            result.error || 'Failed to open file',
            'error'
          );
        }
        return result;
      } catch (error) {
        console.error('Error opening file:', error);
        return { success: false, error: error.message };
      }
    };
    
    window.portAIOS.launchApp = async function(appPath) {
      try {
        const result = await eel.os_launch_application(appPath)();
        if (result.success) {
          window.osSystemTray?.addNotification(
            'Application Launched',
            `Started ${appPath.split('/').pop()}`,
            'success'
          );
        } else {
          window.osSystemTray?.addNotification(
            'Error',
            result.error || 'Failed to launch application',
            'error'
          );
        }
        return result;
      } catch (error) {
        console.error('Error launching app:', error);
        return { success: false, error: error.message };
      }
    };
    
    window.portAIOS.getSystemInfo = async function() {
      try {
        return await eel.os_get_system_info()();
      } catch (error) {
        console.error('Error getting system info:', error);
        return { success: false, error: error.message };
      }
    };
    
    console.log('[PortAIOS] ✓ OS Integration complete');
    console.log('[PortAIOS] Available APIs:', Object.keys(window.portAIOS));
    
    // Dispatch ready event
    window.dispatchEvent(new Event('portaios-ready'));
  });
  
})();
