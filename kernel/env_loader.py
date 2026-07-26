"""
Environment Variable Loader

Loads .env file with fallback if python-dotenv is not available.
This module ensures environment variables are loaded regardless of installation method.
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("AIOS.EnvLoader")

_env_loaded = False


def load_env_file(env_path: Optional[Path] = None) -> bool:
    """
    Load environment variables from .env file.
    
    Tries to use python-dotenv if available, falls back to manual parsing.
    
    Args:
        env_path: Path to .env file. If None, uses project root.
    
    Returns:
        True if .env was loaded successfully, False otherwise.
    """
    global _env_loaded
    
    if _env_loaded:
        return True
    
    # Determine .env path
    if env_path is None:
        # Try to find project root .env
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        env_path = project_root / '.env'
    
    if not env_path.exists():
        logger.debug(f".env file not found at {env_path}")
        return False
    
    # Try python-dotenv first
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        logger.info(f"✅ Loaded .env using python-dotenv from {env_path}")
        _env_loaded = True
        return True
    except ImportError:
        logger.debug("python-dotenv not available, using manual parser")
    
    # Fallback to manual parsing
    try:
        loaded_vars = []
        with open(env_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value
                if '=' not in line:
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove surrounding quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Set environment variable (don't override existing)
                if key not in os.environ:
                    os.environ[key] = value
                    loaded_vars.append(key)
        
        if loaded_vars:
            logger.info(f"✅ Loaded .env manually from {env_path} ({len(loaded_vars)} variables)")
            logger.debug(f"   Variables loaded: {', '.join(loaded_vars)}")
        else:
            logger.warning(f"⚠️  No variables loaded from {env_path}")
        
        _env_loaded = True
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load .env file: {e}")
        return False


def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable, ensuring .env is loaded first.
    
    Args:
        key: Environment variable name
        default: Default value if not found
    
    Returns:
        Environment variable value or default
    """
    # Ensure .env is loaded
    load_env_file()
    
    return os.getenv(key, default)


def ensure_env_loaded():
    """Ensure .env file is loaded. Call this at module initialization."""
    load_env_file()


# Auto-load on import
load_env_file()
