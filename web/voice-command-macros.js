/**
 * Voice Command Macros & Custom Shortcuts System
 * Allows users to create custom voice commands and multi-step macros
 */

export class VoiceCommandMacros {
    constructor(voiceInput, uiController) {
        this.voiceInput = voiceInput;
        this.uiController = uiController;
        
        // Macro storage
        this.macros = new Map();
        this.shortcuts = new Map();
        
        // State
        this.recordingMacro = false;
        this.currentMacroSteps = [];
        this.currentMacroName = null;
        
        // Load saved macros from localStorage
        this.loadMacros();
        
        console.log('[VoiceMacros] Macro system initialized');
    }
    
    /**
     * Create a custom voice shortcut
     * Maps a custom phrase to an existing command or action
     */
    createShortcut(phrase, targetCommand, options = {}) {
        const shortcut = {
            phrase: phrase.toLowerCase(),
            command: targetCommand,
            description: options.description || `Shortcut for: ${targetCommand}`,
            category: options.category || 'custom',
            confirmBefore: options.confirmBefore || false,
            created: new Date().toISOString()
        };
        
        this.shortcuts.set(phrase.toLowerCase(), shortcut);
        this.saveMacros();
        
        console.log(`[VoiceMacros] Created shortcut: "${phrase}" → "${targetCommand}"`);
        return shortcut;
    }
    
    /**
     * Create a macro (sequence of commands)
     */
    createMacro(name, steps, options = {}) {
        const macro = {
            name: name.toLowerCase(),
            steps: steps,
            description: options.description || `Macro: ${name}`,
            category: options.category || 'custom',
            delay: options.delay || 500, // ms between steps
            confirmBefore: options.confirmBefore || false,
            created: new Date().toISOString()
        };
        
        this.macros.set(name.toLowerCase(), macro);
        this.saveMacros();
        
        console.log(`[VoiceMacros] Created macro: "${name}" with ${steps.length} steps`);
        return macro;
    }
    
    /**
     * Start recording a new macro
     */
    startRecording(macroName) {
        this.recordingMacro = true;
        this.currentMacroName = macroName;
        this.currentMacroSteps = [];
        
        this.speak(`Recording macro: ${macroName}. Execute commands now.`);
        console.log(`[VoiceMacros] Started recording macro: ${macroName}`);
        
        return {
            success: true,
            message: `Recording "${macroName}". Say "stop recording" when done.`
        };
    }
    
    /**
     * Stop recording and save the macro
     */
    stopRecording() {
        if (!this.recordingMacro) {
            return { success: false, message: 'Not currently recording' };
        }
        
        this.recordingMacro = false;
        
        if (this.currentMacroSteps.length === 0) {
            this.speak('No steps recorded. Macro cancelled.');
            return { success: false, message: 'No steps recorded' };
        }
        
        const macro = this.createMacro(this.currentMacroName, this.currentMacroSteps, {
            description: `User-recorded macro with ${this.currentMacroSteps.length} steps`
        });
        
        this.speak(`Macro ${this.currentMacroName} saved with ${this.currentMacroSteps.length} steps.`);
        
        const result = {
            success: true,
            message: `Macro "${this.currentMacroName}" saved`,
            macro: macro
        };
        
        this.currentMacroName = null;
        this.currentMacroSteps = [];
        
        return result;
    }
    
    /**
     * Record a command step during macro recording
     */
    recordStep(command) {
        if (!this.recordingMacro) return;
        
        this.currentMacroSteps.push({
            command: command,
            timestamp: Date.now()
        });
        
        console.log(`[VoiceMacros] Recorded step ${this.currentMacroSteps.length}: ${command}`);
    }
    
    /**
     * Execute a shortcut or macro
     */
    async execute(name) {
        const lower = name.toLowerCase();
        
        // Check shortcuts first
        if (this.shortcuts.has(lower)) {
            return await this.executeShortcut(lower);
        }
        
        // Check macros
        if (this.macros.has(lower)) {
            return await this.executeMacro(lower);
        }
        
        return null; // Not found
    }
    
