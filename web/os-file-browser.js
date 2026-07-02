/**
 * PortAIOS Advanced File Browser Component
 * =========================================
 * Full-featured file browser with multi-select, drag-drop, preview, and context menus
 */

class OSFileBrowser {
  constructor(container) {
    this.container = container;
    this.currentPath = '';
    this.selectedItems = new Set();
    this.clipboard = { operation: null, items: [] }; // 'copy' or 'cut'
    this.viewMode = 'grid'; // 'grid' or 'list'
    this.showHidden = false;
    this.sortBy = 'name'; // 'name', 'size', 'modified', 'type'
    this.sortOrder = 'asc';
    this.history = [];
    this.historyIndex = -1;
    
    this.init();
  }
  
  init() {
    this.render();
    this.setupEventListeners();
    this.loadHome();
  }
  
  render() {
    this.container.innerHTML = `
      <div class="os-file-browser">
        <!-- Toolbar -->
        <div class="fb-toolbar">
          <div class="fb-nav-buttons">
            <button class="fb-btn" id="fb-back" title="Back">◀</button>
            <button class="fb-btn" id="fb-forward" title="Forward">▶</button>
            <button class="fb-btn" id="fb-up" title="Up">⬆</button>
            <button class="fb-btn" id="fb-refresh" title="Refresh">🔄</button>
          </div>
          
          <div class="fb-path-bar">
            <input type="text" id="fb-path-input" class="fb-path-input" placeholder="Path...">
            <button class="fb-btn" id="fb-go" title="Go">→</button>
          </div>
          
          <div class="fb-actions">
            <button class="fb-btn" id="fb-new-folder" title="New Folder">📁+</button>
            <button class="fb-btn" id="fb-upload" title="Upload">⬆️</button>
            <button class="fb-btn" id="fb-search" title="Search">🔍</button>
            <label class="fb-toggle">
              <input type="checkbox" id="fb-show-hidden">
              <span>Hidden</span>
            </label>
            <select id="fb-view-mode" class="fb-select" title="View Mode">
              <option value="grid">Grid</option>
              <option value="list">List</option>
            </select>
          </div>
        </div>
        
        <!-- Main Content -->
        <div class="fb-main">
          <!-- Sidebar -->
          <div class="fb-sidebar">
            <div class="fb-section">
              <h3 class="fb-section-title">Quick Access</h3>
              <div id="fb-bookmarks" class="fb-bookmarks"></div>
            </div>
            
            <div class="fb-section">
              <h3 class="fb-section-title">Storage</h3>
              <div id="fb-storage" class="fb-storage"></div>
            </div>
          </div>
          
          <!-- File Grid/List -->
          <div class="fb-content" id="fb-content">
            <div class="fb-drop-zone" id="fb-drop-zone">
              Drop files here to upload
            </div>
            <div class="fb-files" id="fb-files"></div>
            <div class="fb-loading" id="fb-loading" style="display: none;">
              <div class="spinner"></div>
              <p>Loading...</p>
            </div>
            <div class="fb-empty" id="fb-empty" style="display: none;">
              <p>📂 This folder is empty</p>
            </div>
          </div>
          
          <!-- Preview Panel -->
          <div class="fb-preview" id="fb-preview" style="display: none;">
            <div class="fb-preview-header">
              <h3>Preview</h3>
              <button class="fb-close-btn" id="fb-close-preview">✕</button>
            </div>
            <div class="fb-preview-content" id="fb-preview-content"></div>
          </div>
        </div>
        
        <!-- Status Bar -->
        <div class="fb-statusbar">
          <span id="fb-status-text">Ready</span>
          <span id="fb-selection-info"></span>
        </div>
        
        <!-- Context Menu -->
        <div class="fb-context-menu" id="fb-context-menu" style="display: none;"></div>
      </div>
    `;
    
    this.injectStyles();
  }
  
