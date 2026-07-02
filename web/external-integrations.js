/**
 * External Integrations System
 * Connect PortAIOS to external APIs, webhooks, and automation platforms
 * Supports: REST APIs, Webhooks, Zapier, IFTTT, Home Assistant, and custom integrations
 */

export class ExternalIntegrations {
    constructor(options = {}) {
        this.options = {
            enableWebhooks: true,
            enableAPICalls: true,
            enableAutomation: true,
            rateLimitPerMinute: 60,
            timeout: 10000,
            retryAttempts: 3,
            ...options
        };
        
        // Integration storage
        this.integrations = new Map();
        this.webhooks = new Map();
        this.apiEndpoints = new Map();
        this.automations = new Map();
        
        // Rate limiting
        this.requestQueue = [];
        this.requestCounts = new Map();
        
        // Event listeners
        this.eventListeners = new Map();
        
        // Load saved integrations
        this.loadIntegrations();
        
        console.log('[ExternalIntegrations] Integration system initialized');
    }
    
    /**
     * Register a new integration
     */
    registerIntegration(config) {
        const integration = {
            id: config.id || this.generateId(),
            name: config.name,
            type: config.type, // 'webhook', 'api', 'automation'
            enabled: config.enabled !== false,
            config: config,
            created: new Date().toISOString(),
            lastUsed: null,
            usageCount: 0
        };
        
        this.integrations.set(integration.id, integration);
        
        // Register based on type
        switch (integration.type) {
            case 'webhook':
                this.registerWebhook(integration);
                break;
            case 'api':
                this.registerAPIEndpoint(integration);
                break;
            case 'automation':
                this.registerAutomation(integration);
                break;
        }
        
        this.saveIntegrations();
        
        console.log(`[ExternalIntegrations] Registered: ${integration.name} (${integration.type})`);
        
        return integration;
    }
    
    /**
     * Register a webhook
     */
    registerWebhook(integration) {
        const webhook = {
            id: integration.id,
            url: integration.config.url,
            method: integration.config.method || 'POST',
            headers: integration.config.headers || {},
            trigger: integration.config.trigger, // Event to trigger on
            transform: integration.config.transform // Data transformation function
        };
        
        this.webhooks.set(integration.id, webhook);
        
        // Listen for trigger events
        if (webhook.trigger) {
            this.addEventListener(webhook.trigger, async (data) => {
                if (integration.enabled) {
                    await this.sendWebhook(integration.id, data);
                }
            });
        }
    }
    
    /**
     * Register an API endpoint
     */
    registerAPIEndpoint(integration) {
        const api = {
            id: integration.id,
            baseUrl: integration.config.baseUrl,
            authentication: integration.config.authentication, // 'none', 'apikey', 'bearer', 'oauth'
            apiKey: integration.config.apiKey,
            bearerToken: integration.config.bearerToken,
            headers: integration.config.headers || {},
            endpoints: integration.config.endpoints || {}
        };
        
        this.apiEndpoints.set(integration.id, api);
    }
    
    /**
     * Register an automation
     */
    registerAutomation(integration) {
        const automation = {
            id: integration.id,
            platform: integration.config.platform, // 'zapier', 'ifttt', 'homeassistant', 'nodered'
            webhookUrl: integration.config.webhookUrl,
            trigger: integration.config.trigger,
            actions: integration.config.actions || []
        };
        
        this.automations.set(integration.id, automation);
        
        // Listen for trigger events
        if (automation.trigger) {
            this.addEventListener(automation.trigger, async (data) => {
                if (integration.enabled) {
                    await this.triggerAutomation(integration.id, data);
                }
            });
        }
    }
    
