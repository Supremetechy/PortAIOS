export class ShooterGame {
    constructor(container) {
        this.container = container;
        this.canvas = null;
        this.ctx = null;
        this.player = null;
        this.enemies = [];
        this.bullets = [];
        this.particles = [];
        this.score = 0;
        this.isGameOver = false;
        this.lastTime = 0;
        this.spawnTimer = 0;
        this.keys = {};
        this.mouse = { x: 0, y: 0, down: false };
        
        this.assets = {
            player: new Image(),
            enemy: new Image(),
            bg: new Image()
        };
        this.assets.player.src = 'assets/images/player_ship.webp';
        this.assets.enemy.src = 'assets/images/energy_drone.webp';
        this.assets.bg.src = 'assets/images/shooter_bg_title.webp';

        // External control state
        this.voiceMove    = { dx: 0, dy: 0, active: false, timer: null };
        this.gesturePos   = null; // { x, y } normalized, maps to canvas
        this.externalFire = false;
    }

    init() {
        this.container.innerHTML = `
            <style>
                #shooter-canvas {
                    display: block;
                    width: 100%;
                    height: 100%;
                    background: #000;
                }
                #shooter-hud {
                    position: absolute;
                    top: 15px;
                    left: 20px;
                    font-family: 'Orbitron', sans-serif;
                    color: var(--neon-magenta);
                    pointer-events: none;
                    font-size: 18px;
                    z-index: 5;
                }
            </style>
            <div id="shooter-hud">SCORE: <span id="shooter-score">0</span></div>
            <canvas id="shooter-canvas"></canvas>
        `;

        this.canvas = this.container.querySelector('#shooter-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.scoreDisplay = this.container.querySelector('#shooter-score');

        window.addEventListener('resize', () => this.resize());
        this.resize();

        this.player = {
            x: this.canvas.width / 2,
            y: this.canvas.height / 2,
            radius: 20,
            speed: 5,
            angle: 0
        };

        this.setupInput();
        this.start();
    }

    resize() {
        const rect = this.container.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
    }

    // ── External control API (voice / gesture) ────────────────────────────
    setVoiceMove(dx, dy) {
        // Apply a burst of movement in the given direction (normalized -1…1)
        clearTimeout(this.voiceMove.timer);
        this.voiceMove = { dx, dy, active: true,
            timer: setTimeout(() => { this.voiceMove.active = false; }, 800) };
    }

    setHandPosition(normX, normY) {
        // Gesture: move player toward hand position on canvas
        this.gesturePos = { x: normX, y: normY };
        clearTimeout(this._gesturePosTimer);
        this._gesturePosTimer = setTimeout(() => { this.gesturePos = null; }, 200);
    }

    setAutoFire(on) { this.externalFire = on; }

    restart() {
        this.container.querySelector('.overlay')?.remove();
        this.start();
    }
    // ─────────────────────────────────────────────────────────────────────────

    setupInput() {
        this.container.onmousemove = (e) => {
            const rect = this.canvas.getBoundingClientRect();
            this.mouse.x = e.clientX - rect.left;
            this.mouse.y = e.clientY - rect.top;
        };
        this.container.onmousedown = () => this.mouse.down = true;
        this.container.onmouseup = () => this.mouse.down = false;

        window.addEventListener('keydown', (e) => this.keys[e.code] = true);
        window.addEventListener('keyup', (e) => this.keys[e.code] = false);
    }

    start() {
        this.isGameOver = false;
        this.score = 0;
        this.enemies = [];
        this.bullets = [];
        this.particles = [];
        this.spawnTimer = 0;
        this.scoreDisplay.textContent = '0';
        requestAnimationFrame((t) => this.loop(t));
    }

    spawnEnemy() {
        const side = Math.floor(Math.random() * 4);
        let x, y;
        if (side === 0) { x = Math.random() * this.canvas.width; y = -50; }
        else if (side === 1) { x = this.canvas.width + 50; y = Math.random() * this.canvas.height; }
        else if (side === 2) { x = Math.random() * this.canvas.width; y = this.canvas.height + 50; }
        else { x = -50; y = Math.random() * this.canvas.height; }

        this.enemies.push({
            x, y,
            radius: 20,
            speed: 1.5 + Math.random() * 2
        });
    }

    shoot() {
        const dx = this.mouse.x - this.player.x;
        const dy = this.mouse.y - this.player.y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        
        this.bullets.push({
            x: this.player.x,
            y: this.player.y,
            vx: (dx / dist) * 8,
            vy: (dy / dist) * 8,
            radius: 4
        });
        window.playSound('laser_shot');
    }

    loop(time) {
        if (this.isGameOver || !this.container.offsetParent) return;

        const dt = (time - this.lastTime) / 16.66;
        this.lastTime = time;

        this.update(dt);
        this.draw();

        requestAnimationFrame((t) => this.loop(t));
    }

    update(dt) {
        // Player movement — keyboard
        if (this.keys['KeyW'] || this.keys['ArrowUp'])    this.player.y -= this.player.speed * dt;
        if (this.keys['KeyS'] || this.keys['ArrowDown'])  this.player.y += this.player.speed * dt;
        if (this.keys['KeyA'] || this.keys['ArrowLeft'])  this.player.x -= this.player.speed * dt;
        if (this.keys['KeyD'] || this.keys['ArrowRight']) this.player.x += this.player.speed * dt;

        // Voice directional burst
        if (this.voiceMove.active) {
            this.player.x += this.voiceMove.dx * this.player.speed * 2.5 * dt;
            this.player.y += this.voiceMove.dy * this.player.speed * 2.5 * dt;
        }

        // Gesture hand-position tracking (smooth lerp)
        if (this.gesturePos) {
            const tx = this.gesturePos.x * this.canvas.width;
            const ty = this.gesturePos.y * this.canvas.height;
            this.player.x += (tx - this.player.x) * 0.12 * dt;
            this.player.y += (ty - this.player.y) * 0.12 * dt;
        }

        // Keep player in bounds
        this.player.x = Math.max(20, Math.min(this.canvas.width - 20, this.player.x));
        this.player.y = Math.max(20, Math.min(this.canvas.height - 20, this.player.y));

        // Player angle
        this.player.angle = Math.atan2(this.mouse.y - this.player.y, this.mouse.x - this.player.x) + Math.PI / 2;

        // Shooting — mouse hold or external-fire (voice / gesture)
        if ((this.mouse.down || this.externalFire) && Math.random() < 0.15 * dt) {
            this.shoot();
        }

        // Bullets
        this.bullets.forEach((b, i) => {
            b.x += b.vx * dt;
            b.y += b.vy * dt;
            if (b.x < 0 || b.x > this.canvas.width || b.y < 0 || b.y > this.canvas.height) {
                this.bullets.splice(i, 1);
            }
        });

        // Spawn enemies
        this.spawnTimer += dt;
        if (this.spawnTimer > 60) {
            this.spawnEnemy();
            this.spawnTimer = 0;
        }

        // Enemies
        this.enemies.forEach((e, ei) => {
            const dx = this.player.x - e.x;
            const dy = this.player.y - e.y;
            const dist = Math.sqrt(dx*dx + dy*dy);
            e.x += (dx / dist) * e.speed * dt;
            e.y += (dy / dist) * e.speed * dt;

            // Collision with player
            if (dist < this.player.radius + e.radius) {
                this.gameOver();
            }

            // Collision with bullets
            this.bullets.forEach((b, bi) => {
                const bdx = b.x - e.x;
                const bdy = b.y - e.y;
                const bdist = Math.sqrt(bdx*bdx + bdy*bdy);
                if (bdist < b.radius + e.radius) {
                    this.enemies.splice(ei, 1);
                    this.bullets.splice(bi, 1);
                    this.score += 10;
                    this.scoreDisplay.textContent = this.score;
                    this.createExplosion(e.x, e.y);
                    window.playSound('explosion_digital');
                }
            });
        });

        // Particles
        this.particles.forEach((p, i) => {
            p.x += p.vx * dt;
            p.y += p.vy * dt;
            p.life -= 0.02 * dt;
            if (p.life <= 0) this.particles.splice(i, 1);
        });
    }

    createExplosion(x, y) {
        for (let i = 0; i < 8; i++) {
            const angle = Math.random() * Math.PI * 2;
            const speed = 1 + Math.random() * 3;
            this.particles.push({
                x, y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: 1,
                color: '#ff0000'
            });
        }
    }

    draw() {
        this.ctx.fillStyle = '#050505';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // BG Tile (simple pattern for now as texture might need tiling)
        const pattern = this.ctx.createPattern(this.assets.bg, 'repeat');
        if (pattern) {
            this.ctx.save();
            this.ctx.globalAlpha = 0.2;
            this.ctx.fillStyle = pattern;
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.restore();
        }

        // Bullets
        this.ctx.fillStyle = varColor('--neon-blue');
        this.bullets.forEach(b => {
            this.ctx.beginPath();
            this.ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
            this.ctx.fill();
        });

        // Particles
        this.particles.forEach(p => {
            this.ctx.globalAlpha = p.life;
            this.ctx.fillStyle = p.color;
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
            this.ctx.fill();
        });
        this.ctx.globalAlpha = 1;

        // Enemies
        this.enemies.forEach(e => {
            this.ctx.drawImage(this.assets.enemy, e.x - e.radius, e.y - e.radius, e.radius * 2, e.radius * 2);
        });

        // Player
        this.ctx.save();
        this.ctx.translate(this.player.x, this.player.y);
        this.ctx.rotate(this.player.angle);
        this.ctx.drawImage(this.assets.player, -this.player.radius, -this.player.radius, this.player.radius * 2, this.player.radius * 2);
        this.ctx.restore();
    }

    gameOver() {
        this.isGameOver = true;
        const overlay = document.createElement('div');
        overlay.className = 'overlay';
        overlay.innerHTML = `
            <h1 style="font-family:Orbitron; color:#ff3333;">SYSTEM COMPROMISED</h1>
            <p>Score: ${this.score}</p>
            <button class="btn" id="restart-shooter">REBOOT</button>
        `;
        this.container.appendChild(overlay);
        overlay.querySelector('#restart-shooter').onclick = () => {
            overlay.remove();
            this.start();
        };
    }
}

function varColor(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
