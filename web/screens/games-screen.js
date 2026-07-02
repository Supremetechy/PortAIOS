/**
 * Games Screen - Integrated AIOS Mini-Games
 * Consolidates games/AIOS-Games.html into internal screen
 */

export function createGamesScreen() {
  const content = document.createElement('div');
  content.className = 'games-screen-container';
  
  content.innerHTML = `
    <style>
      .games-screen-container {
        height: 100%;
        display: flex;
        flex-direction: column;
        background: linear-gradient(135deg, #0a0f1e, #0f1428);
      }
      
      .games-launcher {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 24px;
        padding: 32px;
        flex: 1;
        overflow-y: auto;
      }
      
      .game-card {
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.1), rgba(0, 200, 255, 0.05));
        border: 2px solid rgba(0, 255, 255, 0.3);
        border-radius: 12px;
        padding: 24px;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
      }
      
      .game-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.2), transparent);
        transition: left 0.5s ease;
      }
      
      .game-card:hover::before {
        left: 100%;
      }
      
      .game-card:hover {
        border-color: #0ff;
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.4);
        transform: translateY(-4px);
      }
      
      .game-icon {
        font-size: 64px;
        margin-bottom: 16px;
        filter: drop-shadow(0 0 10px currentColor);
      }
      
      .game-title {
        font-family: 'Orbitron', monospace;
        font-size: 20px;
        font-weight: 700;
        color: #0ff;
        margin-bottom: 12px;
        text-transform: uppercase;
        letter-spacing: 2px;
      }
      
      .game-description {
        font-size: 13px;
        color: rgba(0, 255, 255, 0.8);
        line-height: 1.6;
        margin-bottom: 16px;
      }
      
      .game-stats {
        display: flex;
        gap: 16px;
        margin-top: auto;
        padding-top: 16px;
        border-top: 1px solid rgba(0, 255, 255, 0.2);
        width: 100%;
        justify-content: center;
      }
      
      .game-stat {
        display: flex;
        flex-direction: column;
        align-items: center;
        font-size: 11px;
        color: rgba(0, 255, 255, 0.6);
      }
      
      .game-stat-value {
        font-size: 16px;
        font-weight: 700;
        color: #0ff;
        margin-bottom: 4px;
      }
      
      .game-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.95);
        z-index: 10000;
        display: none;
        flex-direction: column;
      }
      
      .game-container.active {
        display: flex;
      }
      
      .game-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 24px;
        background: rgba(0, 255, 255, 0.1);
        border-bottom: 2px solid #0ff;
      }
      
      .game-back-btn {
        background: rgba(0, 255, 255, 0.2);
        border: 1px solid #0ff;
        color: #0ff;
        padding: 10px 20px;
        border-radius: 6px;
        font-family: 'Orbitron', monospace;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.3s ease;
      }
      
      .game-back-btn:hover {
        background: rgba(0, 255, 255, 0.3);
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.5);
      }
      
      .game-content {
        flex: 1;
        position: relative;
      }
      
      #game-canvas {
        width: 100%;
        height: 100%;
      }
      
      @media (max-width: 768px) {
        .games-launcher {
          grid-template-columns: 1fr;
          padding: 16px;
        }
      }
    </style>
    
    <div class="games-launcher">
      <div class="game-card" data-game="memory">
        <div class="game-icon">🧠</div>
        <div class="game-title">Memory Matrix</div>
        <div class="game-description">Test your neural pathways with this cyberpunk memory challenge. Match pairs in the grid.</div>
        <div class="game-stats">
          <div class="game-stat">
            <div class="game-stat-value" id="memory-highscore">0</div>
            <div>High Score</div>
          </div>
          <div class="game-stat">
            <div class="game-stat-value" id="memory-plays">0</div>
            <div>Plays</div>
          </div>
        </div>
      </div>
      
      <div class="game-card" data-game="shooter">
        <div class="game-icon">🎯</div>
        <div class="game-title">Neural Shooter</div>
        <div class="game-description">Defend the neural network! Shoot incoming data packets before they corrupt the system.</div>
        <div class="game-stats">
          <div class="game-stat">
            <div class="game-stat-value" id="shooter-highscore">0</div>
            <div>High Score</div>
          </div>
          <div class="game-stat">
            <div class="game-stat-value" id="shooter-plays">0</div>
            <div>Plays</div>
          </div>
        </div>
      </div>
      
      <div class="game-card" data-game="poker">
        <div class="game-icon">🎴</div>
        <div class="game-title">Cyber Poker</div>
        <div class="game-description">Play Texas Hold'em in the digital frontier. Can you outsmart the AI dealer?</div>
        <div class="game-stats">
          <div class="game-stat">
            <div class="game-stat-value" id="poker-balance">1000</div>
            <div>Credits</div>
          </div>
          <div class="game-stat">
            <div class="game-stat-value" id="poker-plays">0</div>
            <div>Plays</div>
          </div>
        </div>
      </div>
      
      <div class="game-card" data-game="coming-soon" style="opacity: 0.6; cursor: not-allowed;">
        <div class="game-icon">🚀</div>
        <div class="game-title">Coming Soon</div>
        <div class="game-description">More neural games in development. Stay tuned for updates!</div>
        <div class="game-stats">
          <div class="game-stat">
            <div class="game-stat-value">?</div>
            <div>Soon™</div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="game-container" id="game-container">
      <div class="game-header">
        <button class="game-back-btn" id="game-back">← Back to Games</button>
        <div style="color: #0ff; font-family: 'Orbitron', monospace; font-size: 18px; font-weight: 700;" id="active-game-title"></div>
        <div style="color: #0ff; font-size: 14px;">Score: <span id="game-score">0</span></div>
      </div>
      <div class="game-content">
        <canvas id="game-canvas"></canvas>
      </div>
    </div>
  `;
  
  return content;
}

