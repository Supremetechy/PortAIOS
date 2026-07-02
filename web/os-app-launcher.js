/**
 * PortAIOS Application Launcher & Manager
 * ========================================
 * Launch and manage system applications, processes, and recent apps
 */

class OSAppLauncher {
  constructor(container) {
    this.container = container;
    this.apps = [];
    this.processes = [];
    this.recentApps = [];
    this.categories = {};
    this.refreshInterval = null;
    
    this.init();
  }
  
  async init() {
    this.render();
    await this.loadApplications();
    this.startProcessMonitoring();
  }
  
  render() {
    this.container.innerHTML = `
      <div class="os-app-launcher">
        <!-- App Launcher View -->
        <div class="app-launcher-view" id="app-launcher-view">
          <div class="app-header">
            <h2>Applications</h2>
            <div class="app-actions">
              <input type="text" id="app-search" class="app-search" placeholder="Search applications...">
              <button class="app-btn" id="show-processes">⚙️ Processes</button>
            </div>
          </div>
          
          <div class="app-categories" id="app-categories"></div>
          
          <div class="app-grid" id="app-grid"></div>
          
          <div class="recent-apps">
            <h3>Recent</h3>
            <div class="recent-apps-list" id="recent-apps-list"></div>
          </div>
        </div>
        
        <!-- Process Manager View -->
        <div class="process-manager-view" id="process-manager-view" style="display: none;">
          <div class="process-header">
            <h2>Process Manager</h2>
            <div class="process-actions">
              <button class="app-btn" id="show-launcher">← Back to Apps</button>
              <button class="app-btn" id="refresh-processes">🔄 Refresh</button>
              <label class="process-toggle">
                <input type="checkbox" id="auto-refresh">
                <span>Auto-refresh</span>
              </label>
            </div>
          </div>
          
          <div class="process-stats" id="process-stats"></div>
          
          <div class="process-list">
            <div class="process-list-header">
              <div class="process-col process-name">Name</div>
              <div class="process-col process-pid">PID</div>
              <div class="process-col process-cpu">CPU %</div>
              <div class="process-col process-memory">Memory</div>
              <div class="process-col process-status">Status</div>
              <div class="process-col process-actions">Actions</div>
            </div>
            <div class="process-list-body" id="process-list"></div>
          </div>
        </div>
      </div>
    `;
    
    this.injectStyles();
    this.setupEventListeners();
  }
  
