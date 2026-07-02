/**
 * PortAIOS Integrated Browser Component
 * ======================================
 * Full-featured browser with tab management, bookmarks, and history
 */

class OSBrowser {
  constructor(container) {
    this.container = container;
    this.tabs = [];
    this.activeTabId = null;
    this.tabCounter = 0;
    this.bookmarks = [];
    this.history = [];
    
    this.init();
  }
  
  init() {
    this.loadBookmarks();
    this.render();
    this.createNewTab('https://www.google.com');
  }
  
  render() {
    this.container.innerHTML = `
      <div class="os-browser">
        <!-- Tab Bar -->
        <div class="browser-tabs">
          <div class="tab-list" id="tab-list"></div>
          <button class="new-tab-btn" id="new-tab-btn" title="New Tab">+</button>
        </div>
        
        <!-- Address Bar -->
        <div class="browser-toolbar">
          <div class="nav-buttons">
            <button class="nav-btn" id="back-btn" title="Back">◀</button>
            <button class="nav-btn" id="forward-btn" title="Forward">▶</button>
            <button class="nav-btn" id="reload-btn" title="Reload">🔄</button>
            <button class="nav-btn" id="home-btn" title="Home">🏠</button>
          </div>
          
          <div class="address-bar">
            <div class="security-indicator" id="security-indicator">🔒</div>
            <input type="text" id="url-input" class="url-input" placeholder="Enter URL or search...">
            <button class="go-btn" id="go-btn">Go</button>
          </div>
          
          <div class="browser-actions">
            <button class="action-btn" id="bookmark-btn" title="Bookmark">⭐</button>
            <button class="action-btn" id="bookmarks-btn" title="Bookmarks">📚</button>
            <button class="action-btn" id="history-btn" title="History">🕐</button>
            <button class="action-btn" id="settings-btn" title="Settings">⚙️</button>
          </div>
        </div>
        
        <!-- Content Area -->
        <div class="browser-content" id="browser-content"></div>
        
        <!-- Bookmarks Panel -->
        <div class="browser-panel" id="bookmarks-panel" style="display: none;">
          <div class="panel-header">
            <h3>Bookmarks</h3>
            <button class="close-panel-btn" data-panel="bookmarks-panel">✕</button>
          </div>
          <div class="panel-content">
            <div class="bookmarks-grid" id="bookmarks-grid"></div>
          </div>
        </div>
        
        <!-- History Panel -->
        <div class="browser-panel" id="history-panel" style="display: none;">
          <div class="panel-header">
            <h3>History</h3>
            <button class="close-panel-btn" data-panel="history-panel">✕</button>
          </div>
          <div class="panel-content">
            <div class="history-list" id="history-list"></div>
          </div>
        </div>
      </div>
    `;
    
    this.injectStyles();
    this.setupEventListeners();
  }
  
