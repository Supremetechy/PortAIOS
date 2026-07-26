/**
 * AI Guardian Frontend Bridge
 * Receives state updates from Python backend and syncs with Guardian 3D
 */

// Listen for backend state updates
if (typeof eel !== 'undefined') {
    // Exposed function that backend calls to update guardian state
    function guardian_state_update(state) {
        const guardian = window.AIOS?.guardian;
        if (!guardian) {
            console.debug('[GuardianBridge] Guardian not ready, ignoring state:', state);
            return;
        }
        
        console.log('[GuardianBridge] State update from backend:', state);
        
        if (state.activity) {
            guardian.setActivity(state.activity);
        }
        
        if (state.emotion) {
            guardian.setEmotion(state.emotion);
        }
        
        if (state.gesture) {
            guardian.setGesture(state.gesture);
        }
    }
    
    eel.expose(guardian_state_update);
    
    // Exposed function for backend to make guardian speak
    function guardian_speak(text, emotion, gesture) {
        const guardian = window.AIOS?.guardian;
        if (!guardian) {
            console.warn('[GuardianBridge] Guardian not available for speech');
            return;
        }
        
        console.log('[GuardianBridge] Backend speech request:', { text, emotion, gesture });
        guardian.speak(text, { emotion, gesture });
    }
    
    eel.expose(guardian_speak);
    
    // Exposed function for backend to stop guardian
    function guardian_stop() {
        const guardian = window.AIOS?.guardian;
        if (!guardian) return;
        
        console.log('[GuardianBridge] Backend stop request');
        guardian.stop();
    }
    
    eel.expose(guardian_stop);
    
    console.log('[GuardianBridge] Eel integration ready');
}

// Helper to notify backend of frontend state changes
export function notifyBackendStateChange(state) {
    if (typeof eel !== 'undefined' && eel.guardian_frontend_state_update) {
        try {
            eel.guardian_frontend_state_update(state);
        } catch (error) {
            console.debug('[GuardianBridge] Could not sync to backend:', error);
        }
    }
}

export default {
    guardian_state_update,
    guardian_speak,
    guardian_stop,
    notifyBackendStateChange
};
