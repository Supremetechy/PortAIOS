/**
 * Avatar Animation Sequences
 * Pre-built expression and lip-sync animations
 */

export const EXPRESSION_ANIMATIONS = {
    greet: {
        name: "Greeting",
        description: "Friendly wave and smile",
        duration: 3000,
        keyframes: [
            {
                time: 0,
                duration: 500,
                morphs: {
                    'Smile': 0.8,
                    'mouthSmileLeft': 0.8,
                    'mouthSmileRight': 0.8,
                    'eyeBlinkLeft': 0.0,
                    'eyeBlinkRight': 0.0
                },
                hold: 500
            },
            {
                time: 1000,
                duration: 200,
                morphs: {
                    'eyeBlinkLeft': 1.0,
                    'eyeBlinkRight': 1.0
                },
                hold: 100
            },
            {
                time: 1300,
                duration: 200,
                morphs: {
                    'eyeBlinkLeft': 0.0,
                    'eyeBlinkRight': 0.0
                },
                hold: 300
            }
        ]
    },
    
    surprise: {
        name: "Surprise",
        description: "Surprised expression",
        duration: 2000,
        keyframes: [
            {
                time: 0,
                duration: 300,
                morphs: {
                    'Surprise': 1.0,
                    'browInnerUp': 1.0,
                    'jawOpen': 0.6
                },
                hold: 800
            },
            {
                time: 1100,
                duration: 500,
                morphs: {
                    'Surprise': 0.0,
                    'browInnerUp': 0.0,
                    'jawOpen': 0.0
                },
                hold: 0
            }
        ]
    },
    
    think: {
        name: "Thinking",
        description: "Contemplative expression",
        duration: 3000,
        keyframes: [
            {
                time: 0,
                duration: 500,
                morphs: {
                    'browInnerUp': 0.4,
                    'Frown': 0.2
                },
                hold: 1000
            },
            {
                time: 1500,
                duration: 300,
                morphs: {
                    'Wink_Left': 0.5,
                    'eyeBlinkLeft': 0.5
                },
                hold: 200
            },
            {
                time: 2000,
                duration: 500,
                morphs: {
                    'Wink_Left': 0.0,
                    'eyeBlinkLeft': 0.0,
                    'browInnerUp': 0.0,
                    'Frown': 0.0
                },
                hold: 0
            }
        ]
    },
    
    happy: {
        name: "Happy",
        description: "Joyful expression",
        duration: 2500,
        keyframes: [
            {
                time: 0,
                duration: 400,
                morphs: {
                    'Smile': 1.0,
                    'mouthSmileLeft': 1.0,
                    'mouthSmileRight': 1.0,
                    'browInnerUp': 0.3
                },
                hold: 1000
            },
            {
                time: 1400,
                duration: 150,
                morphs: {
                    'eyeBlinkLeft': 1.0,
                    'eyeBlinkRight': 1.0
                },
                hold: 100
            },
            {
                time: 1650,
                duration: 150,
                morphs: {
                    'eyeBlinkLeft': 0.0,
                    'eyeBlinkRight': 0.0
                },
                hold: 200
            },
            {
                time: 2000,
                duration: 500,
                morphs: {
                    'Smile': 0.0,
                    'mouthSmileLeft': 0.0,
                    'mouthSmileRight': 0.0,
                    'browInnerUp': 0.0
                },
                hold: 0
            }
        ]
    },
    
    blink: {
        name: "Blink",
        description: "Natural blink",
        duration: 400,
        keyframes: [
            {
                time: 0,
                duration: 100,
                morphs: {
                    'eyeBlinkLeft': 1.0,
                    'eyeBlinkRight': 1.0
                },
                hold: 50
            },
            {
                time: 150,
                duration: 100,
                morphs: {
                    'eyeBlinkLeft': 0.0,
                    'eyeBlinkRight': 0.0
                },
                hold: 0
            }
        ]
    },
    
    wink: {
        name: "Wink",
        description: "Playful wink",
        duration: 1000,
        keyframes: [
            {
                time: 0,
                duration: 200,
                morphs: {
                    'Wink_Left': 1.0,
                    'eyeBlinkLeft': 1.0,
                    'Smile': 0.6,
                    'mouthSmileLeft': 0.6,
                    'mouthSmileRight': 0.6
                },
                hold: 300
            },
            {
                time: 500,
                duration: 300,
                morphs: {
                    'Wink_Left': 0.0,
                    'eyeBlinkLeft': 0.0,
                    'Smile': 0.0,
                    'mouthSmileLeft': 0.0,
                    'mouthSmileRight': 0.0
                },
                hold: 0
            }
        ]
    }
};

