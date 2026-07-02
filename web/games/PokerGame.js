export class PokerGame {
    constructor(container) {
        this.container = container;
        this.icons = [
            'assets/images/icon_microchip.webp',
            'assets/images/icon_brain_circuits.webp',
            'assets/images/icon_code_brackets.webp',
            'assets/images/icon_wifi_signal.webp',
            'assets/images/icon_gear_setting.webp',
            'assets/images/icon_atom_energy.webp',
            'assets/images/icon_lock_security.webp',
            'assets/images/icon_power_button.webp'
        ];
        this.suits = ['#00f2ff', '#ff00ff', '#ffff00', '#00ff00'];
        this.deck = [];
        this.currentHand = [];
        this.targetHand = '';
        this.score = 0;
        this.round = 1;
        this.maxRounds = 5;
    }

    init() {
        this.container.innerHTML = `
            <style>
                #poker-layout {
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    padding: 20px;
                    box-sizing: border-box;
                    justify-content: space-around;
                }
                #target-panel {
                    padding: 15px 30px;
                    background: rgba(0, 242, 255, 0.1);
                    border: 2px solid var(--neon-blue);
                    border-radius: 8px;
                    text-align: center;
                }
                #target-hand-name {
                    font-family: 'Orbitron', sans-serif;
                    font-size: 24px;
                    color: var(--neon-blue);
                    text-transform: uppercase;
                }
                #cards-hand {
                    display: flex;
                    gap: 10px;
                    justify-content: center;
                    flex-wrap: wrap;
                }
                .poker-card {
                    width: 100px;
                    aspect-ratio: 3/4;
                    background: #1a1a1a;
                    border: 2px solid #333;
                    border-radius: 10px;
                    cursor: pointer;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: space-between;
                    padding: 10px;
                    transition: transform 0.2s, border-color 0.2s;
                    position: relative;
                }
                .poker-card.selected {
                    border-color: var(--neon-blue);
                    transform: translateY(-20px);
                    box-shadow: 0 0 15px var(--neon-blue);
                }
                .poker-card .suit-dot {
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    position: absolute;
                    top: 10px;
                    left: 10px;
                }
                .poker-card img {
                    width: 60%;
                    height: 60%;
                    object-fit: contain;
                }
                #poker-hud {
                    width: 100%;
                    display: flex;
                    justify-content: space-between;
                    font-family: 'Orbitron', sans-serif;
                    color: #aaa;
                }
            </style>
            <div id="poker-layout">
                <div id="poker-hud">
                    <span>ROUND: <span id="poker-round">1</span>/5</span>
                    <span>SCORE: <span id="poker-score">0</span></span>
                </div>
                <div id="target-panel">
                    <div style="font-size: 12px; margin-bottom: 5px; opacity: 0.7;">QUANTUM GOAL</div>
                    <div id="target-hand-name">THREE OF A KIND</div>
                </div>
                <div id="cards-hand"></div>
                <button class="btn" id="submit-hand">ANALYZE SELECTION</button>
            </div>
        `;

        this.handDiv = this.container.querySelector('#cards-hand');
        this.submitBtn = this.container.querySelector('#submit-hand');
        this.submitBtn.onclick = () => this.checkHand();

        // ── External control API (voice / gesture) ────────────────────────
        this._setupExternalAPI();

        this.startRound();
    }

    _setupExternalAPI() {
        // nothing extra — methods below are called directly by main.js
    }

    toggleCardAt(i) {
        const card = this.currentHand[i];
        const el   = this.handDiv.querySelectorAll('.poker-card')[i];
        if (!card || !el) return;
        card.selected = !card.selected;
        el.classList.toggle('selected', card.selected);
    }

    toggleCardByPosition(normX, normY) {
        const x  = normX * window.innerWidth;
        const y  = normY * window.innerHeight;
        const el = document.elementFromPoint(x, y)?.closest('.poker-card');
        if (!el) return;
        const cards = [...this.handDiv.querySelectorAll('.poker-card')];
        const i = cards.indexOf(el);
        if (i >= 0) this.toggleCardAt(i);
    }

    clearSelection() {
        this.currentHand.forEach((c, i) => {
            c.selected = false;
            const el = this.handDiv.querySelectorAll('.poker-card')[i];
            if (el) el.classList.remove('selected');
        });
    }

    submitHand() { this.checkHand(); }

    restart() {
        this.container.querySelector('.overlay')?.remove();
        this.round = 1;
        this.score = 0;
        this.startRound();
    }

    startRound() {
        this.generateTarget();
        this.dealCards();
        this.updateHUD();
    }

    generateTarget() {
        const targets = ['PAIR', 'TWO PAIR', 'THREE OF A KIND', 'FLUSH'];
        this.targetHand = targets[Math.floor(Math.random() * targets.length)];
        this.container.querySelector('#target-hand-name').textContent = this.targetHand;
    }

    dealCards() {
        this.currentHand = [];
        this.handDiv.innerHTML = '';
        
        // Generate a pool of 8 cards to select from
        for (let i = 0; i < 8; i++) {
            const card = {
                rank: Math.floor(Math.random() * this.icons.length),
                suit: Math.floor(Math.random() * this.suits.length),
                selected: false
            };
            this.createCardElement(card);
            this.currentHand.push(card);
        }
    }

    createCardElement(card) {
        const el = document.createElement('div');
        el.className = 'poker-card';
        el.innerHTML = `
            <div class="suit-dot" style="background: ${this.suits[card.suit]}"></div>
            <img src="${this.icons[card.rank]}" alt="rank">
        `;
        el.onclick = () => {
            card.selected = !card.selected;
            el.classList.toggle('selected', card.selected);
        };
        this.handDiv.appendChild(el);
    }

    checkHand() {
        const selected = this.currentHand.filter(c => c.selected);
        if (selected.length === 0) return;

        let win = false;
        const ranks = selected.map(c => c.rank);
        const suits = selected.map(c => c.suit);
        
        const rankCounts = {};
        ranks.forEach(r => rankCounts[r] = (rankCounts[r] || 0) + 1);
        const counts = Object.values(rankCounts);

        if (this.targetHand === 'PAIR') {
            win = counts.some(c => c >= 2);
        } else if (this.targetHand === 'TWO PAIR') {
            win = counts.filter(c => c >= 2).length >= 2;
        } else if (this.targetHand === 'THREE OF A KIND') {
            win = counts.some(c => c >= 3);
        } else if (this.targetHand === 'FLUSH') {
            const suitCounts = {};
            suits.forEach(s => suitCounts[s] = (suitCounts[s] || 0) + 1);
            win = Object.values(suitCounts).some(c => c >= 5);
        }

        if (win) {
            this.score += 100;
            window.playSound('ui_success_chime');
            this.showResult('TARGET MATCHED', varColor('--neon-blue'));
        } else {
            this.showResult('TARGET FAILED', '#ff3333');
        }
    }

    showResult(msg, color) {
        const overlay = document.createElement('div');
        overlay.className = 'overlay';
        overlay.innerHTML = `
            <h1 style="font-family:Orbitron; color:${color};">${msg}</h1>
            <button class="btn" id="next-round">CONTINUE</button>
        `;
        this.container.appendChild(overlay);
        overlay.querySelector('#next-round').onclick = () => {
            overlay.remove();
            this.round++;
            if (this.round > this.maxRounds) {
                this.showGameOver();
            } else {
                this.startRound();
            }
        };
    }

    showGameOver() {
        const overlay = document.createElement('div');
        overlay.className = 'overlay';
        overlay.innerHTML = `
            <h1 style="font-family:Orbitron; color:var(--neon-blue);">SESSION COMPLETE</h1>
            <p>Final Score: ${this.score}</p>
            <button class="btn" id="poker-restart">RESTART</button>
        `;
        this.container.appendChild(overlay);
        overlay.querySelector('#poker-restart').onclick = () => {
            overlay.remove();
            this.round = 1;
            this.score = 0;
            this.startRound();
        };
    }

    updateHUD() {
        this.container.querySelector('#poker-round').textContent = this.round;
        this.container.querySelector('#poker-score').textContent = this.score;
    }
}

function varColor(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
