/**
 * PortAIOS System Tray & Notifications
 * =====================================
 * System tray with notifications, quick settings, and system status
 */

class OSSystemTray {
  constructor() {
    this.notifications = [];
    this.systemInfo = null;
    this.updateInterval = null;
    
    this.init();
  }
  
  async init() {
    this.render();
    this.setupEventListeners();
    await this.updateSystemInfo();
    this.startAutoUpdate();
  }
  
  render() {
    // Create tray container if not exists
    let tray = document.getElementById('os-system-tray');
    if (!tray) {
      tray = document.createElement('div');
      tray.id = 'os-system-tray';
      document.body.appendChild(tray);
    }
    
    tray.innerHTML = `
      <div class="system-tray">
        <!-- Tray Icons -->
        <div class="tray-icons">
          <div class="tray-icon" id="notifications-icon" title="Notifications">
            🔔
            <span class="notification-badge" id="notification-badge" style="display: none;">0</span>
          </div>
          <div class="tray-icon" id="system-icon" title="System">
            ⚙️
          </div>
          <div class="tray-icon system-stats">
            <span id="cpu-indicator" title="CPU Usage">⚡ --</span>
            <span id="mem-indicator" title="Memory Usage">💾 --</span>
          </div>
          <div class="tray-icon" id="time-display">--:--</div>
        </div>
        
        <!-- Notification Center -->
        <div class="notification-center" id="notification-center" style="display: none;">
          <div class="notification-header">
            <h3>Notifications</h3>
            <div class="notification-actions">
              <button class="notification-btn" id="clear-all-notifications">Clear All</button>
              <button class="close-panel-btn" id="close-notifications">✕</button>
            </div>
          </div>
          <div class="notification-list" id="notification-list">
            <div class="no-notifications">No notifications</div>
          </div>
        </div>
        
        <!-- System Panel -->
        <div class="system-panel" id="system-panel" style="display: none;">
          <div class="system-panel-header">
            <h3>System</h3>
            <button class="close-panel-btn" id="close-system-panel">✕</button>
          </div>
          
          <div class="system-info" id="system-info-display"></div>
          
          <div class="quick-settings">
            <h4>Quick Settings</h4>
            <div class="settings-grid">
              <button class="setting-btn" id="toggle-theme">
                <span class="setting-icon">🌙</span>
                <span class="setting-label">Dark Mode</span>
              </button>
              <button class="setting-btn" id="open-file-manager">
                <span class="setting-icon">📁</span>
                <span class="setting-label">Files</span>
              </button>
              <button class="setting-btn" id="open-terminal">
                <span class="setting-icon">⚫</span>
                <span class="setting-label">Terminal</span>
              </button>
              <button class="setting-btn" id="open-task-manager">
                <span class="setting-icon">⚙️</span>
                <span class="setting-label">Processes</span>
              </button>
            </div>
          </div>
          
          <div class="power-options">
            <button class="power-btn" id="restart-btn">🔄 Restart</button>
            <button class="power-btn" id="shutdown-btn">⏻ Shutdown</button>
          </div>
        </div>
      </div>
      
      <!-- Toast Notifications -->
      <div class="toast-container" id="toast-container"></div>
    `;
    
    this.injectStyles();
  }
  
