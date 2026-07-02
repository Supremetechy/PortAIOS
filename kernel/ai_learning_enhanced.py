#!/usr/bin/env python3
"""
PortAIOS Enhanced AI Learning Engine
Advanced machine learning with neural networks and deep learning
Sophisticated pattern recognition and predictive modeling
"""

import logging
import json
import time
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque
import threading

logger = logging.getLogger("AIOS.EnhancedAI")

# Import base learning engine
from kernel.ai_learning_engine import (
    AILearningEngine, 
    UserAction, 
    Prediction,
    BehaviorDatabase
)

# Try to import advanced ML libraries
try:
    from sklearn.neural_network import MLPClassifier
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available - using basic learning")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas not available - using numpy arrays")


class TemporalPattern:
    """Analyzes temporal patterns in user behavior"""
    
    def __init__(self):
        self.hourly_patterns = defaultdict(lambda: defaultdict(int))
        self.daily_patterns = defaultdict(lambda: defaultdict(int))
        self.weekly_patterns = defaultdict(lambda: defaultdict(int))
        
    def learn_pattern(self, action: UserAction):
        """Learn temporal patterns from action"""
        dt = datetime.fromtimestamp(action.timestamp)
        hour = dt.hour
        day_of_week = dt.weekday()
        week_number = dt.isocalendar()[1]
        
        action_key = f"{action.action_type}:{action.target}"
        
        # Hourly patterns
        self.hourly_patterns[hour][action_key] += 1
        
        # Daily patterns
        self.daily_patterns[day_of_week][action_key] += 1
        
        # Weekly patterns
        self.weekly_patterns[week_number % 4][action_key] += 1  # 4-week cycle
    
    def predict_for_time(self, dt: datetime, top_k: int = 5) -> List[Tuple[str, float]]:
        """Predict likely actions for given time"""
        hour = dt.hour
        day_of_week = dt.weekday()
        
        predictions = defaultdict(float)
        
        # Weight hourly patterns (50%)
        hour_total = sum(self.hourly_patterns[hour].values())
        if hour_total > 0:
            for action, count in self.hourly_patterns[hour].items():
                predictions[action] += (count / hour_total) * 0.5
        
        # Weight daily patterns (30%)
        day_total = sum(self.daily_patterns[day_of_week].values())
        if day_total > 0:
            for action, count in self.daily_patterns[day_of_week].items():
                predictions[action] += (count / day_total) * 0.3
        
        # Weight adjacent hours (20%)
        for offset in [-1, 1]:
            adj_hour = (hour + offset) % 24
            adj_total = sum(self.hourly_patterns[adj_hour].values())
            if adj_total > 0:
                for action, count in self.hourly_patterns[adj_hour].items():
                    predictions[action] += (count / adj_total) * 0.1
        
        # Sort and return top K
        sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        return sorted_predictions[:top_k]


class SequencePredictor:
    """Advanced sequence prediction using n-grams and transition matrices"""
    
    def __init__(self, n: int = 3):
        self.n = n  # N-gram size
        self.sequences = deque(maxlen=1000)  # Store recent sequences
        self.transition_matrix = defaultdict(lambda: defaultdict(int))
        self.ngrams = defaultdict(lambda: defaultdict(int))
        
    def add_action(self, action_key: str):
        """Add action to sequence"""
        self.sequences.append(action_key)
        
        # Update transition matrix (1-gram)
        if len(self.sequences) >= 2:
            prev = self.sequences[-2]
            curr = self.sequences[-1]
            self.transition_matrix[prev][curr] += 1
        
        # Update n-grams
        if len(self.sequences) >= self.n:
            ngram = tuple(list(self.sequences)[-self.n:-1])
            next_action = self.sequences[-1]
            self.ngrams[ngram][next_action] += 1
    
    def predict_next(self, context_size: int = 3) -> List[Tuple[str, float]]:
        """Predict next action based on recent history"""
        if len(self.sequences) < context_size:
            return []
        
        predictions = defaultdict(float)
        
        # N-gram prediction (if available)
        if len(self.sequences) >= self.n:
            ngram = tuple(list(self.sequences)[-(self.n-1):])
            if ngram in self.ngrams:
                total = sum(self.ngrams[ngram].values())
                for action, count in self.ngrams[ngram].items():
                    predictions[action] += (count / total) * 0.6
        
        # Transition matrix prediction
        last_action = self.sequences[-1]
        if last_action in self.transition_matrix:
            total = sum(self.transition_matrix[last_action].values())
            if total > 0:
                for action, count in self.transition_matrix[last_action].items():
                    predictions[action] += (count / total) * 0.4
        
        # Sort and return
        sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        return sorted_predictions[:5]