  injectStyles() {
    if (document.getElementById('os-file-browser-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'os-file-browser-styles';
    style.textContent = `
      .os-file-browser {
        height: 100%;
        display: flex;
        flex-direction: column;
        background: #1a1a1a;
        color: #e0e0e0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }
      
      /* Toolbar */
      .fb-toolbar {
        display: flex;
        gap: 12px;
        padding: 8px 12px;
        background: #2a2a2a;
        border-bottom: 1px solid #3a3a3a;
        align-items: center;
      }
      
      .fb-nav-buttons {
        display: flex;
        gap: 4px;
      }
      
      .fb-btn {
        background: #3a3a3a;
        border: 1px solid #4a4a4a;
        color: #e0e0e0;
        padding: 6px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.2s;
      }
      
      .fb-btn:hover {
        background: #4a4a4a;
        border-color: #00ff88;
      }
      
      .fb-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      
      .fb-path-bar {
        flex: 1;
        display: flex;
        gap: 4px;
      }
      
      .fb-path-input {
        flex: 1;
        background: #2a2a2a;
        border: 1px solid #4a4a4a;
        color: #e0e0e0;
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 14px;
        font-family: 'Courier New', monospace;
      }
      
      .fb-path-input:focus {
        outline: none;
        border-color: #00ff88;
      }
      
      .fb-actions {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      
      .fb-toggle {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        cursor: pointer;
      }
      
      .fb-select {
        background: #3a3a3a;
        border: 1px solid #4a4a4a;
        color: #e0e0e0;
        padding: 6px 8px;
        border-radius: 4px;
        cursor: pointer;
      }
      
      /* Main Layout */
      .fb-main {
        flex: 1;
        display: flex;
        overflow: hidden;
        position: relative;
      }
      
      /* Sidebar */
      .fb-sidebar {
        width: 200px;
        background: #242424;
        border-right: 1px solid #3a3a3a;
        padding: 12px;
        overflow-y: auto;
      }
      
      .fb-section {
        margin-bottom: 20px;
      }
      
      .fb-section-title {
        font-size: 12px;
        font-weight: 600;
        color: #888;
        margin-bottom: 8px;
        text-transform: uppercase;
      }
      
      .fb-bookmarks {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      
      .fb-bookmark {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 8px;
        border-radius: 4px;
        cursor: pointer;
        transition: background 0.2s;
        font-size: 14px;
      }
      
      .fb-bookmark:hover {
        background: #3a3a3a;
      }
      
      .fb-bookmark-icon {
        font-size: 16px;
      }
      
      .fb-bookmark-name {
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      
      /* Content Area */
      .fb-content {
        flex: 1;
        position: relative;
        overflow: auto;
        padding: 16px;
      }
      
      .fb-files {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
        gap: 12px;
      }
      
      .fb-files.list-view {
        grid-template-columns: 1fr;
        gap: 2px;
      }
      
      .fb-file-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 12px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s;
        background: #2a2a2a;
        border: 2px solid transparent;
        user-select: none;
      }
      
      .fb-file-item:hover {
        background: #3a3a3a;
        border-color: #4a4a4a;
      }
      
      .fb-file-item.selected {
        background: #1a4a3a;
        border-color: #00ff88;
      }
      
      .fb-file-item.cut {
        opacity: 0.5;
      }
      
      .fb-files.list-view .fb-file-item {
        flex-direction: row;
        justify-content: flex-start;
        gap: 12px;
        padding: 8px 12px;
      }
      
      .fb-file-icon {
        font-size: 48px;
        margin-bottom: 8px;
      }
      
      .fb-files.list-view .fb-file-icon {
        font-size: 24px;
        margin-bottom: 0;
      }
      
      .fb-file-info {
        text-align: center;
        width: 100%;
      }
      
      .fb-files.list-view .fb-file-info {
        text-align: left;
        display: flex;
        flex: 1;
        justify-content: space-between;
        align-items: center;
      }
      
      .fb-file-name {
        font-size: 13px;
        word-break: break-word;
        margin-bottom: 4px;
      }
      
      .fb-file-meta {
        font-size: 11px;
        color: #888;
      }
      
      /* Drop Zone */
      .fb-drop-zone {
        display: none;
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 255, 136, 0.1);
        border: 3px dashed #00ff88;
        z-index: 1000;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        font-weight: 600;
        color: #00ff88;
      }
      
      .fb-drop-zone.active {
        display: flex;
      }
      
      /* Preview Panel */
      .fb-preview {
        width: 300px;
        background: #242424;
        border-left: 1px solid #3a3a3a;
        display: flex;
        flex-direction: column;
      }
      
      .fb-preview-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        border-bottom: 1px solid #3a3a3a;
      }
      
      .fb-preview-header h3 {
        margin: 0;
        font-size: 14px;
        font-weight: 600;
      }
      
      .fb-close-btn {
        background: none;
        border: none;
        color: #888;
        font-size: 18px;
        cursor: pointer;
        padding: 4px;
      }
      
      .fb-close-btn:hover {
        color: #e0e0e0;
      }
      
      .fb-preview-content {
        flex: 1;
        padding: 12px;
        overflow: auto;
      }
      
      /* Status Bar */
      .fb-statusbar {
        display: flex;
        justify-content: space-between;
        padding: 6px 12px;
        background: #242424;
        border-top: 1px solid #3a3a3a;
        font-size: 12px;
        color: #888;
      }
      
      /* Context Menu */
      .fb-context-menu {
        position: fixed;
        background: #2a2a2a;
        border: 1px solid #4a4a4a;
        border-radius: 6px;
        padding: 4px 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        z-index: 10000;
        min-width: 180px;
      }
      
      .fb-context-item {
        padding: 8px 16px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 14px;
        transition: background 0.2s;
      }
      
      .fb-context-item:hover {
        background: #3a3a3a;
      }
      
      .fb-context-item.disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      
      .fb-context-divider {
        height: 1px;
        background: #3a3a3a;
        margin: 4px 0;
      }
      
      /* Loading & Empty States */
      .fb-loading, .fb-empty {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        text-align: center;
      }
      
      .spinner {
        width: 40px;
        height: 40px;
        border: 4px solid #3a3a3a;
        border-top-color: #00ff88;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 12px;
      }
      
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
      
      /* Scrollbar */
      .fb-content::-webkit-scrollbar,
      .fb-sidebar::-webkit-scrollbar {
        width: 8px;
      }
      
      .fb-content::-webkit-scrollbar-track,
      .fb-sidebar::-webkit-scrollbar-track {
        background: #1a1a1a;
      }
      
      .fb-content::-webkit-scrollbar-thumb,
      .fb-sidebar::-webkit-scrollbar-thumb {
        background: #4a4a4a;
        border-radius: 4px;
      }
      
      .fb-content::-webkit-scrollbar-thumb:hover,
      .fb-sidebar::-webkit-scrollbar-thumb:hover {
        background: #5a5a5a;
      }
    `;
    document.head.appendChild(style);
  }
  
  setupEventListeners() {
    const $$ = (id) => document.getElementById(id);
    
    // Navigation
    $$('fb-back')?.addEventListener('click', () => this.goBack());
    $$('fb-forward')?.addEventListener('click', () => this.goForward());
    $$('fb-up')?.addEventListener('click', () => this.goUp());
    $$('fb-refresh')?.addEventListener('click', () => this.refresh());
    
    // Path input
    $$('fb-path-input')?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.navigateTo(e.target.value);
    });
    $$('fb-go')?.addEventListener('click', () => {
      this.navigateTo($$('fb-path-input').value);
    });
    
    // Actions
    $$('fb-new-folder')?.addEventListener('click', () => this.createNewFolder());
    $$('fb-upload')?.addEventListener('click', () => this.uploadFiles());
    $$('fb-search')?.addEventListener('click', () => this.showSearch());
    $$('fb-show-hidden')?.addEventListener('change', (e) => {
      this.showHidden = e.target.checked;
      this.refresh();
    });
    $$('fb-view-mode')?.addEventListener('change', (e) => {
      this.viewMode = e.target.value;
      this.updateViewMode();
    });
    
    // Preview
    $$('fb-close-preview')?.addEventListener('click', () => this.closePreview());
    
    // Content area - click to deselect
    $$('fb-content')?.addEventListener('click', (e) => {
      if (e.target.id === 'fb-content' || e.target.id === 'fb-files') {
        this.clearSelection();
      }
    });
    
    // Drag and drop
    const content = $$('fb-content');
    content?.addEventListener('dragover', (e) => {
      e.preventDefault();
      $$('fb-drop-zone')?.classList.add('active');
    });
    
    content?.addEventListener('dragleave', (e) => {
      if (e.target.id === 'fb-content') {
        $$('fb-drop-zone')?.classList.remove('active');
      }
    });
    
    content?.addEventListener('drop', (e) => {
      e.preventDefault();
      $$('fb-drop-zone')?.classList.remove('active');
      this.handleFileDrop(e.dataTransfer.files);
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (this.container.contains(document.activeElement)) {
        this.handleKeyboard(e);
      }
    });
    
    // Context menu - close on click outside
    document.addEventListener('click', () => {
      $$('fb-context-menu').style.display = 'none';
    });
  }
  
