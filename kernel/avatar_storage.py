"""
Avatar Storage System
Save and load custom avatar configurations
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import shutil

logger = logging.getLogger("AIOS.AvatarStorage")

class AvatarStorage:
    """Manage custom avatar storage and retrieval"""
    
    STORAGE_DIR = Path.home() / ".aios" / "avatars"
    AVATARS_INDEX = STORAGE_DIR / "avatars.json"
    
    def __init__(self):
        self.storage_dir = self.STORAGE_DIR
        self.index_file = self.AVATARS_INDEX
        self._ensure_storage_exists()
        self.index = self._load_index()
    
    def _ensure_storage_exists(self):
        """Create storage directory if it doesn't exist"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.index_file.exists():
            self._save_index({})
    
    def _load_index(self) -> Dict[str, Any]:
        """Load the avatar index"""
        try:
            with open(self.index_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load avatar index: {e}")
            return {}
    
    def _save_index(self, index: Dict[str, Any]):
        """Save the avatar index"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save avatar index: {e}")
    
    def save_avatar(self, name: str, params: Dict[str, Any], 
                   glb_path: Optional[str] = None, 
                   tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Save a custom avatar configuration
        
        Args:
            name: Avatar name
            params: Avatar parameters (head_radius, colors, etc.)
            glb_path: Path to the GLB file (optional)
            tags: List of tags for categorization
        
        Returns:
            Dictionary with save result
        """
        try:
            avatar_id = self._generate_id(name)
            avatar_dir = self.storage_dir / avatar_id
            avatar_dir.mkdir(parents=True, exist_ok=True)
            
            # Save parameters
            params_file = avatar_dir / "params.json"
            with open(params_file, 'w') as f:
                json.dump(params, f, indent=2)
            
            # Copy GLB file if provided
            glb_dest = None
            if glb_path and Path(glb_path).exists():
                glb_dest = avatar_dir / "avatar.glb"
                shutil.copy2(glb_path, glb_dest)
            
            # Create metadata
            metadata = {
                "id": avatar_id,
                "name": name,
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat(),
                "tags": tags or [],
                "has_glb": glb_dest is not None,
                "params": params
            }
            
            # Save metadata
            metadata_file = avatar_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Update index
            self.index[avatar_id] = {
                "name": name,
                "created": metadata["created"],
                "modified": metadata["modified"],
                "tags": metadata["tags"],
                "has_glb": metadata["has_glb"]
            }
            self._save_index(self.index)
            
            logger.info(f"Saved avatar: {name} ({avatar_id})")
            
            return {
                "success": True,
                "avatar_id": avatar_id,
                "path": str(avatar_dir),
                "message": f"Avatar '{name}' saved successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to save avatar {name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def load_avatar(self, avatar_id: str) -> Optional[Dict[str, Any]]:
        """
        Load avatar configuration by ID
        
        Args:
            avatar_id: Avatar identifier
        
        Returns:
            Avatar data or None if not found
        """
        try:
            avatar_dir = self.storage_dir / avatar_id
            
            if not avatar_dir.exists():
                logger.warning(f"Avatar not found: {avatar_id}")
                return None
            
            # Load metadata
            metadata_file = avatar_dir / "metadata.json"
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Load parameters
            params_file = avatar_dir / "params.json"
            with open(params_file, 'r') as f:
                params = json.load(f)
            
            # Check for GLB
            glb_file = avatar_dir / "avatar.glb"
            glb_path = str(glb_file) if glb_file.exists() else None
            
            return {
                "id": avatar_id,
                "name": metadata["name"],
                "params": params,
                "glb_path": glb_path,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to load avatar {avatar_id}: {e}")
            return None
    
    def list_avatars(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all saved avatars
        
        Args:
            tag: Filter by tag (optional)
        
        Returns:
            List of avatar summaries
        """
        avatars = []
        
        for avatar_id, info in self.index.items():
            if tag and tag not in info.get("tags", []):
                continue
            
            avatars.append({
                "id": avatar_id,
                "name": info["name"],
                "created": info["created"],
                "modified": info["modified"],
                "tags": info.get("tags", []),
                "has_glb": info.get("has_glb", False)
            })
        
        # Sort by modified date (newest first)
        avatars.sort(key=lambda x: x["modified"], reverse=True)
        
        return avatars
    
    def delete_avatar(self, avatar_id: str) -> Dict[str, Any]:
        """
        Delete an avatar
        
        Args:
            avatar_id: Avatar identifier
        
        Returns:
            Dictionary with delete result
        """
        try:
            avatar_dir = self.storage_dir / avatar_id
            
            if not avatar_dir.exists():
                return {
                    "success": False,
                    "error": f"Avatar not found: {avatar_id}"
                }
            
            # Remove directory
            shutil.rmtree(avatar_dir)
            
            # Update index
            if avatar_id in self.index:
                name = self.index[avatar_id]["name"]
                del self.index[avatar_id]
                self._save_index(self.index)
            else:
                name = avatar_id
            
            logger.info(f"Deleted avatar: {name} ({avatar_id})")
            
            return {
                "success": True,
                "message": f"Avatar '{name}' deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete avatar {avatar_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_avatar(self, avatar_id: str, params: Optional[Dict[str, Any]] = None,
                     name: Optional[str] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Update avatar configuration
        
        Args:
            avatar_id: Avatar identifier
            params: New parameters (optional)
            name: New name (optional)
            tags: New tags (optional)
        
        Returns:
            Dictionary with update result
        """
        try:
            avatar_dir = self.storage_dir / avatar_id
            
            if not avatar_dir.exists():
                return {
                    "success": False,
                    "error": f"Avatar not found: {avatar_id}"
                }
            
            # Load existing metadata
            metadata_file = avatar_dir / "metadata.json"
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Update fields
            if name:
                metadata["name"] = name
            if tags is not None:
                metadata["tags"] = tags
            if params:
                metadata["params"] = params
                # Save new params
                params_file = avatar_dir / "params.json"
                with open(params_file, 'w') as f:
                    json.dump(params, f, indent=2)
            
            metadata["modified"] = datetime.now().isoformat()
            
            # Save metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Update index
            self.index[avatar_id] = {
                "name": metadata["name"],
                "created": metadata["created"],
                "modified": metadata["modified"],
                "tags": metadata["tags"],
                "has_glb": metadata.get("has_glb", False)
            }
            self._save_index(self.index)
            
            logger.info(f"Updated avatar: {metadata['name']} ({avatar_id})")
            
            return {
                "success": True,
                "message": f"Avatar '{metadata['name']}' updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to update avatar {avatar_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def export_avatar(self, avatar_id: str, export_path: str) -> Dict[str, Any]:
        """
        Export avatar as a shareable package
        
        Args:
            avatar_id: Avatar identifier
            export_path: Destination path for export
        
        Returns:
            Dictionary with export result
        """
        try:
            avatar_dir = self.storage_dir / avatar_id
            
            if not avatar_dir.exists():
                return {
                    "success": False,
                    "error": f"Avatar not found: {avatar_id}"
                }
            
            # Create archive
            export_file = Path(export_path)
            shutil.make_archive(
                str(export_file.with_suffix('')),
                'zip',
                avatar_dir
            )
            
            logger.info(f"Exported avatar {avatar_id} to {export_path}")
            
            return {
                "success": True,
                "path": str(export_file.with_suffix('.zip')),
                "message": "Avatar exported successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to export avatar {avatar_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def import_avatar(self, import_path: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Import avatar from a package
        
        Args:
            import_path: Path to avatar package
            name: Optional new name for imported avatar
        
        Returns:
            Dictionary with import result
        """
        try:
            import_file = Path(import_path)
            
            if not import_file.exists():
                return {
                    "success": False,
                    "error": f"Import file not found: {import_path}"
                }
            
            # Extract to temp directory
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                shutil.unpack_archive(import_file, temp_dir)
                
                # Load metadata
                metadata_file = Path(temp_dir) / "metadata.json"
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Load params
                params_file = Path(temp_dir) / "params.json"
                with open(params_file, 'r') as f:
                    params = json.load(f)
                
                # Check for GLB
                glb_file = Path(temp_dir) / "avatar.glb"
                glb_path = str(glb_file) if glb_file.exists() else None
                
                # Save with new ID
                avatar_name = name or metadata["name"]
                result = self.save_avatar(
                    avatar_name,
                    params,
                    glb_path,
                    metadata.get("tags", [])
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to import avatar from {import_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def _generate_id(name: str) -> str:
        """Generate a unique ID from name"""
        import hashlib
        import time
        
        # Use name + timestamp for uniqueness
        unique_string = f"{name}_{time.time()}"
        hash_obj = hashlib.md5(unique_string.encode())
        return f"avatar_{hash_obj.hexdigest()[:12]}"


# Global storage instance
_storage = None

def get_avatar_storage() -> AvatarStorage:
    """Get global avatar storage instance"""
    global _storage
    if _storage is None:
        _storage = AvatarStorage()
    return _storage