class NeuralPredictor:
    """Neural network-based action prediction"""
    
    def __init__(self):
        self.enabled = SKLEARN_AVAILABLE
        self.model = None
        self.label_encoder = LabelEncoder()
        self.scaler = StandardScaler()
        self.trained = False
        self.min_training_samples = 100
        
        if self.enabled:
            # Multi-layer perceptron for classification
            self.model = MLPClassifier(
                hidden_layer_sizes=(128, 64, 32),
                activation='relu',
                solver='adam',
                max_iter=500,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1
            )
    
    def prepare_features(self, action: UserAction) -> np.ndarray:
        """Convert action to feature vector"""
        dt = datetime.fromtimestamp(action.timestamp)
        
        features = [
            dt.hour,  # Hour of day (0-23)
            dt.weekday(),  # Day of week (0-6)
            dt.day,  # Day of month (1-31)
            dt.month,  # Month (1-12)
            action.timestamp % 86400,  # Seconds since midnight
            1 if dt.weekday() < 5 else 0,  # Is weekday
            1 if 9 <= dt.hour < 17 else 0,  # Is work hours
            hash(action.input_method) % 1000,  # Input method hash
        ]
        
        return np.array(features).reshape(1, -1)
    
    def train(self, actions: List[UserAction]) -> Dict[str, Any]:
        """Train neural network on historical data"""
        if not self.enabled:
            return {'success': False, 'error': 'ML libraries not available'}
        
        if len(actions) < self.min_training_samples:
            return {
                'success': False, 
                'error': f'Need at least {self.min_training_samples} samples, have {len(actions)}'
            }
        
        logger.info(f"Training neural network on {len(actions)} samples...")
        
        # Prepare training data
        X = []
        y = []
        
        for action in actions:
            features = self.prepare_features(action)
            X.append(features.flatten())
            y.append(f"{action.action_type}:{action.target}")
        
        X = np.array(X)
        y = np.array(y)
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_encoded, test_size=0.2, random_state=42
        )
        
        # Train model
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        self.trained = True
        
        logger.info(f"Neural network trained with {accuracy:.2%} accuracy")
        
        return {
            'success': True,
            'accuracy': accuracy,
            'samples': len(actions),
            'classes': len(self.label_encoder.classes_)
        }
    
    def predict(self, context: Dict[str, Any], top_k: int = 5) -> List[Tuple[str, float]]:
        """Predict next actions using neural network"""
        if not self.enabled or not self.trained:
            return []
        
        # Create dummy action for feature extraction
        dummy_action = UserAction(
            timestamp=time.time(),
            action_type='dummy',
            target='dummy',
            context=context,
            input_method='dummy'
        )
        
        features = self.prepare_features(dummy_action)
        features_scaled = self.scaler.transform(features)
        
        # Get prediction probabilities
        probas = self.model.predict_proba(features_scaled)[0]
        
        # Get top K predictions
        top_indices = np.argsort(probas)[-top_k:][::-1]
        
        predictions = []
        for idx in top_indices:
            action_key = self.label_encoder.classes_[idx]
            confidence = probas[idx]
            predictions.append((action_key, float(confidence)))
        
        return predictions


