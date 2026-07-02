#!/usr/bin/env python3
"""
PortAIOS Multimodal Integration Layer
Integrates all multimodal components with the existing system
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("AIOS.Integration")

# Import all multimodal components
try:
    from kernel.gesture_controller import setup_gesture_eel_api, get_gesture_controller
    from kernel.gesture_commands import setup_gesture_commands_eel_api, get_gesture_command_mapper
    from kernel.ai_learning_engine import setup_ai_learning_eel_api, get_ai_learning_engine
    from kernel.ai_learning_enhanced import setup_enhanced_ai_eel_api, get_enhanced_ai_engine
    from kernel.multimodal_controller import setup_multimodal_eel_api, get_multimodal_controller
    MULTIMODAL_AVAILABLE = True
except ImportError as e:
    MULTIMODAL_AVAILABLE = False
    logger.error(f"Multimodal components not available: {e}")


def initialize_multimodal_system() -> Dict[str, Any]:
    """
    Initialize all multimodal components
    Returns status of initialization
    """
    if not MULTIMODAL_AVAILABLE:
        return {
            'success': False,
            'error': 'Multimodal components not available',
            'components': {}
        }
    
    logger.info("Initializing multimodal system...")
    
    components = {}
    errors = []
    
    # Initialize gesture controller
    try:
        gesture_controller = get_gesture_controller()
        components['gesture_controller'] = {
            'status': 'initialized',
            'available': True
        }
        logger.info("✓ Gesture controller initialized")
    except Exception as e:
        errors.append(f"Gesture controller: {e}")
        components['gesture_controller'] = {
            'status': 'failed',
            'error': str(e),
            'available': False
        }
    
    # Initialize gesture command mapper
    try:
        gesture_mapper = get_gesture_command_mapper()
        components['gesture_mapper'] = {
            'status': 'initialized',
            'available': True,
            'commands': len(gesture_mapper.get_command_list())
        }
        logger.info("✓ Gesture command mapper initialized")
    except Exception as e:
        errors.append(f"Gesture mapper: {e}")
        components['gesture_mapper'] = {
            'status': 'failed',
            'error': str(e),
            'available': False
        }
    
    # Initialize Enhanced AI learning engine
    try:
        ai_engine = get_enhanced_ai_engine()
        components['ai_engine'] = {
            'status': 'initialized',
            'available': True,
            'learning_enabled': ai_engine.learning_enabled,
            'neural_network': ai_engine.neural_predictor.enabled,
            'enhanced': True
        }
        logger.info("✓ Enhanced AI learning engine initialized")
    except Exception as e:
        # Fallback to basic AI engine
        try:
            ai_engine = get_ai_learning_engine()
            components['ai_engine'] = {
                'status': 'initialized',
                'available': True,
                'learning_enabled': ai_engine.learning_enabled,
                'enhanced': False
            }
            logger.info("✓ Basic AI learning engine initialized")
        except Exception as e2:
            errors.append(f"AI engine: {e}")
            components['ai_engine'] = {
                'status': 'failed',
                'error': str(e),
                'available': False
            }
    
    # Initialize multimodal controller
    try:
        multimodal = get_multimodal_controller()
        multimodal.enable()
        components['multimodal_controller'] = {
            'status': 'initialized',
            'available': True,
            'enabled': True
        }
        logger.info("✓ Multimodal controller initialized")
    except Exception as e:
        errors.append(f"Multimodal controller: {e}")
        components['multimodal_controller'] = {
            'status': 'failed',
            'error': str(e),
            'available': False
        }
    
    success = len(errors) == 0
    
    if success:
        logger.info("✅ Multimodal system initialized successfully")
    else:
        logger.warning(f"⚠️  Multimodal system initialized with errors: {errors}")
    
    return {
        'success': success,
        'components': components,
        'errors': errors if errors else None
    }


def setup_multimodal_eel_integration(eel_module):
    """
    Setup all Eel-exposed APIs for multimodal system
    Call this from kernel/onboarding_gui.py after Eel initialization
    """
    if not MULTIMODAL_AVAILABLE:
        logger.warning("Multimodal system not available - skipping Eel integration")
        return None
    
    logger.info("Setting up multimodal Eel integration...")
    
    apis = {}
    
    # Setup gesture controller API
    try:
        apis['gesture'] = setup_gesture_eel_api()
        logger.info("✓ Gesture Eel API registered")
    except Exception as e:
        logger.error(f"Failed to setup gesture Eel API: {e}")
    
    # Setup gesture commands API
    try:
        apis['gesture_commands'] = setup_gesture_commands_eel_api()
        logger.info("✓ Gesture commands Eel API registered")
    except Exception as e:
        logger.error(f"Failed to setup gesture commands Eel API: {e}")
    
    # Setup Enhanced AI learning API
    try:
        apis['ai_learning_enhanced'] = setup_enhanced_ai_eel_api()
        logger.info("✓ Enhanced AI learning Eel API registered")
    except Exception as e:
        # Fallback to basic AI learning
        try:
            apis['ai_learning'] = setup_ai_learning_eel_api()
            logger.info("✓ Basic AI learning Eel API registered")
        except Exception as e2:
            logger.error(f"Failed to setup AI learning Eel API: {e}")
    
    # Setup multimodal controller API
    try:
        apis['multimodal'] = setup_multimodal_eel_api()
        logger.info("✓ Multimodal Eel API registered")
    except Exception as e:
        logger.error(f"Failed to setup multimodal Eel API: {e}")
    
    # Add master initialization endpoint
    @eel_module.expose
    def initialize_multimodal() -> Dict[str, Any]:
        """Initialize multimodal system"""
        return initialize_multimodal_system()
    
    @eel_module.expose
    def get_multimodal_capabilities() -> Dict[str, Any]:
        """Get list of available multimodal capabilities"""
        return {
            'gesture_control': MULTIMODAL_AVAILABLE,
            'face_tracking': MULTIMODAL_AVAILABLE,
            'eye_gaze': MULTIMODAL_AVAILABLE,
            'ai_learning': MULTIMODAL_AVAILABLE,
            'multimodal_fusion': MULTIMODAL_AVAILABLE,
            'voice_gesture_fusion': MULTIMODAL_AVAILABLE,
            'predictive_suggestions': MULTIMODAL_AVAILABLE
        }
    
    logger.info("✅ Multimodal Eel integration complete")
    
    return apis


__all__ = [
    'initialize_multimodal_system',
    'setup_multimodal_eel_integration',
    'MULTIMODAL_AVAILABLE'
]