    /**
     * Execute a shortcut
     */
    async executeShortcut(name) {
        const shortcut = this.shortcuts.get(name);
        if (!shortcut) return null;
        
        console.log(`[VoiceMacros] Executing shortcut: ${name}`);
        
        // Confirmation if required
        if (shortcut.confirmBefore) {
            const confirmed = await this.confirmAction(`Execute shortcut: ${shortcut.phrase}?`);
            if (!confirmed) {
                this.speak('Cancelled');
                return { success: false, message: 'Cancelled by user' };
            }
        }
        
        // Execute the target command
        if (this.voiceInput && this.voiceInput.processCommand) {
            await this.voiceInput.processCommand(shortcut.command);
        }
        
        return {
            success: true,
            message: `Executed shortcut: ${shortcut.phrase}`,
            command: shortcut.command
        };
    }
    
    /**
     * Execute a macro (sequence of commands)
     */
    async executeMacro(name) {
        const macro = this.macros.get(name);
        if (!macro) return null;
        
        console.log(`[VoiceMacros] Executing macro: ${name} (${macro.steps.length} steps)`);
        
        // Confirmation if required
        if (macro.confirmBefore) {
            const confirmed = await this.confirmAction(`Execute macro: ${macro.name}?`);
            if (!confirmed) {
                this.speak('Cancelled');
                return { success: false, message: 'Cancelled by user' };
            }
        }
        
        this.speak(`Executing macro: ${macro.name}`);
        
        // Execute each step with delay
        for (let i = 0; i < macro.steps.length; i++) {
            const step = macro.steps[i];
            console.log(`[VoiceMacros] Step ${i + 1}/${macro.steps.length}: ${step.command}`);
            
            if (this.voiceInput && this.voiceInput.processCommand) {
                await this.voiceInput.processCommand(step.command);
            }
            
            // Wait between steps (except after last step)
            if (i < macro.steps.length - 1) {
                await this.delay(macro.delay);
            }
        }
        
        this.speak(`Macro ${macro.name} complete`);
        
        return {
            success: true,
            message: `Executed macro: ${macro.name}`,
            stepsExecuted: macro.steps.length
        };
    }
    
    /**
     * Delete a shortcut or macro
     */
    delete(name) {
        const lower = name.toLowerCase();
        
        if (this.shortcuts.has(lower)) {
            this.shortcuts.delete(lower);
            this.saveMacros();
            return { success: true, message: `Deleted shortcut: ${name}`, type: 'shortcut' };
        }
        
        if (this.macros.has(lower)) {
            this.macros.delete(lower);
            this.saveMacros();
            return { success: true, message: `Deleted macro: ${name}`, type: 'macro' };
        }
        
        return { success: false, message: `Not found: ${name}` };
    }
    
    /**
     * List all shortcuts and macros
     */
    list(category = null) {
        const result = {
            shortcuts: [],
            macros: []
        };
        
        // List shortcuts
        for (const [name, shortcut] of this.shortcuts) {
            if (!category || shortcut.category === category) {
                result.shortcuts.push({
                    name: shortcut.phrase,
                    command: shortcut.command,
                    description: shortcut.description,
                    category: shortcut.category
                });
            }
        }
        
        // List macros
        for (const [name, macro] of this.macros) {
            if (!category || macro.category === category) {
                result.macros.push({
                    name: macro.name,
                    steps: macro.steps.length,
                    description: macro.description,
                    category: macro.category
                });
            }
        }
        
        return result;
    }
    
    /**
     * Export shortcuts and macros to JSON
     */
    export() {
        return {
            shortcuts: Array.from(this.shortcuts.values()),
            macros: Array.from(this.macros.values()),
            exported: new Date().toISOString()
        };
    }
    
    /**
     * Import shortcuts and macros from JSON
     */
    import(data) {
        let imported = 0;
        
        if (data.shortcuts) {
            data.shortcuts.forEach(shortcut => {
                this.shortcuts.set(shortcut.phrase.toLowerCase(), shortcut);
                imported++;
            });
        }
        
        if (data.macros) {
            data.macros.forEach(macro => {
                this.macros.set(macro.name.toLowerCase(), macro);
                imported++;
            });
        }
        
        this.saveMacros();
        
        return {
            success: true,
            message: `Imported ${imported} items`,
            shortcuts: data.shortcuts?.length || 0,
            macros: data.macros?.length || 0
        };
    }
    