class EnhancedAILearningEngine(AILearningEngine):
    """
    Enhanced AI learning engine with advanced ML algorithms
    Extends base engine with neural networks and sophisticated pattern recognition
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        super().__init__(data_dir)
        
        # Advanced predictors
        self.temporal_predictor = TemporalPattern()
        self.sequence_predictor = SequencePredictor(n=3)
        self.neural_predictor = NeuralPredictor()
        
        # Training state
        self.auto_train_enabled = True
        self.auto_train_threshold = 100  # Train every 100 actions
        self.actions_since_training = 0
        
        # Ensemble weights
        self.ensemble_weights = {
            'temporal': 0.3,
            'sequence': 0.25,
            'neural': 0.35,
            'context': 0.1
        }
        
        # Performance tracking
        self.prediction_accuracy = deque(maxlen=100)
        self.prediction_history = deque(maxlen=1000)
        
        logger.info("Enhanced AI Learning Engine initialized")
    
    def record_action(self, action: UserAction):
        """Record action and update all predictors"""
        # Call parent implementation
        super().record_action(action)
        
        # Update advanced predictors
        action_key = f"{action.action_type}:{action.target}"
        
        self.temporal_predictor.learn_pattern(action)
        self.sequence_predictor.add_action(action_key)
        
        # Check if we need to retrain neural network
        self.actions_since_training += 1
        if self.auto_train_enabled and self.actions_since_training >= self.auto_train_threshold:
            self._auto_train()
    
    def _auto_train(self):
        """Automatically retrain neural network"""
        logger.info("Auto-training neural network...")
        
        # Get recent actions
        actions = self.db.get_actions(limit=1000)
        
        if len(actions) >= self.neural_predictor.min_training_samples:
            result = self.neural_predictor.train(actions)
            if result['success']:
                logger.info(f"Auto-training complete: {result['accuracy']:.2%} accuracy")
            self.actions_since_training = 0
    
    def predict_next_actions(self, context: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Prediction]:
        """
        Enhanced prediction using ensemble of multiple algorithms
        Combines temporal, sequence, neural, and context-based predictions
        """
        if context is None:
            context = self._get_current_context()
        
        # Get predictions from all sources
        all_predictions = defaultdict(lambda: {'confidence': 0.0, 'sources': []})
        
        # 1. Temporal predictions
        dt = datetime.fromtimestamp(context.get('timestamp', time.time()))
        temporal_preds = self.temporal_predictor.predict_for_time(dt, top_k=10)
        
        for action_key, score in temporal_preds:
            all_predictions[action_key]['confidence'] += score * self.ensemble_weights['temporal']
            all_predictions[action_key]['sources'].append('temporal')
        
        # 2. Sequence predictions
        sequence_preds = self.sequence_predictor.predict_next()
        
        for action_key, score in sequence_preds:
            all_predictions[action_key]['confidence'] += score * self.ensemble_weights['sequence']
            all_predictions[action_key]['sources'].append('sequence')
        
        # 3. Neural network predictions
        neural_preds = self.neural_predictor.predict(context, top_k=10)
        
        for action_key, score in neural_preds:
            all_predictions[action_key]['confidence'] += score * self.ensemble_weights['neural']
            all_predictions[action_key]['sources'].append('neural')
        
        # 4. Context-based predictions (from parent)
        context_preds = super().predict_next_actions(context, limit=10)
        
        for pred in context_preds:
            action_key = f"{pred.action_type}:{pred.target}"
            all_predictions[action_key]['confidence'] += pred.confidence * self.ensemble_weights['context']
            all_predictions[action_key]['sources'].append('context')
        
        # Combine and rank predictions
        final_predictions = []
        
        for action_key, data in all_predictions.items():
            if ':' in action_key:
                parts = action_key.split(':', 1)
                action_type = parts[0]
                target = parts[1]
                
                # Create reasoning
                sources = data['sources']
                reasoning = self._generate_reasoning(sources, dt, action_type, target)
                
                final_predictions.append(Prediction(
                    action_type=action_type,
                    target=target,
                    confidence=min(data['confidence'], 0.99),  # Cap at 99%
                    reasoning=reasoning,
                    timestamp=time.time()
                ))
        
        # Sort by confidence
        final_predictions.sort(key=lambda p: p.confidence, reverse=True)
        
        # Log predictions for accuracy tracking
        self.prediction_history.append({
            'timestamp': time.time(),
            'predictions': [(p.action_type, p.target, p.confidence) for p in final_predictions[:limit]]
        })
        
        return final_predictions[:limit]
    
    def _generate_reasoning(self, sources: List[str], dt: datetime, action_type: str, target: str) -> str:
        """Generate human-readable reasoning for prediction"""
        source_count = len(set(sources))
        
        if source_count >= 3:
            reasoning = f"Strong pattern detected across multiple systems"
        elif 'neural' in sources:
            reasoning = f"AI predicts you'll do this based on learned patterns"
        elif 'temporal' in sources:
            hour = dt.hour
            day_name = dt.strftime('%A')
            reasoning = f"You often do this at {hour:02d}:00 on {day_name}"
        elif 'sequence' in sources:
            reasoning = f"You typically do this next in this workflow"
        else:
            reasoning = f"Predicted based on your usage patterns"
        
        return reasoning
    
    def record_prediction_outcome(self, predicted_action: str, actual_action: str):
        """Record whether prediction was correct (for accuracy tracking)"""
        correct = (predicted_action == actual_action)
        self.prediction_accuracy.append(1.0 if correct else 0.0)
        
        logger.debug(f"Prediction {'correct' if correct else 'incorrect'}: {predicted_action} vs {actual_action}")
    
    def get_prediction_accuracy(self) -> float:
        """Get current prediction accuracy"""
        if not self.prediction_accuracy:
            return 0.0
        return sum(self.prediction_accuracy) / len(self.prediction_accuracy)
    
    def get_advanced_statistics(self) -> Dict[str, Any]:
        """Get enhanced statistics including ML model performance"""
        base_stats = super().get_statistics()
        
        advanced_stats = {
            **base_stats,
            'neural_network': {
                'enabled': self.neural_predictor.enabled,
                'trained': self.neural_predictor.trained,
                'accuracy': getattr(self.neural_predictor, 'last_accuracy', None)
            },
            'prediction_accuracy': self.get_prediction_accuracy(),
            'ensemble_weights': self.ensemble_weights,
            'actions_since_training': self.actions_since_training,
            'temporal_patterns': len(self.temporal_predictor.hourly_patterns),
            'sequence_depth': self.sequence_predictor.n,
            'auto_train_enabled': self.auto_train_enabled
        }
        
        return advanced_stats
    
    def manual_train(self, sample_limit: int = 1000) -> Dict[str, Any]:
        """Manually trigger neural network training"""
        actions = self.db.get_actions(limit=sample_limit)
        result = self.neural_predictor.train(actions)
        
        if result['success']:
            self.actions_since_training = 0
        
        return result
    
    def set_ensemble_weights(self, weights: Dict[str, float]):
        """Customize ensemble prediction weights"""
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        
        self.ensemble_weights = weights
        logger.info(f"Ensemble weights updated: {weights}")
    
    def export_model_stats(self) -> Dict[str, Any]:
        """Export detailed model statistics for dashboard"""
        return {
            'temporal': {
                'hourly_patterns': dict(self.temporal_predictor.hourly_patterns),
                'daily_patterns': dict(self.temporal_predictor.daily_patterns),
                'weekly_patterns': dict(self.temporal_predictor.weekly_patterns)
            },
            'sequence': {
                'transition_matrix': dict(self.sequence_predictor.transition_matrix),
                'ngrams': dict(self.sequence_predictor.ngrams),
                'sequence_length': len(self.sequence_predictor.sequences)
            },
            'neural': {
                'enabled': self.neural_predictor.enabled,
                'trained': self.neural_predictor.trained,
                'feature_importance': self._get_feature_importance()
            },
            'performance': {
                'prediction_accuracy': self.get_prediction_accuracy(),
                'recent_predictions': list(self.prediction_history)[-10:]
            }
        }
    
    def _get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance from neural network (if trained)"""
        if not self.neural_predictor.trained:
            return None
        
        # Feature names
        feature_names = [
            'hour', 'day_of_week', 'day_of_month', 'month',
            'seconds_since_midnight', 'is_weekday', 'is_work_hours', 'input_method'
        ]
        
        # For neural networks, we can't directly get feature importance
        # But we can provide the feature names for the dashboard
        return {name: 1.0/len(feature_names) for name in feature_names}


