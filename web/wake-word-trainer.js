/**
 * Wake Word Training System
 * Allows users to create and train custom wake words using voice samples
 */

export class WakeWordTrainer {
    constructor(voiceInput, options = {}) {
        this.voiceInput = voiceInput;
        this.options = {
            samplesRequired: 3,
            minSampleLength: 1000, // ms
            maxSampleLength: 3000, // ms
            similarityThreshold: 0.75,
            ...options
        };
        
        // Training state
        this.isTraining = false;
        this.currentWakeWord = null;
        this.samples = [];
        this.trainedModels = new Map();
        
        // Audio analysis
        this.audioContext = null;
        this.analyzer = null;
        
        // Load saved models
        this.loadTrainedModels();
        
        console.log('[WakeWordTrainer] Wake word trainer initialized');
    }
    
    /**
     * Initialize audio context for analysis
     */
    initializeAudio() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyzer = this.audioContext.createAnalyser();
            this.analyzer.fftSize = 2048;
        }
    }
    
    /**
     * Start training a new wake word
     */
    async startTraining(wakeWord) {
        if (this.isTraining) {
            return {
                success: false,
                message: 'Already training a wake word'
            };
        }
        
        this.isTraining = true;
        this.currentWakeWord = wakeWord.toLowerCase();
        this.samples = [];
        
        this.initializeAudio();
        
        this.speak(`Training wake word: ${wakeWord}. Please say "${wakeWord}" ${this.options.samplesRequired} times clearly.`);
        
        console.log(`[WakeWordTrainer] Started training: ${wakeWord}`);
        
        return {
            success: true,
            message: `Training "${wakeWord}". Say it ${this.options.samplesRequired} times.`,
            wakeWord: wakeWord,
            samplesRequired: this.options.samplesRequired
        };
    }
    
    /**
     * Record a training sample
     */
    async recordSample(audioData) {
        if (!this.isTraining) {
            return { success: false, message: 'Not in training mode' };
        }
        
        // Extract audio features
        const features = await this.extractFeatures(audioData);
        
        // Validate sample length
        if (features.duration < this.options.minSampleLength) {
            this.speak('Too short. Please say it again.');
            return {
                success: false,
                message: 'Sample too short',
                minLength: this.options.minSampleLength
            };
        }
        
        if (features.duration > this.options.maxSampleLength) {
            this.speak('Too long. Please say it again.');
            return {
                success: false,
                message: 'Sample too long',
                maxLength: this.options.maxSampleLength
            };
        }
        
        // Add sample
        this.samples.push({
            features,
            timestamp: Date.now(),
            wakeWord: this.currentWakeWord
        });
        
        const remaining = this.options.samplesRequired - this.samples.length;
        
        if (remaining > 0) {
            this.speak(`Good. ${remaining} more time${remaining > 1 ? 's' : ''}.`);
            return {
                success: true,
                message: `Sample ${this.samples.length} recorded`,
                remaining
            };
        } else {
            // All samples collected, create model
            return await this.finalizeTraining();
        }
    }
    
    /**
     * Finalize training and create wake word model
     */
    async finalizeTraining() {
        if (this.samples.length < this.options.samplesRequired) {
            return {
                success: false,
                message: 'Not enough samples'
            };
        }
        
        // Create wake word model from samples
        const model = this.createModel(this.samples);
        
        // Test model consistency
        const consistency = this.testModelConsistency(model, this.samples);
        
        if (consistency < this.options.similarityThreshold) {
            this.speak('Samples too different. Please try again.');
            this.isTraining = false;
            this.samples = [];
            
            return {
                success: false,
                message: 'Samples inconsistent, training failed',
                consistency: consistency
            };
        }
        
        // Save model
        this.trainedModels.set(this.currentWakeWord, {
            model,
            wakeWord: this.currentWakeWord,
            trained: new Date().toISOString(),
            samples: this.samples.length,
            consistency
        });
        
        this.saveTrainedModels();
        
        // Add to voice input
        if (this.voiceInput) {
            this.voiceInput.addWakeWord(this.currentWakeWord);
        }
        
        this.speak(`Wake word "${this.currentWakeWord}" trained successfully!`);
        
        const result = {
            success: true,
            message: `Wake word "${this.currentWakeWord}" trained`,
            wakeWord: this.currentWakeWord,
            consistency: consistency,
            samples: this.samples.length
        };
        
        this.isTraining = false;
        this.currentWakeWord = null;
        this.samples = [];
        
        return result;
    }
    
    /**
     * Cancel current training
     */
    cancelTraining() {
        if (!this.isTraining) {
            return { success: false, message: 'Not in training mode' };
        }
        
        const wakeWord = this.currentWakeWord;
        
        this.isTraining = false;
        this.currentWakeWord = null;
        this.samples = [];
        
        this.speak('Training cancelled');
        
        return {
            success: true,
            message: `Training for "${wakeWord}" cancelled`
        };
    }
    
    /**
     * Extract audio features from sample
     */
    async extractFeatures(audioData) {
        // Simple feature extraction: energy, pitch, duration, spectral centroid
        const features = {
            duration: audioData.duration || 0,
            energy: this.calculateEnergy(audioData),
            pitch: this.estimatePitch(audioData),
            spectralCentroid: this.calculateSpectralCentroid(audioData),
            mfcc: this.extractMFCC(audioData), // Mel-frequency cepstral coefficients
            timestamp: Date.now()
        };
        
        return features;
    }
    
    /**
     * Calculate audio energy
     */
    calculateEnergy(audioData) {
        if (!audioData.samples) return 0;
        
        let sum = 0;
        for (let i = 0; i < audioData.samples.length; i++) {
            sum += audioData.samples[i] * audioData.samples[i];
        }
        return Math.sqrt(sum / audioData.samples.length);
    }
    
    /**
     * Estimate pitch (fundamental frequency)
     */
    estimatePitch(audioData) {
        // Simplified autocorrelation method
        if (!audioData.samples || audioData.samples.length < 100) return 0;
        
        const sampleRate = audioData.sampleRate || 48000;
        const minPeriod = Math.floor(sampleRate / 500); // 500 Hz max
        const maxPeriod = Math.floor(sampleRate / 50);  // 50 Hz min
        
        let bestPeriod = 0;
        let bestCorrelation = -1;
        
        for (let period = minPeriod; period < maxPeriod; period++) {
            let correlation = 0;
            for (let i = 0; i < audioData.samples.length - period; i++) {
                correlation += audioData.samples[i] * audioData.samples[i + period];
            }
            
            if (correlation > bestCorrelation) {
                bestCorrelation = correlation;
                bestPeriod = period;
            }
        }
        
        return bestPeriod > 0 ? sampleRate / bestPeriod : 0;
    }
    
    /**
     * Calculate spectral centroid
     */
    calculateSpectralCentroid(audioData) {
        if (!audioData.spectrum) return 0;
        
        let weightedSum = 0;
        let sum = 0;
        
        for (let i = 0; i < audioData.spectrum.length; i++) {
            weightedSum += i * audioData.spectrum[i];
            sum += audioData.spectrum[i];
        }
        
        return sum > 0 ? weightedSum / sum : 0;
    }
    
    /**
     * Extract MFCC features (simplified)
     */
    extractMFCC(audioData) {
        // Simplified MFCC extraction - in production, use a proper library
        const mfcc = [];
        const numCoefficients = 13;
        
        if (audioData.spectrum) {
            for (let i = 0; i < numCoefficients && i < audioData.spectrum.length; i++) {
                mfcc.push(audioData.spectrum[i]);
            }
        }
        
        return mfcc;
    }
    
    /**
     * Create wake word model from samples
     */
    createModel(samples) {
        // Average features across all samples
        const model = {
            avgEnergy: 0,
            avgPitch: 0,
            avgSpectralCentroid: 0,
            avgMFCC: [],
            avgDuration: 0,
            variance: {}
        };
        
        // Calculate averages
        samples.forEach(sample => {
            model.avgEnergy += sample.features.energy;
            model.avgPitch += sample.features.pitch;
            model.avgSpectralCentroid += sample.features.spectralCentroid;
            model.avgDuration += sample.features.duration;
            
            if (sample.features.mfcc) {
                sample.features.mfcc.forEach((coef, i) => {
                    model.avgMFCC[i] = (model.avgMFCC[i] || 0) + coef;
                });
            }
        });
        
        const n = samples.length;
        model.avgEnergy /= n;
        model.avgPitch /= n;
        model.avgSpectralCentroid /= n;
        model.avgDuration /= n;
        model.avgMFCC = model.avgMFCC.map(v => v / n);
        
        // Calculate variance for threshold
        model.variance = this.calculateVariance(samples, model);
        
        return model;
    }
    
    /**
     * Calculate variance in features
     */
    calculateVariance(samples, model) {
        const variance = {
            energy: 0,
            pitch: 0,
            spectralCentroid: 0,
            duration: 0
        };
        
        samples.forEach(sample => {
            variance.energy += Math.pow(sample.features.energy - model.avgEnergy, 2);
            variance.pitch += Math.pow(sample.features.pitch - model.avgPitch, 2);
            variance.spectralCentroid += Math.pow(sample.features.spectralCentroid - model.avgSpectralCentroid, 2);
            variance.duration += Math.pow(sample.features.duration - model.avgDuration, 2);
        });
        
        const n = samples.length;
        variance.energy = Math.sqrt(variance.energy / n);
        variance.pitch = Math.sqrt(variance.pitch / n);
        variance.spectralCentroid = Math.sqrt(variance.spectralCentroid / n);
        variance.duration = Math.sqrt(variance.duration / n);
        
        return variance;
    }
    
    /**
     * Test model consistency across samples
     */
    testModelConsistency(model, samples) {
        let totalSimilarity = 0;
        
        samples.forEach(sample => {
            const similarity = this.calculateSimilarity(model, sample.features);
            totalSimilarity += similarity;
        });
        
        return totalSimilarity / samples.length;
    }
    
    /**
     * Calculate similarity between model and features
     */
    calculateSimilarity(model, features) {
        // Weighted similarity calculation
        const weights = {
            energy: 0.2,
            pitch: 0.3,
            spectralCentroid: 0.2,
            mfcc: 0.3
        };
        
        let similarity = 0;
        
        // Energy similarity
        const energyDiff = Math.abs(model.avgEnergy - features.energy);
        const energySim = 1 - Math.min(1, energyDiff / (model.avgEnergy + 0.0001));
        similarity += weights.energy * energySim;
        
        // Pitch similarity
        const pitchDiff = Math.abs(model.avgPitch - features.pitch);
        const pitchSim = 1 - Math.min(1, pitchDiff / (model.avgPitch + 0.0001));
        similarity += weights.pitch * pitchSim;
        
        // Spectral centroid similarity
        const centroidDiff = Math.abs(model.avgSpectralCentroid - features.spectralCentroid);
        const centroidSim = 1 - Math.min(1, centroidDiff / (model.avgSpectralCentroid + 0.0001));
        similarity += weights.spectralCentroid * centroidSim;
        
        // MFCC similarity (cosine similarity)
        if (model.avgMFCC && features.mfcc) {
            const mfccSim = this.cosineSimilarity(model.avgMFCC, features.mfcc);
            similarity += weights.mfcc * mfccSim;
        }
        
        return similarity;
    }
    
    /**
     * Calculate cosine similarity between two vectors
     */
    cosineSimilarity(a, b) {
        if (!a || !b || a.length !== b.length) return 0;
        
        let dotProduct = 0;
        let normA = 0;
        let normB = 0;
        
        for (let i = 0; i < a.length; i++) {
            dotProduct += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        
        normA = Math.sqrt(normA);
        normB = Math.sqrt(normB);
        
        return (normA > 0 && normB > 0) ? dotProduct / (normA * normB) : 0;
    }
    
    /**
     * Recognize wake word from audio features
     */
    recognize(features) {
        let bestMatch = null;
        let bestSimilarity = 0;
        
        for (const [wakeWord, modelData] of this.trainedModels) {
            const similarity = this.calculateSimilarity(modelData.model, features);
            
            if (similarity > bestSimilarity && similarity >= this.options.similarityThreshold) {
                bestSimilarity = similarity;
                bestMatch = wakeWord;
            }
        }
        
        return {
            wakeWord: bestMatch,
            confidence: bestSimilarity,
            recognized: bestMatch !== null
        };
    }
    
    /**
     * Delete a trained wake word
     */
    deleteWakeWord(wakeWord) {
        const lower = wakeWord.toLowerCase();
        
        if (!this.trainedModels.has(lower)) {
            return {
                success: false,
                message: `Wake word "${wakeWord}" not found`
            };
        }
        
        this.trainedModels.delete(lower);
        this.saveTrainedModels();
        
        // Remove from voice input
        if (this.voiceInput) {
            this.voiceInput.removeWakeWord(lower);
        }
        
        return {
            success: true,
            message: `Wake word "${wakeWord}" deleted`
        };
    }
    
    /**
     * List all trained wake words
     */
    listWakeWords() {
        const list = [];
        
        for (const [wakeWord, modelData] of this.trainedModels) {
            list.push({
                wakeWord: wakeWord,
                trained: modelData.trained,
                samples: modelData.samples,
                consistency: modelData.consistency
            });
        }
        
        return list;
    }
    
    /**
     * Export trained models
     */
    export() {
        const data = {
            models: Array.from(this.trainedModels.entries()),
            exported: new Date().toISOString()
        };
        
        return data;
    }
    
    /**
     * Import trained models
     */
    import(data) {
        if (!data.models) {
            return { success: false, message: 'Invalid data format' };
        }
        
        let imported = 0;
        
        data.models.forEach(([wakeWord, modelData]) => {
            this.trainedModels.set(wakeWord, modelData);
            imported++;
        });
        
        this.saveTrainedModels();
        
        return {
            success: true,
            message: `Imported ${imported} wake words`,
            count: imported
        };
    }
    
    /**
     * Save trained models to localStorage
     */
    saveTrainedModels() {
        try {
            const data = {
                models: Array.from(this.trainedModels.entries())
            };
            localStorage.setItem('aios_wake_word_models', JSON.stringify(data));
            console.log(`[WakeWordTrainer] Saved ${this.trainedModels.size} models`);
        } catch (error) {
            console.error('[WakeWordTrainer] Error saving models:', error);
        }
    }
    
    /**
     * Load trained models from localStorage
     */
    loadTrainedModels() {
        try {
            const data = localStorage.getItem('aios_wake_word_models');
            if (data) {
                const parsed = JSON.parse(data);
                this.trainedModels = new Map(parsed.models || []);
                console.log(`[WakeWordTrainer] Loaded ${this.trainedModels.size} models`);
            }
        } catch (error) {
            console.error('[WakeWordTrainer] Error loading models:', error);
        }
    }
    
    /**
     * Get training status
     */
    getStatus() {
        return {
            isTraining: this.isTraining,
            currentWakeWord: this.currentWakeWord,
            samplesCollected: this.samples.length,
            samplesRequired: this.options.samplesRequired,
            trainedWakeWords: this.trainedModels.size
        };
    }
    
    /**
     * Utility: Speak
     */
    speak(text) {
        if (window.speak) {
            window.speak(text);
        } else if (window.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(utterance);
        }
    }
}

export default WakeWordTrainer;