    /**
     * Send webhook
     */
    async sendWebhook(integrationId, data) {
        const integration = this.integrations.get(integrationId);
        const webhook = this.webhooks.get(integrationId);
        
        if (!integration || !webhook) {
            throw new Error(`Webhook not found: ${integrationId}`);
        }
        
        // Check rate limit
        if (!this.checkRateLimit(integrationId)) {
            console.warn(`[ExternalIntegrations] Rate limit exceeded for ${integration.name}`);
            return { success: false, error: 'Rate limit exceeded' };
        }
        
        try {
            // Transform data if transform function provided
            let payload = data;
            if (webhook.transform && typeof webhook.transform === 'function') {
                payload = webhook.transform(data);
            }
            
            const response = await this.makeRequest({
                url: webhook.url,
                method: webhook.method,
                headers: webhook.headers,
                body: payload
            });
            
            // Update usage stats
            integration.lastUsed = new Date().toISOString();
            integration.usageCount++;
            this.saveIntegrations();
            
            console.log(`[ExternalIntegrations] Webhook sent: ${integration.name}`);
            
            return {
                success: true,
                integration: integration.name,
                response: response
            };
            
        } catch (error) {
            console.error(`[ExternalIntegrations] Webhook error:`, error);
            return {
                success: false,
                integration: integration.name,
                error: error.message
            };
        }
    }
    
    /**
     * Call API endpoint
     */
    async callAPI(integrationId, endpoint, params = {}) {
        const integration = this.integrations.get(integrationId);
        const api = this.apiEndpoints.get(integrationId);
        
        if (!integration || !api) {
            throw new Error(`API not found: ${integrationId}`);
        }
        
        // Check rate limit
        if (!this.checkRateLimit(integrationId)) {
            console.warn(`[ExternalIntegrations] Rate limit exceeded for ${integration.name}`);
            return { success: false, error: 'Rate limit exceeded' };
        }
        
        try {
            const endpointConfig = api.endpoints[endpoint];
            if (!endpointConfig) {
                throw new Error(`Endpoint not found: ${endpoint}`);
            }
            
            // Build URL
            let url = `${api.baseUrl}${endpointConfig.path}`;
            
            // Replace path parameters
            if (params.path) {
                Object.keys(params.path).forEach(key => {
                    url = url.replace(`{${key}}`, params.path[key]);
                });
            }
            
            // Add query parameters
            if (params.query) {
                const queryString = new URLSearchParams(params.query).toString();
                url += `?${queryString}`;
            }
            
            // Build headers with authentication
            const headers = { ...api.headers };
            
            if (api.authentication === 'apikey' && api.apiKey) {
                headers['X-API-Key'] = api.apiKey;
            } else if (api.authentication === 'bearer' && api.bearerToken) {
                headers['Authorization'] = `Bearer ${api.bearerToken}`;
            }
            
            const response = await this.makeRequest({
                url: url,
                method: endpointConfig.method || 'GET',
                headers: headers,
                body: params.body
            });
            
            // Update usage stats
            integration.lastUsed = new Date().toISOString();
            integration.usageCount++;
            this.saveIntegrations();
            
            console.log(`[ExternalIntegrations] API called: ${integration.name}/${endpoint}`);
            
            return {
                success: true,
                integration: integration.name,
                endpoint: endpoint,
                data: response
            };
            
        } catch (error) {
            console.error(`[ExternalIntegrations] API error:`, error);
            return {
                success: false,
                integration: integration.name,
                endpoint: endpoint,
                error: error.message
            };
        }
    }
    
    /**
     * Trigger automation
     */
    async triggerAutomation(integrationId, data) {
        const integration = this.integrations.get(integrationId);
        const automation = this.automations.get(integrationId);
        
        if (!integration || !automation) {
            throw new Error(`Automation not found: ${integrationId}`);
        }
        
        try {
            const payload = {
                platform: automation.platform,
                trigger: automation.trigger,
                data: data,
                timestamp: new Date().toISOString()
            };
            
            const response = await this.makeRequest({
                url: automation.webhookUrl,
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: payload
            });
            
            // Update usage stats
            integration.lastUsed = new Date().toISOString();
            integration.usageCount++;
            this.saveIntegrations();
            
            console.log(`[ExternalIntegrations] Automation triggered: ${integration.name}`);
            
            return {
                success: true,
                integration: integration.name,
                platform: automation.platform,
                response: response
            };
            
        } catch (error) {
            console.error(`[ExternalIntegrations] Automation error:`, error);
            return {
                success: false,
                integration: integration.name,
                error: error.message
            };
        }
    }
    