  injectStyles() {
    if (document.getElementById('os-browser-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'os-browser-styles';
    style.textContent = `
      .os-browser {
        height: 100%;
        display: flex;
        flex-direction: column;
        background: #1a1a1a;
        color: #e0e0e0;
        position: relative;
      }
      
      /* Tab Bar */
      .browser-tabs {
        display: flex;
        background: #242424;
        border-bottom: 1px solid #3a3a3a;
        padding: 4px 4px 0 4px;
        gap: 4px;
      }
      
      .tab-list {
        display: flex;
        gap: 4px;
        flex: 1;
        overflow-x: auto;
        overflow-y: hidden;
      }
      
      .tab-list::-webkit-scrollbar {
        height: 0;
      }
      
      .browser-tab {
        background: #2a2a2a;
        border: 1px solid #3a3a3a;
        border-bottom: none;
        border-radius: 6px 6px 0 0;
        padding: 8px 12px;
        min-width: 180px;
        max-width: 240px;
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
        transition: background 0.2s;
        position: relative;
      }
      
      .browser-tab:hover {
        background: #333;
      }
      
      .browser-tab.active {
        background: #1a1a1a;
        border-color: #00ff88;
      }
      
      .tab-favicon {
        font-size: 16px;
      }
      
      .tab-title {
        flex: 1;
        font-size: 13px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      
      .tab-close {
        background: none;
        border: none;
        color: #888;
        font-size: 16px;
        cursor: pointer;
        padding: 0;
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 3px;
      }
      
      .tab-close:hover {
        background: #ff4444;
        color: white;
      }
      
      .new-tab-btn {
        background: #2a2a2a;
        border: 1px solid #3a3a3a;
        color: #888;
        font-size: 20px;
        width: 36px;
        height: 36px;
        border-radius: 6px 6px 0 0;
        cursor: pointer;
        transition: all 0.2s;
      }
      
      .new-tab-btn:hover {
        background: #3a3a3a;
        color: #00ff88;
      }
      
      /* Toolbar */
      .browser-toolbar {
        display: flex;
        gap: 12px;
        padding: 8px 12px;
        background: #2a2a2a;
        border-bottom: 1px solid #3a3a3a;
        align-items: center;
      }
      
      .nav-buttons, .browser-actions {
        display: flex;
        gap: 4px;
      }
      
      .nav-btn, .action-btn {
        background: #3a3a3a;
        border: 1px solid #4a4a4a;
        color: #e0e0e0;
        padding: 6px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.2s;
      }
      
      .nav-btn:hover, .action-btn:hover {
        background: #4a4a4a;
        border-color: #00ff88;
      }
      
      .nav-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      
      .address-bar {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 8px;
        background: #1a1a1a;
        border: 1px solid #4a4a4a;
        border-radius: 6px;
        padding: 0 12px;
      }
      
      .address-bar:focus-within {
        border-color: #00ff88;
      }
      
      .security-indicator {
        font-size: 14px;
      }
      
      .url-input {
        flex: 1;
        background: transparent;
        border: none;
        color: #e0e0e0;
        padding: 8px 0;
        font-size: 14px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }
      
      .url-input:focus {
        outline: none;
      }
      
      .go-btn {
        background: #00ff88;
        border: none;
        color: #1a1a1a;
        padding: 6px 16px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 13px;
        font-weight: 600;
        transition: background 0.2s;
      }
      
      .go-btn:hover {
        background: #00cc6a;
      }
      
      /* Content Area */
      .browser-content {
        flex: 1;
        position: relative;
        overflow: hidden;
      }
      
      .tab-content {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        display: none;
      }
      
      .tab-content.active {
        display: block;
      }
      
      .browser-iframe {
        width: 100%;
        height: 100%;
        border: none;
        background: white;
      }
      
      .browser-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        gap: 24px;
        background: #1a1a1a;
      }
      
      .placeholder-logo {
        font-size: 64px;
      }
      
      .placeholder-title {
        font-size: 32px;
        font-weight: 600;
      }
      
      .quick-links {
        display: grid;
        grid-template-columns: repeat(4, 150px);
        gap: 16px;
        margin-top: 24px;
      }
      
      .quick-link {
        background: #2a2a2a;
        border: 1px solid #4a4a4a;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
      }
      
      .quick-link:hover {
        background: #3a3a3a;
        border-color: #00ff88;
        transform: translateY(-2px);
      }
      
      .quick-link-icon {
        font-size: 32px;
        margin-bottom: 8px;
      }
      
      .quick-link-title {
        font-size: 13px;
      }
      
      /* Panels */
      .browser-panel {
        position: absolute;
        top: 0;
        right: 0;
        width: 320px;
        height: 100%;
        background: #2a2a2a;
        border-left: 1px solid #3a3a3a;
        z-index: 100;
        display: flex;
        flex-direction: column;
        box-shadow: -4px 0 12px rgba(0, 0, 0, 0.5);
      }
      
      .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        border-bottom: 1px solid #3a3a3a;
      }
      
      .panel-header h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
      }
      
      .close-panel-btn {
        background: none;
        border: none;
        color: #888;
        font-size: 20px;
        cursor: pointer;
        padding: 4px;
      }
      
      .close-panel-btn:hover {
        color: #e0e0e0;
      }
      
      .panel-content {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
      }
      
      .bookmarks-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
      }
      
      .bookmark-item {
        background: #242424;
        border: 1px solid #3a3a3a;
        border-radius: 6px;
        padding: 12px;
        cursor: pointer;
        transition: all 0.2s;
      }
      
      .bookmark-item:hover {
        background: #333;
        border-color: #00ff88;
      }
      
      .bookmark-icon {
        font-size: 24px;
        margin-bottom: 8px;
      }
      
      .bookmark-title {
        font-size: 13px;
        font-weight: 500;
        margin-bottom: 4px;
      }
      
      .bookmark-url {
        font-size: 11px;
        color: #888;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      
      .history-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      
      .history-item {
        background: #242424;
        border: 1px solid #3a3a3a;
        border-radius: 6px;
        padding: 12px;
        cursor: pointer;
        transition: all 0.2s;
      }
      
      .history-item:hover {
        background: #333;
        border-color: #00ff88;
      }
      
      .history-time {
        font-size: 11px;
        color: #888;
        margin-bottom: 4px;
      }
      
      .history-title {
        font-size: 13px;
        font-weight: 500;
        margin-bottom: 4px;
      }
      
      .history-url {
        font-size: 11px;
        color: #888;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    `;
    document.head.appendChild(style);
  }
  
  setupEventListeners() {
    // New tab
    document.getElementById('new-tab-btn')?.addEventListener('click', () => {
      this.createNewTab();
    });
    
    // Navigation
    document.getElementById('back-btn')?.addEventListener('click', () => this.goBack());
    document.getElementById('forward-btn')?.addEventListener('click', () => this.goForward());
    document.getElementById('reload-btn')?.addEventListener('click', () => this.reload());
    document.getElementById('home-btn')?.addEventListener('click', () => this.goHome());
    
    // URL input
    const urlInput = document.getElementById('url-input');
    urlInput?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.navigate(urlInput.value);
    });
    
    document.getElementById('go-btn')?.addEventListener('click', () => {
      this.navigate(urlInput.value);
    });
    
    // Actions
    document.getElementById('bookmark-btn')?.addEventListener('click', () => this.addBookmark());
    document.getElementById('bookmarks-btn')?.addEventListener('click', () => this.togglePanel('bookmarks-panel'));
    document.getElementById('history-btn')?.addEventListener('click', () => this.togglePanel('history-panel'));
    
    // Close panels
    document.querySelectorAll('.close-panel-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.getElementById(btn.dataset.panel).style.display = 'none';
      });
    });
  }
  
  createNewTab(url = null) {
    const tabId = this.tabCounter++;
    const tab = {
      id: tabId,
      url: url || '',
      title: url ? 'Loading...' : 'New Tab',
      history: [],
      historyIndex: -1
    };
    
    this.tabs.push(tab);
    this.renderTabs();
    this.renderTabContent(tab);
    this.switchToTab(tabId);
    
    if (url) {
      this.navigate(url, tabId);
    }
  }
  
  renderTabs() {
    const container = document.getElementById('tab-list');
    if (!container) return;
    
    container.innerHTML = this.tabs.map(tab => `
      <div class="browser-tab ${tab.id === this.activeTabId ? 'active' : ''}" data-tab-id="${tab.id}">
        <span class="tab-favicon">${this.getFavicon(tab.url)}</span>
        <span class="tab-title">${tab.title}</span>
        <button class="tab-close" data-tab-id="${tab.id}">×</button>
      </div>
    `).join('');
    
    // Add event listeners
    container.querySelectorAll('.browser-tab').forEach(el => {
      const tabId = parseInt(el.dataset.tabId);
      el.addEventListener('click', (e) => {
        if (!e.target.classList.contains('tab-close')) {
          this.switchToTab(tabId);
        }
      });
    });
    
    container.querySelectorAll('.tab-close').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.closeTab(parseInt(btn.dataset.tabId));
      });
    });
  }
  
  renderTabContent(tab) {
    const container = document.getElementById('browser-content');
    if (!container) return;
    
    const content = document.createElement('div');
    content.className = 'tab-content';
    content.id = `tab-content-${tab.id}`;
    content.dataset.tabId = tab.id;
    
    if (tab.url) {
      content.innerHTML = `<iframe class="browser-iframe" src="${this.getEmbedUrl(tab.url)}"></iframe>`;
    } else {
      content.innerHTML = this.getNewTabPage();
    }
    
    container.appendChild(content);
  }
  
  getNewTabPage() {
    return `
      <div class="browser-placeholder">
        <div class="placeholder-logo">🌐</div>
        <div class="placeholder-title">PortAIOS Browser</div>
        <div class="quick-links">
          <div class="quick-link" data-url="https://www.google.com">
            <div class="quick-link-icon">🔍</div>
            <div class="quick-link-title">Google</div>
          </div>
          <div class="quick-link" data-url="https://github.com">
            <div class="quick-link-icon">💻</div>
            <div class="quick-link-title">GitHub</div>
          </div>
          <div class="quick-link" data-url="https://stackoverflow.com">
            <div class="quick-link-icon">📚</div>
            <div class="quick-link-title">Stack Overflow</div>
          </div>
          <div class="quick-link" data-url="https://news.ycombinator.com">
            <div class="quick-link-icon">📰</div>
            <div class="quick-link-title">Hacker News</div>
          </div>
        </div>
      </div>
    `;
  }
  
  switchToTab(tabId) {
    this.activeTabId = tabId;
    
    // Update tab styles
    document.querySelectorAll('.browser-tab').forEach(el => {
      el.classList.toggle('active', parseInt(el.dataset.tabId) === tabId);
    });
    
    // Update content visibility
    document.querySelectorAll('.tab-content').forEach(el => {
      el.classList.toggle('active', parseInt(el.dataset.tabId) === tabId);
    });
    
    // Update URL input
    const tab = this.tabs.find(t => t.id === tabId);
    if (tab) {
      document.getElementById('url-input').value = tab.url || '';
    }
    
    // Setup quick links if new tab
    const content = document.getElementById(`tab-content-${tabId}`);
    content?.querySelectorAll('.quick-link').forEach(link => {
      link.addEventListener('click', () => {
        this.navigate(link.dataset.url, tabId);
      });
    });
  }
  
  closeTab(tabId) {
    const index = this.tabs.findIndex(t => t.id === tabId);
    if (index === -1) return;
    
    // Remove tab
    this.tabs.splice(index, 1);
    
    // Remove content
    document.getElementById(`tab-content-${tabId}`)?.remove();
    
    // If closing active tab, switch to another
    if (tabId === this.activeTabId) {
      if (this.tabs.length > 0) {
        const newActive = this.tabs[Math.max(0, index - 1)];
        this.switchToTab(newActive.id);
      } else {
        this.createNewTab();
        return;
      }
    }
    
    this.renderTabs();
  }
  
  navigate(url, tabId = null) {
    const targetTabId = tabId !== null ? tabId : this.activeTabId;
    const tab = this.tabs.find(t => t.id === targetTabId);
    if (!tab) return;
    
    // Process URL
    let processedUrl = url.trim();
    if (!processedUrl) return;
    
    // Add protocol if missing
    if (!processedUrl.match(/^https?:\/\//)) {
      if (processedUrl.includes('.') && !processedUrl.includes(' ')) {
        processedUrl = 'https://' + processedUrl;
      } else {
        // Search query
        processedUrl = `https://www.google.com/search?q=${encodeURIComponent(processedUrl)}`;
      }
    }
    
    // Update tab
    tab.url = processedUrl;
    tab.title = new URL(processedUrl).hostname;
    
    // Add to history
    tab.history = tab.history.slice(0, tab.historyIndex + 1);
    tab.history.push(processedUrl);
    tab.historyIndex = tab.history.length - 1;
    
    // Add to global history
    this.addToHistory(tab.title, processedUrl);
    
    // Update UI
    this.renderTabs();
    
    // Update iframe
    const content = document.getElementById(`tab-content-${targetTabId}`);
    if (content) {
      content.innerHTML = `<iframe class="browser-iframe" src="${this.getEmbedUrl(processedUrl)}"></iframe>`;
    }
    
    // Update URL input if active tab
    if (targetTabId === this.activeTabId) {
      document.getElementById('url-input').value = processedUrl;
    }
  }
  
  goBack() {
    const tab = this.tabs.find(t => t.id === this.activeTabId);
    if (!tab || tab.historyIndex <= 0) return;
    
    tab.historyIndex--;
    const url = tab.history[tab.historyIndex];
    this.navigate(url);
  }
  
  goForward() {
    const tab = this.tabs.find(t => t.id === this.activeTabId);
    if (!tab || tab.historyIndex >= tab.history.length - 1) return;
    
    tab.historyIndex++;
    const url = tab.history[tab.historyIndex];
    this.navigate(url);
  }
  
  reload() {
    const tab = this.tabs.find(t => t.id === this.activeTabId);
    if (!tab || !tab.url) return;
    
    const content = document.getElementById(`tab-content-${this.activeTabId}`);
    const iframe = content?.querySelector('iframe');
    if (iframe) {
      iframe.src = iframe.src; // Reload
    }
  }
  
  goHome() {
    this.navigate('https://www.google.com');
  }
  
  addBookmark() {
    const tab = this.tabs.find(t => t.id === this.activeTabId);
    if (!tab || !tab.url) return;
    
    const bookmark = {
      id: Date.now(),
      title: tab.title,
      url: tab.url,
      icon: this.getFavicon(tab.url),
      addedAt: new Date().toISOString()
    };
    
    this.bookmarks.unshift(bookmark);
    this.saveBookmarks();
    this.renderBookmarks();
    
    alert(`Added "${tab.title}" to bookmarks`);
  }
  
  loadBookmarks() {
    try {
      const saved = localStorage.getItem('portaios_bookmarks');
      this.bookmarks = saved ? JSON.parse(saved) : this.getDefaultBookmarks();
    } catch {
      this.bookmarks = this.getDefaultBookmarks();
    }
  }
  
  saveBookmarks() {
    try {
      localStorage.setItem('portaios_bookmarks', JSON.stringify(this.bookmarks));
    } catch (e) {
      console.error('Failed to save bookmarks:', e);
    }
  }
  
  getDefaultBookmarks() {
    return [
      { title: 'Google', url: 'https://www.google.com', icon: '🔍' },
      { title: 'GitHub', url: 'https://github.com', icon: '💻' },
      { title: 'Stack Overflow', url: 'https://stackoverflow.com', icon: '📚' },
      { title: 'MDN Web Docs', url: 'https://developer.mozilla.org', icon: '📖' }
    ];
  }
  
  renderBookmarks() {
    const container = document.getElementById('bookmarks-grid');
    if (!container) return;
    
    container.innerHTML = this.bookmarks.map(b => `
      <div class="bookmark-item" data-url="${b.url}">
        <div class="bookmark-icon">${b.icon}</div>
        <div class="bookmark-title">${b.title}</div>
        <div class="bookmark-url">${b.url}</div>
      </div>
    `).join('');
    
    container.querySelectorAll('.bookmark-item').forEach(item => {
      item.addEventListener('click', () => {
        this.navigate(item.dataset.url);
        this.togglePanel('bookmarks-panel');
      });
    });
  }
  
  addToHistory(title, url) {
    this.history.unshift({
      title,
      url,
      visitedAt: new Date().toISOString()
    });
    
    // Keep last 100 items
    this.history = this.history.slice(0, 100);
    this.renderHistory();
  }
  
  renderHistory() {
    const container = document.getElementById('history-list');
    if (!container) return;
    
    container.innerHTML = this.history.map(h => `
      <div class="history-item" data-url="${h.url}">
        <div class="history-time">${this.formatTime(h.visitedAt)}</div>
        <div class="history-title">${h.title}</div>
        <div class="history-url">${h.url}</div>
      </div>
    `).join('');
    
    container.querySelectorAll('.history-item').forEach(item => {
      item.addEventListener('click', () => {
        this.navigate(item.dataset.url);
        this.togglePanel('history-panel');
      });
    });
  }
  
  togglePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    
    // Close other panels
    document.querySelectorAll('.browser-panel').forEach(p => {
      if (p.id !== panelId) p.style.display = 'none';
    });
    
    // Toggle this panel
    panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
    
    // Render content
    if (panelId === 'bookmarks-panel') {
      this.renderBookmarks();
    } else if (panelId === 'history-panel') {
      this.renderHistory();
    }
  }
  
  getFavicon(url) {
    if (!url) return '📄';
    
    try {
      const hostname = new URL(url).hostname.toLowerCase();
      const icons = {
        'google.com': '🔍',
        'github.com': '💻',
        'stackoverflow.com': '📚',
        'youtube.com': '📺',
        'twitter.com': '🐦',
        'facebook.com': '📘',
        'reddit.com': '🤖',
        'wikipedia.org': '📖'
      };
      
      for (const [domain, icon] of Object.entries(icons)) {
        if (hostname.includes(domain)) return icon;
      }
    } catch {}
    
    return '🌐';
  }
  
  getEmbedUrl(url) {
    // Some sites don't allow embedding, but we'll try anyway
    return url;
  }
  
  formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    
    return date.toLocaleString();
  }
}

// Export for use in dynamic UI
window.OSBrowser = OSBrowser;
