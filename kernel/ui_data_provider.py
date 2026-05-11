"""
AIOS UI Data Provider
Provides file system, document, and media data to the dynamic UI frontend.
Integrates with the avatar system to enable visual UI transformations.
"""

import os
import json
import mimetypes
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger("AIOS.UIDataProvider")

try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    logger.warning("Eel not available - UI data provider will run in limited mode")
    EEL_AVAILABLE = False


class UIDataProvider:
    """Provides file system and content data for the dynamic UI"""
    
    def __init__(self, root_path: Optional[Path] = None):
        self.root_path = root_path or Path.home()
        self.current_path = self.root_path
        self.allowed_extensions = {
            'documents': ['.txt', '.md', '.pdf', '.doc', '.docx', '.rtf'],
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'],
            'videos': ['.mp4', '.webm', '.mov', '.avi', '.mkv'],
            'audio': ['.mp3', '.wav', '.ogg', '.flac', '.m4a'],
            'code': ['.py', '.js', '.rs', '.cpp', '.c', '.h', '.java', '.go', '.html', '.css', '.json', '.xml']
        }
        logger.info(f"UIDataProvider initialized with root: {self.root_path}")
    
    def get_directory_contents(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Get contents of a directory for desktop mode"""
        try:
            target_path = Path(path) if path else self.current_path
            
            # Security: ensure path is within allowed root
            if not self._is_safe_path(target_path):
                logger.warning(f"Attempted access to restricted path: {target_path}")
                return {'error': 'Access denied', 'files': [], 'path': str(self.current_path)}
            
            files = []
            total_size = 0
            
            for item in sorted(target_path.iterdir()):
                try:
                    stat = item.stat()
                    file_info = {
                        'name': item.name,
                        'path': str(item),
                        'type': 'folder' if item.is_dir() else self._get_file_type(item),
                        'size': self._format_size(stat.st_size) if item.is_file() else '',
                        'modified': stat.st_mtime,
                        'size_bytes': stat.st_size if item.is_file() else 0
                    }
                    files.append(file_info)
                    if item.is_file():
                        total_size += stat.st_size
                except (PermissionError, OSError) as e:
                    logger.debug(f"Skipping {item}: {e}")
                    continue
            
            return {
                'files': files,
                'path': str(target_path),
                'parent': str(target_path.parent) if target_path != self.root_path else None,
                'total_size': self._format_size(total_size),
                'count': len(files)
            }
        
        except Exception as e:
            logger.error(f"Error reading directory: {e}")
            return {'error': str(e), 'files': [], 'path': str(self.current_path)}
    
    def get_file_content(self, file_path: str, max_size: int = 1024 * 1024) -> Dict[str, Any]:
        """Get content of a file for document viewer mode"""
        try:
            path = Path(file_path)
            
            if not self._is_safe_path(path) or not path.is_file():
                return {'error': 'File not found or access denied'}
            
            file_type = self._get_file_type(path)
            stat = path.stat()
            
            # Check file size
            if stat.st_size > max_size:
                return {
                    'error': f'File too large ({self._format_size(stat.st_size)}). Maximum size: {self._format_size(max_size)}',
                    'title': path.name,
                    'type': file_type
                }
            
            result = {
                'title': path.name,
                'type': file_type,
                'size': self._format_size(stat.st_size),
                'modified': stat.st_mtime,
                'path': str(path)
            }
            
            # Read content based on file type
            if file_type == 'image':
                result['content_type'] = 'image'
                result['url'] = f'file://{path}'
                # For web display, we could base64 encode small images
                if stat.st_size < 500 * 1024:  # 500KB limit for base64
                    with open(path, 'rb') as f:
                        mime_type, _ = mimetypes.guess_type(str(path))
                        b64_data = base64.b64encode(f.read()).decode('utf-8')
                        result['data_url'] = f'data:{mime_type};base64,{b64_data}'
            
            elif file_type == 'video':
                result['content_type'] = 'video'
                result['url'] = f'file://{path}'
            
            elif file_type in ['document', 'code']:
                # Try to read as text
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    result['content_type'] = 'text'
                    result['content'] = self._format_text_content(content, file_type)
                except UnicodeDecodeError:
                    result['content_type'] = 'binary'
                    result['content'] = f'<p>Binary file ({self._format_size(stat.st_size)})</p>'
            
            else:
                result['content_type'] = 'unknown'
                result['content'] = f'<p>Unknown file type: {path.suffix}</p>'
            
            return result
        
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return {'error': str(e)}
    
    def search_files(self, query: str, search_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for files by name"""
        try:
            target_path = Path(search_path) if search_path else self.current_path
            
            if not self._is_safe_path(target_path):
                return []
            
            results = []
            query_lower = query.lower()
            
            for item in target_path.rglob('*'):
                try:
                    if not self._is_safe_path(item):
                        continue
                    
                    if query_lower in item.name.lower():
                        stat = item.stat()
                        results.append({
                            'name': item.name,
                            'path': str(item),
                            'type': 'folder' if item.is_dir() else self._get_file_type(item),
                            'size': self._format_size(stat.st_size) if item.is_file() else '',
                            'parent': str(item.parent)
                        })
                    
                    if len(results) >= 100:  # Limit results
                        break
                
                except (PermissionError, OSError):
                    continue
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return []
    
    def get_recent_files(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently modified files"""
        try:
            files = []
            
            for item in self.current_path.rglob('*'):
                try:
                    if not item.is_file() or not self._is_safe_path(item):
                        continue
                    
                    stat = item.stat()
                    files.append({
                        'name': item.name,
                        'path': str(item),
                        'type': self._get_file_type(item),
                        'size': self._format_size(stat.st_size),
                        'modified': stat.st_mtime
                    })
                
                except (PermissionError, OSError):
                    continue
            
            # Sort by modification time and limit
            files.sort(key=lambda x: x['modified'], reverse=True)
            return files[:limit]
        
        except Exception as e:
            logger.error(f"Error getting recent files: {e}")
            return []
    
    def _get_file_type(self, path: Path) -> str:
        """Determine file type category"""
        ext = path.suffix.lower()
        
        for category, extensions in self.allowed_extensions.items():
            if ext in extensions:
                return category.rstrip('s')  # 'documents' -> 'document'
        
        return 'file'
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _format_text_content(self, content: str, file_type: str) -> str:
        """Format text content as HTML for display"""
        # Escape HTML
        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Add syntax highlighting class for code
        if file_type == 'code':
            return f'<pre><code class="language-auto">{content}</code></pre>'
        
        # Convert markdown-like formatting for documents
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Headers
            if line.startswith('# '):
                formatted_lines.append(f'<h1>{line[2:]}</h1>')
            elif line.startswith('## '):
                formatted_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('### '):
                formatted_lines.append(f'<h3>{line[4:]}</h3>')
            # Lists
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                formatted_lines.append(f'<li>{line.strip()[2:]}</li>')
            # Regular text
            elif line.strip():
                formatted_lines.append(f'<p>{line}</p>')
            else:
                formatted_lines.append('<br>')
        
        return '\n'.join(formatted_lines)
    
    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is within allowed root directory"""
        try:
            path_resolved = path.resolve()
            root_resolved = self.root_path.resolve()
            return path_resolved == root_resolved or root_resolved in path_resolved.parents
        except Exception:
            return False


# Eel exposed functions for frontend integration
if EEL_AVAILABLE:
    ui_provider = UIDataProvider()
    
    @eel.expose
    def get_desktop_files(path: Optional[str] = None) -> Dict[str, Any]:
        """Get directory contents for desktop mode"""
        return ui_provider.get_directory_contents(path)
    
    @eel.expose
    def get_document_content(file_path: str) -> Dict[str, Any]:
        """Get file content for document viewer"""
        return ui_provider.get_file_content(file_path)
    
    @eel.expose
    def search_filesystem(query: str, path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for files"""
        return ui_provider.search_files(query, path)
    
    @eel.expose
    def get_recent_documents(limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently modified files"""
        return ui_provider.get_recent_files(limit)
    
    @eel.expose
    def switch_ui_mode(mode: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle UI mode switches from voice commands or agent actions
        Modes: 'desktop', 'document', 'media', 'terminal', 'browser', 'avatar'
        """
        logger.info(f"UI mode switch requested: {mode}")
        
        result = {'mode': mode, 'success': True}
        
        if mode == 'desktop':
            path = data.get('path') if data else None
            result['data'] = ui_provider.get_directory_contents(path)
        
        elif mode == 'document' and data and 'file_path' in data:
            result['data'] = ui_provider.get_file_content(data['file_path'])
        
        elif mode == 'media' and data:
            # Media data passed through
            result['data'] = data
        
        elif mode == 'terminal':
            result['data'] = {'message': 'Terminal mode activated', 'clear': data.get('clear', False) if data else False}
        
        elif mode == 'browser' and data:
            result['data'] = data
        
        elif mode == 'avatar':
            result['data'] = {'message': 'Returning to avatar mode'}
        
        else:
            result['success'] = False
            result['error'] = 'Invalid mode or missing data'
        
        return result


def setup_ui_data_provider():
    """Initialize UI data provider for AIOS"""
    if EEL_AVAILABLE:
        logger.info("UI Data Provider initialized and exposed to Eel")
        return ui_provider
    else:
        logger.warning("Eel not available - UI Data Provider running in standalone mode")
        return UIDataProvider()


# Export for direct usage
__all__ = ['UIDataProvider', 'setup_ui_data_provider']