  injectStyles() {
    if (document.getElementById('os-app-launcher-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'os-app-launcher-styles';
    style.textContent = `
      .os-app-launcher {
        height: 100%;
        background: #1a1a1a;
        color: #e0e0e0;
        overflow: auto;
        padding: 24px;
      }
      
      /* App Launcher View */
      .app-header, .process-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
      }
      
      .app-header h2, .process-header h2 {
        margin: 0;
        font-size: 24px;
        font-weight: 600;
      }
      
      .app-actions, .process-actions {
        display: flex;
        gap: 12px;
        align-items: center;
      }
      
      .app-search {
        background: #2a2a2a;
        border: 1px solid #4a4a4a;
        color: #e0e0e0;
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 14px;
        width: 300px;
      }
      
      .app-search:focus {
        outline: none;
        border-color: #00ff88;
      }
      
      .app-btn {
        background: #3a3a3a;
        border: 1px solid #4a4a4a;
        color: #e0e0e0;
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.2s;
      }
      
      .app-btn:hover {
        background: #4a4a4a;
        border-color: #00ff88;
      }
      
      .app-categories {
        display: flex;
        gap: 8px;
        margin-bottom: 24px;
        flex-wrap: wrap;
      }
      
      .app-category-btn {
        background: #2a2a2a;
        border: 1px solid #4a4a4a;
        color: #888;
        padding: 8px 16px;
        border-radius: 20px;
        cursor: pointer;
        font-size: 13px;
        transition: all 0.2s;
      }
      
      .app-category-btn:hover,
      .app-category-btn.active {
        background: #00ff88;
        color: #1a1a1a;
        border-color: #00ff88;
      }
      
      .app-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 16px;
        margin-bottom: 32px;
      }
      
      .app-item {
        background: #2a2a2a;
        border: 2px solid transparent;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
        position: relative;
      }
      
      .app-item:hover {
        background: #3a3a3a;
        border-color: #00ff88;
        transform: translateY(-2px);
      }
      
      .app-icon {
        font-size: 48px;
        margin-bottom: 12px;
      }
      
      .app-name {
        font-size: 14px;
        font-weight: 500;
        margin-bottom: 4px;
      }
      
      .app-category {
        font-size: 11px;
        color: #888;
      }
      
      .recent-apps {
        margin-top: 32px;
      }
      
      .recent-apps h3 {
        font-size: 16px;
        margin-bottom: 12px;
        color: #888;
      }
      
      .recent-apps-list {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
      }
      
      .recent-app-item {
        background: #2a2a2a;
        border: 1px solid #4a4a4a;
        border-radius: 8px;
        padding: 12px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        cursor: pointer;
        transition: all 0.2s;
      }
      
      .recent-app-item:hover {
        background: #3a3a3a;
        border-color: #00ff88;
      }
      
      .recent-app-icon {
        font-size: 24px;
      }
      
      .recent-app-info {
        display: flex;
        flex-direction: column;
      }
      
      .recent-app-name {
        font-size: 14px;
        font-weight: 500;
      }
      
      .recent-app-time {
        font-size: 11px;
        color: #888;
      }
      
      /* Process Manager View */
      .process-toggle {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        cursor: pointer;
      }
      
      .process-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
      }
      
      .stat-card {
        background: #2a2a2a;
        border: 1px solid #4a4a4a;
        border-radius: 8px;
        padding: 16px;
      }
      
      .stat-label {
        font-size: 12px;
        color: #888;
        margin-bottom: 8px;
      }
      
      .stat-value {
        font-size: 24px;
        font-weight: 600;
        color: #00ff88;
      }
      
      .stat-bar {
        margin-top: 8px;
        height: 6px;
        background: #1a1a1a;
        border-radius: 3px;
        overflow: hidden;
      }
      
      .stat-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #00ff88, #00cc6a);
        transition: width 0.3s;
      }
      
      .process-list {
        background: #2a2a2a;
        border: 1px solid #4a4a4a;
        border-radius: 8px;
        overflow: hidden;
      }
      
      .process-list-header {
        display: grid;
        grid-template-columns: 2fr 0.8fr 0.8fr 1fr 0.8fr 0.8fr;
        background: #242424;
        border-bottom: 1px solid #4a4a4a;
        padding: 12px 16px;
        font-size: 12px;
        font-weight: 600;
        color: #888;
        text-transform: uppercase;
      }
      
      .process-list-body {
        max-height: 500px;
        overflow-y: auto;
      }
      
      .process-row {
        display: grid;
        grid-template-columns: 2fr 0.8fr 0.8fr 1fr 0.8fr 0.8fr;
        padding: 12px 16px;
        border-bottom: 1px solid #3a3a3a;
        font-size: 13px;
        align-items: center;
        transition: background 0.2s;
      }
      
      .process-row:hover {
        background: #333;
      }
      
      .process-col {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      
      .process-name {
        font-weight: 500;
      }
      
      .process-pid {
        color: #888;
        font-family: 'Courier New', monospace;
      }
      
      .process-cpu, .process-memory {
        font-family: 'Courier New', monospace;
      }
      
      .process-status {
        text-transform: capitalize;
      }
      
      .process-status.running {
        color: #00ff88;
      }
      
      .process-status.sleeping {
        color: #888;
      }
      
      .process-kill-btn {
        background: #ff4444;
        border: none;
        color: white;
        padding: 4px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 11px;
        transition: background 0.2s;
      }
      
      .process-kill-btn:hover {
        background: #ff6666;
      }
      
      /* Scrollbar */
      .os-app-launcher::-webkit-scrollbar,
      .process-list-body::-webkit-scrollbar {
        width: 8px;
      }
      
      .os-app-launcher::-webkit-scrollbar-track,
      .process-list-body::-webkit-scrollbar-track {
        background: #1a1a1a;
      }
      
      .os-app-launcher::-webkit-scrollbar-thumb,
      .process-list-body::-webkit-scrollbar-thumb {
        background: #4a4a4a;
        border-radius: 4px;
      }
      
      .os-app-launcher::-webkit-scrollbar-thumb:hover,
      .process-list-body::-webkit-scrollbar-thumb:hover {
        background: #5a5a5a;
      }
    `;
    document.head.appendChild(style);
  }
  
  setupEventListeners() {
    // Search
    document.getElementById('app-search')?.addEventListener('input', (e) => {
      this.filterApps(e.target.value);
    });
    
    // View switching
    document.getElementById('show-processes')?.addEventListener('click', () => {
      this.showProcessManager();
    });
    
    document.getElementById('show-launcher')?.addEventListener('click', () => {
      this.showAppLauncher();
    });
    
    // Process manager
    document.getElementById('refresh-processes')?.addEventListener('click', () => {
      this.loadProcesses();
    });
    
    document.getElementById('auto-refresh')?.addEventListener('change', (e) => {
      this.toggleAutoRefresh(e.target.checked);
    });
  }
  
  async loadApplications() {
    try {
      this.apps = await eel.os_get_applications()();
      this.categorizeApps();
      this.renderCategories();
      this.renderApps();
    } catch (error) {
      console.error('Failed to load applications:', error);
    }
  }
  
  categorizeApps() {
    this.categories = { 'All': this.apps };
    
    this.apps.forEach(app => {
      const category = app.category || 'Other';
      if (!this.categories[category]) {
        this.categories[category] = [];
      }
      this.categories[category].push(app);
    });
  }
  
  renderCategories() {
    const container = document.getElementById('app-categories');
    if (!container) return;
    
    const categoryNames = Object.keys(this.categories);
    container.innerHTML = categoryNames.map(cat => `
      <button class="app-category-btn ${cat === 'All' ? 'active' : ''}" data-category="${cat}">
        ${cat} (${this.categories[cat].length})
      </button>
    `).join('');
    
    // Add click handlers
    container.querySelectorAll('.app-category-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        container.querySelectorAll('.app-category-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.filterByCategory(btn.dataset.category);
      });
    });
  }
  
  renderApps(apps = null) {
    const container = document.getElementById('app-grid');
    if (!container) return;
    
    const appsToRender = apps || this.apps;
    
    if (appsToRender.length === 0) {
      container.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #888;">No applications found</p>';
      return;
    }
    
    container.innerHTML = appsToRender.map(app => `
      <div class="app-item" data-app='${JSON.stringify(app)}'>
        <div class="app-icon">${app.icon || '📦'}</div>
        <div class="app-name">${app.name}</div>
        <div class="app-category">${app.category || 'Application'}</div>
      </div>
    `).join('');
    
    // Add click handlers
    container.querySelectorAll('.app-item').forEach(item => {
      item.addEventListener('click', () => {
        const app = JSON.parse(item.dataset.app);
        this.launchApp(app);
      });
    });
  }
  
  async launchApp(app) {
    try {
      const command = app.command || app.path;
      const result = await eel.os_launch_application(command)();
      
      if (result.success) {
        this.addToRecent(app);
        this.showNotification(`Launched ${app.name}`, 'success');
      } else {
        this.showNotification(`Failed to launch ${app.name}: ${result.error}`, 'error');
      }
    } catch (error) {
      this.showNotification(`Error launching ${app.name}`, 'error');
      console.error('Launch error:', error);
    }
  }
  
  addToRecent(app) {
    // Remove if already exists
    this.recentApps = this.recentApps.filter(a => a.name !== app.name);
    
    // Add to beginning
    this.recentApps.unshift({
      ...app,
      launchedAt: new Date().toISOString()
    });
    
    // Keep only last 10
    this.recentApps = this.recentApps.slice(0, 10);
    
    this.renderRecentApps();
  }
  
  renderRecentApps() {
    const container = document.getElementById('recent-apps-list');
    if (!container) return;
    
    if (this.recentApps.length === 0) {
      container.innerHTML = '<p style="color: #888; font-size: 13px;">No recent applications</p>';
      return;
    }
    
    container.innerHTML = this.recentApps.map(app => `
      <div class="recent-app-item" data-app='${JSON.stringify(app)}'>
        <div class="recent-app-icon">${app.icon || '📦'}</div>
        <div class="recent-app-info">
          <div class="recent-app-name">${app.name}</div>
          <div class="recent-app-time">${this.formatTimeAgo(app.launchedAt)}</div>
        </div>
      </div>
    `).join('');
    
    // Add click handlers
    container.querySelectorAll('.recent-app-item').forEach(item => {
      item.addEventListener('click', () => {
        const app = JSON.parse(item.dataset.app);
        this.launchApp(app);
      });
    });
  }
  
  filterApps(query) {
    if (!query.trim()) {
      this.renderApps();
      return;
    }
    
    const filtered = this.apps.filter(app => 
      app.name.toLowerCase().includes(query.toLowerCase()) ||
      (app.category && app.category.toLowerCase().includes(query.toLowerCase()))
    );
    
    this.renderApps(filtered);
  }
  
  filterByCategory(category) {
    if (category === 'All') {
      this.renderApps();
    } else {
      this.renderApps(this.categories[category]);
    }
  }
  
  showAppLauncher() {
    document.getElementById('app-launcher-view').style.display = 'block';
    document.getElementById('process-manager-view').style.display = 'none';
    this.stopAutoRefresh();
  }
  
  async showProcessManager() {
    document.getElementById('app-launcher-view').style.display = 'none';
    document.getElementById('process-manager-view').style.display = 'block';
    await this.loadProcesses();
    await this.loadSystemStats();
  }
  
  async loadProcesses() {
    try {
      this.processes = await eel.os_get_processes(100)();
      this.renderProcesses();
    } catch (error) {
      console.error('Failed to load processes:', error);
    }
  }
  
  async loadSystemStats() {
    try {
      const stats = await eel.os_get_system_info()();
      if (!stats.success) return;
      
      const container = document.getElementById('process-stats');
      if (!container) return;
      
      container.innerHTML = `
        <div class="stat-card">
          <div class="stat-label">CPU Usage</div>
          <div class="stat-value">${stats.cpu.percent.toFixed(1)}%</div>
          <div class="stat-bar">
            <div class="stat-bar-fill" style="width: ${stats.cpu.percent}%"></div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Memory Usage</div>
          <div class="stat-value">${stats.memory.percent.toFixed(1)}%</div>
          <div class="stat-bar">
            <div class="stat-bar-fill" style="width: ${stats.memory.percent}%"></div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Memory Used</div>
          <div class="stat-value">${stats.memory.used_gb.toFixed(1)} GB</div>
          <div style="font-size: 12px; color: #888; margin-top: 4px;">
            of ${stats.memory.total_gb.toFixed(1)} GB
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Disk Usage</div>
          <div class="stat-value">${stats.disk.percent.toFixed(1)}%</div>
          <div class="stat-bar">
            <div class="stat-bar-fill" style="width: ${stats.disk.percent}%"></div>
          </div>
        </div>
      `;
    } catch (error) {
      console.error('Failed to load system stats:', error);
    }
  }
  
  renderProcesses() {
    const container = document.getElementById('process-list');
    if (!container) return;
    
    if (this.processes.length === 0) {
      container.innerHTML = '<div style="padding: 24px; text-align: center; color: #888;">No processes found</div>';
      return;
    }
    
    container.innerHTML = this.processes.map(proc => `
      <div class="process-row">
        <div class="process-col process-name" title="${proc.name}">${proc.name}</div>
        <div class="process-col process-pid">${proc.pid}</div>
        <div class="process-col process-cpu">${proc.cpu_percent.toFixed(1)}%</div>
        <div class="process-col process-memory">${proc.memory_mb.toFixed(1)} MB</div>
        <div class="process-col process-status ${proc.status}">${proc.status}</div>
        <div class="process-col process-actions">
          <button class="process-kill-btn" data-pid="${proc.pid}">Kill</button>
        </div>
      </div>
    `).join('');
    
    // Add kill handlers
    container.querySelectorAll('.process-kill-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.killProcess(parseInt(btn.dataset.pid));
      });
    });
  }
  
  async killProcess(pid) {
    if (!confirm(`Kill process ${pid}?`)) return;
    
    try {
      const result = await eel.os_kill_process(pid)();
      if (result.success) {
        this.showNotification(`Process ${pid} terminated`, 'success');
        await this.loadProcesses();
      } else {
        this.showNotification(`Failed to kill process: ${result.error}`, 'error');
      }
    } catch (error) {
      this.showNotification('Failed to kill process', 'error');
      console.error('Kill process error:', error);
    }
  }
  
  toggleAutoRefresh(enabled) {
    if (enabled) {
      this.startProcessMonitoring();
    } else {
      this.stopAutoRefresh();
    }
  }
  
  startProcessMonitoring() {
    this.stopAutoRefresh();
    this.refreshInterval = setInterval(() => {
      if (document.getElementById('process-manager-view').style.display !== 'none') {
        this.loadProcesses();
        this.loadSystemStats();
      }
    }, 2000); // Refresh every 2 seconds
  }
  
  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }
  
  formatTimeAgo(isoString) {
    const date = new Date(isoString);
    const seconds = Math.floor((new Date() - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return date.toLocaleDateString();
  }
  
  showNotification(message, type = 'info') {
    // Use system notification if available
    if (typeof eel !== 'undefined' && eel.send_notification) {
      eel.send_notification('PortAIOS', message)();
    }
    
    // Also show in-app toast
    console.log(`[${type.toUpperCase()}] ${message}`);
  }
  
  destroy() {
    this.stopAutoRefresh();
  }
}

// Export for use in dynamic UI
window.OSAppLauncher = OSAppLauncher;
