/**
 * AI Guardian Onboarding Integration
 * Replaces static AI-Guardian.jpg with interactive 3D avatar
 */

import { AIGuardianController } from './ai-guardian-integration.js';

let guardianInstance = null;

export async function initAIGuardian() {
    const container = document.getElementById('binary-avatar-container');
    const placeholder = document.getElementById('avatar-placeholder');
    
    if (!container) {
        console.warn('[Onboarding] AI Guardian container not found');
        return null;
    }
    
    try {
        console.log('[Onboarding] Initializing AI Guardian 3D...');
        
        // Show loading state
        if (placeholder) {
            placeholder.style.display = 'flex';
            placeholder.innerHTML = `
                <div class="loader-ring"></div>
                <span>Initializing AI Guardian...</span>
            `;
        }
        
        // Initialize the 3D guardian
        guardianInstance = new AIGuardianController(container, {
            modelUrl: '/models/ai_guardian.glb',
            autoRotate: true,
            enableParticles: true,
            visemeWebSocket: 'ws://localhost:8766'
        });
        
        await guardianInstance.init();
        
        // Hide placeholder once loaded
        if (placeholder) {
            placeholder.style.display = 'none';
        }
        
        // Update status
        const statusText = document.getElementById('avatar-status-text');
        if (statusText) {
            statusText.textContent = 'Online';
        }
        
        // Make available globally
        window.AIOS = window.AIOS || {};
        window.AIOS.guardian = guardianInstance;
        window.AIOS.avatar = guardianInstance; // Backward compatibility
        
        console.log('[Onboarding] ✓ AI Guardian 3D ready');
        
        // Initial greeting gesture
        guardianInstance.setGesture('wave');
        setTimeout(() => guardianInstance.setGesture('none'), 2000);
        
        return guardianInstance;
        
    } catch (error) {
        console.error('[Onboarding] Failed to initialize AI Guardian:', error);
        
        // Show fallback
        if (placeholder) {
            placeholder.innerHTML = `
                <div style="text-align: center; padding: 20px;">
                    <div style="font-size: 48px; margin-bottom: 10px;">🤖</div>
                    <span>AI Guardian (Fallback Mode)</span>
                </div>
            `;
            placeholder.style.display = 'flex';
        }
        
        // Create minimal fallback object
        const fallback = {
            speak: (text) => console.log('[Guardian Fallback] Speak:', text),
            setActivity: () => fallback,
            setEmotion: () => fallback,
            setGesture: () => fallback,
            stop: () => fallback
        };
        
        window.AIOS = window.AIOS || {};
        window.AIOS.guardian = fallback;
        window.AIOS.avatar = fallback;
        
        return fallback;
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAIGuardian);
} else {
    // DOM already loaded
    setTimeout(initAIGuardian, 100);
}

export function getGuardian() {
    return guardianInstance;
}

export function destroyGuardian() {
    if (guardianInstance) {
        guardianInstance.destroy();
        guardianInstance = null;
    }
}