  async loadHome() {
    try {
      const paths = await eel.os_get_special_paths()();
      this.navigateTo(paths.home);
      await this.loadBookmarks();
    } catch (error) {
      console.error('Failed to load home:', error);
      this.showStatus('Failed to load home directory', 'error');
    }
  }
  
  async loadBookmarks() {
    try {
      const bookmarks = await eel.os_get_bookmarks()();
      const container = document.getElementById('fb-bookmarks');
      if (!container) return;
      
      container.innerHTML = bookmarks.map(b => `
        <div class="fb-bookmark" data-path="${b.path}">
          <span class="fb-bookmark-icon">${b.icon}</span>
          <span class="fb-bookmark-name">${b.name}</span>
        </div>
      `).join('');
      
      // Add click handlers
      container.querySelectorAll('.fb-bookmark').forEach(el => {
        el.addEventListener('click', () => {
          this.navigateTo(el.dataset.path);
        });
      });
    } catch (error) {
      console.error('Failed to load bookmarks:', error);
    }
  }
  
  async navigateTo(path) {
    if (!path) return;
    
    this.showLoading(true);
    this.clearSelection();
    
    try {
      const result = await eel.os_list_directory(path, this.showHidden)();
      
      if (!result.success) {
        this.showStatus(result.error, 'error');
        this.showLoading(false);
        return;
      }
      
      // Add to history
      if (this.currentPath !== path) {
        this.history = this.history.slice(0, this.historyIndex + 1);
        this.history.push(path);
        this.historyIndex = this.history.length - 1;
      }
      
      this.currentPath = path;
      document.getElementById('fb-path-input').value = path;
      this.renderFiles(result.files);
      this.showStatus(`${result.total_folders} folders, ${result.total_files} files`);
      this.updateNavigationButtons();
      
    } catch (error) {
      console.error('Navigation error:', error);
      this.showStatus('Failed to load directory', 'error');
    } finally {
      this.showLoading(false);
    }
  }
  
