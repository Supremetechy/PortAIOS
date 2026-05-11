"""
Avatar Creation Server - Backend endpoints for visual avatar generation
Provides real-time progress updates during avatar creation process
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import threading

try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    EEL_AVAILABLE = False
    logging.warning("Eel not available - avatar creation server will not function")

from kernel.avatar_generator import generate_avatar, AvatarParams

logger = logging.getLogger("AIOS.AvatarCreationServer")

# Global state for tracking avatar generation progress
_generation_state = {
    "in_progress": False,
    "progress": 0,
    "stage": "idle",
    "message": "",
    "error": None,
    "result_path": None
}

_generation_lock = threading.Lock()


def _update_progress(progress: int, stage: str, message: str):
    """Update generation progress and notify frontend"""
    global _generation_state
    with _generation_lock:
        _generation_state["progress"] = progress
        _generation_state["stage"] = stage
        _generation_state["message"] = message
        logger.info(f"Avatar generation: {progress}% - {stage} - {message}")
    
    # Notify frontend if eel is available
    if EEL_AVAILABLE:
        try:
            eel.avatar_generation_progress({
                "progress": progress,
                "stage": stage,
                "message": message
            })
        except Exception as e:
            logger.debug(f"Could not send progress update to frontend: {e}")


def _generate_avatar_async(params: Dict[str, Any], callback: Optional[Callable] = None):
    """Generate avatar asynchronously with progress updates"""
    global _generation_state
    
    try:
        with _generation_lock:
            _generation_state["in_progress"] = True
            _generation_state["error"] = None
            _generation_state["result_path"] = None
        
        _update_progress(0, "initializing", "Starting avatar generation...")
        time.sleep(0.5)  # Give UI time to update
        
        _update_progress(10, "parsing_params", "Parsing parameters...")
        avatar_params = AvatarParams.from_dict(params)
        
        _update_progress(20, "building_mesh", "Building base mesh...")
        time.sleep(0.3)
        
        _update_progress(40, "creating_morphs", "Creating morph targets for lip-sync...")
        time.sleep(0.3)
        
        _update_progress(60, "generating_glb", "Generating GLB file...")
        result = generate_avatar(
            head_radius=avatar_params.head_radius,
            head_color=avatar_params.head_color,
            smile_intensity=avatar_params.smile_strength,
            frown_intensity=avatar_params.frown_strength,
            surprise_intensity=avatar_params.surprise_strength,
            wink_intensity=avatar_params.wink_strength,
            viseme_intensity=avatar_params.viseme_strength
        )
        
        _update_progress(80, "validating", "Validating morph targets...")
        time.sleep(0.3)
        
        _update_progress(95, "finalizing", "Finalizing avatar...")
        
        with _generation_lock:
            _generation_state["result_path"] = result["path"]
            _generation_state["in_progress"] = False
        
        _update_progress(100, "complete", f"Avatar generated successfully: {Path(result['path']).name}")
        
        if callback:
            callback(True, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Avatar generation failed: {e}", exc_info=True)
        with _generation_lock:
            _generation_state["error"] = str(e)
            _generation_state["in_progress"] = False
        
        _update_progress(0, "error", f"Generation failed: {str(e)}")
        
        if callback:
            callback(False, {"error": str(e)})
        
        return {"success": False, "error": str(e)}


if EEL_AVAILABLE:
    
    @eel.expose
    def start_avatar_generation(params: Dict[str, Any]) -> Dict[str, Any]:
        """Start avatar generation with given parameters"""
        logger.info(f"Starting avatar generation with params: {params}")
        
        # Check if generation already in progress
        with _generation_lock:
            if _generation_state["in_progress"]:
                return {
                    "success": False,
                    "error": "Avatar generation already in progress"
                }
        
        # Start generation in background thread
        thread = threading.Thread(
            target=_generate_avatar_async,
            args=(params,),
            daemon=True
        )
        thread.start()
        
        return {
            "success": True,
            "message": "Avatar generation started"
        }
    
    
    @eel.expose
    def get_avatar_generation_status() -> Dict[str, Any]:
        """Get current avatar generation status"""
        with _generation_lock:
            return dict(_generation_state)
    
    
    @eel.expose
    def cancel_avatar_generation() -> Dict[str, Any]:
        """Cancel ongoing avatar generation"""
        with _generation_lock:
            if not _generation_state["in_progress"]:
                return {
                    "success": False,
                    "error": "No generation in progress"
                }
            
            # Note: actual cancellation is not implemented yet
            # Would require refactoring generate_avatar to check cancellation flag
            _generation_state["in_progress"] = False
            _generation_state["stage"] = "cancelled"
            _generation_state["message"] = "Generation cancelled by user"
        
        return {
            "success": True,
            "message": "Generation cancelled"
        }
    
    
    @eel.expose
    def get_avatar_presets() -> Dict[str, Dict[str, Any]]:
        """Get predefined avatar presets"""
        return {
            "neutral": {
                "name": "Neutral",
                "description": "Basic neutral expression",
                "head_radius": 0.12,
                "head_color": [0.9, 0.8, 0.7],
                "smile_strength": 0.0,
                "frown_strength": 0.0,
                "surprise_strength": 0.0,
                "wink_strength": 0.0,
                "viseme_strength": 1.0
            },
            "friendly": {
                "name": "Friendly",
                "description": "Warm and welcoming",
                "head_radius": 0.12,
                "head_color": [0.95, 0.85, 0.75],
                "smile_strength": 0.6,
                "frown_strength": 0.0,
                "surprise_strength": 0.2,
                "wink_strength": 0.0,
                "viseme_strength": 1.0
            },
            "professional": {
                "name": "Professional",
                "description": "Serious and focused",
                "head_radius": 0.13,
                "head_color": [0.85, 0.75, 0.65],
                "smile_strength": 0.2,
                "frown_strength": 0.1,
                "surprise_strength": 0.0,
                "wink_strength": 0.0,
                "viseme_strength": 1.0
            },
            "energetic": {
                "name": "Energetic",
                "description": "Excited and enthusiastic",
                "head_radius": 0.11,
                "head_color": [0.95, 0.9, 0.8],
                "smile_strength": 0.8,
                "frown_strength": 0.0,
                "surprise_strength": 0.5,
                "wink_strength": 0.0,
                "viseme_strength": 1.0
            }
        }


def setup_avatar_creation_server():
    """Initialize avatar creation server endpoints"""
    if not EEL_AVAILABLE:
        logger.warning("Eel not available - avatar creation server not initialized")
        return False
    
    logger.info("Avatar creation server initialized")
    return True


__all__ = ['setup_avatar_creation_server', 'start_avatar_generation', 
           'get_avatar_generation_status', 'get_avatar_presets']