    /**
     * Get predefined shortcuts (examples)
     */
    static getPredefinedShortcuts() {
        return [
            { phrase: 'demo mode', command: 'click demo', category: 'quick-actions' },
            { phrase: 'say hi', command: 'click greet', category: 'quick-actions' },
            { phrase: 'go crazy', command: 'click glitch', category: 'quick-actions' },
            { phrase: 'blue theme', command: 'set palette to cyan', category: 'themes' },
            { phrase: 'green theme', command: 'set palette to matrix', category: 'themes' },
            { phrase: 'red theme', command: 'set palette to red', category: 'themes' },
            { phrase: 'happy face', command: 'set smile to 1', category: 'avatar' },
            { phrase: 'sad face', command: 'set frown to 1', category: 'avatar' },
            { phrase: 'surprised face', command: 'set surprise to 1', category: 'avatar' },
            { phrase: 'neutral face', command: 'set smile to 0.5', category: 'avatar' },
            { phrase: 'start kernel', command: 'boot minikernel', category: 'system' },
            { phrase: 'stop kernel', command: 'halt minikernel', category: 'system' }
        ];
    }
    
    /**
     * Get predefined macros (examples)
     */
    static getPredefinedMacros() {
        return [
            {
                name: 'morning setup',
                steps: [
                    { command: 'set palette to cyan' },
                    { command: 'click greet' },
                    { command: 'boot minikernel' }
                ],
                category: 'workflow',
                description: 'Morning startup routine'
            },
            {
                name: 'demo sequence',
                steps: [
                    { command: 'click demo' },
                    { command: 'set palette to cyan' },
                    { command: 'set activity to thinking' }
                ],
                category: 'demo',
                description: 'Full demo sequence'
            },
            {
                name: 'avatar test',
                steps: [
                    { command: 'set smile to 1' },
                    { command: 'set surprise to 0.5' },
                    { command: 'set wink to 0.3' }
                ],
                category: 'avatar',
                description: 'Test avatar expressions'
            },
            {
                name: 'reset all',
                steps: [
                    { command: 'set palette to matrix' },
                    { command: 'set activity to idle' },
                    { command: 'set smile to 0.5' },
                    { command: 'set frown to 0.5' },
                    { command: 'set surprise to 0.5' }
                ],
                category: 'system',
                description: 'Reset to defaults'
            }
        ];
    }
    
    /**
     * Install predefined shortcuts and macros
     */
    installPredefined() {
        let installed = 0;
        
        // Install shortcuts
        VoiceCommandMacros.getPredefinedShortcuts().forEach(shortcut => {
            this.createShortcut(shortcut.phrase, shortcut.command, {
                category: shortcut.category,
                description: `Predefined: ${shortcut.phrase}`
            });
            installed++;
        });
        
        // Install macros
        VoiceCommandMacros.getPredefinedMacros().forEach(macro => {
            this.createMacro(macro.name, macro.steps, {
                category: macro.category,
                description: macro.description,
                delay: 800
            });
            installed++;
        });
        
        return {
            success: true,
            message: `Installed ${installed} predefined commands`,
            shortcuts: VoiceCommandMacros.getPredefinedShortcuts().length,
            macros: VoiceCommandMacros.getPredefinedMacros().length
        };
    }
    
    /**
     * Save macros to localStorage
     */
    saveMacros() {
        try {
            const data = {
                shortcuts: Array.from(this.shortcuts.entries()),
                macros: Array.from(this.macros.entries())
            };
            localStorage.setItem('aios_voice_macros', JSON.stringify(data));
        } catch (error) {
            console.error('[VoiceMacros] Error saving macros:', error);
        }
    }
    
    /**
     * Load macros from localStorage
     */
    loadMacros() {
        try {
            const data = localStorage.getItem('aios_voice_macros');
            if (data) {
                const parsed = JSON.parse(data);
                this.shortcuts = new Map(parsed.shortcuts || []);
                this.macros = new Map(parsed.macros || []);
                console.log(`[VoiceMacros] Loaded ${this.shortcuts.size} shortcuts and ${this.macros.size} macros`);
            }
        } catch (error) {
            console.error('[VoiceMacros] Error loading macros:', error);
        }
    }
    
    /**
     * Utility: Delay
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Utility: Speak
     */
    speak(text) {
        if (window.speak) {
            window.speak(text);
        } else if (window.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(utterance);
        }
    }
    
    /**
     * Utility: Confirm action
     */
    async confirmAction(message) {
        if (window.showConfirmation) {
            return await window.showConfirmation(message);
        }
        return confirm(message);
    }
}

export default VoiceCommandMacros;