export const LIPSYNC_ANIMATIONS = {
    hello: {
        name: "Say 'Hello'",
        description: "Lip-sync for the word 'Hello'",
        duration: 1000,
        keyframes: [
            // H sound
            {
                time: 0,
                duration: 100,
                morphs: {
                    'jawOpen': 0.3,
                    'viseme_PP': 0.0
                },
                hold: 50
            },
            // EH sound
            {
                time: 150,
                duration: 150,
                morphs: {
                    'jawOpen': 0.5,
                    'viseme_E': 0.8,
                    'Viseme_E': 0.8
                },
                hold: 100
            },
            // L sound
            {
                time: 400,
                duration: 100,
                morphs: {
                    'jawOpen': 0.3,
                    'viseme_E': 0.2
                },
                hold: 50
            },
            // OW sound
            {
                time: 550,
                duration: 200,
                morphs: {
                    'jawOpen': 0.6,
                    'viseme_O': 0.9,
                    'Viseme_O': 0.9
                },
                hold: 150
            },
            // Close
            {
                time: 900,
                duration: 100,
                morphs: {
                    'jawOpen': 0.0,
                    'viseme_O': 0.0,
                    'Viseme_O': 0.0
                },
                hold: 0
            }
        ]
    },
    
    yes: {
        name: "Say 'Yes'",
        description: "Lip-sync for 'Yes'",
        duration: 800,
        keyframes: [
            // Y sound
            {
                time: 0,
                duration: 100,
                morphs: {
                    'jawOpen': 0.3,
                    'viseme_E': 0.5
                },
                hold: 50
            },
            // EH sound
            {
                time: 150,
                duration: 200,
                morphs: {
                    'jawOpen': 0.5,
                    'viseme_E': 0.9,
                    'Viseme_E': 0.9
                },
                hold: 150
            },
            // S sound
            {
                time: 500,
                duration: 200,
                morphs: {
                    'jawOpen': 0.2,
                    'viseme_E': 0.3,
                    'viseme_PP': 0.5
                },
                hold: 100
            },
            // Close
            {
                time: 700,
                duration: 100,
                morphs: {
                    'jawOpen': 0.0,
                    'viseme_E': 0.0,
                    'viseme_PP': 0.0
                },
                hold: 0
            }
        ]
    },
    
    wow: {
        name: "Say 'Wow'",
        description: "Lip-sync for 'Wow' with surprise",
        duration: 1200,
        keyframes: [
            // W sound
            {
                time: 0,
                duration: 150,
                morphs: {
                    'jawOpen': 0.3,
                    'viseme_O': 0.5,
                    'Viseme_O': 0.5
                },
                hold: 50
            },
            // OW sound
            {
                time: 200,
                duration: 300,
                morphs: {
                    'jawOpen': 0.8,
                    'viseme_O': 1.0,
                    'Viseme_O': 1.0,
                    'Surprise': 0.7,
                    'browInnerUp': 0.7
                },
                hold: 400
            },
            // Close
            {
                time: 900,
                duration: 300,
                morphs: {
                    'jawOpen': 0.0,
                    'viseme_O': 0.0,
                    'Viseme_O': 0.0,
                    'Surprise': 0.0,
                    'browInnerUp': 0.0
                },
                hold: 0
            }
        ]
    },
    
    counting: {
        name: "Count 1-2-3",
        description: "Lip-sync for counting",
        duration: 2500,
        keyframes: [
            // "One"
            {
                time: 0,
                duration: 200,
                morphs: {
                    'jawOpen': 0.5,
                    'viseme_O': 0.7
                },
                hold: 300
            },
            // Close
            {
                time: 500,
                duration: 100,
                morphs: {
                    'jawOpen': 0.0,
                    'viseme_O': 0.0
                },
                hold: 100
            },
            // "Two"
            {
                time: 700,
                duration: 200,
                morphs: {
                    'jawOpen': 0.4,
                    'viseme_O': 0.8
                },
                hold: 300
            },
            // Close
            {
                time: 1200,
                duration: 100,
                morphs: {
                    'jawOpen': 0.0,
                    'viseme_O': 0.0
                },
                hold: 100
            },
            // "Three"
            {
                time: 1400,
                duration: 250,
                morphs: {
                    'jawOpen': 0.6,
                    'viseme_E': 0.9
                },
                hold: 400
            },
            // Close
            {
                time: 2050,
                duration: 200,
                morphs: {
                    'jawOpen': 0.0,
                    'viseme_E': 0.0
                },
                hold: 0
            }
        ]
    }
};

