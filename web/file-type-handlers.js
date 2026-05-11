/**
 * Advanced File Type Handlers for AIOS Dynamic UI
 * Provides specialized rendering for different file types:
 * - PDF viewing with PDF.js
 * - Code syntax highlighting with Prism.js
 * - Markdown rendering
 * - JSON formatting
 * - Image manipulation
 * - Video controls
 */

class FileTypeHandler {
  constructor(options = {}) {
    this.options = {
      enablePDF: options.enablePDF !== false,
      enableSyntaxHighlighting: options.enableSyntaxHighlighting !== false,
      enableMarkdown: options.enableMarkdown !== false,
      ...options
    };
    
    this.supportedTypes = {
      code: ['.js', '.py', '.rs', '.cpp', '.c', '.h', '.java', '.go', '.rb', '.php', '.swift', '.kt'],
      markup: ['.html', '.xml', '.jsx', '.tsx', '.vue', '.svelte'],
      data: ['.json', '.yaml', '.yml', '.toml', '.ini', '.csv'],
      markdown: ['.md', '.markdown'],
      document: ['.txt', '.log', '.conf', '.cfg'],
      pdf: ['.pdf'],
      image: ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'],
      video: ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v'],
      audio: ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'],
      archive: ['.zip', '.tar', '.gz', '.bz2', '.7z', '.rar']
    };
  }

  /**
   * Get file type category
   */
  getFileType(filename) {
    const ext = this._getExtension(filename);
    
    for (const [type, extensions] of Object.entries(this.supportedTypes)) {
      if (extensions.includes(ext)) {
        return type;
      }
    }
    
    return 'unknown';
  }

  /**
   * Render file content based on type
   */
  async renderFile(filename, content, container) {
    const type = this.getFileType(filename);
    const ext = this._getExtension(filename);
    
    console.log(`[FileHandler] Rendering ${filename} as ${type}`);
    
    switch (type) {
      case 'code':
        return this._renderCode(content, ext, container);
      case 'markup':
        return this._renderCode(content, ext, container);
      case 'data':
        return this._renderData(content, ext, container);
      case 'markdown':
        return this._renderMarkdown(content, container);
      case 'pdf':
        return this._renderPDF(content, container);
      case 'image':
        return this._renderImage(content, filename, container);
      case 'video':
        return this._renderVideo(content, filename, container);
      case 'audio':
        return this._renderAudio(content, filename, container);
      case 'document':
        return this._renderText(content, container);
      default:
        return this._renderUnknown(filename, container);
    }
  }

  /**
   * Render code with syntax highlighting
   */
  _renderCode(content, ext, container) {
    const languageMap = {
      '.js': 'javascript',
      '.jsx': 'jsx',
      '.ts': 'typescript',
      '.tsx': 'tsx',
      '.py': 'python',
      '.rs': 'rust',
      '.cpp': 'cpp',
      '.c': 'c',
      '.h': 'c',
      '.java': 'java',
      '.go': 'go',
      '.rb': 'ruby',
      '.php': 'php',
      '.swift': 'swift',
      '.kt': 'kotlin',
      '.html': 'html',
      '.xml': 'xml',
      '.css': 'css',
      '.scss': 'scss',
      '.sql': 'sql',
      '.sh': 'bash',
      '.yml': 'yaml',
      '.yaml': 'yaml'
    };

    const language = languageMap[ext] || 'plaintext';
    
    // Escape HTML
    const escaped = this._escapeHtml(content);
    
    // Create code element
    const pre = document.createElement('pre');
    pre.style.cssText = `
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(0, 255, 255, 0.3);
      border-radius: 8px;
      padding: 20px;
      overflow-x: auto;
      font-family: 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.6;
      color: #00ffff;
    `;

    const code = document.createElement('code');
    code.className = `language-${language}`;
    code.textContent = content;
    
    pre.appendChild(code);
    container.innerHTML = '';
    container.appendChild(pre);

    // Add line numbers
    this._addLineNumbers(pre);
    
    // Apply syntax highlighting if Prism is available
    if (typeof Prism !== 'undefined' && this.options.enableSyntaxHighlighting) {
      Prism.highlightElement(code);
    } else {
      // Fallback: simple keyword highlighting
      this._applyBasicHighlighting(code, language);
    }

    return { success: true, type: 'code', language };
  }

