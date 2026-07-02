export class MemoryGame {
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
        this.cards = [];
        this.flippedCards = [];
        this.matchedCount = 0;
        this.canFlip = true;
    }

    init() {
        this.container.innerHTML = `
            <style>
                #memory-grid {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    padding: 20px;
                    height: 100%;
                    box-sizing: border-box;
                    align-content: center;
                    justify-items: center;
                }
                .memory-card {
                    aspect-ratio: 3/4;
                    width: 100%;
                    max-width: 120px;
                    background: #111;
                    border: 2px solid #333;
                    border-radius: 8px;
                    cursor: pointer;
                    position: relative;
                    transform-style: preserve-3d;
                    transition: transform 0.5s, border-color 0.3s;
                }
                .memory-card.flipped {
                    transform: rotateY(180deg);
                    border-color: var(--neon-blue);
                }
                .memory-card .face {
                    position: absolute;
                    width: 100%;
                    height: 100%;
                    backface-visibility: hidden;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 6px;
                    overflow: hidden;
                }
                .memory-card .back {
                    background-image: url('assets/images/card_back.webp');
                    background-size: cover;
                }
                .memory-card .front {
                    background: #1a1a1a;
                    transform: rotateY(180deg);
                }
                .memory-card .front img {
                    width: 70%;
                    height: 70%;
                    object-fit: contain;
                }
                #memory-hud {
                    position: absolute;
                    top: 10px;
                    right: 20px;
                    font-family: 'Orbitron', sans-serif;
                    color: var(--neon-blue);
                }
            </style>
            <div id="memory-hud">MATCHED: <span id="match-count">0</span>/8</div>
            <div id="memory-grid"></div>
        `;

        this.grid = this.container.querySelector('#memory-grid');
        this.matchDisplay = this.container.querySelector('#match-count');
        this.setupBoard();
    }

    setupBoard() {
        const gameIcons = [...this.icons, ...this.icons];
        gameIcons.sort(() => Math.random() - 0.5);

        this.grid.innerHTML = '';
        this.cards = gameIcons.map((icon, index) => {
            const card = document.createElement('div');
            card.className = 'memory-card';
            card.dataset.icon = icon;
            card.dataset.index = index;
            card.innerHTML = `
                <div class="face back"></div>
                <div class="face front">
                    <img src="${icon}" alt="icon">
                </div>
            `;
            card.addEventListener('click', () => this.flipCard(card));
            this.grid.appendChild(card);
            return card;
        });

        this.matchedCount = 0;
        this.flippedCards = [];
        this.canFlip = true;
        this.updateHUD();
    }

    // ── External control API (voice / gesture) ────────────────────────────
    flipCardByIndex(i) {
        const card = this.cards[i];
        if (card) this.flipCard(card);
    }

    flipCardByPosition(normX, normY) {
        // Map normalized cursor coords to card under the cursor
        const x = normX * window.innerWidth;
        const y = normY * window.innerHeight;
        const el = document.elementFromPoint(x, y)?.closest('.memory-card');
        if (el) this.flipCard(el);
    }

    revealHint() {
        if (!this.canFlip) return;
        // Briefly show all unmatched cards
        this.cards.forEach(c => { if (!c.dataset.matched) c.classList.add('flipped'); });
        setTimeout(() => {
            this.cards.forEach(c => {
                if (!c.dataset.matched && !this.flippedCards.includes(c)) c.classList.remove('flipped');
            });
        }, 800);
    }

    restart() {
        // Remove any overlay
        this.container.querySelector('.overlay')?.remove();
        this.setupBoard();
    }
    // ─────────────────────────────────────────────────────────────────────────

    flipCard(card) {
        if (!this.canFlip || card.classList.contains('flipped') || this.flippedCards.includes(card)) return;

        card.classList.add('flipped');
        this.flippedCards.push(card);

        if (this.flippedCards.length === 2) {
            this.checkMatch();
        }
    }

    checkMatch() {
        this.canFlip = false;
        const [card1, card2] = this.flippedCards;
        const isMatch = card1.dataset.icon === card2.dataset.icon;

        if (isMatch) {
            card1.dataset.matched = '1';
            card2.dataset.matched = '1';
            this.matchedCount++;
            this.flippedCards = [];
            this.canFlip = true;
            this.updateHUD();
            window.playSound('ui_success_chime');
            
            if (this.matchedCount === this.icons.length) {
                this.showWin();
            }
        } else {
            setTimeout(() => {
                card1.classList.remove('flipped');
                card2.classList.remove('flipped');
                this.flippedCards = [];
                this.canFlip = true;
            }, 1000);
        }
    }

    updateHUD() {
        this.matchDisplay.textContent = this.matchedCount;
    }

    showWin() {
        const overlay = document.createElement('div');
        overlay.className = 'overlay';
        overlay.innerHTML = `
            <h1 style="font-family:Orbitron; color:var(--neon-blue);">MEMORY SYNC COMPLETE</h1>
            <p>All neural pathways restored.</p>
            <button class="btn" id="restart-memory">RESTART</button>
        `;
        this.container.appendChild(overlay);
        overlay.querySelector('#restart-memory').onclick = () => {
            overlay.remove();
            this.setupBoard();
        };
    }
}