    /**
     * Make HTTP request with retry logic
     */
    async makeRequest(config, attempt = 1) {
        try {
            const response = await fetch(config.url, {
                method: config.method || 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    ...config.headers
                },
                body: config.body ? JSON.stringify(config.body) : undefined,
                signal: AbortSignal.timeout(this.options.timeout)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
            
        } catch (error) {
            if (attempt < this.options.retryAttempts) {
                console.log(`[ExternalIntegrations] Retry ${attempt}/${this.options.retryAttempts}`);
                await this.delay(1000 * attempt); // Exponential backoff
                return this.makeRequest(config, attempt + 1);
            }
            throw error;
        }
    }
    
    /**
     * Check rate limit
     */
    checkRateLimit(integrationId) {
        const now = Date.now();
        const counts = this.requestCounts.get(integrationId) || [];
        
        // Remove requests older than 1 minute
        const recentCounts = counts.filter(timestamp => (now - timestamp) < 60000);
        
        if (recentCounts.length >= this.options.rateLimitPerMinute) {
            return false;
        }
        
        recentCounts.push(now);
        this.requestCounts.set(integrationId, recentCounts);
        
        return true;
    }
    
    /**
     * Emit event to trigger integrations
     */
    emit(eventName, data) {
        const listeners = this.eventListeners.get(eventName) || [];
        listeners.forEach(listener => {
            try {
                listener(data);
            } catch (error) {
                console.error(`[ExternalIntegrations] Event listener error:`, error);
            }
        });
    }
    
    /**
     * Add event listener
     */
    addEventListener(eventName, callback) {
        if (!this.eventListeners.has(eventName)) {
            this.eventListeners.set(eventName, []);
        }
        this.eventListeners.get(eventName).push(callback);
    }
    
    /**
     * Get predefined integration templates
     */
    static getTemplates() {
        return {
            // Zapier integration
            zapier: {
                name: 'Zapier Webhook',
                type: 'automation',
                platform: 'zapier',
                description: 'Trigger Zapier workflows from PortAIOS events',
                config: {
                    webhookUrl: 'https://hooks.zapier.com/hooks/catch/YOUR_WEBHOOK_ID/',
                    trigger: 'voice_command' // Customize event
                }
            },
            
            // IFTTT integration
            ifttt: {
                name: 'IFTTT Webhook',
                type: 'automation',
                platform: 'ifttt',
                description: 'Trigger IFTTT applets from PortAIOS',
                config: {
                    webhookUrl: 'https://maker.ifttt.com/trigger/EVENT_NAME/with/key/YOUR_KEY',
                    trigger: 'gesture_detected'
                }
            },
            
            // Home Assistant
            homeAssistant: {
                name: 'Home Assistant',
                type: 'api',
                description: 'Control Home Assistant devices',
                config: {
                    baseUrl: 'http://homeassistant.local:8123',
                    authentication: 'bearer',
                    bearerToken: 'YOUR_LONG_LIVED_TOKEN',
                    endpoints: {
                        turnOnLight: {
                            path: '/api/services/light/turn_on',
                            method: 'POST'
                        },
                        turnOffLight: {
                            path: '/api/services/light/turn_off',
                            method: 'POST'
                        }
                    }
                }
            },
            
            // Slack webhook
            slack: {
                name: 'Slack Notification',
                type: 'webhook',
                description: 'Send notifications to Slack',
                config: {
                    url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
                    method: 'POST',
                    trigger: 'system_event',
                    transform: (data) => ({
                        text: `PortAIOS Event: ${data.event}`,
                        blocks: [{
                            type: 'section',
                            text: {
                                type: 'mrkdwn',
                                text: `*${data.event}*\n${data.message || ''}`
                            }
                        }]
                    })
                }
            },
            
            // Discord webhook
            discord: {
                name: 'Discord Notification',
                type: 'webhook',
                description: 'Send notifications to Discord',
                config: {
                    url: 'https://discord.com/api/webhooks/YOUR/WEBHOOK',
                    method: 'POST',
                    trigger: 'voice_command',
                    transform: (data) => ({
                        content: `Voice command executed: ${data.command}`,
                        embeds: [{
                            title: 'PortAIOS Command',
                            description: data.command,
                            color: 65535,
                            timestamp: new Date().toISOString()
                        }]
                    })
                }
            },
            
            // Custom REST API
            customAPI: {
                name: 'Custom REST API',
                type: 'api',
                description: 'Connect to any REST API',
                config: {
                    baseUrl: 'https://api.example.com',
                    authentication: 'apikey',
                    apiKey: 'YOUR_API_KEY',
                    endpoints: {
                        getData: {
                            path: '/data/{id}',
                            method: 'GET'
                        },
                        postData: {
                            path: '/data',
                            method: 'POST'
                        }
                    }
                }
            }
        };
    }
    
    /**
     * List all integrations
     */
    list(type = null) {
        const list = [];
        
        for (const [id, integration] of this.integrations) {
            if (!type || integration.type === type) {
                list.push({
                    id: integration.id,
                    name: integration.name,
                    type: integration.type,
                    enabled: integration.enabled,
                    usageCount: integration.usageCount,
                    lastUsed: integration.lastUsed
                });
            }
        }
        
        return list;
    }
    
    /**
     * Enable/disable integration
     */
    setEnabled(integrationId, enabled) {
        const integration = this.integrations.get(integrationId);
        if (!integration) {
            return { success: false, error: 'Integration not found' };
        }
        
        integration.enabled = enabled;
        this.saveIntegrations();
        
        return {
            success: true,
            message: `${integration.name} ${enabled ? 'enabled' : 'disabled'}`
        };
    }
    
    /**
     * Delete integration
     */
    delete(integrationId) {
        const integration = this.integrations.get(integrationId);
        if (!integration) {
            return { success: false, error: 'Integration not found' };
        }
        
        this.integrations.delete(integrationId);
        this.webhooks.delete(integrationId);
        this.apiEndpoints.delete(integrationId);
        this.automations.delete(integrationId);
        
        this.saveIntegrations();
        
        return {
            success: true,
            message: `Deleted integration: ${integration.name}`
        };
    }
    
    /**
     * Test integration
     */
    async test(integrationId) {
        const integration = this.integrations.get(integrationId);
        if (!integration) {
            return { success: false, error: 'Integration not found' };
        }
        
        try {
            const testData = {
                event: 'test',
                message: 'Test from PortAIOS',
                timestamp: new Date().toISOString()
            };
            
            let result;
            
            switch (integration.type) {
                case 'webhook':
                    result = await this.sendWebhook(integrationId, testData);
                    break;
                case 'automation':
                    result = await this.triggerAutomation(integrationId, testData);
                    break;
                case 'api':
                    // For API, test first available endpoint
                    const api = this.apiEndpoints.get(integrationId);
                    const firstEndpoint = Object.keys(api.endpoints)[0];
                    if (firstEndpoint) {
                        result = await this.callAPI(integrationId, firstEndpoint, {});
                    }
                    break;
            }
            
            return {
                success: true,
                message: `Test successful for ${integration.name}`,
                result
            };
            
        } catch (error) {
            return {
                success: false,
                message: `Test failed for ${integration.name}`,
                error: error.message
            };
        }
    }
    
    /**
     * Save integrations to localStorage
     */
    saveIntegrations() {
        try {
            const data = {
                integrations: Array.from(this.integrations.entries())
            };
            localStorage.setItem('aios_external_integrations', JSON.stringify(data));
        } catch (error) {
            console.error('[ExternalIntegrations] Error saving:', error);
        }
    }
    
    /**
     * Load integrations from localStorage
     */
    loadIntegrations() {
        try {
            const data = localStorage.getItem('aios_external_integrations');
            if (data) {
                const parsed = JSON.parse(data);
                const integrations = new Map(parsed.integrations || []);
                
                // Re-register each integration
                integrations.forEach(integration => {
                    this.registerIntegration(integration.config);
                });
                
                console.log(`[ExternalIntegrations] Loaded ${integrations.size} integrations`);
            }
        } catch (error) {
            console.error('[ExternalIntegrations] Error loading:', error);
        }
    }
    
    /**
     * Export integrations
     */
    export() {
        return {
            integrations: Array.from(this.integrations.values()),
            exported: new Date().toISOString()
        };
    }
    
    /**
     * Import integrations
     */
    import(data) {
        if (!data.integrations) {
            return { success: false, error: 'Invalid data format' };
        }
        
        let imported = 0;
        
        data.integrations.forEach(integration => {
            this.registerIntegration(integration.config);
            imported++;
        });
        
        return {
            success: true,
            message: `Imported ${imported} integrations`
        };
    }
    
    /**
     * Utility: Generate unique ID
     */
    generateId() {
        return `int_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Utility: Delay
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

export default ExternalIntegrations;