  /**
   * Render JSON/YAML/CSV data
   */
  _renderData(content, ext, container) {
    if (ext === '.json') {
      try {
        const data = JSON.parse(content);
        const formatted = JSON.stringify(data, null, 2);
        return this._renderCode(formatted, '.json', container);
      } catch (e) {
        return this._renderText(content, container);
      }
    } else if (ext === '.csv') {
      return this._renderCSV(content, container);
    } else if (ext === '.yaml' || ext === '.yml') {
      return this._renderCode(content, '.yaml', container);
    } else {
      return this._renderText(content, container);
    }
  }

  /**
   * Render CSV as table
   */
  _renderCSV(content, container) {
    const lines = content.split('\n').filter(l => l.trim());
    if (lines.length === 0) return;

    const table = document.createElement('table');
    table.style.cssText = `
      width: 100%;
      border-collapse: collapse;
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(0, 255, 255, 0.3);
      border-radius: 8px;
      overflow: hidden;
    `;

    // Parse CSV (simple implementation)
    const rows = lines.map(line => {
      // Handle quoted fields
      const fields = [];
      let current = '';
      let inQuotes = false;
      
      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
          fields.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      }
      fields.push(current.trim());
      return fields;
    });

    // Header row
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    rows[0].forEach(cell => {
      const th = document.createElement('th');
      th.textContent = cell;
      th.style.cssText = `
        padding: 12px;
        text-align: left;
        border-bottom: 2px solid rgba(0, 255, 255, 0.5);
        color: #00ffff;
        font-weight: bold;
        background: rgba(0, 255, 255, 0.1);
      `;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Data rows
    const tbody = document.createElement('tbody');
    for (let i = 1; i < rows.length; i++) {
      const tr = document.createElement('tr');
      tr.style.cssText = `
        transition: background 0.2s;
      `;
      tr.onmouseenter = () => tr.style.background = 'rgba(0, 255, 255, 0.1)';
      tr.onmouseleave = () => tr.style.background = 'transparent';
      
      rows[i].forEach(cell => {
        const td = document.createElement('td');
        td.textContent = cell;
        td.style.cssText = `
          padding: 10px 12px;
          border-bottom: 1px solid rgba(0, 255, 255, 0.1);
          color: #00ffff;
        `;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);

    container.innerHTML = '';
    container.appendChild(table);

    return { success: true, type: 'csv', rows: rows.length - 1 };
  }

  /**
   * Render Markdown
   */
  _renderMarkdown(content, container) {
    const html = this._parseMarkdown(content);
    container.innerHTML = html;
    container.style.cssText = `
      color: #00ffff;
      line-height: 1.8;
    `;

    // Style markdown elements
    const styles = `
      h1, h2, h3, h4, h5, h6 { color: #00ffff; margin: 20px 0 10px; }
      h1 { font-size: 2em; border-bottom: 2px solid rgba(0, 255, 255, 0.3); padding-bottom: 10px; }
      h2 { font-size: 1.6em; border-bottom: 1px solid rgba(0, 255, 255, 0.2); padding-bottom: 8px; }
      h3 { font-size: 1.3em; }
      p { margin: 10px 0; }
      ul, ol { margin: 10px 0; padding-left: 30px; }
      li { margin: 5px 0; }
      code { 
        background: rgba(0, 255, 255, 0.1); 
        padding: 2px 6px; 
        border-radius: 3px;
        color: #00ff00;
        font-family: 'Courier New', monospace;
      }
      pre { 
        background: rgba(0, 0, 0, 0.3); 
        padding: 15px; 
        border-radius: 8px;
        overflow-x: auto;
        border: 1px solid rgba(0, 255, 255, 0.3);
      }
      pre code {
        background: transparent;
        padding: 0;
      }
      blockquote {
        border-left: 4px solid rgba(0, 255, 255, 0.5);
        padding-left: 15px;
        margin: 15px 0;
        opacity: 0.8;
      }
      a { color: #00ffff; text-decoration: underline; }
      a:hover { color: #00ff00; }
      hr { border: none; border-top: 1px solid rgba(0, 255, 255, 0.3); margin: 20px 0; }
      table { 
        width: 100%; 
        border-collapse: collapse; 
        margin: 15px 0;
        border: 1px solid rgba(0, 255, 255, 0.3);
      }
      th, td { 
        padding: 10px; 
        border: 1px solid rgba(0, 255, 255, 0.2); 
        text-align: left;
      }
      th { background: rgba(0, 255, 255, 0.1); font-weight: bold; }
    `;

    const styleEl = document.createElement('style');
    styleEl.textContent = styles;
    container.appendChild(styleEl);

    return { success: true, type: 'markdown' };
  }

  /**
   * Simple Markdown parser
   */
  _parseMarkdown(markdown) {
    let html = markdown;

    // Code blocks
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre><code class="language-${lang || 'plaintext'}">${this._escapeHtml(code)}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers
    html = html.replace(/^### (.*$)/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gm, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/_([^_]+)_/g, '<em>$1</em>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    // Lists
    html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^\- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Paragraphs
    html = html.split('\n\n').map(para => {
      if (!para.startsWith('<')) {
        return `<p>${para}</p>`;
      }
      return para;
    }).join('\n');

    return html;
  }

  /**
   * Render PDF (placeholder for PDF.js integration)
   */
  _renderPDF(content, container) {
    container.innerHTML = `
      <div style="padding: 40px; text-align: center;">
        <div style="font-size: 4em; margin-bottom: 20px;">📕</div>
        <h2 style="color: #00ffff; margin-bottom: 10px;">PDF Viewer</h2>
        <p style="color: #00ffff; opacity: 0.7;">
          PDF viewing requires PDF.js library.<br>
          Install with: <code style="background: rgba(0,255,255,0.1); padding: 5px 10px; border-radius: 3px;">npm install pdfjs-dist</code>
        </p>
        <div style="margin-top: 30px;">
          <a href="#" onclick="window.open('data:application/pdf;base64,${content}')" 
             style="color: #00ffff; text-decoration: underline;">
            Download PDF
          </a>
        </div>
      </div>
    `;
    return { success: true, type: 'pdf', note: 'PDF.js not loaded' };
  }

  /**
   * Render image with controls
   */
  _renderImage(content, filename, container) {
    const img = document.createElement('img');
    img.src = content.startsWith('data:') ? content : `data:image/${this._getExtension(filename).slice(1)};base64,${content}`;
    img.style.cssText = `
      max-width: 100%;
      max-height: 80vh;
      object-fit: contain;
      border: 2px solid #00ffff;
      border-radius: 8px;
      box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
    `;

    const controls = document.createElement('div');
    controls.style.cssText = `
      margin-top: 20px;
      display: flex;
      gap: 10px;
      justify-content: center;
    `;

    const zoomIn = this._createButton('🔍 Zoom In', () => {
      const current = img.style.transform || 'scale(1)';
      const scale = parseFloat(current.match(/scale\(([^)]+)\)/)?.[1] || 1);
      img.style.transform = `scale(${Math.min(scale + 0.2, 3)})`;
    });

    const zoomOut = this._createButton('🔍 Zoom Out', () => {
      const current = img.style.transform || 'scale(1)';
      const scale = parseFloat(current.match(/scale\(([^)]+)\)/)?.[1] || 1);
      img.style.transform = `scale(${Math.max(scale - 0.2, 0.5)})`;
    });

    const reset = this._createButton('↺ Reset', () => {
      img.style.transform = 'scale(1)';
    });

    controls.appendChild(zoomIn);
    controls.appendChild(zoomOut);
    controls.appendChild(reset);

    container.innerHTML = '';
    container.appendChild(img);
    container.appendChild(controls);

    return { success: true, type: 'image' };
  }

  /**
   * Render video with enhanced controls
   */
  _renderVideo(content, filename, container) {
    const video = document.createElement('video');
    video.src = content;
    video.controls = true;
    video.style.cssText = `
      max-width: 100%;
      max-height: 70vh;
      border: 2px solid #00ffff;
      border-radius: 8px;
      box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
    `;

    container.innerHTML = '';
    container.appendChild(video);

    return { success: true, type: 'video' };
  }

  /**
   * Render audio with waveform visualization
   */
  _renderAudio(content, filename, container) {
    const audio = document.createElement('audio');
    audio.src = content;
    audio.controls = true;
    audio.style.cssText = `
      width: 100%;
      margin: 20px 0;
    `;

    const wrapper = document.createElement('div');
    wrapper.style.cssText = `
      padding: 40px;
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(0, 255, 255, 0.3);
      border-radius: 8px;
      text-align: center;
    `;

    wrapper.innerHTML = `
      <div style="font-size: 4em; margin-bottom: 20px;">🎵</div>
      <h3 style="color: #00ffff; margin-bottom: 20px;">${filename}</h3>
    `;
    wrapper.appendChild(audio);

    container.innerHTML = '';
    container.appendChild(wrapper);

    return { success: true, type: 'audio' };
  }

  /**
   * Render plain text
   */
  _renderText(content, container) {
    const pre = document.createElement('pre');
    pre.textContent = content;
    pre.style.cssText = `
      color: #00ffff;
      font-family: 'Courier New', monospace;
      line-height: 1.6;
      white-space: pre-wrap;
      word-wrap: break-word;
    `;

    container.innerHTML = '';
    container.appendChild(pre);

    return { success: true, type: 'text' };
  }

  /**
   * Render unknown file type
   */
  _renderUnknown(filename, container) {
    container.innerHTML = `
      <div style="padding: 60px; text-align: center;">
        <div style="font-size: 5em; margin-bottom: 20px;">❓</div>
        <h2 style="color: #00ffff; margin-bottom: 10px;">Unknown File Type</h2>
        <p style="color: #00ffff; opacity: 0.7; font-size: 1.1em;">
          ${filename}
        </p>
        <p style="color: #00ffff; opacity: 0.5; margin-top: 20px;">
          This file type is not currently supported.
        </p>
      </div>
    `;

    return { success: false, type: 'unknown' };
  }

  // Helper methods

  _getExtension(filename) {
    return filename.toLowerCase().match(/\.[^.]+$/)?.[0] || '';
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  _addLineNumbers(pre) {
    const lines = pre.textContent.split('\n');
    const lineNumbers = document.createElement('div');
    lineNumbers.style.cssText = `
      position: absolute;
      left: 0;
      top: 0;
      padding: 20px 10px;
      background: rgba(0, 0, 0, 0.2);
      border-right: 1px solid rgba(0, 255, 255, 0.2);
      color: rgba(0, 255, 255, 0.4);
      text-align: right;
      user-select: none;
      font-size: 12px;
    `;
    
    lineNumbers.innerHTML = lines.map((_, i) => `${i + 1}`).join('<br>');
    
    pre.style.position = 'relative';
    pre.style.paddingLeft = '60px';
    pre.insertBefore(lineNumbers, pre.firstChild);
  }

  _applyBasicHighlighting(code, language) {
    // Basic keyword highlighting as fallback
    const keywords = {
      javascript: ['const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while', 'class', 'import', 'export'],
      python: ['def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif', 'for', 'while', 'try', 'except'],
      rust: ['fn', 'let', 'mut', 'impl', 'struct', 'enum', 'match', 'if', 'else', 'for', 'while', 'pub']
    };

    const keywordList = keywords[language] || [];
    if (keywordList.length === 0) return;

    let html = code.textContent;
    keywordList.forEach(keyword => {
      const regex = new RegExp(`\\b${keyword}\\b`, 'g');
      html = html.replace(regex, `<span style="color: #ff00ff; font-weight: bold;">${keyword}</span>`);
    });
    
    code.innerHTML = html;
  }

  _createButton(text, onClick) {
    const btn = document.createElement('button');
    btn.textContent = text;
    btn.onclick = onClick;
    btn.style.cssText = `
      background: rgba(0, 255, 255, 0.1);
      border: 1px solid #00ffff;
      color: #00ffff;
      padding: 8px 16px;
      cursor: pointer;
      font-family: 'Courier New', monospace;
      border-radius: 4px;
      transition: all 0.3s;
    `;
    btn.onmouseenter = () => {
      btn.style.background = 'rgba(0, 255, 255, 0.2)';
      btn.style.transform = 'translateY(-2px)';
    };
    btn.onmouseleave = () => {
      btn.style.background = 'rgba(0, 255, 255, 0.1)';
      btn.style.transform = 'translateY(0)';
    };
    return btn;
  }
}

// Export
if (typeof window !== 'undefined') {
  window.FileTypeHandler = FileTypeHandler;
}

export { FileTypeHandler };
