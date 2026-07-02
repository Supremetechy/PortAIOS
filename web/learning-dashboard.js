/**
 * PortAIOS AI Learning Dashboard
 * Visualizes learned patterns, predictions, and AI model performance
 */

class LearningDashboard {
    constructor() {
        this.stats = null;
        this.modelStats = null;
        this.refreshInterval = null;
        
        // Load initial data
        this.loadData();
    }
    
    async loadData() {
        try {
            // Load statistics
            if (typeof eel !== 'undefined') {
                if (eel.get_advanced_ai_stats) {
                    this.stats = await eel.get_advanced_ai_stats()();
                }
                
                if (eel.get_model_stats_for_dashboard) {
                    this.modelStats = await eel.get_model_stats_for_dashboard()();
                }
            }
        } catch (error) {
            console.error('[LearningDashboard] Failed to load data:', error);
        }
    }
    
    async refresh() {
        await this.loadData();
        this.render();
    }
    
    renderUI(container) {
        container.innerHTML = `
            <div class="learning-dashboard">
                <!-- Header Stats -->
                <div class="dashboard-header">
                    <div class="stat-card">
                        <div class="stat-value" id="total-actions">--</div>
                        <div class="stat-label">Total Actions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="prediction-accuracy">--%</div>
                        <div class="stat-label">Prediction Accuracy</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="neural-status">--</div>
                        <div class="stat-label">Neural Network</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="patterns-learned">--</div>
                        <div class="stat-label">Patterns Learned</div>
                    </div>
                </div>
                
                <!-- Main Content Grid -->
                <div class="dashboard-grid">
                    <!-- Usage Patterns -->
                    <div class="dashboard-card">
                        <h3>📊 Usage Patterns</h3>
                        <div id="usage-patterns"></div>
                    </div>
                    
                    <!-- Top Apps -->
                    <div class="dashboard-card">
                        <h3>🚀 Most Used Apps</h3>
                        <div id="top-apps"></div>
                    </div>
                    
                    <!-- Hourly Activity -->
                    <div class="dashboard-card full-width">
                        <h3>🕐 Activity by Hour</h3>
                        <div id="hourly-chart"></div>
                    </div>
                    
                    <!-- Input Methods -->
                    <div class="dashboard-card">
                        <h3>🎮 Input Method Preference</h3>
                        <div id="input-methods"></div>
                    </div>
                    
                    <!-- Recent Predictions -->
                    <div class="dashboard-card">
                        <h3>🔮 Recent Predictions</h3>
                        <div id="recent-predictions"></div>
                    </div>
                    
                    <!-- Model Performance -->
                    <div class="dashboard-card full-width">
                        <h3>🧠 AI Model Performance</h3>
                        <div id="model-performance"></div>
                    </div>
                    
                    <!-- Training Controls -->
                    <div class="dashboard-card">
                        <h3>⚙️ Model Controls</h3>
                        <div id="model-controls"></div>
                    </div>
                    
                    <!-- Data Management -->
                    <div class="dashboard-card">
                        <h3>🗄️ Data Management</h3>
                        <div id="data-management"></div>
                    </div>
                </div>
            </div>
        `;
        
        // Start auto-refresh
        this.startAutoRefresh();
        
        // Initial render
        this.render();
    }
    
    render() {
        this.renderHeaderStats();
        this.renderUsagePatterns();
        this.renderTopApps();
        this.renderHourlyChart();
        this.renderInputMethods();
        this.renderRecentPredictions();
        this.renderModelPerformance();
        this.renderModelControls();
        this.renderDataManagement();
    }
    
    renderHeaderStats() {
        if (!this.stats) return;
        
        const totalActions = document.getElementById('total-actions');
        const predictionAccuracy = document.getElementById('prediction-accuracy');
        const neuralStatus = document.getElementById('neural-status');
        const patternsLearned = document.getElementById('patterns-learned');
        
        if (totalActions) {
            totalActions.textContent = this.stats.total_actions || 0;
        }
        
        if (predictionAccuracy) {
            const accuracy = (this.stats.prediction_accuracy || 0) * 100;
            predictionAccuracy.textContent = `${accuracy.toFixed(1)}%`;
        }
        
        if (neuralStatus) {
            const nn = this.stats.neural_network || {};
            neuralStatus.textContent = nn.trained ? '✓ Trained' : 'Not Trained';
            neuralStatus.style.color = nn.trained ? '#0f0' : '#fa0';
        }
        
        if (patternsLearned) {
            patternsLearned.textContent = this.stats.temporal_patterns || 0;
        }
    }
    