  renderFiles(files) {
    const container = document.getElementById('fb-files');
    const empty = document.getElementById('fb-empty');
    
    if (!files || files.length === 0) {
      container.innerHTML = '';
      empty.style.display = 'block';
      return;
    }
    
    empty.style.display = 'none';
    
    // Sort files
    const sorted = this.sortFiles(files);
    
    container.innerHTML = sorted.map(file => `
      <div class="fb-file-item" 
           data-path="${file.path}"
           data-type="${file.type}"
           data-name="${file.name}">
        <div class="fb-file-icon">${file.icon}</div>
        <div class="fb-file-info">
          <div class="fb-file-name">${file.name}</div>
          <div class="fb-file-meta">
            ${file.type === 'file' ? this.formatSize(file.size) : ''}
            ${file.type === 'file' ? ' • ' : ''}
            ${new Date(file.modified * 1000).toLocaleDateString()}
          </div>
        </div>
      </div>
    `).join('');
    
    // Add event listeners
    container.querySelectorAll('.fb-file-item').forEach(el => {
      el.addEventListener('click', (e) => this.handleFileClick(e, el));
      el.addEventListener('dblclick', () => this.handleFileDoubleClick(el));
      el.addEventListener('contextmenu', (e) => this.showContextMenu(e, el));
    });
  }
  
  sortFiles(files) {
    const sorted = [...files];
    const comparator = (a, b) => {
      // Folders first
      if (a.type !== b.type) {
        return a.type === 'folder' ? -1 : 1;
      }
      
      let valA, valB;
      switch (this.sortBy) {
        case 'name':
          valA = a.name.toLowerCase();
          valB = b.name.toLowerCase();
          break;
        case 'size':
          valA = a.size;
          valB = b.size;
          break;
        case 'modified':
          valA = a.modified;
          valB = b.modified;
          break;
        case 'type':
          valA = a.extension.toLowerCase();
          valB = b.extension.toLowerCase();
          break;
        default:
          return 0;
      }
      
      const result = valA < valB ? -1 : valA > valB ? 1 : 0;
      return this.sortOrder === 'asc' ? result : -result;
    };
    
    return sorted.sort(comparator);
  }
  
