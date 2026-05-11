"""
AI-Powered File Operations for AIOS Dynamic UI
Integrates with the agent executor to provide intelligent file operations.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("AIOS.AIFileOps")

try:
    import eel
except ImportError:
    eel = None  # type: ignore[assignment]
    logger.warning("Eel not available - AI file operations will run in limited mode")
EEL_AVAILABLE = eel is not None


class AIFileOperations:
    """AI-powered file operations integrated with agent executor"""
    
    def __init__(self, ui_data_provider=None):
        self.ui_data_provider = ui_data_provider
        self.agent_executor = None
        self._init_agent()
        logger.info("AI File Operations initialized")
    
    def _init_agent(self):
        """Initialize agent executor if available"""
        try:
            from kernel.agent_executor import AgentExecutor
            self.agent_executor = AgentExecutor()
            logger.info("Agent executor connected for AI file operations")
        except Exception as e:
            logger.warning(f"Agent executor not available: {e}")
    
    async def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze file content using AI
        Returns summary, key points, file type info, etc.
        """
        try:
            if not self.ui_data_provider:
                return {'error': 'UI data provider not available'}
            
            # Get file content
            file_info = self.ui_data_provider.get_file_content(file_path)
            if 'error' in file_info:
                return file_info
            
            # Prepare analysis prompt
            prompt = f"""Analyze this file and provide:
1. Brief summary (2-3 sentences)
2. Key points or main topics (3-5 bullet points)
3. File type and purpose
4. Any notable patterns or issues

File: {file_info['title']}
Type: {file_info['type']}
Content preview:
{file_info.get('content', '')[:1000]}...
"""
            
            # Use agent executor if available
            if self.agent_executor:
                result = self.agent_executor.execute(prompt)
                return {
                    'success': True,
                    'analysis': result,
                    'file': file_info['title'],
                    'type': file_info['type']
                }
            else:
                # Fallback: basic analysis
                return self._basic_file_analysis(file_info)
        
        except Exception as e:
            logger.error(f"Error analyzing file: {e}")
            return {'error': str(e)}
    
    def _basic_file_analysis(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Basic file analysis without AI"""
        content = file_info.get('content', '')
        lines = content.split('\n') if isinstance(content, str) else []
        
        return {
            'success': True,
            'analysis': {
                'summary': f"File contains {len(lines)} lines",
                'size': file_info.get('size', 'Unknown'),
                'type': file_info.get('type', 'Unknown'),
                'line_count': len(lines),
                'word_count': len(content.split()) if isinstance(content, str) else 0
            },
            'file': file_info['title']
        }
    
    async def smart_search(self, query: str, search_path: Optional[str] = None) -> Dict[str, Any]:
        """
        AI-enhanced file search
        Uses semantic understanding to find relevant files
        """
        try:
            if not self.ui_data_provider:
                return {'error': 'UI data provider not available'}
            
            # Get initial search results
            results = self.ui_data_provider.search_files(query, search_path)
            
            # If agent is available, enhance results with AI ranking
            if self.agent_executor and len(results) > 0:
                prompt = f"""Given this search query: "{query}"
                
Rank these files by relevance (most relevant first):
{json.dumps([{'name': r['name'], 'path': r['path']} for r in results[:20]], indent=2)}

Return JSON array with ranked results including relevance score (0-100).
"""
                
                try:
                    ai_result = self.agent_executor.execute(prompt)
                    # Try to parse AI response as JSON
                    if isinstance(ai_result, str):
                        import re
                        json_match = re.search(r'\[.*\]', ai_result, re.DOTALL)
                        if json_match:
                            ranked = json.loads(json_match.group())
                            return {
                                'success': True,
                                'results': ranked,
                                'query': query,
                                'ai_ranked': True
                            }
                except Exception as e:
                    logger.warning(f"AI ranking failed, using basic results: {e}")
            
            # Return basic results
            return {
                'success': True,
                'results': results,
                'query': query,
                'ai_ranked': False
            }
        
        except Exception as e:
            logger.error(f"Error in smart search: {e}")
            return {'error': str(e)}
    
    async def suggest_organization(self, directory_path: str) -> Dict[str, Any]:
        """
        Suggest how to organize files in a directory
        """
        try:
            if not self.ui_data_provider:
                return {'error': 'UI data provider not available'}
            
            # Get directory contents
            dir_info = self.ui_data_provider.get_directory_contents(directory_path)
            if 'error' in dir_info:
                return dir_info
            
            files = dir_info.get('files', [])
            
            if not self.agent_executor:
                return self._basic_organization_suggestion(files)
            
            # Create prompt for AI
            prompt = f"""Analyze these files and suggest an organization structure:

Files in {directory_path}:
{json.dumps([{'name': f['name'], 'type': f['type']} for f in files], indent=2)}

Suggest:
1. Folder structure to organize these files
2. Which files should go in which folders
3. Any files that should be deleted or archived

Return as JSON with structure:
{{
  "folders": [
    {{"name": "folder_name", "purpose": "description", "files": ["file1", "file2"]}}
  ],
  "recommendations": ["suggestion 1", "suggestion 2"]
}}
"""
            
            result = self.agent_executor.execute(prompt)
            
            return {
                'success': True,
                'suggestions': result,
                'path': directory_path,
                'file_count': len(files)
            }
        
        except Exception as e:
            logger.error(f"Error suggesting organization: {e}")
            return {'error': str(e)}
    
    def _basic_organization_suggestion(self, files: List[Dict]) -> Dict[str, Any]:
        """Basic organization suggestions without AI"""
        # Group by file type
        by_type = {}
        for file in files:
            ftype = file.get('type', 'unknown')
            if ftype not in by_type:
                by_type[ftype] = []
            by_type[ftype].append(file['name'])
        
        suggestions = []
        if 'image' in by_type and len(by_type['image']) > 3:
            suggestions.append(f"Create 'Images' folder for {len(by_type['image'])} image files")
        if 'document' in by_type and len(by_type['document']) > 3:
            suggestions.append(f"Create 'Documents' folder for {len(by_type['document'])} document files")
        if 'code' in by_type and len(by_type['code']) > 3:
            suggestions.append(f"Create 'Code' folder for {len(by_type['code'])} code files")
        
        return {
            'success': True,
            'suggestions': {
                'by_type': by_type,
                'recommendations': suggestions
            }
        }
    
    async def generate_file_summary(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Generate a summary of multiple files
        """
        try:
            if not self.ui_data_provider or not self.agent_executor:
                return {'error': 'Required services not available'}
            
            # Collect file information
            file_infos = []
            for path in file_paths[:10]:  # Limit to 10 files
                info = self.ui_data_provider.get_file_content(path)
                if 'error' not in info:
                    file_infos.append({
                        'name': info['title'],
                        'type': info['type'],
                        'size': info.get('size', 'Unknown'),
                        'preview': str(info.get('content', ''))[:200]
                    })
            
            prompt = f"""Provide a summary of these files:

{json.dumps(file_infos, indent=2)}

Include:
1. Overall purpose of these files
2. Relationships between files
3. Main topics covered
4. Any missing or recommended files
"""
            
            result = self.agent_executor.execute(prompt)
            
            return {
                'success': True,
                'summary': result,
                'file_count': len(file_infos)
            }
        
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {'error': str(e)}
    
    async def suggest_file_actions(self, file_path: str) -> Dict[str, Any]:
        """
        Suggest actions for a file based on its content
        """
        try:
            if not self.ui_data_provider:
                return {'error': 'UI data provider not available'}
            
            file_info = self.ui_data_provider.get_file_content(file_path)
            if 'error' in file_info:
                return file_info
            
            if not self.agent_executor:
                return self._basic_file_actions(file_info)
            
            prompt = f"""Suggest useful actions for this file:

File: {file_info['title']}
Type: {file_info['type']}
Size: {file_info.get('size', 'Unknown')}
Content preview:
{str(file_info.get('content', ''))[:500]}...

Suggest 3-5 actions the user might want to take with this file.
Return as JSON array: [{{"action": "action_name", "description": "why this is useful"}}]
"""
            
            result = self.agent_executor.execute(prompt)
            
            return {
                'success': True,
                'actions': result,
                'file': file_info['title']
            }
        
        except Exception as e:
            logger.error(f"Error suggesting actions: {e}")
            return {'error': str(e)}
    
    def _basic_file_actions(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Basic action suggestions without AI"""
        actions = [
            {'action': 'view', 'description': 'Open in document viewer'},
            {'action': 'edit', 'description': 'Edit file content'},
        ]
        
        ftype = file_info.get('type', '')
        if ftype == 'code':
            actions.append({'action': 'run', 'description': 'Execute code file'})
        elif ftype == 'image':
            actions.append({'action': 'enhance', 'description': 'Enhance image quality'})
        elif ftype == 'document':
            actions.append({'action': 'summarize', 'description': 'Generate summary'})
        
        return {
            'success': True,
            'actions': actions,
            'file': file_info['title']
        }


# Eel integration
if eel is not None:
    ai_file_ops = None
    
    def setup_ai_file_operations(ui_data_provider=None):
        """Initialize AI file operations"""
        global ai_file_ops
        ai_file_ops = AIFileOperations(ui_data_provider)
        logger.info("AI File Operations setup complete")
        return ai_file_ops
    
    @eel.expose
    async def ai_analyze_file(file_path: str) -> Dict[str, Any]:
        """Analyze file with AI"""
        if not ai_file_ops:
            return {'error': 'AI file operations not initialized'}
        return await ai_file_ops.analyze_file(file_path)
    
    @eel.expose
    async def ai_smart_search(query: str, path: Optional[str] = None) -> Dict[str, Any]:
        """AI-enhanced file search"""
        if not ai_file_ops:
            return {'error': 'AI file operations not initialized'}
        return await ai_file_ops.smart_search(query, path)
    
    @eel.expose
    async def ai_suggest_organization(directory_path: str) -> Dict[str, Any]:
        """Get AI suggestions for organizing files"""
        if not ai_file_ops:
            return {'error': 'AI file operations not initialized'}
        return await ai_file_ops.suggest_organization(directory_path)
    
    @eel.expose
    async def ai_file_summary(file_paths: List[str]) -> Dict[str, Any]:
        """Generate summary of multiple files"""
        if not ai_file_ops:
            return {'error': 'AI file operations not initialized'}
        return await ai_file_ops.generate_file_summary(file_paths)
    
    @eel.expose
    async def ai_file_actions(file_path: str) -> Dict[str, Any]:
        """Get AI-suggested actions for a file"""
        if not ai_file_ops:
            return {'error': 'AI file operations not initialized'}
        return await ai_file_ops.suggest_file_actions(file_path)


# Export
__all__ = ['AIFileOperations', 'setup_ai_file_operations']