    renderUsagePatterns() {
        const container = document.getElementById('usage-patterns');
        if (!container || !this.stats) return;
        
        const actions24h = this.stats.actions_last_24h || 0;
        const actions7d = this.stats.actions_last_week || 0;
        
        container.innerHTML = `
            <div class="usage-item">
                <span class="usage-label">Last 24 hours</span>
                <span class="usage-value">${actions24h}</span>
            </div>
            <div class="usage-item">
                <span class="usage-label">Last 7 days</span>
                <span class="usage-value">${actions7d}</span>
            </div>
            <div class="usage-item">
                <span class="usage-label">Avg per day</span>
                <span class="usage-value">${Math.round(actions7d / 7)}</span>
            </div>
        `;
    }
    
    renderTopApps() {
        const container = document.getElementById('top-apps');
        if (!container || !this.stats) return;
        
        const apps = this.stats.most_used_apps || [];
        
        if (apps.length === 0) {
            container.innerHTML = '<div class="no-data">No app data yet</div>';
            return;
        }
        
        const maxCount = apps[0][1];
        
        container.innerHTML = apps.map(([app, count]) => `
            <div class="app-item">
                <div class="app-info">
                    <div class="app-name">${app}</div>
                    <div class="app-count">${count} launches</div>
                </div>
                <div class="app-bar">
                    <div class="app-bar-fill" style="width: ${(count / maxCount) * 100}%"></div>
                </div>
            </div>
        `).join('');
    }
    
