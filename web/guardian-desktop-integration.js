/**
 * AI Guardian Desktop Integration
 * Connects Guardian 3D with desktop features and voice commands
 */

// Integration with voice commands
if (typeof window.AIOS !== 'undefined') {
    const originalVoiceHandler = window.AIOS.handleVoiceCommand;
    
    window.AIOS.handleVoiceCommand = async function(command) {
        const guardian = window.AIOS?.guardian;
        
        // Update guardian to listening state
        if (guardian) {
            guardian.setActivity('listening');
        }
        
        // Process command
        let result;
        if (originalVoiceHandler) {
            result = await originalVoiceHandler(command);
        }
        
        // Update guardian based on result
        if (guardian) {
            if (result && result.success) {
                guardian.setEmotion('happy');
                guardian.setGesture('none');
            } else if (result && !result.success) {
                guardian.setEmotion('neutral');
                guardian.setGesture('none');
            }
            
            guardian.setActivity('idle');
        }
        
        return result;
    };
}

// Integration with gesture system
if (window.GestureController) {
    const originalGestureHandler = window.GestureController.prototype.onGestureRecognized;
    
    window.GestureController.prototype.onGestureRecognized = function(gesture) {
        const guardian = window.AIOS?.guardian;
        
        // Mirror user gestures on guardian
        if (guardian && gesture) {
            const gestureMap = {
                'STOP': 'stop',
                'WAVE': 'wave',
                'POINT': 'point',
                'THUMBS_UP': 'wave',
                'PALM': 'stop'
            };
            
            const guardianGesture = gestureMap[gesture.type] || 'none';
            guardian.setGesture(guardianGesture);
            
            // Return to idle after gesture
            setTimeout(() => {
                guardian.setGesture('none');
            }, 2000);
        }
        
        // Call original handler
        if (originalGestureHandler) {
            return originalGestureHandler.call(this, gesture);
        }
    };
}

// Integration with app launcher
if (window.OSAppLauncher) {
    const originalLaunch = window.OSAppLauncher.prototype.launchApp;
    
    window.OSAppLauncher.prototype.launchApp = async function(appName) {
        const guardian = window.AIOS?.guardian;
        
        if (guardian) {
            guardian.setActivity('thinking');
            guardian.setGesture('point');
            guardian.speak(`Launching ${appName}...`, { emotion: 'neutral' });
        }
        
        const result = await originalLaunch.call(this, appName);
        
        if (guardian) {
            if (result.success) {
                guardian.setEmotion('happy');
                setTimeout(() => {
                    guardian.setGesture('none');
                    guardian.setActivity('idle');
                }, 1500);
            } else {
                guardian.setEmotion('neutral');
                guardian.setGesture('none');
                guardian.setActivity('idle');
            }
        }
        
        return result;
    };
}

// Integration with file browser
document.addEventListener('file-browser-action', (event) => {
    const guardian = window.AIOS?.guardian;
    if (!guardian) return;
    
    const action = event.detail?.action;
    
    switch (action) {
        case 'open':
            guardian.setGesture('point');
            break;
        case 'delete':
            guardian.setGesture('stop');
            guardian.speak('Are you sure you want to delete this?', { emotion: 'neutral' });
            break;
        case 'copy':
        case 'move':
            guardian.setGesture('point');
            break;
    }
    
    setTimeout(() => guardian.setGesture('none'), 2000);
});

// Integration with system tray
document.addEventListener('system-tray-action', (event) => {
    const guardian = window.AIOS?.guardian;
    if (!guardian) return;
    
    const action = event.detail?.action;
    
    if (action === 'shutdown' || action === 'restart') {
        guardian.setGesture('stop');
        guardian.setEmotion('neutral');
        guardian.speak('Preparing system for shutdown...', { emotion: 'neutral' });
    } else if (action === 'settings') {
        guardian.setGesture('point');
        guardian.setActivity('thinking');
    }
});

// Auto-speak for notifications
document.addEventListener('system-notification', (event) => {
    const guardian = window.AIOS?.guardian;
    if (!guardian) return;
    
    const notification = event.detail;
    
    if (notification.priority === 'high' || notification.type === 'error') {
        guardian.setGesture('stop');
        guardian.speak(notification.message, { emotion: 'neutral' });
    } else if (notification.type === 'success') {
        guardian.speak(notification.message, { emotion: 'happy', gesture: 'none' });
    }
});

console.log('[GuardianDesktop] Desktop integration loaded');

export default {
    // Future expansion: export specific integration functions
};