# Global instance
_enhanced_ai_engine = None


def get_enhanced_ai_engine() -> EnhancedAILearningEngine:
    """Get or create global enhanced AI learning engine"""
    global _enhanced_ai_engine
    if _enhanced_ai_engine is None:
        _enhanced_ai_engine = EnhancedAILearningEngine()
    return _enhanced_ai_engine


# Eel integration
try:
    import eel
    
    def setup_enhanced_ai_eel_api():
        """Setup Eel-exposed functions for enhanced AI learning"""
        engine = get_enhanced_ai_engine()
        
        @eel.expose
        def get_enhanced_predictions(context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
            """Get enhanced AI predictions"""
            predictions = engine.predict_next_actions(context)
            return [
                {
                    'action_type': p.action_type,
                    'target': p.target,
                    'confidence': p.confidence,
                    'reasoning': p.reasoning
                }
                for p in predictions
            ]
        
        @eel.expose
        def train_neural_network(sample_limit: int = 1000) -> Dict[str, Any]:
            """Manually train neural network"""
            return engine.manual_train(sample_limit)
        
        @eel.expose
        def get_advanced_ai_stats() -> Dict[str, Any]:
            """Get advanced AI statistics"""
            return engine.get_advanced_statistics()
        
        @eel.expose
        def get_model_stats_for_dashboard() -> Dict[str, Any]:
            """Get model statistics for visualization"""
            return engine.export_model_stats()
        
        @eel.expose
        def set_prediction_weights(weights: Dict[str, float]) -> Dict[str, Any]:
            """Set ensemble prediction weights"""
            try:
                engine.set_ensemble_weights(weights)
                return {'success': True, 'weights': weights}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        @eel.expose
        def get_prediction_accuracy() -> float:
            """Get current prediction accuracy"""
            return engine.get_prediction_accuracy()
        
        logger.info("Enhanced AI Learning Eel API initialized")
        return engine

except ImportError:
    pass


__all__ = [
    'EnhancedAILearningEngine',
    'NeuralPredictor',
    'TemporalPattern',
    'SequencePredictor',
    'get_enhanced_ai_engine',
    'setup_enhanced_ai_eel_api'
]