    renderHourlyChart() {
        const container = document.getElementById('hourly-chart');
        if (!container || !this.modelStats) return;
        
        const hourlyData = this.modelStats.temporal?.hourly_patterns || {};
        
        // Aggregate counts by hour
        const hourCounts = new Array(24).fill(0);
        Object.entries(hourlyData).forEach(([hour, actions]) => {
            const h = parseInt(hour);
            const count = Object.values(actions).reduce((sum, val) => sum + val, 0);
            hourCounts[h] = count;
        });
        
        const maxCount = Math.max(...hourCounts, 1);
        
        container.innerHTML = `
            <div class="hour-chart">
                ${hourCounts.map((count, hour) => `
                    <div class="hour-bar" title="${hour}:00 - ${count} actions">
                        <div class="hour-bar-fill" style="height: ${(count / maxCount) * 100}%"></div>
                        <div class="hour-label">${hour}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    renderInputMethods() {
        const container = document.getElementById('input-methods');
        if (!container || !this.stats) return;
        
        const methods = this.stats.most_used_input || [];
        
        if (methods.length === 0) {
            container.innerHTML = '<div class="no-data">No input data yet</div>';
            return;
        }
        
        const total = methods.reduce((sum, [, count]) => sum + count, 0);
        
        const colors = {
            'voice': '#0ff',
            'gesture': '#fa0',
            'keyboard': '#0f0',
            'mouse': '#f0f'
        };
        
        container.innerHTML = `
            <div class="input-chart">
                ${methods.map(([method, count]) => {
                    const percent = (count / total) * 100;
                    return `
                        <div class="input-item">
                            <div class="input-label">${method}</div>
                            <div class="input-bar">
                                <div class="input-bar-fill" style="width: ${percent}%; background: ${colors[method] || '#0ff'}"></div>
                            </div>
                            <div class="input-percent">${percent.toFixed(1)}%</div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }
    
    renderRecentPredictions() {
        const container = document.getElementById('recent-predictions');
        if (!container || !this.modelStats) return;
        
        const predictions = this.modelStats.performance?.recent_predictions || [];
        
        if (predictions.length === 0) {
            container.innerHTML = '<div class="no-data">No predictions yet</div>';
            return;
        }
        
        container.innerHTML = `
            <div class="predictions-list">
                ${predictions.slice(0, 5).map(pred => {
                    const timestamp = new Date(pred.timestamp * 1000);
                    const timeStr = timestamp.toLocaleTimeString();
                    
                    return `
                        <div class="prediction-item">
                            <div class="prediction-time">${timeStr}</div>
                            <div class="prediction-actions">
                                ${pred.predictions.slice(0, 3).map(([type, target, conf]) => `
                                    <div class="prediction-action">
                                        <span class="pred-type">${type}</span>
                                        <span class="pred-target">${target}</span>
                                        <span class="pred-conf">${(conf * 100).toFixed(0)}%</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }
    
    renderModelPerformance() {
        const container = document.getElementById('model-performance');
        if (!container || !this.stats) return;
        
        const nn = this.stats.neural_network || {};
        const weights = this.stats.ensemble_weights || {};
        
        container.innerHTML = `
            <div class="model-info">
                <div class="model-stat">
                    <span class="model-label">Neural Network</span>
                    <span class="model-value">${nn.trained ? '✓ Active' : '✗ Not Trained'}</span>
                </div>
                <div class="model-stat">
                    <span class="model-label">Ensemble Weights</span>
                    <div class="weights-grid">
                        ${Object.entries(weights).map(([name, weight]) => `
                            <div class="weight-item">
                                <span>${name}</span>
                                <span>${(weight * 100).toFixed(0)}%</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="model-stat">
                    <span class="model-label">Actions Since Training</span>
                    <span class="model-value">${this.stats.actions_since_training || 0}</span>
                </div>
            </div>
        `;
    }
    
    renderModelControls() {
        const container = document.getElementById('model-controls');
        if (!container) return;
        
        container.innerHTML = `
            <div class="control-buttons">
                <button class="dashboard-btn" onclick="learningDashboard.trainModel()">
                    🧠 Train Neural Network
                </button>
                <button class="dashboard-btn" onclick="learningDashboard.toggleLearning()">
                    ${this.stats?.learning_enabled ? '⏸️ Pause Learning' : '▶️ Resume Learning'}
                </button>
                <button class="dashboard-btn" onclick="learningDashboard.refresh()">
                    🔄 Refresh Data
                </button>
            </div>
        `;
    }
    
    renderDataManagement() {
        const container = document.getElementById('data-management');
        if (!container || !this.stats) return;
        
        container.innerHTML = `
            <div class="data-info">
                <p class="data-desc">All data is stored locally on your device.</p>
                <div class="control-buttons">
                    <button class="dashboard-btn" onclick="learningDashboard.exportData()">
                        📥 Export Data
                    </button>
                    <button class="dashboard-btn btn-danger" onclick="learningDashboard.clearData()">
                        🗑️ Clear All Data
                    </button>
                </div>
            </div>
        `;
    }
    
    async trainModel() {
        this.showNotification('Training neural network...', 'info');
        
        try {
            if (typeof eel !== 'undefined' && eel.train_neural_network) {
                const result = await eel.train_neural_network()();
                
                if (result.success) {
                    this.showNotification(`Model trained! Accuracy: ${(result.accuracy * 100).toFixed(1)}%`, 'success');
                    await this.refresh();
                } else {
                    this.showNotification(`Training failed: ${result.error}`, 'error');
                }
            }
        } catch (error) {
            this.showNotification('Training error: ' + error.message, 'error');
        }
    }
    
    async toggleLearning() {
        try {
            if (typeof eel !== 'undefined' && eel.toggle_learning) {
                const enabled = !this.stats?.learning_enabled;
                const result = await eel.toggle_learning(enabled)();
                
                if (result.success) {
                    this.showNotification(`Learning ${enabled ? 'enabled' : 'disabled'}`, 'success');
                    await this.refresh();
                }
            }
        } catch (error) {
            this.showNotification('Error toggling learning: ' + error.message, 'error');
        }
    }
    
    async exportData() {
        try {
            if (typeof eel !== 'undefined' && eel.get_model_stats_for_dashboard) {
                const data = await eel.get_model_stats_for_dashboard()();
                
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `portaios_learning_data_${Date.now()}.json`;
                a.click();
                URL.revokeObjectURL(url);
                
                this.showNotification('Data exported successfully', 'success');
            }
        } catch (error) {
            this.showNotification('Export failed: ' + error.message, 'error');
        }
    }
    
    async clearData() {
        if (!confirm('Are you sure you want to delete all learning data? This cannot be undone.')) {
            return;
        }
        
        try {
            if (typeof eel !== 'undefined' && eel.clear_learning_data) {
                const result = await eel.clear_learning_data()();
                
                if (result.success) {
                    this.showNotification('All data cleared', 'success');
                    await this.refresh();
                }
            }
        } catch (error) {
            this.showNotification('Clear failed: ' + error.message, 'error');
        }
    }
    
    startAutoRefresh() {
        // Refresh every 30 seconds
        this.refreshInterval = setInterval(() => this.refresh(), 30000);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `dashboard-notification dashboard-notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => notification.classList.add('show'), 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// CSS Styles
const dashboardStyles = document.createElement('style');
dashboardStyles.textContent = `
    .learning-dashboard {
        padding: 20px;
        color: white;
    }
    
    .dashboard-header {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin-bottom: 30px;
    }
    
    .stat-card {
        background: rgba(0, 255, 255, 0.05);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 8px;
        padding: 20px;
        text-align: center;
    }
    
    .stat-value {
        font-size: 32px;
        font-weight: bold;
        color: #0ff;
        margin-bottom: 5px;
    }
    
    .stat-label {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
        text-transform: uppercase;
    }
    
    .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        gap: 20px;
    }
    
    .dashboard-card {
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 8px;
        padding: 20px;
    }
    
    .dashboard-card.full-width {
        grid-column: 1 / -1;
    }
    
    .dashboard-card h3 {
        color: #0ff;
        margin: 0 0 15px 0;
        font-size: 16px;
    }
    
    .usage-item, .app-item, .input-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid rgba(0, 255, 255, 0.1);
    }
    
    .usage-item:last-child, .app-item:last-child, .input-item:last-child {
        border-bottom: none;
    }
    
    .usage-label, .app-name, .input-label {
        font-size: 13px;
        color: rgba(255, 255, 255, 0.8);
    }
    
    .usage-value, .app-count, .input-percent {
        font-size: 14px;
        font-weight: bold;
        color: #0ff;
    }
    
    .app-item {
        flex-direction: column;
        align-items: stretch;
    }
    
    .app-info {
        display: flex;
        justify-content: space-between;
        margin-bottom: 5px;
    }
    
    .app-count {
        font-size: 11px;
    }
    
    .app-bar, .input-bar {
        height: 6px;
        background: rgba(0, 255, 255, 0.1);
        border-radius: 3px;
        overflow: hidden;
    }
    
    .app-bar-fill, .input-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #0ff, #0af);
        transition: width 0.3s;
    }
    
    .hour-chart {
        display: flex;
        gap: 3px;
        height: 150px;
        align-items: flex-end;
        padding: 10px 0;
    }
    
    .hour-bar {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 5px;
    }
    
    .hour-bar-fill {
        width: 100%;
        background: linear-gradient(180deg, #0ff, #0af);
        border-radius: 2px 2px 0 0;
        transition: height 0.3s;
    }
    
    .hour-label {
        font-size: 9px;
        color: rgba(255, 255, 255, 0.5);
    }
    
    .input-item {
        display: grid;
        grid-template-columns: 80px 1fr 50px;
        gap: 10px;
        align-items: center;
    }
    
    .predictions-list, .model-info, .data-info {
        font-size: 13px;
    }
    
    .prediction-item {
        padding: 10px;
        background: rgba(0, 255, 255, 0.05);
        border-radius: 4px;
        margin-bottom: 10px;
    }
    
    .prediction-time {
        color: rgba(255, 255, 255, 0.6);
        font-size: 11px;
        margin-bottom: 5px;
    }
    
    .prediction-action {
        display: flex;
        gap: 10px;
        padding: 3px 0;
        font-size: 12px;
    }
    
    .pred-type {
        color: #fa0;
        min-width: 80px;
    }
    
    .pred-target {
        color: white;
        flex: 1;
    }
    
    .pred-conf {
        color: #0ff;
    }
    
    .model-stat {
        padding: 10px 0;
        border-bottom: 1px solid rgba(0, 255, 255, 0.1);
    }
    
    .model-stat:last-child {
        border-bottom: none;
    }
    
    .model-label {
        color: rgba(255, 255, 255, 0.6);
        font-size: 11px;
        display: block;
        margin-bottom: 5px;
    }
    
    .model-value {
        color: #0ff;
        font-size: 14px;
        font-weight: bold;
    }
    
    .weights-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 5px;
        margin-top: 5px;
    }
    
    .weight-item {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: white;
    }
    
    .control-buttons {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    
    .dashboard-btn {
        padding: 10px 15px;
        background: rgba(0, 255, 255, 0.2);
        border: 1px solid #0ff;
        color: #0ff;
        border-radius: 4px;
        cursor: pointer;
        font-size: 13px;
        transition: all 0.2s;
    }
    
    .dashboard-btn:hover {
        background: rgba(0, 255, 255, 0.3);
    }
    
    .dashboard-btn.btn-danger {
        border-color: #f00;
        color: #f00;
    }
    
    .dashboard-btn.btn-danger:hover {
        background: rgba(255, 0, 0, 0.2);
    }
    
    .data-desc {
        color: rgba(255, 255, 255, 0.6);
        font-size: 12px;
        margin-bottom: 15px;
    }
    
    .no-data {
        text-align: center;
        padding: 30px;
        color: rgba(255, 255, 255, 0.4);
        font-style: italic;
    }
    
    .dashboard-notification {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%) translateY(100px);
        padding: 12px 24px;
        background: rgba(0, 0, 0, 0.9);
        border-radius: 8px;
        color: white;
        font-size: 14px;
        opacity: 0;
        transition: all 0.3s;
        z-index: 10003;
    }
    
    .dashboard-notification.show {
        transform: translateX(-50%) translateY(0);
        opacity: 1;
    }
    
    .dashboard-notification-success {
        border: 2px solid #0f0;
    }
    
    .dashboard-notification-error {
        border: 2px solid #f00;
    }
    
    .dashboard-notification-info {
        border: 2px solid #0ff;
    }
`;
document.head.appendChild(dashboardStyles);

// Create global instance
window.learningDashboard = new LearningDashboard();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LearningDashboard;
}
