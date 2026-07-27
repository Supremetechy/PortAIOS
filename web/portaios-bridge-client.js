/**
PortAIOS Secure WebSocket Bridge Client
Polyfills window.eel with a WebSocket RPC proxy when running outside Eel's python-wrapper.
Supports remote daemon connection, token authorization, and dynamic callbacks.
*/

(function() {
    console.log("[Bridge] Initializing PortAIOS client bridge...");

    // Helper to generate UUIDs
    function generateUuid() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // Parse configuration from URL query params or localStorage
    const urlParams = new URLSearchParams(window.location.search);
    
    // Read or initialize configuration
    const token = urlParams.get('token') || localStorage.getItem('portaios_secret_token') || 'portaios-secret-2026';
    const wsPort = urlParams.get('ws_port') || '9000';
    const host = urlParams.get('host') || window.location.hostname || 'localhost';
    
    // Persist token for future page reloads
    if (urlParams.get('token')) {
        localStorage.setItem('portaios_secret_token', urlParams.get('token'));
    }

    class PortAIOSBridge {
        constructor() {
            this.ws = null;
            this.exposedFunctions = {};
            this.pendingCalls = {};
            this.isConnected = false;
            
            // Map legacy global callback registration
            window.receive_viseme_data = window.receive_viseme_data || null;
        }

        connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${host}:${wsPort}/?token=${encodeURIComponent(token)}`;
            
            console.log(`[Bridge] Connecting to agent daemon: ${wsUrl}`);
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log("[Bridge] WebSocket connection established successfully.");
                this.isConnected = true;
                
                // Alert UI components that might be waiting
                window.dispatchEvent(new CustomEvent('portaios-bridge-connected'));
            };

            this.ws.onclose = (event) => {
                console.warn(`[Bridge] WebSocket closed (code: ${event.code}). Retrying in 3 seconds...`);
                this.isConnected = false;
                setTimeout(() => this.connect(), 3000);
            };

            this.ws.onerror = (error) => {
                console.error("[Bridge] WebSocket error observed:", error);
            };

            this.ws.onmessage = async (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'response') {
                        // Response from Python call
                        const resolver = this.pendingCalls[data.id];
                        if (resolver) {
                            if (data.success) {
                                resolver.resolve(data.result);
                            } else {
                                resolver.reject(new Error(data.error));
                            }
                            delete this.pendingCalls[data.id];
                        }
                    } else if (data.type === 'callback') {
                        // Callback from Python calling JS
                        logger_log(`[Bridge] Python callback requested: ${data.name}`);
                        await this.executeCallback(data.id, data.name, data.args);
                    }
                } catch (e) {
                    console.warn("[Bridge] Error handling message:", e);
                }
            };
        }

        async executeCallback(callId, name, args) {
            // Check in our exposed functions registry first
            let fn = this.exposedFunctions[name];
            
            // Fallback: check window/global scope functions
            if (!fn) {
                fn = window[name];
            }

            if (!fn) {
                console.error(`[Bridge] Callback function '${name}' is not exposed or registered in JS.`);
                this.ws.send(JSON.stringify({
                    type: 'callback_response',
                    id: callId,
                    success: false,
                    error: `JS Callback '${name}' not found`
                }));
                return;
            }

            try {
                // Execute function (supports both sync and async/promise-returning functions)
                const result = await Promise.resolve(fn(...args));
                this.ws.send(JSON.stringify({
                    type: 'callback_response',
                    id: callId,
                    success: true,
                    result: result
                }));
            } catch (err) {
                console.error(`[Bridge] Error running callback '${name}':`, err);
                this.ws.send(JSON.stringify({
                    type: 'callback_response',
                    id: callId,
                    success: false,
                    error: err.message
                }));
            }
        }

        callPython(method, args) {
            if (!this.isConnected) {
                console.warn(`[Bridge] WebSocket not connected. Queueing call: ${method}`);
            }

            return new Promise((resolve, reject) => {
                const callId = generateUuid();
                this.pendingCalls[callId] = { resolve, reject };
                
                try {
                    this.ws.send(JSON.stringify({
                        type: 'call',
                        id: callId,
                        method: method,
                        args: args
                    }));
                } catch (err) {
                    delete this.pendingCalls[callId];
                    reject(err);
                }
            });
        }
    }

    function logger_log(msg) {
        // Suppress visual noise from repetitive viseme updates unless debugging is enabled
        if (msg.includes('receive_viseme_data')) return;
        console.log(msg);
    }

    const bridge = new PortAIOSBridge();
    window.portaiosBridge = bridge;
    bridge.connect();

    // Polyfill window.eel using a JavaScript Proxy
    if (typeof window.eel === 'undefined') {
        console.log("[Bridge] window.eel not found. Registering WebSocket Eel Polyfill proxy.");
        
        window.eel = new Proxy({}, {
            get(target, prop) {
                if (prop === 'expose') {
                    return function(fn, name) {
                        const exposeName = name || fn.name;
                        bridge.exposedFunctions[exposeName] = fn;
                        console.log(`[Bridge] Exposed JS function: ${exposeName}`);
                    };
                }
                
                // Return curried caller to mirror Eel syntax: eel.py_func(args)() -> Promise
                return function(...args) {
                    return function() {
                        return bridge.callPython(prop, args);
                    };
                };
            }
        });
    } else {
        console.log("[Bridge] Native Eel object exists. Skipping polyfill.");
    }
})();
