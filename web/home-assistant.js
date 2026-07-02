const ha = window.AIOS.externalIntegrations.registerIntegration({
    name: 'Home Assistant',
    type: 'api',
    config: {
        baseUrl: 'http://homeassistant.local:8123',
        authentication: 'bearer',
        bearerToken: 'YOUR_LONG_LIVED_TOKEN',
        endpoints: {
            turnOnLight: {
                path: '/api/services/light/turn_on',
                method: 'POST'
            }
        }
    }
});

export default homeAssistant