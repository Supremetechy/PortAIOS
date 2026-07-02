/**
 * Confirmation Dialog for Voice Commands
 * Handles user confirmations for destructive actions like shutdown/restart
 */

class ConfirmationDialog {
    constructor() {
        this.currentPromise = null;
        this.createDialog();
    }

    createDialog() {
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.id = 'confirmation-overlay';
        overlay.style.cssText = `
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 10000;
            backdrop-filter: blur(5px);
        `;

        // Create dialog container
        const dialog = document.createElement('div');
        dialog.id = 'confirmation-dialog';
        dialog.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            min-width: 400px;
            max-width: 90%;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;

        // Create message element
        const message = document.createElement('div');
        message.id = 'confirmation-message';
        message.style.cssText = `
            font-size: 18px;
            margin-bottom: 25px;
            text-align: center;
            line-height: 1.5;
        `;

        // Create button container
        const buttonContainer = document.createElement('div');
        buttonContainer.style.cssText = `
            display: flex;
            gap: 15px;
            justify-content: center;
        `;

        // Create Yes button
        const yesButton = document.createElement('button');
        yesButton.id = 'confirmation-yes';
        yesButton.textContent = 'Yes';
        yesButton.style.cssText = `
            padding: 12px 30px;
            border: none;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.9);
            color: #667eea;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        `;
        yesButton.onmouseover = () => {
            yesButton.style.background = 'white';
            yesButton.style.transform = 'scale(1.05)';
        };
        yesButton.onmouseout = () => {
            yesButton.style.background = 'rgba(255, 255, 255, 0.9)';
            yesButton.style.transform = 'scale(1)';
        };

        // Create No button
        const noButton = document.createElement('button');
        noButton.id = 'confirmation-no';
        noButton.textContent = 'No';
        noButton.style.cssText = `
            padding: 12px 30px;
            border: 2px solid white;
            border-radius: 10px;
            background: transparent;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        `;
        noButton.onmouseover = () => {
            noButton.style.background = 'rgba(255, 255, 255, 0.1)';
            noButton.style.transform = 'scale(1.05)';
        };
        noButton.onmouseout = () => {
            noButton.style.background = 'transparent';
            noButton.style.transform = 'scale(1)';
        };

        // Assemble dialog
        buttonContainer.appendChild(noButton);
        buttonContainer.appendChild(yesButton);
        dialog.appendChild(message);
        dialog.appendChild(buttonContainer);
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        this.overlay = overlay;
        this.message = message;
        this.yesButton = yesButton;
        this.noButton = noButton;
    }

    show(message, timeout = 10000) {
        return new Promise((resolve, reject) => {
            this.message.textContent = message;
            this.overlay.style.display = 'block';

            // Auto-reject after timeout
            const timeoutId = setTimeout(() => {
                this.hide();
                reject(new Error('Confirmation timeout'));
            }, timeout);

            // Yes button handler
            const yesHandler = () => {
                clearTimeout(timeoutId);
                this.hide();
                resolve(true);
            };

            // No button handler
            const noHandler = () => {
                clearTimeout(timeoutId);
                this.hide();
                resolve(false);
            };

            // Keyboard handler (Enter = Yes, Escape = No)
            const keyHandler = (e) => {
                if (e.key === 'Enter') {
                    yesHandler();
                } else if (e.key === 'Escape') {
                    noHandler();
                }
            };

            // Add event listeners
            this.yesButton.onclick = yesHandler;
            this.noButton.onclick = noHandler;
            document.addEventListener('keydown', keyHandler);

            // Store cleanup function
            this.cleanup = () => {
                this.yesButton.onclick = null;
                this.noButton.onclick = null;
                document.removeEventListener('keydown', keyHandler);
                clearTimeout(timeoutId);
            };
        });
    }

    hide() {
        this.overlay.style.display = 'none';
        if (this.cleanup) {
            this.cleanup();
        }
    }

    async confirm(message, options = {}) {
        const { timeout = 10000, speakMessage = true } = options;

        // Speak the confirmation message if TTS is available
        if (speakMessage && window.speak_with_lipsync) {
            try {
                await eel.speak_with_lipsync(message)();
            } catch (e) {
                console.warn('TTS not available:', e);
            }
        }

        try {
            return await this.show(message, timeout);
        } catch (e) {
            console.error('Confirmation error:', e);
            return false;
        }
    }
}

// Create global instance
const confirmationDialog = new ConfirmationDialog();

/**
 * Show confirmation dialog
 * @param {string} message - Message to display
 * @param {object} options - Options (timeout, speakMessage)
 * @returns {Promise<boolean>} - True if confirmed, false otherwise
 */
async function showConfirmation(message, options = {}) {
    return await confirmationDialog.confirm(message, options);
}

// Expose globally
window.showConfirmation = showConfirmation;
window.confirmationDialog = confirmationDialog;

// Voice command integration
if (window.eel) {
    // Override execute_system_command to handle confirmations
    const originalExecuteSystemCommand = window.execute_system_command;
    
    window.execute_system_command = async function(command, data) {
        // Commands that need confirmation
        const needsConfirmation = ['shutdown', 'restart', 'logout'];
        
        if (needsConfirmation.includes(command)) {
            let message = '';
            switch(command) {
                case 'shutdown':
                    message = 'Are you sure you want to shutdown PortAIOS?';
                    break;
                case 'restart':
                    message = 'Are you sure you want to restart PortAIOS?';
                    break;
                case 'logout':
                    message = 'Are you sure you want to log out?';
                    break;
            }
            
            const confirmed = await showConfirmation(message, { speakMessage: true });
            
            if (!confirmed) {
                console.log(`${command} cancelled by user`);
                if (window.speak_with_lipsync) {
                    try {
                        await eel.speak_with_lipsync('Cancelled')();
                    } catch (e) {}
                }
                return { success: false, message: 'Cancelled by user', cancelled: true };
            }
        }
        
        // Execute the command
        if (originalExecuteSystemCommand) {
            return await originalExecuteSystemCommand(command, data);
        } else if (window.eel && window.eel.execute_system_command) {
            return await eel.execute_system_command(command, data)();
        }
    };
}

console.log('✅ Confirmation dialog system loaded');