  handleFileClick(e, element) {
    const isMultiSelect = e.ctrlKey || e.metaKey;
    const isRangeSelect = e.shiftKey;
    
    if (!isMultiSelect && !isRangeSelect) {
      this.clearSelection();
    }
    
    const path = element.dataset.path;
    if (this.selectedItems.has(path)) {
      this.selectedItems.delete(path);
      element.classList.remove('selected');
    } else {
      this.selectedItems.add(path);
      element.classList.add('selected');
    }
    
    this.updateSelectionInfo();
    
    // Show preview for single selection
    if (this.selectedItems.size === 1 && element.dataset.type === 'file') {
      this.showPreview(path);
    }
  }
  
  async handleFileDoubleClick(element) {
    const path = element.dataset.path;
    const type = element.dataset.type;
    
    if (type === 'folder') {
      this.navigateTo(path);
    } else {
      // Open file with default application
      try {
        await eel.os_open_file(path)();
        this.showStatus(`Opened ${element.dataset.name}`);
      } catch (error) {
        this.showStatus('Failed to open file', 'error');
      }
    }
  }
  
  showContextMenu(e, element) {
    e.preventDefault();
    
    const menu = document.getElementById('fb-context-menu');
    const path = element.dataset.path;
    const type = element.dataset.type;
    
    // Ensure item is selected
    if (!this.selectedItems.has(path)) {
      this.clearSelection();
      this.selectedItems.add(path);
      element.classList.add('selected');
      this.updateSelectionInfo();
    }
    
    const isMultiple = this.selectedItems.size > 1;
    
    menu.innerHTML = `
      <div class="fb-context-item" data-action="open">
        <span>📂</span> Open
      </div>
      <div class="fb-context-divider"></div>
      <div class="fb-context-item" data-action="cut">
        <span>✂️</span> Cut
      </div>
      <div class="fb-context-item" data-action="copy">
        <span>📋</span> Copy
      </div>
      <div class="fb-context-item ${this.clipboard.items.length === 0 ? 'disabled' : ''}" data-action="paste">
        <span>📌</span> Paste
      </div>
      <div class="fb-context-divider"></div>
      <div class="fb-context-item ${isMultiple ? 'disabled' : ''}" data-action="rename">
        <span>✏️</span> Rename
      </div>
      <div class="fb-context-item" data-action="delete">
        <span>🗑️</span> Delete
      </div>
      <div class="fb-context-divider"></div>
      <div class="fb-context-item ${isMultiple ? 'disabled' : ''}" data-action="properties">
        <span>ℹ️</span> Properties
      </div>
    `;
    
    // Position menu
    menu.style.display = 'block';
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';
    
    // Add action handlers
    menu.querySelectorAll('.fb-context-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = item.dataset.action;
        if (!item.classList.contains('disabled')) {
          this.handleContextAction(action);
        }
        menu.style.display = 'none';
      });
    });
  }
  
  async handleContextAction(action) {
    const selected = Array.from(this.selectedItems);
    
    switch (action) {
      case 'open':
        if (selected.length === 1) {
          const el = document.querySelector(`[data-path="${selected[0]}"]`);
          this.handleFileDoubleClick(el);
        }
        break;
        
      case 'cut':
        this.clipboard = { operation: 'cut', items: selected };
        this.updateCutVisual();
        this.showStatus(`Cut ${selected.length} item(s)`);
        break;
        
      case 'copy':
        this.clipboard = { operation: 'copy', items: selected };
        this.showStatus(`Copied ${selected.length} item(s)`);
        break;
        
      case 'paste':
        await this.pasteItems();
        break;
        
      case 'rename':
        if (selected.length === 1) {
          this.renameItem(selected[0]);
        }
        break;
        
      case 'delete':
        await this.deleteItems(selected);
        break;
        
      case 'properties':
        if (selected.length === 1) {
          this.showProperties(selected[0]);
        }
        break;
    }
  }
  
  async pasteItems() {
    if (this.clipboard.items.length === 0) return;
    
    try {
      const operation = this.clipboard.operation;
      const items = this.clipboard.items;
      
      if (operation === 'copy') {
        const result = await eel.os_copy_items(items, this.currentPath)();
        if (result.success) {
          this.showStatus(`Copied ${items.length} item(s)`);
          this.refresh();
        } else {
          this.showStatus(result.error, 'error');
        }
      } else if (operation === 'cut') {
        const result = await eel.os_move_items(items, this.currentPath)();
        if (result.success) {
          this.showStatus(`Moved ${items.length} item(s)`);
          this.clipboard = { operation: null, items: [] };
          this.refresh();
        } else {
          this.showStatus(result.error, 'error');
        }
      }
    } catch (error) {
      this.showStatus('Paste failed', 'error');
    }
  }
  
  async deleteItems(items) {
    if (!confirm(`Delete ${items.length} item(s)?`)) return;
    
    try {
      for (const item of items) {
        const result = await eel.os_delete_item(item, true)();
        if (!result.success) {
          this.showStatus(`Failed to delete ${item}`, 'error');
          return;
        }
      }
      this.showStatus(`Deleted ${items.length} item(s)`);
      this.clearSelection();
      this.refresh();
    } catch (error) {
      this.showStatus('Delete failed', 'error');
    }
  }
  
  async renameItem(path) {
    const currentName = path.split('/').pop().split('\\').pop();
    const newName = prompt('Enter new name:', currentName);
    
    if (!newName || newName === currentName) return;
    
    try {
      const result = await eel.os_rename_item(path, newName)();
      if (result.success) {
        this.showStatus(`Renamed to ${newName}`);
        this.refresh();
      } else {
        this.showStatus(result.error, 'error');
      }
    } catch (error) {
      this.showStatus('Rename failed', 'error');
    }
  }
  
  async createNewFolder() {
    const name = prompt('Enter folder name:', 'New Folder');
    if (!name) return;
    
    try {
      const result = await eel.os_create_folder(this.currentPath, name)();
      if (result.success) {
        this.showStatus(`Created folder: ${name}`);
        this.refresh();
      } else {
        this.showStatus(result.error, 'error');
      }
    } catch (error) {
      this.showStatus('Failed to create folder', 'error');
    }
  }
  
  async showPreview(path) {
    const preview = document.getElementById('fb-preview');
    const content = document.getElementById('fb-preview-content');
    
    preview.style.display = 'flex';
    content.innerHTML = '<div class="fb-loading"><div class="spinner"></div></div>';
    
    try {
      const result = await eel.os_read_file(path, 1024 * 100)(); // 100KB max for preview
      
      if (!result.success) {
        content.innerHTML = `<p>Cannot preview this file</p><p style="color: #888">${result.error}</p>`;
        return;
      }
      
      const fileName = path.split('/').pop().split('\\').pop();
      const ext = fileName.split('.').pop().toLowerCase();
      
      if (result.type === 'text') {
        // Text preview with syntax highlighting hint
        content.innerHTML = `
          <div style="margin-bottom: 12px;">
            <strong>${fileName}</strong>
          </div>
          <pre style="background: #1a1a1a; padding: 12px; border-radius: 4px; overflow: auto; max-height: 500px; font-size: 12px; line-height: 1.5;">${this.escapeHtml(result.content)}</pre>
        `;
      } else {
        content.innerHTML = `<p>Binary file</p><p style="color: #888">Size: ${this.formatSize(result.content.length)}</p>`;
      }
    } catch (error) {
      content.innerHTML = '<p>Preview failed</p>';
    }
  }
  
  closePreview() {
    document.getElementById('fb-preview').style.display = 'none';
  }
  
  showProperties(path) {
    // TODO: Show detailed file properties
    alert('Properties: ' + path);
  }
  
  goBack() {
    if (this.historyIndex > 0) {
      this.historyIndex--;
      this.navigateTo(this.history[this.historyIndex]);
    }
  }
  
  goForward() {
    if (this.historyIndex < this.history.length - 1) {
      this.historyIndex++;
      this.navigateTo(this.history[this.historyIndex]);
    }
  }
  
  async goUp() {
    const result = await eel.os_list_directory(this.currentPath)();
    if (result.parent) {
      this.navigateTo(result.parent);
    }
  }
  
  refresh() {
    this.navigateTo(this.currentPath);
  }
  
  updateNavigationButtons() {
    const back = document.getElementById('fb-back');
    const forward = document.getElementById('fb-forward');
    
    if (back) back.disabled = this.historyIndex <= 0;
    if (forward) forward.disabled = this.historyIndex >= this.history.length - 1;
  }
  
  updateViewMode() {
    const files = document.getElementById('fb-files');
    if (this.viewMode === 'list') {
      files?.classList.add('list-view');
    } else {
      files?.classList.remove('list-view');
    }
  }
  
  clearSelection() {
    this.selectedItems.clear();
    document.querySelectorAll('.fb-file-item.selected').forEach(el => {
      el.classList.remove('selected');
    });
    this.updateSelectionInfo();
    this.closePreview();
  }
  
  updateSelectionInfo() {
    const info = document.getElementById('fb-selection-info');
    if (!info) return;
    
    if (this.selectedItems.size === 0) {
      info.textContent = '';
    } else {
      info.textContent = `${this.selectedItems.size} selected`;
    }
  }
  
  updateCutVisual() {
    document.querySelectorAll('.fb-file-item.cut').forEach(el => {
      el.classList.remove('cut');
    });
    
    this.clipboard.items.forEach(path => {
      const el = document.querySelector(`[data-path="${path}"]`);
      if (el) el.classList.add('cut');
    });
  }
  
  showLoading(show) {
    const loading = document.getElementById('fb-loading');
    const files = document.getElementById('fb-files');
    if (loading) loading.style.display = show ? 'block' : 'none';
    if (files) files.style.display = show ? 'none' : 'grid';
  }
  
  showStatus(message, type = 'info') {
    const status = document.getElementById('fb-status-text');
    if (!status) return;
    
    status.textContent = message;
    status.style.color = type === 'error' ? '#ff4444' : '#888';
    
    if (type !== 'error') {
      setTimeout(() => {
        if (status.textContent === message) {
          status.textContent = 'Ready';
          status.style.color = '#888';
        }
      }, 3000);
    }
  }
  
  formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  handleKeyboard(e) {
    if (e.ctrlKey || e.metaKey) {
      switch (e.key.toLowerCase()) {
        case 'a':
          e.preventDefault();
          this.selectAll();
          break;
        case 'c':
          e.preventDefault();
          this.handleContextAction('copy');
          break;
        case 'x':
          e.preventDefault();
          this.handleContextAction('cut');
          break;
        case 'v':
          e.preventDefault();
          this.handleContextAction('paste');
          break;
      }
    } else if (e.key === 'Delete') {
      if (this.selectedItems.size > 0) {
        this.deleteItems(Array.from(this.selectedItems));
      }
    } else if (e.key === 'F5') {
      e.preventDefault();
      this.refresh();
    }
  }
  
  selectAll() {
    document.querySelectorAll('.fb-file-item').forEach(el => {
      this.selectedItems.add(el.dataset.path);
      el.classList.add('selected');
    });
    this.updateSelectionInfo();
  }
  
  uploadFiles() {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.onchange = (e) => this.handleFileDrop(e.target.files);
    input.click();
  }
  
  async handleFileDrop(files) {
    // TODO: Implement file upload
    console.log('Files to upload:', files);
    this.showStatus(`Upload not yet implemented (${files.length} files)`);
  }
  
  showSearch() {
    const query = prompt('Search for:');
    if (!query) return;
    
    this.performSearch(query);
  }
  
  async performSearch(query) {
    this.showLoading(true);
    try {
      const result = await eel.os_search_files(query, this.currentPath, 100)();
      if (result.success) {
        this.renderFiles(result.results);
        this.showStatus(`Found ${result.count} matches`);
      } else {
        this.showStatus(result.error, 'error');
      }
    } catch (error) {
      this.showStatus('Search failed', 'error');
    } finally {
      this.showLoading(false);
    }
  }
}

// Export for use in dynamic UI
window.OSFileBrowser = OSFileBrowser;