/**
 * Initialize games screen functionality
 */
export function initGamesScreen() {
  // Load stats from localStorage
  loadGameStats();
  
  // Game card click handlers
  document.querySelectorAll('.game-card').forEach(card => {
    card.addEventListener('click', () => {
      const game = card.dataset.game;
      if (game && game !== 'coming-soon') {
        launchGame(game);
      }
    });
  });
  
  // Back button
  const backBtn = document.getElementById('game-back');
  if (backBtn) {
    backBtn.addEventListener('click', closeGame);
  }
}

function loadGameStats() {
  const stats = JSON.parse(localStorage.getItem('aios_game_stats') || '{}');
  
  // Memory
  document.getElementById('memory-highscore').textContent = stats.memoryHighScore || 0;
  document.getElementById('memory-plays').textContent = stats.memoryPlays || 0;
  
  // Shooter
  document.getElementById('shooter-highscore').textContent = stats.shooterHighScore || 0;
  document.getElementById('shooter-plays').textContent = stats.shooterPlays || 0;
  
  // Poker
  document.getElementById('poker-balance').textContent = stats.pokerBalance || 1000;
  document.getElementById('poker-plays').textContent = stats.pokerPlays || 0;
}

function saveGameStats(game, stats) {
  const allStats = JSON.parse(localStorage.getItem('aios_game_stats') || '{}');
  Object.assign(allStats, stats);
  localStorage.setItem('aios_game_stats', JSON.stringify(allStats));
  loadGameStats();
}

function launchGame(gameType) {
  const container = document.getElementById('game-container');
  const title = document.getElementById('active-game-title');
  const canvas = document.getElementById('game-canvas');
  
  if (!container || !title || !canvas) return;
  
  // Set title
  const titles = {
    memory: 'Memory Matrix',
    shooter: 'Neural Shooter',
    poker: 'Cyber Poker'
  };
  title.textContent = titles[gameType] || gameType;
  
  // Show container
  container.classList.add('active');
  
  // Initialize game
  switch (gameType) {
    case 'memory':
      initMemoryGame(canvas);
      break;
    case 'shooter':
      initShooterGame(canvas);
      break;
    case 'poker':
      initPokerGame(canvas);
      break;
  }
  
  // Increment play count
  const stats = JSON.parse(localStorage.getItem('aios_game_stats') || '{}');
  const key = `${gameType}Plays`;
  stats[key] = (stats[key] || 0) + 1;
  saveGameStats(gameType, stats);
  
  window.toast?.(`Launching ${titles[gameType]}...`);
}

function closeGame() {
  const container = document.getElementById('game-container');
  if (container) {
    container.classList.remove('active');
  }
  
  // Clean up canvas
  const canvas = document.getElementById('game-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
  
  // Stop any running game loops (would need to track these)
  if (window.currentGameLoop) {
    cancelAnimationFrame(window.currentGameLoop);
    window.currentGameLoop = null;
  }
}

// Simple game implementations (placeholders - real games would import from separate modules)
function initMemoryGame(canvas) {
  canvas.width = canvas.offsetWidth;
  canvas.height = canvas.offsetHeight;
  
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#0a0f1e';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  ctx.fillStyle = '#0ff';
  ctx.font = '24px Orbitron';
  ctx.textAlign = 'center';
  ctx.fillText('Memory Matrix - Coming Soon', canvas.width / 2, canvas.height / 2);
  ctx.font = '16px "Share Tech Mono"';
  ctx.fillText('Full game implementation in progress', canvas.width / 2, canvas.height / 2 + 40);
}

function initShooterGame(canvas) {
  canvas.width = canvas.offsetWidth;
  canvas.height = canvas.offsetHeight;
  
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#0a0f1e';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  ctx.fillStyle = '#0ff';
  ctx.font = '24px Orbitron';
  ctx.textAlign = 'center';
  ctx.fillText('Neural Shooter - Coming Soon', canvas.width / 2, canvas.height / 2);
  ctx.font = '16px "Share Tech Mono"';
  ctx.fillText('Full game implementation in progress', canvas.width / 2, canvas.height / 2 + 40);
}

function initPokerGame(canvas) {
  canvas.width = canvas.offsetWidth;
  canvas.height = canvas.offsetHeight;
  
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#0a0f1e';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  ctx.fillStyle = '#0ff';
  ctx.font = '24px Orbitron';
  ctx.textAlign = 'center';
  ctx.fillText('Cyber Poker - Coming Soon', canvas.width / 2, canvas.height / 2);
  ctx.font = '16px "Share Tech Mono"';
  ctx.fillText('Full game implementation in progress', canvas.width / 2, canvas.height / 2 + 40);
}

// Export game stats functions for external access
export { loadGameStats, saveGameStats };
