
const zapier = window.AIOS.externalIntegrations.registerIntegration({
    name: 'My Zapier Workflow',
    type: 'automation',
    config: {
        platform: 'zapier',
        webhookUrl: 'https://hooks.zapier.com/hooks/catch/YOUR_ID/',
        trigger: 'voice_command' // Trigger on voice commands
    }
});