  injectStyles() {
    if (document.getElementById('os-system-tray-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'os-system-tray-styles';
    style.textContent = `
      .system-tray {
        position: fixed;
        top: 12px;
        right: 12px;
        z-index: 9999;
      }
      
      .tray-icons {
        display: flex;
        gap: 8px;
        align-items: center;
        background: rgba(42, 42, 42, 0.95);
        backdrop-filter: blur(10px);
        border: 1px solid #4a4a4a;
        border-radius: 8px;
        padding: 8px 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      }
      
      .tray-icon {
        position: relative;
        cursor: pointer;
        font-size: 16px;
        padding: 4px 8px;
        border-radius: 4px;
        transition: background 0.2s;
        color: #e0e0e0;
      }
      
      .tray-icon:hover {
        background: rgba(0, 255, 136, 0.1);
      }
      
      .system-stats {
        display: flex;
        gap: 8px;
        font-size: 12px;
        font-family: 'Courier New', monospace;
        cursor: default;
      }
      
      .notification-badge {
        position: absolute;
        top: -4px;
        right: -4px;
        background: #ff4444;
        color: white;
        font-size: 10px;
        padding: 2px 5px;
        border-radius: 10px;
        font-weight: 600;
      }
      
      #time-display {
        font-family: 'Courier New', monospace;
        font-size: 13px;
        min-width: 50px;
        text-align: center;
      }
      
      /* Notification Center */
      .notification-center, .system-panel {
        position: fixed;
        top: 60px;
        right: 12px;
        width: 360px;
        max-height: 600px;
        background: rgba(42, 42, 42, 0.98);
        backdrop-filter: blur(20px);
        border: 1px solid #4a4a4a;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        animation: slideDown 0.2s ease-out;
      }
      
      @keyframes slideDown {
        from {
          opacity: 0;
          transform: translateY(-10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
      
      .notification-header, .system-panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        border-bottom: 1px solid #3a3a3a;
      }
      
      .notification-header h3, .system-panel-header h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: #e0e0e0;
      }
      
      .notification-actions {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      
      .notification-btn {
        background: #3a3a3a;
        border: 1px solid #4a4a4a;
        color: #e0e0e0;
        padding: 4px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
        transition: all 0.2s;
      }
      
      .notification-btn:hover {
        background: #4a4a4a;
        border-color: #00ff88;
      }
      
      .close-panel-btn {
        background: none;
        border: none;
        color: #888;
        font-size: 18px;
        cursor: pointer;
        padding: 4px;
      }
      
      .close-panel-btn:hover {
        color: #e0e0e0;
      }
      
      .notification-list {
        flex: 1;
        overflow-y: auto;
        padding: 8px;
      }
      
      .no-notifications {
        text-align: center;
        padding: 40px 20px;
        color: #888;
        font-size: 14px;
      }
      
      .notification-item {
        background: #2a2a2a;
        border: 1px solid #3a3a3a;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        transition: all 0.2s;
        cursor: pointer;
      }
      
      .notification-item:hover {
        background: #333;
        border-color: #00ff88;
      }
      
      .notification-item.unread {
        border-left: 3px solid #00ff88;
      }
      
      .notification-title {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 4px;
        color: #e0e0e0;
      }
      
      .notification-message {
        font-size: 13px;
        color: #aaa;
        margin-bottom: 4px;
      }
      
      .notification-time {
        font-size: 11px;
        color: #666;
      }
      
      .notification-actions-inline {
        margin-top: 8px;
        display: flex;
        gap: 8px;
      }
      
      .notification-action-btn {
        background: #3a3a3a;
        border: 1px solid #4a4a4a;
        color: #e0e0e0;
        padding: 4px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 11px;
        transition: all 0.2s;
      }
      
      .notification-action-btn:hover {
        background: #00ff88;
        color: #1a1a1a;
        border-color: #00ff88;
      }
      
      /* System Panel */
      .system-info {
        padding: 16px;
        border-bottom: 1px solid #3a3a3a;
      }
      
      .info-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        font-size: 13px;
        border-bottom: 1px solid #2a2a2a;
      }
      
      .info-row:last-child {
        border-bottom: none;
      }
      
      .info-label {
        color: #888;
      }
      
      .info-value {
        color: #e0e0e0;
        font-family: 'Courier New', monospace;
      }
      
      .quick-settings {
        padding: 16px;
        border-bottom: 1px solid #3a3a3a;
      }
      
      .quick-settings h4 {
        margin: 0 0 12px 0;
        font-size: 14px;
        font-weight: 600;
        color: #888;
      }
      
      .settings-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
      }
      
      .setting-btn {
        background: #2a2a2a;
        border: 1px solid #3a3a3a;
        border-radius: 8px;
        padding: 16px;
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
      }
      
      .setting-btn:hover {
        background: #333;
        border-color: #00ff88;
        transform: translateY(-2px);
      }
      
      .setting-icon {
        font-size: 24px;
      }
      
      .setting-label {
        font-size: 12px;
        color: #e0e0e0;
      }
      
      .power-options {
        padding: 16px;
        display: flex;
        gap: 8px;
      }
      
      .power-btn {
        flex: 1;
        background: #3a3a3a;
        border: 1px solid #4a4a4a;
        color: #e0e0e0;
        padding: 12px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 13px;
        font-weight: 600;
        transition: all 0.2s;
      }
      
      .power-btn:hover {
        background: #4a4a4a;
        border-color: #00ff88;
      }
      
      /* Toast Notifications */
      .toast-container {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 10000;
        display: flex;
        flex-direction: column;
        gap: 8px;
        max-width: 360px;
      }
      
      .toast {
        background: rgba(42, 42, 42, 0.98);
        backdrop-filter: blur(20px);
        border: 1px solid #4a4a4a;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        animation: slideIn 0.3s ease-out;
        cursor: pointer;
      }
      
      @keyframes slideIn {
        from {
          opacity: 0;
          transform: translateX(100%);
        }
        to {
          opacity: 1;
          transform: translateX(0);
        }
      }
      
      .toast.success {
        border-left: 3px solid #00ff88;
      }
      
      .toast.error {
        border-left: 3px solid #ff4444;
      }
      
      .toast.warning {
        border-left: 3px solid #ffaa00;
      }
      
      .toast.info {
        border-left: 3px solid #00aaff;
      }
      
      .toast-title {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 4px;
        color: #e0e0e0;
      }
      
      .toast-message {
        font-size: 13px;
        color: #aaa;
      }
      
      /* Scrollbar */
      .notification-list::-webkit-scrollbar {
        width: 6px;
      }
      
      .notification-list::-webkit-scrollbar-track {
        background: #1a1a1a;
      }
      
      .notification-list::-webkit-scrollbar-thumb {
        background: #4a4a4a;
        border-radius: 3px;
      }
    `;
    document.head.appendChild(style);
  }
  
  setupEventListeners() {
    // Toggle notification center
    document.getElementById('notifications-icon')?.addEventListener('click', () => {
      this.togglePanel('notification-center');
    });
    
    // Toggle system panel
    document.getElementById('system-icon')?.addEventListener('click', () => {
      this.togglePanel('system-panel');
    });
    
    // Close panels
    document.getElementById('close-notifications')?.addEventListener('click', () => {
      document.getElementById('notification-center').style.display = 'none';
    });
    
    document.getElementById('close-system-panel')?.addEventListener('click', () => {
      document.getElementById('system-panel').style.display = 'none';
    });
    
    // Clear all notifications
    document.getElementById('clear-all-notifications')?.addEventListener('click', () => {
      this.clearAllNotifications();
    });
    
    // Quick settings
    document.getElementById('open-file-manager')?.addEventListener('click', () => {
      window.dispatchEvent(new CustomEvent('os-switch-mode', { detail: 'desktop' }));
      this.togglePanel('system-panel');
    });
    
    document.getElementById('open-terminal')?.addEventListener('click', () => {
      window.dispatchEvent(new CustomEvent('os-switch-mode', { detail: 'terminal' }));
      this.togglePanel('system-panel');
    });
    
    document.getElementById('open-task-manager')?.addEventListener('click', () => {
      window.dispatchEvent(new CustomEvent('os-open-process-manager'));
      this.togglePanel('system-panel');
    });
    
    // Update time every second
    setInterval(() => this.updateTime(), 1000);
    this.updateTime();
    
    // Close panels when clicking outside
    document.addEventListener('click', (e) => {
      const tray = document.querySelector('.system-tray');
      if (!tray?.contains(e.target)) {
        document.getElementById('notification-center').style.display = 'none';
        document.getElementById('system-panel').style.display = 'none';
      }
    });
  }
  
  togglePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    
    // Close other panels
    const panels = ['notification-center', 'system-panel'];
    panels.forEach(id => {
      if (id !== panelId) {
        document.getElementById(id).style.display = 'none';
      }
    });
    
    // Toggle this panel
    const isVisible = panel.style.display !== 'none';
    panel.style.display = isVisible ? 'none' : 'flex';
    
    // Update content
    if (panelId === 'system-panel' && !isVisible) {
      this.renderSystemInfo();
    }
  }
  
  async updateSystemInfo() {
    try {
      this.systemInfo = await eel.os_get_system_info()();
      this.updateStatusIndicators();
    } catch (error) {
      console.error('Failed to update system info:', error);
    }
  }
  
  updateStatusIndicators() {
    if (!this.systemInfo || !this.systemInfo.success) return;
    
    const cpuIndicator = document.getElementById('cpu-indicator');
    const memIndicator = document.getElementById('mem-indicator');
    
    if (cpuIndicator) {
      cpuIndicator.textContent = `⚡ ${this.systemInfo.cpu.percent.toFixed(0)}%`;
      cpuIndicator.title = `CPU Usage: ${this.systemInfo.cpu.percent.toFixed(1)}%`;
    }
    
    if (memIndicator) {
      memIndicator.textContent = `💾 ${this.systemInfo.memory.percent.toFixed(0)}%`;
      memIndicator.title = `Memory Usage: ${this.systemInfo.memory.percent.toFixed(1)}%`;
    }
  }
  
  renderSystemInfo() {
    if (!this.systemInfo || !this.systemInfo.success) return;
    
    const container = document.getElementById('system-info-display');
    if (!container) return;
    
    const info = this.systemInfo;
    container.innerHTML = `
      <div class="info-row">
        <span class="info-label">OS</span>
        <span class="info-value">${info.system.os}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Hostname</span>
        <span class="info-value">${info.system.hostname}</span>
      </div>
      <div class="info-row">
        <span class="info-label">CPU</span>
        <span class="info-value">${info.cpu.count_logical} cores @ ${info.cpu.percent.toFixed(1)}%</span>
      </div>
      <div class="info-row">
        <span class="info-label">Memory</span>
        <span class="info-value">${info.memory.used_gb.toFixed(1)} / ${info.memory.total_gb.toFixed(1)} GB</span>
      </div>
      <div class="info-row">
        <span class="info-label">Disk</span>
        <span class="info-value">${info.disk.used_gb.toFixed(1)} / ${info.disk.total_gb.toFixed(1)} GB</span>
      </div>
    `;
  }
  
  updateTime() {
    const timeDisplay = document.getElementById('time-display');
    if (timeDisplay) {
      const now = new Date();
      timeDisplay.textContent = now.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
    }
  }
  
  startAutoUpdate() {
    this.updateInterval = setInterval(() => {
      this.updateSystemInfo();
    }, 5000); // Update every 5 seconds
  }
  
  addNotification(title, message, type = 'info', actions = []) {
    const notification = {
      id: Date.now(),
      title,
      message,
      type,
      actions,
      time: new Date().toISOString(),
      read: false
    };
    
    this.notifications.unshift(notification);
    this.updateNotificationBadge();
    this.renderNotifications();
    this.showToast(title, message, type);
    
    return notification.id;
  }
  
  renderNotifications() {
    const container = document.getElementById('notification-list');
    if (!container) return;
    
    if (this.notifications.length === 0) {
      container.innerHTML = '<div class="no-notifications">No notifications</div>';
      return;
    }
    
    container.innerHTML = this.notifications.map(n => `
      <div class="notification-item ${n.read ? '' : 'unread'}" data-id="${n.id}">
        <div class="notification-title">${n.title}</div>
        <div class="notification-message">${n.message}</div>
        <div class="notification-time">${this.formatTime(n.time)}</div>
        ${n.actions.length > 0 ? `
          <div class="notification-actions-inline">
            ${n.actions.map(a => `
              <button class="notification-action-btn" data-action="${a.action}">${a.label}</button>
            `).join('')}
          </div>
        ` : ''}
      </div>
    `).join('');
    
    // Add click handlers
    container.querySelectorAll('.notification-item').forEach(item => {
      item.addEventListener('click', () => {
        this.markAsRead(parseInt(item.dataset.id));
      });
    });
  }
  
  markAsRead(id) {
    const notification = this.notifications.find(n => n.id === id);
    if (notification) {
      notification.read = true;
      this.updateNotificationBadge();
      this.renderNotifications();
    }
  }
  
  clearAllNotifications() {
    this.notifications = [];
    this.updateNotificationBadge();
    this.renderNotifications();
  }
  
  updateNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    if (!badge) return;
    
    const unreadCount = this.notifications.filter(n => !n.read).length;
    
    if (unreadCount > 0) {
      badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
      badge.style.display = 'block';
    } else {
      badge.style.display = 'none';
    }
  }
  
  showToast(title, message, type = 'info', duration = 5000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after duration
    setTimeout(() => {
      toast.style.animation = 'slideIn 0.3s ease-out reverse';
      setTimeout(() => toast.remove(), 300);
    }, duration);
    
    // Click to dismiss
    toast.addEventListener('click', () => {
      toast.style.animation = 'slideIn 0.3s ease-out reverse';
      setTimeout(() => toast.remove(), 300);
    });
  }
  
  formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }
  
  destroy() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }
  }
}

// Create global instance
window.osSystemTray = new OSSystemTray();

// Export
window.OSSystemTray = OSSystemTray;