export const IDLE_ANIMATIONS = {
    naturalBlink: {
        name: "Natural Blinking",
        description: "Automatic random blinking",
        enabled: true,
        minInterval: 2000,
        maxInterval: 5000,
        animation: EXPRESSION_ANIMATIONS.blink
    },
    
    subtleMovement: {
        name: "Subtle Movement",
        description: "Minor facial movements for realism",
        enabled: false,
        interval: 3000,
        keyframes: [
            {
                time: 0,
                duration: 1000,
                morphs: {
                    'browInnerUp': 0.1
                },
                hold: 500
            },
            {
                time: 1500,
                duration: 1000,
                morphs: {
                    'browInnerUp': 0.0
                },
                hold: 0
            }
        ]
    }
};

/**
 * Animation player class
 */
export class AnimationPlayer {
    constructor(avatarPreview) {
        this.preview = avatarPreview;
        this.isPlaying = false;
        this.queue = [];
        this.idleTimers = {};
    }
    
    play(animationKey, category = 'expression') {
        let animation;
        
        if (category === 'expression') {
            animation = EXPRESSION_ANIMATIONS[animationKey];
        } else if (category === 'lipsync') {
            animation = LIPSYNC_ANIMATIONS[animationKey];
        }
        
        if (!animation) {
            console.warn(`[AnimationPlayer] Animation not found: ${animationKey}`);
            return;
        }
        
        console.log(`[AnimationPlayer] Playing: ${animation.name}`);
        this.preview.playExpressionSequence(animation);
    }
    
    queue(animationKeys) {
        this.queue = animationKeys;
        this.playNext();
    }
    
    playNext() {
        if (this.queue.length === 0) {
            this.isPlaying = false;
            return;
        }
        
        this.isPlaying = true;
        const next = this.queue.shift();
        
        const animation = EXPRESSION_ANIMATIONS[next] || LIPSYNC_ANIMATIONS[next];
        if (animation) {
            this.play(next);
            setTimeout(() => this.playNext(), animation.duration);
        }
    }
    
    startIdle(idleKey) {
        const idle = IDLE_ANIMATIONS[idleKey];
        if (!idle || !idle.enabled) return;
        
        const scheduleNext = () => {
            const delay = idle.minInterval 
                ? Math.random() * (idle.maxInterval - idle.minInterval) + idle.minInterval
                : idle.interval;
            
            this.idleTimers[idleKey] = setTimeout(() => {
                if (idle.animation) {
                    this.preview.playExpressionSequence(idle.animation);
                } else if (idle.keyframes) {
                    this.preview.playExpressionSequence(idle);
                }
                scheduleNext();
            }, delay);
        };
        
        scheduleNext();
    }
    
    stopIdle(idleKey) {
        if (this.idleTimers[idleKey]) {
            clearTimeout(this.idleTimers[idleKey]);
            delete this.idleTimers[idleKey];
        }
    }
    
    stopAll() {
        this.queue = [];
        this.isPlaying = false;
        Object.keys(this.idleTimers).forEach(key => this.stopIdle(key));
    }
}
